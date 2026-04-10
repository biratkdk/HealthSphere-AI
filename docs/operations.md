# Operations Guide

## Local workspace notes

- run commands from the project root
- use the repo venv for Python work:
  - POSIX shells: `source .venv/bin/activate`
  - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
- keep `.env` local and do not commit it
- use the architecture, deployment, and security guides for broader system context

## Service priorities

- keep authenticated operator workflows available
- keep report queue movement predictable and observable
- preserve inbox, alert, and audit consistency
- maintain storage and model artifact availability

## Daily checks

- review `/health/live` and `/health/ready`
- check queue depth and failed report jobs
- review unread notification growth and critical alerts
- inspect audit events after admin or identity changes
- confirm storage availability and model registry status

## Runtime indicators

Primary metrics:

- HTTP request count and latency
- in-flight request volume
- report job lifecycle events
- imaging analysis events by severity
- authentication events by provider
- notification creation rate

Operational views:

- dashboard queue summary
- population operations board
- imaging review workbench
- admin audit history
- notification inbox
- report workflow stage progression

## Common commands

Backend tests:

```bash
python -m pytest backend/tests -q
# or on Windows PowerShell without activating:
# .\.venv\Scripts\python.exe -m pytest backend/tests -q
```

Frontend build:

```bash
cd frontend
npm run build
```

Synthetic dataset refresh:

```bash
python scripts/generate_nepali_demo_assets.py
```

Smoke test:

```bash
python scripts/smoke_test.py --base-url http://localhost:8000 --username clinician --password ClinicianPass123!
```

## Queue operations

### Dispatcher mode

- report requests create queued jobs immediately
- an external scheduler, CI job, platform cron, or a manual trigger claims queued jobs
- jobs are retried with backoff until `JOB_MAX_ATTEMPTS` is reached
- workflow stage and progress fields are exposed to the frontend

### Celery mode

- queue work is pushed to Redis-backed workers
- Flower can be used for queue inspection

### Inline mode

- intended only for lightweight local validation
- request handling and report execution share the same process

## Failure triage

### Dashboard fails to load

- verify `/health/live`
- verify `/health/ready`
- confirm database reachability
- confirm the frontend points at the correct API base URL

### Reports stay queued

- confirm `TASK_EXECUTION_MODE`
- if dispatcher mode: invoke `POST /internal/jobs/dispatch` or verify the external scheduler or platform trigger
- if Celery mode: inspect Redis and worker health
- review report job `workflow_stage`, `attempt_count`, and `error`

### Live updates stop moving

- verify `GET /events/stream-token`
- confirm the browser event stream is reconnecting
- verify `REALTIME_STREAM_INTERVAL_SECONDS`
- inspect backend logs for stream token or auth errors

### Imaging uploads fail

- confirm file type and content type
- verify storage backend readiness
- verify object storage credentials or filesystem permissions

### OIDC sign-in fails

- verify provider metadata URL
- verify client ID and secret
- verify redirect URI alignment with frontend and backend domains

## Maintenance

Scheduled retention route:

- `POST /internal/maintenance/retention`

Expected cleanup tasks:

- notification pruning
- completed and failed report job pruning
- audit-log retention trimming

Keep `CRON_SECRET` configured so the maintenance endpoint cannot be invoked anonymously.
