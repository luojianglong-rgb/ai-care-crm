@echo off
chcp 65001 >nul
title AI-Care CRM - Starting...

echo ============================================
echo   AI-Care CRM System Startup
echo ============================================
echo.

:: Check Python venv
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python venv not found. Run: python -m venv .venv
    echo         Then: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

:: Check node_modules
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend && npm install && cd ..
)

:: Start backend
echo [1/2] Starting backend (FastAPI :8000) ...
start "AI-Care Backend" cmd /k "cd /d %~dp0src && ..\\.venv\\Scripts\\python main.py"

:: Wait for backend to be ready
timeout /t 5 /nobreak >nul

:: Start frontend
echo [2/2] Starting frontend (Vite :5173) ...
start "AI-Care Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo   AI-Care CRM Started Successfully!
echo.
echo   Admin:  http://localhost:5173
echo   WAP:    http://localhost:5173/wap
echo   API:    http://localhost:8000/docs
echo ============================================
echo.
echo Press any key to open browser...
pause >nul
start http://localhost:5173
