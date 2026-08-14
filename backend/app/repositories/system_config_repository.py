from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from app.models.system_config import SystemConfig, FormTemplate
from app.models.user import User
from app.models.job_description import JobDescription
from app.models.job_application import JobApplication
from app.models.audit_log import AuditLog


"""Database operations for system configuration."""

# ─── SystemConfig CRUD ────────────────────────────────────────────────────

async def get_all_configs(db: AsyncSession) -> List[SystemConfig]:
    result = await db.execute(select(SystemConfig).order_by(SystemConfig.category, SystemConfig.key))
    return result.scalars().all()

async def get_configs_by_category(db: AsyncSession, category: str) -> List[SystemConfig]:
    result = await db.execute(
        select(SystemConfig).where(SystemConfig.category == category).order_by(SystemConfig.key)
    )
    return result.scalars().all()

async def get_config_by_key(db: AsyncSession, key: str) -> Optional[SystemConfig]:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    return result.scalar_one_or_none()

async def upsert_config(db: AsyncSession, key: str, value: str, category: str,
                        description: str = None, updated_by: int = None) -> SystemConfig:
    existing = await SystemConfigRepository.get_config_by_key(db, key)
    if existing:
        existing.value = value
        existing.description = description or existing.description
        existing.updated_by = updated_by
        existing.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        new_config = SystemConfig(
            key=key, value=value, category=category,
            description=description, updated_by=updated_by
        )
        db.add(new_config)
        await db.commit()
        await db.refresh(new_config)
        return new_config

async def delete_config(db: AsyncSession, key: str) -> bool:
    result = await db.execute(delete(SystemConfig).where(SystemConfig.key == key))
    await db.commit()
    return result.rowcount > 0

# ─── User Role Management ─────────────────────────────────────────────────

