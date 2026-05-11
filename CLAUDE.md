# CLAUDE.md — Project Memory for Inkwell

This file is the source of truth for AI assistants working on this codebase.
When this project is opened in Claude Code (or similar AI coding tools), this file is read first.
Keep it updated as the project evolves.

## Project

**Name:** Inkwell  
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
   - [x] First commit + pushed to GitHub: https://github.com/Bridev04/inkwell
   - [x] `backend/` setup with uv + FastAPI
   - [x] Health check endpoint

### Up Next
- [ ] Tests: pytest harness + `tests/test_health.py`
- [ ] Ruff + mypy config
- [ ] Anthropic LLM service abstraction
- [ ] First feature endpoint: `POST /api/v1/feedback`
- [ ] PostgreSQL setup
- [ ] User model + JWT auth
- [ ] Frontend scaffold (Next.js)
- [ ] CI/CD with GitHub Actions
- [ ] Deployment (Railway)
