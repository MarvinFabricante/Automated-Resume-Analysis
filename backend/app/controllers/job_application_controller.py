from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.utils.database import get_db
from app.schemas.job_application_schema import JobApplicationCreate, JobApplicationResponse, JobApplicationStatusUpdate
from app.services import job_application_service
from app.services.audit_service import record_activity
from app.utils.auth import get_current_user, get_optional_current_user
from app.utils.cache import cache_response, clear_cache_pattern


router = APIRouter(prefix="/applications", tags=["Job Applications"])

@router.post("/", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_job_application(application_in: JobApplicationCreate, db: AsyncSession = Depends(get_db)):
    """
    Submit a new job application.
    """
    # Verify job exists via service
    job = await job_application_service.get_and_validate_job(db, application_in.job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    res = await job_application_service.create_job_application(db, application_in, job.id)
    
    # Invalidate cache so HR immediately sees the new applicant
    from app.utils.cache import delete_cache
    await delete_cache("app_stats:{}")
    await delete_cache("resume_count:{}")
    await clear_cache_pattern("all_apps*")
    await clear_cache_pattern("job_apps*")
    await clear_cache_pattern("cand_apps*")
    
    return res

@router.get("/", response_model=List[JobApplicationResponse])
@cache_response("all_apps", ttl=60)
async def get_all_applications(db: AsyncSession = Depends(get_db)):
    """
    Get all job applications from all jobs.
    """
    return await job_application_service.get_all_applications(db)

@router.get("/job/{job_id}", response_model=List[JobApplicationResponse])
@cache_response("job_apps", ttl=60)
async def get_applications_for_job(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get all applications for a specific job.
    """
    return await job_application_service.get_applications_by_job(db, job_id)

@router.get("/job/{job_id}/compare")
async def get_candidate_comparison(job_id: int):
    """
    Get the AI candidate comparison summary for a specific job.
    """
    from app.utils.cache import get_cache
    comparison_cache_key = f"job_comparison:{job_id}"
    cached_result = await get_cache(comparison_cache_key)
    if not cached_result:
        raise HTTPException(status_code=404, detail="Comparison not found or still processing.")
    return cached_result

@router.get("/candidate/{email}", response_model=List[JobApplicationResponse])
@cache_response("cand_apps", ttl=60)
async def get_applications_for_candidate(email: str, db: AsyncSession = Depends(get_db)):
    """
    Get all applications for a specific candidate by email.
    """
    return await job_application_service.get_applications_by_email(db, email)

@router.patch("/{application_id}/status", response_model=JobApplicationResponse)
async def update_application_status(
    application_id: int, 
    status_update: JobApplicationStatusUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Update the status of a job application.
    """
    db_application = await job_application_service.update_application_status(
        db, application_id, status_update.status
    )
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    # Record in audit log
    user_id = current_user.get("id") if current_user else None
    await record_activity(
        db=db,
        user_id=user_id,
        action="UPDATE_STATUS",
        target=f"Application ID: {application_id}",
        details=f"HR updated application status for {db_application.candidate_name} to {status_update.status}"
    )
        
    # Invalidate cache since stats might change
    from app.utils.cache import delete_cache
    await delete_cache("app_stats:{}")
    await clear_cache_pattern("all_apps*")
    await clear_cache_pattern("job_apps*")
    await clear_cache_pattern("cand_apps*")

    # Record Human-in-the-Loop recruiter feedback in ML feedback database
    try:
        from app.ml_engine import get_feedback_db, get_production_model
        fb_db = get_feedback_db()
        st_upper = status_update.status.upper()
        action = None
        if st_upper in ("ACCEPTED", "SHORTLISTED", "HIRED", "INTERVIEWED"):
            action = 1
        elif st_upper in ("REJECTED", "PASSED_OVER"):
            action = 0

        if action is not None:
            # 1. Resolve job code and all possible identifiers for the job
            job_code = None
            try:
                app_dict = getattr(db_application, "__dict__", {})
                if "job" in app_dict and app_dict["job"] and getattr(app_dict["job"], "job_id", None):
                    job_code = str(app_dict["job"].job_id)
            except Exception:
                pass

            if not job_code:
                from app.repositories.job_description_repository import JobDescriptionRepository
                try:
                    job_desc = await JobDescriptionRepository.get_by_id(db, db_application.job_id)
                    if job_desc and getattr(job_desc, "job_id", None):
                        job_code = str(job_desc.job_id)
                except Exception:
                    pass

            job_identifiers = [str(db_application.job_id)]
            if job_code and job_code not in job_identifiers:
                job_identifiers.append(job_code)

            # 2. Resolve all candidate identifiers (email, id, name)
            candidate_identifiers = [str(db_application.id)]
            if db_application.candidate_email:
                candidate_identifiers.append(db_application.candidate_email)
            if db_application.candidate_name:
                candidate_identifiers.append(db_application.candidate_name)

            updated = fb_db.record_recruiter_feedback(
                candidate_email=db_application.candidate_email,
                candidate_name=db_application.candidate_name,
                resume_id=str(db_application.id),
                job_id=job_code or str(db_application.job_id),
                job_code=job_code,
                job_identifiers=job_identifiers,
                candidate_identifiers=candidate_identifiers,
                recruiter_action=action,
            )

            # 3. Fallback: If no live prediction was previously logged for this candidate,
            # synthesize the evaluation record from application data so the decision is not lost
            if not updated:
                job_desc = None
                try:
                    app_dict = getattr(db_application, "__dict__", {})
                    if "job" in app_dict:
                        job_desc = app_dict["job"]
                except Exception:
                    pass
                if not job_desc:
                    from app.repositories.job_description_repository import JobDescriptionRepository
                    try:
                        job_desc = await JobDescriptionRepository.get_by_id(db, db_application.job_id)
                    except Exception:
                        pass

                prod_model = get_production_model()
                cand_skills = db_application.skills or []
                job_skills = job_desc.skills_requirements if job_desc else ""
                cand_title = db_application.job_title or "applicant"
                job_title_req = job_desc.job_title if job_desc else ""
                cand_years = (db_application.total_experience_months or 0) / 12.0
                cand_edu = db_application.degree or db_application.highest_educational_attainment or ""
                req_edu = getattr(job_desc, "education_requirements", "") if job_desc else ""

                eval_result = prod_model.predict(
                    candidate_skills=cand_skills,
                    job_skills=job_skills,
                    candidate_title=cand_title,
                    job_title=job_title_req,
                    candidate_years=cand_years,
                    required_years=0.0,
                    candidate_edu=cand_edu,
                    required_edu=req_edu,
                )

                new_eval_id = fb_db.log_live_prediction(
                    resume_id=str(db_application.id),
                    job_id=str(job_code or db_application.job_id),
                    resume_skills=cand_skills,
                    job_skills=job_skills,
                    resume_titles=cand_title,
                    job_titles=job_title_req,
                    candidate_years=cand_years,
                    required_years=0.0,
                    candidate_edu=cand_edu,
                    required_edu=req_edu,
                    feature_vector=eval_result["feature_vector"],
                    predicted_fit_score=eval_result["fit_probability"],
                    candidate_email=db_application.candidate_email,
                    candidate_name=db_application.candidate_name,
                    job_code=job_code,
                )
                fb_db.record_recruiter_feedback(evaluation_id=new_eval_id, recruiter_action=action)

            # 4. Check if threshold for automated continuous retraining is reached
            try:
                import os
                stats = fb_db.get_evaluation_stats()
                unassimilated = stats.get("unassimilated_verified", 0)
                auto_threshold = int(os.getenv("ML_AUTO_RETRAIN_THRESHOLD", "5"))

                if unassimilated >= auto_threshold:
                    from app.tasks import retrain_ml_model_task
                    try:
                        retrain_ml_model_task.delay(min_new_samples=auto_threshold, force=False)
                        import logging
                        logging.getLogger(__name__).info(
                            f"[HITL] Auto-enqueued Celery ML retraining task: {unassimilated} verified samples >= threshold {auto_threshold}"
                        )
                    except Exception as celery_err:
                        import threading
                        from app.ml_engine import retrain_production_model
                        threading.Thread(
                            target=retrain_production_model,
                            kwargs={"min_new_samples": auto_threshold, "force": False},
                            daemon=True
                        ).start()
                        import logging
                        logging.getLogger(__name__).info(
                            f"[HITL] Celery worker unavailable ({celery_err}). Dispatched background thread for continuous retraining."
                        )
            except Exception as auto_train_err:
                import logging
                logging.getLogger(__name__).debug(f"Notice on auto-retraining check: {auto_train_err}")
    except Exception as ml_fb_err:
        import logging
        logging.getLogger(__name__).debug(f"Notice on recording HITL feedback: {ml_fb_err}")
    
    return db_application

@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Remove/delete a job application.
    """
    db_application = await job_application_service.delete_application(db, application_id)
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Record in audit log
    user_id = current_user.get("id") if current_user else None
    await record_activity(
        db=db,
        user_id=user_id,
        action="DELETE_APPLICATION",
        target=f"Application ID: {application_id}",
        details=f"HR deleted application for {db_application.candidate_name}"
    )
    
    # Invalidate cache since stats might change
    from app.utils.cache import delete_cache
    await delete_cache("app_stats:{}")
    await clear_cache_pattern("all_apps*")
    await clear_cache_pattern("job_apps*")
    await clear_cache_pattern("cand_apps*")
    
    return None


