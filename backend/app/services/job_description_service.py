import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.job_description_schema import JobCreate, JobUpdate
from app.services.notification_service import create_notification
from app.repositories.job_description_repository import JobDescriptionRepository

logger = logging.getLogger(__name__)

VALID_JOB_STATUSES = {"DRAFT", "ACTIVE", "CLOSED", "ARCHIVED"}
ALLOWED_JOB_TRANSITIONS = {
    "DRAFT": {"ACTIVE", "ARCHIVED"},
    "ACTIVE": {"CLOSED", "ARCHIVED"},
    "CLOSED": {"ACTIVE", "ARCHIVED"},
    "ARCHIVED": set(),  # Terminal: archived jobs cannot be reopened
}
NON_SHORTLISTED_CLOSE_ELIGIBLE = {"Submitted", "Under Review"}


async def get_default_job_weights(db: AsyncSession) -> dict:
    """
    Weights every new job starts with: the global default from System Settings,
    which itself defaults to the thesis distribution (40/30/15/10/5).
    """
    from app.services.job_matching_service import THESIS_DEFAULT_WEIGHTS, normalize_scoring_weights

    try:
        from app.services.system_config_service import get_matching_parameters
        config = await get_matching_parameters(db)
        weights = normalize_scoring_weights(config.get("weights"))
        if weights:
            total = sum(weights.values())
            return {k: round(v / total, 4) for k, v in weights.items()}
    except Exception as e:
        logger.warning(f"Could not load global default weights, using thesis defaults: {e}")
    return dict(THESIS_DEFAULT_WEIGHTS)


def apply_match_result_to_application(app, scores: dict) -> None:
    """Copy a calculate_match_score() result onto a JobApplication row."""
    app.match_score = scores.get("match_percentage")
    app.skills_score = scores.get("skills_score")
    app.experience_score = scores.get("experience_score")
    app.education_score = scores.get("education_score")
    app.certifications_score = scores.get("certifications_score")
    if scores.get("completeness_score") is not None:
        app.completeness_score = scores.get("completeness_score")
    if scores.get("applied_weights") is not None:
        app.applied_weights = scores.get("applied_weights")

    app.skills_reason = scores.get("skills_reason")
    app.experience_reason = scores.get("experience_reason")
    app.education_reason = scores.get("education_reason")
    app.certifications_reason = scores.get("certifications_reason")

    app.matched_skills = scores.get("matched_skills")
    app.missing_skills = scores.get("missing_skills")
    app.requirement_evaluations = scores.get("requirement_evaluations", [])
    app.relevant_experience = scores.get("relevant_experience")
    app.experience_gaps = scores.get("experience_gaps")
    app.required_degree = scores.get("required_degree")
    app.candidate_degree = scores.get("candidate_degree")
    app.required_certifications = scores.get("required_certifications")
    app.candidate_certifications = scores.get("candidate_certifications")
    app.recommendations = scores.get("recommendations")
    app.ai_summary = scores.get("ai_summary")
    app.strengths = scores.get("strengths")
    app.weaknesses = scores.get("weaknesses")
    app.ai_powered = bool(scores.get("ai_powered", False))


async def rescore_job_applications(db: AsyncSession, db_job, progress_cb=None) -> int:
    """Re-score every application of a job with its current requirements and weights.
    Never modifies application status or shortlist rosters.
    """
    from app.services.job_matching_service import calculate_match_score
    from app.services.job_application_service import _resume_data_from_application
    from app.services.system_config_service import get_matching_parameters

    config = await get_matching_parameters(db)
    applications = await JobDescriptionRepository.get_applications_for_job(db, db_job.id)
    total = len(applications)
    for idx, app in enumerate(applications, start=1):
        resume_data = _resume_data_from_application(app)
        scores = calculate_match_score(resume_data, db_job, matching_config=config)
        apply_match_result_to_application(app, scores)
        if progress_cb:
            progress_cb(idx, total)

    await JobDescriptionRepository.bulk_update_applications(db, applications)
    return total


async def create_job(db: AsyncSession, job: JobCreate):
    """Create a new job and trigger notification."""
    job_data = job.model_dump()
    raw_status = (job_data.get("status") or ("ACTIVE" if job_data.get("is_active", True) else "DRAFT")).strip().upper()
    if raw_status not in VALID_JOB_STATUSES:
        raw_status = "ACTIVE"
    job_data["status"] = raw_status
    job_data["is_active"] = raw_status == "ACTIVE"
    # Every new job starts with the default weights unless the admin already adjusted them.
    if not job_data.get("scoring_weights"):
        job_data["scoring_weights"] = await get_default_job_weights(db)
    db_job = await JobDescriptionRepository.create(db, job_data)

    # Trigger notification for HR and Admin
    await create_notification(
        db=db,
        title="New Job Created",
        message=f"A new position '{db_job.job_title}' has been posted ({raw_status}).",
        type="job_creation",
        target_role="HR",
        sender_role="ADMIN"
    )

    return db_job


