# HealthSphere AI Context

## What This Project Is

HealthSphere AI is a deployable clinical intelligence application, not just a prototype notebook or isolated API.
It combines:

- a Vite + React operator console
- a FastAPI backend
- a relational persistence layer
- a report workflow engine
- an imaging upload and analysis flow
- ML artifacts and training assets
- deployment assets for Vercel, Docker Compose, Kubernetes, and Terraform

The project is oriented around patient review, care coordination, risk scoring, imaging triage, report generation, notifications, and admin governance.

## What Exists Today

### Frontend

The frontend lives in `frontend/` and provides:

- login and federated callback handling
- operations dashboard
- patients list and patient detail workflows
- reports workspace
- notifications inbox
- profile management
- admin screens
- live update integration through SSE

Key frontend files:

- `frontend/src/App.js`
- `frontend/src/context/AuthContext.js`
- `frontend/src/services/api.js`
- `frontend/src/hooks/useDashboardData.js`
- `frontend/src/hooks/useOperationsStream.js`

### Backend

The backend lives in `backend/` and provides:

- password login, signup, refresh, logout
- optional Google and Facebook sign-in flows
- session inventory and revocation
- patient roster, summary, timeline, tasks, handoffs, and imaging study retrieval
- ICU, disease, and treatment prediction endpoints
- imaging upload validation and analysis
- alerts, analytics, notifications, and live operations feed
- queue-first report generation and artifact download
- model registry visibility
- admin audit, user, and invite flows
- internal dispatch and retention routes

Key backend files:

- `backend/main.py`
- `backend/app/routes.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/db/enterprise_repository.py`
- `backend/app/db/repository.py`
- `backend/app/tasks.py`

### Data And ML

The data and ML workspace includes:

- relational entities for users, sessions, patients, labs, alerts, notifications, imaging studies, report jobs, invites, tasks, and audit logs
- synthetic Nepali patient data and sample imaging assets
- notebooks and training scripts under `ml_pipeline/`
- packaged model artifacts under `ml_pipeline/models/`

### Infra And Delivery

The repo also includes:

- `docker-compose.yml` for local full-stack execution
- Dockerfiles in `deployment/`
- Kubernetes manifests in `deployment/k8s/`
- Azure-oriented Terraform in `deployment/terraform/`
- Vercel configs at repo root and in `frontend/`
- CI in `.github/workflows/ci.yml`

## Architecture Summary

### Request Flow

1. The frontend authenticates a user against the FastAPI backend.
2. The backend issues an access token plus refresh cookie-backed session.
3. Frontend data fetching uses Axios and SWR against `/api/v1`.
4. Patient and operations views query tenant-scoped data.
5. Live updates are delivered through `GET /events/stream-token` and `GET /events/operations`.

### Report Flow

1. Frontend calls `POST /reports/patient/{patient_id}`.
2. Backend writes a `report_jobs` row immediately.
3. Execution is handled by dispatcher, Celery, or inline mode.
4. Workflow stages advance through claiming, summary assembly, artifact render, artifact persistence, and notification.
5. Artifact data is stored in relational state and optionally object storage.

### Imaging Flow

1. Frontend uploads an image or DICOM with a required `patient_id`.
2. Backend validates extension, content type, size, file structure, and decodability.
3. Model runtime performs imaging analysis.
4. Stored upload metadata is written to `imaging_studies`.
5. A notification is created for the submitting user.

### Auth And Governance Flow

- auth uses JWT access tokens, refresh cookies, and persisted session records
- route access is role-gated
- authenticated requests are audit-logged
- admin users can manage statuses, roles, and invite codes
- organization scoping is enforced mostly through `enterprise_repository.py`

## Current Workspace State

Observed on 2026-04-10:

- current folder: `D:\HealthSphere AI`
- this folder is the git repo root
- `.env` exists locally and should be treated as secret-bearing runtime state
- `.venv` exists and works
- backend tests pass with `.venv`: 31 tests
- frontend production build passes
- model registry shows all packaged artifacts loading successfully
- workspace includes generated artifacts and runtime state:
  - local `.db` files
  - `storage/` report and imaging outputs
  - `frontend/dist/`
  - `frontend/node_modules/`

## Strengths

