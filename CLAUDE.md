# CLAUDE.md — Project Memory for Draftwell

This file is the source of truth for AI assistants working on this codebase.
When this project is opened in Claude Code (or similar AI coding tools), this file is read first.
Keep it updated as the project evolves.

## Project

**Name:** Draftwell  
**Purpose:** AI-powered writing assistant. Users submit drafts, receive feedback, rewrites, and tone analysis. Authenticated, with per-user history.  
**Stage:** Phase 1 — Backend foundation  

## Tech Stack & Decisions

- **Language:** Python 3.12 (pinned via `.python-version`)
- **Package manager:** `uv` (NOT pip, NOT poetry)
- **Web framework:** FastAPI (async-first, type-validated, auto-generated OpenAPI docs)
- **Database:** PostgreSQL + SQLAlchemy 2.x (async) + Alembic migrations
- **LLM provider:** Anthropic Claude (provider-abstracted in `app/services/llm/`)
- **Default model:** `claude-haiku-4-5-20251001` (cheapest viable; configurable via env)
- **Auth:** JWT (planned, week 2)
- **Tests:** pytest + httpx for async API testing
- **Linting:** ruff (lint + format) + mypy (types)

## Architecture Principles

1. **Layered architecture:** `api → services → models/db`. Routes never query the DB directly; they call services.
2. **Pydantic at every boundary:** Every request/response is a Pydantic model. No raw dicts crossing the API surface.
3. **Provider-agnostic LLM layer:** All LLM calls go through `app/services/llm/client.py`. Swappable adapters per provider.
4. **Secrets via env only:** Never hardcoded. `app/config.py` is the only place env vars are read.
5. **Async by default:** All I/O (DB, HTTP, LLM) uses `async`/`await`.

## Folder Conventions (Backend)

backend/app/
├── api/         # FastAPI routers — thin, delegate to services
├── core/        # Cross-cutting: logging, security, middleware
├── db/          # Database session, base model, migrations
├── models/      # SQLAlchemy ORM models
├── schemas/     # Pydantic request/response schemas
├── services/    # Business logic — the heart of the app
└── config.py    # Single source for all settings

## Coding Style

- Type hints on every function signature.
- Docstrings on public functions explaining the *why*, not the *what*.
- No print statements; use the configured logger.
- Functions over classes when state isn't needed.
- One concept per commit; conventional-commit messages.

## Workflow

- Branch off `main` for every feature: `feat/<short-name>`
- Open PRs even for solo work — they document the change.
- CI must pass before merge (lint + tests).
- Squash-merge to keep `main` history clean.
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`, `ci:`.

## Current Status & TODOs

### Completed
   - [x] Dev environment: WSL2 + pyenv + Python 3.12 + uv + Node + VS Code+WSL
   - [x] Anthropic API key with spend limits configured
   - [x] Project scaffolding (folder, git init, branch=main)
   - [x] Foundational files: `.gitignore`, `README.md`, `CLAUDE.md`, `LICENSE`, `.env.example`
   - [x] First commit + pushed to GitHub: https://github.com/Bridev04/draftwell
   - [x] `backend/` setup with uv + FastAPI
   - [x] Health check endpoint (`GET /api/v1/health`)
   - [x] Test harness: pytest + httpx (ASGITransport)
   - [x] Quality gates: ruff (lint + format), mypy (strict), Makefile
   - [x] LLM service layer foundation: `LLMClient` Protocol, Pydantic schemas, `FakeLLMClient` for tests
   - [x] AnthropicClient: concrete LLMClient implementation wrapping the Anthropic SDK
   - [x] First feature endpoint: POST /api/v1/feedback (draft → structured AI feedback)
   - [x] Tests with mocked LLM client (no real API calls in CI)
   - [x] Structured per-request logging with key=value format
   - [x] Second feature endpoint: POST /api/v1/rewrites (streamed SSE)
   - [x] Streaming AI responses for low perceived latency
   - [x] PostgreSQL 16 via Docker Compose (`backend/docker-compose.yml`)
   - [x] Async SQLAlchemy 2.0 + asyncpg + Alembic migrations
   - [x] Three tables: `documents`, `feedbacks` (JSONB), `rewrites` (CHECK style constraint)
   - [x] Anonymous persistence layer: `save=true` flag on feedback + rewrites endpoints
   - [x] `document_id` returned in feedback response; `document` SSE event in rewrite stream
   - [x] `GET /api/v1/documents/{id}` — fetch saved doc with embedded feedbacks + rewrites
   - [x] Testcontainers-based integration tests with per-test transaction rollback
   - [x] `alembic/env.py` URL-precedence fix (caller-supplied URL wins over settings fallback)

### Up Next
- [ ] Frontend scaffold (Next.js)
- [ ] User model + JWT auth
- [ ] CI/CD with GitHub Actions
- [ ] Deployment (Railway)

## Local DB Setup

```bash
# Start Postgres (from backend/)
docker compose up -d

# Apply migrations
uv run alembic upgrade head

# Wipe and restart from scratch
docker compose down -v && docker compose up -d && uv run alembic upgrade head
```

The app reads `DATABASE_URL` (asyncpg) and `DATABASE_URL_SYNC` (psycopg) from `.env`.
Copy `.env.example` → `.env` and fill in your values. The docker-compose defaults match the example.
