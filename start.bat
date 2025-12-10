@echo off
REM LocalClip Editor Windows Startup Script

echo ================================
echo    LocalClip Editor Startup
echo ================================
echo.

REM Get script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Check and clean occupied ports
echo [1/6] Checking and cleaning occupied ports...
echo.

REM Clean port 8000 (backend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing process on port 8000: %%a
    taskkill /F /PID %%a 2>nul
)

REM Clean port 5173 (frontend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do (
    echo Killing process on port 5173: %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo [2/6] Starting backend service (FastAPI)...
echo.

REM Activate conda environment and start backend
cd "%SCRIPT_DIR%backend"
start "LocalClip-Backend" cmd /k "call conda activate ui && uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to start
echo [3/6] Waiting for backend service to start...
timeout /t 5 /nobreak > nul
echo.

REM Check frontend dependencies
echo [4/6] Checking frontend dependencies...
cd "%SCRIPT_DIR%frontend"
if not exist "node_modules" (
    echo First run, installing frontend dependencies...
    call npm install
) else (
    echo Frontend dependencies already installed, skipping...
)
echo.

REM Start frontend service
echo [5/6] Starting frontend service (React + Vite)...
cd "%SCRIPT_DIR%frontend"
start "LocalClip-Frontend" cmd /k "npm run dev"
echo.

echo [6/6] Done!
echo.
echo ================================
echo   LocalClip Editor Started!
echo ================================
echo.
echo Frontend URL: http://localhost:5173
echo Backend API:  http://localhost:8000/docs
echo.
echo Press any key to close this window (services will keep running)
echo To stop services, close the corresponding windows
echo ================================
pause > nul
