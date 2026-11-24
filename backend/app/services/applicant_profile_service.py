import logging
import re
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
from app.models.user import User
from app.services.status_management_service import normalize_status
from app.services.requirement_rules import extract_criterion_status, STATUS_MANUAL_REVIEW

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
    raw_identifier = (email or "").strip()
    clean_email = raw_identifier.lower()

    # Log access for Data Privacy Act compliance
    await log_applicant_profile_access(db, clean_email, accessed_by)

    # Resolve candidate identity by user_id or any email (account email, contact email, resume email)
    matched_user_id: Optional[int] = None
    account_email: Optional[str] = None

    if raw_identifier.isdigit():
        matched_user_id = int(raw_identifier)
    elif clean_email.startswith("uid_") and clean_email[4:].isdigit():
        matched_user_id = int(clean_email[4:])
    else:
        u_res = await db.execute(
            select(User.id, User.email).where(func.lower(User.email) == clean_email)
        )
        u_row = u_res.first()
        if u_row:
            matched_user_id = u_row[0]
            account_email = u_row[1]

    # 1. Fetch initial matching applications by user_id or any email column
    email_match_cond = or_(
        func.lower(JobApplication.candidate_email) == clean_email,
        func.lower(JobApplication.contact_email) == clean_email,
        func.lower(JobApplication.resume_email) == clean_email,
    )
    if matched_user_id is not None:
        initial_cond = or_(
            JobApplication.user_id == matched_user_id,
            email_match_cond,
        )
    else:
        initial_cond = email_match_cond

    stmt = (
        select(JobApplication)
        .where(initial_cond)
        .order_by(JobApplication.created_at.desc())
    )
    res = await db.execute(stmt)
    applications = list(res.scalars().all())

    if not applications:
        return None

    # If any matched application has a user_id, unify all applications for that user_id
    # so the person is never split or lost when account email and resume/contact email differ.
    if matched_user_id is None:
        for a in applications:
            if getattr(a, "user_id", None) is not None:
                matched_user_id = a.user_id
                break

    if matched_user_id is not None:
        if not account_email:
            u_res = await db.execute(select(User.email).where(User.id == matched_user_id))
            account_email = u_res.scalar_one_or_none()
        known_emails_for_query = {clean_email}
        if account_email:
            known_emails_for_query.add(account_email.strip().lower())
        for a in applications:
            for em in (a.candidate_email, getattr(a, "contact_email", None), getattr(a, "resume_email", None)):
                if em and em.strip():
                    known_emails_for_query.add(em.strip().lower())

        unified_stmt = (
            select(JobApplication)
            .where(
                or_(
                    JobApplication.user_id == matched_user_id,
                    and_(
                        JobApplication.user_id.is_(None),
                        or_(
                            func.lower(JobApplication.candidate_email).in_(known_emails_for_query),
                            func.lower(JobApplication.contact_email).in_(known_emails_for_query),
                            func.lower(JobApplication.resume_email).in_(known_emails_for_query),
                        ),
                    ),
                )
            )
            .order_by(JobApplication.created_at.desc())
        )
        unified_res = await db.execute(unified_stmt)
        applications = list(unified_res.scalars().all())

    primary_app = applications[0]
    chosen_contact_email = getattr(primary_app, "contact_email", None) or primary_app.candidate_email
    extracted_resume_email = getattr(primary_app, "resume_email", None)
    if not extracted_resume_email:
        for a in applications:
            if getattr(a, "resume_email", None):
                extracted_resume_email = a.resume_email
                break

    # Collect all known emails for this person (for notes lookup)
    known_emails = {clean_email}
    if account_email and account_email.strip():
        known_emails.add(account_email.strip().lower())
    for a in applications:
        for em in (a.candidate_email, getattr(a, "contact_email", None), getattr(a, "resume_email", None)):
            if em and em.strip():
                known_emails.add(em.strip().lower())

    # 2. Extract applicant details (show chosen HR contact email, plus account_email & resume_email)
    candidate_summary = {
        "user_id": matched_user_id,
        "applicant_id": matched_user_id,
        "name": primary_app.candidate_name or chosen_contact_email or "Applicant",
        "email": chosen_contact_email,
        "candidate_name": primary_app.candidate_name or chosen_contact_email or "Applicant",
        "candidate_email": chosen_contact_email,
        "contact_email": chosen_contact_email,
        "account_email": account_email,
        "resume_email": extracted_resume_email,
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
            "skills_score": app.skills_score,
            "experience_score": app.experience_score,
            "education_score": app.education_score,
            "certifications_score": app.certifications_score,
            "skills_reason": app.skills_reason,
            "experience_reason": app.experience_reason,
            "education_reason": app.education_reason,
            "certifications_reason": getattr(app, "certifications_reason", None),
            "skills_status": extract_criterion_status(app.skills_reason),
            "experience_status": extract_criterion_status(app.experience_reason),
            "education_status": extract_criterion_status(app.education_reason),
            "certifications_status": extract_criterion_status(getattr(app, "certifications_reason", None)),
            "education_needs_manual_review": extract_criterion_status(app.education_reason) == STATUS_MANUAL_REVIEW,
            "required_degree": getattr(app, "required_degree", None),
            "candidate_degree": getattr(app, "candidate_degree", None),
            "required_certifications": getattr(app, "required_certifications", None),
            "candidate_certifications": getattr(app, "candidate_certifications", None),
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

        interviewer_obj = getattr(item, "interviewer", None)
        interviewer_name = (
            (interviewer_obj.fullname or interviewer_obj.email)
            if interviewer_obj
            else None
        )

        interviews_data.append({
            "id": item.id,
            "title": item.title,
            "start_time": item.start_time.isoformat() if item.start_time else None,
            "end_time": item.end_time.isoformat() if item.end_time else None,
            "interviewer_name": interviewer_name,
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

    # 6. Fetch HR Notes across all emails associated with this candidate
    notes_stmt = (
        select(HRCandidateNote)
        .where(func.lower(HRCandidateNote.candidate_email).in_(known_emails))
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

    # 7. Generate top summary strip + multi-application & anonymized repeat-applicant flags
    from app.services.retention_service import is_application_active, has_previous_anonymized_application

    active_apps_list = [
        {
            "id": a["id"],
            "job_id": a["job_id"],
            "job_title": a["job_title"],
            "status": a["status"],
        }
        for a in apps_data
        if is_application_active(a["status"])
    ]
    active_applications_count = len(active_apps_list)
    other_active_count = max(0, active_applications_count - 1)
    other_active_flag = (
        f"This applicant has {other_active_count} other active {'application' if other_active_count == 1 else 'applications'}"
        if other_active_count > 0
        else None
    )

    # Repeat-applicant detection strictly from salted one-way email_hash (zero PII exposed)
    repeat_anon = await has_previous_anonymized_application(
        db=db,
        email=account_email or chosen_contact_email,
        exclude_user_id=matched_user_id,
    )
    previous_application_flag = (
        "Previous application on record (anonymized)" if repeat_anon else None
    )

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
        "shortlisted_count": shortlisted_count,
        "active_applications_count": active_applications_count,
        "active_applications": active_apps_list,
        "other_active_count": other_active_count,
        "other_active_flag": other_active_flag,
        "has_previous_anonymized_application": repeat_anon,
        "previous_application_flag": previous_application_flag,
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

def _split_words(text: str) -> List[str]:
    return [w for w in re.split(r"[\s,;/().\-–—]+", (text or "").lower().strip()) if w]


def _get_job_search_rank(job: JobDescription, raw_query: str) -> Optional[int]:
    query = (raw_query or "").lower().strip()
    if not query:
        return 0

    title = (job.job_title or "").lower().strip()
    title_words = _split_words(title)

    if title.startswith(query):
        return 0
    if any(w.startswith(query) for w in title_words):
        return 1

    # Single-letter search: only match jobs whose title (or a word in the title) starts with that letter
    if len(query) == 1:
        return None

    dept = (job.department or "").lower().strip()
    dept_words = _split_words(dept)
    raw_skills = getattr(job, "skills_requirements", "") or ""
    if isinstance(raw_skills, list):
        skills = ", ".join(str(s) for s in raw_skills).lower()
    else:
        skills = str(raw_skills).lower()
    skill_tokens = [s.strip() for s in re.split(r"[,;\n•]+", skills) if s.strip()]

    if query in title:
        return 2

    if (
        dept.startswith(query)
        or any(w.startswith(query) for w in dept_words)
        or any(s.startswith(query) for s in skill_tokens)
    ):
        return 3

    if len(query) == 2:
        return None

    loc = (job.location or "").lower().strip()
    desc = (getattr(job, "description", "") or "").lower()

    if query in dept or query in skills:
        return 4
    if query in loc:
        return 5
    if query in desc:
        return 6

    return None


def _get_candidate_search_rank(
    name: str,
    email: str,
    job_title: str,
    raw_query: str
) -> Optional[int]:
    query = (raw_query or "").lower().strip()
    if not query:
        return 0

    clean_name = (name or "").lower().strip()
    name_words = [w for w in _split_words(clean_name) if len(w) > 1 or w == query]
    all_name_tokens = _split_words(clean_name)

    if clean_name.startswith(query):
        return 0
    # Match any word in candidate name (ignoring single-letter middle initials like "T." unless the whole first/last name starts with query)
    if any(w.startswith(query) for w in name_words) or any(w.startswith(query) for w in all_name_tokens if len(w) >= 2):
        return 1

    # Single-letter search (e.g. "J"): strictly match candidates whose name (or a name word like "John", "James") starts with that letter
    if len(query) == 1:
        return None

    email_local = ((email or "").lower().split("@")[0]).strip()
    role = (job_title or "").lower().strip()
    role_words = _split_words(role)

    if query in clean_name:
        return 2
    if email_local.startswith(query):
        return 3
    if role.startswith(query) or any(w.startswith(query) for w in role_words):
        return 4

    if len(query) == 2:
        return None

    if query in email_local:
        return 5
    if query in role:
        return 6

    return None


async def universal_search_hr(
    db: AsyncSession,
    query: str
) -> Dict[str, Any]:
    """
    Universal Search for HR:
    Ranks Jobs (using Candidate job search ranking) and Candidates/Applicants (prefix & word-prefix aware),
    plus Shortlist Rosters.
    """
    q = query.strip()
    if not q:
        return {"applicants": [], "jobs": [], "shortlists": []}

    q_lower = q.lower()
    pattern = f"%{q_lower}%"

    # 1. Search & Rank Jobs (mirrors Candidate job search getJobSearchRank)
    job_stmt = select(JobDescription)
    job_res = await db.execute(job_stmt)
    all_jobs = list(job_res.scalars().all())

    # Count applicants per job
    counts_stmt = select(JobApplication.job_id, func.count(JobApplication.id)).group_by(JobApplication.job_id)
    counts_res = await db.execute(counts_stmt)
    job_app_counts = {row[0]: row[1] for row in counts_res.all() if row[0] is not None}

    scored_jobs = []
    for j in all_jobs:
        rank = _get_job_search_rank(j, q)
        if rank is not None:
            scored_jobs.append((rank, (j.job_title or "").lower(), j))

    scored_jobs.sort(key=lambda item: (item[0], item[1]))

    jobs_results = [
        {
            "id": j.id,
            "job_id": j.id,
            "title": j.job_title,
            "job_title": j.job_title,
            "department": j.department or "General",
            "location": j.location or "Plant",
            "applicant_count": job_app_counts.get(j.id, 0),
            "is_active": getattr(j, "is_active", True)
        }
        for _, _, j in scored_jobs[:10]
    ]

    # 2. Search & Rank Candidates / Applicants (deduplicated by user_id first, then email)
    app_stmt = (
        select(JobApplication)
        .where(
            or_(
                func.lower(JobApplication.candidate_name).like(pattern),
                func.lower(JobApplication.candidate_email).like(pattern),
                func.lower(JobApplication.contact_email).like(pattern),
                func.lower(JobApplication.resume_email).like(pattern),
                func.lower(JobApplication.job_title).like(pattern)
            )
        )
        .order_by(JobApplication.created_at.desc())
    )
    app_res = await db.execute(app_stmt)
    apps = list(app_res.scalars().all())

    job_title_map = {j.id: j.job_title for j in all_jobs}

    scored_applicants = []
    seen_people = set()
    seen_emails = set()
    for a in apps:
        app_uid = getattr(a, "user_id", None)
        email_key = (getattr(a, "contact_email", None) or a.candidate_email or "").lower().strip()
        person_key = f"uid_{app_uid}" if app_uid else email_key
        if (person_key and person_key in seen_people) or (email_key and email_key in seen_emails):
            continue
        resolved_job_title = a.job_title or job_title_map.get(a.job_id, "Position") or "Position"
        candidate_emails = [
            em for em in (
                getattr(a, "contact_email", None),
                a.candidate_email,
                getattr(a, "resume_email", None),
            )
            if em
        ] or [""]
        ranks = [
            r for r in (
                _get_candidate_search_rank(a.candidate_name or "", em, resolved_job_title, q)
                for em in candidate_emails
            )
            if r is not None
        ]
        rank = min(ranks) if ranks else None
        if rank is not None:
            if person_key:
                seen_people.add(person_key)
            for em in candidate_emails:
                if em.strip():
                    seen_emails.add(em.strip().lower())
            display_email = getattr(a, "contact_email", None) or a.candidate_email
            scored_applicants.append((
                rank,
                (a.candidate_name or "").lower(),
                {
                    "id": a.id,
                    "user_id": app_uid,
                    "applicant_id": app_uid,
                    "name": a.candidate_name,
                    "email": display_email,
                    "contact_email": display_email,
                    "resume_email": getattr(a, "resume_email", None),
                    "job_title": resolved_job_title,
                    "position": resolved_job_title,
                    "status": normalize_status(a.status),
                    "match_score": a.match_score,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                }
            ))

    scored_applicants.sort(key=lambda item: (item[0], item[1]))
    applicants_results = [item[2] for item in scored_applicants[:10]]

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
        roster_name = (r.name or "").lower().strip()
        roster_words = _split_words(roster_name)
        if len(q_lower) == 1 and not (
            roster_name.startswith(q_lower) or any(w.startswith(q_lower) for w in roster_words)
        ):
            continue

        j_title = job_title_map.get(r.job_id, "Position")

        count_stmt = select(func.count(ShortlistRosterItem.id)).where(ShortlistRosterItem.roster_id == r.id)
        c_res = await db.execute(count_stmt)
        c_count = c_res.scalar_one() or 0

        shortlists_results.append({
            "id": r.id,
            "name": r.name,
            "job_title": j_title,
            "candidate_count": c_count,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })

    return {
        "jobs": jobs_results,
        "applicants": applicants_results,
        "shortlists": shortlists_results
    }
