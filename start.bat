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
start "LocalClip-Backend" cmd /k "C:\Miniconda3\Scripts\conda.exe run -n ui --no-capture-output uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend to be ready
echo [3/6] Waiting for backend service to start...
echo This may take 10-20 seconds...
echo.

REM Check if backend is ready (loop until service responds)
set BACKEND_MAX_RETRIES=30
set BACKEND_RETRY_COUNT=0

:check_backend
REM Use curl if available, otherwise use powershell
curl -s -o nul -w "%%{http_code}" http://localhost:8000/ | findstr "200 404" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Backend service is ready!
    goto backend_ready
)

set /a BACKEND_RETRY_COUNT+=1
if %BACKEND_RETRY_COUNT% GEQ %BACKEND_MAX_RETRIES% (
    echo Warning: Backend service check timed out after %BACKEND_MAX_RETRIES% seconds
    echo Continuing anyway, but API may not be available yet...
    goto backend_ready
)

echo Waiting for backend... (%BACKEND_RETRY_COUNT%/%BACKEND_MAX_RETRIES%)
timeout /t 1 /nobreak > nul
goto check_backend

:backend_ready
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
start "LocalClip-Frontend" cmd /k "node node_modules\vite\bin\vite.js"
echo.

echo [6/7] Waiting for frontend service to be ready...
echo This may take 10-30 seconds on first run...
echo.

REM Wait for frontend to be accessible (loop until service responds)
set MAX_RETRIES=60
set RETRY_COUNT=0

:check_frontend
powershell -Command "try { $response = Invoke-WebRequest -Uri http://localhost:5173 -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop; exit 0 } catch { exit 1 }" >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    echo Frontend service is ready!
    goto frontend_ready
)

set /a RETRY_COUNT+=1
if %RETRY_COUNT% GEQ %MAX_RETRIES% (
    echo Warning: Frontend service check timed out after %MAX_RETRIES% seconds
    echo The service may still be starting, please check manually
    goto open_browser
)

timeout /t 1 /nobreak > nul
goto check_frontend

:frontend_ready
echo.

:open_browser
echo [7/7] Opening browser...
echo.
start http://localhost:5173
timeout /t 2 /nobreak > nul

echo ================================
echo   LocalClip Editor Started!
echo ================================
echo.
echo Frontend URL: http://localhost:5173
echo Backend API:  http://localhost:8000/docs
echo.
echo Browser window should open automatically
echo If not, please manually open: http://localhost:5173
echo.
echo Press any key to close this window (services will keep running)
echo To stop services, close the corresponding windows
echo ================================
pause > nul
