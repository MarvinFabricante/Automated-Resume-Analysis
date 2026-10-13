# Services (`app/services`)

The `services` directory contains the core **Domain & Business Logic** of the application. Services act as the orchestrator for all application rules, coordinating transactions, external integrations, AI evaluations, and data access.

## Architecture & Submodules

```
app/services/
├── admin_service.py                # Admin user management and system metrics
├── ai_analysis_service.py          # AI resume deep analysis and strength/gap assessments
├── ai_caller_service.py            # AI automated phone screening caller integration
├── audit_service.py                # Security and operational audit log dispatch
├── auth_service.py                 # Authentication workflows, JWT creation, and password hashing
├── candidate_service.py            # Candidate profile management and application timelines
├── chat_service.py                 # Messaging channels, unread counts, and notifications
├── email_service.py                # Asynchronous transactional email dispatch
├── google_calendar_service.py      # Google Calendar OAuth 2.0 interview scheduling
├── hr_service.py                   # HR recruitment pipelines, candidate stage transitions
├── interview_service.py            # Interview coordination, status, and reminders
├── job_application_service.py      # Application lifecycle, duplicate checks, and status changes
├── job_description_service.py      # Job posting CRUD, activation, and archiving
├── job_matching_service.py         # Multi-factor candidate-job match score algorithm
├── notification_service.py         # Real-time WebSocket broadcasting and persistence
├── resume_service.py               # Resume upload, Supabase cloud sync, and extraction
└── system_config_service.py        # System flags, rate limiting rules, and settings
```

## Responsibilities

- **Enforce Business Invariants**: Validate domain constraints, check permissions, and calculate match scores.
- **Workflow Orchestration**: Coordinate multi-step workflows (e.g. upload resume → extract data → calculate match score → notify HR).
- **External API Integration**: Interact with Google Gemini, Google Calendar, Supabase Storage, and SMTP mail servers.
- **Data Access Delegation**: Call `repositories/` for all database reads and writes.

## Best Practices & Prohibitions

- **No HTTP Concerns**: Do not import `Request`, `Response`, or raise `HTTPException` inside services. Services should raise standard Python domain exceptions (`ValueError`, `PermissionError`), allowing controllers to map them to HTTP status codes.
- **No Direct Queries**: Avoid executing raw SQL or raw SQLAlchemy queries in services; delegate queries cleanly to `repositories/`.

## Developer Guidelines & Example

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.auth_repository import AuthRepository
from app.services.email_service import EmailService

class UserService:
    @staticmethod
    async def register_user(db: AsyncSession, email: str, password_hash: str) -> dict:
        # 1. Enforce domain constraint
        existing = await AuthRepository.get_by_email(db, email)
        if existing:
            raise ValueError("Email is already registered.")

        # 2. Delegate persistence
        user = await AuthRepository.create(db, {"email": email, "password_hash": password_hash})

        # 3. Trigger side-effects
        await EmailService.send_welcome_email(user.email)
        return user
```
