#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  OculusIQ — One-command launcher (macOS / Linux)
#  Usage: ./start.sh
#  Prerequisites: Python ≥ 3.11 with a .venv at the repo root, Node.js ≥ 18
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ── Activate Python virtual environment ──────────────────────────────────────
if [ ! -f "$REPO_ROOT/.venv/bin/activate" ]; then
  echo "Virtual environment not found. Creating one..."
  python3 -m venv "$REPO_ROOT/.venv"
fi

source "$REPO_ROOT/.venv/bin/activate"

# ── Install / sync backend dependencies ──────────────────────────────────────
echo "Installing backend dependencies..."
pip install -q -r "$REPO_ROOT/backend/requirements.txt"

# ── Start backend in background ───────────────────────────────────────────────
echo "Starting backend on http://localhost:8000 ..."
cd "$REPO_ROOT/backend"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# ── Install / sync frontend dependencies ─────────────────────────────────────
echo "Installing frontend dependencies..."
cd "$REPO_ROOT/frontend"
npm install --silent

# ── Start frontend (blocks until Ctrl-C) ─────────────────────────────────────
echo "Starting frontend on http://localhost:5173 ..."
trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM
npm run dev
