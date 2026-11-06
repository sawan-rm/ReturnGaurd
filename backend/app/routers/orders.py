from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Order
from app.schemas import OrderRead
from app.auth import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/", response_model=list[OrderRead])
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    scope: str = "own",
):
    """
    scope=own → only orders belonging to the logged-in user (default)
    scope=all → all orders in the system (for demo / admin use)
    """
    if scope == "all":
        result = await db.execute(
            select(Order).order_by(Order.ordered_at.desc())
        )
    else:
        user_id = UUID(current_user["sub"])
        result = await db.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.ordered_at.desc())
        )
    return result.scalars().all()
