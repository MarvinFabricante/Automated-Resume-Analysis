import sys
import json
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.utils.auth import SECRET_KEY, ALGORITHM
from app.models.user import User
from app.models.message import Message
from app.schemas.message_schema import ChatUser
from app.utils.websocket_manager import manager
from app.utils.cache import get_cache, set_cache, clear_cache_pattern
from app.repositories.chat_repository import ChatRepository


async def get_allowed_roles(user_role: str) -> List[str]:
    """
    Returns the list of roles that the given user role is allowed to message.
    """
    role = user_role.upper()
    if role == "CANDIDATE":
        return ["HR"]
    elif role == "HR":
        return ["CANDIDATE", "ADMIN", "HR"]
    elif role == "ADMIN":
        return ["HR"]
    return []


async def verify_token(token: str, db: AsyncSession):
    """
    Verifies the JWT token and returns the corresponding User object.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        return await ChatRepository.get_user_by_email(db, email)
    except JWTError:
        return None


async def get_contacts(db: AsyncSession, current_user: User, search: Optional[str] = None) -> List[ChatUser]:
    """
    Fetches the list of contacts for the current user, including last message and unread count.
    Uses in-memory caching to improve performance.
    """
    cache_key = f"contacts:{current_user.id}:{search or ''}"

    # Try to get from cache
    cached_data = await get_cache(cache_key)
    if cached_data:
        try:
            chat_users = []
            for u_data in cached_data:
                # Convert back to ChatUser objects and refresh online status
                u_data['is_online'] = await manager.is_user_online(u_data['id'])
                if u_data.get('last_message_time'):
                    u_data['last_message_time'] = datetime.fromisoformat(u_data['last_message_time'])
                chat_users.append(ChatUser(**u_data))
            return chat_users
        except Exception:
            pass # Fallback to DB if cache parsing fails

    allowed_roles = await get_allowed_roles(current_user.role)
    if not allowed_roles:
        return []

    users = await ChatRepository.get_contact_users(db, allowed_roles, current_user.id, search)
    archived_contact_ids = await ChatRepository.get_archived_contact_ids(db, current_user.id)
    archived_set = set(archived_contact_ids)

    chat_users = []
    for u in users:
        # Get last message
        last_msg = await ChatRepository.get_last_message_between(db, current_user.id, u.id)

        # Unread count
        unread_count = await ChatRepository.get_unread_count(db, u.id, current_user.id)

        chat_users.append(ChatUser(
            id=u.id,
            fullname=u.fullname,
            role=u.role,
            profile_image_url=u.profile_image_url,
            is_online=await manager.is_user_online(u.id),
            last_message=last_msg.content if last_msg else None,
            last_message_time=last_msg.timestamp if last_msg else None,
            unread_count=unread_count,
            is_archived=(u.id in archived_set)
        ))

    # Sort by recent message time
    chat_users.sort(key=lambda x: x.last_message_time.timestamp() if x.last_message_time else 0, reverse=True)

    # Save to cache (TTL 10 seconds for safety, though we invalidate on message events)
    cache_users = []
    for u in chat_users:
        u_dict = u.model_dump() if hasattr(u, 'model_dump') else u.dict()
        if u_dict.get('last_message_time'):
            u_dict['last_message_time'] = u_dict['last_message_time'].isoformat()
        cache_users.append(u_dict)

    await set_cache(cache_key, cache_users, ttl=10)
    return chat_users


async def invalidate_contacts_cache(user_id: int):
    """Invalidates the contacts cache for a specific user."""
    await clear_cache_pattern(f"contacts:{user_id}:")


async def get_messages(db: AsyncSession, current_user: User, other_user_id: int) -> List[Message]:
    """
    Retrieves message history between the current user and another user,
    and marks all incoming messages as read.
    """
    # Mark messages as read
    unreads = await ChatRepository.get_unread_messages(db, other_user_id, current_user.id)
    if unreads:
        await ChatRepository.mark_messages_as_read(db, unreads)
        # Invalidate cache for current user since unread counts changed
        await invalidate_contacts_cache(current_user.id)

    # Get history
    return await ChatRepository.get_chat_history(db, current_user.id, other_user_id)


class ConversationClosedError(Exception):
    """Raised when attempting to send a message in a closed or read-only conversation."""
    pass


async def get_thread_status(
    db: AsyncSession,
    current_user: User,
    other_user_id: int,
    application_id: Optional[int] = None,
) -> dict:
    """
    Determine whether a conversation thread is open or closed (read-only):
    - HR <-> HR / Admin threads are always open.
    - For Candidate <-> HR threads:
      - If a specific application_id is given, evaluate that application;
        otherwise evaluate the candidate's applications collectively.
      - Active application(s) -> open.
      - Withdrawn application -> read-only immediately ('This conversation is closed').
      - Finished (Passed / Not Selected) -> open for configurable `messaging_closure_days`
        (default 30 days) after `resolved_at`, then read-only ('This conversation is closed').
    """
    from datetime import timedelta
    from sqlalchemy import func, or_, select
    from app.models.job_application import JobApplication
    from app.services.retention_service import is_application_active
    from app.services.status_management_service import is_withdrawn_status
    from app.services.system_config_service import system_config_service

    other_user = await ChatRepository.get_user_by_id(db, other_user_id)
    if not other_user:
        return {"is_closed": True, "can_reply": False, "reason": "User not found", "closes_at": None}

    cand_user = None
    if (current_user.role or "").upper() == "CANDIDATE":
        cand_user = current_user
    elif (other_user.role or "").upper() == "CANDIDATE":
        cand_user = other_user

    if not cand_user:
        return {"is_closed": False, "can_reply": True, "reason": None, "closes_at": None}

    if getattr(cand_user, "is_deactivated", False) or getattr(cand_user, "is_anonymized", False):
        return {
            "is_closed": True,
            "can_reply": False,
            "reason": "This conversation is closed",
            "closes_at": None,
        }

    if application_id is not None:
        apps_res = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
        apps = list(apps_res.scalars().all())
    else:
        norm_email = (cand_user.email or "").strip().lower()
        apps_res = await db.execute(
            select(JobApplication).where(
                or_(
                    JobApplication.user_id == cand_user.id,
                    func.lower(JobApplication.candidate_email) == norm_email,
                )
            )
        )
        apps = list(apps_res.scalars().all())

    if not apps:
        return {"is_closed": False, "can_reply": True, "reason": None, "closes_at": None}

    # If any relevant application is still active, thread stays open
    if any(is_application_active(a.status) for a in apps):
        return {"is_closed": False, "can_reply": True, "reason": None, "closes_at": None}

    now = datetime.utcnow()
    closure_days = await system_config_service.get_messaging_closure_days(db)

    latest_closes_at = None
    for app in apps:
        if is_withdrawn_status(app.status):
            # Withdrawn applications are read-only immediately
            continue
        if app.messaging_closed_at and app.messaging_closed_at <= now:
            continue
        resolved_ref = app.resolved_at or app.updated_at or app.created_at
        if resolved_ref:
            closes_at = resolved_ref + timedelta(days=int(closure_days))
            if closes_at > now:
                if latest_closes_at is None or closes_at > latest_closes_at:
                    latest_closes_at = closes_at

    if latest_closes_at is not None:
        return {
            "is_closed": False,
            "can_reply": True,
            "reason": None,
            "closes_at": latest_closes_at.isoformat(),
        }

    return {
        "is_closed": True,
        "can_reply": False,
        "reason": "This conversation is closed",
        "closes_at": None,
    }


async def send_message(
    db: AsyncSession, 
    current_user: User, 
    other_user_id: int, 
    content: str, 
    client_id: Optional[str] = None,
    message_type: Optional[str] = "general",
    application_id: Optional[int] = None
) -> Optional[Message]:
    """
    Sends a message to another user if the roles are compatible and the conversation
    thread has not closed, then broadcasts it via WebSocket.
    Applicants can view and reply until the thread closes (withdrawn = immediate;
    finished = after configured messaging closure period, default 30 days).
    """
    # Verify allowed to message
    allowed_roles = await get_allowed_roles(current_user.role)
    receiver = await ChatRepository.get_user_by_id(db, other_user_id)

    if not receiver or receiver.role not in allowed_roles:
        return None

    # Enforce thread closure window for Candidate <-> HR conversations
    thread_status = await get_thread_status(
        db=db,
        current_user=current_user,
        other_user_id=other_user_id,
        application_id=application_id,
    )
    if thread_status.get("is_closed"):
        raise ConversationClosedError(thread_status.get("reason") or "This conversation is closed")

    new_msg = await ChatRepository.create_message(
        db, 
        current_user.id, 
        other_user_id, 
        content,
        message_type=message_type or "general",
        application_id=application_id
    )

    msg_data = {
        "type": "new_message",
        "id": new_msg.id,
        "sender_id": new_msg.sender_id,
        "receiver_id": new_msg.receiver_id,
        "application_id": new_msg.application_id,
        "message_type": new_msg.message_type,
        "content": new_msg.content,
        "timestamp": new_msg.timestamp.isoformat(),
        "is_read": new_msg.is_read,
        "client_id": client_id
    }

    # Broadcast to receiver
    await manager.send_personal_message(msg_data, other_user_id)
    # Also to sender (if they have multiple tabs open)
    await manager.send_personal_message(msg_data, current_user.id)

    # Invalidate caches
    await invalidate_contacts_cache(current_user.id)
    await invalidate_contacts_cache(other_user_id)

    # Create in-app notification & email for receiver (REQ064)
    try:
        from app.services.notification_service import create_notification
        sender_name = (getattr(current_user, "fullname", None) or "").strip() or getattr(current_user, "email", "HR")
        content_preview = content.strip()
        preview = (content_preview[:100] + "...") if len(content_preview) > 100 else content_preview
        await create_notification(
            db=db,
            title=f"New Message: {(message_type or 'General').title()}",
            message=f"{sender_name}: {preview}",
            type="message",
            target_role=receiver.role.upper() if receiver.role else None,
            target_email=receiver.email.lower() if receiver.email else None,
            sender_role=current_user.role.upper() if current_user.role else None,
        )

        if receiver.email:
            try:
                from app.services.email_service import send_hr_message_notification_email
                await send_hr_message_notification_email(
                    to_email=receiver.email,
                    candidate_name=receiver.fullname or "Applicant",
                    sender_name=sender_name,
                    message_type=message_type or "general",
                    content=content
                )
            except Exception as email_err:
                logging.warning(f"Failed to dispatch message notification email: {email_err}")
    except Exception as e_notif:
        logging.warning(f"Failed to create chat notification: {e_notif}")

    return new_msg


async def handle_websocket_message(db_factory, sender_id: int, data: dict):
    """
    Handles a message received through a WebSocket connection.
    Parses the data, saves the message to the database, and broadcasts it.
    """
    try:
        receiver_id = data.get("receiver_id")
        content = data.get("content")
        client_id = data.get("client_id")

        if not receiver_id or not content:
            return

        async with db_factory() as db:
            # Get sender object
            sender = await ChatRepository.get_user_by_id(db, sender_id)
            if not sender:
                return

            # Use existing send_message logic
            try:
                await send_message(
                    db,
                    sender,
                    receiver_id,
                    content,
                    client_id=client_id,
                    application_id=data.get("application_id"),
                )
            except ConversationClosedError as closed_err:
                await manager.send_personal_message(
                    {
                        "type": "conversation_closed",
                        "receiver_id": receiver_id,
                        "detail": str(closed_err),
                        "client_id": client_id,
                    },
                    sender_id,
                )

    except Exception as e:
        # Log error but don't crash the WS loop
        logging.error(f"Error handling WS message: {e}")


async def delete_conversation(db: AsyncSession, current_user_id: int, other_user_id: int):
    """Deletes all messages exchanged between current user and contact."""
    await ChatRepository.delete_messages_between(db, current_user_id, other_user_id)


async def delete_single_message(db: AsyncSession, current_user: User, message_id: int) -> bool:
    """Deletes a single message if user is sender or admin."""
    return await ChatRepository.delete_message_by_id(db, message_id, current_user.id, current_user.role)


async def get_archived_contact_ids(db: AsyncSession, user_id: int) -> List[int]:
    """Retrieves list of contact IDs archived by the specified user."""
    return await ChatRepository.get_archived_contact_ids(db, user_id)


async def archive_conversation(db: AsyncSession, user_id: int, contact_id: int) -> bool:
    """Archives conversation with contact_id for user_id."""
    success = await ChatRepository.archive_conversation(db, user_id, contact_id)
    await invalidate_contacts_cache(user_id)
    return success


async def unarchive_conversation(db: AsyncSession, user_id: int, contact_id: int) -> bool:
    """Unarchives conversation with contact_id for user_id."""
    success = await ChatRepository.unarchive_conversation(db, user_id, contact_id)
    await invalidate_contacts_cache(user_id)
    return success


async def broadcast_job_message(
    db: AsyncSession,
    current_user: User,
    job_id: int,
    content: str,
    message_type: str = "announcement",
    target_group: str = "all"
) -> int:
    """
    Broadcast a single message to all or shortlisted applicants for a specific job posting (REQ062, REQ064).
    """
    if current_user.role.upper() == "CANDIDATE":
        return 0

    from app.repositories.job_application_repository import JobApplicationRepository
    from app.repositories.job_description_repository import JobDescriptionRepository
    from app.services.email_service import send_hr_message_notification_email

    job = await JobDescriptionRepository.get_by_id(db, job_id)
    job_title = job.job_title if job else "Mariwasa Position"

    applications = await JobApplicationRepository.get_by_job_id(db, job_id)
    if not applications:
        return 0

    if target_group.lower() == "shortlisted":
        applications = [a for a in applications if (getattr(a, "status", "") or "").upper() in ("SHORTLISTED", "SHORTLIST")]

    sent_count = 0
    sender_name = (getattr(current_user, "fullname", None) or "").strip() or getattr(current_user, "email", "HR Panel")

    seen_recipients = set()
    for app in applications:
        app_uid = getattr(app, "user_id", None)
        email = (app.candidate_email or "").strip().lower()
        recipient_key = f"uid_{app_uid}" if app_uid else email
        if not recipient_key or recipient_key in seen_recipients:
            continue
        seen_recipients.add(recipient_key)

        candidate_user = None
        if app_uid:
            candidate_user = await ChatRepository.get_user_by_id(db, app_uid)
        if not candidate_user and email:
            candidate_user = await ChatRepository.get_user_by_email(db, email)
        if candidate_user:
            await send_message(
                db=db,
                current_user=current_user,
                other_user_id=candidate_user.id,
                content=content,
                message_type=message_type,
                application_id=app.id
            )
            sent_count += 1
        elif email:
            try:
                from app.services.notification_service import create_notification
                await create_notification(
                    db=db,
                    title=f"New Announcement: {job_title}",
                    message=f"{sender_name}: {content[:100]}...",
                    type="message",
                    target_role="CANDIDATE",
                    target_email=email,
                    sender_role=current_user.role.upper()
                )
                await send_hr_message_notification_email(
                    to_email=email,
                    candidate_name=app.candidate_name or "Applicant",
                    sender_name=sender_name,
                    message_type=message_type,
                    content=content,
                    job_title=job_title
                )
                sent_count += 1
            except Exception as direct_err:
                logging.warning(f"Failed to dispatch broadcast to {email}: {direct_err}")

    return sent_count


async def get_sent_messages(db: AsyncSession, current_user: User) -> list:
    """Retrieve all messages sent by HR with receiver details and read receipts (REQ063, REQ065)."""
    messages = await ChatRepository.get_sent_messages(db, current_user.id)
    records = []
    for msg in messages:
        rec_name = getattr(msg.receiver, "fullname", "Candidate") if msg.receiver else "Candidate"
        rec_email = getattr(msg.receiver, "email", "") if msg.receiver else ""
        job_title = None
        if msg.job_application and getattr(msg.job_application, "job", None):
            job_title = getattr(msg.job_application.job, "job_title", None)
        elif msg.job_application:
            job_title = getattr(msg.job_application, "job_title", None)

        records.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "receiver_id": msg.receiver_id,
            "receiver_name": rec_name,
            "receiver_email": rec_email,
            "application_id": msg.application_id,
            "job_title": job_title,
            "message_type": msg.message_type or "general",
            "content": msg.content,
            "timestamp": msg.timestamp,
            "is_read": msg.is_read,
            "read_at": msg.read_at
        })
    return records


async def mark_single_message_read(db: AsyncSession, message_id: int, current_user: User):
    """Mark a message as read when opened (REQ063)."""
    return await ChatRepository.mark_single_message_read(db, message_id, current_user.id)


chat_service = sys.modules[__name__]


