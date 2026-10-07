import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Candidate and standard authentication scopes: ONLY identity and basic profile.
# Completely excludes Google Calendar scopes to ensure zero calendar permissions,
# preventing conflicts with Google Cloud Console test-user restrictions.
CANDIDATE_AUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

# Scopes for authorized HR staff who manage interview schedules & Google Calendar events.
CALENDAR_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

# Legacy alias for backwards compatibility with calendar services
SCOPES = CALENDAR_SCOPES

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CREDENTIALS_FILE = os.path.join(_BACKEND_DIR, 'credentials.json')

import redis

# Multi-worker store for PKCE code_verifier, flow_type, role, and scopes, keyed by OAuth state.
# Uses Redis so any Uvicorn worker process can exchange the code, falling back to in-memory dict.
_pending_flows: dict[str, dict] = {}
_redis_sync_client = None

def _get_redis_client():
    global _redis_sync_client
    if _redis_sync_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
            client.ping()
            _redis_sync_client = client
        except Exception:
            _redis_sync_client = False
    return _redis_sync_client if _redis_sync_client is not False else None

def _save_pending_flow(state: str, flow_info: dict):
    _pending_flows[state] = flow_info
    client = _get_redis_client()
    if client:
        try:
            client.setex(f"oauth_flow:{state}", 900, json.dumps(flow_info))
        except Exception as e:
            print(f"Warning: Failed to cache OAuth state in Redis: {e}")

def _pop_pending_flow(state: str) -> dict:
    flow_info = None
    client = _get_redis_client()
    if client:
        try:
            raw = client.get(f"oauth_flow:{state}")
            if raw:
                client.delete(f"oauth_flow:{state}")
                flow_info = json.loads(raw)
        except Exception as e:
            print(f"Warning: Failed to retrieve OAuth state from Redis: {e}")
    if not flow_info:
        flow_info = _pending_flows.pop(state, {})
    else:
        _pending_flows.pop(state, None)
    return flow_info or {}


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


def _get_redirect_uri(base_origin: str = None) -> str:
    """
    Build the Google OAuth redirect URI dynamically.
    If base_origin is provided, constructs redirect URI from it.
    Uses PUBLIC_BASE_URL (e.g. Cloudflare tunnel URL) when available,
    otherwise falls back to localhost for local development.
    The redirect goes through nginx's /api/ proxy which strips the prefix,
    so the backend sees /auth/google/callback.
    """
    if base_origin:
        clean = base_origin.rstrip("/")
        if clean.endswith(":8000"):
            return f"{clean}/auth/google/callback"
        return f"{clean}/api/auth/google/callback"

    public_url = (os.getenv("PUBLIC_BASE_URL") or os.getenv("APP_PUBLIC_URL") or "").rstrip("/")
    if public_url:
        return f"{public_url}/api/auth/google/callback"
    return os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")


def _create_flow(scopes: list[str], redirect_uri: str):
    config = _client_config()
    if config:
        return Flow.from_client_config(
            config,
            scopes=scopes,
            redirect_uri=redirect_uri
        )
    return Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=scopes,
        redirect_uri=redirect_uri
    )


def get_candidate_google_auth_url(flow_type: str = "candidate_login", redirect_uri: str = None):
    """
    Generate Google OAuth URL specifically for candidate login or registration.
    Uses CANDIDATE_AUTH_SCOPES (openid, email, profile) ONLY.
    Does NOT request calendar permissions or interact with Google Calendar Console services,
    avoiding 403 access_denied / unverified app blocks for non-test users.
    """
    chosen_redirect_uri = redirect_uri or _get_redirect_uri()
    flow = _create_flow(
        scopes=CANDIDATE_AUTH_SCOPES,
        redirect_uri=chosen_redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type='online',
        prompt='select_account'
    )
    _save_pending_flow(state, {
        "verifier": flow.code_verifier,
        "flow_type": flow_type,
        "role": "candidate",
        "scopes": CANDIDATE_AUTH_SCOPES,
        "redirect_uri": chosen_redirect_uri
    })
    return auth_url, state


