import pytest
from unittest.mock import patch, AsyncMock
from app.services import chat_service
from app.models.user import User
from app.models.hr import HR
from app.models.candidate import Candidate
from app.models.admin import Admin
from app.utils.auth import create_access_token


@pytest.mark.asyncio
async def test_get_allowed_roles():
    assert await chat_service.get_allowed_roles("CANDIDATE") == ["HR"]
    assert await chat_service.get_allowed_roles("candidate") == ["HR"]
    assert await chat_service.get_allowed_roles("HR") == ["CANDIDATE", "ADMIN", "HR"]
    assert await chat_service.get_allowed_roles("ADMIN") == ["HR"]
    assert await chat_service.get_allowed_roles("UNKNOWN") == []


@pytest.mark.asyncio
async def test_verify_token(db_session):
    hr = HR(
        fullname="HR Token User",
        email="hr_token@example.com",
        password="hash",
        role="HR",
        company_name="Mariwasa"
    )
    db_session.add(hr)
    await db_session.flush()

    token = create_access_token({"sub": hr.email, "role": "HR", "id": hr.id})
    verified_user = await chat_service.verify_token(token, db_session)
    assert verified_user is not None
    assert verified_user.email == hr.email

    # Invalid token returns None
    invalid = await chat_service.verify_token("invalid.jwt.token", db_session)
    assert invalid is None


@pytest.mark.asyncio
async def test_send_message_and_role_restrictions(db_session):
    hr = HR(
        fullname="HR Sender",
        email="hr_sender@example.com",
        password="hash",
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Candidate Receiver",
        email="cand_receiver@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add_all([hr, cand])
    await db_session.flush()

    # Candidates cannot send messages directly
    candidate_sent = await chat_service.send_message(
        db=db_session,
        current_user=cand,
        other_user_id=hr.id,
        content="Hello HR"
    )
    assert candidate_sent is None

    # HR can send messages to Candidate
    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock) as mock_send:
        msg = await chat_service.send_message(
            db=db_session,
            current_user=hr,
            other_user_id=cand.id,
            content="Hello Candidate, welcome to Mariwasa!"
        )
        assert msg is not None
        assert msg.id is not None
        assert msg.sender_id == hr.id
        assert msg.receiver_id == cand.id
        assert msg.content == "Hello Candidate, welcome to Mariwasa!"
        assert mock_send.call_count == 2  # Sent to receiver and sender tabs


@pytest.mark.asyncio
async def test_get_messages_and_mark_as_read(db_session):
    hr = HR(
        fullname="HR Reader",
        email="hr_reader@example.com",
        password="hash",
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Candidate Contact",
        email="cand_contact@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add_all([hr, cand])
    await db_session.flush()

    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        await chat_service.send_message(
            db=db_session,
            current_user=hr,
            other_user_id=cand.id,
            content="Message 1"
        )

    # Candidate views messages from HR (marks incoming messages as read)
    messages = await chat_service.get_messages(db_session, cand, hr.id)
    assert len(messages) >= 1
    assert messages[0].content == "Message 1"


@pytest.mark.asyncio
async def test_archive_and_unarchive_conversation(db_session):
    hr = HR(
        fullname="HR Archiver",
        email="hr_archiver@example.com",
        password="hash",
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Candidate To Archive",
        email="cand_archive@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add_all([hr, cand])
    await db_session.flush()

    # Archive
    archived = await chat_service.archive_conversation(db_session, hr.id, cand.id)
    assert archived is True

    archived_ids = await chat_service.get_archived_contact_ids(db_session, hr.id)
    assert cand.id in archived_ids

    # Unarchive
    unarchived = await chat_service.unarchive_conversation(db_session, hr.id, cand.id)
    assert unarchived is True

    archived_ids_after = await chat_service.get_archived_contact_ids(db_session, hr.id)
    assert cand.id not in archived_ids_after


@pytest.mark.asyncio
async def test_delete_message_and_conversation(db_session):
    hr = HR(
        fullname="HR Deleter",
        email="hr_deleter@example.com",
        password="hash",
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Candidate Deleted",
        email="cand_deleter@example.com",
        password="hash",
        role="CANDIDATE"
    )
    db_session.add_all([hr, cand])
    await db_session.flush()

    with patch("app.services.chat_service.manager.send_personal_message", new_callable=AsyncMock):
        msg = await chat_service.send_message(
            db=db_session,
            current_user=hr,
            other_user_id=cand.id,
            content="To be deleted"
        )

    # Delete single message
    deleted = await chat_service.delete_single_message(db_session, hr, msg.id)
    assert deleted is True

    # Delete entire conversation
    await chat_service.delete_conversation(db_session, hr.id, cand.id)
    remaining = await chat_service.get_messages(db_session, hr, cand.id)
    assert len(remaining) == 0
