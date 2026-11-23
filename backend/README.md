# Mariwasa Automated Resume Analysis — Backend (FastAPI & Celery)

The backend service is built with **FastAPI (Python 3.12)**, **SQLAlchemy 2.0 (Async)**, and **Celery**, backed by PostgreSQL, Redis, and a custom spaCy Natural Language Processing (NLP) resume extraction engine.

## Architecture & Project Structure

The project follows a modular, layered enterprise architecture (Controllers → Services → Repositories → Models):

```
backend/
├── main.py                     # Single unified FastAPI application & startup runner
├── Dockerfile                  # Container build specification (Python 3.12-slim)
├── requirements.txt            # Python dependencies (FastAPI, SQLAlchemy, Celery, spaCy)
├── reset-db.sh                 # Database migration & seed script
└── app/
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
- `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`: Directly runs the Uvicorn ASGI server.
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
- `SUPABASE_PROFILE_BUCKET`: Storage bucket name for profile images (default: `profile_images`).
- `SUPABASE_PROFILE_PATH`: Folder path inside the profile images bucket (default: `profiles`).
- `SUPABASE_RESUME_IMAGES_BUCKET`: Storage bucket name for extracted resume images (default: `resume_images`).
- `SUPABASE_RESUME_IMAGES_PATH`: Folder path inside the resume images bucket (default: `resumeimages`).
- `WEB_CONCURRENCY`: Number of Uvicorn worker processes in production (default: `4`).
- `CELERY_CONCURRENCY`: Number of concurrent worker threads for background task processing (default: `4`).

## Redis-First Architecture

To ensure high concurrency, ultra-low latency, and smooth application execution, all backend data operations and outside services use a **Redis-first pipeline**:

1. **Transaction Staging (Pre-commit)**:
   - When any mutation occurs (`create`, `update`, `delete`, or external call), the transaction is staged in Redis first with status `PENDING` via `RedisTransactionManager`.
   - The transaction details (`tx_id`, `target`, `action`, `payload`, `timestamp`) are stored in Redis hash `tx:<tx_id>` and added to `transactions:pending` and `transactions:recent`.
2. **Persistence to Source of Truth**:
   - The operation is executed against the persistent source of truth (PostgreSQL database, Supabase Storage, Gmail SMTP, Google Calendar).
3. **Commit & Cache Finalization**:
   - Upon successful execution, the Redis transaction is marked as `COMMITTED` with timestamp and result metadata.
   - If an error occurs, the transaction is marked as `FAILED` in Redis for auditing and recovery.
4. **Read-Through Caching**:
   - Database queries (`User`, `JobApplication`, `JobDescription`, `Resume`, `Interview`, `SystemConfig`, `AuditLog`) check Redis first before hitting PostgreSQL, eliminating database query bottlenecks.
5. **Outside Services Integration**:
   - **Supabase Storage**: Resume uploads are staged in Redis first; file downloads are served directly from Redis in-memory cache with 0ms network round-trip.
   - **Email Service**: Outgoing emails are recorded as transactions in Redis first and queued in `queue:outgoing_emails` before SMTP delivery.
   - **Google Calendar**: Calendar queries check Redis first; calendar mutations are staged in Redis first.
   - **Rate Limiting**: Backed by Redis distributed storage via Slowapi.
   - **Real-Time WebSockets**: Distributed cross-worker broadcasting using Redis Pub/Sub (`pubsub:ws_notifications`, `pubsub:ws_chat`, `pubsub:ws_status`).

## SMS verification

Interview scheduling, rescheduling, and cancellation send candidate SMS through
[iProgSMS v1](https://www.iprogsms.com/api/v1/documentation). Configure
`IPROG_SMS_API_TOKEN`, `IPROG_SMS_API_URL`, and `IPROG_SMS_PROVIDER` in the backend
environment. The application accepts Philippine mobile numbers in local, +63,
0063, and formatted resume notation. Invalid application numbers fall back to
candidate contact fields in the stored resume and profile. Missing recipients
and provider rejections appear as `SMS_FAILED` in interview logs.

Run from the repository root (use your Python environment):

```bash
.venv/bin/python backend/scripts/check_sms.py
.venv/bin/python backend/scripts/check_sms.py --phone YOUR_TEST_MOBILE
```

These checks do not send messages. To send one test SMS to a number you control,
add `--send-test` (uses SMS credits). Check an existing message without resending:

```bash
.venv/bin/python backend/scripts/check_sms.py --message-id YOUR_MESSAGE_ID
```

`SMS Queued` means the API accepted the message; it does not prove receipt on the
phone. Verify receipt with the test recipient. Smart/TNT requires an approved
custom sender name and a supported route confirmed by iProgSMS; a successful API
response alone cannot establish carrier support. Configure `IPROG_SMS_SENDER_NAME`
only after approval.
# Requirement confirmation and extraction fixes

Unconfirmed job requirements are returned as `Not confirmed` (or `Possible match`
when related evidence exists). Grouped clarification questions retain every item.
`clarification_responses` is an optional list of `{field, requirement, answer,
years?, details?}` objects; answers are `yes`, `some`, or `no`. Positive answers use
the regular scoring pipeline and retain `Confirmed by applicant` provenance.
Scores describe confirmed evidence coverage while unresolved items remain neutral.

Related terms can be edited in `app/services/requirement_related_terms.json`
(restart API and Celery workers after changing it), or overridden through the
matching configuration's `related_terms` mapping.

Startup adds the two nullable evidence columns automatically. For an explicit
deployment migration, run `python -m migrations.add_requirement_confirmations`
from `backend` before starting API and Celery processes. This migration does not
modify application statuses or existing records. Existing resumes can be
re-extracted through the existing upload flow to repair education/skill data.

