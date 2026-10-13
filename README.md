# Automated Resume Analysis System

<p align="left">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=tailwind,typescript,nextjs,redux,py,fastapi,redis,postgres,supabase,nginx,cloudflare,docker,linux" />
  </a>
</p>

The **Automated Resume Analysis System** is an enterprise-grade recruitment ecosystem designed to streamline the hiring lifecycle for **Mariwasa Siam Ceramics Inc.** Leveraging Natural Language Processing (NLP), asynchronous task processing, and real-time synchronization, the system transforms unstructured resume documents into structured insights—enabling HR teams to screen talent with speed and precision.

---

## Core Ecosystem: The Three Portals

### 1. Candidate Portal
- **Smart Resume Upload**: Upload a resume directly without selecting a job; the system parses credentials and automatically recommends the best-matching open positions.
- **Job-Specific Application**: Drag-and-drop resume upload for specific roles with sub-second entity extraction.
- **Preview & Verification**: Review and adjust AI-extracted data (skills, experience, education) prior to final submission.
- **AI Match Scoring**: Instant transparency into candidate-job alignment and match percentages.
- **Application Tracking**: Real-time status progression (Submitted, Under Review, Shortlisted, Interview Scheduled, Accepted, Rejected).
- **Interactive Chat**: Direct messaging channel with HR recruiters.

### 2. HR Screening Portal
- **Recruitment Dashboard**: Real-time analytics on total applicant volume, hiring funnels, and department distribution.
- **Candidate Screening & Ranking**: High-fidelity interface displaying applicants sorted by AI Match Scores, skill overlap, and tenure.
- **Job Posting Management**: Full CRUD capabilities for job descriptions, qualification requirements, and archive states.
- **Deep Candidate Inspection**: Detailed inspection of matched vs. missing skills, relevant work history, and degree hierarchies.
- **Interview Scheduling**: Integrated calendar slot management and Google Calendar synchronization.
- **Real-Time Alerts**: Instant WebSocket alerts for incoming applications and candidate messages.

### 3. Admin Control Center
- **User & Role Management**: Centralized oversight of accounts, credentials, and role permissions (Admin, HR, Candidate).
- **Audit Logging**: Comprehensive security audit trail recording system events, logins, and profile modifications.
- **System Health & Config**: Live monitoring of service health, rate limit ceilings, and dynamic runtime configurations.

---

## AI Intelligence Layer

### Deterministic Resume Parsing Engine
Document ingestion processes PDF and DOCX files through a multi-stage deterministic pipeline without recurring LLM latency:
- **Document Preprocessing**: PyMuPDF and python-docx extract plain text, formatting boundaries, and section headers.
- **Named Entity Recognition (NER)**: Identifies contact details, candidate names, institutions, and dates.
- **spaCy PhraseMatcher**: Scans text against curated skill taxonomies and technical term dictionaries.
- **Contextual Classifiers**: Segments experience timelines, degree qualifications, and industry certifications.

