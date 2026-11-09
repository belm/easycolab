#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ]; then
    echo "Creating virtual environment (.venv)..."
    python3 -m venv .venv
    .venv/bin/pip install -r windows_app/requirements-windows.txt
fi

exec .venv/bin/python windows_app/easycolab_win.py "$@"
