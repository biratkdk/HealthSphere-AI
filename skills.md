# HealthSphere AI Skills Map

## What This Project Is Good At

- full-stack web application assembly
- FastAPI service design
- cookie and token-based auth flows
- role-based access control
- tenant-aware operational data access
- queue-first report workflow design
- imaging upload validation and lightweight inference integration
- deployment portability across local, Vercel, containers, Kubernetes, and Azure Terraform

## Core Skills Required To Work On This Project

### Backend API Skill

Needed for:

- FastAPI routes
- request validation
- auth and RBAC
- session and refresh flows
- SSE endpoints
- audit logging

Main files:

- `backend/main.py`
- `backend/app/routes.py`
- `backend/app/core/security.py`
- `backend/app/core/oidc.py`
- `backend/app/core/config.py`

### Data And Repository Skill

Needed for:

- SQLAlchemy entities
- tenant scoping
- seed data
- audit records
- report job persistence
- notifications, tasks, and handoffs

Main files:

- `backend/app/db/entities.py`
- `backend/app/db/enterprise_repository.py`
- `backend/app/db/repository.py`
- `backend/app/db/session.py`
- `alembic/`

### Frontend Product Skill

Needed for:

- React screens and routing
- auth state handling
- API integration
- SWR data flow
- SSE consumption
- operator dashboard UX

Main files:

- `frontend/src/App.js`
- `frontend/src/context/AuthContext.js`
- `frontend/src/services/api.js`
- `frontend/src/hooks/useDashboardData.js`
- `frontend/src/hooks/useOperationsStream.js`
- `frontend/src/pages/`
- `frontend/src/components/`

### Background Workflow Skill

Needed for:

- queue dispatch behavior
- retry and lease semantics
- Celery worker execution
- report artifact lifecycle

Main files:

- `backend/app/tasks.py`
- `backend/app/workers/report_tasks.py`
- `backend/app/workers/celery_app.py`
- `backend/app/services/reporting_service.py`

### ML Runtime Skill

Needed for:

- model artifact packaging
- fallback scoring logic
- imaging feature extraction
- prediction contract stability
- retraining handoff paths

Main files:

- `backend/app/services/model_runtime.py`
- `backend/app/ml_utils.py`
- `ml_pipeline/models/`
- `ml_pipeline/training/`
- `airflow/dags/`

### Storage And File Handling Skill

Needed for:

- local filesystem artifact storage
- Vercel Blob storage
- imaging upload validation
- artifact download behavior

Main files:

- `backend/app/services/storage.py`
- `backend/app/services/upload_guard.py`

### Infra And Delivery Skill

Needed for:

- local stack bring-up
- container images
- Vercel deployment
- Kubernetes rollout
- Azure infrastructure provisioning

Main files:

- `docker-compose.yml`
- `deployment/Dockerfile.backend`
- `deployment/Dockerfile.frontend`
- `deployment/k8s/`
- `deployment/terraform/`
- `vercel.json`
- `frontend/vercel.json`
- `.github/workflows/ci.yml`

## Task-To-Skill Routing

- New API endpoint -> backend API skill + data skill
- Auth or session changes -> backend API skill + security skill
- Tenant scoping bug -> data skill first, then route audit
- Dashboard or page changes -> frontend product skill
- Report stuck or retry behavior -> background workflow skill
- Imaging upload issue -> storage skill + ML runtime skill
- Blob or artifact path issue -> storage skill + deployment skill
- Production rollout issue -> infra and delivery skill
- Model registry or fallback issue -> ML runtime skill

## Current Skill Strengths In The Codebase

- backend functional coverage is much stronger than frontend coverage
- auth and governance concerns are already embedded in the API design
- deployment options are broad and practical
- code organization by domain is already decent at the top level

## Current Skill Gaps In The Codebase

- frontend testing skill is underrepresented
- frontend static analysis and type-safety skill is underrepresented
- performance and load-testing skill is not visible in the current repo
- formal security hardening skill is incomplete around CSRF and upload scanning
- data governance and compliance skill is not fully codified
- infra validation is present, but operational excellence skill still needs stronger dashboards, alerts, and scale validation

## Where The Project Needs Stronger Skills Next

- React testing and UI regression automation
- TypeScript migration or stronger frontend contract discipline
- Redis and Celery integration testing
- high-concurrency live-update architecture
- security review for cross-origin cookie flows
- PHI-safe storage and retention design
- model governance, drift monitoring, and release approval workflow
- production incident response automation

## Practical Advice For Contributors

- if the task touches organizations, roles, or shared data, think about tenant boundaries first
- if the task touches reports, think about retries, leases, idempotency, and artifact consistency
- if the task touches auth, think about cookies, refresh flow, RBAC, and audit logging together
- if the task touches real-time UI, think about DB load and SSE fanout cost
- if the task touches deployment, verify how the same change behaves in local, Vercel, and Kubernetes modes
