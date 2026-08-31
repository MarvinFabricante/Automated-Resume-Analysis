from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.utils.auth import get_current_user, require_role
from app.schemas.system_config_schema import (
    SystemConfigResponse, SystemConfigCreate, SystemConfigUpdate,
    MatchingConfigResponse, MatchingWeightsUpdate, MatchingThresholdsUpdate,
    UserRoleResponse, RoleUpdate,
    FormTemplateResponse, FormTemplateCreate, FormTemplateUpdate,
    SystemPerformanceResponse
)
from app.services.system_config_service import system_config_service
from app.services.audit_service import audit_service
from app.utils.cache import cache_response, clear_cache_pattern


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
    weights_dict = weights.model_dump(exclude_unset=True)
    result = await system_config_service.update_matching_parameters(db, weights=weights_dict, user_id=current_user.get("id"))
    
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="UPDATE_CONFIG", target="Matching Weights", details="Updated matching algorithm weights"
    )
    await clear_cache_pattern("matching_config*")
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
    valid_roles = ["ADMIN", "HR", "CANDIDATE"]
    if role_update.role.upper() not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid role specified")
        
    user = await system_config_service.update_user_role(db, user_id, role_update.role.upper())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    await audit_service.record_activity(
        db=db, user_id=current_user.get("id"), action="UPDATE_ROLE", target=f"User {user.email}", details=f"Changed role to {role_update.role.upper()}"
    )
    await clear_cache_pattern("users_role*")
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


# ─── System Performance ───────────────────────────────────────────────────────

@router.get("/performance", response_model=SystemPerformanceResponse)
@cache_response("system_performance", ttl=300)
async def get_system_performance(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("ADMIN"))
):
    return await system_config_service.get_performance_stats(db)
