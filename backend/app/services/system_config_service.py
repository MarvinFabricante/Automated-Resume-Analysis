import json
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from app.repositories.system_config_repository import SystemConfigRepository
from app.schemas.system_config_schema import FormTemplateCreate, FormTemplateUpdate


class SystemConfigService:
    # ─── System Configurations ───────────────────────────────────────────────

    async def get_all_configs(self, db: AsyncSession):
        return await SystemConfigRepository.get_all_configs(db)

    async def get_configs_by_category(self, db: AsyncSession, category: str):
        return await SystemConfigRepository.get_configs_by_category(db, category)

    async def update_config(self, db: AsyncSession, key: str, value: str, category: str, description: str = None, user_id: int = None):
        return await SystemConfigRepository.upsert_config(
            db=db, key=key, value=value, category=category, description=description, updated_by=user_id
        )

    # ─── Matching Parameters ────────────────────────────────────────────────

    async def get_matching_parameters(self, db: AsyncSession) -> dict:
        weights_config = await SystemConfigRepository.get_config_by_key(db, "matching_weights")
        thresholds_config = await SystemConfigRepository.get_config_by_key(db, "matching_thresholds")

        default_weights = {
            "skills_weight": 0.45,
            "experience_weight": 0.25,
            "education_weight": 0.15,
            "certifications_weight": 0.10,
            "location_weight": 0.05
        }
        
        default_thresholds = {
            "fuzzy_match_threshold": 0.75,
            "minimum_match_score": 30.0,
            "ai_score_weight": 0.8,
            "rule_score_weight": 0.2,
            "transferable_skills_cap": 2
        }

        weights = json.loads(weights_config.value) if weights_config else default_weights
        thresholds = json.loads(thresholds_config.value) if thresholds_config else default_thresholds

        return {
            "weights": weights,
            "thresholds": thresholds
        }

    async def update_matching_parameters(self, db: AsyncSession, weights: dict = None, thresholds: dict = None, user_id: int = None):
        if weights:
            await self.update_config(db, "matching_weights", json.dumps(weights), "matching", "Weights for job matching algorithm components", user_id)
        if thresholds:
            await self.update_config(db, "matching_thresholds", json.dumps(thresholds), "matching", "Thresholds and limits for job matching algorithm", user_id)
        
        return await self.get_matching_parameters(db)

    # ─── Role Permissions ───────────────────────────────────────────────────
    
    async def get_users_by_role(self, db: AsyncSession, role: str):
        return await SystemConfigRepository.get_users_by_role(db, role)

    async def update_user_role(self, db: AsyncSession, user_id: int, new_role: str):
        return await SystemConfigRepository.update_user_role(db, user_id, new_role)


    # ─── Form Templates ─────────────────────────────────────────────────────

    async def get_all_templates(self, db: AsyncSession):
        return await SystemConfigRepository.get_all_templates(db)

    async def get_template_by_id(self, db: AsyncSession, template_id: int):
        return await SystemConfigRepository.get_template_by_id(db, template_id)

    async def create_template(self, db: AsyncSession, template_in: FormTemplateCreate, user_id: int):
        data = template_in.model_dump()
        data["created_by"] = user_id
        return await SystemConfigRepository.create_template(db, data)

    async def update_template(self, db: AsyncSession, template_id: int, template_in: FormTemplateUpdate):
        data = template_in.model_dump(exclude_unset=True)
        return await SystemConfigRepository.update_template(db, template_id, data)

    async def delete_template(self, db: AsyncSession, template_id: int):
        return await SystemConfigRepository.delete_template(db, template_id)

    # ─── Performance Monitoring ──────────────────────────────────────────────

    async def get_performance_stats(self, db: AsyncSession):
        return await SystemConfigRepository.get_performance_stats(db)


system_config_service = SystemConfigService()
