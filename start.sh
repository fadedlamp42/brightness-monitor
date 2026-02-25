#!/usr/bin/env bash
# start brightness-monitor daemon via PM2
# uses the project's venv python directly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="${SCRIPT_DIR}/.venv/bin/python3"

if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "error: venv not found at ${VENV_PYTHON}"
    echo "run: python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
    exit 1
fi

exec "$VENV_PYTHON" -m brightness_monitor.main "$@"
