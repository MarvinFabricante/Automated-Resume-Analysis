from fastapi import APIRouter, WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.services import ai_caller_service

class AICallerController:
    def __init__(self):
        self.router = APIRouter(prefix="/ai-caller", tags=["AI Interview Caller"])
        self.register_routes()

    def register_routes(self):
        self.router.get("/status", response_class=JSONResponse)(self.status)
        self.router.api_route("/incoming-call", methods=["GET", "POST"])(self.handle_incoming_call)
        self.router.post("/call-candidate/{phone_number}")(self.call_candidate)
        self.router.websocket("/media-stream")(self.handle_media_stream)

    async def status(self):
        return {"message": "AI Caller Service is active"}

    async def handle_incoming_call(self, request: Request):
        """Twilio Webhook: Returns TwiML to start the Media Stream."""
        twiml = await ai_caller_service.generate_incoming_twiml(request.url.hostname)
        return HTMLResponse(content=twiml, media_type="application/xml")

    async def call_candidate(self, phone_number: str, request: Request):
        """Initiates an outbound call to the candidate's phone number."""
        return await ai_caller_service.initiate_outbound_call(phone_number, request.url.hostname)

    async def handle_media_stream(self, websocket: WebSocket):
        """FastAPI WebSocket: Bridges Twilio audio and Gemini AI."""
        await ai_caller_service.handle_ai_media_stream(websocket)


ai_caller_controller = AICallerController()
router = ai_caller_controller.router
