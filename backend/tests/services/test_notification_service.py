import pytest
from unittest.mock import patch, AsyncMock
from app.services import notification_service


@pytest.mark.asyncio
async def test_create_notification_role_targeted(db_session):
    with patch("app.services.notification_service.manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        notif = await notification_service.create_notification(
            db=db_session,
            title="System Maintenance",
            message="Scheduled downtime tonight at 10 PM.",
            type="announcement",
            target_role="HR",
            sender_role="ADMIN"
        )

        assert notif.id is not None
        assert notif.title == "System Maintenance"
        assert notif.target_role == "HR"
        assert notif.sender_role == "ADMIN"
        mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_create_notification_email_targeted(db_session):
    with patch("app.services.notification_service.manager.broadcast", new_callable=AsyncMock) as mock_broadcast:
        notif = await notification_service.create_notification(
            db=db_session,
            title="Interview Invitation",
            message="You have an interview scheduled.",
            type="interview",
            target_email="candidate.notif@example.com",
            sender_role="HR"
        )

        assert notif.id is not None
        assert notif.target_email == "candidate.notif@example.com"
        mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_notifications_and_mark_read(db_session):
    with patch("app.services.notification_service.manager.broadcast", new_callable=AsyncMock):
        await notification_service.create_notification(
            db=db_session,
            title="Alert 1",
            message="Msg 1",
            type="alert",
            target_role="CANDIDATE",
            target_email="test.reader@example.com"
        )
        await notification_service.create_notification(
            db=db_session,
            title="Alert 2",
            message="Msg 2",
            type="alert",
            target_role="CANDIDATE",
            target_email="test.reader@example.com"
        )

    # Get notifications
    notifs = await notification_service.get_all_notifications(
        db_session,
        role="CANDIDATE",
        email="test.reader@example.com"
    )
    assert len(notifs) >= 2
    assert all(not getattr(n, "is_read", False) for n in notifs)

    # Mark all as read
    marked = await notification_service.mark_all_as_read(
        db_session,
        role="CANDIDATE",
        email="test.reader@example.com"
    )
    assert marked is True

    # Verify updated
    notifs_after = await notification_service.get_all_notifications(
        db_session,
        role="CANDIDATE",
        email="test.reader@example.com"
    )
    assert all(n.is_read for n in notifs_after)


@pytest.mark.asyncio
async def test_create_notification_broadcast_failure_resilience(db_session):
    # Even if broadcast raises an error, notification is saved to DB
    with patch("app.services.notification_service.manager.broadcast", side_effect=Exception("WebSocket Error")):
        notif = await notification_service.create_notification(
            db=db_session,
            title="Resilience Test",
            message="Testing error catch",
            type="system"
        )
        assert notif is not None
        assert notif.id is not None
