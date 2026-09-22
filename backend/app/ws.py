import asyncio
import json
from fastapi import WebSocket
from redis.asyncio import Redis
from app.config import settings

# Store all connected browsers
active_connections: list[WebSocket] = []

async def redis_listener():
    """Runs in background: listens to Redis and forwards to all WebSockets"""
    r = Redis.from_url(settings.redis_url)
    pubsub = r.pubsub()
    await pubsub.subscribe("return_updates")
    
    async for message in pubsub.listen():
        if message["type"] == "message":
            data = message["data"].decode("utf-8")
            # Send to all connected browsers
            for connection in active_connections:
                try:
                    await connection.send_text(data)
                except:
                    pass

async def broadcast_update(return_id: str, status: str, risk_score: float = None):
    """Called by the worker to announce a status change"""
    r = Redis.from_url(settings.redis_url)
    await r.publish("return_updates", json.dumps({
        "id": return_id, 
        "status": status,
        "risk_score": risk_score
    }))
