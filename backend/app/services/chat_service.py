import html
import logging
import os
import re
import sys
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.job_application import JobApplication
from app.models.message import ApplicationThread, Message
from app.models.user import User
from app.repositories.chat_repository import ChatRepository
from app.schemas.message_schema import ChatUser
from app.utils.auth import ALGORITHM, SECRET_KEY
from app.utils.cache import clear_cache_pattern, get_cache, set_cache
from app.utils.file_validator import validate_file_content
from app.utils.websocket_manager import manager

logger = logging.getLogger(__name__)

# ─── Anti-Abuse Constants ─────────────────────────────────────────────────────

MAX_MESSAGE_LENGTH = 2000
RATE_LIMIT_MAX_MESSAGES = 10
RATE_LIMIT_WINDOW_SECONDS = 60
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_ATTACHMENT_EXTS = {"pdf", "png", "jpg", "jpeg"}
ATTACHMENT_MIME_MAP = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}
CHAT_ATTACHMENTS_DIR = "uploads/chat_attachments"

# In-memory fallback sliding-window rate limiter (used when Redis is unreachable)
_in_memory_rate_buckets: Dict[int, deque] = defaultdict(deque)

# Small plain-text HR message templates (editable before sending)
HR_MESSAGE_TEMPLATES: List[Dict[str, str]] = [
    {
        "key": "request_clarification",
        "label": "Request for clarification",
        "body": (
            "Hi {candidate_name}, thank you for applying for the {job_title} position. "
            "Could you please clarify a quick detail about your recent experience or qualifications?"
        ),
    },
    {
        "key": "interview_reminder",
        "label": "Interview reminder",
        "body": (
            "Hi {candidate_name}, this is a friendly reminder about your upcoming interview "
            "for the {job_title} position. Please reply here if you have any questions."
        ),
    },
    {
        "key": "document_request",
        "label": "Document request",
        "body": (
            "Hi {candidate_name}, for your {job_title} application, could you please share a copy "
            "of the requested supporting document (PDF, PNG, or JPG) when you have a moment?"
        ),
    },
]

_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


# ─── Domain Exceptions ────────────────────────────────────────────────────────

class ConversationClosedError(Exception):
    """Raised when attempting to send a message in a closed or read-only conversation."""
    pass


class ThreadNotStartedError(Exception):
    """Raised when an applicant tries to create a thread or message before HR starts it."""
    pass


class MessageValidationError(Exception):
    """Raised when message text or attachment fails validation."""
    pass


class ChatRateLimitError(Exception):
    """Raised when a user exceeds the per-minute messaging rate limit."""
    pass


class ThreadAccessDeniedError(Exception):
    """Raised when a user tries to access or post to a thread they do not belong to."""
    pass


# ─── Helpers: Sanitization, Rate Limiting, Attachments, Serialization ─────────

def _is_hr_or_admin(role: Optional[str]) -> bool:
    return (role or "").strip().upper() in {"HR", "ADMIN", "SUPERADMIN"}


def sanitize_message_text(raw: Optional[str], allow_empty: bool = False) -> str:
    """
    Strip HTML/script/style tags and control characters so only plain text is stored.
    Enforces MAX_MESSAGE_LENGTH.
    """
    text = raw or ""
    # Unescape entities first so encoded tags like &lt;script&gt; are also stripped cleanly
    text = html.unescape(text)
    text = _SCRIPT_STYLE_RE.sub("", text)
    text = _HTML_TAG_RE.sub("", text)
    # Remove null/control characters except newline & tab
    text = "".join(ch for ch in text if ch in ("\n", "\t") or ord(ch) >= 32)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip()

    if not text and not allow_empty:
        raise MessageValidationError("Message cannot be empty.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise MessageValidationError(
            f"Message is too long (maximum {MAX_MESSAGE_LENGTH:,} characters)."
        )
    return text


async def enforce_chat_rate_limit(user_id: int) -> None:
    """
    Enforce a per-user sliding-window rate limit (10 messages / 60 seconds).
    Uses Redis when available and falls back to an in-memory sliding window.
    """
    now = time.time()
    redis_checked = False
    try:
        from app.utils.redis_client import get_async_redis, is_redis_available
        if await is_redis_available():
            client = get_async_redis()
            key = f"chat:ratelimit:{user_id}"
            window_start = now - RATE_LIMIT_WINDOW_SECONDS
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = await pipe.execute()
            current_count = int(results[1] or 0)
            if current_count >= RATE_LIMIT_MAX_MESSAGES:
                raise ChatRateLimitError(
                    f"Rate limit reached ({RATE_LIMIT_MAX_MESSAGES} messages per minute). Please wait a moment and try again."
                )
            member = f"{now}:{uuid.uuid4().hex[:8]}"
            pipe2 = client.pipeline()
            pipe2.zadd(key, {member: now})
            pipe2.expire(key, RATE_LIMIT_WINDOW_SECONDS + 5)
            await pipe2.execute()
            redis_checked = True
    except ChatRateLimitError:
        raise
    except Exception as exc:
        logger.debug(f"Redis chat rate limit unavailable, falling back to memory: {exc}")

    if not redis_checked:
        bucket = _in_memory_rate_buckets[user_id]
        cutoff = now - RATE_LIMIT_WINDOW_SECONDS
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= RATE_LIMIT_MAX_MESSAGES:
            raise ChatRateLimitError(
                f"Rate limit reached ({RATE_LIMIT_MAX_MESSAGES} messages per minute). Please wait a moment and try again."
            )
        bucket.append(now)


def reset_in_memory_rate_limits() -> None:
    """Helper for tests to reset in-memory rate limit buckets."""
    _in_memory_rate_buckets.clear()


async def validate_and_save_chat_attachment(
    file_bytes: bytes,
    original_filename: str,
) -> Dict[str, Any]:
    """Validate (pdf/png/jpg, <= 5MB, magic-byte checked) and persist a chat attachment."""
    clean_orig = os.path.basename(original_filename or "attachment").strip()
    ext = os.path.splitext(clean_orig)[1].lower().strip(".")
    if ext not in ALLOWED_ATTACHMENT_EXTS:
        raise MessageValidationError(
            "Unsupported attachment type. Only PDF, PNG, and JPG files are allowed."
        )
    if not file_bytes or len(file_bytes) == 0:
        raise MessageValidationError("Attachment file is empty.")
    if len(file_bytes) > MAX_ATTACHMENT_BYTES:
        raise MessageValidationError("Attachment exceeds the 5 MB size limit.")

    is_valid, err = validate_file_content(file_bytes, clean_orig)
    if not is_valid:
        raise MessageValidationError(err or "Invalid attachment content.")

    os.makedirs(CHAT_ATTACHMENTS_DIR, exist_ok=True)
    safe_base = re.sub(r"[^A-Za-z0-9._-]+", "_", clean_orig)[:80]
    stored_name = f"{int(time.time())}_{uuid.uuid4().hex[:8]}_{safe_base}"
    stored_path = os.path.join(CHAT_ATTACHMENTS_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)

    return {
        "attachment_url": stored_path,
        "attachment_name": clean_orig,
        "attachment_type": ATTACHMENT_MIME_MAP.get(ext, "application/octet-stream"),
        "attachment_size": len(file_bytes),
    }


