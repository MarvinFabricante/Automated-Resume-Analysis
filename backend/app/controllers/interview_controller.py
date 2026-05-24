from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.utils.database import get_db
from app.schemas.interview_schema import InterviewCreateSchema, InterviewResponseSchema, TimeSlotSchema, AvailableSlotsRequest
from app.utils.auth import get_current_user
from app.services import interview_service
from app.models.user import User

class InterviewController:
    def __init__(self):
        self.router = APIRouter(prefix="/interviews", tags=["Interviews"])
        self.register_routes()

    def register_routes(self):
        self.router.post("/available-slots", response_model=List[TimeSlotSchema])(self.get_available_slots)
        self.router.post("/schedule", response_model=InterviewResponseSchema)(self.schedule_interview)
        self.router.put("/{interview_id}/status", response_model=InterviewResponseSchema)(self.update_interview_status)
        self.router.get("/application/{application_id}", response_model=List[InterviewResponseSchema])(self.get_application_interviews)

    async def get_available_slots(
        self,
        request: AvailableSlotsRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """
        Automatically view available time slots by syncing HR and panel calendars using Google Calendar API.
        """
        try:
            slots = await interview_service.get_available_slots(db, request.panelist_ids, request.start_date, request.end_date)
            return slots
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def schedule_interview(
        self,
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

    async def update_interview_status(
        self,
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

    async def get_application_interviews(
        self,
        application_id: int,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ):
        """
        Maintain interview history.
        """
        return await interview_service.get_interviews_for_application(db, application_id)


interview_controller = InterviewController()
router = interview_controller.router
