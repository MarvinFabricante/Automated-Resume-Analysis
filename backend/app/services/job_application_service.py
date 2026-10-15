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
    if getattr(app, "total_experience_months", 0):
        years_experience = max(1, round(app.total_experience_months / 12.0))
    else:
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
        "work_experiences": getattr(app, "work_experiences", []) or [],
        "total_experience_months": getattr(app, "total_experience_months", 0) or 0,
        "years_experience": years_experience,
        "education": " - ".join(part for part in [app.degree, app.college] if part),
        "highest_degree": app.degree or "",
        "highest_educational_attainment": getattr(app, "highest_educational_attainment", None) or app.degree or "",
        "education_entries": getattr(app, "education_entries", []) or [],
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
    Check if analysis fields are missing for older records.
    Instead of calculating synchronously, dispatch a background task to process it.
    """
    if not app.job or not _needs_analysis_enrichment(app):
        return

    try:
        from app.tasks import analyze_application_task
        analyze_application_task.delay(app.id)
    except Exception as e:
        print(f"WARNING: Failed to dispatch background analysis for {app.id}: {e}")


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
        app.resume_url = f"/{upload_dir}/{best_match}"

def _enrich_applications(apps: list[JobApplication]) -> list[JobApplication]:
    for app in apps:
        _apply_transient_analysis(app)
        _enrich_resume_url(app)
        if not getattr(app, "work_experiences", None):
            exp_source = app.relevant_experience or app.relevance or ""
            if exp_source and len(exp_source.strip()) > 5:
                try:
                    from app.extractors.content.experience_extractor import extract_structured_experience
                    structured = extract_structured_experience(exp_source)
                    if structured.get("work_experiences"):
                        app.work_experiences = structured["work_experiences"]
                        app.total_experience_months = structured.get("total_experience_months", 0)
                except Exception:
                    pass

        if not getattr(app, "education_entries", None):
            edu_source = " \n ".join(part for part in [app.candidate_degree, app.degree, app.college] if part)
            if edu_source and len(edu_source.strip()) > 3:
                try:
                    from app.extractors.content.education_extractor import extract_structured_education
                    structured_edu = extract_structured_education(edu_source)
                    if structured_edu.get("education_entries"):
                        app.education_entries = structured_edu["education_entries"]
                        app.highest_educational_attainment = structured_edu.get("highest_educational_attainment")
                except Exception:
                    pass
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

    # Trigger notifications
    try:
        # Resolve the exact job title of the position applied for
        applied_job_title = None
        if new_application and getattr(new_application, "job", None) and new_application.job.job_title:
            applied_job_title = new_application.job.job_title
        else:
            from app.repositories.job_description_repository import JobDescriptionRepository
            job_desc = await JobDescriptionRepository.get_by_id(db, db_job_id)
            if job_desc and job_desc.job_title:
                applied_job_title = job_desc.job_title

        if not applied_job_title:
            applied_job_title = application_in.job_title or "the position"

        # 1. Alert HR team
        await create_notification(
            db=db,
            title="New Application Submitted",
            message=f"{application_in.candidate_name} applied for {applied_job_title}.",
            type="application",
            target_role="HR",
            sender_role="CANDIDATE"
        )
        # 2. Alert Admin team
        await create_notification(
            db=db,
            title="New Application Submitted",
            message=f"{application_in.candidate_name} applied for {applied_job_title}.",
            type="application",
            target_role="ADMIN",
            sender_role="CANDIDATE"
        )
        # 3. Personal confirmation for Candidate
        if application_in.candidate_email:
            await create_notification(
                db=db,
                title="Application Submitted",
                message=f"You successfully applied for {applied_job_title}.",
                type="application",
                target_role="CANDIDATE",
                target_email=application_in.candidate_email,
                sender_role="SYSTEM"
            )
    except Exception as notif_err:
        print(f"WARNING: Notification failed but application saved: {notif_err}")
    # Trigger background AI analysis
    try:
        import asyncio
        from app.tasks import analyze_application_task
        analyze_application_task.delay(new_application.id)
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
        job_title = None
        if db_application.job and db_application.job.job_title:
            job_title = db_application.job.job_title
        elif getattr(db_application, "job_id", None):
            from app.repositories.job_description_repository import JobDescriptionRepository
            job_desc = await JobDescriptionRepository.get_by_id(db, db_application.job_id)
            if job_desc and job_desc.job_title:
                job_title = job_desc.job_title
        if not job_title:
            job_title = db_application.job_title or "Position"

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


import sys
job_application_service = sys.modules[__name__]
