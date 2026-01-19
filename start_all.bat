@echo off
chcp 65001 >nul
title LocalClip Editor - 启动中...

echo.
echo ========================================
echo   LocalClip Editor 一键启动
echo ========================================
echo.

REM 保存脚本所在目录
set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Conda 设置
set "CONDA_ACTIVATE=C:\Miniconda3\Scripts\activate.bat"
set "CONDA_ENV=ui"
set "CONDA_NODE=C:\Miniconda3\envs\ui\node.exe"
set "CONDA_PYTHON=C:\Miniconda3\envs\ui\python.exe"

REM 检查 Conda 环境
if not exist "%CONDA_PYTHON%" (
    echo [错误] 未找到 Conda 环境 ui
    pause
    exit /b 1
)

echo [1/4] 清理旧进程...
REM 清理占用 8000 端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING"') do (
    echo   - 关闭端口 8000 占用进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
REM 清理占用 5173 端口的进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING"') do (
    echo   - 关闭端口 5173 占用进程 PID: %%a
    taskkill /F /PID %%a >nul 2>&1
)
echo   - 端口清理完成
echo.

echo [2/4] 检查环境...
echo   - Conda 环境: %CONDA_ENV%
echo.

REM 检查前端依赖
echo [3/4] 检查前端依赖...
if not exist "%SCRIPT_DIR%\frontend\node_modules\" (
    echo   ! Node 模块不存在，正在安装...
    cd /d "%SCRIPT_DIR%\frontend"
    call "%CONDA_ACTIVATE%" %CONDA_ENV%
    npm install --ignore-scripts
    node node_modules\esbuild\install.js 2>nul
    cd /d "%SCRIPT_DIR%"
) else (
    echo   - Node 模块已安装
)
echo.

echo [4/4] 启动服务...
echo.

REM 创建临时启动脚本 - 后端
echo @echo off > "%TEMP%\localclip_backend.bat"
echo call "%CONDA_ACTIVATE%" %CONDA_ENV% >> "%TEMP%\localclip_backend.bat"
echo cd /d "%SCRIPT_DIR%\backend" >> "%TEMP%\localclip_backend.bat"
echo python main.py >> "%TEMP%\localclip_backend.bat"

REM 创建临时启动脚本 - 前端
echo @echo off > "%TEMP%\localclip_frontend.bat"
echo call "%CONDA_ACTIVATE%" %CONDA_ENV% >> "%TEMP%\localclip_frontend.bat"
echo cd /d "%SCRIPT_DIR%\frontend" >> "%TEMP%\localclip_frontend.bat"
echo node node_modules\vite\bin\vite.js >> "%TEMP%\localclip_frontend.bat"

REM 启动后端
echo   - 正在启动后端服务...
start "LocalClip-Backend" cmd /k "%TEMP%\localclip_backend.bat"
timeout /t 3 /nobreak >nul

REM 启动前端
echo   - 正在启动前端服务...
start "LocalClip-Frontend" cmd /k "%TEMP%\localclip_frontend.bat"
timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   启动完成！
echo ========================================
echo.
echo   后端服务: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo   前端界面: http://localhost:5173
echo.
echo   提示：关闭服务窗口即可停止服务
echo.

REM 等待后自动打开浏览器
echo   5 秒后自动打开浏览器...
timeout /t 5 /nobreak >nul

start http://localhost:5173/dashboard

echo.
echo   浏览器已打开！
echo.
pause
