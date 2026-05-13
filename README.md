# Draftwell

> An AI-powered writing assistant that helps users improve their drafts with feedback, rewrites, and tone analysis.

## Status

🚧 **In active development** — Phase 1: Backend foundation

## Features (Planned)

- ✍️ Submit drafts and receive AI-generated feedback (clarity, tone, structure)
- 🔁 Request rewrites in different styles (formal, casual, persuasive)
- 📚 Save documents with version history
- 🔐 User authentication with JWT
- 📊 Per-user usage tracking and cost monitoring
- ⚡ Streaming AI responses for low perceived latency

## Tech Stack

**Backend**
- Python 3.12 · FastAPI · SQLAlchemy · Alembic · PostgreSQL
- Anthropic Claude API for LLM inference
- Pydantic for request/response validation

**Frontend** *(coming soon)*
- Next.js 15 · TypeScript · Tailwind CSS

**Infrastructure**
- Docker · GitHub Actions (CI/CD) · Railway (hosting)

## Architecture

See [`docs/architecture.md`](docs/architecture.md) for the full system design *(coming soon)*.

## Local Development

```bash
# Clone and enter
git clone https://github.com/Bridev04/draftwell.git
cd draftwell

# Backend setup
cd backend
uv sync
cp ../.env.example .env  # then edit .env with your real keys

# Start Postgres
docker compose up -d

# Apply database migrations
uv run alembic upgrade head

# Run the API server
uv run uvicorn app.main:app --reload
```

### Running tests

```bash
cd backend

# Unit tests (no DB required)
uv run python -m pytest tests/ --ignore=tests/db -q

# Integration tests (requires Docker)
uv run python -m pytest tests/db -q

# Full suite
uv run python -m pytest -q
```

### Quality gates

```bash
cd backend
uv run python -m ruff check .        # lint
uv run python -m ruff format --check . # format
uv run python -m mypy app            # type-check
```

### Wipe and restart the DB

```bash
cd backend
docker compose down -v
docker compose up -d
uv run alembic upgrade head
```

## License

MIT — see [LICENSE](LICENSE)

## Author

Built by [Brian Ramos](https://github.com/Bridev04) as a portfolio project to demonstrate production AI engineering practices.