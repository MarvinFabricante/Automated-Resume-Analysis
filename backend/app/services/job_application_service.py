from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.job_application import JobApplication
from app.schemas.job_application_schema import JobApplicationCreate
from app.services.notification_service import create_notification
from app.repositories.job_application_repository import JobApplicationRepository


def _resume_data_from_application(app: JobApplication) -> dict:
    skills = app.skills or []
    if isinstance(skills, list):
        skills_text = " | ".join(str(skill).strip() for skill in skills if str(skill).strip())
    else:
        skills_text = str(skills or "")

    experience_text = " | ".join(
        part for part in [
            app.relevance,
            f"{app.job_title} at {app.company}" if app.job_title or app.company else "",
        ]
        if part
    )

    years_experience = 0
    try:
        import re
        matches = re.findall(r"(\d+)\+?\s*(?:years?|yrs?)", app.relevance or "", re.IGNORECASE)
        if matches:
            years_experience = max(int(match) for match in matches)
    except Exception:
        years_experience = 0

    return {
        "fullname": app.candidate_name,
        "email": app.candidate_email,
        "phone": app.phone or "",
        "location": app.location or "",
        "skills": skills_text,
        "experience": experience_text,
        "years_experience": years_experience,
        "education": " - ".join(part for part in [app.degree, app.college] if part),
        "highest_degree": app.degree or "",
    }


def _needs_analysis_enrichment(app: JobApplication) -> bool:
    return any([
        app.skills_score is None,
        app.experience_score is None,
        app.education_score is None,
        not app.skills_reason,
        not app.experience_reason,
        not app.education_reason,
        not app.matched_skills and not app.missing_skills,
        not app.recommendations,
    ])


def _apply_transient_analysis(app: JobApplication):
    """
    Fill missing analysis fields for older records before serialization.
    This does not commit changes; it only prevents the frontend from showing
    empty/contradictory details when match_score was saved without its breakdown.
    """
    if not app.job or not _needs_analysis_enrichment(app):
        return

    try:
        from app.services.job_matching_service import calculate_match_score
        scores = calculate_match_score(_resume_data_from_application(app), app.job)
    except Exception as e:
        print(f"WARNING: Failed to enrich application analysis for {app.id}: {e}")
        return

    app.match_score = app.match_score if app.match_score is not None else scores.get("match_percentage")
    if app.skills_score is None or (app.skills_score == 0 and scores.get("skills_score", 0) > 0):
        app.skills_score = scores.get("skills_score")
    if app.experience_score is None or (app.experience_score == 0 and scores.get("experience_score", 0) > 0):
        app.experience_score = scores.get("experience_score")
    if app.education_score is None or (app.education_score == 0 and scores.get("education_score", 0) > 0):
        app.education_score = scores.get("education_score")
    app.skills_reason = app.skills_reason or scores.get("skills_reason")
    app.experience_reason = app.experience_reason or scores.get("experience_reason")
    app.education_reason = app.education_reason or scores.get("education_reason")
    app.matched_skills = app.matched_skills or scores.get("matched_skills")
    app.missing_skills = app.missing_skills or scores.get("missing_skills")
    app.relevant_experience = app.relevant_experience or scores.get("relevant_experience")
    app.experience_gaps = app.experience_gaps or scores.get("experience_gaps")
    app.required_degree = app.required_degree or scores.get("required_degree")
    app.candidate_degree = app.candidate_degree or scores.get("candidate_degree")
    app.recommendations = app.recommendations or scores.get("recommendations")
    app.ai_summary = app.ai_summary or scores.get("ai_summary")
    app.strengths = app.strengths or scores.get("strengths")
    app.weaknesses = app.weaknesses or scores.get("weaknesses")
    app.ai_powered = app.ai_powered or scores.get("ai_powered", False)


