import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.job_matching_service import calculate_match_score
import json

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(JobApplication).options(selectinload(JobApplication.job)))
        apps = result.scalars().all()
        for app in apps:
            if app.job:
                resume_data = {
                    "skills": ", ".join(app.skills) if app.skills else "",
                    "years_experience": 0, # calculate_match_score uses experience text via job desc if years = 0
                    "highest_degree": app.degree or ""
                }
                
                # To get years of experience, let's use the relevance string
                import re
                try:
                    match = re.search(r'(\d+)', app.relevance or "")
                    if match:
                        resume_data["years_experience"] = int(match.group(1))
                except Exception:
                    pass
                
                scores = calculate_match_score(resume_data, app.job)
                
                app.skills_score = scores["skills_score"]
                app.experience_score = scores["experience_score"]
                app.education_score = scores["education_score"]
                
                # also update reasons
                app.skills_reason = scores["skills_reason"]
                app.experience_reason = scores["experience_reason"]
                app.education_reason = scores["education_reason"]
                
                app.match_score = scores["match_percentage"]
                
        await session.commit()
        print(f"Updated {len(apps)} applications with detailed scores.")

if __name__ == "__main__":
    asyncio.run(main())
