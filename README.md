# HealthSphere AI

HealthSphere AI is a full-stack clinical intelligence platform for patient risk review, imaging triage, report orchestration, care coordination, analytics, and governance. The repository is structured as a deployable product rather than a disconnected demo: the frontend, API, persistence layer, background execution path, ML artifacts, documentation, and delivery assets all ship together.

## What the product includes

- FastAPI service with typed contracts, secure session cookies, JWT-backed API tokens, role-based access control, optional single sign-on, audit logging, Prometheus metrics, and structured runtime logs
- Durable report workflow with queue-first job creation, staged execution state, retry handling, lease-based dispatcher claims, and Celery support for worker deployments
- Live operations feed built on secure stream tokens and server-sent events for queue and inbox refresh
- React operator console built with Vite, route-level code splitting, SWR data orchestration, patient directory search, collaboration workspaces, profile management, notifications, reports, and admin review
- Population Operations board for care-unit pressure, hottest-patient triage, overdue workflow, unresolved alerts, and imaging review demand
- Imaging review workbench with queue-first study handling, review states, escalation flow, and linked report creation
- Relational persistence for users, patients, labs, alerts, notifications, imaging studies, audit history, and report jobs
- Storage abstraction for uploaded studies and generated artifacts with local and Vercel Blob implementations
- ML workspace with notebooks, sample datasets, training scripts, model artifacts, retraining helpers, and Airflow DAGs
- Synthetic Nepali demo patients and imaging assets for local validation, UI walkthroughs, and upload testing

## Repository layout

```text
.
|-- backend/                # API service, auth, persistence, workers, tests
|-- frontend/               # Vite React operator console
|-- ml_pipeline/            # Raw data, external demo data, notebooks, training, artifacts
|-- airflow/                # Retraining and operations DAGs
|-- deployment/             # Docker, Kubernetes, Terraform, NGINX config
|-- docs/                   # Architecture, API, deployment, operations, security, runbooks
|-- scripts/                # Smoke tests and synthetic demo-data generation
|-- alembic/                # Migration history
|-- agent.md                # Working rules for humans and AI agents
|-- context.md              # Current architecture, risks, and project context
|-- memory.md               # Durable workspace facts and operational memory
|-- skills.md               # Skill map and contributor guidance
|-- todo.md                 # Premium roadmap and implementation backlog
|-- docker-compose.yml
|-- requirements.txt
`-- vercel.json
```

## Product architecture

1. The frontend loads authenticated workspace data through the FastAPI backend and keeps operational panels fresh through a live event stream.
2. The backend persists transactional state in SQLAlchemy-managed tables and exposes clinical, operational, and governance routes.
3. Report creation is queue-first. Jobs are claimed by either the built-in dispatcher, Celery workers, or inline execution for lightweight environments.
4. Imaging uploads and report artifacts are stored through a pluggable storage layer.
5. The ML runtime loads the packaged model artifacts directly and only falls back to governed deterministic scoring if an artifact cannot be loaded or executed safely.

Detailed design notes live in [architecture.md](d:/HealthSphere%20AI/docs/architecture.md).

## Quick start

### Backend

```bash
python -m venv .venv
source .venv/bin/activate   # POSIX shells
# or on Windows PowerShell:
# .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# or for the full local/dev stack with tests, workers, and optional ML extras:
# pip install -r requirements-dev.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Full local stack

```bash
docker compose up --build
```

The compose stack provisions PostgreSQL, Redis, the backend API, a Celery worker, Flower, and the frontend.

## Workspace notes

- this folder is the project root and currently contains a real `.git` directory
- a real `.env` may exist locally; do not print or commit its secrets
- prefer the repo venv for Python commands:
  - activated shell: `python ...`
  - direct invocation on Windows PowerShell: `.\.venv\Scripts\python.exe ...`
- Vercel backend deploys use the slimmer runtime `requirements.txt`; local development should prefer `requirements-dev.txt`
- this workspace may contain generated local state such as `.db` files, `storage/`, `frontend/dist/`, and `frontend/node_modules/`

## Configuration

Copy `.env.example` to `.env` and set at least:

- `DATABASE_URL`
- `SERVICE_API_KEY`
- `CRON_SECRET`
- `JWT_SECRET_KEY`
- `SESSION_SECRET_KEY`
- `FRONTEND_APP_URL`
- `ALLOWED_ORIGINS`
- `VITE_API_BASE_URL`

Important queue and runtime settings:

- `TASK_EXECUTION_MODE=dispatcher|celery|inline`
- `DISPATCHER_BATCH_SIZE`
- `JOB_LEASE_SECONDS`
- `JOB_MAX_ATTEMPTS`
- `JOB_RETRY_BACKOFF_SECONDS`
- `STREAM_TOKEN_EXPIRE_MINUTES`
- `REALTIME_STREAM_INTERVAL_SECONDS`

Optional platform settings:

