import pytest
from sqlalchemy import func, select

from app.models.job_description import JobDescription
from app.models.system_config import FormTemplate, SystemConfig
from app.models.user import User
from scripts import seed_defaults


@pytest.mark.asyncio
async def test_seed_defaults_populates_all_entities_and_is_idempotent(db_session):
    """Running seed functions twice creates all defaults once with zero duplicates."""
    acc1 = await seed_defaults.seed_accounts(db_session)
    job1 = await seed_defaults.seed_jobs(db_session)
    tpl1 = await seed_defaults.seed_form_templates(db_session)
    cfg1 = await seed_defaults.seed_system_configs(db_session)

    assert acc1["created_admin"] == 1
    assert acc1["created_hr"] == len(seed_defaults.HR_ACCOUNTS)
    assert job1["created_jobs"] == len(seed_defaults.MARIWASA_JOBS)
    assert tpl1["created_form_templates"] == len(seed_defaults.DEFAULT_FORM_TEMPLATES)
    assert cfg1["created_configs"] == 4

    # Re-run to verify strict idempotency
    acc2 = await seed_defaults.seed_accounts(db_session)
    job2 = await seed_defaults.seed_jobs(db_session)
    tpl2 = await seed_defaults.seed_form_templates(db_session)
    cfg2 = await seed_defaults.seed_system_configs(db_session)

    assert acc2["created_admin"] == 0
    assert acc2["created_hr"] == 0
    assert job2["created_jobs"] == 0
    assert job2["existing_jobs"] == len(seed_defaults.MARIWASA_JOBS)
    assert tpl2["created_form_templates"] == 0
    assert cfg2["created_configs"] == 0

    total_jobs = (await db_session.execute(select(func.count(JobDescription.id)))).scalar()
    total_staff = (
        await db_session.execute(
            select(func.count(User.id)).where(User.role.in_(["ADMIN", "HR"]))
        )
    ).scalar()
    total_templates = (await db_session.execute(select(func.count(FormTemplate.id)))).scalar()
    total_configs = (await db_session.execute(select(func.count(SystemConfig.id)))).scalar()

    assert total_jobs == len(seed_defaults.MARIWASA_JOBS)
    assert total_staff == 1 + len(seed_defaults.HR_ACCOUNTS)
    assert total_templates == len(seed_defaults.DEFAULT_FORM_TEMPLATES)
    assert total_configs == 4
