# Railway Bid Intelligence & Readiness System

A security-first enterprise workspace for railway bidding teams. **Phase 1** delivers bid-project creation, controlled bulk tender upload, checksum duplicate detection, a project document repository, development RBAC, and auditable events. It deliberately does not implement AI extraction or later bid workflows.

## Architecture and stack

- **Web:** Next.js 15, React 19, TypeScript, Tailwind; feature-oriented components and a typed REST client.
- **API:** FastAPI, Pydantic, service/domain separation, SQLAlchemy 2.
- **Data:** PostgreSQL 16 with Alembic migrations; tests alone use isolated in-memory SQLite.
- **Files:** private `StorageProvider` boundary with a traversal-safe local implementation. It can be replaced by S3, Azure Blob, private object, or on-prem storage.
- **Identity:** header-based development identity and global/project role schema, intentionally isolated for future Entra ID/SSO/MFA.
- **Intelligence:** provider-neutral interface only; Phase 2 is not implemented.

See [architecture](docs/architecture.md) and [roadmap](docs/roadmap.md).

## Quick start with Docker

```bash
cp .env.example .env                 # change all development credentials
# Requires Docker Engine with Compose v2
docker compose up --build
```

Open `http://localhost:3000`; API docs are at `http://localhost:8000/docs`. The backend waits for healthy PostgreSQL, migrates, seeds demo users, and starts. Verify with `curl http://localhost:8000/api/v1/health`.

## Local start

PostgreSQL remains the application database. Start a PostgreSQL 16 instance, copy `.env.example` to `.env`, and set `DATABASE_URL` (for a host-run API, use `localhost` rather than `db`).

```bash
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1 npm run dev
```

### Environment variables

`DATABASE_URL`, `SECRET_KEY`, `STORAGE_ROOT`, `MAX_FILE_SIZE_MB`, `MAX_BATCH_SIZE_MB`, `MAX_FILES_PER_BATCH`, and `NEXT_PUBLIC_API_URL` are documented in `.env.example`. Never commit `.env`. Upload policy is centralized in backend settings; the client mirrors the published development policy for immediate feedback, while the server remains authoritative.

### Migrations and seed data

Run `cd backend && alembic upgrade head`. Create future revisions with `alembic revision --autogenerate -m "description"`. `python -m app.seed` idempotently creates all eleven roles and admin/read-only demo identities. Development requests default to user 1; send `X-User-ID: 2` to demonstrate read-only denial.

## Phase 1 features

- Responsive enterprise dashboard, complete navigation, workflow indicator, and honest “Coming Soon” states.
- Validated, unique Bid ID master form and REST API.
- Multiple-file drag/drop, browse, queue/remove/retry, status/progress, limits, extension validation, secure randomized filenames, SHA-256 detection, and upload summary.
- Project repository metadata, filename search, protected API download, revisions/tags/category-ready schema.
- RBAC, project membership foundation, admin audit endpoint, structured logging, CORS and defensive response headers.

## Tests

```bash
cd backend && pytest -q
cd frontend && npm test
cd frontend && npm run build
```

## Security considerations and limitations

Assume TLS termination at the corporate ingress; do not expose the development services directly. No file has a public URL. This foundation prevents traversal, restricts types/sizes, randomizes stored names, records key events, and denies writes to read-only roles. Before production: replace development headers with verified SSO tokens, deploy secrets/key management, encryption at rest, malware scanning/quarantine, MIME signature inspection, DLP, MFA, rate limits, CSRF strategy if cookie auth is adopted, project membership enforcement on every endpoint, immutable audit export, backup/retention controls, and security review. Local storage writes each non-duplicate atomically enough for development but does not yet provide object locking or distributed transactions. Revision/reclassify/archive UI actions and full repository filters are schema/API roadmap work within Phase 1 hardening; AI and all advanced workflows remain intentionally absent.
