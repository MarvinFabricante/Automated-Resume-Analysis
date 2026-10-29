from fastapi import APIRouter, WebSocket, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.services import ai_caller_service
from app.schemas.interview_schema import SimulateVoiceCallRequest, VoiceCallRecordResponseSchema


router = APIRouter(prefix="/ai-caller", tags=["AI Interview Caller"])

@router.get("/status", response_class=JSONResponse)
async def status():
    return {"message": "AI Caller Service is active"}

@router.api_route("/incoming-call", methods=["GET", "POST"])
async def handle_incoming_call(request: Request):
    """Twilio Webhook: Returns TwiML to start the Media Stream."""
    twiml = await ai_caller_service.generate_incoming_twiml(request.url.hostname)
    return HTMLResponse(content=twiml, media_type="application/xml")

@router.post("/call-candidate/{phone_number}")
async def call_candidate(phone_number: str, request: Request):
    """Initiates an outbound call to the candidate's phone number."""
    return await ai_caller_service.initiate_outbound_call(phone_number, request.url.hostname)

@router.websocket("/media-stream")
async def handle_media_stream(websocket: WebSocket):
    """FastAPI WebSocket: Bridges Twilio audio and Gemini AI."""
    await ai_caller_service.handle_ai_media_stream(websocket)


# ── AI Voice Notification Endpoints (REQ028 - REQ034) ───────────────────────

@router.post("/interview/{interview_id}/call")
async def place_interview_call(
    interview_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    REQ028: Places an automated voice call to the candidate for a scheduled interview.
    """
    try:
        result = await ai_caller_service.initiate_candidate_interview_call(
            interview_id=interview_id,
            db=db,
            request_host=request.url.hostname,
            force=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/{interview_id}/retry")
async def retry_interview_call(
    interview_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    REQ031: Triggers an immediate retry call for an interview (up to 3 attempts).
    """
    try:
        result = await ai_caller_service.initiate_candidate_interview_call(
            interview_id=interview_id,
            db=db,
            request_host=request.url.hostname,
            force=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/{interview_id}/send-backup-sms")
async def send_backup_sms(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    REQ033: Manually or automatically dispatches SMS backup notification.
    """
    try:
        sent = await ai_caller_service.send_backup_sms_notification(interview_id, db)
        return {"status": "success", "sms_sent": sent, "message": "Backup SMS dispatched to candidate"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/{interview_id}/simulate")
async def simulate_call_response(
    interview_id: int,
    payload: SimulateVoiceCallRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Simulates a candidate verbal response or call outcome (for HR testing and development).
    Supports outcomes: CONFIRMED, RESCHEDULE_REQUESTED, NO_ANSWER, BUSY, FAILED.
    """
    try:
        result = await ai_caller_service.simulate_voice_call(
            interview_id=interview_id,
            outcome=payload.outcome,
            spoken_phrase=payload.spoken_phrase,
            language=payload.language or "en",
            db=db
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interview/{interview_id}/logs")
async def get_call_logs(
    interview_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    REQ032: Retrieves all voice call attempts, candidate responses, and timestamps.
    """
    try:
        return await ai_caller_service.get_interview_call_logs(interview_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Twilio Webhooks (Voice Generation & Speech Interpretation) ───────────────

@router.api_route("/interview-twiml/{interview_id}", methods=["GET", "POST"])
async def get_interview_twiml(
    interview_id: int,
    request: Request,
    attempt: int = Query(1),
    lang: str = Query("bilingual"),
    db: AsyncSession = Depends(get_db)
):
    """
    REQ029 & REQ030: Twilio Webhook delivering interview details in English or Filipino,
    and gathering candidate's verbal confirmation response.
    """
    from sqlalchemy import select
    from app.models.interview import Interview
    from app.models.job_application import JobApplication

    res = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = res.scalar_one_or_none()
    if not interview:
        return HTMLResponse("<Response><Say>Interview details not found. Goodbye.</Say></Response>", media_type="application/xml")

    app_res = await db.execute(select(JobApplication).where(JobApplication.id == interview.job_application_id))
    application = app_res.scalar_one_or_none()

    cand_name = getattr(application, "candidate_name", "Candidate") if application else "Candidate"
    job_name = getattr(application, "job_title", interview.title) if application else interview.title
    interviewer_name = interview.interviewer.fullname if getattr(interview, "interviewer", None) else "Mariwasa HR"

    twiml = ai_caller_service.build_interview_voice_twiml(
        interview_id=interview_id,
        candidate_name=cand_name,
        job_title=job_name,
        start_time=interview.start_time,
        interviewer_name=interviewer_name,
        language=lang,
        attempt=attempt,
        request_host=request.url.hostname
    )
    return HTMLResponse(content=twiml, media_type="application/xml")


@router.post("/voice-response")
async def handle_voice_response(
    request: Request,
    interview_id: int = Query(...),
    attempt: int = Query(1),
    lang: str = Query("bilingual"),
    db: AsyncSession = Depends(get_db)
):
    """
    REQ030 & REQ034: Twilio Gather Action Webhook.
    Receives candidate's verbal speech transcript (SpeechResult) or DTMF keypad digits (Digits).
    Updates interview status to CONFIRMED or RESCHEDULE_REQUESTED.
    """
    form_data = await request.form()
    speech_result = form_data.get("SpeechResult")
    digits = form_data.get("Digits")
    call_sid = form_data.get("CallSid")

    twiml = await ai_caller_service.handle_voice_response(
        interview_id=interview_id,
        speech_result=speech_result,
        digits=digits,
        call_sid=call_sid,
        db=db,
        language=lang
    )
    return HTMLResponse(content=twiml, media_type="application/xml")


@router.post("/status-callback")
async def handle_status_callback(
    request: Request,
    interview_id: int = Query(...),
    attempt: int = Query(1),
    db: AsyncSession = Depends(get_db)
):
    """
    REQ031 & REQ033: Twilio Call Status Callback Webhook.
    Captures completed, busy, no-answer, or failed status events.
    Schedules retry (up to 3 times within 24h) or triggers backup SMS.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "completed")
    call_duration = int(form_data.get("CallDuration", 0))

    await ai_caller_service.handle_call_status_callback(
        interview_id=interview_id,
        call_sid=call_sid,
        call_status=call_status,
        duration=call_duration,
        db=db
    )
    return JSONResponse(content={"status": "received"})
