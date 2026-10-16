import pytest
from unittest.mock import patch, AsyncMock
from app.models.hr import HR
from app.models.candidate import Candidate
from app.utils.auth import hash_password, create_access_token


@pytest.mark.asyncio
async def test_chat_controller_endpoints(client, db_session):
    # Active count endpoint (public)
    count_res = await client.get("/chat/active-count")
    assert count_res.status_code == 200
    assert "count" in count_res.json()

    # Setup HR and Candidate
    hr = HR(
        fullname="HR Chat Tester",
        email="hr_chat@example.com",
        password=hash_password("password123"),
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Cand Chat Tester",
        email="cand_chat@example.com",
        password=hash_password("password123"),
        role="CANDIDATE"
    )
    db_session.add_all([hr, cand])
    await db_session.commit()

    token = create_access_token({"sub": "hr_chat@example.com", "role": "HR", "id": hr.id})
    headers = {"Authorization": f"Bearer {token}"}

    # Get contacts
    contacts_res = await client.get("/chat/contacts", headers=headers)
    assert contacts_res.status_code == 200
    assert "users" in contacts_res.json()

    # Send message from HR to Candidate
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        send_res = await client.post(
            f"/chat/messages/{cand.id}",
            headers=headers,
            json={"content": "Hello candidate!"}
        )
        assert send_res.status_code == 200
        msg_data = send_res.json()
        assert msg_data["content"] == "Hello candidate!"
        msg_id = msg_data["id"]

    # Get message history
    hist_res = await client.get(f"/chat/messages/{cand.id}", headers=headers)
    assert hist_res.status_code == 200
    assert len(hist_res.json()) >= 1

    # Archive conversation
    arch_res = await client.post(f"/chat/conversations/{cand.id}/archive", headers=headers)
    assert arch_res.status_code == 200

    # Get archived contacts
    arch_contacts_res = await client.get("/chat/archived-conversations", headers=headers)
    assert arch_contacts_res.status_code == 200
    assert cand.id in arch_contacts_res.json()["archived_contact_ids"]

    # Unarchive conversation
    unarch_res = await client.post(f"/chat/conversations/{cand.id}/unarchive", headers=headers)
    assert unarch_res.status_code == 200

    # Delete single message
    del_msg_res = await client.delete(f"/chat/message/{msg_id}", headers=headers)
    assert del_msg_res.status_code == 200

    # Delete full conversation
    del_conv_res = await client.delete(f"/chat/messages/{cand.id}", headers=headers)
    assert del_conv_res.status_code == 200


@pytest.mark.asyncio
async def test_chat_unauthorized_access(client):
    res = await client.get("/chat/contacts")
    assert res.status_code == 401
