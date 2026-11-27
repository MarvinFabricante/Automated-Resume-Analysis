from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.utils.auth import get_current_user, require_role
from app.schemas.system_config_schema import (
    SystemConfigResponse, SystemConfigCreate, SystemConfigUpdate,
    MatchingConfigResponse, MatchingWeightsUpdate, MatchingThresholdsUpdate,
    RecruitmentConfigResponse, RecruitmentConfigUpdate,
    RetentionRunRequest, RetentionRunLogResponse,
    UserRoleResponse, RoleUpdate,
    FormTemplateResponse, FormTemplateCreate, FormTemplateUpdate,
    SystemPerformanceResponse,
    NotificationTemplatesUpdate, NotificationTemplatesResetRequest,
    ResumeTipsConfigResponse, ResumeTipsConfigUpdate
)
from app.services.system_config_service import system_config_service
from app.services import message_template_service
from app.services.audit_service import audit_service
from app.services import admin_service
from app.utils.cache import cache_response, clear_cache_pattern, invalidate_application_dashboard_caches


router = APIRouter(prefix="/system-config", tags=["System Configuration"])


# ─── System Parameters ────────────────────────────────────────────────────────

@router.get("/matching", response_model=MatchingConfigResponse)
@cache_response("matching_config", ttl=3600)
async def get_matching_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    return await system_config_service.get_matching_parameters(db)


@router.put("/matching/weights", response_model=MatchingConfigResponse)
async def update_matching_weights(
    weights: MatchingWeightsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    from app.services.job_matching_service import validate_scoring_weights
    from app.controllers.admin_controller import _describe_weights

    current_cfg = await system_config_service.get_matching_parameters(db)
    old_weights = dict(current_cfg.get("weights") or {})

    weights_dict = weights.model_dump(exclude_unset=True)
    if "completeness_weight" not in weights_dict and "location_weight" in weights_dict:
        weights_dict["completeness_weight"] = weights_dict.pop("location_weight")
    else:
        weights_dict.pop("location_weight", None)

    merged = {**old_weights, **weights_dict}
    try:
        validated = validate_scoring_weights(merged)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    result = await system_config_service.update_matching_parameters(db, weights=validated, user_id=current_user.get("id"))

    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="UPDATE_CONFIG",
        target="Global Matching Weights",
        details=f"Global default weights changed from ({_describe_weights(old_weights)}) to ({_describe_weights(validated)})",
    )
    await clear_cache_pattern("matching_config*")
    await clear_cache_pattern("ai_analysis:*")
    await clear_cache_pattern("job_matches:*")
    await clear_cache_pattern("job_comparison:*")
    await clear_cache_pattern("app_stats:*")
    await clear_cache_pattern("screening:*")
    return result


@router.put("/matching/thresholds", response_model=MatchingConfigResponse)
async def update_matching_thresholds(
    thresholds: MatchingThresholdsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    thresholds_dict = thresholds.model_dump(exclude_unset=True)
    result = await system_config_service.update_matching_parameters(db, thresholds=thresholds_dict, user_id=current_user.get("id"))
    
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="UPDATE_CONFIG", target="Matching Thresholds", details="Updated matching algorithm thresholds"
    )
    await clear_cache_pattern("matching_config*")
    await clear_cache_pattern("ai_analysis:*")
    await clear_cache_pattern("job_matches:*")
    await clear_cache_pattern("job_comparison:*")
    await clear_cache_pattern("app_stats:*")
    await clear_cache_pattern("screening:*")
    return result


