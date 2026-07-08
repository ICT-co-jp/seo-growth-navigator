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

if [ ! -f "requirements.lock" ]; then
  echo "[ictgrowthhacker-mcp] requirements.lock が見つかりません。" >&2
  exit 1
fi

lock_hash="$(".venv/bin/python" -c 'import hashlib, pathlib; print(hashlib.sha256(pathlib.Path("requirements.lock").read_bytes()).hexdigest())')"
lock_marker=".venv/requirements.lock.sha256"
installed_hash=""
if [ -f "$lock_marker" ]; then
  installed_hash="$(cat "$lock_marker")"
fi

if [ "$installed_hash" != "$lock_hash" ]; then
  echo "[ictgrowthhacker-mcp] Installing locked dependencies..."
  .venv/bin/python -m pip install --quiet --no-deps -r requirements.lock
  printf '%s\n' "$lock_hash" > "$lock_marker"
fi

exec .venv/bin/python server.py
