# HealthSphere AI Agent Guide

## Purpose

This file is for any human or AI agent entering the `D:\HealthSphere AI` workspace.
It explains how to work inside this project without breaking its runtime model,
tenant boundaries, auth flows, or report workflow.

## Project Mission

HealthSphere AI is a full-stack clinical operations platform with these core goals:

- provide a React operator console for patient review, alerts, notifications, reports, profile, and admin actions
- expose a FastAPI backend with auth, RBAC, audit logging, patient APIs, imaging analysis, analytics, and report orchestration
- persist operational state in SQLAlchemy-managed relational tables
- support queue-first report generation through dispatcher, Celery, or inline execution
- store imaging uploads and report artifacts through a pluggable local or Vercel Blob storage layer
- ship packaged ML artifacts with deterministic fallback logic for resilient runtime behavior

## Working Model

- Backend app entrypoint: `backend.main:app`
- Vercel entrypoints: `app.py` and `api/index.py`
- Frontend app: `frontend/`
- Primary tenant-aware data access layer: `backend/app/db/enterprise_repository.py`
- Legacy/shared data layer still present: `backend/app/db/repository.py`
- Report orchestration logic: `backend/app/tasks.py`
- Celery worker task: `backend/app/workers/report_tasks.py`
- Storage abstraction: `backend/app/services/storage.py`
- Model runtime: `backend/app/services/model_runtime.py`

## Current Verified State

Verified on 2026-04-10 in this workspace:

- backend tests pass with the repo venv: `.\.venv\Scripts\python.exe -m pytest backend/tests -q`
- frontend production build passes: `npm run build` in `frontend/`
- the folder is the project root and currently contains a real `.git` directory
- `.env` exists locally; treat it as secret-bearing runtime state and do not print or commit it
- packaged model artifacts load successfully in the current environment
- Vercel linkage exists for both backend root and frontend subproject

## Mandatory Operating Rules

### Environment

- Use the repo venv for Python commands. The system Python in this machine does not have the required packages.
- Create `.env` from `.env.example` before trying to run the stack manually.
- Do not assume SQLite settings are production-safe. Local defaults are for development only.

### Backend

- Prefer `enterprise_repository.py` for tenant-scoped reads and writes.
- Touch `repository.py` only when working on shared primitives, bootstrapping, report lifecycle internals, or old compatibility paths.
- Preserve the `organization_id` boundary whenever you add or change data access.
- Do not bypass upload validation for imaging. Keep `validate_imaging_upload()` in the request path.
- Preserve request audit logging behavior in `backend.main`.
- Keep `workflow_stage`, `attempt_count`, `lease_expires_at`, and `delivery_status` coherent for report jobs.

### Frontend

- The frontend assumes `/api/v1` as the API prefix.
- Auth is cookie-based with refresh support through Axios interceptors.
- Live updates are delivered through SSE and short-lived stream tokens.
- Do not add localStorage-based auth storage unless the security model is intentionally redesigned.

### Auth and Security

- Password login, signup, refresh, logout, and federated login all feed the same session and audit model.
- RBAC is enforced through `require_roles(...)`.
- Service-key and cron-secret access is intentionally narrow. Do not broaden internal route access casually.
- Be careful with `SameSite=None` production cookies. There is no explicit CSRF token framework in the current codebase.

### Deployment

- Backend and frontend are separate Vercel projects.
- Docker Compose is the main full local stack.
- Kubernetes and Terraform exist as production-style baselines, but they should be treated as templates that still need environment review.

## Verification Checklist

Run these before declaring backend or UI work done:

- `.\.venv\Scripts\python.exe -m pytest backend/tests -q`
- `npm run build` from `frontend/`
- if auth, reports, or imaging changed, also run `python scripts/smoke_test.py --base-url http://localhost:8000 --username clinician --password ClinicianPass123!`

## Known Weaknesses And Gaps

- The repo currently has two repository layers (`repository.py` and `enterprise_repository.py`), which increases maintenance cost and makes ownership less obvious.
- `legacy_routes_enabled` is on by default, so most routes exist both under `/api/v1` and root paths. This increases API surface area and compatibility debt.
- Frontend CI only builds. The workflow comment says lint and type-check, but there is no frontend lint step, no type-check step, and no frontend test suite.
- The frontend is plain JavaScript, not TypeScript, so UI contracts rely on runtime behavior rather than compile-time guarantees.
- The SSE live-feed model polls the database repeatedly for each connected client. This is workable for small to moderate operator counts but not efficient for high concurrency.
- The default local database is SQLite, which is not suitable for multi-instance or high-write production workloads.
- Local storage is not shared across instances. Shared deployments must use Blob or another shared artifact backend.
- Rate limiting can fall back from Redis to in-memory enforcement, which weakens global protection when Redis is unavailable.
- The project contains runtime-generated artifacts in the workspace: local DB files, storage files, `frontend/dist`, and `frontend/node_modules`.

## Observed Errors And Inconsistencies

- Running backend tests with the system Python fails because required packages are missing. Use `.venv`.
- `_authorize_internal_request()` accepts a cron secret with length `>= 16`, while config and docs describe a stronger `CRON_SECRET` expectation of 32 characters. The enforcement is inconsistent.
- `notify_report_ready()` marks a report as notified, and `execute_report_job()` also marks it notified after calling the notifier. The duplicated write is harmless but redundant.
- CI comments for the frontend overstate what the job actually validates.

## Scalability Assessment

What helps:

- queue-first report job model
- Celery mode for async execution
- Redis-backed rate limiting in shared environments
- Kubernetes manifests with HPA objects for backend, worker, and frontend
- split deployment support for backend and frontend
- storage abstraction that can move from local disk to Vercel Blob

What limits scale today:

- SSE snapshot generation is DB-driven and per-connection
- no published load test or concurrency benchmark
- no explicit caching layer for analytics or dashboard summaries
- no dedicated search index for patient lookup
- no background stream fanout layer
- no frontend e2e regression suite
- no explicit queue dead-letter policy beyond retry and failure status

Practical reading:

- good fit for local development, demos, internal pilots, and modest shared deployments
- not yet proven for enterprise hospital-scale traffic, strict compliance programs, or high-fanout real-time operations

## Pending Work

High priority:

- manage `.env` and other local-only runtime files without leaking secrets into version control
- keep git hygiene around local artifacts such as `.claude/`, generated PDFs, databases, and storage outputs
- consolidate `repository.py` vs `enterprise_repository.py`
- remove or intentionally retire legacy root-path routes if `/api/v1` is the contract
- add frontend linting, type-checking, and automated tests
- add load testing for SSE, report dispatch, and imaging upload paths

Security and governance:

- add explicit CSRF strategy for cookie-authenticated state-changing requests
- harden secret rotation and bootstrap-account handling for shared environments
- add malware scanning or stricter content inspection for uploaded imaging files
- define PHI, retention, and data-handling policy beyond code comments and basic retention routes

Scale and operability:

- move live operations updates to a more scalable fanout or cache-backed architecture
- add queue dashboards, failure alerts, and retry visibility outside app-level lists
- add dedicated observability dashboards and alerting rules
- validate multi-instance storage behavior in cluster and Vercel modes

Product and code quality:

- add browser-based integration tests for auth, reports, notifications, and admin flows
- add Celery and Redis integration tests
- add stronger migration validation against disposable PostgreSQL instances
- document ownership boundaries for backend, frontend, ML, and infra
