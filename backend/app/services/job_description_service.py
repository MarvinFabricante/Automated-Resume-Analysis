import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.job_description_schema import JobCreate, JobUpdate
from app.services.notification_service import create_notification
from app.repositories.job_description_repository import JobDescriptionRepository

logger = logging.getLogger(__name__)


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
    app.ai_powered = False


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
    # Every new job starts with the default weights unless the admin already adjusted them.
    if not job_data.get("scoring_weights"):
        job_data["scoring_weights"] = await get_default_job_weights(db)
    db_job = await JobDescriptionRepository.create(db, job_data)

    # Trigger notification for HR and Admin
    await create_notification(
        db=db,
        title="New Job Created",
        message=f"A new position '{db_job.job_title}' has been posted.",
        type="job_creation",
        target_role="HR",
        sender_role="ADMIN"
    )

    return db_job


async def get_job(db: AsyncSession, job_id: str):
    """Get a job by job_id."""
    return await JobDescriptionRepository.get_by_job_id(db, job_id)


async def get_all_active_jobs(db: AsyncSession, skip: int = 0, limit: int = 100, include_inactive: bool = False):
    """Get all active jobs with pagination."""
    return await JobDescriptionRepository.get_all_active(db, skip, limit, include_inactive)


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


async def set_job_status(db: AsyncSession, job_id: str, active_status: bool):
    """Set job status (active/inactive)."""
    db_job = await JobDescriptionRepository.get_by_job_id(db, job_id)

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

