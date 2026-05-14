# Draftwell — Frontend

Next.js 16, React 19, Tailwind v4, shadcn/ui (base-ui/react primitives).

## Prerequisites

- Node.js 20+
- The backend running at `http://localhost:8000` (see `backend/` in the repo root)

## Setup

```bash
# from repo root
cd frontend

# install dependencies
npm install

# copy env template
cp .env.local.example .env.local
# edit .env.local if your backend is not on port 8000
```

## Run locally

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Available routes

| Route | Description |
|---|---|
| `/` | Submit a draft for feedback or a streaming rewrite |
| `/documents` | List of locally-saved document IDs (localStorage) |
| `/documents/[id]` | Fetch and display a saved document from the backend |

## Quality gates

```bash
npm run lint    # ESLint
npm run build   # TypeScript check + production build
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Draftwell backend base URL |
