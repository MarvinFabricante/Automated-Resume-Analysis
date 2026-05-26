# Repositories (`/backend/app/repositories`)

## Overview
The `repositories` directory implements the **Repository Pattern**. It abstracts the data layer, providing a collection-like interface for accessing and manipulating database records. 

## Responsibilities
- **Database Abstraction**: Centralize all SQLAlchemy ORM operations (`select`, `insert`, `update`, `delete`).
- **Raw SQL execution**: If complex raw SQL is necessary, it must be encapsulated here.
- **Transaction Scoping**: Provide methods that accept an `AsyncSession` so the caller (Service) can control the database transaction commit/rollback lifecycle.

## What NOT to do here
- **NO Business Logic**: A repository should only care about *how* to save or fetch data, not *why*. Never send emails, trigger notifications, or validate domain rules here.
- **NO HTTP or Schemas**: Do not return Pydantic schemas (DTOs). Return SQLAlchemy Model objects (`app/models/`) or scalar values.

## Developer Guidelines & Example
All repository methods should be `staticmethod`s or part of a singleton class. They should take `db: AsyncSession` as their first argument.

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from app.models.user import User

class UserRepository:
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Fetches a user by their exact email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()
        
    @staticmethod
    async def create_user(db: AsyncSession, user_data: dict) -> User:
        """Inserts a new user record."""
        new_user = User(**user_data)
        db.add(new_user)
        # Note: We usually flush/commit here, but it can also be handled 
        # by the Service layer if part of a larger transaction.
        await db.commit()
        await db.refresh(new_user)
        return new_user
```
