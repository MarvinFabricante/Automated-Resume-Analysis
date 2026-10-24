from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete, text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.models.system_config import SystemConfig, FormTemplate
from app.models.user import User
from app.models.job_description import JobDescription
from app.models.job_application import JobApplication
from app.models.audit_log import AuditLog
from app.utils.redis_client import redis_tx_manager
from app.utils.cache import get_cache, set_cache, delete_cache, clear_cache_pattern

logger = logging.getLogger(__name__)

"""Database operations for system configuration with Redis-first architecture."""

# ─── SystemConfig CRUD ────────────────────────────────────────────────────

async def get_all_configs(db: AsyncSession) -> List[SystemConfig]:
    """Get all configs (checks Redis cache first)."""
    cache_key = "sys_config:all"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(SystemConfig).order_by(SystemConfig.category, SystemConfig.key))
    configs = result.scalars().all()
    await set_cache(cache_key, configs, ttl=1800)
    return configs


async def get_configs_by_category(db: AsyncSession, category: str) -> List[SystemConfig]:
    """Get configs by category (checks Redis cache first)."""
    cache_key = f"sys_config:cat:{category}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(
        select(SystemConfig).where(SystemConfig.category == category).order_by(SystemConfig.key)
    )
    configs = result.scalars().all()
    await set_cache(cache_key, configs, ttl=1800)
    return configs


async def get_config_by_key(db: AsyncSession, key: str) -> Optional[SystemConfig]:
    """Get config by key (checks Redis cache first)."""
    cache_key = f"sys_config:key:{key}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
    config = result.scalar_one_or_none()
    if config:
        await set_cache(cache_key, config, ttl=1800)
    return config


async def upsert_config(
    db: AsyncSession, key: str, value: str, category: str,
    description: str = None, updated_by: int = None
) -> SystemConfig:
    """Upsert config (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="system_config",
        action="UPSERT",
        payload={"key": key, "value": value, "category": category},
    )
    try:
        query_res = await db.execute(select(SystemConfig).where(SystemConfig.key == key))
        existing = query_res.scalar_one_or_none()
        if existing:
            existing.value = value
            existing.description = description or existing.description
            existing.updated_by = updated_by
            existing.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(existing)
            res = existing
        else:
            new_config = SystemConfig(
                key=key, value=value, category=category,
                description=description, updated_by=updated_by
            )
            db.add(new_config)
            await db.commit()
            await db.refresh(new_config)
            res = new_config

        await redis_tx_manager.commit_transaction(tx_id, {"key": key, "value": value})

        await clear_cache_pattern("sys_config:")
        return res
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] upsert_config failed: {e}")
        raise


async def delete_config(db: AsyncSession, key: str) -> bool:
    """Delete config (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="system_config",
        action="DELETE",
        payload={"key": key},
    )
    try:
        result = await db.execute(delete(SystemConfig).where(SystemConfig.key == key))
        await db.commit()
        success = result.rowcount > 0

        await redis_tx_manager.commit_transaction(tx_id, {"key": key, "deleted": success})

        await clear_cache_pattern("sys_config:")
        return success
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] delete_config failed: {e}")
        raise


# ─── User Role Management ─────────────────────────────────────────────────

async def update_user_role(db: AsyncSession, user_id: int, new_role: str) -> Optional[User]:
    """Update user role (Redis-first transaction)."""
    new_role = new_role.upper()
    tx_id = await redis_tx_manager.stage_transaction(
        target="user_role",
        action="UPDATE_ROLE",
        payload={"user_id": user_id, "new_role": new_role},
    )
    try:
        result = await db.execute(text("SELECT id, email, role FROM users WHERE id = :uid"), {"uid": user_id})
        row = result.fetchone()
        if not row:
            await redis_tx_manager.fail_transaction(tx_id, "User not found")
            return None

        email = (row.email or "").strip().lower()

        # Ensure child table entry exists for the polymorphic role
        if new_role == "HR":
            await db.execute(
                text("INSERT INTO hr_staffs (id, company_name) VALUES (:uid, 'Company') ON CONFLICT (id) DO NOTHING"),
                {"uid": user_id}
            )
        elif new_role == "CANDIDATE":
            await db.execute(
                text("INSERT INTO candidates (id, experience_years) VALUES (:uid, 0) ON CONFLICT (id) DO NOTHING"),
                {"uid": user_id}
            )

        # Update users role directly via SQL
        await db.execute(
            text("UPDATE users SET role = :new_role WHERE id = :uid"),
            {"new_role": new_role, "uid": user_id}
        )
        await db.commit()
        db.expire_all()

        # Re-fetch updated user
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()

        await redis_tx_manager.commit_transaction(tx_id, {"user_id": user_id, "new_role": new_role})

        await delete_cache(f"user:id:{user_id}")
        if email:
            await delete_cache(f"user:email:{email}")
            await clear_cache_pattern(f"user:email_role:{email}")
        await clear_cache_pattern("users:")
        await clear_cache_pattern("admin_users")
        await clear_cache_pattern("admin:stats")

        return user
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_user_role failed: {e}")
        raise


async def get_users_by_role(db: AsyncSession, role: str) -> List[User]:
    """Get users by role (checks Redis cache first)."""
    cache_key = f"users:by_role:{role}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(User).where(User.role == role))
    users = result.scalars().all()
    await set_cache(cache_key, users, ttl=600)
    return users


# ─── Form Template CRUD ───────────────────────────────────────────────────

async def get_all_templates(db: AsyncSession) -> List[FormTemplate]:
    """Get all templates (checks Redis cache first)."""
    cache_key = "templates:all"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(FormTemplate).order_by(FormTemplate.created_at.desc()))
    templates = result.scalars().all()
    await set_cache(cache_key, templates, ttl=600)
    return templates


