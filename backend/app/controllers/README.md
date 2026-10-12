# Controllers (`app/controllers`)

The `controllers` directory acts as the entry point for all incoming HTTP requests to the FastAPI application. Controllers define route mappings, accept validated request payloads, and delegate business execution to the service layer.

## Architecture & Submodules

```
app/controllers/
├── admin_controller.py             # System administrator endpoints and audit logs
├── auth_controller.py              # User authentication, registration, and JWT issuance
├── candidate_controller.py         # Candidate profile management and application history
├── chat_controller.py              # Real-time WebSocket and HTTP messaging
├── hr_controller.py                # HR recruitment workflows, analytics, and job postings
├── interview_controller.py         # Interview scheduling and Google Calendar sync
├── job_application_controller.py   # Application submission and status tracking
├── job_matching_controller.py      # Match score computation and ranking
├── notification_controller.py      # Notification retrieval and read-state management
├── resume_controller.py            # Resume parsing, upload, and data extraction
└── system_config_controller.py     # System-wide dynamic settings and flags
```

## Responsibilities

- **Routing**: Define HTTP methods (`GET`, `POST`, `PUT`, `DELETE`, `PATCH`) and endpoint paths.
- **Validation**: Accept request payloads validated by Pydantic schemas.
- **Dependency Injection**: Inject required dependencies such as Database sessions (`get_db`) and Authentication (`get_current_user`).
- **Delegation**: Call the appropriate methods from the `services/` layer to process requests.
- **Response**: Return standard HTTP responses and map service exceptions to `HTTPException`.

## Best Practices & Prohibitions

- **No Business Logic**: Keep controllers thin. Domain rules, calculations, and complex conditionals belong in `services/`.
- **No Direct Database Queries**: Never import or invoke SQLAlchemy queries (`select`, `insert`, `delete`) in controllers. All database interactions must go through Services → Repositories.

## Developer Guidelines & Example

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.schemas.user_schema import UserResponse, UserCreate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Example of a thin controller delegating execution to user_service.
    """
    try:
        user = await user_service.create_user(db, request)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```
