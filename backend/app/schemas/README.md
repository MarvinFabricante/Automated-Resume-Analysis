# Schemas (`app/schemas`)

The `schemas` directory defines **Pydantic v2 Models** (Data Transfer Objects / DTOs). They establish strict type validation and serialization contracts for all data crossing the API boundary.

## Architecture & Submodules

```
app/schemas/
├── admin_schema.py             # Admin analytics, audits, and management schemas
├── candidate_schema.py         # Candidate profile, education, and experience schemas
├── hr_schema.py                # HR profile, stats, and team schemas
├── interview_schema.py         # Interview scheduling, slot, and calendar schemas
├── job_application_schema.py   # Job application submission and status schemas
├── job_description_schema.py   # Job post creation, update, and search schemas
├── job_matching_schema.py      # Match breakdown, score vectors, and missing skills
├── message_schema.py           # Real-time chat message payloads
├── notification_schema.py      # In-app notification DTOs
├── resume_schema.py            # Resume upload responses and extracted entity schemas
├── system_config_schema.py     # Runtime configuration schemas
└── user_schema.py              # User authentication, token, and credential schemas
```

## Responsibilities

- **Request Validation**: Automatically validate incoming JSON payloads (types, regex formats, required fields, constraints).
- **Response Serialization**: Filter and shape data returned to clients (e.g. omitting password hashes and sensitive internal metadata).
- **Type Safety & OpenAPI**: Power FastAPI automatic interactive OpenAPI / Swagger documentation and IDE autocompletion.

## Best Practices & Prohibitions

- **No Database Logic**: Never import or invoke SQLAlchemy sessions or database queries inside schemas.
- **Separate Inbound and Outbound Schemas**: Keep `*Create`, `*Update`, and `*Response` schemas decoupled for clear security boundaries.
- **Pydantic v2 Standards**: Use `ConfigDict(from_attributes=True)` for parsing SQLAlchemy ORM entities.

## Developer Guidelines & Example

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# Base Schema (Common attributes)
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)

# Request Schema (Incoming registration payload)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# Response Schema (Outgoing serialized DTO)
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```
