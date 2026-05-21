from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.hr import HR
from app.schemas.hr_schema import HRCreate, HRUpdate
from app.utils.auth import hash_password
from app.services.notification_service import create_notification

async def create_hr_profile(db: AsyncSession, hr_in: HRCreate):
    email_lower = hr_in.email.strip().lower()
    new_hr = HR(
        fullname=hr_in.fullname,
        email=email_lower,
        password=hash_password(hr_in.password),
        role="HR",
        company_name=hr_in.company_name,
        department=hr_in.department
    )
    
    db.add(new_hr)
    await db.commit()
    await db.refresh(new_hr)
    
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
    result = await db.execute(select(HR).where(HR.id == hr_id))
    return result.scalar_one_or_none()

async def update_hr_profile(db: AsyncSession, hr_id: int, hr_update: HRUpdate):
    result = await db.execute(select(HR).where(HR.id == hr_id))
    hr = result.scalar_one_or_none()
    if not hr:
        return None
    
    update_data = hr_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(hr, key, value)
    
    await db.commit()
    await db.refresh(hr)
    return hr

async def get_total_candidates_count(db: AsyncSession):
    from app.models.candidate import Candidate
    from sqlalchemy import func
    result = await db.execute(select(func.count(Candidate.id)))
    return result.scalar()

async def get_total_resumes_count(db: AsyncSession):
    from app.models.job_application import JobApplication
    from sqlalchemy import func
    result = await db.execute(select(func.count(JobApplication.id)))
    return result.scalar()

async def get_application_stats(db: AsyncSession):
    from app.models.job_application import JobApplication
    from sqlalchemy import func
    
    # Get counts grouped by status
    result = await db.execute(select(JobApplication.status, func.count(JobApplication.id)).group_by(JobApplication.status))
    stats = {row[0]: row[1] for row in result.all()}
    
    return {
        "pending": stats.get("PENDING", 0),
        "reviewed": stats.get("REVIEWED", 0),
        "accepted": stats.get("ACCEPTED", 0),
        "rejected": stats.get("REJECTED", 0)
    }

async def get_dashboard_trends(db: AsyncSession):
    from app.models.job_application import JobApplication
    from app.models.job_description import JobDescription
    from sqlalchemy import func, cast, Date
    from datetime import datetime, timedelta

    # 1. Weekly Trends (past 7 days)
    today = datetime.utcnow().date()
    dates = [today - timedelta(days=i) for i in range(6, -1, -1)]
    
    # Initialize dictionary with 0 counts
    daily_counts = {d: 0 for d in dates}
    
    # Query database
    start_date = datetime.combine(dates[0], datetime.min.time())
    result = await db.execute(
        select(
            cast(JobApplication.created_at, Date),
            func.count(JobApplication.id)
        )
        .where(JobApplication.created_at >= start_date)
        .group_by(cast(JobApplication.created_at, Date))
    )
    
    for row in result.all():
        row_date = row[0]
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
    dept_result = await db.execute(
        select(
            JobDescription.department,
            func.count(JobApplication.id)
        )
        .join(JobApplication, JobApplication.job_id == JobDescription.id)
        .group_by(JobDescription.department)
    )
    
    dept_data = dept_result.all()
    total_apps = sum(row[1] for row in dept_data)
    
    # Premium colors list
    colors = ['#D60041', '#F43F5E', '#FDA4AF', '#3B82F6', '#8B5CF6', '#10B981']
    
    department_distribution = []
    for idx, row in enumerate(dept_data):
        dept_name = row[0]
        count = row[1]
        pct_val = int((count / total_apps) * 100) if total_apps > 0 else 0
        
        department_distribution.append({
            "label": dept_name,
            "value": count,
            "color": colors[idx % len(colors)],
            "percentage": f"{pct_val}%"
        })
        
    if not department_distribution:
        # If no real data, try to query all active jobs to populate some default departments with 0 counts
        active_jobs_result = await db.execute(select(JobDescription.department).distinct())
        distinct_depts = [r[0] for r in active_jobs_result.all()]
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
        
    return {
        "weekly_trends": weekly_trends,
        "department_distribution": department_distribution,
        "total_applications": total_apps
    }