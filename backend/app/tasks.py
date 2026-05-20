import asyncio
import os
import logging
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.celery_app import celery_app
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.gemini_service import gemini_analyze_match
from app.services.job_application_service import _resume_data_from_application

load_dotenv()
logger = logging.getLogger(__name__)

DB_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:passwordnamin@localhost/automated_resume_db")
engine = create_async_engine(DB_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def async_analyze_application(application_id: int):
    async with async_session() as db:
        result = await db.execute(select(JobApplication).filter(JobApplication.id == application_id))
        app = result.scalars().first()
        if not app:
            logger.error(f"Application {application_id} not found.")
            return
            
        job_result = await db.execute(select(JobDescription).filter(JobDescription.job_id == app.job_id))
        job = job_result.scalars().first()
        
        # Fallback if app.job_id is numeric (foreign key id)
        if not job:
            try:
                numeric_id = int(app.job_id)
                job_result = await db.execute(select(JobDescription).filter(JobDescription.id == numeric_id))
                job = job_result.scalars().first()
            except ValueError:
                pass
                
        if not job:
            logger.error(f"Job not found for application {application_id}.")
            return

        resume_data = _resume_data_from_application(app)
        job_data = {
            "job_title": job.job_title,
            "department": getattr(job, "department", ""),
            "description": job.description or "",
            "skills_requirements": job.skills_requirements or "",
            "experience_requirements": getattr(job, "experience_requirements", ""),
            "education_requirements": getattr(job, "education_requirements", ""),
        }
        
        logger.info(f"Starting Gemini analysis for application {application_id}...")
        ai_result = gemini_analyze_match(resume_data, job_data)
        
        if ai_result:
            app.match_score = ai_result.get("ai_match_score")
            app.skills_score = ai_result.get("ai_skills_score")
            app.experience_score = ai_result.get("ai_experience_score")
            app.education_score = ai_result.get("ai_education_score")
            app.matched_skills = ai_result.get("matched_skills")
            app.missing_skills = ai_result.get("missing_skills")
            app.recommendations = ai_result.get("recommendations")
            app.ai_summary = ai_result.get("ai_summary")
            app.strengths = ai_result.get("strengths")
            app.weaknesses = ai_result.get("weaknesses")
            app.ai_powered = True
            
            await db.commit()
            logger.info(f"Successfully saved AI analysis for application {application_id}.")
            
            # Optionally clear cache
            from app.utils.cache import delete_cache
            try:
                # Remove loop wrapper for cache deleting since delete_cache uses aioredis
                await delete_cache("app_stats:*")
            except Exception as e:
                logger.warning(f"Failed to clear cache: {e}")
        else:
            logger.warning(f"AI analysis returned empty for application {application_id}.")

@celery_app.task(name="analyze_application_task")
def analyze_application_task(application_id: int):
    """
    Celery task to run heavy AI analysis in the background.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # if somehow running in an existing loop
        loop.create_task(async_analyze_application(application_id))
    else:
        asyncio.run(async_analyze_application(application_id))
