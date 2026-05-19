import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.models.job_application import JobApplication

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(JobApplication))
        apps = result.scalars().all()
        for app in apps:
            if app.skills_score is not None and app.experience_score is not None and app.education_score is not None:
                new_score = round(
                    (app.skills_score * 0.35) + 
                    (app.experience_score * 0.50) + 
                    (app.education_score * 0.15), 1
                )
                app.match_score = min(new_score, 100.0)
        await session.commit()
        print(f"Updated {len(apps)} applications.")

if __name__ == "__main__":
    asyncio.run(main())
