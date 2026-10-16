import pytest
from app.repositories import chat_repository
from app.models.user import User
from app.models.candidate import Candidate
from app.models.hr import HR
from app.utils.auth import hash_password


@pytest.mark.asyncio
async def test_chat_repo_messaging_and_history(db_session):
    hr = HR(
        fullname="Chat HR Sender",
        email="chat_hr_sender@example.com",
        password=hash_password("pass123"),
        role="HR",
        company_name="Mariwasa"
    )
    cand = Candidate(
        fullname="Chat Cand Receiver",
        email="chat_cand_receiver@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    db_session.add_all([hr, cand])
    await db_session.commit()
    hr_id = hr.id
    cand_id = cand.id

    # 1. Get user by email and ID
    by_email = await chat_repository.get_user_by_email(db_session, "chat_hr_sender@example.com")
    assert by_email is not None
    assert by_email.id == hr_id

    by_id = await chat_repository.get_user_by_id(db_session, cand_id)
    assert by_id is not None
    assert by_id.email == "chat_cand_receiver@example.com"

    # 2. Get contacts
    contacts = await chat_repository.get_contact_users(db_session, ["CANDIDATE"], hr_id)
    assert len(contacts) >= 1
    assert any(c.id == cand_id for c in contacts)

    # 3. Create message
    msg = await chat_repository.create_message(db_session, hr_id, cand_id, "Hello from HR!")
    assert msg.id is not None
    assert msg.content == "Hello from HR!"
    msg_id = msg.id

    # 4. Get last message
    last_msg = await chat_repository.get_last_message_between(db_session, hr_id, cand_id)
    assert last_msg is not None
    assert last_msg.id == msg_id

    # 5. Unread count and unread messages
    unread_count = await chat_repository.get_unread_count(db_session, hr_id, cand_id)
    assert unread_count == 1

    unread_msgs = await chat_repository.get_unread_messages(db_session, hr_id, cand_id)
    assert len(unread_msgs) == 1

    # 6. Mark as read
    await chat_repository.mark_messages_as_read(db_session, unread_msgs)
    after_read_count = await chat_repository.get_unread_count(db_session, hr_id, cand_id)
    assert after_read_count == 0

    # 7. Get chat history
    history = await chat_repository.get_chat_history(db_session, hr_id, cand_id)
    assert len(history) == 1

    # 8. Delete message by id
    del_single = await chat_repository.delete_message_by_id(db_session, msg_id, hr_id, "HR")
    assert del_single is True

    # 9. Create another message and delete conversation
    msg2 = await chat_repository.create_message(db_session, hr_id, cand_id, "Second message")
    await chat_repository.delete_messages_between(db_session, hr_id, cand_id)
    history_after = await chat_repository.get_chat_history(db_session, hr_id, cand_id)
    assert len(history_after) == 0


@pytest.mark.asyncio
async def test_chat_repo_archive_and_unarchive(db_session):
    u1 = User(
        fullname="Archive Tester 1",
        email="arch_test1@example.com",
        password=hash_password("pass123"),
        role="HR"
    )
    u2 = User(
        fullname="Archive Tester 2",
        email="arch_test2@example.com",
        password=hash_password("pass123"),
        role="CANDIDATE"
    )
    db_session.add_all([u1, u2])
    await db_session.commit()
    u1_id = u1.id
    u2_id = u2.id

    # Archive
    archived = await chat_repository.archive_conversation(db_session, u1_id, u2_id)
    assert archived is True

    # Get archived contact IDs
    arch_ids = await chat_repository.get_archived_contact_ids(db_session, u1_id)
    assert u2_id in arch_ids

    # Unarchive
    unarchived = await chat_repository.unarchive_conversation(db_session, u1_id, u2_id)
    assert unarchived is True

    after_unarch = await chat_repository.get_archived_contact_ids(db_session, u1_id)
    assert u2_id not in after_unarch
