#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x ".venv/bin/python" ] || [ ! -x ".venv/bin/pip" ]; then
    echo "Creating virtual environment (.venv)..."
    rm -rf .venv
    if ! python3 -m venv .venv; then
        echo "Error: Failed to create virtual environment. On Ubuntu/Debian, please install python3-venv (sudo apt install python3-venv)." >&2
        exit 1
    fi
    .venv/bin/pip install -r windows_app/requirements-windows.txt
fi

exec .venv/bin/python windows_app/easycolab_win.py "$@"
