from fastapi import APIRouter, Depends, HTTPException, Query, Response, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Union

from app.utils.database import get_db
from app.schemas.interview_schema import (
    AvailableSlotsRequest,
    AvailableSlotsResponseSchema,
    CandidateRescheduleSchema,
    InterviewCancelSchema,
    InterviewCreateSchema,
    InterviewUpdateSchema,
    InterviewResponseSchema,
    TimeSlotSchema,
    CalendarFeedResponseSchema,
    GoogleCalendarStatusSchema,
)
from app.utils.auth import get_current_user
from app.services import interview_service
from app.models.user import User
from app.utils.cache import cache_response, clear_cache_pattern


router = APIRouter(prefix="/interviews", tags=["Interviews"])

@router.get("/defaults")
async def get_interview_defaults(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    import json
    from app.repositories.system_config_repository import get_config_by_key
    config = await get_config_by_key(db, "company_address")
    address = config.value if config else ""
    try:
        address = json.loads(address)
    except (ValueError, TypeError):
        pass
    return {"company_address": address if isinstance(address, str) else ""}


@router.get("", response_model=List[InterviewResponseSchema])
async def get_all_interviews(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch all scheduled interviews with candidate details for the HR scheduling module.
    """
    try:
        return await interview_service.get_all_interviews(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar-feed", response_model=CalendarFeedResponseSchema)
async def get_calendar_feed(
    time_min: Optional[str] = Query(None),
    time_max: Optional[str] = Query(None),
    hr_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Unified calendar feed: returns all system interviews, syncs any external Google Calendar updates,
    and returns external Google Calendar events so HR has a complete schedule.
    """
    try:
        feed = await interview_service.get_calendar_feed(
            db, current_user.get("id"), time_min=time_min, time_max=time_max, hr_id=hr_id
        )
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync", response_model=CalendarFeedResponseSchema)
async def sync_google_calendar(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Manually trigger two-way synchronization between the system calendar and Google Calendar.
    """
    try:
        from app.services.google_calendar_service import invalidate_google_calendar_cache
        invalidate_google_calendar_cache()
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        feed = await interview_service.get_calendar_feed(db, current_user.get("id"), bypass_cache=True)
        return feed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/google-status", response_model=GoogleCalendarStatusSchema)
async def get_google_status(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if the current HR user has connected their Google Calendar.
    """
    try:
        return await interview_service.get_google_calendar_status(db, current_user.get("id"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/available-slots", response_model=Union[AvailableSlotsResponseSchema, List[TimeSlotSchema]])
async def get_available_slots(
    request: AvailableSlotsRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Automatically view available time slots by syncing HR and panel calendars using Google Calendar API.
    If the requested date/time is fully booked, returns a message offering alternative dates with available slots.
    """
    try:
        target_ids = []
        if request.user_ids:
            target_ids.extend(request.user_ids)
        if request.interviewer_ids:
            target_ids.extend(request.interviewer_ids)
        if request.panelist_ids:
            target_ids.extend(request.panelist_ids)
        if request.hr_id:
            target_ids.append(request.hr_id)
        if request.manager_id:
            target_ids.append(request.manager_id)

        if not target_ids and (current_user.get("role") or "").upper() != "CANDIDATE":
            target_ids = [current_user.get("id")]

        slots = await interview_service.get_available_slots(
            db,
            request.start_date,
            request.end_date,
            user_ids=target_ids
        )

        if not slots:
            msg = getattr(slots, "message", None) or "The selected date is fully booked."
            alt_dates = getattr(slots, "alternative_dates", []) or []
            alt_slots = getattr(slots, "alternative_slots", []) or []
            response.headers["X-Availability-Message"] = msg
            if alt_dates:
                response.headers["X-Alternative-Dates"] = ",".join(alt_dates)

            return AvailableSlotsResponseSchema(
                slots=[],
                message=msg,
                alternative_dates=alt_dates,
                alternative_slots=alt_slots
            )

        return slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/candidate-shortlisted/{application_id}")
async def get_candidate_shortlisted_for_combined(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Return other shortlisted applications for the same candidate so HR can schedule one combined slot."""
    try:
        return await interview_service.get_candidate_shortlisted_applications(db, application_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/schedule", response_model=InterviewResponseSchema)
async def schedule_interview(
    data: InterviewCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Allow one-click interview scheduling based on system-recommended available time slots.
    Validates that the requested slot falls within working hours (9 AM–5 PM, Mon–Fri)
    and does not conflict with existing interviews.
    """
    # ── Server-side working-hours validation ──────────────────────────
    start = data.start_time
    end = data.end_time

    # Weekday check (Monday=0 … Friday=4)
    if start.weekday() > 4:
        raise HTTPException(
            status_code=400,
            detail="Interviews can only be scheduled on weekdays (Monday – Friday)."
        )

    # Working-hours check (9:00 AM – 5:00 PM)
    if start.hour < 9 or end.hour > 17 or (end.hour == 17 and end.minute > 0):
        raise HTTPException(
            status_code=400,
            detail="Interviews must be scheduled within working hours (9:00 AM – 5:00 PM)."
        )

    # Lunch break check (12:00 PM – 1:00 PM)
    break_start = start.replace(hour=12, minute=0, second=0, microsecond=0)
    break_end = start.replace(hour=13, minute=0, second=0, microsecond=0)
    if start < break_end and end > break_start:
        raise HTTPException(
            status_code=400,
            detail="Interviews cannot be scheduled during break time (12:00 PM – 1:00 PM)."
        )

    # ── Conflict check against existing DB interviews ─────────────────
    from app.repositories.interview_repository import InterviewRepository
    INACTIVE_INTERVIEW_STATUSES = {"CANCELED", "CANCELLED", "COMPLETED", "REJECTED", "NO_SHOW"}
    target_interviewer = data.interviewer_id if data.interviewer_id else current_user.get("id")
    existing = await InterviewRepository.get_interviews_in_range(
        db,
        start.replace(tzinfo=None),
        end.replace(tzinfo=None),
        interviewer_id=target_interviewer,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="The selected time slot conflicts with an existing interview for this HR panelist. Please choose another slot."
        )

    # ── Check candidate conflict across all applications (REQ084) ────────────
    application = await InterviewRepository.get_job_application(db, data.job_application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Job application not found")

    from app.services.status_management_service import is_withdrawn_status, is_resolved_status
    if is_withdrawn_status(application.status):
        raise HTTPException(
            status_code=400,
            detail="Cannot schedule an interview for a withdrawn application."
        )
    if is_resolved_status(application.status):
        raise HTTPException(
            status_code=400,
            detail="Cannot schedule an interview for an already resolved application."
        )

    # Check if this application already has an active interview
    app_interviews = await InterviewRepository.get_interviews_for_application(db, data.job_application_id)
    active_app_ivs = [iv for iv in app_interviews if (iv.status or "").upper() not in INACTIVE_INTERVIEW_STATUSES]
    if active_app_ivs:
        raise HTTPException(
            status_code=409,
            detail="An active interview is already scheduled for this application."
        )

    # Check if candidate has an overlapping interview across ANY of their applications (REQ084)
    if getattr(application, "user_id", None):
        cand_all_ivs = await InterviewRepository.get_interviews_for_candidate_by_user_id(
            db, application.user_id, fallback_email=application.candidate_email
        )
    elif application.candidate_email:
        cand_all_ivs = await InterviewRepository.get_interviews_for_candidate(db, application.candidate_email)
    else:
        cand_all_ivs = app_interviews

    cand_conflict = [
        iv for iv in cand_all_ivs
        if (iv.status or "").upper() not in INACTIVE_INTERVIEW_STATUSES
        and iv.start_time < end.replace(tzinfo=None)
        and iv.end_time > start.replace(tzinfo=None)
    ]
    if cand_conflict:
        conflicting_iv = cand_conflict[0]
        start_str = conflicting_iv.start_time.strftime('%b %d, %Y %I:%M %p') if conflicting_iv.start_time else "the same time"
        raise HTTPException(
            status_code=409,
            detail=f"Scheduling conflict (REQ084): Candidate already has an interview scheduled that overlaps with this time slot ({start_str})."
        )

    try:
        result = await interview_service.schedule_interview(db, data, current_user.get("id"))
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        await clear_cache_pattern("all_apps*")
        await clear_cache_pattern("job_apps*")
        await clear_cache_pattern("cand_apps*")
        await clear_cache_pattern("app_stats*")
        await clear_cache_pattern("screening*")
        await clear_cache_pattern("hr:stats*")
        await clear_cache_pattern("admin:stats*")
        return result
    except ValueError as e:
        await db.rollback()
        if "already scheduled" in str(e).lower() or "conflict" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        if "rate limit" in str(e).lower() or "429" in str(e).lower():
            raise HTTPException(status_code=429, detail=str(e))
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            raise HTTPException(status_code=504, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{interview_id}", response_model=InterviewResponseSchema)
async def update_interview(
    interview_id: int,
    data: InterviewUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Modify or reschedule an interview and update the event directly on Google Calendar.
    """
    try:
        result = await interview_service.update_interview(
            db, interview_id, data, current_user.get("id"), user_role=current_user.get("role")
        )
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        from app.utils.cache import invalidate_application_dashboard_caches
        await invalidate_application_dashboard_caches()
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{interview_id}/candidate-reschedule", response_model=InterviewResponseSchema)
async def candidate_reschedule_interview(
    interview_id: int,
    data: CandidateRescheduleSchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Allow a candidate to reschedule a missed or pending interview into an available
    slot on the assigned interviewer's calendar.
    """
    try:
        result = await interview_service.candidate_reschedule_interview(
            db,
            interview_id,
            data,
            candidate_email=current_user.get("sub") or current_user.get("email"),
            candidate_user_id=current_user.get("id"),
        )
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        from app.utils.cache import invalidate_application_dashboard_caches
        await invalidate_application_dashboard_caches()
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{interview_id}")
async def delete_interview(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete an interview and delete its corresponding event on Google Calendar.
    """
    try:
        await interview_service.delete_interview(
            db, interview_id, current_user.get("id"), user_role=current_user.get("role")
        )
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        from app.utils.cache import invalidate_application_dashboard_caches
        await invalidate_application_dashboard_caches()
        return {"message": "Interview deleted successfully and removed from Google Calendar"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar-events")
async def get_calendar_events(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch and display the currently authenticated HR user's own Google Calendar schedules.
    """
    try:
        events = await interview_service.get_calendar_events(db, current_user.get("id"))
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{interview_id}/status", response_model=InterviewResponseSchema)
async def update_interview_status(
    interview_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Track interview confirmations and detect no-shows.
    """
    try:
        result = await interview_service.update_interview_status(
            db, interview_id, status, user_id=current_user.get("id"), user_role=current_user.get("role")
        )
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        from app.utils.cache import invalidate_application_dashboard_caches
        await invalidate_application_dashboard_caches()
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{interview_id}/cancel", response_model=InterviewResponseSchema)
async def cancel_interview(
    interview_id: int,
    reason: Optional[str] = Query(None),
    payload: Optional[InterviewCancelSchema] = Body(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel an interview: removes the Google Calendar event, notifies participants, and updates status to CANCELED.
    """
    try:
        effective_reason = (payload.reason if payload and payload.reason is not None else reason)
        result = await interview_service.cancel_interview(
            db,
            interview_id,
            current_user.get("id"),
            user_role=current_user.get("role"),
            reason=effective_reason,
            custom_email_subject=payload.custom_email_subject if payload else None,
            custom_email_message=payload.custom_email_message if payload else None,
            custom_sms_message=payload.custom_sms_message if payload else None,
        )
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        from app.utils.cache import invalidate_application_dashboard_caches
        await invalidate_application_dashboard_caches()
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/application/{application_id}", response_model=List[InterviewResponseSchema])
@cache_response("app_interviews", ttl=60)
async def get_application_interviews(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Maintain interview history.
    """
    return await interview_service.get_interviews_for_application(db, application_id)

@router.get("/candidate/{email}", response_model=List[InterviewResponseSchema])
async def get_candidate_interviews(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Maintain interview history for a candidate (linked by authenticated user_id first).
    """
    raw_param = (email or "").strip()
    if (current_user.get("role") or "").upper() == "CANDIDATE":
        auth_uid = current_user.get("id")
        auth_email = (current_user.get("sub") or current_user.get("email") or "").strip().lower()
        if auth_uid:
            return await interview_service.get_interviews_for_candidate(
                db, auth_email or raw_param, user_id=auth_uid
            )
    if raw_param.isdigit():
        return await interview_service.get_interviews_for_candidate(
            db, raw_param, user_id=int(raw_param)
        )
    return await interview_service.get_interviews_for_candidate(db, email)




