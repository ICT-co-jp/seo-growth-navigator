#!/usr/bin/env bash
# ga4-gsc-mcp 起動スクリプト (mac/Linux)
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "[ga4-gsc-mcp] .venv が無いので作成します..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
exec .venv/bin/python server.py
