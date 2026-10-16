import pytest
from unittest.mock import patch, AsyncMock
from app.utils.auth import create_access_token
from app.services import notification_service


@pytest.mark.asyncio
async def test_get_and_mark_read_notifications_endpoint(client, db_session):
    hr_token = create_access_token({"sub": "hr_notif@example.com", "role": "HR", "id": 10})
    headers = {"Authorization": f"Bearer {hr_token}"}

    with patch("app.services.notification_service.manager.broadcast", new_callable=AsyncMock):
        await notification_service.create_notification(
            db=db_session,
            title="HR Announcement",
            message="Please review applicants",
            type="announcement",
            target_role="HR",
            target_email="hr_notif@example.com"
        )

    # Get notifications
    get_res = await client.get("/notifications/", headers=headers)
    assert get_res.status_code == 200
    notifs = get_res.json()
    assert len(notifs) >= 1
    assert notifs[0]["title"] == "HR Announcement"

    # Mark all read
    mark_res = await client.put("/notifications/mark-read", headers=headers)
    assert mark_res.status_code == 200


@pytest.mark.asyncio
async def test_notifications_unauthorized_access(client):
    # Without token
    res = await client.get("/notifications/")
    assert res.status_code == 401
