from qdrant_client import AsyncQdrantClient
from app.config import settings

qdrant = AsyncQdrantClient(url=settings.qdrant_url)
COLLECTION_NAME = "return_policy"
