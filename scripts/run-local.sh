#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ -x "$PROJECT_ROOT/.venv/bin/python" ]; then
    PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if [ ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
    echo "Compiled frontend assets are missing from frontend/dist." >&2
    exit 1
fi

DATA_DIR="${CER_DATA_DIR:-$PROJECT_ROOT/data}"
mkdir -p "$DATA_DIR"
export CER_DATABASE_PATH="${CER_DATABASE_PATH:-$DATA_DIR/cer-emulator.db}"

exec "$PYTHON_BIN" -m uvicorn app.main:app \
    --app-dir "$PROJECT_ROOT/backend" \
    --host "${CER_HOST:-0.0.0.0}" \
    --port "${CER_PORT:-8080}"
