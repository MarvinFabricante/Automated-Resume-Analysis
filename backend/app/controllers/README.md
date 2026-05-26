# Controllers Directory

This directory contains the API route handlers (endpoints) for the FastAPI application. 

**Purpose:**
- Define the REST API routes (e.g., `@router.get`, `@router.post`).
- Parse incoming HTTP requests (path parameters, query parameters, request bodies).
- Delegate complex business logic to the `services/` layer.
- Format and return standard HTTP responses and errors (e.g., `HTTPException`).

By keeping controllers "thin", the application remains modular, and the core business logic is easier to test independently.
