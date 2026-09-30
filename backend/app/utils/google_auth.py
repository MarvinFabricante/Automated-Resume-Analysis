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

# In-memory store for PKCE code_verifier and flow_type, keyed by OAuth state
_pending_flows: dict[str, dict] = {}


def _get_redirect_uri() -> str:
    """
    Build the Google OAuth redirect URI dynamically.
    Uses PUBLIC_BASE_URL (the Cloudflare tunnel URL) when available,
    otherwise falls back to localhost for local development.
    The redirect goes through nginx's /api/ proxy which strips the prefix,
    so the backend sees /auth/google/callback.
    """
    public_url = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if public_url:
        return f"{public_url}/api/auth/google/callback"
    return "http://localhost:8000/auth/google/callback"


def get_google_auth_url(flow_type: str = "login"):
    redirect_uri = _get_redirect_uri()
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    # Store the code_verifier and flow_type so we can pass it during token exchange
    _pending_flows[state] = {
        "verifier": flow.code_verifier,
        "flow_type": flow_type
    }
    return auth_url, state

def exchange_code_for_credentials(code: str, state: str):
    redirect_uri = _get_redirect_uri()
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    # Restore the PKCE code_verifier and flow_type from the original auth request
    flow_info = _pending_flows.pop(state, None)
    if isinstance(flow_info, dict):
        code_verifier = flow_info.get("verifier")
        flow_type = flow_info.get("flow_type", "login")
    else:
        code_verifier = flow_info
        flow_type = "login"

    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials
    return creds, flow_type

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
