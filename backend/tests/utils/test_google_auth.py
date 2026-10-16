import os
import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

import app.utils.google_auth as ga


def test_scopes_constants():
    assert "openid" in ga.CANDIDATE_AUTH_SCOPES
    assert "https://www.googleapis.com/auth/calendar" in ga.CALENDAR_SCOPES
    assert ga.SCOPES == ga.CALENDAR_SCOPES


def test_get_redis_client_success():
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True

    with patch("redis.Redis.from_url", return_value=mock_redis):
        with patch.object(ga, "_redis_sync_client", None):
            client = ga._get_redis_client()
            assert client == mock_redis


def test_get_redis_client_failure():
    with patch("redis.Redis.from_url", side_effect=Exception("Redis down")):
        with patch.object(ga, "_redis_sync_client", None):
            client = ga._get_redis_client()
            assert client is None
            assert ga._redis_sync_client is False


def test_save_and_pop_pending_flow_memory_only():
    with patch.object(ga, "_get_redis_client", return_value=None):
        ga._pending_flows.clear()
        flow_info = {"verifier": "xyz123", "role": "candidate"}
        ga._save_pending_flow("state_abc", flow_info)

        popped = ga._pop_pending_flow("state_abc")
        assert popped == flow_info
        # Popping again should return empty dict
        assert ga._pop_pending_flow("state_abc") == {}


def test_save_and_pop_pending_flow_with_redis():
    mock_redis = MagicMock()
    mock_redis.get.return_value = json.dumps({"verifier": "ver1", "role": "hr"})

    with patch.object(ga, "_get_redis_client", return_value=mock_redis):
        ga._save_pending_flow("state_redis", {"verifier": "ver1", "role": "hr"})
        mock_redis.setex.assert_called_once()

        popped = ga._pop_pending_flow("state_redis")
        assert popped == {"verifier": "ver1", "role": "hr"}
        mock_redis.delete.assert_called_once_with("oauth_flow:state_redis")


def test_client_config():
    with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "cid_123", "GOOGLE_CLIENT_SECRET": "sec_456"}):
        cfg = ga._client_config()
        assert cfg is not None
        assert cfg["web"]["client_id"] == "cid_123"
        assert cfg["web"]["client_secret"] == "sec_456"

    with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "", "GOOGLE_CLIENT_SECRET": ""}):
        assert ga._client_config() is None


def test_get_redirect_uri():
    # Base origin with port 8000
    uri_8000 = ga._get_redirect_uri("http://localhost:8000")
    assert uri_8000 == "http://localhost:8000/auth/google/callback"

    # Base origin production / standard
    uri_prod = ga._get_redirect_uri("https://mycompany.com")
    assert uri_prod == "https://mycompany.com/api/auth/google/callback"

    # From PUBLIC_BASE_URL env var
    with patch.dict(os.environ, {"PUBLIC_BASE_URL": "https://tunnel.example.com", "APP_PUBLIC_URL": ""}):
        assert ga._get_redirect_uri() == "https://tunnel.example.com/api/auth/google/callback"

    # Fallback to GOOGLE_REDIRECT_URI
    with patch.dict(os.environ, {"PUBLIC_BASE_URL": "", "APP_PUBLIC_URL": "", "GOOGLE_REDIRECT_URI": "http://custom/cb"}):
        assert ga._get_redirect_uri() == "http://custom/cb"


def test_create_flow():
    mock_flow_instance = MagicMock()
    # When client config is present
    with patch.object(ga, "_client_config", return_value={"web": {"client_id": "c"}}):
        with patch("google_auth_oauthlib.flow.Flow.from_client_config", return_value=mock_flow_instance) as mock_from_cfg:
            flow = ga._create_flow(["openid"], "http://cb")
            assert flow == mock_flow_instance
            mock_from_cfg.assert_called_once()

    # When client config is None -> from client secrets file
    with patch.object(ga, "_client_config", return_value=None):
        with patch("google_auth_oauthlib.flow.Flow.from_client_secrets_file", return_value=mock_flow_instance) as mock_from_file:
            flow = ga._create_flow(["openid"], "http://cb")
            assert flow == mock_flow_instance
            mock_from_file.assert_called_once()


def test_get_candidate_google_auth_url():
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://accounts.google.com/auth", "state_cand")
    mock_flow.code_verifier = "cand_verifier"

    with patch.object(ga, "_create_flow", return_value=mock_flow):
        with patch.object(ga, "_save_pending_flow") as mock_save:
            auth_url, state = ga.get_candidate_google_auth_url(user_id=10)
            assert auth_url == "https://accounts.google.com/auth"
            assert state == "state_cand"
            mock_flow.authorization_url.assert_called_once_with(
                access_type="online",
                prompt="select_account",
            )
            mock_save.assert_called_once()
            save_args = mock_save.call_args[0]
            assert save_args[0] == "state_cand"
            assert save_args[1]["role"] == "candidate"
            assert save_args[1]["user_id"] == 10


