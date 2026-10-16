import pytest
from unittest.mock import patch
from app.services import audit_service
from app.models.user import User


@pytest.mark.asyncio
async def test_record_activity_with_valid_user(db_session):
    user = User(
        fullname="Audit Target User",
        email="audit_user@example.com",
        password="password123",
        role="HR"
    )
    db_session.add(user)
    await db_session.flush()

    log = await audit_service.record_activity(
        db=db_session,
        user_id=user.id,
        action="LOGIN",
        target="User Session",
        details="User logged in from browser",
        ip_address="192.168.1.1"
    )
    assert log is not None
    assert log.id is not None
    assert log.user_id == user.id
    assert log.action == "LOGIN"
    assert log.target == "User Session"
    assert log.details == "User logged in from browser"
    assert log.ip_address == "192.168.1.1"


@pytest.mark.asyncio
async def test_record_activity_with_invalid_or_none_user(db_session):
    # Non-existent user_id should result in user_id=None
    log_invalid = await audit_service.record_activity(
        db=db_session,
        user_id=999999,
        action="SYSTEM_ALERT",
        details="Alert without valid user"
    )
    assert log_invalid is not None
    assert log_invalid.user_id is None

    # None user_id
    log_none = await audit_service.record_activity(
        db=db_session,
        user_id=None,
        action="ANONYMOUS_ACTION"
    )
    assert log_none is not None
    assert log_none.user_id is None


@pytest.mark.asyncio
async def test_get_recent_and_all_activities(db_session):
    await audit_service.record_activity(db=db_session, action="ACTION_1", details="Detail 1")
    await audit_service.record_activity(db=db_session, action="ACTION_2", details="Detail 2")

    recent = await audit_service.get_recent_hr_activities(db_session, limit=2)
    assert isinstance(recent, list)
    assert len(recent) >= 2

    all_logs = await audit_service.get_all_audit_logs(db_session)
    assert isinstance(all_logs, list)
    assert len(all_logs) >= 2


@pytest.mark.asyncio
async def test_record_activity_exception_handling(db_session):
    with patch("app.repositories.audit_repository.AuditRepository.create_audit_log", side_effect=Exception("DB Error")):
        result = await audit_service.record_activity(db=db_session, action="ERROR_ACTION")
        assert result is None
