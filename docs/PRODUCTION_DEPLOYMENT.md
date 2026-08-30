# Production Deployment and Operations Runbook

## Release gate

A release candidate is eligible for controlled deployment only when all three branch workflows are green:

- Internal CI
- Internal UAT
- Release Readiness

Release Readiness validates production configuration, database migrations and rollback/reapply, dependency audits, backend/frontend regression tests, PostgreSQL UAT, database backup/restore, production frontend build, Docker image builds, runtime container smoke tests and Docker Compose rendering.

A green release gate means the application build is internally deployable. It does not replace L&T cyber-security approval, penetration testing, infrastructure approval or enterprise identity-provider onboarding.

## Required enterprise inputs

L&T IT must provide or approve:

- production DNS and TLS termination
- PostgreSQL service and backup retention policy
- persistent document storage and backup policy
- production secret manager
- OIDC issuer, API audience, JWKS endpoint, SPA client ID and callback URL
- approved frontend/API origins
- network/firewall rules
- monitoring/log aggregation destination
- vulnerability/penetration assessment process

Never deploy with development_header authentication, localhost CORS, placeholder database credentials or the development secret.

## Deployment sequence

1. Create production PostgreSQL database and persistent document storage.
2. Load secrets/configuration from the approved secret manager using .env.production.example as the field reference.
3. Build backend and frontend images from the exact release commit.
4. Build the frontend with the approved NEXT_PUBLIC OIDC/API values.
5. Run database backup before any migration on an existing environment.
6. Apply `alembic upgrade head`.
7. Start backend and wait for `/api/v1/health/ready` to return ready.
8. Start frontend and verify HTTPS response plus OIDC redirect/callback.
9. Perform an authenticated smoke test with a provisioned non-admin user and an administrator.
10. Confirm audit events, document upload/download, decision analytics and submission workflows.
11. Record the release commit SHA and database migration revision.

The backend intentionally does not seed users or roles in production. Enterprise users must be provisioned through the approved onboarding process before OIDC identities can access the application.

## Health checks

- Liveness: `GET /api/v1/health/live`
- Readiness: `GET /api/v1/health/ready`

Readiness verifies both database connectivity and writable persistent storage. Do not route production traffic to an instance that is not ready.

## Backup and recovery

Before migrations and according to the enterprise backup schedule:

```bash
pg_dump --no-owner --no-privileges -h <host> -U <user> -d <database> > railway_bid_backup.sql
```

Restore into a separate recovery database first:

```bash
createdb -h <host> -U <user> railway_bid_restore
psql -h <host> -U <user> -d railway_bid_restore -v ON_ERROR_STOP=1 -f railway_bid_backup.sql
```

Verify `alembic_version`, critical table counts and representative bid/document records before declaring recovery successful. Document storage must be restored from its independent persistent-storage backup using the same recovery point whenever possible.

## Rollback

Application rollback:

1. Stop new traffic to the affected release.
2. Re-deploy the previously approved application image/commit.
3. Do not downgrade the database automatically unless the migration has been tested as reversible and no newer data depends on it.
4. For a required schema rollback, take a fresh backup and use the explicitly tested Alembic downgrade target.
5. Re-run readiness and authenticated smoke checks.

Migrations 0022 and 0023 are exercised by the automated release rollback/reapply smoke. Production rollback decisions still require assessment of live data created after deployment.

## Security operations

Production controls include OIDC bearer-token verification, RBAC/project membership checks, source-linked audit events, CSP, anti-framing, no-store responses, request IDs, upload validation, bounded parsing, non-root containers and dependency-audit release gates.

Operational teams should additionally centralize logs, monitor repeated authentication failures and rejected uploads, configure alerting for readiness failures, rotate secrets according to policy and retain audit data according to the approved records schedule.

## AI and data governance

Deterministic engines remain authoritative for calculations, readiness and decision scoring. Any external semantic/LLM provider must be explicitly approved before activation. Tender content must not be sent to an unapproved provider. Provider retention, no-training commitments, regional/data-residency requirements and access controls must be approved by L&T before enabling external AI.

## Release evidence to retain

Retain the release commit SHA, workflow run links/results, migration revision, dependency-audit results, database backup identifier, image digests, deployment date, environment configuration version (without secrets), cyber-security approval reference and production smoke-test record.
