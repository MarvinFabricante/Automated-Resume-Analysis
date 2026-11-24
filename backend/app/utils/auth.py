from datetime import datetime, timedelta
import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


def hash_password(password: str):
    safe_password = password[:72] if len(password) > 72 else password
    return pwd_context.hash(safe_password)

def verify_password(plain, hashed):
    if len(plain) > 72:
        plain = plain[:72]
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_minutes: int = None):
    if expires_minutes is None:
        expires_minutes = ACCESS_TOKEN_EXPIRE_MINUTES
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(minutes=expires_minutes)
    to_encode.update({
        "exp": expire,
        "iat": now,
        "expires_in": expires_minutes * 60
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def _validate_token_against_db(payload: dict, db: Optional[AsyncSession]) -> None:
    """
    Verify that the user behind a decoded JWT has not been deactivated, anonymized,
    or logged out everywhere (token_version bumped).
    """
    if db is None:
        return
    user_id = payload.get("id")
    if not user_id:
        return
    try:
        res = await db.execute(
            text(
                "SELECT is_deactivated, is_anonymized, token_version "
                "FROM users WHERE id = :uid"
            ),
            {"uid": int(user_id)},
        )
        row = res.fetchone()
    except Exception:
        return

    if not row:
        return

    is_deactivated = bool(row[0]) if row[0] is not None else False
    is_anonymized = bool(row[1]) if row[1] is not None else False
    db_tv = int(row[2] or 0)
    token_tv = payload.get("tv")

    if is_deactivated or is_anonymized:
        raise HTTPException(
            status_code=401,
            detail="This account has been deactivated. Please sign in or reactivate your account.",
        )

    if token_tv is not None and int(token_tv) != db_tv:
        raise HTTPException(
            status_code=401,
            detail="Session has been invalidated. Please sign in again.",
        )
    if token_tv is None and db_tv > 0:
        raise HTTPException(
            status_code=401,
            detail="Session has been invalidated. Please sign in again.",
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired: token has exceeded the 1-hour expiration window. Please sign in again.",
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    await _validate_token_against_db(payload, db)
    return payload


async def get_optional_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    if not authorization:
        return None
    try:
        token = authorization.replace("Bearer ", "").strip()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        await _validate_token_against_db(payload, db)
        return payload
    except Exception:
        return None


def require_role(required_role: str):
    def role_checker(user=Depends(get_current_user)):
        if user.get("role") != required_role:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return role_checker