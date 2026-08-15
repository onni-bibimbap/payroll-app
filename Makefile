.PHONY: up up-local-db down clean logs

# Build and start ui + backend, pointed at Supabase (default DATABASE_URL in .env)
up:
	docker compose up -d --build
	@echo
	@echo "Onni Payroll: http://localhost:8077"
	@echo "Demo accounts: preparer/preparer123 · approver/approver123 · admin/admin123"

# Build and start ui + backend + a local disposable Postgres instead of Supabase
up-local-db:
	docker compose --profile local-db up -d --build
	@echo
	@echo "Onni Payroll: http://localhost:8077"
	@echo "Demo accounts: preparer/preparer123 · approver/approver123 · admin/admin123"

# Stop containers, keep data
down:
	docker compose down

# Stop containers and wipe the local db volume
clean:
	docker compose down -v

# Follow logs
logs:
	docker compose logs -f
