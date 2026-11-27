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
    "ai_score_weight": 0.4,
    "rule_score_weight": 0.6,
    "transferable_skills_cap": 2
}

DEFAULT_RECRUITMENT_CONFIG = {
    "max_active_applications": 3,
    "retention_months": 12,
    "reapplication_cooldown_days": 0,
    "messaging_closure_days": 30,
    "allow_hired_elsewhere_withdrawal": False,
}

RESUME_TIPS_CONFIG_KEY = "ats_resume_tips"

DEFAULT_RESUME_TIPS: Dict[str, Any] = {
    "title": "Tips for a better match",
    "tooltip": "Clear formatting helps our system read your resume accurately so your match reflects your actual experience.",
    "intro": "A clean, easy-to-read resume helps the system read your details accurately.",
    "bullets": [
        "Use a simple one-column layout with clear headings: Education, Skills, Work Experience, Certifications.",
        "Upload a text-based PDF or DOCX, not a photo or scanned image.",
        "Use standard fonts and avoid text inside images, tables, text boxes, headers and footers.",
        'Write dates and job titles clearly, for example "Customer Service Representative, June 2023 - Present".',
        "List your skills and tools by name (for example Excel, Shopify, data entry) and use the same words as in the job posting when they truly apply to you.",
        "Include your certifications and trainings, and keep the resume up to date.",
    ],
    "honesty_reminder": "Only include what is true.",
    "apply_skills_reminder": "Review the required skills for this position and make sure your resume mentions the skills and matching experience you actually have.",
}


async def get_resume_tips_config(db: AsyncSession) -> Dict[str, Any]:
    """Retrieve applicant-facing ATS resume tips, merged with Admin SystemConfig overrides."""
    merged = {
        **DEFAULT_RESUME_TIPS,
        "bullets": list(DEFAULT_RESUME_TIPS["bullets"]),
    }
    try:
        cfg = await SystemConfigRepository.get_config_by_key(db, RESUME_TIPS_CONFIG_KEY)
        if cfg and cfg.value:
            saved = json.loads(cfg.value)
            if isinstance(saved, dict):
                for field in ("title", "tooltip", "intro", "honesty_reminder", "apply_skills_reminder"):
                    if isinstance(saved.get(field), str) and saved[field].strip():
                        merged[field] = saved[field].strip()
                if isinstance(saved.get("bullets"), list):
                    cleaned_bullets = [str(b).strip() for b in saved["bullets"] if str(b).strip()]
                    if cleaned_bullets:
                        merged["bullets"] = cleaned_bullets[:10]
    except Exception as exc:
        logger.warning(f"Failed loading custom ATS resume tips, using defaults: {exc}")
    return merged


