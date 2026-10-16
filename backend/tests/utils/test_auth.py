import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from jose import jwt

from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_optional_current_user,
    require_role,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


def test_hash_password_and_verify():
    raw = "MySuperSecretPassword123!"
    hashed = hash_password(raw)

    assert hashed != raw
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_hash_and_verify_long_password():
    # Passwords over 72 chars are truncated to 72 by bcrypt
    long_pwd = "A" * 100
    hashed = hash_password(long_pwd)
    
    assert verify_password(long_pwd, hashed) is True
    assert verify_password("A" * 72, hashed) is True
    assert verify_password("A" * 71, hashed) is False


def test_create_access_token_default_expiry():
    data = {"sub": "user@example.com", "role": "CANDIDATE"}
    token = create_access_token(data)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "user@example.com"
    assert payload["role"] == "CANDIDATE"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["expires_in"] == ACCESS_TOKEN_EXPIRE_MINUTES * 60


def test_create_access_token_custom_expiry():
    data = {"sub": "admin@example.com", "role": "ADMIN"}
    custom_minutes = 15
    token = create_access_token(data, expires_minutes=custom_minutes)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin@example.com"
    assert payload["expires_in"] == custom_minutes * 60


def test_get_current_user_valid_token():
    token = create_access_token({"sub": "valid_user", "role": "HR"})
    payload = get_current_user(token)

    assert payload["sub"] == "valid_user"
    assert payload["role"] == "HR"


def test_get_current_user_expired_token():
    # Create an already expired token
    now = datetime.utcnow()
    past = now - timedelta(minutes=5)
    expired_token = jwt.encode(
        {"sub": "expired_user", "exp": past, "iat": past - timedelta(minutes=60)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(expired_token)
    assert exc_info.value.status_code == 401
    assert "Session expired" in exc_info.value.detail


def test_get_current_user_invalid_token():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user("invalid.jwt.token")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


def test_get_optional_current_user_none_or_empty():
    assert get_optional_current_user(None) is None
    assert get_optional_current_user("") is None


def test_get_optional_current_user_valid_header():
    token = create_access_token({"sub": "opt_user", "role": "CANDIDATE"})
    auth_header = f"Bearer {token}"
    payload = get_optional_current_user(auth_header)
    assert payload is not None
    assert payload["sub"] == "opt_user"
    assert payload["role"] == "CANDIDATE"


def test_get_optional_current_user_invalid_header():
    assert get_optional_current_user("Bearer malformed.token.value") is None
    assert get_optional_current_user("Basic invalid") is None


def test_require_role_authorized():
    role_checker = require_role("HR")
    user = {"sub": "123", "role": "HR"}
    result = role_checker(user=user)
    assert result == user


def test_require_role_forbidden():
    role_checker = require_role("ADMIN")
    user = {"sub": "123", "role": "CANDIDATE"}
    with pytest.raises(HTTPException) as exc_info:
        role_checker(user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden"


def test_require_role_missing_role():
    role_checker = require_role("ADMIN")
    user = {"sub": "123"}
    with pytest.raises(HTTPException) as exc_info:
        role_checker(user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Forbidden"
