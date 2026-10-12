# Models (`app/models`)

The `models` directory contains the **SQLAlchemy 2.0 ORM Declarations**. These classes define the database schema, table relationships, foreign key constraints, and column data types for PostgreSQL.

## Architecture & Submodules

```
app/models/
├── __init__.py                 # Export and metadata registration for Alembic
├── admin.py                    # Administrator profiles and permissions
├── audit_log.py                # Security audit trail and action logs
├── candidate.py                # Candidate demographic, contact, and profile models
├── hr.py                       # HR personnel profiles and organizational metadata
├── interview.py                # Interview schedules and Google Calendar synchronization
├── job_application.py          # Candidate applications, review status, and stages
├── job_description.py          # Job postings, required qualifications, and skills
├── message.py                  # Real-time chat messages between candidates and HR
├── notification.py             # User notification records and read states
├── password_reset.py           # Temporary tokens for password recovery flows
├── resume.py                   # Parsed resume records, skill vectors, and Supabase URLs
├── system_config.py            # Dynamic runtime parameters and feature flags
└── user.py                     # Unified user authentication entity and roles
```

## Responsibilities

- **Table Schemas**: Define column definitions, data types (e.g. `String`, `Integer`, `JSONB`, `Boolean`), constraints, and default values.
- **ORM Relationships**: Establish explicit bidirectional relationships (`relationship()`) between related entities.
- **Database Migrations**: Provide declarative targets for Alembic automatic revision generation.

## Best Practices & Prohibitions

- **No Business Logic**: Models should be purely declarative declarations. Do not write workflow methods inside model classes.
- **No Direct Queries**: Never execute queries inside model classes. Queries are strictly encapsulated in `repositories/`.
- **SQLAlchemy 2.0 Conventions**: Use modern `Mapped[...]` and `mapped_column()` annotations for full type safety.

## Developer Guidelines & Example

```python
from datetime import datetime
from sqlalchemy import Integer, String, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.utils.database import Base

class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Foreign Key
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    # Relationships
    author = relationship("User", back_populates="job_postings")
    applications = relationship("JobApplication", back_populates="job", cascade="all, delete-orphan")
```
