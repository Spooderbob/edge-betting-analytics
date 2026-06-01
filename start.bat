@echo off
title EDGE — Betting Analytics Engine
echo.
echo  ========================================
echo   EDGE - Sports Analytics Engine v2.0
echo  ========================================
echo.

REM Start backend
echo [1/3] Starting backend API on port 8000...
cd /d "%~dp0backend"
pip install -r requirements.txt -q
start "EDGE Backend" cmd /k "python -m uvicorn main:app --reload --port 8000"
timeout /t 3 /nobreak >nul

REM Start frontend
echo [2/3] Starting frontend on port 3000...
cd /d "%~dp0frontend"
if not exist node_modules (
    echo Installing frontend dependencies...
    npm install
)
start "EDGE Frontend" cmd /k "npm run dev"
timeout /t 4 /nobreak >nul

REM Open browser
echo [3/3] Opening dashboard...
start http://localhost:3000

echo.
echo  EDGE is running!
echo  Dashboard : http://localhost:3000
echo  API Docs  : http://localhost:8000/docs
echo.
echo  To stop: close the two terminal windows
echo.
