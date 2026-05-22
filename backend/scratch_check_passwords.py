import asyncio
from app.utils.database import AsyncSessionLocal
from app.services.auth_service import login_user
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def test():
    async with AsyncSessionLocal() as db:
        emails_to_test = ['marvin@gmail.com', 'marvinfabricante630@gmail.com', 'tyron@gmail.com', 'cand1@example.com']
        for email in emails_to_test:
            try:
                res = await login_user(db, email, 'password')
                print(f"Login success for {email}")
            except Exception as e:
                print(f"Login failed for {email} with 'password': {e}")
            try:
                res = await login_user(db, email, 'password123')
                print(f"Login success for {email} with 'password123'")
            except Exception as e:
                print(f"Login failed for {email} with 'password123': {e}")

asyncio.run(test())