@router.get("/recruitment", response_model=RecruitmentConfigResponse)
async def get_recruitment_config(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if (current_user.get("role") or "").upper() not in ("ADMIN", "HR"):
        raise HTTPException(status_code=403, detail="Forbidden")
    cfg = await system_config_service.get_recruitment_config(db)
    return RecruitmentConfigResponse(**cfg)


@router.put("/recruitment", response_model=RecruitmentConfigResponse)
async def update_recruitment_config(
    payload: RecruitmentConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    updates = payload.model_dump(exclude_unset=True)
    cfg = await system_config_service.update_recruitment_config(
        db, updates, user_id=current_user.get("id")
    )
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="UPDATE_CONFIG",
        target="Recruitment Config",
        details=f"Admin updated recruitment settings: {updates}",
    )
    return RecruitmentConfigResponse(**cfg)


@router.post("/retention/run", response_model=RetentionRunLogResponse)
async def trigger_retention_anonymization(
    payload: RetentionRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Run data retention anonymization in dry-run (default) or live mode (Admin only)."""
    from app.services.retention_service import run_retention_anonymization
    actor_email = current_user.get("sub") or current_user.get("email") or "admin"
    run_log = await run_retention_anonymization(
        db=db,
        dry_run=payload.dry_run,
        retention_months=payload.retention_months,
        triggered_by=f"manual:{actor_email}",
    )
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="RETENTION_ANONYMIZATION_RUN",
        target="Data Retention Job",
        details=(
            f"Admin executed retention job (dry_run={payload.dry_run}, months={run_log.retention_months}): "
            f"evaluated={run_log.candidates_evaluated}, candidates_anonymized={run_log.candidates_anonymized}, "
            f"applications_anonymized={run_log.applications_anonymized}, files_deleted={run_log.files_deleted}, "
            f"skipped_active={run_log.skipped_active}."
        ),
    )
    if not payload.dry_run:
        await invalidate_application_dashboard_caches()
    return run_log


@router.get("/retention/logs", response_model=List[RetentionRunLogResponse])
async def list_retention_logs(
    limit: int = 25,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Return historical run logs for the retention anonymization job (Admin only)."""
    from app.services.retention_service import get_retention_run_logs
    return await get_retention_run_logs(db, limit=limit)


@router.post("/matching/recalculate")
async def recalculate_matching_scores(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="RECALCULATE_SCORES",
        target="Job Applications",
        details="Admin triggered batch ATS match scores recalculation via Celery background worker"
    )

    try:
        from app.tasks import recalculate_all_applications_task
        task = recalculate_all_applications_task.delay()
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "ATS match scores recalculation queued in Celery worker successfully.",
            "updated_applications": 0
        }
    except Exception as celery_err:
        import logging
        logging.getLogger(__name__).warning(f"Celery dispatch failed ({celery_err}). Executing synchronously.")
        result = await system_config_service.recalculate_all_applications(db)
        await invalidate_application_dashboard_caches()
        await clear_cache_pattern("job_matches:*")
        await clear_cache_pattern("job_comparison:*")
        return result


# ─── Role Management ──────────────────────────────────────────────────────────

@router.get("/roles/{role_name}", response_model=List[UserRoleResponse])
@cache_response("users_role", ttl=300)
async def get_users_by_role(
    role_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    return await system_config_service.get_users_by_role(db, role_name.upper())


@router.patch("/users/{user_id}/role", response_model=UserRoleResponse)
async def change_user_role(
    user_id: int,
    role_update: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    if current_user and current_user.get("id") == user_id:
        raise HTTPException(status_code=400, detail="You cannot change your own role.")

    valid_roles = ["HR", "CANDIDATE"]
    if role_update.role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role specified. Only HR and CANDIDATE roles are permitted.")

    target_user = await admin_service.get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    if target_user.role == "ADMIN":
        raise HTTPException(status_code=400, detail="Administrator accounts cannot be modified.")

    user = await system_config_service.update_user_role(db, user_id, role_update.role.upper())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="UPDATE_ROLE", target=f"User {user.email}", details=f"Changed role to {role_update.role.upper()}"
    )
    await clear_cache_pattern("users_role*")
    await clear_cache_pattern("admin_users:*")
    await clear_cache_pattern("users:all:*")
    return user


# ─── Form Templates ───────────────────────────────────────────────────────────

@router.get("/templates", response_model=List[FormTemplateResponse])
@cache_response("form_templates", ttl=600)
async def list_form_templates(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return await system_config_service.get_all_templates(db)


@router.post("/templates", response_model=FormTemplateResponse)
async def create_form_template(
    template: FormTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    result = await system_config_service.create_template(db, template, current_user.get("id"))
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="CREATE_TEMPLATE", target=template.name, details="Created new application form template"
    )
    await clear_cache_pattern("form_templates*")
    return result


@router.put("/templates/{template_id}", response_model=FormTemplateResponse)
async def update_form_template(
    template_id: int,
    template: FormTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    result = await system_config_service.update_template(db, template_id, template)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
        
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="UPDATE_TEMPLATE", target=result.name, details="Updated application form template"
    )
    await clear_cache_pattern("form_templates*")
    return result


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_form_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    success = await system_config_service.delete_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Template not found")
        
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="DELETE_TEMPLATE", target=f"Template {template_id}", details="Deleted application form template"
    )
    await clear_cache_pattern("form_templates*")


# ─── Notification Message Templates (Email & SMS) ────────────────────────────

def _require_hr_or_admin(current_user: dict):
    role = (current_user.get("role") or "").upper()
    if role not in {"HR", "ADMIN", "SUPERADMIN"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.get("/notification-templates")
async def get_notification_templates(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_hr_or_admin(current_user)
    templates = await message_template_service.get_all_templates(db)
    return {"templates": templates}


@router.put("/notification-templates")
async def update_notification_templates(
    payload: NotificationTemplatesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_hr_or_admin(current_user)
    updates = {k: v.model_dump(exclude_unset=True) for k, v in payload.templates.items()}
    templates = await message_template_service.update_templates(
        db, updates, user_id=current_user.get("id")
    )
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="UPDATE_NOTIFICATION_TEMPLATES",
        target="Email & SMS Templates",
        details="Updated customizable Email & SMS notification templates",
    )
    return {"templates": templates}


@router.post("/notification-templates/reset")
async def reset_notification_templates(
    payload: NotificationTemplatesResetRequest = NotificationTemplatesResetRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _require_hr_or_admin(current_user)
    templates = await message_template_service.reset_templates(
        db, template_key=payload.template_key, user_id=current_user.get("id")
    )
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="RESET_NOTIFICATION_TEMPLATES",
        target="Email & SMS Templates",
        details=f"Reset notification templates ({payload.template_key or 'all'}) to defaults",
    )
    return {"templates": templates}


# ─── ATS-Friendly Resume Tips (Public Read, Admin Edit) ──────────────────────

@router.get("/resume-tips", response_model=ResumeTipsConfigResponse)
async def get_resume_tips(db: AsyncSession = Depends(get_db)):
    """Public endpoint returning applicant-facing ATS-friendly resume tips."""
    return await system_config_service.get_resume_tips_config(db)


@router.put("/resume-tips", response_model=ResumeTipsConfigResponse)
async def update_resume_tips(
    payload: ResumeTipsConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Admin-only endpoint to customize applicant-facing ATS resume tips."""
    updates = payload.model_dump(exclude_unset=True)
    result = await system_config_service.update_resume_tips_config(
        db, updates, user_id=current_user.get("id")
    )
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="UPDATE_RESUME_TIPS",
        target="ATS Resume Tips",
        details="Admin updated applicant-facing ATS-friendly resume tips",
    )
    return result


@router.post("/resume-tips/reset", response_model=ResumeTipsConfigResponse)
async def reset_resume_tips(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN")),
):
    """Admin-only endpoint to restore default ATS resume tips."""
    result = await system_config_service.reset_resume_tips_config(db, user_id=current_user.get("id"))
    await audit_service.record_activity(
        db=db,
        user_id=current_user.get("id"),
        action="RESET_RESUME_TIPS",
        target="ATS Resume Tips",
        details="Admin reset applicant-facing ATS-friendly resume tips to defaults",
    )
    return result


# ─── System Performance ───────────────────────────────────────────────────────

@router.get("/performance", response_model=SystemPerformanceResponse)
@cache_response("system_performance", ttl=300)
async def get_system_performance(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    return await system_config_service.get_performance_stats(db)


# ─── Redis-First Infrastructure & Transactions ────────────────────────────────

@router.get("/redis/status")
async def get_redis_status():
    """
    Check Redis connection status, health, and transaction statistics.
    Provides observability into the Redis-first transaction layer.
    """
    import time
    from app.utils.redis_client import is_redis_available, get_async_redis, redis_tx_manager, REDIS_URL

    t0 = time.time()
    available = await is_redis_available()
    latency_ms = round((time.time() - t0) * 1000, 2)

    stats = await redis_tx_manager.get_transaction_stats() if available else {}
    memory_info = {}
    if available:
        try:
            client = get_async_redis()
            info = await client.info("memory")
            memory_info = {
                "used_memory_human": info.get("used_memory_human", "N/A"),
                "used_memory_peak_human": info.get("used_memory_peak_human", "N/A"),
                "total_system_memory_human": info.get("total_system_memory_human", "N/A"),
            }
        except Exception:
            pass

    return {
        "status": "healthy" if available else "degraded",
        "redis_available": available,
        "latency_ms": latency_ms,
        "redis_url": REDIS_URL.split("@")[-1] if "@" in REDIS_URL else REDIS_URL,
        "transaction_stats": stats,
        "memory": memory_info,
    }


@router.get("/redis/transactions")
async def get_redis_transactions(limit: int = 50):
    """
    Retrieve the most recent transactions stored in Redis before the source of truth.
    """
    from app.utils.redis_client import redis_tx_manager
    transactions = await redis_tx_manager.get_recent_transactions(limit=limit)
    return {
        "count": len(transactions),
        "transactions": transactions,
    }


# ─── Gemini API Key Pool Observability (Admin Only) ──────────────────────────

@router.get("/gemini/status")
async def get_gemini_pool_status(
    current_user: dict = Depends(require_role("ADMIN")),
):
    """
    Return safe, non-sensitive health and usage metrics for the Gemini API key pool
    (active primary/failover key fingerprint, cooldowns, rotation & retry counters).
    Never exposes raw API credentials.
    """
    from app.services.gemini_service import get_gemini_status

    return get_gemini_status()

