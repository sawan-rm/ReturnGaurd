import asyncio
import hashlib
import math
import os
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Vector size we will use
VECTOR_SIZE = 768

# Sample corporate return policy
POLICY_DOCS = [
    "General electronics can be returned within 30 days of purchase if unopened.",
    "Laptops and computers have a strict 14-day return window and require a 15% restocking fee.",
    "Clothing and apparel can be returned within 90 days as long as the tags are still attached.",
    "Sale items and clearance items are final sale and cannot be returned or refunded.",
    "If an item arrives damaged, the customer must report it within 3 days to be eligible for a full refund without restocking fees."
]

def simple_embed(text: str, size: int = VECTOR_SIZE) -> list[float]:
    """
    Deterministic hash-based embedding. 
    Same text always produces the same vector (cosine similarity will still work for exact/near-exact matches).
    No external API or library required.
    """
    vector = []
    for i in range(size):
        h = hashlib.sha256(f"{text}_{i}".encode()).digest()
        # Map 2 bytes to a float in [-1, 1]
        val = int.from_bytes(h[:2], "big") / 32767.5 - 1.0
        vector.append(val)
    # L2-normalize so cosine similarity works correctly
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector]


async def seed():
    qdrant_url = os.environ.get("QDRANT_URL", "http://qdrant:6333")
    client = AsyncQdrantClient(url=qdrant_url)
    collection_name = "return_policy"

    print("Recreating collection...")
    if await client.collection_exists(collection_name):
        await client.delete_collection(collection_name)
        
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    print("Generating embeddings...")
    points = []
    for i, text in enumerate(POLICY_DOCS):
        vector = simple_embed(text)
        points.append(
            PointStruct(id=i, vector=vector, payload={"text": text})
        )
        print(f"  [{i+1}/{len(POLICY_DOCS)}] Embedded: {text[:60]}...")
        
    print("Uploading to Qdrant...")
    await client.upsert(collection_name=collection_name, points=points)
    print(f"✅ Policy seeded successfully! {len(points)} documents uploaded.")

if __name__ == "__main__":
    asyncio.run(seed())
