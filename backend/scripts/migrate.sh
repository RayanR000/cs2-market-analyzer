#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "${ROOT_DIR}/venv/bin/alembic" ]]; then
  exec "${ROOT_DIR}/venv/bin/alembic" upgrade head
fi

exec "${ROOT_DIR}/venv/bin/python" "${ROOT_DIR}/scripts/run_task.py" migrate
