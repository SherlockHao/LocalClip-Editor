@echo off
chcp 65001 >nul
REM LocalClip Editor Windows 启动脚本
REM 用于启动打包后的应用程序

echo =========================================
echo   LocalClip Editor - Windows 版
echo =========================================
echo.

REM 获取脚本所在目录
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

REM 设置环境变量
set "LOCALCLIP_BASE_PATH=%APP_DIR%"
set "PATH=%APP_DIR%\ffmpeg;%PATH%"

echo [1/4] 检查目录结构...
if not exist "backend\LocalClipEditor.exe" (
    echo [错误] 未找到后端程序: backend\LocalClipEditor.exe
    echo 请确保已正确解压所有文件！
    pause
    exit /b 1
)

if not exist "ffmpeg\ffmpeg.exe" (
    echo [警告] 未找到 FFmpeg，视频处理功能可能无法使用
)

if not exist "models" (
    echo [警告] 未找到模型目录，AI 功能可能无法使用
)

echo [完成] 目录结构检查通过
echo.

echo [2/4] 创建必要目录...
if not exist "uploads" mkdir uploads
if not exist "exports" mkdir exports
if not exist "audio_segments" mkdir audio_segments
if not exist "logs" mkdir logs
echo [完成] 目录创建完成
echo.

echo [3/4] 清理旧进程...
REM 终止占用 8000 端口的进程
for /f "tokens=5" %%a in ('netstat -aon ^| find ":8000" ^| find "LISTENING"') do (
    echo 发现占用端口 8000 的进程: %%a
    taskkill /F /PID %%a >nul 2>&1
)
echo [完成] 端口清理完成
echo.

echo [4/4] 启动应用程序...
echo.
echo =========================================
echo   应用程序正在启动...
echo =========================================
echo   后端 API: http://localhost:8000
echo   前端界面: http://localhost:8000
echo   API 文档: http://localhost:8000/docs
echo =========================================
echo.
echo [提示] 请在浏览器中打开: http://localhost:8000
echo [提示] 按 Ctrl+C 可以停止程序
echo.

REM 启动后端服务
cd backend
start /B "" "LocalClipEditor.exe" --host 0.0.0.0 --port 8000

REM 等待服务启动
timeout /t 3 /nobreak >nul

REM 尝试在默认浏览器中打开
echo 正在打开浏览器...
start http://localhost:8000

echo.
echo =========================================
echo   应用程序已启动！
echo =========================================
echo   如需停止，请关闭此窗口或按 Ctrl+C
echo =========================================
echo.

REM 保持窗口打开
pause
