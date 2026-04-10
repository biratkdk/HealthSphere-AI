# Security Notes

## Current controls

- JWT-based bearer authentication for interactive API access
- local signup and password hashing with PBKDF2
- optional OIDC federation
- role-based authorization for clinician, analyst, admin, and service actors
- short-lived stream tokens for server-sent event access
- service-key authentication for automation paths
- `CRON_SECRET` support for scheduled internal routes
- audit logging with actor, role, path, entity context, and status code
- structured runtime logs with request IDs
- security headers applied by middleware
- object-storage abstraction for durable artifact retention

## Secret material

Treat these as required runtime secrets in shared environments:

- `DATABASE_URL`
- `SERVICE_API_KEY`
- `CRON_SECRET`
- `JWT_SECRET_KEY`
- `SESSION_SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `FACEBOOK_CLIENT_ID`
- `FACEBOOK_CLIENT_SECRET`
- legacy `OIDC_CLIENT_ID`
- legacy `OIDC_CLIENT_SECRET`
- `BLOB_READ_WRITE_TOKEN`

## Storage and data handling

- transactional clinical state lives in the relational store
- uploaded imaging studies and generated report artifacts use the configured storage backend
- report payloads are also retained in relational state for API continuity
- bundled demo data is synthetic and should remain separate from any live clinical source

## Operational security posture

- enable OIDC for shared deployments instead of relying on bootstrap local accounts
- replace default bootstrap passwords before exposing the product to multiple users
- route secrets through a managed secret store
- restrict admin and internal scheduled routes at the edge or network layer
- rotate service keys and JWT secrets on a schedule
- retain audit logs according to organizational policy

## Remaining external prerequisites

The repository supports:

- OIDC provider login
- durable PostgreSQL state
- object storage retention
- OTLP export

Those controls still depend on environment-specific credentials and infrastructure choices outside the source tree.
