@echo off
chcp 65001 >nul
echo ====================================================================
echo 测试 Qwen3-4B-FP8 模型
echo ====================================================================
echo.

call C:\Users\7\miniconda3\Scripts\activate.bat qwen_inference

echo [环境] qwen_inference 已激活
echo.

python batch_retranslate.py test_qwen3_4b_fp8.json

echo.
pause
