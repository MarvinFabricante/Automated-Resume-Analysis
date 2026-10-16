import pytest
from app.repositories import system_config_repository
from app.models.candidate import Candidate
from app.models.hr import HR
from app.models.admin import Admin
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_system_config_repo_config_crud(db_session):
    # 1. Upsert config
    created = await system_config_repository.upsert_config(
        db_session,
        key="matching.skills_weight",
        value="0.35",
        category="matching",
        description="Weight for skills match"
    )
    assert created.id is not None
    assert created.key == "matching.skills_weight"
    assert created.value == "0.35"

    # 2. Get by key
    by_key = await system_config_repository.get_config_by_key(db_session, "matching.skills_weight")
    assert by_key is not None
    assert by_key.value == "0.35"

    # 3. Get by category
    by_cat = await system_config_repository.get_configs_by_category(db_session, "matching")
    assert len(by_cat) >= 1
    assert any(c.key == "matching.skills_weight" for c in by_cat)

    # 4. Get all
    all_configs = await system_config_repository.get_all_configs(db_session)
    assert len(all_configs) >= 1

    # 5. Update existing config via upsert
    updated = await system_config_repository.upsert_config(
        db_session,
        key="matching.skills_weight",
        value="0.40",
        category="matching"
    )
    assert updated.value == "0.40"

    # 6. Delete config
    deleted = await system_config_repository.delete_config(db_session, "matching.skills_weight")
    assert deleted is True
    assert await system_config_repository.get_config_by_key(db_session, "matching.skills_weight") is None


@pytest.mark.asyncio
async def test_system_config_repo_roles_and_templates(db_session):
    # Setup candidate
    cand = Candidate(
        fullname="Role Cand Tester",
        email="role_cand_repo@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    db_session.add(cand)
    await db_session.commit()
    cand_id = cand.id

    # 1. Get users by role
    cands = await system_config_repository.get_users_by_role(db_session, "CANDIDATE")
    assert len(cands) >= 1
    assert any(c.id == cand_id for c in cands)

    # 2. Update user role to HR
    updated_user = await system_config_repository.update_user_role(db_session, cand_id, "HR")
    assert updated_user is not None
    assert updated_user.role == "HR"

    # 3. Create form template
    tpl_data = {
        "name": "Repo Engineering Form",
        "description": "Form for engineering applicants",
        "fields": [{"field_name": "experience", "label": "Years Experience", "field_type": "number", "required": True}],
        "is_default": False
    }
    tpl = await system_config_repository.create_template(db_session, tpl_data)
    assert tpl.id is not None
    assert tpl.name == "Repo Engineering Form"
    tpl_id = tpl.id

    # 4. Get template by ID & all templates
    by_id = await system_config_repository.get_template_by_id(db_session, tpl_id)
    assert by_id is not None
    assert by_id.name == "Repo Engineering Form"

    all_tpls = await system_config_repository.get_all_templates(db_session)
    assert len(all_tpls) >= 1

    # 5. Update template
    updated_tpl = await system_config_repository.update_template(db_session, tpl_id, {"description": "Updated description"})
    assert updated_tpl.description == "Updated description"

    # 6. Delete template
    deleted_tpl = await system_config_repository.delete_template(db_session, tpl_id)
    assert deleted_tpl is True
    assert await system_config_repository.get_template_by_id(db_session, tpl_id) is None


@pytest.mark.asyncio
async def test_system_config_repo_performance_stats(db_session):
    stats = await system_config_repository.get_performance_stats(db_session)
    assert "total_users" in stats
    assert "total_jobs" in stats
    assert "total_applications" in stats