- `GOOGLE_OAUTH_ENABLED`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_SERVER_METADATA_URL`
- `FACEBOOK_OAUTH_ENABLED`
- `FACEBOOK_CLIENT_ID`
- `FACEBOOK_CLIENT_SECRET`
- `AUTH_DEFAULT_ROLE`
- `AUTH_ADMIN_EMAILS`
- legacy `OIDC_*` values remain accepted for Google compatibility
- `BLOB_READ_WRITE_TOKEN`
- `OTLP_ENDPOINT`

## Authentication

Supported access paths:

- provider-first sign-in and sign-up with Google and Facebook entry points
- local username and password sign-in
- session-cookie auth with refresh, logout, and device-session revocation
- self-service signup for clinician accounts
- analyst access through admin-issued invite codes
- optional federated single sign-on with automatic account creation
- service-key automation through `x-api-key`
- internal scheduled maintenance and dispatcher calls secured through `CRON_SECRET`

Bootstrap users are created on first start if no users exist. Replace the default passwords before using a shared environment.

## Core workflows

### Operations

- Patient roster
- Risk and alert review
- Population Operations board
- Notification inbox
- Model registry visibility
- System capability summary

### Reports

- Queue-first report creation
- Workflow stage tracking
- Retry-aware durable execution
- Stored artifact download
- Delivery notification generation

### Imaging

- File upload
- Immediate analysis response
- Imaging review workbench
- Review-state updates with reviewer notes and escalation capture
- Stored study retrieval
- Notification creation after upload
- Patient-linked imaging submission with required patient association

### Profile and administration

- Self-service account creation
- Profile and preference editing
- Password update for local accounts
- Session inventory and revocation
- Admin user directory
- Admin user activation and role management
- Admin invite-code issuance for analyst onboarding
- Audit trail review for admins

## Synthetic demo data

The repository ships with synthetic Nepali patient records and imaging assets. Startup seeding imports the bundled patient pack so the dashboard has a richer working set out of the box:

- seeded application patients in [seed_data.py](d:/HealthSphere%20AI/backend/app/db/seed_data.py)
- external sample datasets in [nepali_synthetic_patients.json](d:/HealthSphere%20AI/ml_pipeline/data/external/nepali_synthetic_patients.json)
- flat CSV export in [nepali_synthetic_patients.csv](d:/HealthSphere%20AI/ml_pipeline/data/external/nepali_synthetic_patients.csv)
- upload-ready images listed in [nepali_demo_manifest.json](d:/HealthSphere%20AI/ml_pipeline/data/external/nepali_demo_manifest.json)

To regenerate the external demo pack:

```bash
python scripts/generate_nepali_demo_assets.py
```

## Deployment options

### Vercel

Use two projects:

- backend project rooted at the repository root
- frontend project rooted at `frontend/`

On the backend deployment:

- use managed PostgreSQL for `DATABASE_URL`
- use Vercel Blob through `BLOB_READ_WRITE_TOKEN` for durable object storage
- set `TASK_EXECUTION_MODE=dispatcher`
- set `CRON_SECRET` so scheduled dispatcher and maintenance routes are protected

On the frontend deployment:

- set `VITE_API_BASE_URL=https://<backend-domain>` for split-domain deployments
- leave `VITE_API_BASE_URL` empty only when the frontend is served behind a same-origin reverse proxy for `/api`

The backend exposes protected internal routes for queue dispatch and retention maintenance. Trigger them from an external scheduler, CI job, or a platform cron facility that supports your deployment tier.

### Docker and Kubernetes

Compose, Dockerfiles, and Kubernetes manifests are available under `deployment/`. Compose is best for local validation; Kubernetes and Terraform provide the infrastructure baseline for cluster deployments.

## Verification

Backend tests:

```bash
python -m pytest backend/tests -q
# or on Windows PowerShell without activating:
# .\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Frontend production build:

```bash
cd frontend
npm run build
```

Smoke test:

```bash
python scripts/smoke_test.py --base-url http://localhost:8000 --username clinician --password ClinicianPass123!
```

## Documentation index

- [Agent guide](d:/HealthSphere%20AI/agent.md)
- [Project context](d:/HealthSphere%20AI/context.md)
- [Project memory](d:/HealthSphere%20AI/memory.md)
- [Skills map](d:/HealthSphere%20AI/skills.md)
- [Premium todo](d:/HealthSphere%20AI/todo.md)
- [Architecture](d:/HealthSphere%20AI/docs/architecture.md)
- [API documentation](d:/HealthSphere%20AI/docs/api_docs.md)
- [Deployment guide](d:/HealthSphere%20AI/docs/deployment.md)
- [Operations guide](d:/HealthSphere%20AI/docs/operations.md)
- [Presentation audit](d:/HealthSphere%20AI/docs/presentation_audit.md)
- [Population and imaging sprint](d:/HealthSphere%20AI/docs/population_imaging_sprint.md)
- [Security notes](d:/HealthSphere%20AI/docs/security.md)
- [ML pipeline](d:/HealthSphere%20AI/docs/ml_pipeline.md)
- [User manual](d:/HealthSphere%20AI/docs/user_manual.md)
- [Incident runbook](d:/HealthSphere%20AI/docs/runbooks/incident-response.md)
- [Model rollback runbook](d:/HealthSphere%20AI/docs/runbooks/model-rollback.md)
