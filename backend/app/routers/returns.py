from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ReturnRequest, ReturnStatus, Decision, DecisionOutcome, Order
from app.schemas import ReturnRead, ReturnDetail
from app.minio_client import get_minio_client
from app.auth import get_current_user
from app.ws import broadcast_update
from app.graph import return_graph_builder
from app.audit import get_prev_hash
from app.config import settings

from arq import create_pool
from arq.connections import RedisSettings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

router = APIRouter(prefix="/returns", tags=["returns"])


class ResumeAction(BaseModel):
    action: str  # "confirm_deny" or "override_approve"


@router.post("/", response_model=ReturnRead, status_code=201)
async def create_return(
    order_id: UUID = Form(...),
    reason: str = Form(...),
    photo: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Check that the order exists
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    photo_url = None
    if photo:
        minio_client = get_minio_client()
        filename = f"{uuid.uuid4()}-{photo.filename}"
        minio_client.put_object(
            settings.minio_bucket,
            filename,
            photo.file,
            length=-1,
            part_size=10*1024*1024,
            content_type=photo.content_type
        )
        photo_url = f"http://localhost:9000/{settings.minio_bucket}/{filename}"

    ret = ReturnRequest(order_id=order_id, reason=reason, photo_url=photo_url)
    db.add(ret)
    await db.commit()
    await db.refresh(ret)

    # Put the return-processing job into Redis
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job('process_return', str(ret.id))
    
    return ret


@router.get("/", response_model=list[ReturnRead])
async def list_returns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReturnRequest).order_by(ReturnRequest.created_at.desc()))
    return result.scalars().all()


@router.get("/{return_id}", response_model=ReturnDetail)
async def get_return(return_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ReturnRequest)
        .where(ReturnRequest.id == return_id)
        .options(selectinload(ReturnRequest.decision))
    )
    ret = result.scalar_one_or_none()
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    return ret


@router.post("/{return_id}/resume")
async def resume_return(
    return_id: UUID,
    body: ResumeAction,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """HITL: Reviewer confirms an AI denial or overrides it to approved."""

    # 1. Fetch the return and verify it is paused at the governance gate
    ret = await db.get(ReturnRequest, return_id)
    if not ret:
        raise HTTPException(status_code=404, detail="Return not found")
    if ret.status != ReturnStatus.escalated:
        raise HTTPException(status_code=400, detail="Return is not awaiting human review")

    if body.action not in ("confirm_deny", "override_approve"):
        raise HTTPException(status_code=422, detail="action must be 'confirm_deny' or 'override_approve'")

    # 2. Reconnect to LangGraph via the Postgres checkpointer
    psycopg_url = settings.database_url.replace("+asyncpg", "")
    config = {"configurable": {"thread_id": str(return_id)}}

    async with AsyncConnectionPool(
        conninfo=psycopg_url,
        max_size=10,
        kwargs={"autocommit": True},
    ) as pool:
        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        # Compile WITHOUT interrupt_before so the graph can continue past the gate
        graph = return_graph_builder.compile(checkpointer=checkpointer)

        # 3. If reviewer chose to override, update the graph state before resuming
        if body.action == "override_approve":
            await graph.aupdate_state(
                config,
                {
                    "final_decision": "approved",
                    "explanation": "Human reviewer overrode the AI denial. Return approved.",
                },
            )

        # 4. Resume the graph — passing None re-uses the saved checkpoint
        result_state = await graph.ainvoke(None, config)

    final_decision = result_state.get("final_decision", "denied")
    explanation = result_state.get("explanation", "")

    # 5. Map to DB status and outcome
    new_status = ReturnStatus.approved if final_decision == "approved" else ReturnStatus.denied
    outcome = DecisionOutcome.approve if final_decision == "approved" else DecisionOutcome.deny

    # 6. Update the return status in the database
    ret.status = new_status
    await db.commit()

    # 7. Create a new Decision row marking this as a human override
    decision = Decision(
        id=uuid.uuid4(),
        return_id=return_id,
        outcome=outcome,
        explanation=explanation,
        human_override=True,
        prev_hash=await get_prev_hash(db),
    )
    db.add(decision)
    await db.commit()

    # 8. Push live update to the reviewer's dashboard via WebSocket
    await broadcast_update(str(return_id), new_status.value)

    return {"status": "ok", "decision": final_decision}
