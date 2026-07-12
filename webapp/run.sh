#!/usr/bin/env bash
# Start the Onni Payroll web app.
#   ./run.sh            -> install deps (first run), seed if empty, start server
#   ./run.sh --reseed   -> re-import employees from the registration form
set -euo pipefail
cd "$(dirname "$0")"

python3 -m pip install -q -r requirements.txt

if [[ "${1:-}" == "--reseed" ]]; then
  python3 seed.py --reimport
else
  python3 seed.py
fi

echo "→ http://127.0.0.1:8077   (preparer/preparer123 · approver/approver123 · admin/admin123)"
exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8077
