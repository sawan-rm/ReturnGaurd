from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ReturnRequest, Order
from app.schemas import ReturnCreate, ReturnRead, ReturnDetail
from app.auth import get_current_user

router = APIRouter(prefix="/returns", tags=["returns"])


@router.post("/", response_model=ReturnRead, status_code=201)
async def create_return(payload: ReturnCreate, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    # Check that the order exists
    order = await db.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    ret = ReturnRequest(order_id=payload.order_id, reason=payload.reason)
    db.add(ret)
    await db.commit()
    await db.refresh(ret)
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
