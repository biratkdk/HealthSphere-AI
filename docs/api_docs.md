# API Documentation

## Base URL patterns

- local runtime: `http://localhost:8000`
- versioned API prefix: `/api/v1`
- split deployment: frontend points directly at the backend domain

## Authentication model

Protected endpoints accept:

- secure session cookies from `POST /auth/token` or `POST /auth/signup`
- bearer tokens from `POST /auth/token`
- service automation through `x-api-key` on selected internal paths

Public endpoints:

- `GET /auth/providers`
- `POST /auth/token`
- `POST /auth/signup`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/oidc/login`
- `GET /auth/oidc/callback`
- `GET /auth/oauth/{provider}/login`
- `GET /auth/oauth/{provider}/callback`
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`
- `GET /events/operations?stream_token=...`
## Authentication endpoints

- `GET /auth/providers`
  Returns the interactive access methods available in the current deployment.

- `POST /auth/token`
  Username and password exchange. Returns bearer token, expiry, user profile, and sets secure session cookies.

- `POST /auth/signup`
  Creates a local clinician account and immediately returns an authenticated session.

- `POST /auth/refresh`
  Rotates the refresh token, issues a new access token, and refreshes secure session cookies.

- `POST /auth/logout`
  Revokes the current session and clears secure session cookies.

- `GET /auth/oidc/login`
  Starts the Google redirect flow when Google sign-in is enabled.

- `GET /auth/oidc/callback`
  Completes the Google exchange, sets secure session cookies on the backend domain, and redirects to the frontend callback route.

- `GET /auth/oauth/{provider}/login`
  Starts a provider-specific redirect flow for configured providers such as Facebook.

- `GET /auth/oauth/{provider}/callback`
  Completes the provider-specific exchange, sets secure session cookies on the backend domain, and redirects to the frontend callback route.

- `GET /auth/me`
  Returns the current user profile.

- `PATCH /auth/me`
  Updates editable profile fields and local-account password data.

- `GET /auth/sessions`
  Returns the current device/session inventory for the signed-in user.

- `POST /auth/sessions/{session_id}/revoke`
  Revokes one session.

- `POST /auth/sessions/revoke-all`
  Revokes every session for the signed-in user.

- `GET /events/stream-token`
  Returns a short-lived token for the live operations event stream.

## Health and observability

- `GET /health/live`
  Liveness probe.

- `GET /health/ready`
  Readiness probe including database, model, storage, queue mode, auth, and live-update capability data.

- `GET /metrics`
  Prometheus-compatible metrics surface.

- `GET /events/operations?stream_token=...`
  Server-sent event stream containing queue, alert, and notification snapshots.
  Optional `once=true` returns a single snapshot event and closes the stream.

## Patient and prediction routes

- `GET /patients`
- `GET /patients?query=...`
- `GET /patients/{patient_id}`
- `GET /patients/{patient_id}/summary`
- `GET /patients/{patient_id}/timeline`
- `GET /patients/{patient_id}/tasks`
- `POST /patients/{patient_id}/tasks`
- `PATCH /patients/{patient_id}/tasks/{task_id}`
- `GET /patients/{patient_id}/handoffs`
- `POST /patients/{patient_id}/handoffs`
- `GET /patients/{patient_id}/imaging/studies`
- `GET /predict/icu/{patient_id}`
- `GET /predict/disease/{patient_id}`
- `GET /predict/treatment/{patient_id}`

Summary payloads include:

- patient record
- ICU deterioration response
- disease risk response
- treatment recommendation
- open alerts
- care tasks
- recent handoff notes

## Imaging routes

- `POST /analyze/imaging`
  Multipart upload. Requires `patient_id` as a form field.

- `GET /imaging/studies/{study_id}/content`
  Downloads stored imaging content.

Imaging response fields:

- `result`
- `confidence`
- `anomaly_score`
- `suggested_next_step`
- `study_reference`
- `stored_uri`

## Operations routes

- `GET /alerts`
- `GET /analytics/overview`
- `GET /notifications`
- `POST /notifications/{notification_id}/read`

`GET /analytics/overview` includes:

- patient totals
- alert counts
- unread notification count
- queue summary
- care-unit summary
- platform capability summary

## Report routes

- `POST /reports/patient/{patient_id}`
  Creates a queued report job.

- `GET /reports/jobs`
  Returns recent report jobs with workflow stage, progress, attempts, and delivery state.

- `GET /reports/jobs/{job_id}`
  Returns the current job record.

- `GET /reports/jobs/{job_id}/artifact`
  Returns the generated report JSON artifact when available.

Report job fields include:

- `status`
- `workflow_stage`
- `progress_percent`
- `attempt_count`
- `max_attempts`
- `next_attempt_at`
- `lease_expires_at`
- `worker_id`
- `delivery_status`

## Model and governance routes

- `GET /models/registry`
  Returns model metadata, validation state, owner, monitoring tags, artifact availability, and serving mode.

- `GET /admin/audit-logs`
  Returns recent audit records. Admin role required.

- `GET /admin/users`
  Returns the organization user directory. Admin role required.

- `PATCH /admin/users/{username}/status`
  Activates or deactivates a user account within the current organization. Admin role required.

- `PATCH /admin/users/{username}/role`
  Updates a user role within the current organization. Admin role required.

- `GET /admin/invites`
  Returns recent invite codes. Admin role required.

- `POST /admin/invites`
  Creates an invite code for clinician or analyst onboarding. Admin role required.

## Protected internal operations routes

- `POST /internal/jobs/dispatch`
  Triggers one dispatcher cycle. Requires `CRON_SECRET` bearer token or `x-api-key`.

- `POST /internal/maintenance/retention`
  Runs notification, report-job, and audit-log retention tasks. Requires `CRON_SECRET` bearer token or `x-api-key`.

## Common error responses

- `401` missing or invalid credentials
- `403` authenticated caller lacks the required role
- `404` missing patient, notification, job, or study
- `422` invalid payload, form field, or query parameter
