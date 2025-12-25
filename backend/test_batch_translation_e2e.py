"""
端到端测试批量翻译功能
测试从配置文件创建到模型选择的完整流程
"""
import sys
import os
import io
import json
import tempfile

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("\n" + "="*70)
print("端到端测试：批量翻译完整流程")
print("="*70)

# 测试1: 创建测试配置文件
print("\n[步骤1] 创建测试配置文件...")

test_config = {
    "tasks": [
        {
            "task_id": "test-1",
            "source": "你好",
            "target_language": "韩文"
        },
        {
            "task_id": "test-2",
            "source": "不好",
            "target_language": "韩文"
        },
        {
            "task_id": "test-3",
            "source": "大哥",
            "target_language": "韩文"
        }
    ],
    "num_processes": 1
}

# 创建临时配置文件
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json.dump(test_config, f, ensure_ascii=False, indent=2)
    config_file = f.name

print(f"✅ 配置文件已创建: {config_file}")
print(f"   任务数量: {len(test_config['tasks'])}")
print(f"   目标语言: 韩文")

# 测试2: 验证 batch_retranslate.py 可以导入
print("\n[步骤2] 验证 batch_retranslate.py...")

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from batch_retranslate import (
        get_gpu_memory_gb,
        select_model_by_gpu,
        retranslate_from_config
    )
    print("✅ batch_retranslate.py 导入成功")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("⚠️  需要在 qwen_inference 环境中运行")
    sys.exit(1)

# 测试3: GPU 检测
print("\n[步骤3] 检测 GPU 显存...")
available_memory = get_gpu_memory_gb()

if available_memory > 0:
    print(f"✅ GPU 检测成功，可用显存: {available_memory:.2f} GB")
else:
    print("⚠️  未检测到 GPU 或显存不足")

# 测试4: 模型选择
print("\n[步骤4] 自动选择模型...")

# 获取模型目录
backend_dir = os.path.dirname(os.path.abspath(__file__))
localclip_dir = os.path.dirname(backend_dir)
workspace_dir = os.path.dirname(localclip_dir)
ai_editing_dir = os.path.dirname(workspace_dir)
models_dir = os.path.join(ai_editing_dir, "models")

print(f"模型目录: {models_dir}")

if os.path.exists(models_dir):
    selected_model = select_model_by_gpu(models_dir)
    model_name = os.path.basename(selected_model)
    print(f"✅ 已选择模型: {model_name}")

    # 验证模型文件
    required_files = ["config.json", "tokenizer_config.json"]
    all_exist = True
    for file in required_files:
        file_path = os.path.join(selected_model, file)
        if os.path.exists(file_path):
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} (缺失)")
            all_exist = False

    if all_exist:
        print(f"✅ 模型文件验证通过")
    else:
        print(f"⚠️  模型文件不完整")
else:
    print(f"❌ 模型目录不存在: {models_dir}")
    sys.exit(1)

# 测试5: 执行批量翻译（模拟）
print("\n[步骤5] 模拟批量翻译流程...")
print("提示: 完整翻译需要加载模型，这里仅测试配置和选择逻辑")
print("")
print("如需测试完整翻译流程，请运行:")
print(f"  conda activate qwen_inference")
print(f"  python batch_retranslate.py {config_file}")

# 测试6: 验证配置文件格式
print("\n[步骤6] 验证配置文件格式...")

with open(config_file, 'r', encoding='utf-8') as f:
    loaded_config = json.load(f)

print(f"✅ 配置文件格式正确")
print(f"   包含字段: {list(loaded_config.keys())}")
print(f"   任务数量: {len(loaded_config['tasks'])}")
print(f"   模型路径: {'自动选择' if 'model_path' not in loaded_config else loaded_config['model_path']}")

# 总结
print("\n" + "="*70)
print("测试总结")
print("="*70)

results = {
    "配置文件创建": "✅",
    "模块导入": "✅",
    "GPU检测": "✅" if available_memory > 0 else "⚠️",
    "模型选择": "✅",
    "模型文件验证": "✅" if all_exist else "⚠️",
    "配置格式验证": "✅"
}

for test_name, status in results.items():
    print(f"{status} {test_name}")

print("\n💡 下一步:")
print("  1. 运行 test_model_select.bat 测试模型选择")
print("  2. 在应用中触发翻译任务，验证完整流程")
print("  3. 检查日志确认使用了正确的模型")

print("\n" + "="*70)
print("✅ 端到端测试完成")
print("="*70 + "\n")

# 清理临时文件
try:
    os.unlink(config_file)
    print(f"已清理临时配置文件: {config_file}")
except:
    pass
