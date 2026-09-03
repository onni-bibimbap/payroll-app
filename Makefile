.PHONY: up down test migrate psql seed backup restore logs clean

COMPOSE = docker compose

# Start the dev stack (local Postgres + backend + ui) and wait for health.
up:
	$(COMPOSE) --profile dev up -d --build --wait
	@echo
	@echo "Onni Payroll (dev): http://localhost:8077"
	@echo "Demo data (local db only): make seed"

# Stop containers in every profile. Data in the pgdata volume is kept.
down:
	$(COMPOSE) --profile dev --profile test --profile prod down

# Run the backend pytest suite in the test profile (ephemeral tmpfs db +
# migrations + same image). Propagates the pytest exit code.
test:
	$(COMPOSE) --profile test build backend-test
	$(COMPOSE) --profile test run --rm backend-test; \
	status=$$?; \
	$(COMPOSE) --profile test rm -sf db-test migrate-test >/dev/null 2>&1; \
	exit $$status

# Apply supabase/migrations/*.sql to the LOCAL db (idempotent).
migrate:
	$(COMPOSE) run --rm migrate

# psql shell into the local db.
psql:
	$(COMPOSE) exec db psql -U payroll -d payroll

# Explicit one-shot demo seed (synthetic data, local dev db only).
seed:
	$(COMPOSE) --profile dev run --rm -e SEED_DEMO_DATA=true backend python seed.py

# pg_dump the local db into backups/ (gitignored).
backup:
	@mkdir -p backups
	$(COMPOSE) exec -T db pg_dump -U payroll -d payroll \
		> backups/payroll-$$(date +%Y%m%d-%H%M%S).sql
	@echo "Wrote backups/$$(ls -t backups | head -1)"

# Restore a backup into the local db: make restore FILE=backups/payroll-....sql
restore:
ifndef FILE
	$(error Usage: make restore FILE=backups/payroll-YYYYmmdd-HHMMSS.sql)
endif
	$(COMPOSE) exec -T db psql -U payroll -d payroll -v ON_ERROR_STOP=1 < $(FILE)

# Follow dev-stack logs.
logs:
	$(COMPOSE) --profile dev logs -f

# DESTRUCTIVE: removes containers AND the pgdata volume (all local payroll
# data). Requires CONFIRM=wipe-data; running it needs a logged DECISION.
clean:
ifneq ($(CONFIRM),wipe-data)
	@echo "make clean DESTROYS the local database volume 'pgdata':"
	@echo "  - every local payroll run, payslip and approval"
	@echo "  - every local employee row and audit record"
	@echo "  - all containers for the dev/test/prod profiles"
	@echo "If you really mean it:  make clean CONFIRM=wipe-data"
	@exit 1
else
	$(COMPOSE) --profile dev --profile test --profile prod down -v
endif
