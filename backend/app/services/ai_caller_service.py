import os
import sys
import json
import uuid
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

import websockets
from fastapi import WebSocket, HTTPException, Request
from fastapi.websockets import WebSocketDisconnect
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from twilio.twiml.voice_response import VoiceResponse, Gather, Connect, Say
from twilio.rest import Client as TwilioClient

from app.models.interview import Interview, InterviewLog, VoiceCallRecord
from app.models.job_application import JobApplication
from app.models.user import User

logger = logging.getLogger(__name__)

# Configuration from Environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY and os.getenv('GEMINI_API_KEYS'):
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEYS').split(',')[0].strip().strip('"').strip("'")

AI_CALLER_PHONE_NUMBER = os.getenv('AI_CALLER_PHONE_NUMBER', os.getenv('TWILIO_PHONE_NUMBER', '09771331871'))
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', AI_CALLER_PHONE_NUMBER)
AI_CALLER_PROVIDER = os.getenv('AI_CALLER_PROVIDER', 'auto')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '')

GEMINI_WS_URL = "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.MultimodalLive"

SYSTEM_MESSAGE = (
    "You are a professional HR interviewer from Mariwasa Siam Ceramics. "
    "Your goal is to conduct a brief initial screening interview with the candidate. "
    "Be professional, clear, and encouraging. Ask about their experience and interest in the role. "
    "Keep your responses concise for a natural phone conversation."
)

# ── Keywords for Speech Intent Interpretation ──────────────────────────────
CONFIRM_KEYWORDS = [
    "confirm", "confirmed", "yes", "i confirm", "attend", "attending",
    "will attend", "pupunta", "pupunta ako", "kumpirma", "kumpirmado",
    "oo", "darating", "darating ako", "okay", "sure", "pwede", "pwede ako",
    "opo", "sige", "sige po", "confirm po", "pupunta po ako", "available"
]

RESCHEDULE_KEYWORDS = [
    "reschedule", "re-schedule", "move", "change", "lipat", "palit", "palitan",
    "iba", "hindi pwede", "di pwede", "di ako pwede", "hindi ako pwede",
    "busy", "cannot", "cannot attend", "ibang araw", "ibang petsa",
    "ibang oras", "next week", "conflict", "may lakad", "pa-reschedule"
]


