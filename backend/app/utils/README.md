# Utils (`app/utils`)

The `utils` directory provides **Cross-Cutting Infrastructure and Shared Helpers** used across the entire backend application, including database session management, caching, authentication security, and WebSockets.

## Architecture & Submodules

```
app/utils/
├── auth.py                 # Password hashing (bcrypt), JWT creation, and decode verification
├── cache.py                # In-memory and Redis response cache wrappers
├── database.py             # Async SQLAlchemy engine, session maker, and Base declarative class
├── google_auth.py          # Google OAuth 2.0 client credential helper
├── limiter.py              # Rate limiting middleware configuration (slowapi)
├── supabase_storage.py     # Supabase Storage bucket upload and URL retrieval client
└── websocket_manager.py    # Unified multi-client WebSocket & Pub/Sub manager
```

## Responsibilities

- **Database Session Life Cycle**: Provide `get_db()` async generator for dependency injection into FastAPI routes.
- **Security & Cryptography**: Provide bcrypt password hashing/verification and JWT token decoding.
- **Rate Limiting**: Defend endpoints against brute-force or abuse using `slowapi`.
- **Real-Time Communication**: Manage connected WebSocket client sessions and user-targeted notifications.
- **Cloud Storage Integration**: Upload and sign resume file URLs via Supabase Storage.

## Best Practices & Prohibitions

- **No Domain Logic**: Utilities must remain domain-agnostic. Business rules such as match scoring belong in `services/`.
- **Avoid Circular Imports**: Do not import from `services/` or `controllers/` within `utils/`.

## Developer Guidelines & Example

```python
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashes a plaintext password securely using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, secret_key: str, expires_delta: timedelta) -> str:
    """Encodes a JWT payload with an expiration timestamp."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret_key, algorithm="HS256")
```
