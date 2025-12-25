@echo off
chcp 65001 >nul
echo ====================================================================
echo 测试 Ollama 批量翻译
echo ====================================================================
echo.
echo 这个测试会：
echo   1. 检测 Ollama 服务是否运行
echo   2. 如果未运行，自动启动 Ollama
echo   3. 使用异步并发翻译 3 句话
echo   4. 显示翻译结果
echo.
echo ====================================================================
echo.

call C:\Users\7\miniconda3\Scripts\activate.bat ui

echo [环境] ui 已激活
echo.

python batch_retranslate_ollama.py test_ollama_config.json

echo.
echo ====================================================================
echo 测试完成
echo ====================================================================
pause
