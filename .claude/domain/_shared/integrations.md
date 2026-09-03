# Integrations — _shared
Sources: README.md, docker-compose.yml, PRD, `backend/app/storage.py` (skimmed), FEAT-004 infra work · Last verified: 2026-09-03

| system | contract | auth | quirks | mock strategy |
|---|---|---|---|---|
| Supabase Postgres (prod) | SQLAlchemy via `DATABASE_URL` | connection string in `.env` | reachable ONLY via the explicit `prod` compose profile; `dev`/`test` are hardcoded to the local/ephemeral db (FEAT-004) | compose `db` service (postgres:16-alpine) |
| Supabase Storage | private bucket `employee-docs`, signed URLs | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | optional — disabled when unset; dev profile pins both to empty; legacy docs are still Google Drive URLs (`source_url`) | stub storage client / MinIO per infra_skills |
| Legacy Google Form xlsx | `backend/import_legacy_form.py`, sheet `Form Responses 1` | file on disk | ragged rows, corrupted numeric cells; idempotent on `GF-<row>`; xlsx no longer baked into the backend image (`backend/.dockerignore` excludes `*.xlsx`) — run imports from a checkout | synthetic fixture xlsx |

- [confirmed] No inbound webhooks; CSV exports are manual downloads (`/api/payroll-export/*`).
- [confirmed] Compose services (FEAT-004, 2026-09-03): `db` (local Postgres 16, named volume `pgdata`, no profile gate — always starts), `migrate`/`migrate-test`/`migrate-prod` (one-shot `scripts/migrate.sh` applying `supabase/migrations/*.sql` in order, tracked in a `schema_migrations` table, `ON_ERROR_STOP=1`; backend waits on `service_completed_successfully`), `backend`+`ui` (dev), `db-test`+`backend-test` (test: tmpfs db + pytest, exits), `backend-prod`+`ui-prod` (prod: requires `DATABASE_URL`+`PAYROLL_SECRET` from `.env`, no in-file defaults; `backend-prod` carries network alias `backend` because `ui/nginx.conf` proxies to `http://backend:8000`).
- [confirmed] Migration files manage their own `begin;`/`commit;` blocks (0001/0002/0003/0006/0007), so the runner must NOT add `--single-transaction`.
- [confirmed] `0003_rls.sql` references Supabase roles `anon`/`authenticated`; on plain Postgres `scripts/migrate.sh` creates them as NOLOGIN shims first (no-op on Supabase).
- [confirmed] Container boot never seeds: backend image CMD is uvicorn only; seeding is `make seed` (one-shot, gated by `SEED_DEMO_DATA=true`, refuses Supabase-looking URLs without `SEED_ALLOW_REMOTE=true`, never overwrites existing users, synthetic employees only).
- [confirmed] Images pinned by tag+digest (python:3.12-slim, node:20-alpine, nginx:1.27-alpine, postgres:16-alpine; digests fetched from Docker Hub 2026-09-03). Backend runtime runs as non-root `app`; nginx master stays root only because `nginx.conf` listens on :80 (documented in `ui/Dockerfile`; follow-up: nginx-unprivileged + :8080).
- [derived] `docker compose up --wait` with one-shot migrate services relies on compose ≥ v2.17 semantics (exited-0 one-shots satisfy `--wait`); local CLI is v2.31.0. Full-boot verification is the orchestrator's integration step (docker daemon was not running during FEAT-004).
