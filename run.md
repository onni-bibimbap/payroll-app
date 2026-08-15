# Running Onni Payroll

3-tier stack: `ui` (React/Vite SPA on nginx) → `backend` (FastAPI) → Supabase
Postgres (or a local Postgres container).

## Quick start

```bash
make up
open http://localhost:8077
```

Demo accounts: `preparer/preparer123` · `approver/approver123` · `admin/admin123`

The first start builds both images, seeds users, and imports employees from
`backend/employee-registration-form.xlsx`, then applies the active roster.

By default the backend connects to Supabase using `DATABASE_URL` in `.env`
(already configured for this project). To use a local disposable Postgres
instead:

```bash
make up-local-db
```

## Make targets

| target | what it does |
|---|---|
| `make up` | build + start ui + backend (Supabase) |
| `make up-local-db` | build + start ui + backend + local Postgres |
| `make logs` | follow container logs |
| `make down` | stop containers, keep data |
| `make clean` | stop containers, wipe local db volume |

## Equivalent raw docker compose commands

```bash
docker compose up -d --build          # start
docker compose --profile local-db up -d --build   # start with local db
docker compose logs -f                # follow logs
docker compose down                   # stop
docker compose down -v                # stop + wipe local db volume
```

## Development outside docker

- backend:
  ```bash
  cd backend
  pip install -r requirements.txt
  python seed.py
  uvicorn app.main:app --reload
  ```
  Uses a local SQLite file unless `DATABASE_URL` is set in the environment.

- ui:
  ```bash
  cd ui
  npm install
  npm run dev
  ```
  Vite dev server on `http://localhost:5173`, proxies `/api` to `:8000`.

## Notes

- `webapp/` is the previous monolithic (Jinja + SQLite) version, kept only
  for reference — not part of the running stack.
- Data persists in the `pgdata` docker volume when using `--local-db`.
- Supabase connection details (`DATABASE_URL`, `SUPABASE_URL`,
  `SUPABASE_SERVICE_KEY`) live in `.env` at the repo root.
