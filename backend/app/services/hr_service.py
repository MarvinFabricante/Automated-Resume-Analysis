from sqlalchemy.ext.asyncio import AsyncSession
from app.models.hr import HR
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
    return await HRRepository.update_hr(db, hr, update_data)

async def get_total_candidates_count(db: AsyncSession):
    return await HRRepository.get_total_candidates_count(db)

async def get_total_resumes_count(db: AsyncSession):
    return await HRRepository.get_total_resumes_count(db)

async def get_application_stats(db: AsyncSession):
    # Get counts grouped by status
    db_stats = await HRRepository.get_application_stats_by_status(db)
    stats = {row[0]: row[1] for row in db_stats}
    
    return {
        "pending": stats.get("PENDING", 0),
        "reviewed": stats.get("REVIEWED", 0),
        "accepted": stats.get("ACCEPTED", 0),
        "rejected": stats.get("REJECTED", 0)
    }

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
        pct_val = int((count / total_apps) * 100) if total_apps > 0 else 0
        
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
        
    return {
        "weekly_trends": weekly_trends,
        "department_distribution": department_distribution,
        "total_applications": total_apps
    }