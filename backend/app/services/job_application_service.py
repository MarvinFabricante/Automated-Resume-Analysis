from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.job_application import JobApplication
from app.schemas.job_application_schema import JobApplicationCreate
from app.services.notification_service import create_notification


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


def _enrich_applications(apps: list[JobApplication]) -> list[JobApplication]:
    for app in apps:
        _apply_transient_analysis(app)
    return apps

async def create_job_application(db: AsyncSession, application_in: JobApplicationCreate, db_job_id: int) -> JobApplication:
    data = application_in.model_dump()
    
    # Remove job_id from data as we'll pass the internal ID
    if 'job_id' in data:
        del data['job_id']
        
    new_application = JobApplication(
        job_id=db_job_id,
        **data
    )
    
    db.add(new_application)
    await db.commit()
    
    # Refresh with job relationship loaded for serialization
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.id == new_application.id)
    )
    new_application = result.scalars().first()
    
    # Trigger notification
    try:
        job_title = application_in.job_title if application_in.job_title else "a position"
        await create_notification(
            db=db,
            title="New Application Submitted",
            message=f"{application_in.candidate_name} applied for {job_title}.",
            type="application"
        )
    except Exception as notif_err:
        print(f"WARNING: Notification failed but application saved: {notif_err}")
    # Trigger background AI analysis
    try:
        from app.tasks import analyze_application_task
        analyze_application_task.delay(new_application.id)
        print(f"DEBUG: Dispatched background AI analysis task for application {new_application.id}")
    except Exception as task_err:
        print(f"WARNING: Failed to dispatch background task: {task_err}")
        
    return new_application

async def get_applications_by_job(db: AsyncSession, job_id: int) -> list[JobApplication]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.job_id == job_id)
    )
    return _enrich_applications(result.scalars().all())

async def get_applications_by_email(db: AsyncSession, email: str) -> list[JobApplication]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.candidate_email == email)
        .order_by(JobApplication.created_at.desc())
    )
    return _enrich_applications(result.scalars().all())

async def get_all_applications(db: AsyncSession) -> list[JobApplication]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(JobApplication).options(selectinload(JobApplication.job)).order_by(JobApplication.created_at.desc())
    )
    return _enrich_applications(result.scalars().all())

async def update_application_status(db: AsyncSession, application_id: int, new_status: str) -> Optional[JobApplication]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.job))
        .filter(JobApplication.id == application_id)
    )
    db_application = result.scalars().first()
    
    if not db_application:
        return None
        
    status_upper = new_status.upper()
    db_application.status = status_upper
    await db.commit()
    await db.refresh(db_application)
    
    # Send notifications about status change
    try:
        # Notify HR
        await create_notification(
            db=db,
            title="Application Status Updated",
            message=f"Application for {db_application.candidate_name} marked as {status_upper}.",
            type="application_update",
            target_role="HR"
        )
        # Notify ADMIN
        await create_notification(
            db=db,
            title="Application Status Updated",
            message=f"Application for {db_application.candidate_name} marked as {status_upper}.",
            type="application_update",
            target_role="ADMIN"
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
            target_email=db_application.candidate_email
        )
    except Exception as e:
        print(f"Error creating status update notifications: {e}")
        
    return db_application
