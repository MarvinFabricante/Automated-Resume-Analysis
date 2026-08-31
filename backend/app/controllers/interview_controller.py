from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.interview_schema import (
    AvailableSlotsRequest,
    InterviewCreateSchema,
    InterviewResponseSchema,
    TimeSlotSchema,
)
from app.utils.auth import get_current_user
from app.services import interview_service
from app.models.user import User
from app.utils.cache import cache_response, clear_cache_pattern


router = APIRouter(prefix="/interviews", tags=["Interviews"])

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
        slots = await interview_service.get_available_slots(
            db,
            request.start_date,
            request.end_date,
            current_user.get("id")
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
    existing = await InterviewRepository.get_interviews_in_range(
        db,
        start.replace(tzinfo=None),
        end.replace(tzinfo=None),
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="The selected time slot conflicts with an existing interview. Please choose another slot."
        )

    try:
        result = await interview_service.schedule_interview(db, data, current_user.get("id"))
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        await clear_cache_pattern("calendar_events*")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    current_user: User = Depends(get_current_user)
):
    """
    Track interview confirmations and detect no-shows.
    """
    try:
        result = await interview_service.update_interview_status(db, interview_id, status)
        await clear_cache_pattern("app_interviews*")
        await clear_cache_pattern("cand_interviews*")
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/application/{application_id}", response_model=List[InterviewResponseSchema])
@cache_response("app_interviews", ttl=60)
async def get_application_interviews(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(get_current_user)
):
    """
    Maintain interview history for a candidate.
    """
    return await interview_service.get_interviews_for_candidate(db, email)



