import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from app.repositories.system_config_repository import SystemConfigRepository
from app.schemas.system_config_schema import FormTemplateCreate, FormTemplateUpdate


# ─── System Configurations ───────────────────────────────────────────────

async def get_all_configs(db: AsyncSession):
    return await SystemConfigRepository.get_all_configs(db)


async def get_configs_by_category(db: AsyncSession, category: str):
    return await SystemConfigRepository.get_configs_by_category(db, category)


async def update_config(db: AsyncSession, key: str, value: str, category: str, description: str = None, user_id: int = None):
    return await SystemConfigRepository.upsert_config(
        db=db, key=key, value=value, category=category, description=description, updated_by=user_id
    )


logger = logging.getLogger(__name__)

# Global default weights = thesis distribution (Skills 40%, Experience 30%,
# Education 15%, Certifications 10%, Resume Completeness 5%; total 100%).
from app.services.job_matching_service import THESIS_DEFAULT_WEIGHTS

DEFAULT_WEIGHTS = dict(THESIS_DEFAULT_WEIGHTS)

DEFAULT_THRESHOLDS = {
    "fuzzy_match_threshold": 0.75,
    "minimum_match_score": 30.0,
    "ai_score_weight": 0.8,
    "rule_score_weight": 0.2,
    "transferable_skills_cap": 2
}

DEFAULT_RECRUITMENT_CONFIG = {
    "max_active_applications": 3
}


# ─── Matching Parameters & Recruitment Rules ────────────────────────────

async def get_max_active_applications(db: AsyncSession) -> int:
    """Retrieve maximum number of active applications allowed per candidate (REQ081, REQ082)."""
    config = await SystemConfigRepository.get_config_by_key(db, "max_active_applications")
    if config and config.value:
        try:
            raw_val = config.value
            if isinstance(raw_val, str) and (raw_val.startswith('"') or raw_val.startswith('{')):
                parsed = json.loads(raw_val)
                return max(1, int(parsed))
            return max(1, int(raw_val))
        except Exception:
            pass
    return 3


async def update_max_active_applications(db: AsyncSession, limit: int, user_id: int = None):
    """Adjust maximum number of active applications allowed per candidate (REQ082)."""
    safe_limit = max(1, min(20, int(limit)))
    return await update_config(
        db=db,
        key="max_active_applications",
        value=str(safe_limit),
        category="recruitment",
        description="Maximum active applications allowed per candidate",
        user_id=user_id
    )

async def get_matching_parameters(db: AsyncSession) -> dict:
    weights_config = await SystemConfigRepository.get_config_by_key(db, "matching_weights")
    thresholds_config = await SystemConfigRepository.get_config_by_key(db, "matching_thresholds")

    weights = json.loads(weights_config.value) if weights_config else dict(DEFAULT_WEIGHTS)
    thresholds = json.loads(thresholds_config.value) if thresholds_config else dict(DEFAULT_THRESHOLDS)

    # Ensure all default keys exist
    for k, v in DEFAULT_WEIGHTS.items():
        if k not in weights:
            weights[k] = v

    for k, v in DEFAULT_THRESHOLDS.items():
        if k not in thresholds:
            thresholds[k] = v

    config_data = {
        "weights": weights,
        "thresholds": thresholds
    }

    # Store in Redis for instant sync & async access
    try:
        from app.utils.redis_client import get_async_redis
        client = get_async_redis()
        await client.set("matching_config:active", json.dumps(config_data))
    except Exception as e:
        logger.debug(f"Failed to sync matching config to Redis: {e}")

    return config_data


async def update_matching_parameters(db: AsyncSession, weights: dict = None, thresholds: dict = None, user_id: int = None):
    current = await get_matching_parameters(db)
    current_weights = dict(current.get("weights", DEFAULT_WEIGHTS))
    current_thresholds = dict(current.get("thresholds", DEFAULT_THRESHOLDS))

    if weights:
        current_weights.update(weights)
        await update_config(db, "matching_weights", json.dumps(current_weights), "matching", "Weights for job matching algorithm components", user_id)
    if thresholds:
        current_thresholds.update(thresholds)
        await update_config(db, "matching_thresholds", json.dumps(current_thresholds), "matching", "Thresholds and limits for job matching algorithm", user_id)
    
    updated_data = {
        "weights": current_weights,
        "thresholds": current_thresholds
    }

    try:
        from app.utils.redis_client import get_async_redis
        client = get_async_redis()
        await client.set("matching_config:active", json.dumps(updated_data))
    except Exception as e:
        logger.debug(f"Failed to update active matching config in Redis: {e}")

    return updated_data


async def recalculate_all_applications(db: AsyncSession, progress_cb=None) -> dict:
    """
    Recalculate match scores and ATS breakdowns for all existing job applications.
    Each application is scored with its job's own weights (or the global default
    weights when the job has none) and the active thresholds.
    Never modifies application status or shortlist rosters.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.job_application import JobApplication
    from app.services.job_matching_service import calculate_match_score
    from app.services.job_application_service import _resume_data_from_application
    from app.services.job_description_service import apply_match_result_to_application

    config = await get_matching_parameters(db)

    result = await db.execute(
        select(JobApplication).options(selectinload(JobApplication.job))
    )
    apps = result.scalars().all()
    total = len(apps)

    updated_count = 0
    for idx, app in enumerate(apps, start=1):
        if not app.job:
            continue

        resume_data = _resume_data_from_application(app)
        scores = calculate_match_score(resume_data, app.job, matching_config=config)
        apply_match_result_to_application(app, scores)
        updated_count += 1
        if progress_cb:
            progress_cb(idx, total)

    await db.commit()
    logger.info(f"Recalculated match scores for {updated_count} applications.")
    return {"total_applications": total, "updated_applications": updated_count}


# ─── Role Permissions ───────────────────────────────────────────────────

async def get_users_by_role(db: AsyncSession, role: str):
    return await SystemConfigRepository.get_users_by_role(db, role)


async def update_user_role(db: AsyncSession, user_id: int, new_role: str):
    return await SystemConfigRepository.update_user_role(db, user_id, new_role)


# ─── Form Templates ─────────────────────────────────────────────────────

async def get_all_templates(db: AsyncSession):
    return await SystemConfigRepository.get_all_templates(db)


async def get_template_by_id(db: AsyncSession, template_id: int):
    return await SystemConfigRepository.get_template_by_id(db, template_id)


async def create_template(db: AsyncSession, template_in: FormTemplateCreate, user_id: int):
    data = template_in.model_dump()
    data["created_by"] = user_id
    return await SystemConfigRepository.create_template(db, data)


async def update_template(db: AsyncSession, template_id: int, template_in: FormTemplateUpdate):
    data = template_in.model_dump(exclude_unset=True)
    return await SystemConfigRepository.update_template(db, template_id, data)


async def delete_template(db: AsyncSession, template_id: int):
    return await SystemConfigRepository.delete_template(db, template_id)


# ─── Performance Monitoring ──────────────────────────────────────────────

async def get_performance_stats(db: AsyncSession):
    return await SystemConfigRepository.get_performance_stats(db)


import sys
system_config_service = sys.modules[__name__]
config_service = sys.modules[__name__]
