---
name: infra_skills
description: Default runtime for every project — Docker Compose from day one, with all state persisted in PostgreSQL (or another suitable durable store declared in PROJECT_PROFILE §10) on named volumes. Use whenever a project is scaffolded, a service or datastore is added, data is stored anywhere, a local/dev/test environment is set up, migrations or backups are touched, or a release is prepared. No project runs "on the host" and no data lives only in memory, files, or a container's writable layer.
---

# Infra skills — Compose by default, PostgreSQL by default, nothing ephemeral

Every project in this library boots with `docker compose up` and keeps every byte of state in a durable database on a named volume. An agent that stores data any other way has not finished the feature.

## The defaults (override only with a logged DECISION)
| Concern | Default | Notes |
|---|---|---|
| Runtime | `docker compose` (v2, `compose.yaml`) | one file at repo root; profiles `dev`, `test`, `prod` |
| Primary store | **PostgreSQL 16** | named volume `pgdata`; healthcheck `pg_isready` |
| Object store | MinIO (S3 API) when blobs exist (§7 audio, files, exports) | named volume `blobdata`; references in Postgres, bytes in MinIO |
| Cache / queue | Redis only when §11/§12 justify it | never the source of truth |
| Search / vectors | `pgvector` / Postgres FTS first; a separate engine only by DECISION | keeps one backup story |
| Migrations | versioned, forward-only, in repo (Alembic, Prisma, Flyway, golang-migrate — per §10 stack) | applied by a `migrate` service before the app starts |
| Config | `.env` (gitignored) + `.env.example` (committed, every key documented) | secrets never in `compose.yaml` |
| Observability | app logs to stdout; `/health` and `/metrics` endpoints; OTel collector optional | Compose `healthcheck` on every service |

"Suitable DB" means: if PROJECT_PROFILE §10 declares a different durable store (e.g. time-series, graph) with a reason, use it — still on a named volume, still migrated, still backed up. SQLite is acceptable only for a CLI-only surface, and only by DECISION.

## Compose contract
- Services: `app` (+ `worker` if background jobs exist), `db`, `migrate`, optional `minio`, `redis`, `otel`. Every service has `healthcheck`, `restart: unless-stopped`, and `depends_on` with `condition: service_healthy`.
- Volumes: every stateful service mounts a **named volume**, never a bind mount for data, never the container layer. `docker compose down` must not lose data; only `down -v` does, and that is never run by an agent without a human DECISION.
- Profiles: `dev` (hot reload, seeded synthetic data, exposed ports), `test` (ephemeral DB from the same image and migrations, runs the suite, exits), `prod` (no seeds, no exposed DB port, read-only root FS, resource limits).
- Ports: only `app` publishes; the DB is reachable through the compose network. Local admin access via `docker compose exec db psql`.
- Images pinned by tag *and* digest for `prod`; the app image built from a multi-stage `Dockerfile` running as a non-root user.
- One command boots everything: `make up` → `docker compose --profile dev up -d --wait`. `make test` runs the `test` profile. Both are the pre-checks the judge runs.

## Persistence rules
1. **Every entity has a table.** Runtime state, settings, audit events, job queues, feature flags, uploaded files' metadata — all in Postgres. In-memory maps are caches with a documented rebuild path, never the record.
2. **Audit tier never drops.** Events that gate a §6 high-risk path are written in the same transaction as the change, or spilled to disk and replayed; a lost audit row is a security FAIL.
3. **Migrations are the schema.** No `CREATE TABLE IF NOT EXISTS` in app code; no manual DDL. Every migration has a down or a documented reason it is irreversible.
4. **Backups exist before prod.** Nightly `pg_dump` (and MinIO mirror) to a location outside the host, restore rehearsed and timed once per release; retention per §8.
5. **Retention is a job.** Deletion per §8 runs as a scheduled worker that reaches rows *and* blobs, logs counts, and is idempotent.
6. **Seeds are synthetic.** `dev` seeds come from `scripts/seed_*`; never a production dump.
7. **Connections are pooled** (app-side pool or pgbouncer); statement timeouts set; every hot query has an index (performance_skills).

## Agent procedure — when a project or feature touches infra
1. On scaffold: create `compose.yaml`, `Dockerfile`, `.env.example`, `Makefile` (`up`, `down`, `test`, `migrate`, `psql`, `backup`, `restore`), `migrations/0001_init`, and a `/health` endpoint. Log `INFRA | date | scaffold | services: app, db, migrate` in `ORCHESTRATION_LOG.md`.
2. On any new stored entity: add the migration, the model, the retention rule, and the backup inclusion in the same FEAT-###. The UI Spec's "Performance" and features_skills' acceptance criteria cite the table.
3. On a new external dependency: add the service to Compose with a healthcheck, or a documented reason it stays external (§9).
4. Before COMPLETE: `make up` from a clean checkout succeeds with `--wait`; `make test` passes; `docker compose down && docker compose up` preserves the seeded data; `make backup && make restore` round-trips on the `test` profile.

## Gates this skill feeds
- **features_skills**: `make up` and `make test` are mandatory pre-checks; a feature whose data does not survive a container restart is HOLD.
- **security_skills**: secrets via `.env`/vault only; DB port unpublished in `prod`; non-root images; backups encrypted at rest; `down -v` needs a DECISION.
- **performance_skills**: budgets measured against the Compose stack, not the host; load tests run with the `prod` profile's resource limits.
- **domain_skills**: `_shared/integrations.md` records every Compose service and every external system it stands in for.

## Anti-patterns — reject on sight
Running the app with `python main.py` / `npm start` on the host as the documented path · JSON or CSV files as the database · state in a container's writable layer · bind-mounted data directories · `latest` tags in prod · DB port published in prod · secrets in `compose.yaml` or images · app code that creates tables · a feature merged without a migration for its data · a "temporary" in-memory store that ships.
