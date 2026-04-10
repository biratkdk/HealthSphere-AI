# HealthSphere AI Memory

## Durable Facts

- Workspace path: `D:\HealthSphere AI`
- Current folder is the git repository root.
- Backend app entrypoint is `backend.main:app`.
- Repo-root `app.py` and `api/index.py` both import and expose the same backend app.
- Frontend lives in `frontend/` and uses Vite, React, React Router, SWR, and Axios.
- Backend is FastAPI with SQLAlchemy, Alembic, Celery, Redis, Authlib, Prometheus, and optional OTLP.

## Verified On 2026-04-10

- `.\.venv\Scripts\python.exe -m pytest backend/tests -q` -> passed, 31 tests
- `npm run build` in `frontend/` -> passed
- system Python does not have repo dependencies installed
- `.env` exists locally and should not be printed or committed
- model runtime registry shows all four packaged artifacts loading successfully

## Project Layout Memory

- `backend/` = API, auth, DB, services, workers, tests
- `frontend/` = operator console
- `ml_pipeline/` = training, models, notebooks, sample data
- `airflow/` = DAGs
- `deployment/` = Docker, NGINX, Kubernetes, Terraform
- `docs/` = architecture, API, deployment, operations, security, runbooks
- `scripts/` = smoke test, PDF render, demo-data generation

## Runtime Memory

- API prefix for the frontend is `/api/v1`
- `legacy_routes_enabled` is enabled by default, so many backend routes also exist at root paths
- auth is cookie-backed with refresh support plus bearer token support
- session records are stored in `user_sessions`
- SSE live updates require a short-lived stream token first
- report jobs support `dispatcher`, `inline`, and `celery`
- default local task mode in `.env.example` is `dispatcher`
- storage backend resolves to local unless Blob token is present or storage is explicitly set to Blob

## Tenant And Data Memory

- tenant-aware reads and writes primarily live in `backend/app/db/enterprise_repository.py`
- shared or legacy repository logic still exists in `backend/app/db/repository.py`
- most user-facing flows should preserve `organization_id`
- seeded local demo data is attached to a default organization
- bootstrap users exist if the DB is empty

## Bootstrap User Memory

From `.env.example` defaults:

- admin / `AdminPass123!`
- clinician / `ClinicianPass123!`
- analyst / `AnalystPass123!`

These are acceptable only for local or demo use.

## Vercel Memory

- backend Vercel project metadata exists in `.vercel/project.json`
- frontend Vercel project metadata exists in `frontend/.vercel/project.json`
- backend and frontend are intended to be deployed as separate projects

## Infra Memory

- Docker Compose provisions PostgreSQL, Redis, backend, Celery worker, Flower, and frontend
- Kubernetes manifests define backend, worker, frontend, Redis, shared PVC, and HPAs
- Terraform provisions Azure resource group, ACR, storage, PostgreSQL Flexible Server, Redis, Log Analytics, and AKS

## Known Gotchas

- use `.venv` for Python commands
- the workspace currently contains generated state: `.db`, `storage/`, `frontend/dist/`, `frontend/node_modules/`
- frontend CI is weaker than backend CI
- no frontend test framework is present
- no explicit CSRF framework is present
- `_authorize_internal_request()` accepts a shorter cron-secret length than config guidance implies
- report completion currently performs a redundant "mark notified" write

## Important Files To Reopen First

- `README.md`
- `docs/architecture.md`
- `docs/api_docs.md`
- `backend/main.py`
- `backend/app/routes.py`
- `backend/app/core/config.py`
- `backend/app/db/enterprise_repository.py`
- `backend/app/tasks.py`
- `frontend/src/services/api.js`
- `frontend/src/context/AuthContext.js`

## When Modifying The System

- if you touch tenant-facing data access, inspect `enterprise_repository.py`
- if you touch report workflow, inspect both `tasks.py` and repository lifecycle helpers
- if you touch auth, inspect cookie behavior, refresh flow, and audit state
- if you touch live updates, remember the current SSE implementation re-queries DB state
- if you touch deployment, remember this repo supports Vercel, Compose, Kubernetes, and Terraform simultaneously
