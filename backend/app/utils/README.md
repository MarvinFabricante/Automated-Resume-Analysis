# Utils (`/backend/app/utils`)

## Overview
The `utils` directory is the home for **Cross-Cutting Concerns and Shared Helpers**. These are modular, generic functions that are utilized across controllers, services, and repositories.

## Responsibilities
- **Core Infrastructure**: Database connection engines, in-memory caching, and Base declarative mapping.
- **Security & Auth**: JWT generation, password hashing (`bcrypt`), and token decoding.
- **Helper Functions**: Date formatters, math calculators, or generic string manipulation that isn't domain-specific.

## What NOT to do here
- **NO Domain Logic**: Do not place application-specific rules here. If a function is called `calculate_candidate_match_score()`, it belongs in a Service, not a util. 
- **NO Circular Imports**: Because utils are used everywhere, they should rarely import from `services/` or `controllers/` to prevent circular dependency crashes.

## Developer Guidelines & Example
Keep utility functions small, pure (if possible), and highly generic.

```python
# app/utils/auth.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hashes a plain text password securely."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain text password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)
```
