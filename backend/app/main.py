# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routers import health, returns

from app.routers import health, returns, orders  




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="ReturnGuard API", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(returns.router, prefix="/api")

app.include_router(orders.router, prefix="/api")  