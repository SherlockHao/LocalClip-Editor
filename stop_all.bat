@echo off
chcp 65001 >nul
title LocalClip Editor - 停止服务

echo.
echo ========================================
echo   LocalClip Editor 停止服务
echo ========================================
echo.

echo [1/2] 停止后端服务...
taskkill /FI "WINDOWTITLE eq LocalClip - 后端服务*" /F >nul 2>&1
if errorlevel 1 (
    echo   ⚠ 后端服务未运行
) else (
    echo   ✓ 后端服务已停止
)

echo.
echo [2/2] 停止前端服务...
taskkill /FI "WINDOWTITLE eq LocalClip - 前端服务*" /F >nul 2>&1
if errorlevel 1 (
    echo   ⚠ 前端服务未运行
) else (
    echo   ✓ 前端服务已停止
)

echo.
echo ========================================
echo   所有服务已停止
echo ========================================
echo.
pause
