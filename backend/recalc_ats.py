"""
Recalculation script to backfill all existing job applications with the new
detailed ATS breakdown data (matched/missing skills, experience gaps,
education comparison, and optimization recommendations).

Uses the updated 40/40/20 scoring weights.
"""
import asyncio
import re
import os
import json
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select

load_dotenv()

DATABASE_URL = f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.job_matching_service import calculate_match_score


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(JobApplication).options(selectinload(JobApplication.job))
        )
        apps = result.scalars().all()
        
        updated = 0
        for app in apps:
            if not app.job:
                print(f"  ⚠ Skipping application {app.id} — no linked job")
                continue
            
            # Reconstruct resume_data from saved application fields
            resume_data = {
                "skills": ", ".join(app.skills) if app.skills else "",
                "years_experience": 0,
                "highest_degree": app.degree or "",
                "experience": app.relevance or ""
            }
            
            # Extract years from relevance text
            try:
                match = re.search(r'(\d+)', app.relevance or "")
                if match:
                    resume_data["years_experience"] = int(match.group(1))
            except Exception:
                pass
            
            scores = calculate_match_score(resume_data, app.job)
            
            # Update all scores (with new 40/40/20 weights)
            app.match_score = scores["match_percentage"]
            app.skills_score = scores["skills_score"]
            app.experience_score = scores["experience_score"]
            app.education_score = scores["education_score"]
            
            # Update reasons
            app.skills_reason = scores["skills_reason"]
            app.experience_reason = scores["experience_reason"]
            app.education_reason = scores["education_reason"]
            
            # Populate NEW detailed breakdown fields
            app.matched_skills = scores["matched_skills"]
            app.missing_skills = scores["missing_skills"]
            app.relevant_experience = scores["relevant_experience"]
            app.experience_gaps = scores["experience_gaps"]
            app.required_degree = scores["required_degree"]
            app.candidate_degree = scores["candidate_degree"]
            app.recommendations = scores["recommendations"]
            
            updated += 1
            print(f"  ✓ [{app.id}] {app.candidate_name}: {scores['match_percentage']}% match")
        
        await session.commit()
        print(f"\n✅ Updated {updated} applications with detailed ATS breakdown (40/40/20 weights).")


if __name__ == "__main__":
    asyncio.run(main())
