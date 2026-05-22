#!/usr/bin/env bash
# ictgrowthhacker-mcp 起動スクリプト (mac/Linux)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "[ictgrowthhacker-mcp] .venv が無いので作成します..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
exec .venv/bin/python server.py
