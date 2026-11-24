import io
import json
import logging
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.schemas.message_schema import (
    ApplicationThreadDetailResponse,
    ApplicationThreadListResponse,
    ArchiveConversationResponse,
    ArchivedContactsResponse,
    BroadcastMessageCreate,
    BroadcastMessageResponse,
    ChatContactResponse,
    HRMessageTemplateItem,
    MessageCreate,
    MessageReportCreate,
    MessageReportResponse,
    MessageResponse,
    SentMessageRecord,
    ThreadStartRequest,
)
from app.services import chat_service
from app.utils.auth import get_current_user
from app.utils.database import get_db
from app.utils.websocket_manager import manager

logger = logging.getLogger(__name__)


async def get_current_user_obj(payload: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    email = payload.get("sub")
    user = await AuthRepository.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


router = APIRouter(prefix="/chat", tags=["Chat"])


def _handle_chat_exception(exc: Exception):
    if isinstance(exc, (chat_service.ConversationClosedError, chat_service.ThreadNotStartedError, chat_service.ThreadAccessDeniedError)):
        raise HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, chat_service.ChatRateLimitError):
        raise HTTPException(status_code=429, detail=str(exc))
    if isinstance(exc, chat_service.MessageValidationError):
        detail = str(exc)
        status_code = 404 if "not found" in detail.lower() else 400
        raise HTTPException(status_code=status_code, detail=detail)
    raise exc


async def _parse_message_request(request: Request) -> Tuple[str, str, Optional[dict]]:
    """
    Accept either `application/json` or `multipart/form-data` (with optional pdf/png/jpg attachment).
    Returns (content, message_type, attachment_meta).
    """
    content_type = (request.headers.get("content-type") or "").lower()
    if "multipart/form-data" in content_type:
        form = await request.form()
        content = str(form.get("content") or "")
        message_type = str(form.get("message_type") or "general")
        upload = form.get("file") or form.get("attachment")
        attachment_meta = None
        if upload is not None and hasattr(upload, "read"):
            file_bytes = await upload.read()
            if file_bytes:
                attachment_meta = await chat_service.validate_and_save_chat_attachment(
                    file_bytes=file_bytes,
                    original_filename=getattr(upload, "filename", "attachment"),
                )
        return content, message_type, attachment_meta

    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    return (
        str(body.get("content") or ""),
        str(body.get("message_type") or "general"),
        None,
    )


# ─── Application-Scoped Two-Way Chat Threads ─────────────────────────────────

@router.get("/templates", response_model=List[HRMessageTemplateItem])
async def get_hr_templates(
    candidate_name: Optional[str] = None,
    job_title: Optional[str] = None,
    current_user: User = Depends(get_current_user_obj),
):
    """Return editable plain-text HR message templates (HR / Admin only)."""
    if (current_user.role or "").upper() == "CANDIDATE":
        raise HTTPException(status_code=403, detail="Only HR and Admin users can access message templates.")
    return chat_service.get_hr_message_templates(candidate_name=candidate_name, job_title=job_title)