async def get_job(db: AsyncSession, job_id: str):
    """Get a job by job_id (or numeric PK fallback)."""
    job = await JobDescriptionRepository.get_by_job_id(db, job_id)
    if not job and str(job_id).isdigit():
        job = await JobDescriptionRepository.get_by_id(db, int(job_id))
    return job


async def get_all_active_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False,
    include_archived: bool = False,
):
    """Get jobs filtered by lifecycle status with pagination."""
    return await JobDescriptionRepository.get_all_active(
        db,
        skip=skip,
        limit=limit,
        include_inactive=include_inactive,
        include_archived=include_archived,
    )


async def update_job(db: AsyncSession, job_id: str, job_data: JobUpdate, rescore_on_weight_change: bool = False):
    """Update job. When only requirements change, sync application scores; when
    scoring_weights change, keep existing scores intact unless rescore_on_weight_change=True
    (admins choose between 'Update scores now' and 'Apply to new applications only').
    """
    # Fetch the job
    db_job = await JobDescriptionRepository.get_by_job_id(db, job_id)

    if not db_job:
        return None

    # Update job with provided data
    update_data = job_data.model_dump(exclude_unset=True)
    weights_in_payload = "scoring_weights" in job_data.model_fields_set
    db_job = await JobDescriptionRepository.update(db, db_job, update_data)

    if not weights_in_payload or rescore_on_weight_change:
        try:
            count = await rescore_job_applications(db, db_job)
            logger.info(f"Re-scored {count} application(s) for job {db_job.job_id}.")
        except Exception as match_sync_err:
            logger.warning(f"Failed to sync application scores for job {job_id}: {match_sync_err}")

    # Trigger notification for HR and Admin
    await create_notification(
        db=db,
        title="Job Description Modified",
        message=f"The job details for '{db_job.job_title}' have been updated.",
        type="job_update",
        target_role="HR",
        sender_role="ADMIN"
    )

    return db_job


