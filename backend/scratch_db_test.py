import asyncio
from app.utils.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy.future import select

async def test():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"ID: {u.id}, Email: {u.email}, Hash: {u.password[:20]}..., Role: {u.role}")

asyncio.run(test())
