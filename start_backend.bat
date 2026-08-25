@echo off
echo Starting ASTA Voice Dataset Collector - Backend...
echo.

cd backend

REM Check if virtual environment exists
if not exist "venv\" (
    echo Creating Python virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing Python dependencies...
pip install -r ../requirements.txt

REM Start FastAPI server
echo.
echo Starting FastAPI server on http://localhost:9090
echo.
uvicorn main:app --reload --host 0.0.0.0 --port 9090
