import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from app.models.job_application import JobApplication
from app.models.job_description import JobDescription
from app.models.interview import Interview, InterviewLog, VoiceCallRecord
from app.models.shortlist_roster import ShortlistRoster, ShortlistRosterItem
from app.models.candidate_note import HRCandidateNote
from app.models.profile_access_log import ApplicantProfileAccessLog
from app.models.status_history import ApplicationStatusHistory
from app.services.status_management_service import normalize_status

logger = logging.getLogger(__name__)

async def log_applicant_profile_access(
    db: AsyncSession,
    applicant_email: str,
    accessed_by: str,
    purpose: str = "Interview & Screening Review"
) -> ApplicantProfileAccessLog:
    """
    Data Privacy Act compliance logging:
    Logs every time an applicant's complete profile is accessed by an authorized HR user.
    """
    access_log = ApplicantProfileAccessLog(
        applicant_email=applicant_email.lower().strip(),
        accessed_by=accessed_by,
        purpose=purpose,
        accessed_at=datetime.utcnow()
    )
    db.add(access_log)
    await db.commit()
    await db.refresh(access_log)
    return access_log

async def get_applicant_comprehensive_profile(
    db: AsyncSession,
    email: str,
    accessed_by: str = "HR"
) -> Optional[Dict[str, Any]]:
    clean_email = email.lower().strip()

    # Log access for Data Privacy Act compliance
    await log_applicant_profile_access(db, clean_email, accessed_by)

    # 1. Fetch all applications for this candidate
    stmt = (
        select(JobApplication)
        .where(func.lower(JobApplication.candidate_email) == clean_email)
        .order_by(JobApplication.created_at.desc())
    )
    res = await db.execute(stmt)
    applications = list(res.scalars().all())

    if not applications:
        return None

    primary_app = applications[0]

    # 2. Extract applicant details
    candidate_summary = {
        "name": primary_app.candidate_name or primary_app.candidate_email or "Applicant",
        "email": primary_app.candidate_email,
        "candidate_name": primary_app.candidate_name or primary_app.candidate_email or "Applicant",
        "candidate_email": primary_app.candidate_email,
        "phone": primary_app.phone,
        "location": primary_app.location,
        "resume_url": primary_app.resume_url,
        "profile_image_url": primary_app.profile_image_url,
        "source": getattr(primary_app, "source", "Online") or "Online",
        "import_origin": getattr(primary_app, "import_origin", None),
        "imported_by": getattr(primary_app, "imported_by", None),
    }
    contact_details = candidate_summary

    extracted_details = {
        "highest_degree": primary_app.highest_educational_attainment or primary_app.degree,
        "college": primary_app.college,
        "education_entries": primary_app.education_entries or [],
        "years_experience": getattr(primary_app, "years_experience", None) or (
            round((primary_app.total_experience_months or 0) / 12, 1)
            if primary_app.total_experience_months else None
        ),
        "work_experiences": primary_app.work_experiences or [],
        "skills": primary_app.skills or [],
        "certifications": primary_app.candidate_certifications or primary_app.certifications,
        "ai_summary": primary_app.ai_summary,
    }

    # 3. Process all applications with job info and rosters
    apps_data = []
    shortlisted_positions = []
    all_status_history = []

    for app in applications:
        job_stmt = select(JobDescription).where(JobDescription.id == app.job_id)
        job_res = await db.execute(job_stmt)
        job = job_res.scalar_one_or_none()
        job_title = job.job_title if job else (app.job_title or "Position")

        # Find which rosters this application is in
        roster_stmt = (
            select(ShortlistRoster.id, ShortlistRoster.name, ShortlistRosterItem.stage)
            .join(ShortlistRosterItem, ShortlistRoster.id == ShortlistRosterItem.roster_id)
            .where(ShortlistRosterItem.application_id == app.id)
        )
        roster_res = await db.execute(roster_stmt)
        roster_rows = roster_res.all()
        rosters_in = [{"id": r[0], "name": r[1], "stage": r[2]} for r in roster_rows]

        norm_status = normalize_status(app.status)
        if norm_status in ("Shortlisted", "Interview Scheduled", "Interviewed"):
            shortlisted_positions.append(job_title)

        # Status history for this application
        hist_stmt = (
            select(ApplicationStatusHistory)
            .where(ApplicationStatusHistory.application_id == app.id)
            .order_by(ApplicationStatusHistory.created_at.desc())
        )
        hist_res = await db.execute(hist_stmt)
        hist_rows = list(hist_res.scalars().all())
        app_history = [
            {
                "id": h.id,
                "application_id": h.application_id,
                "job_title": job_title,
                "old_status": h.old_status,
                "new_status": h.new_status,
                "changed_by": h.changed_by,
                "change_type": h.change_type,
                "reason": h.reason,
                "can_undo": h.can_undo,
                "created_at": h.created_at.isoformat() if h.created_at else None
            }
            for h in hist_rows
        ]
        all_status_history.extend(app_history)

        apps_data.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": job_title,
            "department": getattr(job, "department", "General") if job else "General",
            "applied_date": app.created_at.isoformat() if app.created_at else None,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "status": norm_status,
            "match_score": app.match_score,
            "matched_skills": app.matched_skills or [],
            "missing_skills": app.missing_skills or [],
            "strengths": app.strengths or [],
            "weaknesses": app.weaknesses or [],
            "skills_reason": app.skills_reason,
            "experience_reason": app.experience_reason,
            "education_reason": app.education_reason,
            "source": getattr(app, "source", "Online") or "Online",
            "import_origin": getattr(app, "import_origin", None),
            "imported_by": getattr(app, "imported_by", None),
            "shortlist_rosters": rosters_in,
            "status_history": app_history
        })

    all_status_history.sort(key=lambda x: x["created_at"] or "", reverse=True)

    # 4. Fetch interviews (all upcoming and past)
    app_ids = [a.id for a in applications]
    if app_ids:
        int_stmt = (
            select(Interview)
            .where(Interview.job_application_id.in_(app_ids))
            .order_by(Interview.start_time.desc())
        )
        int_res = await db.execute(int_stmt)
        interviews = list(int_res.scalars().all())
    else:
        interviews = []

    interviews_data = []
    upcoming_interview_str = None
    now = datetime.utcnow()

    for item in interviews:
        is_upcoming = item.start_time > now and item.status != "CANCELED"
        if is_upcoming and not upcoming_interview_str:
            time_formatted = item.start_time.strftime("%b %d, %Y at %I:%M %p")
            upcoming_interview_str = f"{item.title} on {time_formatted}"

        interviews_data.append({
            "id": item.id,
            "title": item.title,
            "start_time": item.start_time.isoformat() if item.start_time else None,
            "end_time": item.end_time.isoformat() if item.end_time else None,
            "interviewer_name": item.interviewer_name,
            "meeting_link": item.meeting_link,
            "location": item.location,
            "status": item.status,
            "candidate_response": item.candidate_response,
            "is_upcoming": is_upcoming
        })

    # 5. Fetch call logs and phone history
    interview_ids = [i.id for i in interviews]
    if interview_ids:
        call_stmt = (
            select(VoiceCallRecord)
            .where(VoiceCallRecord.interview_id.in_(interview_ids))
            .order_by(VoiceCallRecord.created_at.desc())
        )
        call_res = await db.execute(call_stmt)
        call_logs = list(call_res.scalars().all())
    else:
        call_logs = []

    call_data = [
        {
            "id": c.id,
            "call_sid": c.call_sid,
            "duration": c.duration,
            "call_status": c.status,
            "ai_summary": c.notes or c.candidate_verbal_response,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in call_logs
    ]

    # 6. Fetch HR Notes
    notes_stmt = (
        select(HRCandidateNote)
        .where(func.lower(HRCandidateNote.candidate_email) == clean_email)
        .order_by(HRCandidateNote.created_at.desc())
    )
    notes_res = await db.execute(notes_stmt)
    notes_records = list(notes_res.scalars().all())
    notes_data = [
        {
            "id": n.id,
            "author_email": n.author_email,
            "author_name": n.author_name or n.author_email,
            "content": n.content,
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None
        }
        for n in notes_records
    ]

    # 7. Generate top summary strip (e.g. "Applied to 2 positions • Shortlisted for 1 • Interview: Nov 15 at 2:00 PM")
    total_apps_count = len(applications)
    shortlisted_count = len(shortlisted_positions)
    summary_parts = [f"Applied to {total_apps_count} {'position' if total_apps_count == 1 else 'positions'}"]
    if shortlisted_count > 0:
        summary_parts.append(f"Shortlisted for {shortlisted_count}")
    else:
        summary_parts.append("In Review")

    if upcoming_interview_str:
        summary_parts.append(f"Next: {upcoming_interview_str}")
    else:
        summary_parts.append("No interview booked yet")

    summary_strip = " • ".join(summary_parts)

    return {
        "candidate": candidate_summary,
        "candidate_email": clean_email,
        "contact_details": contact_details,
        "extracted_details": extracted_details,
        "applications": apps_data,
        "interviews": interviews_data,
        "call_logs": call_data,
        "notes": notes_data,
        "hr_notes": notes_data,
        "status_history": all_status_history,
        "summary_strip": summary_strip,
        "total_applications": total_apps_count,
        "shortlisted_count": shortlisted_count
    }

async def add_candidate_hr_note(
    db: AsyncSession,
    candidate_email: str,
    author_email: str,
    content: str,
    author_name: Optional[str] = None
) -> HRCandidateNote:
    note = HRCandidateNote(
        candidate_email=candidate_email.lower().strip(),
        author_email=author_email,
        author_name=author_name or author_email,
        content=content,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note

async def universal_search_hr(
    db: AsyncSession,
    query: str
) -> Dict[str, Any]:
    """
    Universal Search for HR:
    Groups results into Applicants, Jobs, and Shortlists.
    """
    q = query.strip()
    if not q:
        return {"applicants": [], "jobs": [], "shortlists": []}

    pattern = f"%{q.lower()}%"

    # 1. Search Applicants (name, email, job_title)
    app_stmt = (
        select(JobApplication)
        .where(
            or_(
                func.lower(JobApplication.candidate_name).like(pattern),
                func.lower(JobApplication.candidate_email).like(pattern),
                func.lower(JobApplication.job_title).like(pattern)
            )
        )
        .order_by(JobApplication.created_at.desc())
        .limit(10)
    )
    app_res = await db.execute(app_stmt)
    apps = list(app_res.scalars().all())

    applicants_results = []
    for a in apps:
        applicants_results.append({
            "id": a.id,
            "name": a.candidate_name,
            "email": a.candidate_email,
            "job_title": a.job_title or "Position",
            "status": normalize_status(a.status),
            "match_score": a.match_score,
            "created_at": a.created_at.isoformat() if a.created_at else None
        })

    # 2. Search Jobs (title, department, location)
    job_stmt = (
        select(JobDescription)
        .where(
            or_(
                func.lower(JobDescription.job_title).like(pattern),
                func.lower(JobDescription.department).like(pattern),
                func.lower(JobDescription.location).like(pattern)
            )
        )
        .limit(10)
    )
    job_res = await db.execute(job_stmt)
    jobs = list(job_res.scalars().all())

    jobs_results = [
        {
            "id": j.id,
            "title": j.job_title,
            "department": j.department or "General",
            "location": j.location or "Plant",
            "is_active": getattr(j, "is_active", True)
        }
        for j in jobs
    ]

    # 3. Search Shortlists (roster name)
    roster_stmt = (
        select(ShortlistRoster)
        .where(func.lower(ShortlistRoster.name).like(pattern))
        .limit(10)
    )
    roster_res = await db.execute(roster_stmt)
    rosters = list(roster_res.scalars().all())

    shortlists_results = []
    for r in rosters:
        j_stmt = select(JobDescription).where(JobDescription.id == r.job_id)
        j_res = await db.execute(j_stmt)
        j_obj = j_res.scalar_one_or_none()

        count_stmt = select(func.count(ShortlistRosterItem.id)).where(ShortlistRosterItem.roster_id == r.id)
        c_res = await db.execute(count_stmt)
        c_count = c_res.scalar_one() or 0

        shortlists_results.append({
            "id": r.id,
            "name": r.name,
            "job_title": j_obj.job_title if j_obj else "Position",
            "candidate_count": c_count,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return {
        "applicants": applicants_results,
        "jobs": jobs_results,
        "shortlists": shortlists_results
    }
