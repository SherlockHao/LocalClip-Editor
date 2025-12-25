"""
独立的模型文件检查脚本
"""
import os

def check_model_files(model_path):
    """检查模型文件完整性"""
    required_files = ["config.json", "tokenizer_config.json"]
    
    for file in required_files:
        file_path = os.path.join(model_path, file)
        if not os.path.exists(file_path):
            return False, f"Missing {file}"
        
        if os.path.getsize(file_path) == 0:
            return False, f"{file} is empty"
    
    # 检查模型权重
    has_weights = False
    for file in os.listdir(model_path):
        if file.endswith('.safetensors') or file.endswith('.bin'):
            file_path = os.path.join(model_path, file)
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 10:
                has_weights = True
                break
    
    if not has_weights:
        return False, "No valid weight files (>10MB)"
    
    return True, "OK"

# 测试
backend_dir = os.path.dirname(os.path.abspath(__file__))
localclip_dir = os.path.dirname(backend_dir)
workspace_dir = os.path.dirname(localclip_dir)
ai_editing_dir = os.path.dirname(workspace_dir)
models_dir = os.path.join(ai_editing_dir, "models")

print("="*70)
print("Model File Integrity Check")
print("="*70)
print(f"\nModels directory: {models_dir}\n")

models_to_check = ["Qwen3-1.7B", "Qwen3-4B-FP8", "Qwen3-4B"]

for model_name in models_to_check:
    model_path = os.path.join(models_dir, model_name)
    
    print(f"{model_name}:")
    
    if not os.path.exists(model_path):
        print(f"  Status: NOT FOUND")
        print(f"  Path: {model_path}")
    else:
        is_ok, msg = check_model_files(model_path)
        status = "OK" if is_ok else "CORRUPTED"
        symbol = "✓" if is_ok else "✗"
        
        print(f"  Status: {symbol} {status}")
        if not is_ok:
            print(f"  Reason: {msg}")
        
        # List weight files
        weights = [f for f in os.listdir(model_path) if f.endswith('.safetensors') or f.endswith('.bin')]
        if weights:
            print(f"  Weight files ({len(weights)}):")
            for w in weights[:3]:  # Show first 3
                w_path = os.path.join(model_path, w)
                size_mb = os.path.getsize(w_path) / (1024 * 1024)
                print(f"    - {w} ({size_mb:.1f} MB)")
    print()

print("="*70)
print("Recommendation:")
print("="*70)

# Find working model
for model_name in ["Qwen3-1.7B", "Qwen3-4B-FP8", "Qwen3-4B"]:
    model_path = os.path.join(models_dir, model_name)
    if os.path.exists(model_path):
        is_ok, _ = check_model_files(model_path)
        if is_ok:
            print(f"✓ Use {model_name} (verified working)")
            break
else:
    print("✗ No working model found!")
    print("\nSuggestion:")
    print("  1. Re-download Qwen3-1.7B model")
    print("  2. Or fix the corrupted model files")
