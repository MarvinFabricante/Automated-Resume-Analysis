# Schemas (`/backend/app/schemas`)

## Overview
The `schemas` directory contains **Pydantic Models** (Data Transfer Objects or DTOs). They act as a strict contract for data entering and leaving the API.

## Responsibilities
- **Request Validation**: Automatically validate incoming JSON body types, required fields, and constraints (e.g., email format, string length).
- **Response Serialization**: Filter and format the data returned to the client (e.g., hiding password hashes).
- **Type Hinting**: Provide strong typing for IDE autocompletion across the application.

## What NOT to do here
- **NO Database Logic**: Do not reference SQLAlchemy dependencies here.
- **Keep it Simple**: Avoid writing heavy processing functions inside Pydantic classes; stick to `@validator`s for strict data formatting.

## Developer Guidelines & Example
Always separate your Request (Create/Update) schemas from your Response schemas. Response schemas usually require `Config: from_attributes = True` to parse SQLAlchemy ORM objects.

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# 1. Base Schema (Shared fields)
class UserBase(BaseModel):
    email: EmailStr
    fullname: str

# 2. Request Schema (Incoming data)
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

# 3. Response Schema (Outgoing data)
class UserResponse(UserBase):
    id: int
    is_active: bool
    
    # Required for SQLAlchemy ORM translation
    class Config:
        from_attributes = True
```
