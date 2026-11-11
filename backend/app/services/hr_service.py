from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.hr_schema import HRCreate, HRUpdate
from app.utils.auth import hash_password
from app.services.notification_service import create_notification
from app.repositories.hr_repository import HRRepository

async def create_hr_profile(db: AsyncSession, hr_in: HRCreate):
    email_lower = hr_in.email.strip().lower()
    hr_data = {
        "fullname": hr_in.fullname,
        "email": email_lower,
        "password": hash_password(hr_in.password),
        "role": "HR",
        "company_name": hr_in.company_name,
        "department": hr_in.department
    }

    new_hr = await HRRepository.create_hr(db, hr_data)

    # Trigger notification for Admin
    await create_notification(
        db=db,
        title="New HR Registration",
        message=f"{new_hr.fullname} has registered as HR for {new_hr.company_name}.",
        type="hr_registration",
        target_role="ADMIN"
    )

    return new_hr


async def get_hr_profile(db: AsyncSession, hr_id: int):
    return await HRRepository.get_hr_by_id(db, hr_id)


async def update_hr_profile(db: AsyncSession, hr_id: int, hr_update: HRUpdate):
    hr = await HRRepository.get_hr_by_id(db, hr_id)
    if not hr:
        return None

    update_data = hr_update.dict(exclude_unset=True)
    if "email" in update_data and update_data["email"]:
        new_email = update_data["email"].strip().lower()
        update_data["email"] = new_email
        if new_email != hr.email:
            from app.repositories.auth_repository import AuthRepository
            existing = await AuthRepository.get_raw_user_by_email(db, new_email)
            if existing and existing.id != hr_id:
                raise Exception("This email address is already in use by another account.")

    return await HRRepository.update_hr(db, hr, update_data)


async def get_total_candidates_count(db: AsyncSession):
    return await HRRepository.get_total_candidates_count(db)


async def get_total_resumes_count(db: AsyncSession):
    return await HRRepository.get_total_resumes_count(db)


async def get_application_stats(db: AsyncSession):
    # Get counts grouped by status
    db_stats = await HRRepository.get_application_stats_by_status(db)
    stats = {str(row[0]).upper(): row[1] for row in db_stats if row[0]}

    pending = stats.get("PENDING", 0)
    reviewed = stats.get("REVIEWED", 0) + stats.get("TECHNICAL INTERVIEW", 0) + stats.get("FINAL INTERVIEW", 0)
    accepted = stats.get("ACCEPTED", 0)
    rejected = stats.get("REJECTED", 0)
    archived = stats.get("ARCHIVED", 0)
    total_archived = rejected + archived
    average_score = await HRRepository.get_average_match_score(db)

    return {
        "pending": pending,
        "reviewed": reviewed,
        "accepted": accepted,
        "rejected": total_archived,
        "archived": archived,
        "raw_rejected": rejected,
        "total": pending + reviewed + accepted + total_archived,
        "average_score": average_score,
    }


def _build_skills_distribution(skills_rows: list, total_apps: int, colors: list[str]) -> list[dict]:
    """Compute normalized per-applicant skill counts matching manual tallying."""
    import re

    skill_counts: dict[str, int] = {}
    skill_labels: dict[str, str] = {}

    for raw_skills in skills_rows:
        if not raw_skills:
            continue
        if isinstance(raw_skills, list):
            tokens = [str(s).strip() for s in raw_skills if str(s).strip()]
        else:
            tokens = [s.strip() for s in re.split(r'[|,;•\n]+', str(raw_skills)) if s.strip()]

        seen_in_app: set[str] = set()
        for tok in tokens:
            key = tok.lower()
            if key in seen_in_app:
                continue
            seen_in_app.add(key)
            skill_counts[key] = skill_counts.get(key, 0) + 1
            if key not in skill_labels:
                skill_labels[key] = tok

    sorted_skills = sorted(skill_counts.items(), key=lambda kv: (-kv[1], skill_labels[kv[0]].lower()))
    denom = total_apps if total_apps > 0 else 1
    return [
        {
            "label": skill_labels[key],
            "value": count,
            "color": colors[idx % len(colors)],
            "percentage": f"{round((count / denom) * 100)}%",
        }
        for idx, (key, count) in enumerate(sorted_skills)
    ]


