import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from app.database import engine
from app.models import Base
from app.routers import health, returns, orders
from app.ws import redis_listener, active_connections # <-- NEW

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start Redis pub/sub listener in background
    task = asyncio.create_task(redis_listener())
    yield
    task.cancel()

app = FastAPI(title="ReturnGuard API", version="0.1.0", lifespan=lifespan)

# <-- NEW WEBSOCKET ROUTE
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
