import pytest
from app.repositories import audit_repository
from app.models.user import User
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_audit_repo_create_and_query(db_session):
    # Setup test user
    user = User(
        fullname="Audit Target User",
        email="audit_repo_user@example.com",
        password=hash_password("pass123"),
        role="HR"
    )
    db_session.add(user)
    await db_session.commit()
    user_id = user.id

    # 1. Create audit log
    log_data = {
        "user_id": user_id,
        "action": "CONFIG_UPDATE",
        "target": "Algorithm Weights",
        "details": "Changed skills weight to 0.40"
    }
    log = await audit_repository.create_audit_log(db_session, log_data)
    assert log.id is not None
    assert log.action == "CONFIG_UPDATE"

    # 2. Get recent activities
    recent = await audit_repository.get_recent_activities(db_session, limit=5)
    assert len(recent) >= 1
    assert any(l.id == log.id for l in recent)

    # 3. Get all activities
    all_logs = await audit_repository.get_all_activities(db_session)
    assert len(all_logs) >= 1
    assert any(l.action == "CONFIG_UPDATE" for l in all_logs)
