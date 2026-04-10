# Deployment Guide

## Supported targets

- local developer runtime
- Docker Compose
- split Vercel deployment
- Kubernetes
- Terraform-backed infrastructure baseline

## Local development

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend defaults to `http://localhost:8000` for local development. For split frontend/backend deployments, set `VITE_API_BASE_URL` explicitly. For container and ingress deployments, prefer same-origin `/api` proxying.

## Full stack with Docker Compose

```bash
docker compose up --build
```

Compose provisions:

- PostgreSQL
- Redis
- FastAPI backend
- Celery worker
- Flower
- frontend served behind NGINX

The compose path sets:

- `TASK_EXECUTION_MODE=celery`
- Redis-backed asynchronous execution
- persistent Docker volume storage for artifacts

## Frontend container build

`deployment/Dockerfile.frontend`:

- builds the Vite application
- accepts `VITE_API_BASE_URL`
- serves the generated `dist/` bundle from NGINX

Recommended values:

- local compose: `/`
- ingress routing: `/api` through a reverse proxy

## Split deployment on Vercel

Use two projects:

- backend project rooted at the repository root
- frontend project rooted at `frontend/`

### Backend project

The root project contains:

- `app.py` as the Python entrypoint
- `.python-version`
- `.vercelignore`
- `vercel.json` for rewrites and function configuration

Recommended backend environment variables:

- `ENVIRONMENT=vercel`
- `DATABASE_URL=<managed-postgresql-url>`
- `STORAGE_BACKEND=auto`
- `BLOB_READ_WRITE_TOKEN=<vercel-blob-token>`
- `TASK_EXECUTION_MODE=dispatcher`
- `CRON_SECRET=<shared-secret-for-protected-internal-routes>`
- `JWT_SECRET_KEY`
- `SESSION_SECRET_KEY`
- `FRONTEND_APP_URL=https://<frontend-domain>`
- `ALLOWED_ORIGINS=https://<frontend-domain>`
- `ALLOWED_ORIGIN_REGEX=https://.*\\.vercel\\.app`
- `GOOGLE_OAUTH_ENABLED=true`
- `GOOGLE_CLIENT_ID=<google-client-id>`
- `GOOGLE_CLIENT_SECRET=<google-client-secret>`
- `FACEBOOK_OAUTH_ENABLED=true|false`
- `FACEBOOK_CLIENT_ID=<facebook-client-id>`
- `FACEBOOK_CLIENT_SECRET=<facebook-client-secret>`
- `AUTH_DEFAULT_ROLE=clinician`
- `AUTH_ADMIN_EMAILS=<comma-separated-admin-emails>`

Protected internal backend routes:

- `POST /internal/jobs/dispatch`
- `POST /internal/maintenance/retention`

### Frontend project

Required environment variable:

- `VITE_API_BASE_URL=https://<backend-domain>` for split-domain deployments

The `frontend/vercel.json` rewrite keeps client-side routes working on direct loads.

### Vercel runtime notes

- use managed PostgreSQL rather than SQLite for durable state
- use Vercel Blob for report and imaging artifact retention
- keep `TASK_EXECUTION_MODE=dispatcher` so queue work is not tied to a request lifecycle
- set `CRON_SECRET` so the protected internal routes are not publicly callable
- on tiers without committed cron support, invoke the protected internal routes from an external scheduler or CI workflow

## Kubernetes deployment

Apply manifests in this order:

1. create secrets for database URL, JWT secret, session secret, service key, and cron secret
2. apply `deployment/k8s/deployment.yaml`
3. apply `deployment/k8s/service.yaml`
4. apply `deployment/k8s/ingress.yaml`

Recommended production adjustments before applying to a shared cluster:

- provide a RWX storage class or object storage token for shared artifacts
- externalize PostgreSQL
- add HPA policies for backend and worker deployments
- route metrics to a central monitoring platform
- scope ingress and network policies for admin and metrics surfaces

## Terraform workflow

```bash
cd deployment/terraform
terraform init
terraform plan
terraform apply
```

The Terraform assets are a baseline. Review networking, cluster size, registry, and secret-handling assumptions before use in a shared environment.

## CI expectations

Current CI covers:

- backend dependency installation
- backend test suite
- frontend dependency installation through `npm ci`
- frontend production build with `VITE_API_BASE_URL`
- Kubernetes manifest linting
- Docker Compose validation
- Terraform formatting and validation

Recommended release gates:

- dependency audit
- migration validation against a disposable database
- image scanning
- post-deploy smoke tests

## Production hardening checklist

- replace bootstrap credentials or disable them entirely
- enable Google or other federated providers in shared environments
- route secrets through a managed secret store
- keep dispatcher and maintenance routes behind `CRON_SECRET`
- use managed PostgreSQL and object storage
- enable OTLP export or a central observability backend
- validate backup and restore procedures
