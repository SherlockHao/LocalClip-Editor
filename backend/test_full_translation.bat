@echo off
chcp 65001 >nul
echo ====================================================================
echo 完整翻译流程测试
echo ====================================================================
echo.
echo 这个测试会：
echo   1. 检测 GPU 显存
echo   2. 自动选择最优模型
echo   3. 加载模型
echo   4. 翻译测试文本
echo.
echo ====================================================================
echo.

call C:\Users\7\miniconda3\Scripts\activate.bat qwen_inference

echo [环境] qwen_inference 已激活
echo.

python batch_retranslate.py test_config.json

echo.
echo ====================================================================
echo 测试完成
echo ====================================================================
pause
