@echo off
chcp 65001 >nul
title Ascendia - Starting...
color 0B

echo.
echo  ============================================
echo.
echo       A S C E N D I A
echo.
echo       AI-Powered Video Translation Platform
echo.
echo  ============================================
echo.

REM Save script directory
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Conda settings
set "CONDA_ACTIVATE=C:\Miniconda3\Scripts\activate.bat"
set "CONDA_ENV=ui"
set "CONDA_NODE=C:\Miniconda3\envs\ui\node.exe"
set "CONDA_PYTHON=C:\Miniconda3\envs\ui\python.exe"

REM Check Conda environment
if not exist "%CONDA_PYTHON%" (
    color 0C
    echo   [X] ERROR: Conda environment 'ui' not found
    echo.
    pause
    exit /b 1
)

echo   [1/4] Cleaning old processes...
REM Clean processes on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo         - Killing PID %%a [port 8000]
    taskkill /F /PID %%a >nul 2>&1
)
REM Clean processes on port 5173
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    echo         - Killing PID %%a [port 5173]
    taskkill /F /PID %%a >nul 2>&1
)
echo         Done.
echo.

echo   [2/4] Checking environment...
echo         - Conda env: %CONDA_ENV%
echo         Done.
echo.

REM Check frontend dependencies
echo   [3/4] Checking frontend dependencies...
if not exist "%SCRIPT_DIR%\frontend\node_modules\" (
    echo         - Installing node modules...
    cd /d "%SCRIPT_DIR%\frontend"
    call "%CONDA_ACTIVATE%" %CONDA_ENV%
    npm install --ignore-scripts
    node node_modules\esbuild\install.js 2>nul
    cd /d "%SCRIPT_DIR%"
) else (
    echo         - Node modules: OK
)
echo         Done.
echo.

echo   [4/4] Starting services...

REM Create temp startup script - backend
echo @echo off > "%TEMP%\localclip_backend.bat"
echo call "%CONDA_ACTIVATE%" %CONDA_ENV% >> "%TEMP%\localclip_backend.bat"
echo cd /d "%SCRIPT_DIR%\backend" >> "%TEMP%\localclip_backend.bat"
echo python main.py >> "%TEMP%\localclip_backend.bat"

REM Create temp startup script - frontend
echo @echo off > "%TEMP%\localclip_frontend.bat"
echo call "%CONDA_ACTIVATE%" %CONDA_ENV% >> "%TEMP%\localclip_frontend.bat"
echo cd /d "%SCRIPT_DIR%\frontend" >> "%TEMP%\localclip_frontend.bat"
echo node node_modules\vite\bin\vite.js >> "%TEMP%\localclip_frontend.bat"

REM Start backend (minimized)
echo         - Backend starting...
start /min "Ascendia-Backend" cmd /k "%TEMP%\localclip_backend.bat"
timeout /t 3 /nobreak >nul

REM Start frontend (minimized)
echo         - Frontend starting...
start /min "Ascendia-Frontend" cmd /k "%TEMP%\localclip_frontend.bat"
timeout /t 3 /nobreak >nul

echo         Done.
echo.
echo  ============================================
echo.
echo   Ascendia is ready!
echo.
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo.
echo   TIP: Use the Shutdown button in web UI to stop
echo.
echo  ============================================
echo.

REM Wait then open browser
echo   Opening browser in 5 seconds...
timeout /t 5 /nobreak >nul

start http://localhost:5173/dashboard

echo.
echo   Browser opened! This window will close in 3s...
echo.
timeout /t 3 /nobreak >nul
