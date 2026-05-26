# Services (`/backend/app/services`)

## Overview
The `services` directory contains the core **Business Logic** of the application. A Service acts as the brain of a specific domain (e.g., `JobMatchingService`, `AuthService`), orchestrating how data moves between the user, external APIs, and the database.

## Responsibilities
- **Enforcing Business Rules**: Applying validation rules, calculating scores, or deciding if a user has the right permissions to perform an action.
- **Workflow Orchestration**: Coordinating multiple actions, such as saving a user to the database, dispatching a welcome email, and logging an audit event.
- **External API Interaction**: Talking to LLMs (Gemini/Llama), Twilio, or Google Cloud services.
- **Delegating Data Access**: Calling methods from the `repositories/` layer to read or write database records.

## What NOT to do here
- **NO HTTP Logic**: Do not import FastAPI `Request`, `Response`, or `HTTPException`. Return raw data or raise standard Python `Exception`s, which the Controller will catch.
- **NO Direct Database Queries**: Avoid writing raw SQL or SQLAlchemy `select()` statements. Use `Repository` classes instead to keep logic decoupled.

## Developer Guidelines & Example
When adding a new feature, write the logic as an asynchronous method in a Service class. 

```python
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService

class UserService:
    async def process_user_registration(self, db: AsyncSession, email: str, raw_password: str):
        # 1. Enforce business rule
        if await UserRepository.get_user_by_email(db, email):
            raise ValueError("Email already registered.")
            
        # 2. Delegate to repository
        hashed_pw = self.hash_password(raw_password)
        new_user = await UserRepository.create_user(db, email, hashed_pw)
        
        # 3. Coordinate side-effects
        await EmailService.send_welcome_email(new_user.email)
        
        return new_user

user_service = UserService()
```
