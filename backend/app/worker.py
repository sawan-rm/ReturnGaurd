import asyncio
import uuid
from datetime import datetime, timezone
from arq import Worker
from arq.connections import RedisSettings
from sqlalchemy import select
from app.database import async_session
from app.models import ReturnRequest, ReturnStatus, Order, Decision, DecisionOutcome
from app.config import settings
from app.ws import broadcast_update
from app.graph import return_graph_builder
from app.email_service import send_decision_email
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

async def process_return(ctx, return_id: str):
    print(f"⚙️  Worker started processing return {return_id}...")

    # ── 1. Mark as "processing" immediately ──────────────────────────────────
    async with async_session() as session:
        ret = await session.get(ReturnRequest, return_id)
        if not ret:
            print(f"❌ Return {return_id} not found!")
            return
        ret.status = ReturnStatus.processing
        
        # Pre-load the order for the graph
        order = await session.get(Order, ret.order_id)
        order_user_id = order.user_id
        order_product_name = order.product_name
        order_product_category = order.product_category
        order_amount = order.amount
        order_ordered_at = order.ordered_at
        
        # Save return reason and photo_url before closing session
        ret_reason = ret.reason
        ret_photo_url = ret.photo_url
        
        await session.commit()

    await broadcast_update(return_id, "processing")

    # ── 2. Gather data for the AI agents ─────────────────────────────────────
    async with async_session() as session:
        # Count past returns for this user
        stmt = (
            select(ReturnRequest)
            .join(Order, ReturnRequest.order_id == Order.id)
            .where(Order.user_id == order_user_id)
        )
        result = await session.execute(stmt)
        past_returns = result.scalars().all()
        past_return_count = max(0, len(past_returns) - 1)  # exclude current

    days_since_order = (datetime.now(timezone.utc) - order_ordered_at.replace(tzinfo=timezone.utc)).days

    initial_state = {
        "return_id": return_id,
        "reason": ret_reason,
        "photo_url": ret_photo_url,
        "product_name": order_product_name,
        "product_category": order_product_category,
        "amount": order_amount,
        "days_since_order": days_since_order,
        "past_return_count": past_return_count,
        "fraud_score": 0.0,
        "policy_ok": True,
        "final_decision": None,
        "explanation": "",
    }

    # ── 3. Run the LangGraph pipeline with Checkpointer ──────────────────────
    print(f"🤖 Running LangGraph for return {return_id}...")
    
    # The checkpointer needs a psycopg3 connection string (not asyncpg)
    psycopg_url = settings.database_url.replace("+asyncpg", "")
    
    try:
        # Create connection pool for checkpointer
        # autocommit=True is required so checkpointer.setup() can run
        # CREATE INDEX CONCURRENTLY, which cannot run inside a transaction
        async with AsyncConnectionPool(
            conninfo=psycopg_url,
            max_size=10,
            kwargs={"autocommit": True},
        ) as pool:
            # In langgraph-checkpoint-postgres v2+, AsyncPostgresSaver is NOT a context manager
            checkpointer = AsyncPostgresSaver(pool)
            # This creates the checkpoint tables if they don't exist
            await checkpointer.setup()
            
            # Compile graph with memory
            # 1. Add the interrupt_before argument!
            graph = return_graph_builder.compile(checkpointer=checkpointer, interrupt_before=["governance_gate"])
            
            # We use the return_id as the thread_id so memory is tied to this specific return
            config = {"configurable": {"thread_id": return_id}}
            
            # ainvoke runs async!
            result_state = await graph.ainvoke(initial_state, config)

            # 2. Check if the graph is currently paused
            snapshot = await graph.aget_state(config)

            if snapshot.next and "governance_gate" in snapshot.next:
                print(f"⏸️ Return {return_id} paused at Governance Gate for human review!")

                # Override the status to escalated so it appears on the human Reviewer Dashboard
                final_decision = "escalated"
                explanation = "AI proposed DENY. Waiting for human confirmation at the Governance Gate."

                # We pull the actual fraud score from the paused state
                fraud_score = snapshot.values.get("fraud_score", 50.0)
            else:
                # The graph finished successfully (it was approved or naturally escalated)
                final_decision = result_state["final_decision"]
                explanation = result_state["explanation"]
                fraud_score = result_state["fraud_score"]
                

    except Exception as e:
        print(f"❌ LangGraph error: {e}")
        result_state = {
            **initial_state,
            "final_decision": "escalated",
            "explanation": "An error occurred during automated review. This return has been escalated for manual inspection.",
            "fraud_score": 50.0,
        }

    final_decision = result_state["final_decision"]
    explanation = result_state["explanation"]
    fraud_score = result_state["fraud_score"]

    # ── 4. Map decision → ReturnStatus ────────────────────────────────────────
    status_map = {
        "approved": ReturnStatus.approved,
        "denied": ReturnStatus.denied,
        "escalated": ReturnStatus.escalated,
    }
    outcome_map = {
        "approved": DecisionOutcome.approve,
        "denied": DecisionOutcome.deny,
        "escalated": DecisionOutcome.escalate,
    }
    new_status = status_map.get(final_decision, ReturnStatus.escalated)
    outcome = outcome_map.get(final_decision, DecisionOutcome.escalate)

    # ── 5. Save decision to database ─────────────────────────────────────────
    async with async_session() as session:
        ret = await session.get(ReturnRequest, return_id)
        ret.status = new_status
        ret.risk_score = round(fraud_score / 100, 4)

        decision = Decision(
            id=uuid.uuid4(),
            return_id=uuid.UUID(return_id),
            outcome=outcome,
            explanation=explanation,
        )
        session.add(decision)
        await session.commit()

    print(f"✅ LangGraph decided: {final_decision.upper()} for return {return_id}")
    print(f"   Fraud score: {fraud_score:.1f}/100")
    print(f"   Explanation: {explanation[:80]}...")

    # ── 6. Send automated email notification ──────────────────────────────────
    # Use a placeholder email since Keycloak user info isn't available in the worker.
    # In production you'd look up the user's email from the user_id.
    customer_email = f"customer-{str(order_user_id)[:8]}@returnguard.io"
    try:
        await asyncio.to_thread(
            send_decision_email,
            to_email=customer_email,
            decision=final_decision,
            product_name=order_product_name,
            amount=order_amount,
            explanation=explanation,
            return_id=return_id,
        )
    except Exception as e:
        print(f"⚠️  Email send failed: {e}")

    # ── 7. Broadcast live update to the frontend ──────────────────────────────
    await broadcast_update(return_id, new_status.value, round(fraud_score / 100, 4))


class WorkerSettings:
    functions = [process_return]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
