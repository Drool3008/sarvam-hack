#!/usr/bin/env bash
# Run the whole suite. Wrappers are mocked at their own boundary, so this needs
# no Sarvam key and makes no network call.
set -euo pipefail
cd "$(dirname "$0")/backend"
SARVAM_MOCK=true exec ../.venv/bin/python -m pytest tests -q "$@"