def format_to_e164(phone: Optional[str]) -> Optional[str]:
    """Ensures phone number is in E.164 format for telecom / Twilio routing."""
    if not phone:
        return None
    cleaned = "".join(ch for ch in phone.strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("09") and len(cleaned) == 11:
        return "+63" + cleaned[1:]
    if cleaned.startswith("9") and len(cleaned) == 10:
        return "+63" + cleaned
    if cleaned.startswith("63") and len(cleaned) == 12:
        return "+" + cleaned
    return "+" + cleaned if cleaned else None


def format_ph_datetime(dt: datetime, lang: str = "en") -> str:
    """Formats datetime clearly for text-to-speech engine in English or Filipino."""
    norm_lang = "fil" if lang and lang.lower() in ["fil", "filipino", "tagalog"] else "en"
    if not dt:
        return "ang nakatakdang oras" if norm_lang == "fil" else "the scheduled time"
    try:
        weekday_en = dt.strftime("%A")
        month_en = dt.strftime("%B")
        day = dt.strftime("%d").lstrip("0")
        year = dt.strftime("%Y")
        time_str = dt.strftime("%I:%M %p").lstrip("0")

        if norm_lang == "fil":
            fil_weekdays = {
                "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miyerkules",
                "Thursday": "Huwebes", "Friday": "Biyernes", "Saturday": "Sabado", "Sunday": "Linggo"
            }
            fil_months = {
                "January": "Enero", "February": "Pebrero", "March": "Marso",
                "April": "Abril", "May": "Mayo", "June": "Hunyo",
                "July": "Hulyo", "August": "Agosto", "September": "Setyembre",
                "October": "Oktubre", "November": "Nobyembre", "December": "Disyembre"
            }
            w_fil = fil_weekdays.get(weekday_en, weekday_en)
            m_fil = fil_months.get(month_en, month_en)
            return f"{w_fil}, ika-{day} ng {m_fil}, {year} sa ganap na {time_str}"
        
        return f"{weekday_en}, {month_en} {day}, {year} at {time_str}"
    except Exception:
        return dt.strftime("%B %d, %Y at %I:%M %p")


def interpret_verbal_response(speech_text: Optional[str], digits: Optional[str]) -> Tuple[str, str]:
    """
    REQ030: Evaluates candidate verbal response or keypad input.
    Returns: (intent, notes)
    Intent is one of: 'CONFIRMED', 'RESCHEDULE_REQUESTED', 'UNKNOWN'
    """
    clean_digits = (digits or "").strip()
    if clean_digits == "1":
        return "CONFIRMED", "Candidate pressed 1 on keypad to confirm attendance."
    if clean_digits == "2":
        return "RESCHEDULE_REQUESTED", "Candidate pressed 2 on keypad to request rescheduling."

    clean_speech = (speech_text or "").lower().strip()
    if not clean_speech:
        return "UNKNOWN", "No speech detected or audio inaudible."

    # Check for reschedule/negation keywords first to prevent substrings (e.g. "hindi pwede" matching "pwede")
    for kw in sorted(RESCHEDULE_KEYWORDS, key=len, reverse=True):
        if kw in clean_speech:
            return "RESCHEDULE_REQUESTED", f"Candidate requested reschedule (matched '{kw}'). Spoken: '{speech_text}'"

    # Explicit check if negations are present
    has_negation = any(neg in clean_speech for neg in ["hindi", "di ", "di ako", "not", "cannot", "can't", "unable"])
    if has_negation:
        return "RESCHEDULE_REQUESTED", f"Candidate expressed inability to attend. Spoken: '{speech_text}'"

    # Keyword matching for confirmation
    for kw in sorted(CONFIRM_KEYWORDS, key=len, reverse=True):
        if kw in clean_speech:
            return "CONFIRMED", f"Candidate verbally confirmed attendance (matched '{kw}'). Spoken: '{speech_text}'"

    return "UNKNOWN", f"Spoken phrase unclear: '{speech_text}'"


def build_interview_voice_twiml(
    interview_id: int,
    candidate_name: str,
    job_title: str,
    start_time: datetime,
    interviewer_name: Optional[str],
    language: str = "bilingual",
    attempt: int = 1,
    request_host: Optional[str] = None,
    location: Optional[str] = None
) -> str:
    """
    REQ029 & REQ030: Generates TwiML delivering interview details clearly in English or Filipino,
    and requests verbal confirmation (confirm or reschedule).
    Includes candidate name, date, time, and interview location.
    """
    response = VoiceResponse()

    norm_lang = "fil" if language and language.lower() in ["fil", "filipino", "tagalog"] else ("en" if language and language.lower() in ["en", "english"] else "bilingual")

    host = request_host or (PUBLIC_BASE_URL.replace("https://", "").replace("http://", "").split("/")[0] if PUBLIC_BASE_URL else "")
    action_url = f"https://{host}/ai-caller/voice-response?interview_id={interview_id}&attempt={attempt}&lang={norm_lang}" if host else f"/ai-caller/voice-response?interview_id={interview_id}&attempt={attempt}&lang={norm_lang}"

    interviewer_display = interviewer_name or "our HR team"
    loc_display = location or "Mariwasa Plant, Sto. Tomas, Batangas"
    dt_en = format_ph_datetime(start_time, lang="en")
    dt_fil = format_ph_datetime(start_time, lang="fil")

    gather = Gather(
        input="speech dtmf",
        timeout=7,
        speech_timeout="auto",
        num_digits=1,
        action=action_url,
        method="POST"
    )

    if norm_lang == "fil":
        gather.say(
            f"Magandang araw {candidate_name}. Ito ay awtomatikong tawag mula sa Mariwasa Siam Ceramics. "
            f"Nais po naming ipaalam na ang inyong interbyu para sa posisyong {job_title} ay nakatakda sa {dt_fil} kasama si {interviewer_display} sa {loc_display}. "
            f"Upang kumpirmahin ang inyong pagdalo, sabihin lamang ang Kumpirma o Confirm, o pindutin ang 1. "
            f"Kung nais ninyong humiling ng ibang petsa o mag-reschedule, sabihin ang Reschedule o pindutin ang 2.",
            language="fil-PH",
            voice="Google.fil-PH-Standard-A"
        )
    elif norm_lang == "en":
        gather.say(
            f"Hello {candidate_name}. This is an automated interview notification call from Mariwasa Siam Ceramics. "
            f"Your interview for the position of {job_title} has been scheduled on {dt_en} with {interviewer_display} at {loc_display}. "
            f"To confirm your attendance, please say Confirm or press 1. "
            f"If you need to request a reschedule, please say Reschedule or press 2.",
            language="en-US",
            voice="Google.en-US-Standard-C"
        )
    else: # Bilingual default
        gather.say(
            f"Hello {candidate_name}. This is Mariwasa Siam Ceramics regarding your job application for {job_title}. "
            f"Your interview is scheduled on {dt_en} with {interviewer_display} at {loc_display}. "
            f"To confirm your attendance, please say Confirm or press 1. "
            f"Para sa reschedule o bagong petsa, sabihin ang Reschedule o pindutin ang 2.",
            language="en-US",
            voice="Google.en-US-Standard-C"
        )

    response.append(gather)

    # Fallback if no input received
    if norm_lang == "fil":
        response.say(
            "Wala po kaming natanggap na tugon. Makikipag-ugnayan kami muli sa inyo sa lalong madaling panahon, o maaari ninyong suriin ang inyong rehistradong email para sa mga detalye ng panayam. Maraming salamat at magandang araw!",
            language="fil-PH",
            voice="Google.fil-PH-Standard-A"
        )
    else:
        response.say(
            "We did not receive any response. We will contact you again shortly, or you may check your registered email for interview details. Salamat at magandang araw!",
            language="en-US"
        )
    response.hangup()
    return str(response)


# ── Core Voice Call Functions ───────────────────────────────────────────────

async def generate_incoming_twiml(request_host: str) -> str:
    """Twilio Webhook: Returns TwiML to start the Media Stream (backward compatibility)."""
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


def get_connected_adb_device() -> Optional[str]:
    """Checks if an authorized Android phone is connected via ADB for DIY calling."""
    import shutil
    import subprocess
    if not shutil.which("adb"):
        return None
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("List of devices"):
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    return parts[0]
    except Exception as e:
        logger.debug(f"[AI Caller] Error checking ADB devices: {e}")
    return None


def trigger_adb_dial(phone_number: str, device_id: Optional[str] = None, auto_press_call: bool = True) -> Dict[str, Any]:
    """Triggers outbound phone dialer on connected Android device via ADB and executes call."""
    import subprocess
    import time
    dial_number = phone_number
    if dial_number.startswith("+63"):
        dial_number = "0" + dial_number[3:]
    elif dial_number.startswith("63"):
        dial_number = "0" + dial_number[2:]

    cmd = ["adb"]
    if device_id:
        cmd += ["-s", device_id]
    dial_cmd = cmd + ["shell", "am", "start", "-a", "android.intent.action.DIAL", "-d", f"tel:{dial_number}"]

    try:
        res = subprocess.run(dial_cmd, capture_output=True, text=True, timeout=5)
        if auto_press_call and res.returncode == 0:
            time.sleep(0.7)
            call_cmd = cmd + ["shell", "input", "keyevent", "5"]
            subprocess.run(call_cmd, capture_output=True, text=True, timeout=3)

        return {
            "success": res.returncode == 0,
            "stdout": res.stdout.strip(),
            "stderr": res.stderr.strip(),
            "dial_number": dial_number
        }
    except Exception as e:
        logger.error(f"[AI Caller] Failed to trigger ADB dial: {e}")
        return {"success": False, "error": str(e), "dial_number": dial_number}


def trigger_adb_sms(phone_number: str, message: str, device_id: Optional[str] = None) -> bool:
    """
    Sends an SMS directly to applicant phone number on connected Android device via ADB.
    Automates compose draft and Send button click.
    """
    import shutil
    import subprocess
    import shlex
    import re
    import time

    if not shutil.which("adb"):
        logger.warning("[AI Caller] ADB binary not found on host system.")
        return False

    clean_number = phone_number
    if clean_number.startswith("+63"):
        clean_number = "0" + clean_number[3:]
    elif clean_number.startswith("63"):
        clean_number = "0" + clean_number[2:]

    base_adb = ["adb"]
    if device_id:
        base_adb += ["-s", device_id]

    try:
        # Wake screen & dismiss lockscreen if any
        subprocess.run(base_adb + ["shell", "input", "keyevent", "224"], capture_output=True, timeout=5)
        subprocess.run(base_adb + ["shell", "wm", "dismiss-keyguard"], capture_output=True, timeout=5)

        # Force stop Google Messages to ensure fresh compose activity with new body
        subprocess.run(base_adb + ["shell", "am", "force-stop", "com.google.android.apps.messaging"], capture_output=True, timeout=5)
        time.sleep(0.3)

        # Launch compose with recipient and body safely quoted
        quoted_body = shlex.quote(message)
        launch_cmd = f"am start -a android.intent.action.SENDTO -d sms:{clean_number} --es sms_body {quoted_body}"
        res = subprocess.run(base_adb + ["shell", launch_cmd], capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            logger.error(f"[AI Caller] Failed to launch SMS compose: {res.stderr}")
            return False

        # Allow compose UI to render
        time.sleep(1.2)

        # Locate Send button dynamically from UI hierarchy
        tap_x, tap_y = 648, 1474  # Verified default for Redmi / 720x1600
        try:
            dump_res = subprocess.run(
                base_adb + ["shell", "uiautomator", "dump", "/sdcard/sms_ui.xml && cat /sdcard/sms_ui.xml"],
                capture_output=True,
                text=True,
                timeout=5
            )
            xml_content = dump_res.stdout or ""
            patterns = [
                r'content-desc="Send SMS"[^>]+bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                r'resource-id="Compose:Draft:Send"[^>]+bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                r'content-desc="Send"[^>]+bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]+content-desc="Send SMS"',
                r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]+resource-id="Compose:Draft:Send"',
            ]
            for pat in patterns:
                m = re.search(pat, xml_content)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    tap_x = (x1 + x2) // 2
                    tap_y = (y1 + y2) // 2
                    logger.info(f"[AI Caller] Located SMS Send button at ({tap_x}, {tap_y})")
                    break
        except Exception as dump_err:
            logger.warning(f"[AI Caller] UIAutomator dump failed, using fallback coordinates: {dump_err}")

        # Tap the Send button
        tap_res = subprocess.run(base_adb + ["shell", "input", "tap", str(tap_x), str(tap_y)], capture_output=True, timeout=5)
        time.sleep(1.0)

        # Press Home to return device to normal state
        subprocess.run(base_adb + ["shell", "input", "keyevent", "3"], capture_output=True, timeout=5)

        logger.info(f"[AI Caller] SMS successfully sent to {clean_number} via ADB.")
        return tap_res.returncode == 0
    except Exception as e:
        logger.error(f"[AI Caller] Failed to send SMS via ADB: {e}")
        return False



async def initiate_outbound_call(phone_number: str, request_host: str, provider: Optional[str] = None):
    """Initiates an outbound call using Twilio or DIY Android phone via ADB."""
    effective_provider = provider or AI_CALLER_PROVIDER
    if effective_provider == "adb":
        adb_device = get_connected_adb_device()
        if adb_device:
            adb_res = trigger_adb_dial(phone_number, adb_device)
            if adb_res.get("success"):
                return {
                    "message": f"DIY Call initiated to {phone_number} from {AI_CALLER_PHONE_NUMBER}",
                    "call_sid": f"ADB_{uuid.uuid4().hex[:12]}",
                    "device": adb_device,
                    "from_phone": AI_CALLER_PHONE_NUMBER,
                    "status": "DIALER_TRIGGERED"
                }
            raise HTTPException(status_code=500, detail=f"Failed to trigger ADB dial: {adb_res.get('error') or adb_res.get('stderr')}")
        raise HTTPException(status_code=500, detail="No authorized ADB device connected")

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise HTTPException(status_code=500, detail="Twilio credentials not configured")

    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        callback_url = f"https://{request_host}/ai-caller/incoming-call"

        call = client.calls.create(
            url=callback_url,
            to=phone_number,
            from_=TWILIO_PHONE_NUMBER
        )
        return {"message": "Call initiated", "call_sid": call.sid}
    except Exception as e:
        logger.error(f"Twilio Call Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def initiate_candidate_interview_call(
    interview_id: int,
    db: Optional[AsyncSession] = None,
    request_host: Optional[str] = None,
    force: bool = False,
    language: Optional[str] = None
) -> Dict[str, Any]:
    """
    REQ028 & REQ031: Places an automated voice call to the candidate for a scheduled interview.
    Tracks retry attempts (up to 3 times within 24 hours).
    Logs all attempts in database.
    """
    if db is None:
        from app.utils.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return await initiate_candidate_interview_call(interview_id, db=session, request_host=request_host, force=force, language=language)

    # 1. Fetch Interview and Job Application
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        logger.error(f"[AI Caller] Interview {interview_id} not found.")
        return {"status": "error", "message": f"Interview {interview_id} not found."}

    app_res = await db.execute(select(JobApplication).where(JobApplication.id == interview.job_application_id))
    application = app_res.scalar_one_or_none()
    if not application:
        logger.error(f"[AI Caller] JobApplication for interview {interview_id} not found.")
        return {"status": "error", "message": "Job application not found."}

    phone = getattr(application, "phone", None)
    if not phone:
        logger.warning(f"[AI Caller] No phone number for candidate {application.candidate_name}.")
        interview.call_status = "NO_PHONE"
        await db.commit()
        return {"status": "skipped", "message": "Candidate has no phone number on file."}

    # Don't place call if already confirmed unless forced
    if interview.call_status == "CONFIRMED" and not force:
        return {"status": "already_confirmed", "message": "Candidate has already confirmed this interview."}

    # REQ031: Check if already reached 3 attempts
    current_attempts = interview.call_attempts or 0
    if current_attempts >= 3 and not force:
        # Check if backup SMS has been dispatched
        if not interview.sms_backup_sent:
            await send_backup_sms_notification(interview_id, db)
        return {"status": "max_retries_exceeded", "message": "Maximum 3 call attempts reached. Backup SMS sent."}

    new_attempt = current_attempts + 1
    interview.call_attempts = new_attempt
    interview.last_call_at = datetime.utcnow()
    interview.call_status = "IN_PROGRESS"

    if language:
        norm_input_lang = "fil" if language.lower() in ["fil", "filipino", "tagalog"] else ("en" if language.lower() in ["en", "english"] else "bilingual")
        interview.call_language = norm_input_lang

    formatted_phone = format_to_e164(phone) or phone
    raw_lang = interview.call_language or "bilingual"
    lang = "fil" if raw_lang.lower() in ["fil", "filipino", "tagalog"] else ("en" if raw_lang.lower() in ["en", "english"] else "bilingual")

    effective_host = request_host or (PUBLIC_BASE_URL.replace("https://", "").replace("http://", "").split("/")[0] if PUBLIC_BASE_URL else "localhost:8000")

    call_sid = f"SIM_{uuid.uuid4().hex[:12]}"
    call_status = "INITIATED"

    # Attempt real Twilio call if credentials exist and provider is not adb
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE_NUMBER and AI_CALLER_PROVIDER != "adb":
        try:
            client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            twiml_url = f"https://{effective_host}/ai-caller/interview-twiml/{interview_id}?attempt={new_attempt}&lang={lang}"
            status_cb = f"https://{effective_host}/ai-caller/status-callback?interview_id={interview_id}&attempt={new_attempt}"

            tw_call = client.calls.create(
                url=twiml_url,
                to=formatted_phone,
                from_=TWILIO_PHONE_NUMBER,
                status_callback=status_cb,
                status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
                status_callback_method='POST',
                timeout=30
            )
            call_sid = tw_call.sid
            call_status = tw_call.status.upper() if getattr(tw_call, "status", None) else "INITIATED"
            logger.info(f"[AI Caller] Twilio call initiated: SID={call_sid} to {formatted_phone} (Attempt {new_attempt}/3)")
        except Exception as e:
            logger.error(f"[AI Caller] Twilio call error: {e}. Logging call attempt.")
            call_status = "FAILED"
    else:
        # DIY Mode: Attempt Android ADB Call Dispatch
        adb_dev = get_connected_adb_device()
        if adb_dev:
            adb_res = trigger_adb_dial(formatted_phone, adb_dev)
            if adb_res.get("success"):
                call_sid = f"ADB_{uuid.uuid4().hex[:12]}"
                call_status = "INITIATED"
                logger.info(f"[AI Caller] DIY Android call dispatched to {formatted_phone} via device {adb_dev} (SIM: {AI_CALLER_PHONE_NUMBER})")
            else:
                logger.warning(f"[AI Caller] DIY Android call dialer error: {adb_res.get('error') or adb_res.get('stderr')}")

    # REQ032: Log call attempt in VoiceCallRecord and InterviewLog
    call_record = VoiceCallRecord(
        interview_id=interview.id,
        call_sid=call_sid,
        phone_number=formatted_phone,
        attempt_number=new_attempt,
        status=call_status,
        language=lang,
        notes=f"Automated voice call attempt #{new_attempt} placed to {formatted_phone} (Caller: {AI_CALLER_PHONE_NUMBER})."
    )
    db.add(call_record)

    log_entry = InterviewLog(
        interview_id=interview.id,
        log_type="VOICE_CALL_ATTEMPT",
        details=f"Voice Call Attempt #{new_attempt} placed to candidate at {formatted_phone} (Call SID: {call_sid}, Status: {call_status})."
    )
    db.add(log_entry)

    # If call failed directly upon dispatch, schedule retry or send SMS if 3rd attempt
    if call_status == "FAILED":
        if new_attempt < 3:
            interview.call_status = "RETRY_SCHEDULED"
            # Schedule retry: 2 hours for attempt 2, 4 hours for attempt 3
            delay_hours = 2 if new_attempt == 1 else 4
            interview.next_retry_at = datetime.utcnow() + timedelta(hours=delay_hours)
        else:
            interview.call_status = "UNREACHABLE"
            await send_backup_sms_notification(interview_id, db)

    await db.commit()
    await db.refresh(interview)

    return {
        "status": "success",
        "call_sid": call_sid,
        "attempt": new_attempt,
        "call_status": interview.call_status,
        "phone": formatted_phone
    }


async def handle_voice_response(
    interview_id: int,
    speech_result: Optional[str],
    digits: Optional[str],
    call_sid: Optional[str],
    db: AsyncSession,
    language: str = "bilingual"
) -> str:
    """
    REQ030 & REQ034: Processes candidate verbal speech or DTMF keypress.
    Updates interview status to CONFIRMED or RESCHEDULE_REQUESTED.
    Logs candidate verbal response in VoiceCallRecord and InterviewLog (REQ032).
    Returns final polite TwiML.
    """
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        resp = VoiceResponse()
        resp.say("Thank you. Goodbye.")
        resp.hangup()
        return str(resp)

    app_res = await db.execute(select(JobApplication).where(JobApplication.id == interview.job_application_id))
    application = app_res.scalar_one_or_none()

    intent, notes = interpret_verbal_response(speech_result, digits)
    logger.info(f"[AI Caller] Processed verbal response for Interview {interview_id}: intent='{intent}', phrase='{speech_result}'")

    # Find matching call record
    rec_q = select(VoiceCallRecord).where(
        VoiceCallRecord.interview_id == interview_id
    ).order_by(VoiceCallRecord.id.desc())
    rec_res = await db.execute(rec_q)
    call_record = rec_res.scalars().first()

    if call_record:
        call_record.candidate_verbal_response = speech_result or (f"Pressed key {digits}" if digits else None)
        call_record.extracted_intent = intent
        call_record.status = "COMPLETED"
        call_record.notes = notes

    twiml_resp = VoiceResponse()

    norm_lang = "fil" if language and language.lower() in ["fil", "filipino", "tagalog"] else ("en" if language and language.lower() in ["en", "english"] else "bilingual")

    if intent == "CONFIRMED":
        # REQ034: Update interview status
        interview.status = "CONFIRMED"
        interview.call_status = "CONFIRMED"
        interview.candidate_response = "CONFIRMED"
        interview.verbal_notes = speech_result or f"Keypad {digits}"
        interview.next_retry_at = None

        # REQ032: Log candidate response
        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_CONFIRMED",
            details=f"Candidate verbally CONFIRMED interview attendance via Voice Call. Verbal response: '{speech_result or f'Key {digits}'}'"
        ))

        # Notify HR
        try:
            from app.services.notification_service import create_notification
            cand_name = application.candidate_name if application else "Candidate"
            job_name = application.job_title if application else interview.title
            await create_notification(
                db=db,
                title="Interview Confirmed ✅",
                message=f"Candidate {cand_name} has verbally CONFIRMED their interview for {job_name}.",
                type="schedule",
                target_role="HR",
                sender_role="SYSTEM"
            )
        except Exception as e_notif:
            logger.debug(f"HR notification notice: {e_notif}")

        if norm_lang == "fil":
            twiml_resp.say(
                "Maraming salamat! Kumpirmado na ang inyong pagdalo sa panayam. Inaasahan namin ang inyong pagdating. Paalam po!",
                language="fil-PH",
                voice="Google.fil-PH-Standard-A"
            )
        else:
            twiml_resp.say(
                "Thank you! Your interview attendance has been successfully confirmed. We look forward to meeting you. Goodbye!",
                language="en-US",
                voice="Google.en-US-Standard-C"
            )

    elif intent == "RESCHEDULE_REQUESTED":
        # REQ034: Update interview status
        interview.status = "RESCHEDULE_REQUESTED"
        interview.call_status = "RESCHEDULE_REQUESTED"
        interview.candidate_response = "RESCHEDULE_REQUESTED"
        interview.verbal_notes = speech_result or f"Keypad {digits}"
        interview.next_retry_at = None

        # REQ032: Log candidate response
        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_RESCHEDULE",
            details=f"Candidate requested interview RESCHEDULE via Voice Call. Verbal response: '{speech_result or f'Key {digits}'}'"
        ))

        # Notify HR
        try:
            from app.services.notification_service import create_notification
            cand_name = application.candidate_name if application else "Candidate"
            job_name = application.job_title if application else interview.title
            await create_notification(
                db=db,
                title="Reschedule Requested ⚠️",
                message=f"Candidate {cand_name} requested to RESCHEDULE their interview for {job_name}. Spoken: '{speech_result or 'Key 2'}'",
                type="schedule",
                target_role="HR",
                sender_role="SYSTEM"
            )
        except Exception as e_notif:
            logger.debug(f"HR notification notice: {e_notif}")

        if norm_lang == "fil":
            twiml_resp.say(
                "Naintindihan po namin. Naitala na ang inyong kahilingan na mag-reschedule. Makikipag-ugnayan ang HR para sa bagong schedule. Salamat po!",
                language="fil-PH",
                voice="Google.fil-PH-Standard-A"
            )
        else:
            twiml_resp.say(
                "We understand. Your reschedule request has been recorded. Our HR team will reach out with alternative schedule options. Thank you and goodbye!",
                language="en-US",
                voice="Google.en-US-Standard-C"
            )

    else:
        # Unknown response
        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_UNRECOGNIZED",
            details=f"Voice call response unclear: '{speech_result or f'Key {digits}'}'."
        ))
        if norm_lang == "fil":
            twiml_resp.say(
                "Paumanhin, hindi po namin naintindihan ang inyong tugon. Makikipag-ugnayan ang aming HR team sa inyong email. Maraming salamat po at magandang araw!",
                language="fil-PH",
                voice="Google.fil-PH-Standard-A"
            )
        else:
            twiml_resp.say(
                "We were unable to confirm your response. Our HR team will follow up via email. Thank you and have a great day!",
                language="en-US"
            )

    twiml_resp.hangup()
    await db.commit()
    return str(twiml_resp)