def _enrich_resume_url(app: JobApplication):
    if app.resume_url:
        return

    import re

    name_parts = [p.lower() for p in re.split(r'\W+', app.candidate_name) if p]
    if not name_parts:
        return

    # Try Supabase Storage first
    try:
        from app.utils.supabase_storage import _get_client, SUPABASE_BUCKET
        client = _get_client()
        files = client.storage.from_(SUPABASE_BUCKET).list("resumes")

        best_match = None
        best_time = -1

        # Check top-level files and subdirectory files
        all_files = []
        for item in files:
            if item.get("id") is None:
                # It's a folder – list its contents
                folder_name = item.get("name", "")
                try:
                    sub_files = client.storage.from_(SUPABASE_BUCKET).list(f"resumes/{folder_name}")
                    for sf in sub_files:
                        if sf.get("id"):
                            all_files.append((f"resumes/{folder_name}/{sf['name']}", sf["name"]))
                except Exception:
                    pass
            else:
                all_files.append((f"resumes/{item['name']}", item["name"]))

        for storage_path, filename in all_files:
            filename_lower = filename.lower()
            if all(part in filename_lower for part in name_parts):
                match = re.match(r'^(\d+)_', filename)
                if match:
                    ts = int(match.group(1))
                    if ts > best_time:
                        best_time = ts
                        best_match = storage_path
                elif not best_match:
                    best_match = storage_path

        if best_match:
            public_url = client.storage.from_(SUPABASE_BUCKET).get_public_url(best_match)
            app.resume_url = public_url
            return
    except Exception as e:
        print(f"WARNING: Supabase resume lookup failed, trying local: {e}")

    # Fallback: local filesystem
    import os
    upload_dir = "uploads/resumes"
    if not os.path.exists(upload_dir):
        return

    best_match = None
    best_time = -1

    try:
        for filename in os.listdir(upload_dir):
            filename_lower = filename.lower()
            if all(part in filename_lower for part in name_parts):
                match = re.match(r'^(\d+)_', filename)
                if match:
                    ts = int(match.group(1))
                    if ts > best_time:
                        best_time = ts
                        best_match = filename
                elif not best_match:
                    best_match = filename
    except Exception as e:
        print(f"WARNING: Error while trying to auto-resolve resume url: {e}")

    if best_match:
        app.resume_url = f"http://localhost:8000/{upload_dir}/{best_match}"

def _enrich_applications(apps: list[JobApplication]) -> list[JobApplication]:
    for app in apps:
        _apply_transient_analysis(app)
        _enrich_resume_url(app)
    return apps

async def create_job_application(db: AsyncSession, application_in: JobApplicationCreate, db_job_id: int):
    """Create a new job application and trigger AI analysis."""
    data = application_in.model_dump()

    # Remove job_id from data as we'll pass the internal ID
    if 'job_id' in data:
        del data['job_id']

    # Create the application via repository
    new_application = await JobApplicationRepository.create(db, {
        "job_id": db_job_id,
        **data
    })

    # Trigger notification
    try:
        job_title = application_in.job_title if application_in.job_title else "a position"
        await create_notification(
            db=db,
            title="New Application Submitted",
            message=f"{application_in.candidate_name} applied for {job_title}.",
            type="application",
            sender_role="CANDIDATE"
        )
    except Exception as notif_err:
        print(f"WARNING: Notification failed but application saved: {notif_err}")
    # Trigger background AI analysis
    try:
        import asyncio
        from app.tasks import async_analyze_application
        asyncio.create_task(async_analyze_application(new_application.id))
        print(f"DEBUG: Dispatched background AI analysis task for application {new_application.id}")
    except Exception as task_err:
        print(f"WARNING: Failed to dispatch background task: {task_err}")

    return new_application


async def get_applications_by_job(db: AsyncSession, job_id: int):
    """Get all applications for a specific job."""
    applications = await JobApplicationRepository.get_by_job_id(db, job_id)
    return _enrich_applications(applications)


