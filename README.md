# TrustAI

Web application that analyses CVs and job offers with AI, computes a compatibility score and explains it.

| Part | Stack |
| --- | --- |
| Frontend | React + Vite + TypeScript, Tailwind CSS, React Router, TanStack Query + Axios |
| Backend | Python 3.12, FastAPI, Pydantic, SQLAlchemy + Alembic |
| Database | PostgreSQL 16 |

## Project structure

```
backend/      FastAPI API (app/, alembic/, tests/)
frontend/     React application (src/)
docker-compose.yml
.env.example
```

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- API: http://localhost:8000/api (Swagger: http://localhost:8000/docs)
- PostgreSQL: localhost:5432 (`trustai` / `trustai`)

## Running without Docker

Start only the database: `docker compose up db`.

**Backend**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload
```

Lint / format / test: `ruff check .`, `black .`, `pytest`.

New migration after changing a model: `alembic revision --autogenerate -m "describe change"`.

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Lint / format / test: `npm run lint`, `npm run format`, `npm test`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branches, commits and pull requests.
