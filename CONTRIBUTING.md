# Contributing to TrustAI

## Branches

| Branch | Role |
| --- | --- |
| `main` | Stable code, protected. Only updated from `develop` through a pull request (end of sprint / demo). |
| `develop` | Integration branch. Every feature branch is merged here through a pull request. |
| `feature/<ticket>-<short-name>` | A user story, e.g. `feature/US03-cv-upload` |
| `fix/<ticket>-<short-name>` | A bug fix, e.g. `fix/US01-token-expiry` |
| `chore/<ticket>-<short-name>` | Setup / tooling / config, e.g. `chore/T-05-github-actions` |

Always branch from an up-to-date `develop`:

```bash
git checkout develop
git pull
git checkout -b feature/US03-cv-upload
```

## Commits

Short, imperative, prefixed with the ticket:

```
US03: validate file type and size on upload
T-02: add Alembic configuration
```

## Pull requests

- Target **`develop`** (never `main` directly).
- At least **1 approval** from another team member (cross review) before merging.
- Lint and tests must pass (GitHub Actions, T-05).
- Fill in the pull request template and link the Jira ticket.
- Prefer **squash merge** to keep the history readable, then delete the branch.

## Code style

- Backend: Ruff + Black (config in `backend/pyproject.toml`).
- Frontend: ESLint + Prettier (config in `frontend/`).
- Install the git hooks once so they run on every commit:

```bash
pip install pre-commit
pre-commit install
```
