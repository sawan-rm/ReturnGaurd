import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models import Base
from app.minio_client import ensure_bucket_exists
from app.routers import health, returns, orders
from app.ws import redis_listener, active_connections


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        ensure_bucket_exists()
    except Exception as e:
        print(f"⚠️ MinIO setup failed: {e}")
    task = asyncio.create_task(redis_listener())
    yield
    task.cancel()


app = FastAPI(title="ReturnGuard API", version="0.1.0", lifespan=lifespan)

# ── CORS ─────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket ─────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        active_connections.remove(websocket)

app.include_router(health.router)
app.include_router(returns.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
