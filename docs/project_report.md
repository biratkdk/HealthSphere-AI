# Project Report

## Platform summary

HealthSphere AI is a cloud-ready clinical intelligence platform that combines patient review, predictive scoring, imaging triage, report generation, notifications, and operational oversight in a single product surface.

The repository is structured as a delivery-ready product rather than a prototype notebook bundle. It includes a secured API, a production-style frontend, model artifacts, workflow automation, deployment assets, and operations documentation.

## Product scope

Primary product capabilities:

- authenticated clinician, analyst, admin, and service access paths
- self-service local account signup with optional single sign-on integration
- patient command views with vitals, labs, imaging history, and risk signals
- report generation with queue state, retries, delivery tracking, and downloadable artifacts
- imaging upload analysis with stored study history
- notifications, audit review, and administrative oversight
- synthetic product-validation data for safe walkthroughs and UI checks

## Delivery architecture

The implementation is split across four major areas:

- `backend/`: FastAPI application, persistence layer, auth, reporting workflows, storage adapters, and observability hooks
- `frontend/`: Vite-based React operator console with route-level splits, SWR-backed data access, and live operations streaming
- `ml_pipeline/`: model training scripts, artifacts, notebooks, raw datasets, and synthetic validation packs
- `deployment/`: Docker, Kubernetes, Terraform, and Vercel deployment assets

The backend persists operational state in relational tables, exposes typed APIs, and supports multiple report-execution modes:

- dispatcher mode for built-in queued execution
- Celery mode for worker-backed execution
- inline mode for lightweight local validation

## Workflow coverage

The end-to-end operator workflow is supported in the product:

1. patient records are loaded into the dashboard from the API
2. users review current vitals, labs, imaging, and open alerts
3. prediction routes generate ICU, disease, and treatment outputs
4. report requests enter the queue and progress through visible workflow stages
5. generated artifacts are stored and linked back into the user workspace
6. notifications and audit events capture user and system activity

## Engineering posture

The codebase now reflects a more mature engineering baseline:

- Alembic-managed schema history
- JWT access tokens and role-based access control
- optional OIDC integration for managed sign-in
- structured logging and metrics endpoints
- live operations streaming for queue and alert refresh
- storage abstraction for local and object-backed artifacts
- queue state transitions with retries, leases, and retention maintenance
- automated backend tests and frontend production builds

## Data and model assets

The repository includes two complementary data layers:

- seeded application records used directly by the product UI
- external synthetic validation datasets stored under `ml_pipeline/data/external/`

The seeded workspace now imports the bundled synthetic patient pack during startup so the dashboard has a fuller working roster. The current synthetic dataset uses Nepali patient names and includes upload-ready imaging examples for repeated validation.

Model artifacts are loaded through the runtime catalog and surfaced through the registry endpoint with ownership, validation state, retraining timestamps, and serving metadata.

## Operations and governance

Operational support artifacts include:

- runbooks for deployment, security, and operations
- queue-dispatch and retention-maintenance endpoints for scheduled execution
- audit-log visibility for administrative review
- report workflow stage tracking for troubleshooting and support
- synthetic asset manifests for repeatable demo and regression checks

## Validation status

The repository has been validated through:

- backend endpoint tests
- frontend production builds
- seeded synthetic data regeneration
- live queue-state and artifact-path verification

This produces a coherent product baseline suitable for portfolio presentation, internal demos, staging environments, and further rollout hardening.

## External dependencies

Some enterprise capabilities remain environment-driven rather than hardcoded in the repository:

- managed identity provider credentials for single sign-on
- production database and object storage configuration
- infrastructure rollout into the target cloud environment
- long-horizon monitoring dashboards and alert routing outside the app itself

These are deployment concerns, not repository-structure gaps.
