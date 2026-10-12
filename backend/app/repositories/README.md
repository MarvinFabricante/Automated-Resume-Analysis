# Repositories (`app/repositories`)

The `repositories` directory implements the **Repository Pattern**. It abstracts database access and queries behind clean, asynchronous interfaces for entities stored in PostgreSQL.

## Architecture & Submodules

```
app/repositories/
├── admin_repository.py             # Administrator querying and system statistics
├── audit_repository.py             # Audit trail persistence and filtering
├── auth_repository.py              # User lookup, credential queries, and password updates
├── candidate_repository.py         # Candidate profile data and resume associations
├── chat_repository.py              # Message storage and conversation threads
├── hr_repository.py                # HR staff queries and department metrics
├── interview_repository.py         # Interview schedule persistence and availability checks
├── job_application_repository.py   # Application records, stage updates, and ranking queries
├── job_description_repository.py   # Job posting CRUD and status filtering
├── notification_repository.py      # Real-time notification persistence and delivery tracking
├── resume_repository.py            # Resume metadata, parsed content, and vectors
└── system_config_repository.py     # Application configuration persistence
```

## Responsibilities

- **Data Access Abstraction**: Encapsulate all SQLAlchemy `select`, `insert`, `update`, and `delete` query logic.
- **Complex Query Construction**: Handle joins, window functions, and filters cleanly.
- **Transaction Scoping**: Receive an `AsyncSession` parameter from the caller, enabling the service layer to coordinate transactional boundaries.

## Best Practices & Prohibitions

- **No Business Logic**: Repositories must strictly query and persist data—no domain rule checks, emails, or scoring calculations.
- **Return Models or Scalars**: Repositories return ORM model instances or primitive scalar values, not HTTP or Pydantic DTOs.
- **Pure Asynchronous APIs**: All repository methods must be asynchronous (`async def`) and use `await db.execute(...)`.

## Developer Guidelines & Example

```python
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User

class UserRepository:
    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetch a user record by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, user_data: dict) -> User:
        """Persist a new user record."""
        user = User(**user_data)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user
```
