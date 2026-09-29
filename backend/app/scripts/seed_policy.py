import asyncio
from sentence_transformers import SentenceTransformer
from app.qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Sample corporate return policy
POLICY_DOCS = [
    "General electronics can be returned within 30 days of purchase if unopened.",
    "Laptops and computers have a strict 14-day return window and require a 15% restocking fee.",
    "Clothing and apparel can be returned within 90 days as long as the tags are still attached.",
    "Sale items and clearance items are final sale and cannot be returned or refunded.",
    "If an item arrives damaged, the customer must report it within 3 days to be eligible for a full refund without restocking fees."
]

async def seed():
    client = AsyncQdrantClient(url="http://localhost:6333")
    collection_name = "return_policy"
    
    # We use a fast, small, open-source embedding model that runs locally on CPU
    model = SentenceTransformer('all-MiniLM-L6-v2')

    print("Recreating collection...")
    if await client.collection_exists(collection_name):
        await client.delete_collection(collection_name)
        
    await client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

    print("Generating embeddings...")
    points = []
    for i, text in enumerate(POLICY_DOCS):
        vector = model.encode(text).tolist()
        points.append(
            PointStruct(id=i, vector=vector, payload={"text": text})
        )
        
    print("Uploading to Qdrant...")
    await client.upsert(collection_name=collection_name, points=points)
    print("✅ Policy seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
