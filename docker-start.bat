@echo off
echo.
echo ============================================================
echo   Hospital Billing System - Local Docker Deployment
echo ============================================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not running. Please start it and try again.
    pause
    exit /b
)

:: Copy .env.docker to .env if not exists
if not exist .env (
    echo [INFO] Creating .env from .env.docker...
    copy .env.docker .env
)

echo [INFO] Building and starting containers...
docker-compose up --build -d

echo.
echo ============================================================
echo   SUCCESS! The system is starting up.
echo.
echo   Frontend/API: http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo.
echo   Use 'docker-compose logs -f app' to see logs.
echo ============================================================
echo.
pause
