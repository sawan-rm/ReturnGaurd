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
from app.graph import return_graph


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
        order: Order = await session.get(Order, ret.order_id)
        await session.commit()

    await broadcast_update(return_id, "processing")

    # ── 2. Gather data for the AI agents ─────────────────────────────────────
    async with async_session() as session:
        # Count past returns for this user
        stmt = (
            select(ReturnRequest)
            .join(Order, ReturnRequest.order_id == Order.id)
            .where(Order.user_id == order.user_id)
        )
        result = await session.execute(stmt)
        past_returns = result.scalars().all()
        past_return_count = max(0, len(past_returns) - 1)  # exclude current

    days_since_order = (datetime.now(timezone.utc) - order.ordered_at.replace(tzinfo=timezone.utc)).days

    initial_state = {
        "return_id": return_id,
        "reason": ret.reason,
        "photo_url": ret.photo_url,
        "product_name": order.product_name,
        "product_category": order.product_category,
        "amount": order.amount,
        "days_since_order": days_since_order,
        "past_return_count": past_return_count,
        "fraud_score": 0.0,
        "policy_ok": True,
        "final_decision": None,
        "explanation": "",
    }

    # ── 3. Run the LangGraph pipeline ────────────────────────────────────────
    print(f"🤖 Running LangGraph for return {return_id}...")
    try:
        result_state = await asyncio.to_thread(return_graph.invoke, initial_state)
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

    # ── 6. Broadcast live update to the frontend ──────────────────────────────
    await broadcast_update(return_id, new_status.value, round(fraud_score / 100, 4))


class WorkerSettings:
    functions = [process_return]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
