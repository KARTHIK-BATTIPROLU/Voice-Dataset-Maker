@echo off
echo ================================================
echo   ASTA Voice Dataset Collector
echo ================================================
echo.
echo Starting backend and frontend servers...
echo.

REM Start backend in new window
start "ASTA Backend" cmd /k start_backend.bat

REM Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak

REM Start frontend in current window
call start_frontend.bat
