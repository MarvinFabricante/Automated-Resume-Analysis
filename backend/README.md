# Mariwasa Automated Resume Analysis — Backend (FastAPI & Celery)

The backend service is built with **FastAPI (Python 3.12)**, **SQLAlchemy 2.0 (Async)**, and **Celery**, backed by PostgreSQL, Redis, and a custom spaCy Natural Language Processing (NLP) resume extraction engine.

## Architecture & Project Structure

The project follows a modular, layered enterprise architecture (Controllers → Services → Repositories → Models):

```
backend/
├── main.py                     # Local development entrypoint runner
├── Dockerfile                  # Container build specification (Python 3.12-slim)
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, Celery, spaCy)
├── reset-db.sh                 # Database migration & seed script
└── app/
    ├── main.py                 # FastAPI application factory, middleware, & router setup
    ├── celery_app.py           # Celery distributed task queue configuration
    ├── tasks.py                # Asynchronous background tasks (AI parsing, notifications)
    ├── controllers/            # HTTP routers & route endpoints (Thin Controller pattern)
    ├── services/               # Core business logic & workflow orchestration
    ├── repositories/           # Database abstraction & SQLAlchemy async queries
    ├── models/                 # SQLAlchemy 2.0 ORM database models
    ├── schemas/                # Pydantic v2 schemas for request validation & response DTOs
    ├── extractors/             # Resume parsing engine & document extractors
    │   ├── content/            # Section extractors (education, skills, work experience)
    │   ├── file/               # File readers (PDF, DOCX, text)
    │   └── nlp/                # spaCy linguistic models, tokenization, & PhraseMatcher
    └── utils/                  # Shared helpers (DB session, auth, cache, rate limiter)
```

## Available Commands & Scripts

- `python main.py`: Starts the FastAPI development server with hot reload (port `8000`).
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`: Directly runs the Uvicorn ASGI server.
- `celery -A app.celery_app.celery_app worker --loglevel=info`: Starts the Celery background worker.
- `pytest`: Executes the automated test suite across controllers, services, and extractors.
- `bash reset-db.sh`: Reinitializes the database tables and runs schema migrations.

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (`postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>`).
- `REDIS_URL`: Redis connection string for task queue broker and response caching (`redis://<host>:6379/0`).
- `SECRET_KEY`: Cryptographic secret key used for signing JWT authentication tokens.
- `ALGORITHM`: JWT signing algorithm (default: `HS256`).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration window in minutes for access tokens (default: `30`).
- `FRONTEND_URL`: Comma-separated allowed origins for CORS policy configuration.
- `GEMINI_API_KEYS`: Comma-separated API keys for LLM evaluation and scoring rotation pool.
- `GOOGLE_CLIENT_ID`: OAuth 2.0 Client ID for Google Calendar interview scheduling.
- `GOOGLE_CLIENT_SECRET`: OAuth 2.0 Client Secret for Google Calendar integration.
- `SUPABASE_URL`: Supabase project URL for cloud document storage.
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role secret key for storage bucket uploads.
- `SUPABASE_BUCKET`: Storage bucket name for resume uploads (default: `resume storage`).
- `WEB_CONCURRENCY`: Number of Uvicorn worker processes in production (default: `4`).
- `CELERY_CONCURRENCY`: Number of concurrent worker threads for background task processing (default: `4`).