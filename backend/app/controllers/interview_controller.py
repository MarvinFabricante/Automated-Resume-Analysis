from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime

from app.utils.database import get_db
from app.schemas.interview_schema import InterviewCreateSchema, InterviewResponseSchema, TimeSlotSchema
from app.utils.auth import get_current_user
from app.services import interview_service
from app.models.user import User

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("/available-slots", response_model=List[TimeSlotSchema])
async def get_available_slots(
    panelist_ids: List[int],
    start_date: datetime,
    end_date: datetime,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automatically view available time slots by syncing HR and panel calendars using Google Calendar API.
    """
    try:
        slots = await interview_service.get_available_slots(db, panelist_ids, start_date, end_date)
        return slots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule", response_model=InterviewResponseSchema)
async def schedule_interview(
    data: InterviewCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Allow one-click interview scheduling based on system-recommended available time slots.
    Support automatic coordination for multi-panel interviews.
    """
    try:
        result = await interview_service.schedule_interview(db, data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/application/{application_id}", response_model=List[InterviewResponseSchema])
async def get_application_interviews(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Maintain interview history.
    """
    return await interview_service.get_interviews_for_application(db, application_id)