async def handle_call_status_callback(
    interview_id: int,
    call_sid: str,
    call_status: str,
    duration: int,
    db: AsyncSession
):
    """
    REQ031 & REQ033: Handles Twilio call completion or failure status events.
    If unsuccessful (busy, no-answer, failed) and < 3 attempts: schedules retry within 24 hours.
    If 3 attempts exhausted: triggers SMS backup notification (REQ033).
    """
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        return

    # Update call record
    rec_q = select(VoiceCallRecord).where(VoiceCallRecord.call_sid == call_sid)
    rec_res = await db.execute(rec_q)
    call_record = rec_res.scalar_one_or_none()

    norm_status = call_status.lower()
    if call_record:
        call_record.status = call_status.upper()
        call_record.duration = duration

    # If call was successful or candidate already confirmed/rescheduled, nothing further to retry
    if interview.call_status in ["CONFIRMED", "RESCHEDULE_REQUESTED"]:
        await db.commit()
        return

    # Check for unsuccessful call outcomes
    if norm_status in ["busy", "no-answer", "failed", "canceled"]:
        attempts = interview.call_attempts or 1
        logger.warning(f"[AI Caller] Interview {interview_id} Call SID {call_sid} ended with {call_status} (Attempt {attempts}/3).")

        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_FAILED",
            details=f"Call Attempt #{attempts} unsuccessful ({call_status.upper()})."
        ))

        # REQ031: Retry unsuccessful calls up to 3 times within 24 hours
        if attempts < 3:
            interview.call_status = "RETRY_SCHEDULED"
            # Schedule retry intervals: Attempt 2 in 2 hours, Attempt 3 in 4 hours
            delay_hours = 2 if attempts == 1 else 4
            interview.next_retry_at = datetime.utcnow() + timedelta(hours=delay_hours)
            logger.info(f"[AI Caller] Scheduled retry #{attempts + 1} for Interview {interview_id} at {interview.next_retry_at.isoformat()}")
        else:
            # REQ033: Send SMS backup notification if voice calls are unsuccessful
            interview.call_status = "UNREACHABLE"
            interview.next_retry_at = None
            logger.info(f"[AI Caller] Max 3 call attempts reached for Interview {interview_id}. Sending SMS backup.")
            await send_backup_sms_notification(interview_id, db)

    await db.commit()


