"""
测试GPU显存检测和模型选择功能
"""
import sys
import os
import io

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加父目录到路径以便导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from batch_retranslate import get_gpu_memory_gb, select_model_by_gpu


def test_gpu_detection():
    """测试GPU显存检测"""
    print("\n" + "="*60)
    print("测试GPU显存检测")
    print("="*60)

    available_memory = get_gpu_memory_gb()

    if available_memory > 0:
        print(f"\n✅ GPU检测成功，可用显存: {available_memory:.2f} GB")
    else:
        print("\n⚠️  未检测到GPU或显存不足")

    return available_memory


def test_model_selection():
    """测试模型选择逻辑"""
    print("\n" + "="*60)
    print("测试模型选择")
    print("="*60)

    # 获取模型目录
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    localclip_dir = os.path.dirname(backend_dir)
    workspace_dir = os.path.dirname(localclip_dir)
    ai_editing_dir = os.path.dirname(workspace_dir)
    models_dir = os.path.join(ai_editing_dir, "models")

    print(f"\n模型目录: {models_dir}")

    # 检查模型目录是否存在
    if not os.path.exists(models_dir):
        print(f"❌ 模型目录不存在: {models_dir}")
        return None

    # 列出可用模型
    print("\n可用模型:")
    available_models = []
    for model_name in ["Qwen3-4B-FP8", "Qwen3-4B", "Qwen3-1.7B"]:
        model_path = os.path.join(models_dir, model_name)
        exists = os.path.exists(model_path)
        status = "✓" if exists else "✗"
        print(f"  {status} {model_name}")
        if exists:
            available_models.append(model_name)

    if not available_models:
        print("\n⚠️  没有找到任何可用模型")
        return None

    # 执行模型选择
    print("\n" + "-"*60)
    selected_model = select_model_by_gpu(models_dir)
    print("-"*60)

    print(f"\n✅ 选择的模型路径: {selected_model}")
    print(f"   模型名称: {os.path.basename(selected_model)}")

    return selected_model


def main():
    """主测试函数"""
    print("\n🔍 开始测试模型选择功能...\n")

    # 测试1: GPU检测
    available_memory = test_gpu_detection()

    # 测试2: 模型选择
    selected_model = test_model_selection()

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    if available_memory > 0:
        print(f"✅ GPU可用显存: {available_memory:.2f} GB")
    else:
        print("⚠️  GPU显存不足或不可用")

    if selected_model:
        print(f"✅ 已选择模型: {os.path.basename(selected_model)}")

        # 根据选择的模型给出建议
        model_name = os.path.basename(selected_model)
        if model_name == "Qwen3-4B-FP8":
            print("\n💡 建议: 使用 Qwen3-4B-FP8 可以获得最佳翻译质量")
        elif model_name == "Qwen3-4B":
            print("\n💡 建议: 使用 Qwen3-4B 可以获得很好的翻译质量")
        elif model_name == "Qwen3-1.7B":
            print("\n💡 建议: Qwen3-1.7B 是回退模型，如需更好质量请考虑升级GPU")
    else:
        print("❌ 未能选择模型")

    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
