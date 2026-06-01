#!/usr/bin/env bash
set -e
echo "Starting OculusIQ..."
cd backend
source ../.venv/bin/activate
uvicorn main:app --reload --port 8000 &
cd ../frontend
npm run dev
