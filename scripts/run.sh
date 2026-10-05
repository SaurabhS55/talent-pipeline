#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export PYTHONPATH="$ROOT:$ROOT/src/main${PYTHONPATH:+:$PYTHONPATH}"

if [[ -x "$ROOT/.py312/bin/python" ]]; then
  PYTHON="$ROOT/.py312/bin/python"
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
else
  PYTHON="python3"
fi

exec "$PYTHON" src/main/main.py "$@"