async def get_applications_by_email(db: AsyncSession, email: str):
    """Get all applications for a specific candidate email."""
    applications = await JobApplicationRepository.get_by_email(db, email)
    return _enrich_applications(applications)


async def get_all_applications(db: AsyncSession):
    """Get all job applications."""
    applications = await JobApplicationRepository.get_all(db)
    return _enrich_applications(applications)


async def update_application_status(db: AsyncSession, application_id: int, new_status: str) -> Optional[JobApplication]:
    """Update application status and send notifications."""
    db_application = await JobApplicationRepository.get_by_id(db, application_id)

    if not db_application:
        return None

    status_upper = new_status.upper()
    db_application.status = status_upper
    db_application = await JobApplicationRepository.update(db, db_application)

    # Send notifications about status change
    try:
        # Notify HR
        await create_notification(
            db=db,
            title="Application Status Updated",
            message=f"Application for {db_application.candidate_name} marked as {status_upper}.",
            type="application_update",
            target_role="HR",
            sender_role="HR"
        )
        # Notify ADMIN
        await create_notification(
            db=db,
            title="Application Status Updated",
            message=f"Application for {db_application.candidate_name} marked as {status_upper}.",
            type="application_update",
            target_role="ADMIN",
            sender_role="HR"
        )

        # Notify Candidate (Targeted to their email)
        job_title = db_application.job.job_title if (db_application.job and db_application.job.job_title) else (db_application.job_title or "Position")

        if status_upper == "ACCEPTED":
            title = "Application Accepted 🎉"
            message = f"Congratulations! Your application for the position of {job_title} has been accepted."
        elif status_upper == "REJECTED":
            title = "Application Update"
            message = f"Thank you for your interest. Unfortunately, your application for the position of {job_title} has been rejected."
        elif status_upper == "TECHNICAL INTERVIEW":
            title = "Technical Interview Scheduled 💻"
            message = f"You have advanced to the Technical Interview stage for the {job_title} position!"
        elif status_upper == "FINAL INTERVIEW":
            title = "Final Interview Scheduled 🤝"
            message = f"Great news! You have reached the Final Interview stage for the {job_title} position!"
        elif status_upper == "REVIEWED":
            title = "Application Under Review"
            message = f"Great news! Your application for the position of {job_title} has been reviewed."
        else:
            title = "Application Status Update"
            message = f"Your application for the position of {job_title} is currently pending review."

        await create_notification(
            db=db,
            title=title,
            message=message,
            type="application_update",
            target_role="CANDIDATE",
            target_email=db_application.candidate_email,
            sender_role="HR"
        )
    except Exception as e:
        print(f"Error creating status update notifications: {e}")

    return db_application


async def delete_application(db: AsyncSession, application_id: int) -> Optional[JobApplication]:
    """Delete a job application."""
    db_application = await JobApplicationRepository.get_by_id(db, application_id)
    if not db_application:
        return None

    await JobApplicationRepository.delete(db, db_application)
    return db_application


async def get_and_validate_job(db: AsyncSession, job_id: str):
    """Get and validate a job by job_id, with fallback to numeric ID lookup."""
    from app.repositories.job_description_repository import JobDescriptionRepository

    # Try to get by job_id first
    job = await JobDescriptionRepository.get_by_job_id(db, job_id)

    if not job:
        # Fallback for static jobs or numeric IDs
        try:
            numeric_id = int(job_id)
            job = await JobDescriptionRepository.get_by_id(db, numeric_id)
        except (ValueError, TypeError):
            pass

    return job


class JobApplicationService:
    create_job_application = staticmethod(create_job_application)
    get_applications_by_job = staticmethod(get_applications_by_job)
    get_applications_by_email = staticmethod(get_applications_by_email)
    get_all_applications = staticmethod(get_all_applications)
    update_application_status = staticmethod(update_application_status)
    delete_application = staticmethod(delete_application)
    get_and_validate_job = staticmethod(get_and_validate_job)


job_application_service = JobApplicationService()

