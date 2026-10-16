import pytest
from app.repositories import notification_repository
from app.models.notification import Notification


@pytest.mark.asyncio
async def test_notification_repo_crud_and_criteria(db_session):
    # 1. Create notification for candidate
    notif_data = {
        "title": "Application Update",
        "message": "Your job application has been reviewed.",
        "type": "APPLICATION_UPDATE",
        "target_role": "CANDIDATE",
        "target_email": "notif_candidate@example.com",
        "sender_role": "HR",
        "is_read": False
    }
    notif = await notification_repository.create(db_session, notif_data)
    assert notif.id is not None
    assert notif.title == "Application Update"

    # 2. Get by criteria (matching candidate)
    cand_notifs = await notification_repository.get_all_by_criteria(
        db_session,
        role="CANDIDATE",
        email="notif_candidate@example.com"
    )
    assert len(cand_notifs) >= 1
    assert cand_notifs[0].id == notif.id
    assert cand_notifs[0].is_read is False

    # 3. Invalid role criteria returns empty list
    invalid_role = await notification_repository.get_all_by_criteria(db_session, role="UNKNOWN")
    assert invalid_role == []

    # 4. Mark all as read
    marked = await notification_repository.mark_all_as_read(
        db_session,
        role="CANDIDATE",
        email="notif_candidate@example.com"
    )
    assert marked is True

    # Confirm is_read is True
    after_mark = await notification_repository.get_all_by_criteria(
        db_session,
        role="CANDIDATE",
        email="notif_candidate@example.com"
    )
    assert after_mark[0].is_read is True