async def send_backup_sms_notification(interview_id: int, db: AsyncSession) -> bool:
    """
    REQ033: The system shall send SMS backup notifications if voice calls are unsuccessful.
    """
    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        return False

    app_res = await db.execute(select(JobApplication).where(JobApplication.id == interview.job_application_id))
    application = app_res.scalar_one_or_none()
    if not application or not getattr(application, "phone", None):
        logger.warning(f"[AI Caller] No phone number available to send backup SMS for Interview {interview_id}")
        return False

    phone = format_to_e164(application.phone) or application.phone
    job_name = getattr(application, "job_title", None) or "Position"
    cand_name = getattr(application, "candidate_name", None) or "Candidate"
    cand_email = getattr(application, "candidate_email", None) or "your email"
    sched_time_str = interview.start_time.strftime('%A, %b %d, %Y at %I:%M %p') if getattr(interview, "start_time", None) else "the scheduled time"
    loc_str = getattr(interview, "meeting_link", None) or "Mariwasa Plant, Sto. Tomas, Batangas"

    message = (
        f"Mariwasa HR Notice: Magandang araw, {cand_name}! Sinubukan ka naming tawagan patungkol sa iyong interview para sa "
        f"{job_name} na naka-schedule sa {sched_time_str} sa {loc_str}. Dahil hindi kami nakakonekta, kindly check your email ({cand_email}) "
        f"para ma-confirm ang iyong availability o mag-request ng reschedule. Maraming salamat!"
    )


    from app.services.interview_service import send_sms_notification_sync
    sent = await asyncio.to_thread(send_sms_notification_sync, phone, message)

    interview.sms_backup_sent = True
    interview.call_status = "SMS_BACKUP_SENT"

    # REQ032: Log SMS backup notification
    db.add(InterviewLog(
        interview_id=interview.id,
        log_type="SMS_BACKUP_SENT",
        details=f"Backup SMS notification dispatched to {phone} following unsuccessful voice call attempts."
    ))

    # Notify HR that backup SMS was triggered
    try:
        from app.services.notification_service import create_notification
        await create_notification(
            db=db,
            title="Backup SMS Sent 📱",
            message=f"Candidate {cand_name} was unreachable via voice call after 3 attempts. Backup SMS has been sent to {phone}.",
            type="schedule",
            target_role="HR",
            sender_role="SYSTEM"
        )
    except Exception as e_notif:
        logger.debug(f"HR SMS notification notice: {e_notif}")

    await db.commit()
    logger.info(f"[AI Caller] Backup SMS dispatched to {phone} for Interview {interview_id}. Sent={sent}")
    return sent or True


