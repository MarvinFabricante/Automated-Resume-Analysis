import pytest
from app.services import system_config_service
from app.schemas.system_config_schema import FormTemplateCreate, FormTemplateUpdate, FormFieldDefinition
from app.models.user import User
from app.models.job_description import JobDescription, JobType
from app.models.job_application import JobApplication


@pytest.mark.asyncio
async def test_config_crud_and_categories(db_session):
    # Upsert a configuration
    cfg = await system_config_service.update_config(
        db=db_session,
        key="app_title",
        value="Mariwasa Portal",
        category="general",
        description="Main site title"
    )
    assert cfg is not None
    assert cfg.key == "app_title"
    assert cfg.value == "Mariwasa Portal"

    # Get by category
    gen_configs = await system_config_service.get_configs_by_category(db_session, "general")
    assert len(gen_configs) >= 1
    assert any(c.key == "app_title" for c in gen_configs)

    # Get all configs
    all_cfgs = await system_config_service.get_all_configs(db_session)
    assert len(all_cfgs) >= 1


@pytest.mark.asyncio
async def test_matching_parameters_lifecycle(db_session):
    params = await system_config_service.get_matching_parameters(db_session)
    assert "weights" in params
    assert "thresholds" in params
    assert "skills_weight" in params["weights"]

    # Update weights and thresholds
    updated = await system_config_service.update_matching_parameters(
        db=db_session,
        weights={"skills_weight": 0.50, "experience_weight": 0.20},
        thresholds={"fuzzy_match_threshold": 0.80}
    )
    assert updated["weights"]["skills_weight"] == 0.50
    assert updated["thresholds"]["fuzzy_match_threshold"] == 0.80

    # Verify persisted in get_matching_parameters
    persisted = await system_config_service.get_matching_parameters(db_session)
    assert persisted["weights"]["skills_weight"] == 0.50
    assert persisted["thresholds"]["fuzzy_match_threshold"] == 0.80


@pytest.mark.asyncio
async def test_recalculate_all_applications(db_session):
    job = JobDescription(
        job_id="JOB-RECALC-01",
        job_title="Data Scientist",
        department="Analytics",
        job_type=JobType.FULL_TIME,
        location="Remote",
        description="Machine learning and statistics",
        skills_requirements="Python, Machine Learning, SQL, PyTorch"
    )
    db_session.add(job)
    await db_session.flush()

    app = JobApplication(
        job_id=job.id,
        candidate_name="Data Candidate",
        candidate_email="data@example.com",
        skills=["Python", "SQL"],
        degree="Master of Science in Statistics",
        relevance="3 years data science experience"
    )
    db_session.add(app)
    await db_session.commit()

    recalc_result = await system_config_service.recalculate_all_applications(db_session)
    assert "total_applications" in recalc_result
    assert "updated_applications" in recalc_result
    assert recalc_result["updated_applications"] >= 1


@pytest.mark.asyncio
async def test_user_roles_management(db_session):
    user = User(
        fullname="Role Change User",
        email="role_user@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add(user)
    await db_session.commit()

    # Get users by role
    candidates = await system_config_service.get_users_by_role(db_session, "CANDIDATE")
    assert any(u.email == "role_user@example.com" for u in candidates)

    # Change user role to HR
    updated = await system_config_service.update_user_role(db_session, user.id, "HR")
    assert updated.role == "HR"

    # Verify in HR role query
    hrs = await system_config_service.get_users_by_role(db_session, "HR")
    assert any(u.email == "role_user@example.com" for u in hrs)


@pytest.mark.asyncio
async def test_form_template_crud(db_session):
    fields = [
        FormFieldDefinition(
            field_name="portfolio_url",
            field_type="text",
            label="Portfolio Link",
            required=False,
            placeholder="https://..."
        )
    ]
    template_in = FormTemplateCreate(
        name="Developer Application Form",
        description="Custom application form for dev candidates",
        fields=fields,
        is_default=True
    )

    created = await system_config_service.create_template(db_session, template_in, user_id=1)
    assert created.id is not None
    assert created.name == "Developer Application Form"
    assert created.is_default is True

    # Get by ID
    fetched = await system_config_service.get_template_by_id(db_session, created.id)
    assert fetched is not None
    assert fetched.name == created.name

    # Get all
    all_tmps = await system_config_service.get_all_templates(db_session)
    assert len(all_tmps) >= 1

    # Update template
    updated = await system_config_service.update_template(
        db_session,
        created.id,
        FormTemplateUpdate(name="Developer Form v2")
    )
    assert updated.name == "Developer Form v2"

    # Delete template
    deleted = await system_config_service.delete_template(db_session, created.id)
    assert deleted is True
    assert await system_config_service.get_template_by_id(db_session, created.id) is None


@pytest.mark.asyncio
async def test_get_performance_stats(db_session):
    stats = await system_config_service.get_performance_stats(db_session)
    assert isinstance(stats, dict)
