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


@pytest.mark.asyncio
async def test_mark_single_notification_read_endpoint(client, db_session):
    cand_token = create_access_token({"sub": "cand_single@example.com", "role": "CANDIDATE", "id": 11})
    other_token = create_access_token({"sub": "other_cand@example.com", "role": "CANDIDATE", "id": 12})
    headers = {"Authorization": f"Bearer {cand_token}"}
    other_headers = {"Authorization": f"Bearer {other_token}"}

    with patch("app.services.notification_service.manager.broadcast", new_callable=AsyncMock):
        n1 = await notification_service.create_notification(
            db=db_session,
            title="New Message: General",
            message="HR Team: Hello!",
            type="message",
            target_role="CANDIDATE",
            target_email="cand_single@example.com",
            sender_role="HR",
        )
        n2 = await notification_service.create_notification(
            db=db_session,
            title="Interview Update",
            message="Scheduled tomorrow",
            type="schedule",
            target_role="CANDIDATE",
            target_email="cand_single@example.com",
            sender_role="HR",
        )

    # Another candidate cannot mark someone else's notification as read
    forbidden_res = await client.put(f"/notifications/{n1.id}/read", headers=other_headers)
    assert forbidden_res.status_code == 404

    # Owner marks only n1 as read
    ok_res = await client.put(f"/notifications/{n1.id}/read", headers=headers)
    assert ok_res.status_code == 200

    list_res = await client.get("/notifications/", headers=headers)
    assert list_res.status_code == 200
    items = {item["id"]: item for item in list_res.json()}
    assert items[n1.id]["is_read"] is True
    assert items[n2.id]["is_read"] is False
