from fastapi import APIRouter, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.services import ai_caller_service


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