async def update_user_role(db: AsyncSession, user_id: int, new_role: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    return user

async def get_users_by_role(db: AsyncSession, role: str) -> List[User]:
    result = await db.execute(select(User).where(User.role == role))
    return result.scalars().all()

# ─── Form Template CRUD ───────────────────────────────────────────────────

async def get_all_templates(db: AsyncSession) -> List[FormTemplate]:
    result = await db.execute(select(FormTemplate).order_by(FormTemplate.created_at.desc()))
    return result.scalars().all()

async def get_template_by_id(db: AsyncSession, template_id: int) -> Optional[FormTemplate]:
    result = await db.execute(select(FormTemplate).where(FormTemplate.id == template_id))
    return result.scalar_one_or_none()

async def create_template(db: AsyncSession, data: dict) -> FormTemplate:
    template = FormTemplate(**data)
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template

async def update_template(db: AsyncSession, template_id: int, data: dict) -> Optional[FormTemplate]:
    result = await db.execute(select(FormTemplate).where(FormTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        return None
    for key, value in data.items():
        setattr(template, key, value)
    template.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(template)
    return template

async def delete_template(db: AsyncSession, template_id: int) -> bool:
    result = await db.execute(delete(FormTemplate).where(FormTemplate.id == template_id))
    await db.commit()
    return result.rowcount > 0

# ─── System Performance & Usage Stats ─────────────────────────────────────

async def get_performance_stats(db: AsyncSession) -> Dict[str, Any]:
    # Total users
    total_users_q = await db.execute(select(func.count(User.id)))
    total_users = total_users_q.scalar() or 0

    # Active vs archived
    active_users_q = await db.execute(
        select(func.count(User.id)).where(User.is_archived == False)
    )
    active_users = active_users_q.scalar() or 0
    archived_users = total_users - active_users

    # Users by role
    role_counts = {}
    for role in ["ADMIN", "HR", "CANDIDATE"]:
        count_q = await db.execute(
            select(func.count(User.id)).where(User.role == role)
        )
        role_counts[role] = count_q.scalar() or 0

    # Job stats
    total_jobs_q = await db.execute(select(func.count(JobDescription.id)))
    total_jobs = total_jobs_q.scalar() or 0

    active_jobs_q = await db.execute(
        select(func.count(JobDescription.id)).where(JobDescription.is_active == True)
    )
    active_jobs = active_jobs_q.scalar() or 0
    inactive_jobs = total_jobs - active_jobs

    # Application stats
    total_apps_q = await db.execute(select(func.count(JobApplication.id)))
    total_apps = total_apps_q.scalar() or 0

    app_statuses = {}
    for status_val in ["PENDING", "REVIEWED", "ACCEPTED", "REJECTED", "TECHNICAL INTERVIEW", "FINAL INTERVIEW"]:
        count_q = await db.execute(
            select(func.count(JobApplication.id)).where(JobApplication.status == status_val)
        )
        app_statuses[status_val] = count_q.scalar() or 0

    pending = app_statuses.get("PENDING", 0)
    reviewed = app_statuses.get("REVIEWED", 0)
    accepted = app_statuses.get("ACCEPTED", 0)
    rejected = app_statuses.get("REJECTED", 0)

    # Average match score
    avg_score_q = await db.execute(
        select(func.avg(JobApplication.match_score)).where(JobApplication.match_score.isnot(None))
    )
    avg_match = avg_score_q.scalar()
    avg_match_score = round(avg_match, 1) if avg_match else None

    # Total audit logs
    audit_count_q = await db.execute(select(func.count(AuditLog.id)))
    total_audit = audit_count_q.scalar() or 0

    # Recent logins (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_logins_q = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "SIGN_IN",
            AuditLog.created_at >= seven_days_ago
        )
    )
    recent_logins = recent_logins_q.scalar() or 0

    # Applications trend (last 7 days)
    applications_trend = []
    for i in range(6, -1, -1):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_count_q = await db.execute(
            select(func.count(JobApplication.id)).where(
                JobApplication.created_at >= day_start,
                JobApplication.created_at < day_end
            )
        )
        applications_trend.append({
            "date": day_start.strftime("%b %d"),
            "count": day_count_q.scalar() or 0
        })

    # AI Analysis count
    ai_analysis_q = await db.execute(
        select(func.count(JobApplication.id)).where(JobApplication.ai_powered == True)
    )
    ai_analysis_count = ai_analysis_q.scalar() or 0

    # Top Jobs
    top_jobs_q = await db.execute(
        select(
            JobDescription.job_title,
            func.count(JobApplication.id).label('app_count')
        ).outerjoin(JobApplication, JobDescription.id == JobApplication.job_id)
        .group_by(JobDescription.job_title)
        .order_by(func.count(JobApplication.id).desc())
        .limit(3)
    )
    top_jobs = [{"title": row.job_title, "count": row.app_count} for row in top_jobs_q.all()]

    # Conversion rate (Accepted / Total)
    conversion_rate = round((accepted / total_apps * 100), 1) if total_apps > 0 else 0.0

    # Total Data Points (approx load based on key tables)
    data_points = total_users + total_jobs + total_apps + total_audit

    return {
        "total_users": total_users,
        "active_users": active_users,
        "archived_users": archived_users,
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "inactive_jobs": inactive_jobs,
        "total_applications": total_apps,
        "pending_applications": pending,
        "reviewed_applications": reviewed,
        "accepted_applications": accepted,
        "rejected_applications": rejected,
        "total_audit_logs": total_audit,
        "recent_logins": recent_logins,
        "avg_match_score": avg_match_score,
        "ai_analysis_count": ai_analysis_count,
        "data_points": data_points,
        "conversion_rate": conversion_rate,
        "users_by_role": role_counts,
        "applications_by_status": app_statuses,
        "applications_trend": applications_trend,
        "top_jobs": top_jobs,
    }


class SystemConfigRepository:
    get_all_configs = staticmethod(get_all_configs)
    get_configs_by_category = staticmethod(get_configs_by_category)
    get_config_by_key = staticmethod(get_config_by_key)
    upsert_config = staticmethod(upsert_config)
    delete_config = staticmethod(delete_config)
    update_user_role = staticmethod(update_user_role)
    get_users_by_role = staticmethod(get_users_by_role)
    get_all_templates = staticmethod(get_all_templates)
    get_template_by_id = staticmethod(get_template_by_id)
    create_template = staticmethod(create_template)
    update_template = staticmethod(update_template)
    delete_template = staticmethod(delete_template)
    get_performance_stats = staticmethod(get_performance_stats)
