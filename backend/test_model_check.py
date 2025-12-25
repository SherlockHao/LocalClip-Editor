import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
localclip_dir = os.path.dirname(backend_dir)
workspace_dir = os.path.dirname(localclip_dir)
ai_editing_dir = os.path.dirname(workspace_dir)
models_dir = os.path.join(ai_editing_dir, "models")

print(f"Models directory: {models_dir}\n")

# 导入函数
sys.path.insert(0, backend_dir)
from batch_retranslate import check_model_files

# 检查模型
models_to_check = ["Qwen3-1.7B", "Qwen3-4B-FP8"]

for model_name in models_to_check:
    model_path = os.path.join(models_dir, model_name)
    
    if os.path.exists(model_path):
        is_ok = check_model_files(model_path)
        status = "OK" if is_ok else "CORRUPTED"
        print(f"{model_name}: {status}")
        
        if not is_ok:
            print(f"  - Checking files in {model_path}:")
            for file in ["config.json", "tokenizer_config.json"]:
                file_path = os.path.join(model_path, file)
                exists = os.path.exists(file_path)
                if exists:
                    size = os.path.getsize(file_path)
                    print(f"    {file}: {size} bytes")
                else:
                    print(f"    {file}: MISSING")
    else:
        print(f"{model_name}: NOT FOUND")