def get_hr_google_auth_url(flow_type: str = "hr_login", redirect_uri: str = None):
    """
    Generate Google OAuth URL specifically for HR staff.
    Uses CALENDAR_SCOPES to allow Google Calendar synchronization for interview management.
    Requires the Google account to be registered/authorized in Google Console.
    """
    chosen_redirect_uri = redirect_uri or _get_redirect_uri()
    flow = _create_flow(
        scopes=CALENDAR_SCOPES,
        redirect_uri=chosen_redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    _save_pending_flow(state, {
        "verifier": flow.code_verifier,
        "flow_type": flow_type,
        "role": "hr",
        "scopes": CALENDAR_SCOPES,
        "redirect_uri": chosen_redirect_uri
    })
    return auth_url, state


def get_admin_google_auth_url(flow_type: str = "admin_login", redirect_uri: str = None):
    """
    Generate Google OAuth URL specifically for System Administrators.
    Uses CANDIDATE_AUTH_SCOPES (identity and profile).
    """
    chosen_redirect_uri = redirect_uri or _get_redirect_uri()
    flow = _create_flow(
        scopes=CANDIDATE_AUTH_SCOPES,
        redirect_uri=chosen_redirect_uri
    )
    auth_url, state = flow.authorization_url(
        access_type='online',
        prompt='select_account'
    )
    _save_pending_flow(state, {
        "verifier": flow.code_verifier,
        "flow_type": flow_type,
        "role": "admin",
        "scopes": CANDIDATE_AUTH_SCOPES,
        "redirect_uri": chosen_redirect_uri
    })
    return auth_url, state


def get_google_auth_url(role: str = "auto", flow_type: str = "login", redirect_uri: str = None, frontend_origin: str = None):
    """
    Generate Google OAuth URL based on the requested role and flow.
    - If role is 'auto' (default for login): uses CANDIDATE_AUTH_SCOPES (identity and profile)
      so any user (Candidate, HR, Admin) can authenticate without calendar permissions
      or Google Console access_denied restrictions. Role is automatically resolved on callback.
    - If role is explicitly 'hr' or flow is 'hr_login': requests CALENDAR_SCOPES for Google Calendar sync.
    - If role is explicitly 'admin': requests admin authentication scopes.
    - Candidate flows: uses CANDIDATE_AUTH_SCOPES.
    """
    norm_role = (role or "auto").strip().lower()
    norm_flow = (flow_type or "login").strip().lower()

    if norm_flow in ["candidate_register", "register"]:
        return get_candidate_google_auth_url(flow_type="candidate_register", redirect_uri=redirect_uri)
    elif norm_role == "hr" or norm_flow == "hr_login":
        return get_hr_google_auth_url(flow_type="hr_login", redirect_uri=redirect_uri)
    elif norm_role == "admin" or norm_flow == "admin_login":
        return get_admin_google_auth_url(flow_type="admin_login", redirect_uri=redirect_uri)
    elif norm_role == "candidate":
        return get_candidate_google_auth_url(flow_type="candidate_login", redirect_uri=redirect_uri)
    else:
        # Universal login with automatic role detection
        chosen_redirect_uri = redirect_uri or _get_redirect_uri()
        flow = _create_flow(
            scopes=CANDIDATE_AUTH_SCOPES,
            redirect_uri=chosen_redirect_uri
        )
        auth_url, state = flow.authorization_url(
            access_type='online',
            prompt='select_account'
        )
        _save_pending_flow(state, {
            "verifier": flow.code_verifier,
            "flow_type": norm_flow,
            "role": "auto",
            "scopes": CANDIDATE_AUTH_SCOPES,
            "redirect_uri": chosen_redirect_uri
        })
        return auth_url, state


def exchange_code_for_credentials(code: str, state: str):
    flow_info = _pop_pending_flow(state)
    redirect_uri = flow_info.get("redirect_uri") or _get_redirect_uri()
    scopes = flow_info.get("scopes", CANDIDATE_AUTH_SCOPES)
    code_verifier = flow_info.get("verifier")
    flow_type = flow_info.get("flow_type", "login")
    role = flow_info.get("role", "auto")

    flow = _create_flow(
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    if code_verifier:
        flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials
    return creds, {
        "flow_type": flow_type,
        "role": role,
        "scopes": scopes,
        "redirect_uri": redirect_uri
    }


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
