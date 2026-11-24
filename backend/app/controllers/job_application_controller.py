from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.utils.database import get_db
from app.schemas.job_application_schema import (
    JobApplicationCreate, 
    JobApplicationResponse, 
    JobApplicationStatusUpdate,
    JobApplicationNotesUpdate,
    JobApplicationViewedEvent,
    StatusHistoryResponse,
    ApplicationWithdrawRequest,
    PostPassActionRequest,
    ApplicationResumeRequest,
    HiredElsewhereWithdrawRequest,
)
from app.services import job_application_service
from app.services.status_management_service import (
    handle_application_viewed_event,
    get_application_history,
    undo_auto_status_change
)
from app.services.audit_service import record_activity
from app.utils.auth import get_current_user, get_optional_current_user
from app.utils.cache import cache_response, invalidate_application_dashboard_caches


router = APIRouter(prefix="/applications", tags=["Job Applications"], redirect_slashes=False)

@router.post("", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_job_application(
    application_in: JobApplicationCreate, 
    duplicate_policy: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Submit a new job application.
    Supports duplicate handling policy ('block' or 'version').
    Links the application to the authenticated candidate's user_id when logged in.
    """
    # Verify job exists and is open for applications
    job = await job_application_service.get_and_validate_job(db, application_in.job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_status = (getattr(job, "status", None) or ("ACTIVE" if getattr(job, "is_active", True) else "ARCHIVED")).strip().upper()
    if job_status == "CLOSED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This position is closed",
        )
    if job_status == "ARCHIVED" or getattr(job, "is_active", True) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This position is archived and is no longer accepting applications.",
        )
    if job_status == "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This position is not yet open for applications.",
        )
        
    res = await job_application_service.create_job_application(
        db,
        application_in,
        job.id,
        duplicate_policy=duplicate_policy,
        current_user=current_user,
    )
    
    # Invalidate cache so HR immediately sees the new applicant and updated counts
    await invalidate_application_dashboard_caches(res.id if res else None)
    
    return res


@router.get("/check-duplicate")
async def check_duplicate_application(
    job_id: int, 
    email: Optional[str] = None,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Check if a candidate has already applied for a specific job (REQ: Limit / TC-RES-016).
    Uses authenticated user_id first when available.
    """
    effective_user_id = user_id
    if effective_user_id is None and current_user and (current_user.get("role") or "CANDIDATE").upper() == "CANDIDATE":
        effective_user_id = current_user.get("id")
    existing = await job_application_service.check_duplicate(
        db, job_id, email or "", user_id=effective_user_id
    )
    return {
        "is_duplicate": existing is not None,
        "existing_application_id": existing.id if existing else None,
        "status": existing.status if existing else None,
        "applied_at": existing.created_at.isoformat() if existing and existing.created_at else None,
    }


@router.get("", responses={200: {"model": List[JobApplicationResponse]}})
@router.get("/", responses={200: {"model": List[JobApplicationResponse]}})
@cache_response("all_apps", ttl=60)
async def get_all_applications(
    position: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: int = 0,
    summary: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all job applications from all jobs, optionally filtered by position, sorted, paginated,
    or projected as lightweight dashboard summaries (`summary=true`).
    """
    if summary:
        return await job_application_service.get_all_applications_summary(
            db, position=position, sort_by=sort_by, limit=limit, offset=offset
        )
    apps = await job_application_service.get_all_applications(
        db, position=position, sort_by=sort_by, limit=limit, offset=offset
    )
    return [JobApplicationResponse.model_validate(app).model_dump(mode="json") for app in apps]

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

@router.get("/my", response_model=List[JobApplicationResponse])
async def get_my_applications(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Get all applications for the currently authenticated candidate by user_id.
    """
    uid = current_user.get("id")
    u_email = current_user.get("sub") or current_user.get("email")
    return await job_application_service.get_applications_for_user(
        db, user_id=uid, fallback_email=u_email
    )


@router.get("/candidate/{email}", response_model=List[JobApplicationResponse])
async def get_applications_for_candidate(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """
    Get all applications for a candidate.
    Prioritizes authenticated user_id (or numeric user_id parameter) so applications
    are linked to the logged-in user account even if the resume email differs.
    """
    raw_param = (email or "").strip()
    if current_user and (current_user.get("role") or "CANDIDATE").upper() == "CANDIDATE":
        auth_uid = current_user.get("id")
        auth_email = (current_user.get("sub") or current_user.get("email") or "").strip().lower()
        if auth_uid and (
            raw_param in ("me", "my", str(auth_uid))
            or raw_param.lower() == auth_email
        ):
            return await job_application_service.get_applications_for_user(
                db, user_id=auth_uid, fallback_email=auth_email
            )

    if raw_param.isdigit():
        return await job_application_service.get_applications_for_user(
            db, user_id=int(raw_param)
        )

    return await job_application_service.get_applications_by_email(db, email)


@router.get("/{application_id}", response_model=JobApplicationResponse)
async def get_application_by_id(application_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get full detailed evaluation and profile data for a single job application.
    """
    app = await job_application_service.get_application_by_id(db, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app

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
        db,
        application_id,
        status_update.status,
        notes=status_update.notes,
        custom_email_subject=status_update.custom_email_subject,
        custom_email_message=status_update.custom_email_message,
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
        
    # Invalidate cache since stats and lists changed
    await invalidate_application_dashboard_caches(application_id)

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
    Hard-deleting job applications is prohibited by recruitment audit & privacy policy.
    """
    user_id = current_user.get("id") if current_user else None
    if user_id:
        await record_activity(
            db=db,
            user_id=user_id,
            action="DELETE_APPLICATION_BLOCKED",
            target=f"Application ID: {application_id}",
            details="Blocked attempt to hard-delete job application record.",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Applications cannot be hard-deleted. Use status transitions, applicant withdrawal, or the retention anonymization policy.",
    )


@router.patch("/{application_id}/notes", response_model=JobApplicationResponse)
async def update_application_notes(
    application_id: int,
    notes_update: JobApplicationNotesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Update HR shortlisting notes for an application (REQ056).
    """
    db_application = await job_application_service.update_application_notes(
        db, application_id, notes_update.hr_shortlist_notes
    )
    if not db_application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    await invalidate_application_dashboard_caches(application_id)
    return db_application


@router.post("/{application_id}/viewed")
async def record_application_viewed(
    application_id: int,
    view_event: JobApplicationViewedEvent,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Automatic Status Update (Item 1a):
    Triggers Submitted -> Under Review ONLY if HR really opened full view, tab was focused,
    stayed open >= 8 seconds, and engagement was detected.
    """
    user_email = (current_user.get("email") if current_user else None) or "HR"
    result = await handle_application_viewed_event(
        db=db,
        application_id=application_id,
        view_duration_seconds=view_event.view_duration_seconds,
        visible_focused=view_event.visible_focused,
        engaged=view_event.engaged,
        user_email=user_email
    )
    if result.get("changed"):
        await invalidate_application_dashboard_caches(application_id)
    return result


@router.get("/{application_id}/history", response_model=List[StatusHistoryResponse])
async def get_status_history(
    application_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns audit trail history of all automatic and manual status changes for an application.
    """
    history = await get_application_history(db, application_id)
    return history


@router.post("/{application_id}/undo-auto-status")
async def undo_automatic_status(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user)
):
    """
    Allows HR to undo the last automatic status change.
    """
    user_email = (current_user.get("email") if current_user else None) or "HR"
    result = await undo_auto_status_change(db, application_id, user_email)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Cannot undo status change"))
    await invalidate_application_dashboard_caches(application_id)
    return result


@router.post("/{application_id}/withdraw")
async def withdraw_application_endpoint(
    application_id: int,
    payload: Optional[ApplicationWithdrawRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Applicant withdraws a single active application at any time (slot freed immediately)."""
    try:
        result = await job_application_service.withdraw_single_application(
            db=db,
            application_id=application_id,
            actor_user_id=int(current_user.get("id")),
            actor_email=current_user.get("sub") or current_user.get("email") or "",
            reason=payload.reason if payload else None,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await invalidate_application_dashboard_caches(application_id)
    return {
        "message": result["message"],
        "cancelled_interviews": result["cancelled_interviews"],
        "application": JobApplicationResponse.model_validate(result["application"]).model_dump(mode="json"),
    }


@router.post("/{application_id}/post-pass-action")
async def post_pass_action_endpoint(
    application_id: int,
    payload: PostPassActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """HR chooses 'on_hold' or 'continue' for remaining active applications after a Pass."""
    if (current_user.get("role") or "").upper() not in ("HR", "ADMIN"):
        raise HTTPException(status_code=403, detail="Only HR or Admin users may perform this action.")
    try:
        result = await job_application_service.handle_post_pass_other_applications(
            db=db,
            passed_application_id=application_id,
            action=payload.action,
            target_application_ids=payload.target_application_ids,
            actor_id=current_user.get("id"),
            actor_email=current_user.get("sub") or current_user.get("email") or "HR",
            note=payload.note,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await invalidate_application_dashboard_caches(application_id)
    return result


@router.post("/{application_id}/resume", response_model=JobApplicationResponse)
async def resume_application_endpoint(
    application_id: int,
    payload: Optional[ApplicationResumeRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """HR resumes an On Hold application back to its previous active stage."""
    if (current_user.get("role") or "").upper() not in ("HR", "ADMIN"):
        raise HTTPException(status_code=403, detail="Only HR or Admin users may resume applications.")
    try:
        updated = await job_application_service.resume_on_hold_application(
            db=db,
            application_id=application_id,
            actor_id=current_user.get("id"),
            actor_email=current_user.get("sub") or current_user.get("email") or "HR",
            note=payload.note if payload else None,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await invalidate_application_dashboard_caches(application_id)
    return updated


@router.post("/{application_id}/withdraw-hired-elsewhere", response_model=JobApplicationResponse)
async def withdraw_hired_elsewhere_endpoint(
    application_id: int,
    payload: Optional[HiredElsewhereWithdrawRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """HR marks another active application as 'Withdrawn – hired elsewhere in company' (if enabled in System Config)."""
    if (current_user.get("role") or "").upper() not in ("HR", "ADMIN"):
        raise HTTPException(status_code=403, detail="Only HR or Admin users may perform this action.")
    try:
        updated = await job_application_service.withdraw_hired_elsewhere(
            db=db,
            application_id=application_id,
            actor_id=current_user.get("id"),
            actor_email=current_user.get("sub") or current_user.get("email") or "HR",
            note=payload.note if payload else None,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await invalidate_application_dashboard_caches(application_id)
    return updated