async def get_dashboard_trends(db: AsyncSession):
    from datetime import datetime, timedelta

    # 1. Weekly Trends (past 7 days)
    today = datetime.utcnow().date()
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]

    # Initialize dictionary with 0 counts
    daily_counts = {d: 0 for d in dates}

    # Query database
    start_date = datetime.combine(dates[0], datetime.min.time())
    db_result = await HRRepository.get_daily_application_counts(db, start_date)

    for row in db_result:
        row_date = row[0]
        if isinstance(row_date, str):
            try:
                row_date = datetime.strptime(row_date, "%Y-%m-%d").date()
            except Exception:
                pass
        elif hasattr(row_date, "date"):
            row_date = row_date.date()
        if row_date in daily_counts:
            daily_counts[row_date] = row[1]

    weekly_trends = []
    prev_count = None
    for d in dates:
        count = daily_counts[d]

        # Calculate growth compared to previous day
        if prev_count is None or prev_count == 0:
            growth = f"+{count * 100}%" if count > 0 else "+0%"
        else:
            diff = count - prev_count
            pct = int((diff / prev_count) * 100)
            growth = f"+{pct}%" if pct >= 0 else f"{pct}%"

        prev_count = count

        weekly_trends.append({
            "day": d.strftime("%a"),
            "date": d.strftime("%b %d"),
            "applications": count,
            "growth": growth
        })

    # 2. Department Distribution
    dept_data = await HRRepository.get_department_application_counts(db)
    total_apps = sum(row[1] for row in dept_data)

    # Premium colors list
    colors = ['#D60041', '#F43F5E', '#FDA4AF', '#3B82F6', '#8B5CF6', '#10B981']

    department_distribution = []
    for idx, row in enumerate(dept_data):
        dept_name = row[0]
        count = row[1]
        pct_val = round((count / total_apps) * 100) if total_apps > 0 else 0

        department_distribution.append({
            "label": dept_name,
            "value": count,
            "color": colors[idx % len(colors)],
            "percentage": f"{pct_val}%"
        })

    if not department_distribution:
        # If no real data, try to query all active jobs to populate some default departments with 0 counts
        distinct_depts = await HRRepository.get_distinct_departments(db)
        if distinct_depts:
            for idx, dept in enumerate(distinct_depts):
                department_distribution.append({
                    "label": dept,
                    "value": 0,
                    "color": colors[idx % len(colors)],
                    "percentage": "0%"
                })
        else:
            department_distribution = [
                { "label": "No Data", "value": 0, "color": "#E2E8F0", "percentage": "0%" }
            ]

    # 3. Applicants per Position Distribution
    pos_rows = await HRRepository.get_position_application_counts(db)
    pos_sorted = sorted(pos_rows, key=lambda r: (-int(r[1] or 0), str(r[0] or "").lower()))
    position_distribution = []
    pos_total = sum(int(r[1] or 0) for r in pos_sorted) or total_apps
    for idx, row in enumerate(pos_sorted):
        pos_name = row[0] or "Unspecified"
        count = int(row[1] or 0)
        avg_pos_score = round(float(row[2] or 0.0), 1)
        pct_val = round((count / pos_total) * 100) if pos_total > 0 else 0
        position_distribution.append({
            "label": pos_name,
            "value": count,
            "avg_score": avg_pos_score,
            "color": colors[idx % len(colors)],
            "percentage": f"{pct_val}%",
        })

    # 4. Skills Distribution & Overall Average Score
    skills_rows = await HRRepository.get_all_application_skills(db)
    skills_distribution = _build_skills_distribution(skills_rows, total_apps, colors)
    average_score = await HRRepository.get_average_match_score(db)

    return {
        "weekly_trends": weekly_trends,
        "department_distribution": department_distribution,
        "position_distribution": position_distribution,
        "skills_distribution": skills_distribution,
        "average_score": average_score,
        "total_applications": total_apps,
    }


async def build_hr_dashboard_export_data(db: AsyncSession) -> dict:
    """Collect unified HR Dashboard analytics + applicant records for CSV/PDF export."""
    from datetime import datetime
    from app.repositories.job_description_repository import JobDescriptionRepository
    from app.services import job_application_service

    stats = await get_application_stats(db)
    trends = await get_dashboard_trends(db)
    active_jobs = await JobDescriptionRepository.get_all_active(db, include_inactive=False)
    applications = await job_application_service.get_all_applications(db)

    applicants = []
    for app in applications:
        raw_skills = app.skills or []
        skills_text = (
            ", ".join(str(s).strip() for s in raw_skills if str(s).strip())
            if isinstance(raw_skills, list)
            else str(raw_skills or "")
        )
        job_obj = getattr(app, "job", None)
        role_title = (getattr(job_obj, "job_title", None) if job_obj else None) or app.job_title or "Unspecified"
        dept_name = (getattr(job_obj, "department", None) if job_obj else None) or "General"
        score_val = round(float(app.match_score or 0.0), 1)
        applied_date = app.created_at.strftime("%Y-%m-%d") if getattr(app, "created_at", None) else "N/A"
        applicants.append({
            "id": app.id,
            "candidate_name": app.candidate_name or "Applicant",
            "candidate_email": app.candidate_email or "",
            "preferred_role": role_title,
            "department": dept_name,
            "status": (app.status or "PENDING").upper(),
            "match_score": score_val,
            "skills_score": round(float(app.skills_score or 0.0), 1),
            "experience_score": round(float(app.experience_score or 0.0), 1),
            "education_score": round(float(app.education_score or 0.0), 1),
            "skills_text": skills_text,
            "applied_date": applied_date,
            "location": app.location or "N/A",
        })

    return {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "summary": {
            "total_applications": len(applicants) if applicants else stats.get("total", 0),
            "active_positions": len(active_jobs),
            "average_score": stats.get("average_score", trends.get("average_score", 0.0)),
            "pending": stats.get("pending", 0),
            "reviewed": stats.get("reviewed", 0),
            "accepted": stats.get("accepted", 0),
            "rejected": stats.get("rejected", 0),
        },
        "position_distribution": trends.get("position_distribution", []),
        "department_distribution": trends.get("department_distribution", []),
        "skills_distribution": trends.get("skills_distribution", []),
        "applicants": applicants,
    }


import sys
hr_service = sys.modules[__name__]

