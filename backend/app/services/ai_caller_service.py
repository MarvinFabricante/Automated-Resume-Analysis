import os
import json
import asyncio
import websockets
from fastapi import WebSocket, HTTPException, Request
from fastapi.websockets import WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client as TwilioClient

# Configuration from Environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

GEMINI_WS_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.MultimodalLive"

SYSTEM_MESSAGE = (
    "You are a professional HR interviewer from Mariwasa Siam Ceramics. "
    "Your goal is to conduct a brief initial screening interview with the candidate. "
    "Be professional, clear, and encouraging. Ask about their experience and interest in the role. "
    "Keep your responses concise for a natural phone conversation."
)

class AICallerService:
    async def generate_incoming_twiml(self, request_host: str) -> str:
        """Generates the TwiML for incoming/answered calls to connect to media stream."""
        response = VoiceResponse()

        response.say(
            "Connecting you to the Mariwasa AI Interview Assistant. Please wait.",
            voice="Google.en-US-Standard-C"
        )
        response.pause(length=1)

        connect = Connect()
        connect.stream(url=f'wss://{request_host}/ai-caller/media-stream')
        response.append(connect)

        return str(response)

    async def initiate_outbound_call(self, phone_number: str, request_host: str):
        """Initiates an outbound call using Twilio."""
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise HTTPException(status_code=500, detail="Twilio credentials not configured")

        try:
            client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            # Callback URL for Twilio to fetch TwiML upon answer
            callback_url = f"https://{request_host}/ai-caller/incoming-call"

            call = client.calls.create(
                url=callback_url,
                to=phone_number,
                from_=TWILIO_PHONE_NUMBER
            )
            return {"message": "Call initiated", "call_sid": call.sid}
        except Exception as e:
            print(f"Twilio Call Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def handle_ai_media_stream(self, websocket: WebSocket):
        """Handles the WebSocket bridge between Twilio and Gemini AI."""
        await websocket.accept()

        gemini_uri = f"{GEMINI_WS_URL}?key={GEMINI_API_KEY}"

        try:
            async with websockets.connect(gemini_uri) as gemini_ws:
                # 1. Setup Gemini
                setup_msg = {
                    "setup": {
                        "model": "models/gemini-2.0-flash-exp",
                        "generation_config": { "response_modalities": ["AUDIO"] },
                        "system_instruction": { "parts": [{"text": SYSTEM_MESSAGE}] }
                    }
                }
                await gemini_ws.send(json.dumps(setup_msg))
                await gemini_ws.recv() # Wait for setup confirmation

                stream_sid = None

                async def twilio_to_gemini():
                    nonlocal stream_sid
                    try:
                        async for message in websocket.iter_text():
                            data = json.loads(message)
                            if data['event'] == 'media':
                                audio_msg = {
                                    "realtime_input": {
                                        "media_chunks": [{
                                            "data": data['media']['payload'],
                                            "mime_type": "audio/pcm;rate=8000"
                                        }]
                                    }
                                }
                                await gemini_ws.send(json.dumps(audio_msg))
                            elif data['event'] == 'start':
                                stream_sid = data['start']['streamSid']
                    except WebSocketDisconnect:
                        if gemini_ws.open: await gemini_ws.close()

                async def gemini_to_twilio():
                    nonlocal stream_sid
                    try:
                        async for gemini_message in gemini_ws:
                            response = json.loads(gemini_message)
                            if "server_content" in response:
                                parts = response["server_content"].get("model_turn", {}).get("parts", [])
                                for part in parts:
                                    if "inline_data" in part:
                                        audio_delta = {
                                            "event": "media",
                                            "streamSid": stream_sid,
                                            "media": { "payload": part["inline_data"]["data"] }
                                        }
                                        await websocket.send_json(audio_delta)

                            if "interrupted" in response:
                                await websocket.send_json({ "event": "clear", "streamSid": stream_sid })
                    except Exception as e:
                        print(f"Gemini to Twilio error: {e}")

                await asyncio.gather(twilio_to_gemini(), gemini_to_twilio())

        except Exception as e:
            print(f"Service bridge failure: {e}")
            await websocket.close()


ai_caller_service = AICallerService()


async def generate_incoming_twiml(request_host: str) -> str:
    return await ai_caller_service.generate_incoming_twiml(request_host)


async def initiate_outbound_call(phone_number: str, request_host: str):
    return await ai_caller_service.initiate_outbound_call(phone_number, request_host)


async def handle_ai_media_stream(websocket: WebSocket):
    return await ai_caller_service.handle_ai_media_stream(websocket)
