# Draftwell

> An AI-powered writing assistant that helps users improve their drafts with feedback, rewrites, grammar checking, and paraphrasing.

## Status

🚀 **Full-stack MVP** — authenticated, all writing tools live, CI passing

## Features

- **Feedback** — submit a draft and receive structured AI feedback (clarity, tone, structure)
- **Rewrite** — streamed rewrite in 4 styles (formal, casual, persuasive, concise)
- **Grammar checker** — inline underlines by category (grammar, spelling, punctuation, style) with per-category scores; Accept/Ignore per issue
- **Paraphraser** — streamed rewrite in 5 modes (standard, simpler, shorter, academic, creative)
- **Auth** — register/login with JWT stored in an HttpOnly cookie; all documents are user-scoped
- **Document history** — saved drafts with embedded feedback, rewrites, grammar checks, and paraphrases

## Tech Stack

**Backend**
- Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL 16
- Anthropic Claude API (`claude-haiku-4-5-20251001`) for LLM inference
- PyJWT + bcrypt for auth · Pydantic for request/response validation

**Frontend**
- Next.js 16 · React 19 · TypeScript · Tailwind v4 · shadcn (base-ui/react)
- Playfair Display (serif) · Inter Tight (sans) · JetBrains Mono
- Vitest + React Testing Library for component tests

**Infrastructure**
- Docker (local Postgres) · GitHub Actions (CI/CD) · Railway (hosting — coming soon)

## CI

| Workflow | Trigger | Steps |
|---|---|---|
| Backend CI | `backend/**` changes | ruff lint → ruff format check → mypy strict → pytest (testcontainers Postgres 16) |
| Frontend CI | `frontend/**` changes | eslint → next build → vitest run |

## Local Development

```bash
git clone https://github.com/Bridev04/draftwell.git
cd draftwell
```

### Backend

```bash
cd backend
uv sync
cp ../.env.example .env   # fill in SECRET_KEY and ANTHROPIC_API_KEY

# Start Postgres
docker compose up -d

# Apply migrations
uv run alembic upgrade head

# Run the API server
uv run uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm ci
npm run dev   # http://localhost:3000
```

The frontend proxies `/api/*` → `http://localhost:8000` via Next.js rewrites, so the backend must be running.

### Running tests

```bash
# Backend (requires Docker for testcontainers)
cd backend
uv run pytest -v

# Frontend
cd frontend
npx vitest run
```

### Quality gates

```bash
cd backend
uv run ruff check .           # lint
uv run ruff format --check .  # format
uv run mypy app               # type-check (strict)
make ci                       # all three + tests
```

### Wipe and restart the DB

```bash
cd backend
docker compose down -v && docker compose up -d && uv run alembic upgrade head
```

## Environment Variables

Copy `.env.example` → `backend/.env` and set:

| Variable | Description |
|---|---|
| `DATABASE_URL` | asyncpg connection string |
| `DATABASE_URL_SYNC` | psycopg connection string (Alembic) |
| `SECRET_KEY` | random 32+ char string for JWT signing |
| `ANTHROPIC_API_KEY` | your Anthropic API key |
| `CORS_ALLOWED_ORIGINS` | comma-separated frontend origins (default: `http://localhost:3000`) |

## License

MIT — see [LICENSE](LICENSE)

## Author

Built by [Brian Ramos](https://github.com/Bridev04) as a portfolio project demonstrating production AI engineering practices.
