# Architecture

## Boundaries

The browser calls versioned FastAPI routes. Routes authenticate, authorize, and validate transport input; services own bid/upload rules; SQLAlchemy persists metadata; `StorageProvider` owns content. Private storage paths are never returned as downloadable URLs. A download is permission checked and audited through the API. `DocumentIntelligenceProvider` is a dormant anti-corruption boundary for Phase 2.

## Data model

`User` ↔ `Role` supports global RBAC; `ProjectMembership` permits future project-scoped assignments. `BidProject` is the tender master. `BidDocument` holds classification/tags, SHA-256, source, revision/latest link state, and duplicate link. `AuditEvent` stores actor, action, target, request metadata and structured details. PostgreSQL is authoritative and Alembic owns schema evolution.

## Upload sequence

1. Validate role, batch count, safe basename, allowlisted extension, per-file and total bytes.
2. Hash bytes and query within the project for an active checksum.
3. Duplicate: persist a flagged metadata record linked to the original, but no second content blob.
4. New: generate an opaque UUID filename and save below the project root through the provider.
5. Persist metadata and audit event; return repository-safe metadata.

## Security evolution

Production adapters will verify Entra ID OIDC claims and MFA policy. Object providers will add envelope encryption/KMS, malware quarantine, DLP, retention and legal hold without changing bid services. Authorization will combine global capabilities and `ProjectMembership`. Ingress must enforce TLS, request limits, rate limits, security monitoring and private network policy.
