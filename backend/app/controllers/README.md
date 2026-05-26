# Controllers (`/backend/app/controllers`)

## Overview
The `controllers` directory acts as the entry point for all incoming HTTP requests to the FastAPI application. Controllers (often called "Routers" or "Views" in other frameworks) are responsible for handling routing, parsing input, and formatting output.

## Responsibilities
- **Routing**: Define HTTP methods (GET, POST, PUT, DELETE) and path endpoints.
- **Validation**: Accept request payloads validated by Pydantic schemas.
- **Dependency Injection**: Inject required dependencies such as Database sessions (`get_db`) and Authentication (`get_current_user`).
- **Delegation**: Call the appropriate method(s) from the `services/` layer to process the request.
- **Response**: Return standard HTTP responses and handle mapping service exceptions to `HTTPException`.

## What NOT to do here
- **NO Business Logic**: Do not write complex `if/else` workflows or data transformations here. If it involves domain rules, it belongs in a **Service**.
- **NO Database Queries**: Never import SQLAlchemy `select`, `insert`, etc. here. All database interactions must go through Services -> Repositories.

## Developer Guidelines & Example
When creating a new endpoint, follow the "Thin Controller, Fat Service" pattern:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.database import get_db
from app.utils.auth import get_current_user
from app.schemas.user_schema import UserResponse, UserCreate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])

@router.post("/", response_model=UserResponse)
async def create_user(
    request: UserCreate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Example of a thin controller. It relies entirely on `user_service`.
    """
    try:
        user = await user_service.create_user(db, request)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```
