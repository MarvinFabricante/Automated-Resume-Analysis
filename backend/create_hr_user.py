import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import AsyncSessionLocal
from app.services.auth_service import auth_service
from app.repositories.auth_repository import AuthRepository

async def create_hr_user():
    async with AsyncSessionLocal() as db:
        email = "marvinfabricante630@gmail.com"
        password = "password"
        
        # Check if exists
        existing = await AuthRepository.get_raw_user_by_email(db, email)
        if existing:
            print(f"User {email} already exists with role {existing.role}")
        else:
            await auth_service.register_user(db, email, password, "HR", "Marvin Fabricante")
            print(f"Successfully created HR user {email}")

if __name__ == "__main__":
    asyncio.run(create_hr_user())