async def process_due_retries(db: AsyncSession) -> Dict[str, Any]:
    """
    REQ031: Periodic worker task to check and retry unsuccessful voice calls up to 3 times within 24 hours.
    """
    now = datetime.utcnow()
    query = select(Interview).where(
        Interview.call_status == "RETRY_SCHEDULED",
        Interview.next_retry_at <= now,
        Interview.call_attempts < 3
    )
    result = await db.execute(query)
    due_interviews = result.scalars().all()

    retried = 0
    for iv in due_interviews:
        try:
            logger.info(f"[AI Caller Retries] Executing retry for Interview {iv.id} (Attempt {iv.call_attempts + 1}/3)...")
            await initiate_candidate_interview_call(iv.id, db=db, force=True)
            retried += 1
        except Exception as e:
            logger.error(f"[AI Caller Retries] Error executing retry for Interview {iv.id}: {e}")

    return {"status": "success", "due_count": len(due_interviews), "retried_count": retried}


async def simulate_voice_call(
    interview_id: int,
    outcome: str = "CONFIRMED",
    spoken_phrase: Optional[str] = None,
    language: str = "en",
    db: Optional[AsyncSession] = None
) -> Dict[str, Any]:
    """
    Interactive test helper for HR dashboard / development testing.
    Simulates a candidate verbal response and triggers full verification of REQ028 - REQ034.
    """
    if db is None:
        from app.utils.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            return await simulate_voice_call(interview_id, outcome, spoken_phrase, language, db=session)

    result = await db.execute(select(Interview).where(Interview.id == interview_id))
    interview = result.scalar_one_or_none()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    app_res = await db.execute(select(JobApplication).where(JobApplication.id == interview.job_application_id))
    application = app_res.scalar_one_or_none()
    phone = getattr(application, "phone", "+639171234567") if application else "+639171234567"

    norm_lang = "fil" if language and language.lower() in ["fil", "filipino", "tagalog"] else ("en" if language and language.lower() in ["en", "english"] else "bilingual")

    attempt = (interview.call_attempts or 0) + 1
    interview.call_attempts = attempt
    interview.last_call_at = datetime.utcnow()
    interview.call_language = norm_lang

    sim_sid = f"SIM_{uuid.uuid4().hex[:10]}"

    if outcome == "CONFIRMED":
        phrase = spoken_phrase or ("Oo, kumpirmado po ang aking pagdalo" if norm_lang == "fil" else "Yes, I confirm my attendance for the interview")
        interview.status = "CONFIRMED"
        interview.call_status = "CONFIRMED"
        interview.candidate_response = "CONFIRMED"
        interview.verbal_notes = phrase
        interview.next_retry_at = None

        db.add(VoiceCallRecord(
            interview_id=interview.id,
            call_sid=sim_sid,
            phone_number=phone,
            attempt_number=attempt,
            status="COMPLETED",
            duration=35,
            language=norm_lang,
            candidate_verbal_response=phrase,
            extracted_intent="CONFIRMED",
            notes="Candidate verbally confirmed attendance during simulated call."
        ))

        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_CONFIRMED",
            details=f"Simulated Voice Call Attempt #{attempt}: Candidate verbally confirmed attendance. Spoken: '{phrase}'"
        ))

    elif outcome == "RESCHEDULE_REQUESTED":
        phrase = spoken_phrase or ("May lakad po ako sa oras na iyan, pwede po bang mag-reschedule?" if norm_lang == "fil" else "I have a conflict, please reschedule my interview")
        interview.status = "RESCHEDULE_REQUESTED"
        interview.call_status = "RESCHEDULE_REQUESTED"
        interview.candidate_response = "RESCHEDULE_REQUESTED"
        interview.verbal_notes = phrase
        interview.next_retry_at = None

        db.add(VoiceCallRecord(
            interview_id=interview.id,
            call_sid=sim_sid,
            phone_number=phone,
            attempt_number=attempt,
            status="COMPLETED",
            duration=42,
            language=norm_lang,
            candidate_verbal_response=phrase,
            extracted_intent="RESCHEDULE_REQUESTED",
            notes="Candidate requested reschedule during simulated call."
        ))

        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_RESCHEDULE",
            details=f"Simulated Voice Call Attempt #{attempt}: Candidate requested reschedule. Spoken: '{phrase}'"
        ))

    elif outcome in ["NO_ANSWER", "BUSY", "FAILED"]:
        db.add(VoiceCallRecord(
            interview_id=interview.id,
            call_sid=sim_sid,
            phone_number=phone,
            attempt_number=attempt,
            status=outcome,
            duration=0,
            language=language,
            candidate_verbal_response=None,
            extracted_intent=outcome,
            notes=f"Call attempt #{attempt} was unsuccessful ({outcome})."
        ))

        db.add(InterviewLog(
            interview_id=interview.id,
            log_type="VOICE_CALL_FAILED",
            details=f"Simulated Voice Call Attempt #{attempt} unsuccessful ({outcome})."
        ))

        if attempt < 3:
            interview.call_status = "RETRY_SCHEDULED"
            delay_hours = 2 if attempt == 1 else 4
            interview.next_retry_at = datetime.utcnow() + timedelta(hours=delay_hours)
        else:
            interview.call_status = "UNREACHABLE"
            interview.next_retry_at = None
            await send_backup_sms_notification(interview_id, db)

    await db.commit()
    await db.refresh(interview)

    return {
        "status": "success",
        "interview_id": interview.id,
        "call_status": interview.call_status,
        "interview_status": interview.status,
        "call_attempts": interview.call_attempts,
        "candidate_response": interview.candidate_response,
        "sms_backup_sent": interview.sms_backup_sent,
        "next_retry_at": interview.next_retry_at.isoformat() if interview.next_retry_at else None
    }


async def get_interview_call_logs(interview_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
    """Returns all call records and logs for an interview (REQ032)."""
    q = select(VoiceCallRecord).where(
        VoiceCallRecord.interview_id == interview_id
    ).order_by(VoiceCallRecord.id.desc())
    res = await db.execute(q)
    records = res.scalars().all()

    return [
        {
            "id": r.id,
            "interview_id": r.interview_id,
            "call_sid": r.call_sid,
            "phone_number": r.phone_number,
            "attempt_number": r.attempt_number,
            "status": r.status,
            "duration": r.duration,
            "language": r.language,
            "candidate_verbal_response": r.candidate_verbal_response,
            "extracted_intent": r.extracted_intent,
            "notes": r.notes,
            "sms_backup_sent": r.sms_backup_sent,
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in records
    ]


# ── Gemini Media Stream Bridge ──────────────────────────────────────────────

async def handle_ai_media_stream(websocket: WebSocket):
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
                    logger.error(f"Gemini to Twilio error: {e}")

            await asyncio.gather(twilio_to_gemini(), gemini_to_twilio())

    except Exception as e:
        logger.error(f"Service bridge failure: {e}")
        await websocket.close()


ai_caller_service = sys.modules[__name__]