def serialize_message(msg: Message, sender: Optional[User] = None) -> Dict[str, Any]:
    sender_obj = sender or getattr(msg, "sender", None)
    sender_name = None
    sender_role = None
    if sender_obj is not None:
        sender_name = (getattr(sender_obj, "fullname", None) or "").strip() or getattr(sender_obj, "email", None)
        sender_role = getattr(sender_obj, "role", None)

    has_att = bool(getattr(msg, "attachment_url", None))
    return {
        "id": msg.id,
        "thread_id": getattr(msg, "thread_id", None),
        "sender_id": msg.sender_id,
        "sender_name": sender_name,
        "sender_role": sender_role,
        "receiver_id": msg.receiver_id,
        "application_id": msg.application_id,
        "message_type": msg.message_type or "general",
        "content": msg.content,
        "attachment_url": f"/chat/attachments/{msg.id}" if has_att and msg.id else None,
        "attachment_name": getattr(msg, "attachment_name", None) if has_att else None,
        "attachment_type": getattr(msg, "attachment_type", None) if has_att else None,
        "attachment_size": getattr(msg, "attachment_size", None) if has_att else None,
        "is_reported": bool(getattr(msg, "is_reported", False)),
        "timestamp": msg.timestamp,
        "is_read": bool(msg.is_read),
        "read_at": msg.read_at,
    }


def get_hr_message_templates(
    candidate_name: Optional[str] = None,
    job_title: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Return editable plain-text HR message templates."""
    cand = (candidate_name or "Applicant").strip()
    role = (job_title or "the position").strip()
    out: List[Dict[str, str]] = []
    for tmpl in HR_MESSAGE_TEMPLATES:
        out.append({
            "key": tmpl["key"],
            "label": tmpl["label"],
            "body": tmpl["body"].format(candidate_name=cand, job_title=role),
        })
    return out


# ─── Existing / Legacy Chat Service Functions (Preserved & Hardened) ─────────

async def get_allowed_roles(user_role: str) -> List[str]:
    """
    Returns the list of roles that the given user role is allowed to message.
    """
    role = (user_role or "").upper()
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
    For CANDIDATE users, ONLY HR contacts who have already sent a message to the candidate are shown.
    """
    cache_key = f"contacts:{current_user.id}:{search or ''}"

    cached_data = await get_cache(cache_key)
    if cached_data:
        try:
            chat_users = []
            for u_data in cached_data:
                u_data["is_online"] = await manager.is_user_online(u_data["id"])
                if u_data.get("last_message_time"):
                    u_data["last_message_time"] = datetime.fromisoformat(u_data["last_message_time"])
                chat_users.append(ChatUser(**u_data))
            return chat_users
        except Exception:
            pass

    allowed_roles = await get_allowed_roles(current_user.role)
    if not allowed_roles:
        return []

    users = await ChatRepository.get_contact_users(db, allowed_roles, current_user.id, search)
    archived_contact_ids = await ChatRepository.get_archived_contact_ids(db, current_user.id)
    archived_set = set(archived_contact_ids)
    is_candidate = (current_user.role or "").upper() == "CANDIDATE"

    chat_users = []
    for u in users:
        if is_candidate:
            # Applicants must never see HR contacts who have not started a conversation with them
            started = await ChatRepository.has_hr_started_message_between(
                db, candidate_id=current_user.id, hr_user_id=u.id
            )
            if not started:
                continue

        last_msg = await ChatRepository.get_last_message_between(db, current_user.id, u.id)
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
            is_archived=(u.id in archived_set),
        ))

    chat_users.sort(key=lambda x: x.last_message_time.timestamp() if x.last_message_time else 0, reverse=True)

    cache_users = []
    for u in chat_users:
        u_dict = u.model_dump() if hasattr(u, "model_dump") else u.dict()
        if u_dict.get("last_message_time"):
            u_dict["last_message_time"] = u_dict["last_message_time"].isoformat()
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
    unreads = await ChatRepository.get_unread_messages(db, other_user_id, current_user.id)
    if unreads:
        await ChatRepository.mark_messages_as_read(db, unreads)
        await invalidate_contacts_cache(current_user.id)
        try:
            await manager.send_personal_message(
                {
                    "type": "messages_seen",
                    "reader_id": current_user.id,
                    "other_user_id": other_user_id,
                    "message_ids": [m.id for m in unreads if m.id],
                    "read_at": datetime.now(timezone.utc).isoformat(),
                },
                other_user_id,
            )
        except Exception:
            pass

    return await ChatRepository.get_chat_history(db, current_user.id, other_user_id)


# ─── Thread Closure Rules ─────────────────────────────────────────────────────