### Multi-Factor Match Scoring Logic
Candidate profiles are evaluated against job requirements using an algorithmic scoring model:
1. **Skills Alignment (50%)**: Direct overlap between candidate technical/soft skills and required job competencies.
2. **Experience Relevance (30%)**: Evaluation of total years of experience and job title semantic alignment.
3. **Education Hierarchy (20%)**: Weighted scoring based on degree level (Doctorate > Master's > Bachelor's > Associate's).

---

## Technical Architecture

| Layer | Technologies |
|---|---|
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS v4, Redux Toolkit, Nginx |
| **Backend** | FastAPI (Python 3.12), SQLAlchemy 2.0 (Async), Pydantic v2, spaCy NLP |
| **Worker Queue** | Celery, Redis 7 (Alpine) |
| **Database** | PostgreSQL 16 (Alpine) with asyncpg connection pooling |
| **Storage & Network** | Supabase Storage (Resume cloud repository), Cloudflare Quick Tunnel |

---

## Architecture & Project Structure

```
automated_resume_analysis/
├── start.sh                    # Orchestration script for containers & Cloudflare tunnel
├── docker-compose.yml          # Container configuration for full application stack
├── .env                        # Central environment configuration
├── backend/                    # FastAPI & Celery backend application
│   ├── main.py                 # Local dev entrypoint runner
│   ├── Dockerfile              # Python 3.12 production container
│   ├── requirements.txt        # Backend dependencies
│   ├── reset-db.sh             # Database migration and seed script
│   └── app/
│       ├── main.py             # FastAPI factory, middleware, and route mounting
│       ├── celery_app.py       # Celery task queue initialization
│       ├── tasks.py            # Celery background workers (AI processing)
│       ├── controllers/        # Thin HTTP routers (Admin, Auth, HR, Candidate, Jobs)
│       ├── services/           # Core domain business logic & third-party integrations
│       ├── repositories/       # Asynchronous database access layer (SQLAlchemy 2.0)
│       ├── models/             # Relational ORM models (PostgreSQL)
│       ├── schemas/            # Pydantic v2 validation models & response DTOs
│       ├── extractors/         # Deterministic resume parsing & spaCy NLP engine
│       │   ├── content/        # Section parsers (skills, experience, education, contact)
│       │   ├── file/           # File format readers (PDF, DOCX, TXT)
│       │   └── nlp/            # spaCy singleton engine & PhraseMatcher pipeline
│       └── utils/              # Infrastructure helpers (auth, DB session, cache, WebSockets)
└── frontend/                   # Next.js 15 TypeScript frontend application
    ├── dev.mjs                 # Dev server runner with port and host flag handling
    ├── next.config.mjs         # Standalone configuration & reverse proxy API rewrites
    ├── postcss.config.mjs      # Tailwind CSS PostCSS plugin configuration
    ├── package.json            # Scripts & dependencies
    ├── tsconfig.json           # TypeScript configuration with path aliases (@/*)
    ├── public/                 # Static branding assets and illustrations
    └── src/
        ├── app/                # Next.js App Router route segments
        │   ├── layout.tsx      # Root application layout
        │   ├── providers.tsx   # Redux Toolkit, Toast, and Navigation providers
        │   ├── globals.css     # Global styles & Tailwind imports
        │   ├── (public)/       # Public routes (Landing, Careers, Smart Upload)
        │   ├── (auth)/         # Authentication routes (Login, Register, Password Reset)
        │   ├── admin/          # Admin portal routes
        │   ├── hr/             # HR screening and management portal routes
        │   └── candidate/      # Candidate portal routes
        ├── views/              # Page view implementations
        ├── components/         # Reusable UI component library
        ├── redux/              # Redux Toolkit state store & RTK Query slices
        ├── services/           # Axios HTTP clients and API services
        ├── types/              # TypeScript interfaces and type definitions
        └── utils/              # Navigation adapter, formatting, and file export helpers
```

---

## Quick Start: One-Click Application & Cloudflare Tunnel

To start the complete application ecosystem (PostgreSQL, Redis, FastAPI Backend, Celery AI Worker, Next.js Frontend, and Cloudflare Tunnel) with automatic environment synchronization:

```bash
./start.sh
```

### CLI Command Options

| Command | Description |
|---|---|
| `./start.sh` | Build & start all services, generate a live Cloudflare tunnel, and configure CORS |
| `./start.sh -q` or `--quick` | Fast start without rebuilding container images |
| `./start.sh -b` or `--rebuild` | Force a clean rebuild of all containers (`--no-cache`) |
| `./start.sh -r` or `--restart` | Restart all services and regenerate a fresh Cloudflare tunnel |
| `./start.sh -s` or `--stop` | Stop all running services gracefully |
| `./start.sh --status` | Check container health and verify live Cloudflare tunnel status |
| `./start.sh --logs [service]` | Stream service logs (e.g. `./start.sh --logs backend` or all) |
| `./start.sh --seed` | Seed default Mariwasa job openings and HR staff accounts |

---

## Environment Variables

Key parameters defined in `.env`:

- `DATABASE_URL`: Asynchronous PostgreSQL connection string.
- `REDIS_URL`: Redis broker and caching URI.
- `SECRET_KEY`: Cryptographic signing secret for JWT tokens.
- `FRONTEND_URL`: Permitted origins for backend CORS middleware.
- `GEMINI_API_KEYS`: Comma-separated API keys for LLM candidate evaluation rotation pool.
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: Google Calendar OAuth 2.0 credentials for interview booking.
- `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY`: Supabase Storage credentials for resume persistence.
- `NEXT_PUBLIC_API_URL`: Frontend API base path (defaults to `/api` in production).

---

© 2026 Mariwasa Siam Ceramics Inc. — STI CS Thesis Academic Project.
