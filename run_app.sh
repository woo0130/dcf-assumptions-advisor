#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
    echo "[1/3] Creating a Python virtual environment..."
    if command -v python3.12 >/dev/null 2>&1; then
        python3.12 -m venv .venv
    elif command -v python3 >/dev/null 2>&1; then
        python3 -m venv .venv
    else
        echo "[ERROR] Python 3 was not found. Install Python 3.12 and run this script again." >&2
        exit 1
    fi
else
    echo "[1/3] Using the existing .venv."
fi

echo "[2/3] Installing required packages..."
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt

echo "[3/3] Starting DCF Assumptions Advisor..."
export PYTHONPATH="."
exec .venv/bin/python -m streamlit run app.py