@router.get("/threads", response_model=ApplicationThreadListResponse)
async def list_threads(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """
    Combined inbox of application-scoped threads.
    - Candidates see ONLY threads started by HR/Admin for their own applications.
    - HR/Admin see all application threads with position names and unread badges.
    """
    return await chat_service.list_application_threads(db, current_user, search=search)


@router.post("/threads", response_model=ApplicationThreadDetailResponse)
async def start_thread(
    payload: ThreadStartRequest,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """
    HR / Admin ONLY: Start (or open existing) conversation thread for an application.
    Applicants attempting to call this endpoint receive 403.
    """
    try:
        return await chat_service.start_or_get_application_thread(
            db=db,
            current_user=current_user,
            application_id=payload.application_id,
            initial_content=payload.content,
            message_type=payload.message_type or "general",
        )
    except Exception as exc:
        _handle_chat_exception(exc)


@router.get("/applications/{application_id}/thread", response_model=ApplicationThreadDetailResponse)
async def get_application_thread(
    application_id: int,
    mark_read: bool = True,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """Get the conversation thread (if started) and messages for a specific application."""
    try:
        return await chat_service.get_application_thread_detail(
            db=db,
            current_user=current_user,
            application_id=application_id,
            mark_read=mark_read,
        )
    except Exception as exc:
        _handle_chat_exception(exc)


@router.post("/applications/{application_id}/messages", response_model=MessageResponse)
async def send_application_message(
    application_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to an application's thread (supports JSON or multipart/form-data with attachment).
    - HR / Admin: creates the thread if it does not exist yet and sends the first message.
    - Applicants: returns 403 if HR has not started a thread for this application yet.
    """
    try:
        content, message_type, attachment = await _parse_message_request(request)
        return await chat_service.send_message_for_application(
            db=db,
            current_user=current_user,
            application_id=application_id,
            content=content,
            message_type=message_type,
            attachment=attachment,
        )
    except Exception as exc:
        _handle_chat_exception(exc)


@router.get("/threads/{thread_id}/messages", response_model=ApplicationThreadDetailResponse)
async def get_thread_messages_endpoint(
    thread_id: int,
    mark_read: bool = True,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """Fetch messages for a thread and mark incoming messages as read (seen)."""
    try:
        return await chat_service.get_thread_detail_by_id(
            db=db,
            current_user=current_user,
            thread_id=thread_id,
            mark_read=mark_read,
        )
    except Exception as exc:
        _handle_chat_exception(exc)


@router.post("/threads/{thread_id}/messages", response_model=MessageResponse)
async def send_thread_message_endpoint(
    thread_id: int,
    request: Request,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """Send a message inside an existing application thread (JSON or multipart with pdf/png/jpg)."""
    try:
        content, message_type, attachment = await _parse_message_request(request)
        return await chat_service.send_thread_message(
            db=db,
            current_user=current_user,
            thread_id=thread_id,
            content=content,
            message_type=message_type,
            attachment=attachment,
        )
    except Exception as exc:
        _handle_chat_exception(exc)


@router.post("/threads/{thread_id}/archive")
async def archive_thread_endpoint(
    thread_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    await chat_service.archive_thread(db, current_user.id, thread_id)
    return {"success": True, "thread_id": thread_id, "is_archived": True}


@router.post("/threads/{thread_id}/unarchive")
async def unarchive_thread_endpoint(
    thread_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    await chat_service.unarchive_thread(db, current_user.id, thread_id)
    return {"success": True, "thread_id": thread_id, "is_archived": False}


@router.post("/messages/{message_id}/report", response_model=MessageReportResponse)
async def report_message_endpoint(
    message_id: int,
    payload: MessageReportCreate,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """Allow an applicant to report an inappropriate message from HR."""
    try:
        return await chat_service.report_message(
            db=db,
            current_user=current_user,
            message_id=message_id,
            reason=payload.reason,
        )
    except Exception as exc:
        _handle_chat_exception(exc)


@router.get("/attachments/{message_id}")
async def download_chat_attachment(
    message_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """Authenticated download for a chat attachment (participants and HR/Admin only)."""
    try:
        file_path, original_name, mime_type = await chat_service.get_attachment_for_user(
            db=db,
            current_user=current_user,
            message_id=message_id,
        )
        return FileResponse(
            path=file_path,
            filename=original_name,
            media_type=mime_type,
        )
    except Exception as exc:
        _handle_chat_exception(exc)


# ─── Existing / Legacy Chat Endpoints (Maintained for Backward Compatibility) ─

@router.get("/active-count")
async def get_active_count():
    try:
        count = manager.get_online_count()
        if count < 1:
            count = 1
    except Exception:
        count = 1
    return {"count": count}


@router.get("/contacts", response_model=ChatContactResponse)
async def get_contacts(
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    chat_users = await chat_service.get_contacts(db, current_user, search)
    return ChatContactResponse(users=chat_users)


@router.get("/messages/{other_user_id}", response_model=List[MessageResponse])
async def get_messages(
    other_user_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    msgs = await chat_service.get_messages(db, current_user, other_user_id)
    return [chat_service.serialize_message(m) for m in msgs]


@router.get("/thread-status/{other_user_id}")
async def get_thread_status_endpoint(
    other_user_id: int,
    application_id: Optional[int] = None,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """Return whether a conversation thread is open or closed (read-only)."""
    return await chat_service.get_thread_status(
        db=db,
        current_user=current_user,
        other_user_id=other_user_id,
        application_id=application_id,
    )


@router.post("/messages/{other_user_id}", response_model=MessageResponse)
async def send_message(
    other_user_id: int,
    msg_in: MessageCreate,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    try:
        new_msg = await chat_service.send_message(
            db,
            current_user,
            other_user_id,
            msg_in.content,
            message_type=msg_in.message_type or "general",
            application_id=msg_in.application_id,
            raise_on_unstarted=True,
        )
    except Exception as exc:
        _handle_chat_exception(exc)
    if not new_msg:
        raise HTTPException(status_code=403, detail="You cannot message this user.")
    return chat_service.serialize_message(new_msg, sender=current_user)


@router.post("/broadcast-job/{job_id}", response_model=BroadcastMessageResponse)
async def broadcast_job_message(
    job_id: int,
    broadcast_in: BroadcastMessageCreate,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """
    Broadcast a single message to all or shortlisted applicants for a job posting (REQ062, REQ064).
    """
    if (current_user.role or "").upper() == "CANDIDATE":
        raise HTTPException(status_code=403, detail="Candidates cannot broadcast messages.")

    try:
        count = await chat_service.broadcast_job_message(
            db=db,
            current_user=current_user,
            job_id=job_id,
            content=broadcast_in.content,
            message_type=broadcast_in.message_type or "announcement",
            target_group=broadcast_in.target_group or "all",
        )
    except Exception as exc:
        _handle_chat_exception(exc)
    return BroadcastMessageResponse(
        success=True,
        recipient_count=count,
        message=f"Broadcast successfully dispatched to {count} applicant(s).",
    )


@router.get("/sent-messages", response_model=List[SentMessageRecord])
async def get_sent_messages(
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """
    Get consolidated log of sent HR messages with read receipts (REQ063, REQ065).
    """
    if (current_user.role or "").upper() == "CANDIDATE":
        raise HTTPException(status_code=403, detail="Access forbidden.")
    return await chat_service.get_sent_messages(db, current_user)


@router.patch("/message/{message_id}/read")
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark message as read with timestamp receipt (REQ063).
    """
    msg = await chat_service.mark_single_message_read(db, message_id, current_user)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"id": msg.id, "is_read": msg.is_read, "read_at": msg.read_at}


@router.delete("/messages/{other_user_id}")
async def delete_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    await chat_service.delete_conversation(db, current_user.id, other_user_id)
    return {"detail": "Conversation deleted successfully"}


@router.delete("/message/{message_id}")
async def delete_single_message(
    message_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    success = await chat_service.delete_single_message(db, current_user, message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or unauthorized")
    return {"detail": "Message deleted successfully"}


@router.get("/archived-conversations", response_model=ArchivedContactsResponse)
async def get_archived_conversations(
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    archived_ids = await chat_service.get_archived_contact_ids(db, current_user.id)
    return ArchivedContactsResponse(archived_contact_ids=archived_ids)


@router.post("/conversations/{other_user_id}/archive", response_model=ArchiveConversationResponse)
@router.patch("/conversations/{other_user_id}/archive", response_model=ArchiveConversationResponse)
async def archive_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    success = await chat_service.archive_conversation(db, current_user.id, other_user_id)
    return ArchiveConversationResponse(
        success=success,
        contact_id=other_user_id,
        is_archived=True,
        message="Conversation archived successfully",
    )


@router.post("/conversations/{other_user_id}/unarchive", response_model=ArchiveConversationResponse)
@router.delete("/conversations/{other_user_id}/archive", response_model=ArchiveConversationResponse)
async def unarchive_conversation(
    other_user_id: int,
    current_user: User = Depends(get_current_user_obj),
    db: AsyncSession = Depends(get_db),
):
    success = await chat_service.unarchive_conversation(db, current_user.id, other_user_id)
    return ArchiveConversationResponse(
        success=success,
        contact_id=other_user_id,
        is_archived=False,
        message="Conversation unarchived successfully",
    )


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    from app.utils.database import AsyncSessionLocal

    try:
        async with AsyncSessionLocal() as db:
            user = await chat_service.verify_token(token, db)
            if not user:
                logger.warning("WebSocket connection rejected: Invalid token")
                await websocket.close(code=1008)
                return
            user_id = user.id

        await manager.connect(websocket, user_id)
        logger.info(f"WebSocket connected: User {user_id}")

        try:
            while True:
                data_str = await websocket.receive_text()
                try:
                    data = json.loads(data_str)
                    if data.get("type") == "send_message":
                        await chat_service.handle_websocket_message(AsyncSessionLocal, user_id, data)
                except json.JSONDecodeError:
                    continue
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: User {user_id}")
            await manager.disconnect(websocket, user_id)
        except Exception as e:
            logger.error(f"WebSocket error for user {user_id}: {e}")
            await manager.disconnect(websocket, user_id)

    except Exception as e:
        logger.error(f"WebSocket handshake failed: {e}")
