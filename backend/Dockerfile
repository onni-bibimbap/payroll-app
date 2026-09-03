# Multi-stage build; runtime runs as a non-root user and starts uvicorn ONLY.
# Seeding is an explicit one-shot (`make seed`), never part of container boot
# (INFRA-01/SEC-10). No spreadsheets or other data files are copied into the
# image (SEC-09/GAP-07) — backend/.dockerignore excludes *.xlsx as a backstop.
# Legacy imports (import_legacy_form.py) run from a checkout, not the image.

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS builder

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea AS runtime

WORKDIR /srv
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
COPY --from=builder /install /usr/local
COPY app ./app
COPY seed.py ./
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Test image: same runtime plus pytest; the compose `test` profile builds this
# target and mounts backend/tests read-only (tests are not shipped in runtime).
FROM runtime AS test
USER root
RUN pip install --no-cache-dir pytest==8.3.4
USER app