async def get_template_by_id(db: AsyncSession, template_id: int) -> Optional[FormTemplate]:
    """Get template by ID (checks Redis cache first)."""
    cache_key = f"template:id:{template_id}"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    result = await db.execute(select(FormTemplate).where(FormTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if template:
        await set_cache(cache_key, template, ttl=600)
    return template


async def create_template(db: AsyncSession, data: dict) -> FormTemplate:
    """Create template (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="form_template",
        action="CREATE",
        payload=data,
    )
    try:
        template = FormTemplate(**data)
        db.add(template)
        await db.commit()
        await db.refresh(template)

        await redis_tx_manager.commit_transaction(tx_id, {"id": template.id})

        await clear_cache_pattern("templates:")
        return template
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] create_template failed: {e}")
        raise


async def update_template(db: AsyncSession, template_id: int, data: dict) -> Optional[FormTemplate]:
    """Update template (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="form_template",
        action="UPDATE",
        payload={"id": template_id, **data},
    )
    try:
        result = await db.execute(select(FormTemplate).where(FormTemplate.id == template_id))
        template = result.scalar_one_or_none()
        if not template:
            await redis_tx_manager.fail_transaction(tx_id, "Template not found")
            return None
        for key, value in data.items():
            setattr(template, key, value)
        template.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(template)

        await redis_tx_manager.commit_transaction(tx_id, {"id": template.id})

        await delete_cache(f"template:id:{template_id}")
        await clear_cache_pattern("templates:")
        return template
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] update_template failed: {e}")
        raise


async def delete_template(db: AsyncSession, template_id: int) -> bool:
    """Delete template (Redis-first transaction)."""
    tx_id = await redis_tx_manager.stage_transaction(
        target="form_template",
        action="DELETE",
        payload={"id": template_id},
    )
    try:
        result = await db.execute(delete(FormTemplate).where(FormTemplate.id == template_id))
        await db.commit()
        success = result.rowcount > 0

        await redis_tx_manager.commit_transaction(tx_id, {"id": template_id, "deleted": success})

        await delete_cache(f"template:id:{template_id}")
        await clear_cache_pattern("templates:")
        return success
    except Exception as e:
        await redis_tx_manager.fail_transaction(tx_id, str(e))
        logger.error(f"[Redis-First] delete_template failed: {e}")
        raise


# ─── System Performance & Usage Stats ─────────────────────────────────────

async def get_performance_stats(db: AsyncSession) -> Dict[str, Any]:
    """Get aggregated performance stats (checks Redis cache first)."""
    cache_key = "sys_config:performance_stats"
    cached = await get_cache(cache_key)
    if cached is not None:
        return cached

    total_users_q = await db.execute(select(func.count(User.id)))
    total_users = total_users_q.scalar() or 0

    active_users_q = await db.execute(
        select(func.count(User.id)).where(User.is_archived == False)
    )
    active_users = active_users_q.scalar() or 0
    archived_users = total_users - active_users

    role_counts = {}
    for role in ["ADMIN", "HR", "CANDIDATE"]:
        count_q = await db.execute(
            select(func.count(User.id)).where(User.role == role)
        )
        role_counts[role] = count_q.scalar() or 0

    total_jobs_q = await db.execute(select(func.count(JobDescription.id)))
    total_jobs = total_jobs_q.scalar() or 0

    active_jobs_q = await db.execute(
        select(func.count(JobDescription.id)).where(JobDescription.is_active == True)
    )
    active_jobs = active_jobs_q.scalar() or 0
    inactive_jobs = total_jobs - active_jobs

    total_apps_q = await db.execute(select(func.count(JobApplication.id)))
    total_apps = total_apps_q.scalar() or 0

    app_statuses = {}
    for status_val in ["PENDING", "REVIEWED", "ACCEPTED", "REJECTED", "ARCHIVED", "TECHNICAL INTERVIEW", "FINAL INTERVIEW"]:
        count_q = await db.execute(
            select(func.count(JobApplication.id)).where(JobApplication.status == status_val)
        )
        app_statuses[status_val] = count_q.scalar() or 0

    pending = app_statuses.get("PENDING", 0)
    reviewed = app_statuses.get("REVIEWED", 0) + app_statuses.get("TECHNICAL INTERVIEW", 0) + app_statuses.get("FINAL INTERVIEW", 0)
    accepted = app_statuses.get("ACCEPTED", 0)
    rejected = app_statuses.get("REJECTED", 0) + app_statuses.get("ARCHIVED", 0)

    avg_score_q = await db.execute(
        select(func.avg(JobApplication.match_score)).where(JobApplication.match_score.isnot(None))
    )
    avg_match = avg_score_q.scalar()
    avg_match_score = round(avg_match, 1) if avg_match else None

    audit_count_q = await db.execute(select(func.count(AuditLog.id)))
    total_audit = audit_count_q.scalar() or 0

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_logins_q = await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.action == "SIGN_IN",
            AuditLog.created_at >= seven_days_ago
        )
    )
    recent_logins = recent_logins_q.scalar() or 0

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

    ai_analysis_q = await db.execute(
        select(func.count(JobApplication.id)).where(JobApplication.ai_powered == True)
    )
    ai_analysis_count = ai_analysis_q.scalar() or 0

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

    conversion_rate = round((accepted / total_apps * 100), 1) if total_apps > 0 else 0.0
    data_points = total_users + total_jobs + total_apps + total_audit

    stats = {
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
    await set_cache(cache_key, stats, ttl=180)
    return stats


import sys
system_config_repository = sys.modules[__name__]
SystemConfigRepository = sys.modules[__name__]
