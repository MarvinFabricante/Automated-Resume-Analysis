# Models (`/backend/app/models`)

## Overview
The `models` directory contains the **SQLAlchemy ORM Definitions**. These classes define the exact structure, constraints, and relationships of your relational database tables.

## Responsibilities
- **Table Schemas**: Define column names, data types (String, Integer, JSON), constraints (Nullable, Unique), and default values.
- **Relationships**: Define `relationship()` mappings for Foreign Keys to allow easy navigation between linked tables (e.g., `User.applications`).
- **Database Initialization**: These files are scanned by Alembic (or SQLAlchemy `create_all`) to generate the database schema.

## What NOT to do here
- **NO Pydantic Schemas**: Do not confuse ORM Models with Pydantic schemas. Pydantic schemas go in `schemas/`.
- **NO Database Queries**: Models should strictly be declarations. Do not write functions inside these files that execute queries.

## Developer Guidelines & Example
Models should inherit from the `Base` declarative class. Ensure you use `mapped_column` and typing correctly for modern SQLAlchemy 2.0.

```python
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.utils.database import Base

class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Foreign Key
    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    
    # Relationships
    author = relationship("User", back_populates="job_postings")
    applications = relationship("JobApplication", back_populates="job")
```