async def get_non_shortlisted_applications_for_job(
    db: AsyncSession,
    job_pk: int,
    extra_shortlisted_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    """
    Identify applications for a job that are NOT shortlisted:
    status in {Submitted, Under Review} AND not on any ShortlistRoster for this job.
    Protected statuses (Shortlisted, Interview Scheduled, Interviewed, On Hold, Passed, Withdrawn)
    are never included.
    """
    from app.models.job_application import JobApplication
    from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
    from app.services.status_management_service import normalize_status

    apps_res = await db.execute(
        select(JobApplication).where(JobApplication.job_id == job_pk)
    )
    all_apps = list(apps_res.scalars().all())

    roster_res = await db.execute(
        select(ShortlistRosterItem.application_id)
        .join(ShortlistRoster, ShortlistRosterItem.roster_id == ShortlistRoster.id)
        .where(ShortlistRoster.job_id == job_pk)
    )
    roster_app_ids = {row[0] for row in roster_res.fetchall()}
    if extra_shortlisted_ids:
        roster_app_ids.update(int(x) for x in extra_shortlisted_ids)

    affected: List[JobApplication] = []
    protected_count = 0

    for app in all_apps:
        norm = normalize_status(app.status)
        if norm in NON_SHORTLISTED_CLOSE_ELIGIBLE and app.id not in roster_app_ids:
            affected.append(app)
        elif norm in ("Shortlisted", "Interview Scheduled", "Interviewed", "On Hold"):
            protected_count += 1

    return {
        "affected": affected,
        "protected_count": protected_count,
        "total_applications": len(all_apps),
    }


async def get_close_job_preview(db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
    """Return how many non-shortlisted applicants will become Not Selected when closing this job."""
    db_job = await get_job(db, job_id)
    if not db_job:
        return None

    from app.services.message_template_service import render_not_selected_preview

    breakdown = await get_non_shortlisted_applications_for_job(db, db_job.id)
    affected = breakdown["affected"]
    preview = await render_not_selected_preview(
        db=db,
        job_title=db_job.job_title,
        reason="Position closed",
    )

    return {
        "job_id": db_job.job_id,
        "job_pk": db_job.id,
        "job_title": db_job.job_title,
        "current_status": getattr(db_job, "status", None) or ("ACTIVE" if db_job.is_active else "ARCHIVED"),
        "affected_count": len(affected),
        "protected_count": breakdown["protected_count"],
        "affected_applications": [
            {
                "id": a.id,
                "candidate_name": a.candidate_name,
                "candidate_email": a.candidate_email,
                "status": a.status,
            }
            for a in affected
        ],
        "message_preview": preview,
    }


async def transition_job_lifecycle_status(
    db: AsyncSession,
    job_id: str,
    target_status: str,
    actor_id: Optional[int] = None,
    actor_email: str = "HR",
) -> Dict[str, Any]:
    """
    Transition a job opening across lifecycle statuses: DRAFT -> ACTIVE -> CLOSED -> ARCHIVED.
    - Reopen is allowed ONLY from CLOSED -> ACTIVE.
    - ARCHIVED is terminal and cannot be reopened.
    - Transitioning to CLOSED automatically marks non-shortlisted applications
      (Submitted / Under Review and not on a roster) as Not Selected with reason 'Position closed'
      (idempotent, notifies each applicant once only; never touches Shortlisted/Interview Scheduled/Interviewed).
    - Audit logs every status change (who, when, old, new).
    """
    from app.services.audit_service import record_activity
    from app.services.status_management_service import apply_application_status_change

    db_job = await get_job(db, job_id)
    if not db_job:
        raise LookupError(f"Job {job_id} not found")

    old_status = (getattr(db_job, "status", None) or ("ACTIVE" if db_job.is_active else "ARCHIVED")).strip().upper()
    new_status = (target_status or "").strip().upper()
    if new_status not in VALID_JOB_STATUSES:
        raise ValueError(f"Invalid job status '{target_status}'. Allowed values: DRAFT, ACTIVE, CLOSED, ARCHIVED.")

    if old_status == new_status:
        return {
            "job": db_job,
            "old_status": old_status,
            "new_status": new_status,
            "auto_not_selected_count": 0,
            "changed": False,
        }

    if old_status == "ARCHIVED":
        raise ValueError("Archived job openings cannot be reopened or changed.")

    if new_status not in ALLOWED_JOB_TRANSITIONS.get(old_status, set()):
        raise ValueError(
            f"Cannot transition job opening from '{old_status}' to '{new_status}'."
        )

    now = datetime.utcnow()
    closed_at = now if new_status == "CLOSED" else None
    archived_at = now if new_status == "ARCHIVED" else None

    db_job = await JobDescriptionRepository.set_lifecycle_status(
        db=db,
        job=db_job,
        lifecycle_status=new_status,
        closed_at=closed_at,
        archived_at=archived_at,
    )

    auto_not_selected_count = 0
    if new_status == "CLOSED":
        breakdown = await get_non_shortlisted_applications_for_job(db, db_job.id)
        for app in breakdown["affected"]:
            await apply_application_status_change(
                db=db,
                application=app,
                new_status="Not Selected",
                changed_by=actor_email,
                change_type="auto",
                reason="Position closed",
                send_email=True,
                send_notification=True,
            )
            auto_not_selected_count += 1

    await record_activity(
        db=db,
        user_id=actor_id,
        action="CHANGE_JOB_STATUS",
        target=f"Job: {db_job.job_id} ({db_job.job_title})",
        details=(
            f"{actor_email} changed job status from {old_status} to {new_status} at {now.isoformat()}"
            + (f" ({auto_not_selected_count} non-shortlisted application(s) set to Not Selected)." if new_status == "CLOSED" else ".")
        ),
    )

    return {
        "job": db_job,
        "old_status": old_status,
        "new_status": new_status,
        "auto_not_selected_count": auto_not_selected_count,
        "changed": True,
    }


async def set_job_status(db: AsyncSession, job_id: str, active_status: bool):
    """Legacy wrapper for active/inactive toggles."""
    db_job = await get_job(db, job_id)
    if db_job:
        db_job = await JobDescriptionRepository.set_status(db, db_job, active_status)
    return db_job


async def delete_job(db: AsyncSession, job_id: str):
    """Delete a job."""
    db_job = await JobDescriptionRepository.get_by_job_id(db, job_id)

    if db_job:
        await JobDescriptionRepository.delete(db, db_job)

    return db_job


import sys
job_service = sys.modules[__name__]
job_description_service = sys.modules[__name__]