- broad end-to-end scope for a single workspace
- auth, sessions, RBAC, audit logging, and admin flows are already implemented
- report generation is durable and queue-first rather than request-local only
- tenant-aware repository exists and is already used in most user-facing flows
- imaging upload validation is better than extension-only checking
- deployment story spans local, Vercel, containers, Kubernetes, and Terraform
- backend tests cover major functional paths
- frontend already has route-level code splitting and a decent service abstraction

## Weaknesses

- repository ownership is split between `repository.py` and `enterprise_repository.py`
- legacy and versioned routes coexist, which increases attack surface and maintenance burden
- frontend quality gates are weak compared with the backend
- no dedicated frontend test suite
- no TypeScript on the frontend
- real-time updates are implemented with repeated snapshot polling rather than event fanout
- default local seeding and bootstrap credentials are convenient but risky if not tightly controlled
- infra is ambitious, but some assets are still baseline templates rather than fully validated production modules

## Gaps

### Quality Gaps

- no frontend lint script
- no frontend type-check stage
- no browser e2e tests
- no load tests
- no chaos or failure-injection testing
- no explicit migration smoke test against disposable PostgreSQL in local workflow

### Security Gaps

- no explicit CSRF token mechanism for cookie-authenticated state-changing routes
- no malware scanning or quarantine workflow for uploaded files
- no evidence of secrets-management integration beyond env vars and secret refs
- no strong compliance story for PHI handling beyond general retention and audit support

### Product Gaps

- no clinician collaboration workflow beyond tasks, handoffs, and notifications
- no patient search index or advanced filtering beyond basic query support
- no external data ingestion pipeline from hospital systems
- no inference governance workflow beyond registry metadata and fallback notes

### Ops Gaps

- no published SLOs, SLIs, or alert thresholds
- no queue dead-letter handling beyond retries and terminal failure state
- no explicit cache strategy for dashboard summaries
- no formal incident automation beyond docs and protected maintenance endpoints

## Observed Errors And Inconsistencies

- `python -m pytest backend/tests -q` fails under the machine-wide Python because dependencies are not installed there. The correct command is through `.venv`.
- CI comments say the frontend job performs lint and type-check, but the workflow only installs dependencies and builds
- `_authorize_internal_request()` permits `CRON_SECRET` length `>= 16`, while config and docs imply a 32-character standard
- report notification state is written redundantly during report completion
- the workspace currently contains generated runtime assets that should not be treated as source of truth

## Scalability Posture

### What Scales Reasonably Well

- asynchronous report generation in Celery mode
- stateless frontend builds
- backend horizontal scaling when storage and DB are externalized
- Redis-backed rate limiting
- blob-backed storage
- Kubernetes deployment templates with HPA definitions

### What Does Not Scale Cleanly Yet

- per-client SSE polling against relational state
- analytics and dashboard queries without caching
- SQLite default mode
- local filesystem artifact storage across multiple replicas
- unknown performance under high imaging upload volume
- lack of frontend and infra regression automation

### Realistic Current Scale Envelope

This codebase is positioned for:

- local development
- demos
- internal pilots
- modest shared deployments with PostgreSQL, Redis, and Blob storage

It is not yet proven for:

- high-concurrency enterprise deployments
- large operator populations with many concurrent live streams
- strict regulated production environments that require stronger governance evidence
- large-scale imaging throughput or model-serving workloads

## Pending Work

### Immediate

- manage the real `.env` and other local runtime artifacts safely
- keep the repo clean around local-only files such as `.claude/`, generated PDFs, databases, and storage outputs
- clean or segregate generated runtime artifacts from source workflows

### Engineering

- consolidate or clearly separate `repository.py` and `enterprise_repository.py`
- decide whether root-path legacy routes should remain
- add frontend linting, tests, and stronger contract checks
- add integration tests for Celery and Redis-backed execution
- validate Terraform and Kubernetes in a real environment, not just syntax checks

### Security

- implement explicit CSRF protection strategy
- review cookie, CORS, and cross-origin behavior for split-domain deployments
- tighten internal route auth expectations to match config/documented secret strength
- add file scanning and storage governance for uploaded studies

### Scale

- redesign live operations updates for lower DB load
- add caching or denormalized views for analytics-heavy screens
- define benchmarks for report throughput and SSE concurrency
- add observability dashboards and alerts for queue depth, stream failures, auth failures, and storage health

### Product

- improve admin and care-team workflows beyond the current minimum viable set
- define model validation, drift detection, and retraining promotion policy
- add stronger documentation around data governance, deployment ownership, and environment promotion
