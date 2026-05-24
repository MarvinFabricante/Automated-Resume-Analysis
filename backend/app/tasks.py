import asyncio
import os
import logging
import hashlib
import json
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

from app.celery_app import celery_app
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.services.ai_analysis_service import analyze_match_with_fallback
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
        
        from app.utils.cache import get_cache, set_cache
        
        # Compute a unique hash of the resume and job data
        hash_payload = json.dumps({"resume": resume_data, "job": job_data}, sort_keys=True).encode("utf-8")
        content_hash = hashlib.sha256(hash_payload).hexdigest()
        cache_key = f"ai_analysis:{content_hash}"
        
        cached_result = await get_cache(cache_key)
        
        if cached_result:
            logger.info(f"Found cached AI analysis for application {application_id}.")
            ai_result = cached_result
        else:
            logger.info(f"Starting AI analysis for application {application_id}...")
            ai_result = analyze_match_with_fallback(resume_data, job_data)
            
            if ai_result:
                # Store the result in Redis cache (e.g., 30 days TTL)
                await set_cache(cache_key, ai_result, ttl=2592000)
        
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
            
            # Trigger candidate comparison if multiple candidates are available
            from app.tasks import compare_candidates_task
            compare_candidates_task.delay(app.job_id)
            
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

async def async_compare_candidates(job_id: int):
    async with async_session() as db:
        try:
            job_result = await db.execute(select(JobDescription).filter(JobDescription.job_id == str(job_id)))
            job = job_result.scalars().first()
            if not job:
                try:
                    numeric_id = int(job_id)
                    job_result = await db.execute(select(JobDescription).filter(JobDescription.id == numeric_id))
                    job = job_result.scalars().first()
                except ValueError:
                    pass
            if not job:
                logger.error(f"Job not found for comparison task. Job ID: {job_id}")
                return

            all_apps_result = await db.execute(select(JobApplication).filter(JobApplication.job_id == str(job_id)))
            all_apps = all_apps_result.scalars().all()
            if len(all_apps) > 1:
                logger.info(f"Multiple candidates ({len(all_apps)}) found for job {job_id}. Running comparison analysis...")
                from app.services.ai_analysis_service import compare_candidates_with_fallback
                from app.utils.cache import set_cache
                
                job_data = {
                    "job_title": job.job_title,
                    "department": getattr(job, "department", ""),
                    "description": job.description or "",
                    "skills_requirements": job.skills_requirements or "",
                    "experience_requirements": getattr(job, "experience_requirements", ""),
                    "education_requirements": getattr(job, "education_requirements", ""),
                }
                candidates_data = [_resume_data_from_application(a) for a in all_apps]
                comparison_result = compare_candidates_with_fallback(job_data, candidates_data)
                
                if comparison_result:
                    comparison_cache_key = f"job_comparison:{job_id}"
                    await set_cache(comparison_cache_key, comparison_result, ttl=2592000)
                    logger.info(f"Successfully saved candidate comparison for job {job_id}.")
        except Exception as e:
            logger.error(f"Error during candidate comparison task for job {job_id}: {e}")

@celery_app.task(name="compare_candidates_task")
def compare_candidates_task(job_id: int):
    """
    Celery task to run candidate comparison in the background.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(async_compare_candidates(job_id))
    else:
        asyncio.run(async_compare_candidates(job_id))

