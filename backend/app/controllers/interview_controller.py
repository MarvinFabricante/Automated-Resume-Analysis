from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.utils.database import get_db
from app.schemas.interview_schema import (
    AvailableSlotsRequest,
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
        feed = await interview_service.get_calendar_feed(db, current_user.get("id"))
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
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

@router.post("/available-slots", response_model=List[TimeSlotSchema])
async def get_available_slots(
    request: AvailableSlotsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Automatically view available time slots by syncing HR and panel calendars using Google Calendar API.
    """
    try:
        target_id = request.hr_id if request.hr_id else current_user.get("id")
        slots = await interview_service.get_available_slots(
            db,
            request.start_date,
            request.end_date,
            target_id
        )
        return slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule", response_model=InterviewResponseSchema)
async def schedule_interview(
    data: InterviewCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Allow one-click interview scheduling based on system-recommended available time slots.
    Validates that the requested slot falls within working hours (8 AM–5 PM, Mon–Fri)
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

    # Working-hours check (8:00 AM – 5:00 PM)
    if start.hour < 8 or end.hour > 17 or (end.hour == 17 and end.minute > 0):
        raise HTTPException(
            status_code=400,
            detail="Interviews must be scheduled within working hours (8:00 AM – 5:00 PM)."
        )

    # ── Conflict check against existing DB interviews ─────────────────
    from app.repositories.interview_repository import InterviewRepository
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

    # Check candidate conflict
    cand_interviews = await InterviewRepository.get_interviews_for_application(db, data.job_application_id)
    cand_conflict = [
        iv for iv in cand_interviews
        if iv.status != "CANCELED" and iv.start_time < end.replace(tzinfo=None) and iv.end_time > start.replace(tzinfo=None)
    ]
    if cand_conflict:
        raise HTTPException(
            status_code=409,
            detail="This candidate already has an interview scheduled at the selected time."
        )

    # Pre-check against existing active interviews for candidate/application (exclusivity)
    application = await InterviewRepository.get_job_application(db, data.job_application_id)
    if application:
        active_interviews = [iv for iv in cand_interviews if iv.status != "CANCELED"]
        if not active_interviews and application.candidate_email:
            cand_all_ivs = await InterviewRepository.get_interviews_for_candidate(db, application.candidate_email)
            active_interviews = [iv for iv in cand_all_ivs if iv.status != "CANCELED"]

        if active_interviews:
            existing_iv = active_interviews[0]
            interviewer_name = None
            if getattr(existing_iv, "interviewer", None) and getattr(existing_iv.interviewer, "fullname", None):
                interviewer_name = existing_iv.interviewer.fullname
            elif getattr(existing_iv, "interviewer_name", None):
                interviewer_name = existing_iv.interviewer_name
            elif getattr(existing_iv, "interviewer_id", None):
                from app.repositories.auth_repository import AuthRepository
                iv_user = await AuthRepository.get_user_by_id(db, existing_iv.interviewer_id)
                interviewer_name = iv_user.fullname if iv_user else None

            interviewer_display = interviewer_name or "another HR"
            cand_name = application.candidate_name or "Candidate"
            raise HTTPException(
                status_code=409,
                detail=f"Candidate '{cand_name}' is already scheduled for an interview with {interviewer_display}. Another HR cannot schedule an interview for this candidate."
            )

    try:
        result = await interview_service.schedule_interview(db, data, current_user.get("id"))
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        return result
    except ValueError as e:
        if "already scheduled" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
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
        return {"message": "Interview deleted successfully and removed from Google Calendar"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/calendar-events")
@cache_response("calendar_events", ttl=300)
async def get_calendar_events(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch and display the HR's Google Calendar schedules.
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
@cache_response("cand_interviews", ttl=60)
async def get_candidate_interviews(
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Maintain interview history for a candidate.
    """
    return await interview_service.get_interviews_for_candidate(db, email)




