#!/usr/bin/env bash
# Start the backend. The Sarvam key is read server-side from .env only.
set -euo pipefail
cd "$(dirname "$0")"
exec .venv/bin/python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
