#!/bin/sh
# Apply supabase/migrations/*.sql in filename order against $DATABASE_URL.
#
# - Tracks applied files in a schema_migrations table, so re-runs are
#   idempotent (already-applied files are skipped).
# - Every psql call runs with ON_ERROR_STOP=1: the first failing statement
#   aborts the run with a non-zero exit, which blocks dependent services
#   (backend waits on service_completed_successfully).
# - Migration files manage their own begin;/commit; blocks, so the runner
#   does NOT add --single-transaction. If a run dies between applying a file
#   and recording it, the repo convention (additive, idempotent SQL) makes
#   the re-apply safe.
# - On a plain (non-Supabase) Postgres the Supabase roles referenced by
#   0003_rls.sql do not exist; they are created here as NOLOGIN shims.
#
# Env: DATABASE_URL (required; SQLAlchemy postgresql+driver:// URLs accepted),
#      MIGRATIONS_DIR (default /migrations).
set -eu

MIGRATIONS_DIR="${MIGRATIONS_DIR:-/migrations}"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "migrate: FATAL: DATABASE_URL is empty." >&2
    echo "migrate: the prod profile requires it in .env; no default is shipped." >&2
    exit 1
fi

# SQLAlchemy-style URLs (postgresql+psycopg2://...) -> libpq URLs.
url=$(printf '%s' "$DATABASE_URL" | sed -e 's|^postgresql+[a-z0-9]*:|postgresql:|')

run_psql() {
    psql "$url" -X -q -v ON_ERROR_STOP=1 "$@"
}

# Wait for the database (up to 60s) — covers external DBs that sit outside
# the compose healthcheck (e.g. Supabase).
i=0
until run_psql -c 'select 1' >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -ge 60 ]; then
        echo "migrate: FATAL: database not reachable after 60s" >&2
        exit 1
    fi
    sleep 1
done

# Shim the Supabase PostgREST roles on plain Postgres (no-op on Supabase).
run_psql <<'SQL'
do $$
begin
    if not exists (select 1 from pg_roles where rolname = 'anon') then
        create role anon nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'authenticated') then
        create role authenticated nologin;
    end if;
    if not exists (select 1 from pg_roles where rolname = 'service_role') then
        create role service_role nologin;
    end if;
end
$$;
SQL

run_psql -c 'create table if not exists schema_migrations (
    filename   text primary key,
    applied_at timestamptz not null default now()
);'

found=0
for f in "$MIGRATIONS_DIR"/*.sql; do
    [ -e "$f" ] || continue
    found=1
    name=$(basename "$f")
    applied=$(run_psql -tA -c "select 1 from schema_migrations where filename = '$name'")
    if [ "$applied" = "1" ]; then
        echo "migrate: skip  $name (already applied)"
        continue
    fi
    echo "migrate: apply $name"
    run_psql -f "$f"
    run_psql -c "insert into schema_migrations (filename) values ('$name')"
done

if [ "$found" = "0" ]; then
    echo "migrate: FATAL: no .sql files found in $MIGRATIONS_DIR" >&2
    exit 1
fi

echo "migrate: done"
