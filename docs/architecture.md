# Architecture

## Platform summary

HealthSphere AI is organized as a layered clinical operations platform with a web console, API tier, durable workflow execution path, ML serving layer, and operational control plane.

## Runtime layers

### Experience layer

- Vite-based React console
- SWR-driven data access
- route-level code splitting
- secure event-stream token exchange for live updates
- operator-facing pages for operations, patient review, reporting, inbox, profile, and audit review

### Identity and governance layer

- local signup and password login
- optional OIDC single sign-on
- JWT-based API access
- role enforcement for clinician, analyst, admin, and service actors
- audit logging of authenticated requests

### Service layer

- FastAPI routers for auth, health, patients, predictions, imaging, analytics, notifications, reports, models, and admin actions
- structured request logging
- Prometheus metrics and optional OTLP export
- security headers applied by middleware

### Workflow execution layer

Three execution modes are supported:

- `dispatcher`: queue-first report orchestration with persistent workflow state, stage tracking, retries, leases, and scheduled dispatch
- `celery`: Redis-backed asynchronous worker execution
- `inline`: direct execution for lightweight local environments

The durable path is centered on the `report_jobs` table rather than request-local state.

### Data and storage layer

- SQLAlchemy entity model for users, patients, labs, alerts, notifications, imaging studies, report jobs, and audit history
- Alembic migration history under `alembic/`
- local filesystem or Vercel Blob artifact storage
- generated report payloads retained in both relational state and object storage references

### Intelligence layer

- artifact-backed model runtime
- deterministic fallback heuristics for resilient startup and demo behavior
- notebook and training workspace under `ml_pipeline/`
- retraining helpers and Airflow orchestration for scheduled refresh flows

## Report workflow

1. The frontend submits `POST /reports/patient/{patient_id}`.
2. The backend creates a persistent `report_jobs` row with queue metadata.
3. A dispatcher cycle, Celery worker, or inline executor claims the job.
4. The job advances through explicit workflow stages:
   - `claiming`
   - `assembling_summary`
   - `rendering_artifact`
   - `persisting_artifact`
   - `notifying`
5. On success, the artifact payload is saved, the object is stored, and a notification is generated.
6. On failure, the job is either rescheduled with backoff or marked failed after the max-attempt threshold.

## Live update flow

1. An authenticated user requests `GET /events/stream-token`.
2. The backend issues a short-lived stream token separate from the main access token.
3. The frontend opens `GET /events/operations?stream_token=...`.
4. The backend emits server-sent events containing queue, alert, and inbox deltas.
5. The frontend merges the snapshot into SWR-managed state without page reloads.

## Persistence model

Primary tables:

- `users`
- `patients`
- `lab_results`
- `imaging_findings`
- `alerts`
- `notifications`
- `imaging_studies`
- `report_jobs`
- `audit_logs`

Notable `report_jobs` workflow fields:

- `workflow_stage`
- `progress_percent`
- `attempt_count`
- `max_attempts`
- `next_attempt_at`
- `lease_expires_at`
- `worker_id`

## Deployment topologies

### Local compose

- PostgreSQL
- Redis
- backend API
- Celery worker
- Flower
- frontend static delivery

### Split Vercel deployment

- backend deployed from repository root as Python serverless functions
- frontend deployed from `frontend/`
- managed PostgreSQL for transactional state
- Vercel Blob for artifact retention
- scheduled dispatcher and maintenance invocations through `vercel.json`

### Cluster deployment

- backend API deployment
- worker deployment
- Redis deployment
- frontend deployment
- ingress routing
- external object storage and database recommended for durable operation