async def evaluate_application_closure(
    db: AsyncSession,
    app: JobApplication,
    candidate_user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Evaluate read-only / closure status for a single application thread:
      - Withdrawn -> read-only immediately ('This conversation is closed').
      - Deactivated or anonymized candidate -> read-only ('This conversation is closed').
      - Active application -> open.
      - Resolved (Passed / Not Selected / etc.) -> open for configurable
        `messaging_closure_days` (default 30 days) after `resolved_at`, then
        read-only ('This conversation is closed').
    """
    from app.services.retention_service import is_application_active
    from app.services.status_management_service import is_withdrawn_status
    from app.services.system_config_service import system_config_service

    if candidate_user is not None:
        if getattr(candidate_user, "is_deactivated", False) or getattr(candidate_user, "is_anonymized", False):
            return {
                "is_closed": True,
                "can_reply": False,
                "reason": "This conversation is closed",
                "closes_at": None,
            }

    if getattr(app, "is_anonymized", False):
        return {
            "is_closed": True,
            "can_reply": False,
            "reason": "This conversation is closed",
            "closes_at": None,
        }

    if is_withdrawn_status(app.status):
        return {
            "is_closed": True,
            "can_reply": False,
            "reason": "This conversation is closed",
            "closes_at": None,
        }

    if is_application_active(app.status):
        return {
            "is_closed": False,
            "can_reply": True,
            "reason": None,
            "closes_at": None,
        }

    now = datetime.utcnow()
    if app.messaging_closed_at and app.messaging_closed_at <= now:
        return {
            "is_closed": True,
            "can_reply": False,
            "reason": "This conversation is closed",
            "closes_at": None,
        }

    closure_days = await system_config_service.get_messaging_closure_days(db)
    resolved_ref = app.resolved_at or app.updated_at or app.created_at
    if resolved_ref:
        # Normalize timezone-aware datetime to naive UTC if needed
        if getattr(resolved_ref, "tzinfo", None) is not None:
            resolved_ref = resolved_ref.astimezone(timezone.utc).replace(tzinfo=None)
        closes_at = resolved_ref + timedelta(days=int(closure_days))
        if closes_at > now:
            return {
                "is_closed": False,
                "can_reply": True,
                "reason": None,
                "closes_at": closes_at.isoformat(),
            }

    return {
        "is_closed": True,
        "can_reply": False,
        "reason": "This conversation is closed",
        "closes_at": None,
    }


async def get_thread_status(
    db: AsyncSession,
    current_user: User,
    other_user_id: int,
    application_id: Optional[int] = None,
) -> dict:
    """
    Determine whether a conversation thread is open or closed (read-only).
    Also reflects HR-first rule for applicants when no HR-started thread exists.
    """
    other_user = await ChatRepository.get_user_by_id(db, other_user_id)
    if not other_user:
        return {"is_closed": True, "can_reply": False, "reason": "User not found", "closes_at": None}

    cand_user = None
    is_cand_requester = (current_user.role or "").upper() == "CANDIDATE"
    if is_cand_requester:
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
        app = apps_res.scalar_one_or_none()
        if not app:
            return {"is_closed": True, "can_reply": False, "reason": "Application not found", "closes_at": None}
        status_info = await evaluate_application_closure(db, app, cand_user)
        if not status_info["is_closed"] and is_cand_requester:
            thr = await ChatRepository.get_thread_by_application_id(db, app.id)
            has_started = bool(thr and await ChatRepository.thread_has_hr_message(db, thr.id))
            if not has_started:
                has_started = await ChatRepository.has_hr_started_message_between(
                    db, candidate_id=cand_user.id, application_id=app.id
                )
            if not has_started:
                return {
                    "is_closed": False,
                    "can_reply": False,
                    "reason": "HR will message you here if they need anything. You will get a notification.",
                    "closes_at": None,
                }
        return status_info

    # Legacy aggregate check across candidate applications
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

    if apps:
        statuses = [await evaluate_application_closure(db, a, cand_user) for a in apps]
        if all(s["is_closed"] for s in statuses):
            return {
                "is_closed": True,
                "can_reply": False,
                "reason": "This conversation is closed",
                "closes_at": None,
            }
        # Compute latest closes_at if none are active
        open_closes = [s["closes_at"] for s in statuses if not s["is_closed"] and s["closes_at"]]
        any_indefinite = any(not s["is_closed"] and s["closes_at"] is None for s in statuses)
        closes_at = None if any_indefinite else (max(open_closes) if open_closes else None)
    else:
        closes_at = None

    if is_cand_requester:
        has_started = await ChatRepository.has_hr_started_message_between(
            db, candidate_id=cand_user.id, hr_user_id=other_user_id
        )
        if not has_started:
            return {
                "is_closed": False,
                "can_reply": False,
                "reason": "HR will message you here if they need anything. You will get a notification.",
                "closes_at": None,
            }

    return {
        "is_closed": False,
        "can_reply": True,
        "reason": None,
        "closes_at": closes_at,
    }


# ─── Application-Scoped Two-Way Threads ──────────────────────────────────────

async def _resolve_application_candidate(db: AsyncSession, app: JobApplication) -> Optional[User]:
    if app.user_id:
        u = await ChatRepository.get_user_by_id(db, app.user_id)
        if u:
            return u
    for email_candidate in (app.candidate_email, app.contact_email):
        clean = (email_candidate or "").strip().lower()
        if clean:
            u = await ChatRepository.get_user_by_email(db, clean)
            if u:
                return u
    return None


def _candidate_owns_application(user: User, app: JobApplication) -> bool:
    if app.user_id and app.user_id == user.id:
        return True
    user_email = (user.email or "").strip().lower()
    if not user_email:
        return False
    return user_email in {
        (app.candidate_email or "").strip().lower(),
        (app.contact_email or "").strip().lower(),
    }


def _get_job_title_for_app(app: Optional[JobApplication]) -> str:
    if not app:
        return "Position"
    if getattr(app, "job", None) and getattr(app.job, "job_title", None):
        return app.job.job_title
    return getattr(app, "job_title", None) or "Position"


async def _build_thread_summary(
    db: AsyncSession,
    thread: ApplicationThread,
    viewer: User,
    archived_thread_ids: Optional[set] = None,
) -> Dict[str, Any]:
    app = thread.job_application
    if app is None:
        res = await db.execute(select(JobApplication).where(JobApplication.id == thread.application_id))
        app = res.scalar_one_or_none()

    cand = thread.candidate
    if cand is None and thread.candidate_id:
        cand = await ChatRepository.get_user_by_id(db, thread.candidate_id)

    started_by = thread.started_by
    if started_by is None and thread.started_by_id:
        started_by = await ChatRepository.get_user_by_id(db, thread.started_by_id)

    # Fetch messages for unread count & latest sender info
    msgs = await ChatRepository.get_thread_messages(db, thread.id)
    last_msg = msgs[-1] if msgs else None
    viewer_is_cand = (viewer.role or "").upper() == "CANDIDATE"

    unread_count = 0
    for m in msgs:
        if m.is_read:
            continue
        sender_role = (getattr(m.sender, "role", None) or "").upper() if m.sender else ""
        if viewer_is_cand:
            # Candidate's unread messages = unread messages from HR/Admin
            if sender_role in {"HR", "ADMIN", "SUPERADMIN"} or m.sender_id != viewer.id:
                unread_count += 1
        else:
            # HR/Admin's unread messages = unread messages from Candidate
            if sender_role == "CANDIDATE" or (thread.candidate_id and m.sender_id == thread.candidate_id):
                unread_count += 1

    closure = (
        await evaluate_application_closure(db, app, cand)
        if app
        else {"is_closed": True, "can_reply": False, "reason": "Application not found", "closes_at": None}
    )

    last_sender_name = None
    last_sender_role = None
    if last_msg and last_msg.sender:
        last_sender_name = (last_msg.sender.fullname or "").strip() or last_msg.sender.email
        last_sender_role = last_msg.sender.role

    last_preview = thread.last_message_preview
    if last_msg:
        last_preview = last_msg.content or (f"Attachment: {last_msg.attachment_name}" if last_msg.attachment_name else "")

    return {
        "id": thread.id,
        "application_id": thread.application_id,
        "job_id": getattr(app, "job_id", None) if app else None,
        "job_title": _get_job_title_for_app(app),
        "application_status": getattr(app, "status", "Submitted") if app else "Unknown",
        "candidate_id": thread.candidate_id,
        "candidate_name": (
            (getattr(cand, "fullname", None) or "").strip()
            or (getattr(app, "candidate_name", None) if app else None)
            or "Applicant"
        ),
        "candidate_email": getattr(cand, "email", None) or (getattr(app, "candidate_email", None) if app else None),
        "candidate_profile_image_url": getattr(cand, "profile_image_url", None) or (getattr(app, "profile_image_url", None) if app else None),
        "started_by_id": thread.started_by_id,
        "started_by_name": (getattr(started_by, "fullname", None) or "").strip() if started_by else None,
        "last_message": last_preview,
        "last_message_time": last_msg.timestamp if last_msg else thread.last_message_at or thread.created_at,
        "last_sender_name": last_sender_name,
        "last_sender_role": last_sender_role,
        "unread_count": unread_count,
        "is_closed": closure["is_closed"],
        "can_reply": closure["can_reply"],
        "closure_reason": closure["reason"],
        "closes_at": closure["closes_at"],
        "is_archived": (thread.id in archived_thread_ids) if archived_thread_ids is not None else False,
        "created_at": thread.created_at,
    }


async def list_application_threads(
    db: AsyncSession,
    current_user: User,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return the combined inbox of application threads:
    - CANDIDATE: only threads started by HR/Admin for their applications (with >= 1 HR/Admin message).
    - HR / ADMIN: all application threads across applicants.
    """
    is_cand = (current_user.role or "").upper() == "CANDIDATE"
    archived_ids = set(await ChatRepository.get_archived_thread_ids(db, current_user.id))

    query = (
        select(ApplicationThread)
        .options(
            selectinload(ApplicationThread.job_application),
            selectinload(ApplicationThread.candidate),
            selectinload(ApplicationThread.started_by),
        )
        .order_by(desc(ApplicationThread.last_message_at), desc(ApplicationThread.created_at))
    )

    if is_cand:
        norm_email = (current_user.email or "").strip().lower()
        app_ids_res = await db.execute(
            select(JobApplication.id).where(
                or_(
                    JobApplication.user_id == current_user.id,
                    func.lower(JobApplication.candidate_email) == norm_email,
                    func.lower(JobApplication.contact_email) == norm_email,
                )
            )
        )
        owned_app_ids = [r[0] for r in app_ids_res.fetchall()]
        if not owned_app_ids:
            return {"threads": [], "total_unread": 0}
        query = query.where(
            or_(
                ApplicationThread.candidate_id == current_user.id,
                ApplicationThread.application_id.in_(owned_app_ids),
            )
        )

    res = await db.execute(query)
    raw_threads = list(res.scalars().all())

    summaries: List[Dict[str, Any]] = []
    q_lower = (search or "").strip().lower()
    for thr in raw_threads:
        if is_cand:
            # Applicants can only view threads where HR/Admin has sent at least one message
            if not await ChatRepository.thread_has_hr_message(db, thr.id):
                continue

        summary = await _build_thread_summary(db, thr, current_user, archived_ids)
        if q_lower:
            haystack = " ".join([
                str(summary.get("job_title") or ""),
                str(summary.get("candidate_name") or ""),
                str(summary.get("candidate_email") or ""),
                str(summary.get("last_message") or ""),
            ]).lower()
            if q_lower not in haystack:
                continue
        summaries.append(summary)

    summaries.sort(
        key=lambda t: t["last_message_time"].timestamp() if t.get("last_message_time") else 0,
        reverse=True,
    )
    total_unread = sum(int(t.get("unread_count") or 0) for t in summaries)
    return {"threads": summaries, "total_unread": total_unread}


async def _mark_thread_incoming_read(
    db: AsyncSession,
    thread: ApplicationThread,
    viewer: User,
    messages: List[Message],
) -> None:
    viewer_is_cand = (viewer.role or "").upper() == "CANDIDATE"
    to_mark: List[Message] = []
    notify_user_ids: set = set()
    for m in messages:
        if m.is_read:
            continue
        sender_role = (getattr(m.sender, "role", None) or "").upper() if m.sender else ""
        if viewer_is_cand:
            if sender_role in {"HR", "ADMIN", "SUPERADMIN"} or m.sender_id != viewer.id:
                to_mark.append(m)
                if m.sender_id:
                    notify_user_ids.add(m.sender_id)
        else:
            if sender_role == "CANDIDATE" or (thread.candidate_id and m.sender_id == thread.candidate_id):
                to_mark.append(m)
                if m.sender_id:
                    notify_user_ids.add(m.sender_id)

    if to_mark:
        await ChatRepository.mark_messages_as_read(db, to_mark)
        await invalidate_contacts_cache(viewer.id)
        now_iso = datetime.now(timezone.utc).isoformat()
        seen_payload = {
            "type": "messages_seen",
            "thread_id": thread.id,
            "application_id": thread.application_id,
            "reader_id": viewer.id,
            "message_ids": [m.id for m in to_mark if m.id],
            "read_at": now_iso,
        }
        for uid in notify_user_ids:
            try:
                await manager.send_personal_message(seen_payload, uid)
            except Exception:
                pass


async def get_application_thread_detail(
    db: AsyncSession,
    current_user: User,
    application_id: int,
    mark_read: bool = True,
) -> Dict[str, Any]:
    """
    Fetch the thread + messages for a specific application.
    For applicants before HR sends the first message, returns exists=False with no compose permission.
    """
    app_res = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
    app = app_res.scalar_one_or_none()
    if not app:
        raise MessageValidationError("Application not found.")

    is_cand = (current_user.role or "").upper() == "CANDIDATE"
    if is_cand and not _candidate_owns_application(current_user, app):
        raise ThreadAccessDeniedError("You do not have permission to view this application's messages.")

    thread = await ChatRepository.get_thread_by_application_id(db, application_id)
    if not thread:
        if is_cand:
            return {
                "exists": False,
                "thread": None,
                "messages": [],
                "thread_status": {
                    "is_closed": False,
                    "can_reply": False,
                    "reason": "HR will message you here if they need anything. You will get a notification.",
                    "closes_at": None,
                },
            }
        cand = await _resolve_application_candidate(db, app)
        closure = await evaluate_application_closure(db, app, cand)
        return {
            "exists": False,
            "thread": None,
            "messages": [],
            "thread_status": closure,
        }

    # If candidate views a thread that HR hasn't actually sent a message in yet
    if is_cand and not await ChatRepository.thread_has_hr_message(db, thread.id):
        return {
            "exists": False,
            "thread": None,
            "messages": [],
            "thread_status": {
                "is_closed": False,
                "can_reply": False,
                "reason": "HR will message you here if they need anything. You will get a notification.",
                "closes_at": None,
            },
        }

    messages = await ChatRepository.get_thread_messages(db, thread.id)
    if mark_read and messages:
        await _mark_thread_incoming_read(db, thread, current_user, messages)

    archived_ids = set(await ChatRepository.get_archived_thread_ids(db, current_user.id))
    summary = await _build_thread_summary(db, thread, current_user, archived_ids)
    return {
        "exists": True,
        "thread": summary,
        "messages": [serialize_message(m) for m in messages],
        "thread_status": {
            "is_closed": summary["is_closed"],
            "can_reply": summary["can_reply"],
            "reason": summary["closure_reason"],
            "closes_at": summary["closes_at"],
        },
    }


async def get_thread_detail_by_id(
    db: AsyncSession,
    current_user: User,
    thread_id: int,
    mark_read: bool = True,
) -> Dict[str, Any]:
    thread = await ChatRepository.get_thread_by_id(db, thread_id)
    if not thread:
        raise MessageValidationError("Conversation thread not found.")
    return await get_application_thread_detail(
        db=db,
        current_user=current_user,
        application_id=thread.application_id,
        mark_read=mark_read,
    )


async def _schedule_email_digest(receiver_id: int) -> None:
    """
    Schedule ONE debounced email digest per recipient (not one email per message).
    Uses a Redis cooldown key so rapid messages coalesce into a single digest email,
    backed by the periodic Celery beat task `send_chat_email_digest_task`.
    """
    try:
        from app.utils.redis_client import get_async_redis, is_redis_available
        if await is_redis_available():
            client = get_async_redis()
            lock_key = f"chat:digest_scheduled:{receiver_id}"
            already = await client.set(lock_key, "1", ex=300, nx=True)
            if already:
                try:
                    from app.tasks import send_chat_email_digest_task
                    send_chat_email_digest_task.apply_async(args=[receiver_id], countdown=300)
                except Exception as cel_err:
                    logger.debug(f"Could not enqueue debounced digest task (beat will pick it up): {cel_err}")
    except Exception as exc:
        logger.debug(f"Could not schedule debounced chat email digest: {exc}")


async def start_or_get_application_thread(
    db: AsyncSession,
    current_user: User,
    application_id: int,
    initial_content: Optional[str] = None,
    message_type: str = "general",
    attachment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    HR / Admin ONLY: Create (or retrieve existing) one-per-application thread
    and optionally send the initial message.
    Applicants attempting to call this ALWAYS receive 403 (ThreadNotStartedError).
    """
    if not _is_hr_or_admin(current_user.role):
        raise ThreadNotStartedError(
            "Only HR can start a conversation. HR will message you here if they need anything."
        )

    app_res = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
    app = app_res.scalar_one_or_none()
    if not app:
        raise MessageValidationError("Application not found.")

    cand = await _resolve_application_candidate(db, app)
    if not cand:
        raise MessageValidationError(
            "This applicant does not have a candidate portal account linked to this application yet."
        )

    thread = await ChatRepository.get_thread_by_application_id(db, application_id)
    if not thread:
        closure = await evaluate_application_closure(db, app, cand)
        if closure["is_closed"]:
            raise ConversationClosedError(closure["reason"] or "This conversation is closed")
        thread = await ChatRepository.create_application_thread(
            db=db,
            application_id=application_id,
            candidate_id=cand.id,
            started_by_id=current_user.id,
        )

    sent_msg = None
    if (initial_content and initial_content.strip()) or attachment is not None:
        sent_msg = await send_thread_message(
            db=db,
            current_user=current_user,
            thread_id=thread.id,
            content=initial_content or "",
            message_type=message_type,
            attachment=attachment,
        )

    detail = await get_application_thread_detail(
        db=db,
        current_user=current_user,
        application_id=application_id,
        mark_read=False,
    )
    if sent_msg:
        detail["latest_message"] = sent_msg
    return detail


async def send_thread_message(
    db: AsyncSession,
    current_user: User,
    thread_id: int,
    content: str,
    message_type: str = "general",
    attachment: Optional[Dict[str, Any]] = None,
    client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a message inside an application thread.
    Enforces:
      - Applicant cannot send if thread has no HR/Admin message yet (403)
      - Applicant can only post to their own application thread (403)
      - Thread closure rules: withdrawn = immediate, resolved = configurable 30 days (403)
      - Rate limit: 10 messages / minute (429)
      - Plain-text HTML sanitization & max length 2000 chars (400)
      - Never changes application status
      - In-system notification + debounced email digest (NOT one email per message)
    """
    thread = await ChatRepository.get_thread_by_id(db, thread_id)
    if not thread:
        raise MessageValidationError("Conversation thread not found.")

    app = thread.job_application
    if not app:
        res = await db.execute(select(JobApplication).where(JobApplication.id == thread.application_id))
        app = res.scalar_one_or_none()
    if not app:
        raise MessageValidationError("Application not found.")

    is_cand = (current_user.role or "").upper() == "CANDIDATE"
    cand = thread.candidate
    if cand is None and thread.candidate_id:
        cand = await ChatRepository.get_user_by_id(db, thread.candidate_id)
    if cand is None:
        cand = await _resolve_application_candidate(db, app)

    if is_cand:
        if not _candidate_owns_application(current_user, app):
            raise ThreadAccessDeniedError("You do not have permission to message in this application thread.")
        # Must already have at least one HR/Admin message in this thread
        if not await ChatRepository.thread_has_hr_message(db, thread.id):
            raise ThreadNotStartedError(
                "HR has not started a conversation for this application yet. You can reply once HR messages you."
            )
    elif not _is_hr_or_admin(current_user.role):
        raise ThreadAccessDeniedError("You do not have permission to send messages in this thread.")

    # Enforce closing rules
    closure = await evaluate_application_closure(db, app, cand)
    if closure["is_closed"]:
        raise ConversationClosedError(closure["reason"] or "This conversation is closed")

    # Anti-abuse: plain-text sanitization & max length before consuming rate-limit slot
    clean_content = sanitize_message_text(content, allow_empty=(attachment is not None))
    await enforce_chat_rate_limit(current_user.id)

    # Determine receiver_id
    if is_cand:
        # Route reply to the most recent HR/Admin participant, or thread creator
        existing_msgs = await ChatRepository.get_thread_messages(db, thread.id)
        hr_receiver_id = None
        for m in reversed(existing_msgs):
            if m.sender and _is_hr_or_admin(m.sender.role):
                hr_receiver_id = m.sender_id
                break
        if not hr_receiver_id:
            hr_receiver_id = thread.started_by_id
        if not hr_receiver_id:
            hr_res = await db.execute(select(User.id).where(func.upper(User.role) == "HR").limit(1))
            hr_receiver_id = hr_res.scalar_one_or_none()
        if not hr_receiver_id:
            raise MessageValidationError("No HR recipient is available for this thread.")
        receiver_id = hr_receiver_id
    else:
        if not cand:
            raise MessageValidationError("Applicant account not found for this application.")
        receiver_id = cand.id

    receiver = await ChatRepository.get_user_by_id(db, receiver_id)

    new_msg = await ChatRepository.create_message(
        db=db,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=clean_content,
        message_type=message_type or "general",
        application_id=thread.application_id,
        thread_id=thread.id,
        attachment_url=attachment.get("attachment_url") if attachment else None,
        attachment_name=attachment.get("attachment_name") if attachment else None,
        attachment_type=attachment.get("attachment_type") if attachment else None,
        attachment_size=attachment.get("attachment_size") if attachment else None,
    )

    # Update thread summary timestamps & preview
    preview_text = clean_content or (f"Attachment: {attachment['attachment_name']}" if attachment else "")
    thread.last_message_at = new_msg.timestamp or datetime.now(timezone.utc)
    thread.last_message_preview = preview_text[:280]
    thread.updated_at = datetime.now(timezone.utc)
    await db.commit()

    serialized = serialize_message(new_msg, sender=current_user)
    ws_payload = {
        "type": "new_message",
        **serialized,
        "timestamp": new_msg.timestamp.isoformat() if new_msg.timestamp else datetime.now(timezone.utc).isoformat(),
        "read_at": new_msg.read_at.isoformat() if new_msg.read_at else None,
        "job_title": _get_job_title_for_app(app),
        "client_id": client_id,
    }

    # Broadcast real-time update to candidate, receiver, thread starter, and sender
    ws_targets = {current_user.id, receiver_id}
    if thread.candidate_id:
        ws_targets.add(thread.candidate_id)
    if thread.started_by_id:
        ws_targets.add(thread.started_by_id)
    for uid in ws_targets:
        try:
            await manager.send_personal_message(ws_payload, uid)
        except Exception:
            pass

    await invalidate_contacts_cache(current_user.id)
    await invalidate_contacts_cache(receiver_id)

    # In-system notification + email digest (NOT one email per message)
    try:
        from app.services.notification_service import create_notification

        sender_name = (getattr(current_user, "fullname", None) or "").strip() or getattr(current_user, "email", "HR")
        job_title = _get_job_title_for_app(app)
        short_preview = (preview_text[:100] + "...") if len(preview_text) > 100 else preview_text

        if is_cand:
            await create_notification(
                db=db,
                title=f"Applicant Reply ({job_title})",
                message=f"{sender_name}: {short_preview}",
                type="message",
                target_role="HR",
                target_email=receiver.email.lower() if receiver and receiver.email else None,
                sender_role="CANDIDATE",
            )
        else:
            await create_notification(
                db=db,
                title=f"Message from HR ({job_title})",
                message=f"{sender_name}: {short_preview}",
                type="message",
                target_role="CANDIDATE",
                target_email=receiver.email.lower() if receiver and receiver.email else None,
                sender_role=(current_user.role or "HR").upper(),
            )

        # Schedule debounced email digest (coalesces multiple messages into ONE email)
        if receiver and receiver.email:
            await _schedule_email_digest(receiver.id)
    except Exception as notif_err:
        logger.warning(f"Failed to create chat notification: {notif_err}")

    return serialized


async def send_message_for_application(
    db: AsyncSession,
    current_user: User,
    application_id: int,
    content: str,
    message_type: str = "general",
    attachment: Optional[Dict[str, Any]] = None,
    client_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a message directly by application_id:
    - HR / Admin: starts the thread if it doesn't exist yet and sends the message.
    - CANDIDATE: if no HR-started thread exists, raises ThreadNotStartedError -> HTTP 403.
    """
    thread = await ChatRepository.get_thread_by_application_id(db, application_id)
    if not thread:
        if not _is_hr_or_admin(current_user.role):
            raise ThreadNotStartedError(
                "HR has not started a conversation for this application yet. You can reply once HR messages you."
            )
        result = await start_or_get_application_thread(
            db=db,
            current_user=current_user,
            application_id=application_id,
            initial_content=content,
            message_type=message_type,
            attachment=attachment,
        )
        return result["latest_message"]

    return await send_thread_message(
        db=db,
        current_user=current_user,
        thread_id=thread.id,
        content=content,
        message_type=message_type,
        attachment=attachment,
        client_id=client_id,
    )


async def report_message(
    db: AsyncSession,
    current_user: User,
    message_id: int,
    reason: str,
) -> Dict[str, Any]:
    """Allow an applicant to report an HR message in their thread."""
    msg = await ChatRepository.get_message_by_id(db, message_id)
    if not msg:
        raise MessageValidationError("Message not found.")

    if msg.sender_id == current_user.id:
        raise MessageValidationError("You cannot report your own message.")

    is_cand = (current_user.role or "").upper() == "CANDIDATE"
    if not is_cand:
        raise ThreadAccessDeniedError("Only applicants can report messages from HR.")

    # Verify applicant is a participant
    is_participant = msg.receiver_id == current_user.id
    if not is_participant and msg.thread_id:
        thr = await ChatRepository.get_thread_by_id(db, msg.thread_id)
        if thr and thr.candidate_id == current_user.id:
            is_participant = True
    if not is_participant:
        raise ThreadAccessDeniedError("You do not have permission to report this message.")

    clean_reason = sanitize_message_text(reason)
    if len(clean_reason) > 500:
        clean_reason = clean_reason[:500]

    report = await ChatRepository.create_message_report(
        db=db,
        message_id=msg.id,
        thread_id=msg.thread_id,
        reporter_id=current_user.id,
        reason=clean_reason,
    )

    try:
        from app.services.notification_service import create_notification
        from app.services.audit_service import audit_service

        await create_notification(
            db=db,
            title="Reported Chat Message",
            message=f"An applicant reported message #{msg.id}: {clean_reason[:120]}",
            type="system",
            target_role="ADMIN",
            sender_role="CANDIDATE",
        )
        await audit_service.record_activity(
            db=db,
            user_id=current_user.id,
            action="REPORT_MESSAGE",
            target=f"Message #{msg.id}",
            details=f"Applicant reported message #{msg.id} (thread #{msg.thread_id}): {clean_reason[:200]}",
        )
    except Exception as exc:
        logger.warning(f"Could not log/notify message report: {exc}")

    return {
        "id": report.id,
        "message_id": report.message_id,
        "thread_id": report.thread_id,
        "status": report.status,
        "detail": "Thank you. Your report has been sent to our administrators for review.",
    }


async def get_attachment_for_user(
    db: AsyncSession,
    current_user: User,
    message_id: int,
) -> Tuple[str, str, str]:
    """Verify participant access and return (file_path, original_name, mime_type)."""
    msg = await ChatRepository.get_message_by_id(db, message_id)
    if not msg or not msg.attachment_url:
        raise MessageValidationError("Attachment not found.")

    if not _is_hr_or_admin(current_user.role):
        allowed = msg.sender_id == current_user.id or msg.receiver_id == current_user.id
        if not allowed and msg.thread_id:
            thr = await ChatRepository.get_thread_by_id(db, msg.thread_id)
            if thr and thr.candidate_id == current_user.id:
                allowed = True
        if not allowed:
            raise ThreadAccessDeniedError("You do not have permission to download this attachment.")

    if not os.path.isfile(msg.attachment_url):
        raise MessageValidationError("Attachment file is no longer available.")

    return (
        msg.attachment_url,
        msg.attachment_name or os.path.basename(msg.attachment_url),
        msg.attachment_type or "application/octet-stream",
    )


async def dispatch_chat_email_digests(
    db: AsyncSession,
    recipient_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Consolidate unread, not-yet-emailed chat messages into ONE email digest per recipient
    (never one email per message).
    """
    from app.services.email_service import send_chat_digest_email
    from app.services.message_template_service import is_real_email

    conditions = [
        Message.is_read == False,
        Message.email_digest_sent_at.is_(None),
    ]
    if recipient_id is not None:
        conditions.append(Message.receiver_id == recipient_id)

    res = await db.execute(
        select(Message)
        .where(*conditions)
        .options(
            selectinload(Message.receiver),
            selectinload(Message.sender),
            selectinload(Message.job_application),
        )
        .order_by(Message.timestamp)
    )
    pending_msgs = list(res.scalars().all())
    if not pending_msgs:
        return {"recipients_notified": 0, "messages_included": 0}

    # Group by receiver_id
    by_recipient: Dict[int, List[Message]] = defaultdict(list)
    for m in pending_msgs:
        by_recipient[m.receiver_id].append(m)

    now = datetime.now(timezone.utc)
    recipients_notified = 0
    messages_included = 0

    for rec_id, msgs in by_recipient.items():
        rec_user = msgs[0].receiver or await ChatRepository.get_user_by_id(db, rec_id)
        if not rec_user or not is_real_email(getattr(rec_user, "email", None)):
            # Mark as processed so non-deliverable addresses do not pile up
            for m in msgs:
                m.email_digest_sent_at = now
            continue

        # Sub-group by application_id (or thread_id) for clean digest rows
        by_app: Dict[str, List[Message]] = defaultdict(list)
        for m in msgs:
            key = str(m.application_id or m.thread_id or "general")
            by_app[key].append(m)

        digest_items = []
        for _, grp in by_app.items():
            latest = grp[-1]
            job_title = _get_job_title_for_app(latest.job_application) if latest.job_application else "Application Messages"
            latest_sender = (
                (getattr(latest.sender, "fullname", None) or "").strip()
                if latest.sender
                else "Mariwasa Recruitment"
            )
            preview = latest.content or (
                f"Attachment: {latest.attachment_name}" if latest.attachment_name else "New message"
            )
            digest_items.append({
                "job_title": job_title,
                "unread_count": len(grp),
                "latest_sender": latest_sender,
                "latest_preview": preview,
            })

        try:
            await send_chat_digest_email(
                to_email=rec_user.email,
                recipient_name=rec_user.fullname or "Applicant",
                items=digest_items,
                is_hr=_is_hr_or_admin(rec_user.role),
            )
            for m in msgs:
                m.email_digest_sent_at = now
            recipients_notified += 1
            messages_included += len(msgs)
        except Exception as err:
            logger.warning(f"Failed sending chat digest email to user {rec_id}: {err}")

    await db.commit()
    return {
        "recipients_notified": recipients_notified,
        "messages_included": messages_included,
    }


# ─── Legacy send_message (Enforces HR-first, Rate Limit, Sanitization, Digest) ─

async def send_message(
    db: AsyncSession,
    current_user: User,
    other_user_id: int,
    content: str,
    client_id: Optional[str] = None,
    message_type: Optional[str] = "general",
    application_id: Optional[int] = None,
    raise_on_unstarted: bool = False,
) -> Optional[Message]:
    """
    Sends a message to another user if the roles are compatible, the conversation
    was started by HR (for applicants), and the thread has not closed.
    """
    allowed_roles = await get_allowed_roles(current_user.role)
    receiver = await ChatRepository.get_user_by_id(db, other_user_id)

    if not receiver or receiver.role not in allowed_roles:
        return None

    is_cand = (current_user.role or "").upper() == "CANDIDATE"
    receiver_is_cand = (receiver.role or "").upper() == "CANDIDATE"

    # Server-side enforcement: applicants can NEVER start a conversation or message an unstarted application
    thread: Optional[ApplicationThread] = None
    if is_cand:
        if application_id is not None:
            thread = await ChatRepository.get_thread_by_application_id(db, application_id)
            has_hr_started = bool(thread and await ChatRepository.thread_has_hr_message(db, thread.id))
            if not has_hr_started:
                has_hr_started = await ChatRepository.has_hr_started_message_between(
                    db, candidate_id=current_user.id, application_id=application_id
                )
            if not has_hr_started:
                if raise_on_unstarted:
                    raise ThreadNotStartedError(
                        "HR has not started a conversation for this application yet. You can reply once HR messages you."
                    )
                return None
        else:
            has_hr_started = await ChatRepository.has_hr_started_message_between(
                db, candidate_id=current_user.id, hr_user_id=other_user_id
            )
            if not has_hr_started:
                if raise_on_unstarted:
                    raise ThreadNotStartedError(
                        "Only HR can start a conversation. HR will message you here if they need anything."
                    )
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

    # Anti-abuse: plain-text sanitization & max length before consuming rate-limit slot
    clean_content = sanitize_message_text(content)
    await enforce_chat_rate_limit(current_user.id)

    # If HR/Admin sends a message linked to an application_id, ensure the ApplicationThread exists
    if _is_hr_or_admin(current_user.role) and receiver_is_cand and application_id is not None:
        thread = await ChatRepository.get_thread_by_application_id(db, application_id)
        if not thread:
            app_res = await db.execute(select(JobApplication).where(JobApplication.id == application_id))
            app_obj = app_res.scalar_one_or_none()
            if app_obj:
                thread = await ChatRepository.create_application_thread(
                    db=db,
                    application_id=application_id,
                    candidate_id=receiver.id,
                    started_by_id=current_user.id,
                )

    new_msg = await ChatRepository.create_message(
        db,
        current_user.id,
        other_user_id,
        clean_content,
        message_type=message_type or "general",
        application_id=application_id,
        thread_id=thread.id if thread else None,
    )

    if thread:
        thread.last_message_at = new_msg.timestamp or datetime.now(timezone.utc)
        thread.last_message_preview = clean_content[:280]
        thread.updated_at = datetime.now(timezone.utc)
        await db.commit()

    sender_name = (getattr(current_user, "fullname", None) or "").strip() or getattr(current_user, "email", "HR")
    msg_data = {
        "type": "new_message",
        "id": new_msg.id,
        "thread_id": new_msg.thread_id,
        "sender_id": new_msg.sender_id,
        "sender_name": sender_name,
        "sender_role": current_user.role,
        "receiver_id": new_msg.receiver_id,
        "application_id": new_msg.application_id,
        "message_type": new_msg.message_type,
        "content": new_msg.content,
        "timestamp": new_msg.timestamp.isoformat(),
        "is_read": new_msg.is_read,
        "read_at": new_msg.read_at.isoformat() if new_msg.read_at else None,
        "client_id": client_id,
    }

    await manager.send_personal_message(msg_data, other_user_id)
    await manager.send_personal_message(msg_data, current_user.id)

    await invalidate_contacts_cache(current_user.id)
    await invalidate_contacts_cache(other_user_id)

    # Create in-system notification + schedule email digest (not one email per message)
    try:
        from app.services.notification_service import create_notification

        preview = (clean_content[:100] + "...") if len(clean_content) > 100 else clean_content
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
            await _schedule_email_digest(receiver.id)
    except Exception as e_notif:
        logger.warning(f"Failed to create chat notification: {e_notif}")

    return new_msg


async def handle_websocket_message(db_factory, sender_id: int, data: dict):
    """
    Handles a message received through a WebSocket connection.
    Supports both application-scoped (`thread_id` / `application_id`) and legacy (`receiver_id`).
    Enforces all server-side rules (HR-first 403, closure 403, rate limit 429, validation 400).
    """
    try:
        thread_id = data.get("thread_id")
        application_id = data.get("application_id")
        receiver_id = data.get("receiver_id")
        content = data.get("content")
        client_id = data.get("client_id")
        message_type = data.get("message_type") or "general"

        if not content or (not thread_id and not application_id and not receiver_id):
            return

        async with db_factory() as db:
            sender = await ChatRepository.get_user_by_id(db, sender_id)
            if not sender:
                return

            try:
                if thread_id:
                    await send_thread_message(
                        db=db,
                        current_user=sender,
                        thread_id=int(thread_id),
                        content=content,
                        message_type=message_type,
                        client_id=client_id,
                    )
                elif application_id and not receiver_id:
                    await send_message_for_application(
                        db=db,
                        current_user=sender,
                        application_id=int(application_id),
                        content=content,
                        message_type=message_type,
                        client_id=client_id,
                    )
                else:
                    await send_message(
                        db,
                        sender,
                        int(receiver_id),
                        content,
                        client_id=client_id,
                        message_type=message_type,
                        application_id=int(application_id) if application_id else None,
                        raise_on_unstarted=True,
                    )
            except ConversationClosedError as closed_err:
                await manager.send_personal_message(
                    {
                        "type": "conversation_closed",
                        "thread_id": thread_id,
                        "receiver_id": receiver_id,
                        "detail": str(closed_err),
                        "client_id": client_id,
                    },
                    sender_id,
                )
            except (ThreadNotStartedError, ThreadAccessDeniedError) as perm_err:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "code": 403,
                        "thread_id": thread_id,
                        "detail": str(perm_err),
                        "client_id": client_id,
                    },
                    sender_id,
                )
            except ChatRateLimitError as rl_err:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "code": 429,
                        "thread_id": thread_id,
                        "detail": str(rl_err),
                        "client_id": client_id,
                    },
                    sender_id,
                )
            except MessageValidationError as val_err:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "code": 400,
                        "thread_id": thread_id,
                        "detail": str(val_err),
                        "client_id": client_id,
                    },
                    sender_id,
                )
    except Exception as e:
        logger.error(f"Error handling WS message: {e}")


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


