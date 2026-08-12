@echo off
echo Starting ASTA Voice Dataset Collector - Frontend...
echo.

cd frontend

REM Install npm dependencies if node_modules doesn't exist
if not exist "node_modules\" (
    echo Installing npm dependencies...
    npm install
)

REM Start React development server
echo.
echo Starting React development server on http://localhost:3000
echo.
npm run dev
