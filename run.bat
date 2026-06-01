@echo off
echo ======================================================================
echo             CuraAI SMART HEALTHCARE SYSTEM STARTUP SCRIPT
echo ======================================================================
echo.

:: Start Flask Backend in a new window
echo [System] Initializing Flask Backend Server...
start "CuraAI Backend Server" cmd /k "cd backend && py app.py"

:: Start Vite React Frontend in a new window
echo [System] Initializing React Vite Dev Server...
start "CuraAI Frontend Client" cmd /k "cd frontend && npx vite --host 127.0.0.1 --port 5173"

echo.
echo ======================================================================
echo Servers booted successfully!
echo Flask Backend API: http://127.0.0.1:5000/api
echo React Frontend UI:  http://127.0.0.1:5173/
echo ======================================================================
echo.
pause
