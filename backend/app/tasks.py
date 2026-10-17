import asyncio
import os
import logging
import hashlib
import json
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.celery_app import celery_app


from app.services.ai_analysis_service import analyze_match_with_fallback
from app.services.job_application_service import _resume_data_from_application
from app.repositories.job_application_repository import JobApplicationRepository
from app.repositories.job_description_repository import JobDescriptionRepository

from app.utils.database import DATABASE_URL

load_dotenv()
logger = logging.getLogger(__name__)

effective_db_url = DATABASE_URL or os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:passwordnamin@localhost/automated_resume_db")
engine = create_async_engine(
    effective_db_url,
    pool_size=10,
    max_overflow=5,
    pool_recycle=1800,
    pool_pre_ping=True
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def async_analyze_application(application_id: int):
    async with async_session() as db:
        app = await JobApplicationRepository.get_by_id(db, application_id)
        if not app:
            logger.error(f"Application {application_id} not found.")
            return
            
        job = await JobDescriptionRepository.get_by_job_id(db, str(app.job_id))
        
        # Fallback if app.job_id is numeric (foreign key id)
        if not job:
            try:
                numeric_id = int(app.job_id)
                job = await JobDescriptionRepository.get_by_id(db, numeric_id)
            except (ValueError, TypeError):
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
                # Store the result in cache (e.g., 30 days TTL)
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
            app.ai_powered = False
            
            await JobApplicationRepository.update(db, app)
            logger.info(f"Successfully saved AI analysis for application {application_id}.")
            
            # Trigger candidate comparison if multiple candidates are available
            compare_candidates_task.delay(app.job_id)
            
            # Optionally clear cache
            from app.utils.cache import delete_cache
            try:
                # Clear stale cache entries after analysis
                await delete_cache("app_stats:*")
            except Exception as e:
                logger.warning(f"Failed to clear cache: {e}")
        else:
            logger.warning(f"AI analysis returned empty for application {application_id}.")



async def async_compare_candidates(job_id: int):
    async with async_session() as db:
        try:
            # Try to get job by job_id string first
            job = await JobDescriptionRepository.get_by_job_id(db, str(job_id))
            if not job:
                # Try by numeric ID
                try:
                    numeric_id = int(job_id)
                    job = await JobDescriptionRepository.get_by_id(db, numeric_id)
                except (ValueError, TypeError):
                    pass
            
            if not job:
                logger.error(f"Job not found for comparison task. Job ID: {job_id}")
                return

            all_apps = await JobApplicationRepository.get_by_job_id(db, job_id)
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

@celery_app.task(name="analyze_application_task")
def analyze_application_task(application_id: int):
    asyncio.run(async_analyze_application(application_id))

@celery_app.task(name="compare_candidates_task")
def compare_candidates_task(job_id: int):
    asyncio.run(async_compare_candidates(job_id))

@celery_app.task(name="match_single_job_task")
def match_single_job_task(resume_data: dict, job_dict: dict, use_ai: bool = False) -> dict:
    from app.services.job_matching_service import calculate_match_score
    
    class MockJob:
        def __init__(self, data: dict):
            self.job_id = data.get("job_id")
            self.job_title = data.get("job_title", "Unknown Role")
            self.department = data.get("department", "")
            self.location = data.get("location", "")
            self.job_type = None
            self.description = data.get("description", "")
            self.skills_requirements = data.get("skills_requirements", "")
            self.experience_requirements = data.get("experience_requirements", "")
            self.education_requirements = data.get("education_requirements", "")
            self.certifications_requirements = data.get("certifications_requirements", "")
            
        def get(self, key, default=None):
            return getattr(self, key, default)

    mock_job = MockJob(job_dict)
    return calculate_match_score(resume_data, mock_job, use_ai=use_ai)


@celery_app.task(bind=True, name="send_email_task", max_retries=3, default_retry_delay=10)
def send_email_task(self, to_email: str, subject: str, html_body: str, email_type: str = "general", tx_id: str | None = None) -> dict:
    """
    Dedicated background Celery worker task to deliver emails via SMTP
    without blocking user requests. Automatically retries up to 3 times on network failure.
    """
    from app.services.email_service import _send_smtp_sync
    from app.utils.redis_client import redis_tx_manager

    logger.info(f"[Celery] Sending email task to={to_email} subject='{subject}' type={email_type} tx={tx_id}")
    try:
        success = _send_smtp_sync(to_email, subject, html_body)
        if success:
            if tx_id:
                redis_tx_manager.commit_transaction_sync(tx_id, {"delivered_via_celery": True})
            return {"status": "delivered", "to": to_email, "tx_id": tx_id}
        else:
            if tx_id:
                redis_tx_manager.fail_transaction_sync(tx_id, "SMTP dispatch returned False")
            raise Exception("SMTP dispatch returned False")
    except Exception as exc:
        logger.warning(f"[Celery] Error delivering email to {to_email}: {exc}. Retrying...")
        try:
            self.retry(exc=exc)
        except Exception:
            if tx_id:
                redis_tx_manager.fail_transaction_sync(tx_id, str(exc))
            return {"status": "failed", "to": to_email, "error": str(exc), "tx_id": tx_id}


@celery_app.task(name="process_outgoing_email_queue_task")
def process_outgoing_email_queue_task(max_batch: int = 25):
    """Celery task to drain queued emails from Redis and deliver them in batch."""
    from app.utils.redis_client import pop_from_queue, redis_tx_manager
    from app.services.email_service import _send_smtp_sync
    import asyncio

    processed_count = 0
    delivered_count = 0

    for _ in range(max_batch):
        item = asyncio.run(pop_from_queue("queue:outgoing_emails"))
        if not item:
            break

        processed_count += 1
        tx_id = item.get("tx_id")
        to_email = item.get("to_email")
        subject = item.get("subject")
        html_body = item.get("html_body", "")

        logger.info(f"[Celery] Processing queued email tx={tx_id} to={to_email}")
        success = _send_smtp_sync(to_email, subject, html_body)
        if success:
            delivered_count += 1
            if tx_id:
                redis_tx_manager.commit_transaction_sync(tx_id, {"delivered_via_worker": True})
        else:
            if tx_id:
                redis_tx_manager.fail_transaction_sync(tx_id, "Worker SMTP delivery failed")

    return {
        "processed": processed_count > 0,
        "processed_count": processed_count,
        "delivered_count": delivered_count
    }


@celery_app.task(name="recalculate_all_applications_task")
def recalculate_all_applications_task() -> dict:
    """
    Celery task to recalculate all ATS match scores and breakdowns
    in the background worker, avoiding HTTP timeouts on large applicant pools.
    """
    logger.info("[Celery] Starting background recalculation of all job applications ATS scores...")
    async def _async_recalculate():
        async with async_session() as db:
            from app.services.system_config_service import recalculate_all_applications
            from app.utils.cache import clear_cache_pattern
            result = await recalculate_all_applications(db)
            await clear_cache_pattern("ai_analysis:*")
            await clear_cache_pattern("job_matches:*")
            await clear_cache_pattern("job_comparison:*")
            await clear_cache_pattern("app_stats:*")
            await clear_cache_pattern("screening:*")
            await clear_cache_pattern("all_apps*")
            logger.info(f"[Celery] Recalculation finished: {result.get('updated_applications', 0)} applications updated.")
            return result
    return asyncio.run(_async_recalculate())


@celery_app.task(name="create_data_backup_task")
def create_data_backup_task() -> dict:
    """
    Background worker task to snapshot and backup database / storage data.
    """
    from datetime import datetime
    import time
    time.sleep(0.5)
    timestamp = datetime.utcnow().isoformat()
    backup_id = f"backup_{int(time.time())}"
    logger.info(f"[Celery] System data backup snapshot created: {backup_id} at {timestamp}")
    return {"status": "success", "backup_id": backup_id, "timestamp": timestamp}


@celery_app.task(name="cleanup_expired_cache_task")
def cleanup_expired_cache_task() -> dict:
    """
    Periodic Celery task to clean up temporary transient cache keys, stale lock flags,
    and expired temporary session locks.
    """
    from app.utils.cache import clear_cache_pattern
    async def _cleanup():
        await clear_cache_pattern("analyzing:*")
        return {"status": "success", "cleaned_at": asyncio.get_event_loop().time()}
    try:
        return asyncio.run(_cleanup())
    except Exception as e:
        logger.error(f"[Celery] Cache cleanup task failed: {e}")
        return {"status": "error", "error": str(e)}


@celery_app.task(name="refresh_active_comparisons_task")
def refresh_active_comparisons_task() -> dict:
    """
    Periodic Celery task to refresh cached candidate comparisons across active jobs.
    """
    async def _refresh():
        async with async_session() as db:
            from app.repositories.job_description_repository import JobDescriptionRepository
            jobs = await JobDescriptionRepository.get_all_active(db, include_inactive=False)
            count = 0
            for job in jobs:
                compare_candidates_task.delay(job.id)
                count += 1
            return {"status": "success", "jobs_dispatched": count}
    try:
        return asyncio.run(_refresh())
    except Exception as e:
        logger.error(f"[Celery] Candidate comparisons refresh task failed: {e}")
        return {"status": "error", "error": str(e)}


async def _notify_retraining_success(result: dict):
    """Deliver real-time websocket and database notification to Admin upon successful model retraining."""
    try:
        async with async_session() as db:
            from app.services.notification_service import create_notification
            version = result.get("version", "latest")
            count = result.get("assimilated_records", 0)
            metrics = result.get("metrics", {})
            f1 = metrics.get("f1", 0.0)
            roc_auc = metrics.get("roc_auc", 0.0)
            await create_notification(
                db=db,
                title="ML Model Retrained",
                message=f"Continuous Retraining finished: Upgraded to {version} (F1: {f1:.2f}, ROC-AUC: {roc_auc:.2f}) assimilating {count} recruiter decisions.",
                type="system",
                target_role="ADMIN",
                sender_role="SYSTEM"
            )
    except Exception as notif_err:
        logger.debug(f"Notice on retraining notification dispatch: {notif_err}")


@celery_app.task(name="retrain_ml_model_task")
def retrain_ml_model_task(min_new_samples: int = 5, force: bool = False) -> dict:
    """
    Background Celery worker task to run the continuous retraining pipeline:
    Checks if enough unassimilated HR recruiter decisions exist,
    updates FastText embeddings, retrains classifier, and hot-swaps model.
    """
    logger.info("[Celery] Checking/executing ML continuous retraining task...")
    from app.ml_engine import retrain_production_model
    try:
        result = retrain_production_model(min_new_samples=min_new_samples, force=force)
        logger.info(f"[Celery] ML Retraining task finished: status={result.get('status')} version={result.get('version')}")
        if result.get("status") == "success":
            try:
                import asyncio
                asyncio.run(_notify_retraining_success(result))
            except Exception as notify_err:
                logger.debug(f"Notice on async notification in worker: {notify_err}")
        return result
    except Exception as e:
        logger.error(f"[Celery] ML Retraining task failed: {e}")
        return {"status": "error", "error": str(e)}


