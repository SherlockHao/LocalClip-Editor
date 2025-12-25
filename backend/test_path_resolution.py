"""
测试模型路径解析
"""
import os
import sys

print("\n" + "="*70)
print("测试模型路径解析")
print("="*70 + "\n")

# 当前脚本位置
current_file = os.path.abspath(__file__)
print(f"当前文件: {current_file}")

# 模拟 batch_retranslate.py 的路径计算
backend_dir = os.path.dirname(current_file)
print(f"backend目录: {backend_dir}")

localclip_dir = os.path.dirname(backend_dir)
print(f"LocalClip-Editor目录: {localclip_dir}")

workspace_dir = os.path.dirname(localclip_dir)
print(f"workspace目录: {workspace_dir}")

ai_editing_dir = os.path.dirname(workspace_dir)
print(f"ai_editing目录: {ai_editing_dir}")

models_dir = os.path.join(ai_editing_dir, "models")
print(f"models目录: {models_dir}")

# 检查目录是否存在
print("\n" + "="*70)
print("目录存在性检查")
print("="*70 + "\n")

if os.path.exists(models_dir):
    print(f"✅ models目录存在: {models_dir}")

    # 列出模型
    print("\n可用模型:")
    try:
        for item in os.listdir(models_dir):
            item_path = os.path.join(models_dir, item)
            if os.path.isdir(item_path) and "Qwen" in item:
                print(f"  ✓ {item}")
    except Exception as e:
        print(f"  ❌ 列出目录失败: {e}")
else:
    print(f"❌ models目录不存在: {models_dir}")

# 检查特定模型
print("\n" + "="*70)
print("检查Qwen模型")
print("="*70 + "\n")

models_to_check = ["Qwen3-4B-FP8", "Qwen3-1.7B"]

for model_name in models_to_check:
    model_path = os.path.join(models_dir, model_name)
    exists = os.path.exists(model_path)
    status = "✅ 存在" if exists else "❌ 不存在"
    print(f"{status}: {model_path}")

    if exists:
        # 检查关键文件
        required_files = ["config.json", "tokenizer_config.json"]
        for file in required_files:
            file_path = os.path.join(model_path, file)
            if os.path.exists(file_path):
                print(f"    ✓ {file}")
            else:
                print(f"    ✗ {file}")

print("\n" + "="*70)
print("✅ 路径解析测试完成")
print("="*70 + "\n")
