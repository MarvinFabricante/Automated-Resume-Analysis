from fastapi import WebSocket, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.services import ai_caller_service
from app.controllers.base_controller import ApiRoute, BaseController, Get, Post, WebSocketRoute


class AICallerController(BaseController):
    prefix = "/ai-caller"
    tags = ["AI Interview Caller"]

    @Get("/status", response_class=JSONResponse)
    async def status(self):
        return {"message": "AI Caller Service is active"}

    @ApiRoute("/incoming-call", methods=["GET", "POST"])
    async def handle_incoming_call(self, request: Request):
        """Twilio Webhook: Returns TwiML to start the Media Stream."""
        twiml = await ai_caller_service.generate_incoming_twiml(request.url.hostname)
        return HTMLResponse(content=twiml, media_type="application/xml")

    @Post("/call-candidate/{phone_number}")
    async def call_candidate(self, phone_number: str, request: Request):
        """Initiates an outbound call to the candidate's phone number."""
        return await ai_caller_service.initiate_outbound_call(phone_number, request.url.hostname)

    @WebSocketRoute("/media-stream")
    async def handle_media_stream(self, websocket: WebSocket):
        """FastAPI WebSocket: Bridges Twilio audio and Gemini AI."""
        await ai_caller_service.handle_ai_media_stream(websocket)


ai_caller_controller = AICallerController()
router = ai_caller_controller.router