async def archive_thread(db: AsyncSession, user_id: int, thread_id: int) -> bool:
    return await ChatRepository.archive_thread(db, user_id, thread_id)


async def unarchive_thread(db: AsyncSession, user_id: int, thread_id: int) -> bool:
    return await ChatRepository.unarchive_thread(db, user_id, thread_id)


async def broadcast_job_message(
    db: AsyncSession,
    current_user: User,
    job_id: int,
    content: str,
    message_type: str = "announcement",
    target_group: str = "all",
) -> int:
    """
    Broadcast a single message to all or shortlisted applicants for a specific job posting (REQ062, REQ064).
    """
    if (current_user.role or "").upper() == "CANDIDATE":
        return 0

    from app.repositories.job_application_repository import JobApplicationRepository
    from app.repositories.job_description_repository import JobDescriptionRepository

    clean_content = sanitize_message_text(content)
    job = await JobDescriptionRepository.get_by_id(db, job_id)
    job_title = job.job_title if job else "Mariwasa Position"

    applications = await JobApplicationRepository.get_by_job_id(db, job_id)
    if not applications:
        return 0

    if target_group.lower() == "shortlisted":
        applications = [
            a for a in applications
            if (getattr(a, "status", "") or "").upper() in ("SHORTLISTED", "SHORTLIST")
        ]

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
                content=clean_content,
                message_type=message_type,
                application_id=app.id,
            )
            sent_count += 1
        elif email:
            try:
                from app.services.notification_service import create_notification

                await create_notification(
                    db=db,
                    title=f"New Announcement: {job_title}",
                    message=f"{sender_name}: {clean_content[:100]}...",
                    type="message",
                    target_role="CANDIDATE",
                    target_email=email,
                    sender_role=current_user.role.upper(),
                )
                sent_count += 1
            except Exception as direct_err:
                logger.warning(f"Failed to dispatch broadcast to {email}: {direct_err}")

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
            "read_at": msg.read_at,
        })
    return records


async def mark_single_message_read(db: AsyncSession, message_id: int, current_user: User):
    """Mark a message as read when opened (REQ063)."""
    return await ChatRepository.mark_single_message_read(db, message_id, current_user.id)


chat_service = sys.modules[__name__]
