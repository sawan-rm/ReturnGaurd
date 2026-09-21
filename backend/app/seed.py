"""Run with: python -m app.seed"""
import asyncio
import random
from faker import Faker
from app.database import engine, async_session
from app.models import Base, User, Order, Role

fake = Faker()

CATEGORIES = ["Electronics", "Clothing", "Home & Kitchen", "Books", "Toys"]
PRODUCTS = {
    "Electronics": ["Wireless Earbuds", "Phone Case", "USB-C Cable", "Webcam", "Power Bank"],
    "Clothing": ["T-Shirt", "Sneakers", "Hoodie", "Jeans", "Jacket"],
    "Home & Kitchen": ["Coffee Mug", "Cutting Board", "Blender", "Towel Set", "Lamp"],
    "Books": ["Python Cookbook", "Design Patterns", "Clean Code", "AI Handbook", "The Pragmatic Programmer"],
    "Toys": ["LEGO Set", "Puzzle", "Board Game", "Action Figure", "Stuffed Animal"],
}


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Create 10 customers, 2 reviewers, 1 admin
        users = []
        for i in range(10):
            users.append(User(email=fake.unique.email(), name=fake.name(), role=Role.customer))
        users.append(User(email="reviewer1@returnguard.local", name="Alice Reviewer", role=Role.reviewer))
        users.append(User(email="reviewer2@returnguard.local", name="Bob Reviewer", role=Role.reviewer))
        users.append(User(email="admin@returnguard.local", name="Admin User", role=Role.admin))
        session.add_all(users)
        await session.flush()

        # Create 3-5 orders per customer
        customers = [u for u in users if u.role == Role.customer]
        for customer in customers:
            for _ in range(random.randint(3, 5)):
                cat = random.choice(CATEGORIES)
                product = random.choice(PRODUCTS[cat])
                order = Order(
                    user_id=customer.id,
                    product_name=product,
                    product_category=cat,
                    amount=round(random.uniform(9.99, 299.99), 2),
                )
                session.add(order)

        await session.commit()
        print(f"✅ Seeded {len(users)} users and their orders.")


if __name__ == "__main__":
    asyncio.run(seed())
