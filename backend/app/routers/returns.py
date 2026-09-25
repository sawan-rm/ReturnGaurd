from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import ReturnRequest, Order
from app.schemas import ReturnRead, ReturnDetail
from app.minio_client import get_minio_client
from app.auth import get_current_user

from arq import create_pool
from arq.connections import RedisSettings
from app.config import settings

router = APIRouter(prefix="/returns", tags=["returns"])


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
