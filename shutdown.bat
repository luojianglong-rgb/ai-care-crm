@echo off
chcp 65001 >nul
title AI-Care CRM - Shutdown

echo ============================================
echo   AI-Care CRM System Shutdown
echo ============================================
echo.

:: Kill backend (python/uvicorn on port 8000)
echo [1/2] Stopping backend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

:: Kill frontend (node/vite on port 5173)
echo [2/2] Stopping frontend...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo   All services stopped.
echo ============================================
timeout /t 3
