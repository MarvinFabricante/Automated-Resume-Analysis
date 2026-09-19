import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CREDENTIALS_FILE = os.path.join(_BACKEND_DIR, 'credentials.json')

# In-memory store for OAuth metadata, keyed by OAuth state.
_pending_flows: dict[str, dict[str, str]] = {}

def _client_config():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if client_id and client_secret:
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [],
            }
        }
    return None

def _new_flow(redirect_uri: str):
    config = _client_config()
    if config:
        return Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
    return Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

def get_google_auth_url(redirect_uri: str, frontend_origin: str):
    flow = _new_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='select_account consent',
    )
    _pending_flows[state] = {
        "code_verifier": flow.code_verifier,
        "redirect_uri": redirect_uri,
        "frontend_origin": frontend_origin,
    }
    return auth_url, state

def exchange_code_for_credentials(code: str, state: str):
    pending = _pending_flows.pop(state, {})
    redirect_uri = pending.get("redirect_uri") or os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/auth/google/callback",
    )
    flow = _new_flow(redirect_uri)
    flow.code_verifier = pending.get("code_verifier")
    flow.fetch_token(code=code)
    creds = flow.credentials
    return creds, pending.get("frontend_origin")

def get_calendar_service(credentials_json: str):
    if not credentials_json:
        return None
    try:
        creds_data = json.loads(credentials_json)
        creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
        service = build('calendar', 'v3', credentials=creds)
        return service, creds.to_json()
    except Exception as e:
        print(f"Error building calendar service: {e}")
        return None, credentials_json
