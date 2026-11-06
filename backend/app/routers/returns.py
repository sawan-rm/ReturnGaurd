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
from app.audit import get_prev_hash
from app.config import settings

from arq import create_pool
from arq.connections import RedisSettings

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
    # NOTE: In production with real user registration, enforce ownership strictly:
    # if str(order.user_id) != current_user["sub"]:
    #     raise HTTPException(status_code=403, detail="This order does not belong to you")
    # For this demo, DB orders are seeded with test user IDs that differ from Keycloak UUIDs,
    # so we allow any authenticated user to submit a return for any order.

    user_id = current_user.get("sub")
    if str(order.user_id) != user_id:
        raise HTTPException(status_code=403, detail="This order does not belong to you")
    # For this demo, DB orders are seeded with test user IDs that differ from Keycloak UUIDs,
    # so we allow any authenticated user to submit a return for any order.

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
async def list_returns(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    scope: str = "own",
):
    """
    scope=own  → Customer sees only their own returns (default)
    scope=all  → Reviewer/admin dashboard sees all returns
    """
    roles = current_user.get("realm_access", {}).get("roles", [])

    # Allow 'all' scope for reviewers, admins, or any authenticated user on the reviewer page
    if scope == "all" and ("reviewer" in roles or "admin" in roles or "customer" in roles):
        result = await db.execute(
            select(ReturnRequest).order_by(ReturnRequest.created_at.desc())
        )
    else:
        # Customer: only returns linked to their orders
        user_id = UUID(current_user["sub"])
        result = await db.execute(
            select(ReturnRequest)
            .join(Order)
            .where(Order.user_id == user_id)
            .order_by(ReturnRequest.created_at.desc())
        )
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

    # 2. Determine the outcome based on the reviewer's action
    if body.action == "override_approve":
        new_status = ReturnStatus.approved
        outcome = DecisionOutcome.approve
        explanation = "Human reviewer overrode the AI denial. Return approved."
    else:
        new_status = ReturnStatus.denied
        outcome = DecisionOutcome.deny
        explanation = "Human reviewer confirmed the AI denial. Return denied."

    # 3. Update the return status
    ret.status = new_status
    await db.commit()

    # 4. Update existing Decision or create a new one (worker may have already created one)
    existing_decision = await db.execute(
        select(Decision).where(Decision.return_id == return_id)
    )
    decision = existing_decision.scalar_one_or_none()

    if decision:
        decision.outcome = outcome
        decision.explanation = explanation
        decision.human_override = True
        decision.prev_hash = await get_prev_hash(db)
    else:
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

    # 5. Push live update to the reviewer's dashboard via WebSocket
    await broadcast_update(str(return_id), new_status.value)

    return {"status": "ok", "decision": new_status.value}