async def update_resume_tips_config(
    db: AsyncSession,
    updates: Dict[str, Any],
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    current = await get_resume_tips_config(db)
    for field in ("title", "tooltip", "intro", "honesty_reminder", "apply_skills_reminder"):
        if field in updates and updates[field] is not None:
            val = str(updates[field]).strip()
            if val:
                current[field] = val
    if "bullets" in updates and updates["bullets"] is not None:
        cleaned_bullets = [str(b).strip() for b in updates["bullets"] if str(b).strip()]
        if cleaned_bullets:
            current["bullets"] = cleaned_bullets[:10]

    await update_config(
        db=db,
        key=RESUME_TIPS_CONFIG_KEY,
        value=json.dumps(current),
        category="resume_tips",
        description="Applicant-facing ATS-friendly resume tips shown on upload and review screens",
        user_id=user_id,
    )
    return current


async def reset_resume_tips_config(db: AsyncSession, user_id: Optional[int] = None) -> Dict[str, Any]:
    await SystemConfigRepository.delete_config(db, RESUME_TIPS_CONFIG_KEY)
    return {
        **DEFAULT_RESUME_TIPS,
        "bullets": list(DEFAULT_RESUME_TIPS["bullets"]),
    }


# ─── Matching Parameters & Recruitment Rules ────────────────────────────

async def _get_int_config(db: AsyncSession, key: str, default: int, min_val: int, max_val: int) -> int:
    config = await SystemConfigRepository.get_config_by_key(db, key)
    if config and config.value is not None:
        try:
            raw_val = config.value
            if isinstance(raw_val, str) and (raw_val.startswith('"') or raw_val.startswith('{')):
                raw_val = json.loads(raw_val)
            return max(min_val, min(max_val, int(raw_val)))
        except Exception:
            pass
    return default


async def _get_bool_config(db: AsyncSession, key: str, default: bool) -> bool:
    config = await SystemConfigRepository.get_config_by_key(db, key)
    if config and config.value is not None:
        raw = str(config.value).strip().lower()
        if raw in ("true", "1", "yes", "on"):
            return True
        if raw in ("false", "0", "no", "off"):
            return False
    return default


async def get_max_active_applications(db: AsyncSession) -> int:
    """Retrieve maximum number of active applications allowed per candidate (REQ081, REQ082)."""
    return await _get_int_config(db, "max_active_applications", 3, 1, 20)


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


async def get_retention_months(db: AsyncSession) -> int:
    """Data retention window in months (default 12)."""
    return await _get_int_config(db, "retention_months", 12, 1, 120)


async def get_reapplication_cooldown_days(db: AsyncSession) -> int:
    """Reapplication cooldown in days after decision (default 0 = none)."""
    return await _get_int_config(db, "reapplication_cooldown_days", 0, 0, 365)


async def get_messaging_closure_days(db: AsyncSession) -> int:
    """Days after application resolution before messaging thread closes (default 30)."""
    return await _get_int_config(db, "messaging_closure_days", 30, 1, 365)


async def get_allow_hired_elsewhere_withdrawal(db: AsyncSession) -> bool:
    """Whether HR can mark remaining applications as 'Withdrawn – hired elsewhere in company' (default False)."""
    return await _get_bool_config(db, "allow_hired_elsewhere_withdrawal", False)


async def get_recruitment_config(db: AsyncSession) -> Dict[str, Any]:
    return {
        "max_active_applications": await get_max_active_applications(db),
        "retention_months": await get_retention_months(db),
        "reapplication_cooldown_days": await get_reapplication_cooldown_days(db),
        "messaging_closure_days": await get_messaging_closure_days(db),
        "allow_hired_elsewhere_withdrawal": await get_allow_hired_elsewhere_withdrawal(db),
    }


async def update_recruitment_config(
    db: AsyncSession,
    updates: Dict[str, Any],
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    if updates.get("max_active_applications") is not None:
        await update_max_active_applications(db, int(updates["max_active_applications"]), user_id=user_id)
    if updates.get("retention_months") is not None:
        val = max(1, min(120, int(updates["retention_months"])))
        await update_config(db, "retention_months", str(val), "recruitment", "Data retention window in months before anonymization", user_id)
    if updates.get("reapplication_cooldown_days") is not None:
        val = max(0, min(365, int(updates["reapplication_cooldown_days"])))
        await update_config(db, "reapplication_cooldown_days", str(val), "recruitment", "Reapplication cooldown period in days (0 = none)", user_id)
    if updates.get("messaging_closure_days") is not None:
        val = max(1, min(365, int(updates["messaging_closure_days"])))
        await update_config(db, "messaging_closure_days", str(val), "recruitment", "Days after resolution before application messaging closes", user_id)
    if updates.get("allow_hired_elsewhere_withdrawal") is not None:
        val = "true" if bool(updates["allow_hired_elsewhere_withdrawal"]) else "false"
        await update_config(db, "allow_hired_elsewhere_withdrawal", val, "recruitment", "Allow HR to mark remaining apps as Withdrawn – hired elsewhere in company", user_id)
    return await get_recruitment_config(db)

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
