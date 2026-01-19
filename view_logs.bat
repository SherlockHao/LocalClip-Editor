@echo off
REM 查看后端和前端日志的脚本

echo ========================================
echo LocalClip Editor - 日志查看工具
echo ========================================
echo.

:menu
echo 请选择要查看的日志:
echo.
echo [1] 后端日志 (backend_upload_test.log)
echo [2] 前端日志 (frontend.log)
echo [3] 实时监控后端日志 (tail -f)
echo [4] 实时监控前端日志 (tail -f)
echo [5] 查看最近的错误 (后端)
echo [6] 退出
echo.

set /p choice="请输入选择 (1-6): "

if "%choice%"=="1" goto backend_log
if "%choice%"=="2" goto frontend_log
if "%choice%"=="3" goto backend_tail
if "%choice%"=="4" goto frontend_tail
if "%choice%"=="5" goto backend_errors
if "%choice%"=="6" goto end

echo 无效选择，请重试
echo.
goto menu

:backend_log
echo.
echo ========================================
echo 后端日志 (最后50行)
echo ========================================
tail -50 backend\backend_upload_test.log
echo.
pause
goto menu

:frontend_log
echo.
echo ========================================
echo 前端日志 (最后50行)
echo ========================================
tail -50 frontend\frontend.log
echo.
pause
goto menu

:backend_tail
echo.
echo ========================================
echo 实时监控后端日志 (Ctrl+C 退出)
echo ========================================
tail -f backend\backend_upload_test.log
goto menu

:frontend_tail
echo.
echo ========================================
echo 实时监控前端日志 (Ctrl+C 退出)
echo ========================================
tail -f frontend\frontend.log
goto menu

:backend_errors
echo.
echo ========================================
echo 后端错误日志
echo ========================================
findstr /i "error exception failed 失败 错误" backend\backend_upload_test.log
echo.
pause
goto menu

:end
echo.
echo 退出日志查看工具
