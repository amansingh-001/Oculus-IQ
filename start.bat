@echo off
REM ─────────────────────────────────────────────────────────────────────────────
REM  OculusIQ — One-command launcher (Windows)
REM  Usage: start.bat
REM  Prerequisites: Python >= 3.11 with a .venv at the repo root, Node.js >= 18
REM ─────────────────────────────────────────────────────────────────────────────

echo Installing backend dependencies...
.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt

echo Starting backend on http://localhost:8000 ...
start "OculusIQ Backend" cmd /k "cd backend && ..\\.venv\\Scripts\\activate && uvicorn main:app --reload --port 8000"

echo Installing frontend dependencies...
cd frontend
call npm install --silent
cd ..

echo Starting frontend on http://localhost:5173 ...
start "OculusIQ Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo OculusIQ is starting up.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API docs: http://localhost:8000/docs
