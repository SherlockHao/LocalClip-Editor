@echo off
chcp 65001 >nul
call C:\Users\7\miniconda3\Scripts\activate.bat qwen_inference
python test_model_selection.py
pause