def test_get_hr_google_auth_url():
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://accounts.google.com/auth_hr", "state_hr")
    mock_flow.code_verifier = "hr_verifier"

    with patch.object(ga, "_create_flow", return_value=mock_flow):
        with patch.object(ga, "_save_pending_flow") as mock_save:
            auth_url, state = ga.get_hr_google_auth_url()
            assert auth_url == "https://accounts.google.com/auth_hr"
            assert state == "state_hr"
            mock_flow.authorization_url.assert_called_once_with(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
            mock_save.assert_called_once()
            assert mock_save.call_args[0][1]["role"] == "hr"


def test_get_admin_google_auth_url():
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("https://accounts.google.com/auth_admin", "state_admin")
    mock_flow.code_verifier = "admin_verifier"

    with patch.object(ga, "_create_flow", return_value=mock_flow):
        with patch.object(ga, "_save_pending_flow") as mock_save:
            auth_url, state = ga.get_admin_google_auth_url()
            assert auth_url == "https://accounts.google.com/auth_admin"
            assert state == "state_admin"
            mock_save.assert_called_once()
            assert mock_save.call_args[0][1]["role"] == "admin"


def test_get_google_auth_url_routing():
    with patch.object(ga, "get_candidate_google_auth_url", return_value=("cand_url", "s1")) as m_cand, \
         patch.object(ga, "get_hr_google_auth_url", return_value=("hr_url", "s2")) as m_hr, \
         patch.object(ga, "get_admin_google_auth_url", return_value=("admin_url", "s3")) as m_admin:

        # Candidate registration
        url, s = ga.get_google_auth_url(flow_type="candidate_register")
        assert url == "cand_url"
        m_cand.assert_called_once()

        # HR login
        url, s = ga.get_google_auth_url(role="hr")
        assert url == "hr_url"
        m_hr.assert_called_once()

        # Admin login
        url, s = ga.get_google_auth_url(role="admin")
        assert url == "admin_url"
        m_admin.assert_called_once()

        # Candidate login
        url, s = ga.get_google_auth_url(role="candidate")
        assert url == "cand_url"

    # Universal login with role="auto"
    mock_flow = MagicMock()
    mock_flow.authorization_url.return_value = ("auto_url", "s_auto")
    with patch.object(ga, "_create_flow", return_value=mock_flow), \
         patch.object(ga, "_save_pending_flow") as mock_save:
        url, s = ga.get_google_auth_url(role="auto", flow_type="login")
        assert url == "auto_url"
        assert s == "s_auto"
        assert mock_save.call_args[0][1]["role"] == "auto"


def test_exchange_code_for_credentials():
    mock_flow = MagicMock()
    mock_creds = MagicMock()
    mock_flow.credentials = mock_creds

    pending_data = {
        "verifier": "test_code_verifier",
        "redirect_uri": "http://localhost:8000/auth/google/callback",
        "scopes": ga.CANDIDATE_AUTH_SCOPES,
        "flow_type": "login",
        "role": "candidate",
        "user_id": 5,
    }

    with patch.object(ga, "_pop_pending_flow", return_value=pending_data):
        with patch.object(ga, "_create_flow", return_value=mock_flow):
            creds, meta = ga.exchange_code_for_credentials(code="auth_code_123", state="state_xyz")
            assert creds == mock_creds
            assert meta["flow_type"] == "login"
            assert meta["role"] == "candidate"
            assert meta["user_id"] == 5
            assert mock_flow.code_verifier == "test_code_verifier"
            mock_flow.fetch_token.assert_called_once_with(code="auth_code_123")


def test_is_google_credentials_expired():
    # Empty
    assert ga.is_google_credentials_expired("") is True
    assert ga.is_google_credentials_expired(None) is True

    # Expired timestamp
    past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    expired_json = json.dumps({"token": "abc", "expiry": past_iso})
    assert ga.is_google_credentials_expired(expired_json) is True

    # Future timestamp
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    valid_json = json.dumps({"token": "abc", "expiry": future_iso})
    assert ga.is_google_credentials_expired(valid_json) is False

    # Malformed json
    assert ga.is_google_credentials_expired("malformed json") is True


def test_get_calendar_service_expired_or_empty():
    svc, raw = ga.get_calendar_service(None)
    assert svc is None
    assert raw is None

    past_iso = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    expired_json = json.dumps({"token": "abc", "expiry": past_iso})
    svc, raw = ga.get_calendar_service(expired_json)
    assert svc is None
    assert raw == expired_json


def test_get_calendar_service_valid():
    future_iso = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    valid_creds_dict = {
        "token": "tok_123",
        "refresh_token": "ref_123",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "cid",
        "client_secret": "sec",
        "scopes": ga.CALENDAR_SCOPES,
        "expiry": future_iso,
    }
    valid_json = json.dumps(valid_creds_dict)

    mock_service = MagicMock()
    with patch("google.oauth2.credentials.Credentials.from_authorized_user_info") as mock_from_info:
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds.to_json.return_value = valid_json
        mock_from_info.return_value = mock_creds

        with patch("app.utils.google_auth.build", return_value=mock_service) as mock_build:
            svc, creds_out = ga.get_calendar_service(valid_json)
            assert svc == mock_service
            assert creds_out == valid_json
            mock_build.assert_called_once_with("calendar", "v3", credentials=mock_creds)

