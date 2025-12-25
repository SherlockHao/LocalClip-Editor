@echo off
chcp 65001 >nul
echo ================================================================
echo 翻译功能测试
echo ================================================================
echo.
echo 这个测试会：
echo   1. 检测 GPU 显存
echo   2. 自动选择最优模型 (Qwen3-4B-FP8 或 Qwen3-1.7B)
echo   3. 翻译测试文本: "你好" -^> 韩文
echo.
echo ================================================================
echo.

call C:\Users\7\miniconda3\Scripts\activate.bat qwen_inference

echo [环境] qwen_inference 已激活
echo.

python test_translation_simple.py

echo.
pause
