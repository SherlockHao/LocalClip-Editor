"""
简单测试批量重新翻译脚本
不加载 LLM，只测试基本的脚本执行流程
"""
import os
import sys
import json

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_import():
    """测试是否能导入模块"""
    try:
        import batch_retranslate
        print("[OK] batch_retranslate 模块导入成功")
        return True
    except Exception as e:
        print(f"[ERROR] 无法导入 batch_retranslate: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_parse():
    """测试配置文件解析"""
    config_file = "test_retranslate_config.json"

    if not os.path.exists(config_file):
        print(f"[ERROR] 配置文件不存在: {config_file}")
        return False

    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        print("[OK] 配置文件解析成功")
        print(f"     任务数: {len(config['tasks'])}")
        print(f"     模型路径: {config['model_path']}")
        print(f"     进程数: {config['num_processes']}")

        return True
    except Exception as e:
        print(f"[ERROR] 配置文件解析失败: {e}")
        return False


def test_python_env():
    """测试 Python 环境"""
    qwen_env_python = os.environ.get("QWEN_INFERENCE_PYTHON")
    if not qwen_env_python:
        import platform
        if platform.system() == "Windows":
            qwen_env_python = r"C:\Users\7\miniconda3\envs\qwen_inference\python.exe"
        else:
            qwen_env_python = os.path.expanduser("~/miniconda3/envs/qwen_inference/bin/python")

    print(f"[INFO] Qwen Python 路径: {qwen_env_python}")

    if os.path.exists(qwen_env_python):
        print("[OK] Qwen Python 环境存在")
        return True
    else:
        print("[ERROR] Qwen Python 环境不存在")
        return False


def test_model_path():
    """测试模型路径"""
    # 模拟 main.py 中的路径计算
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    localclip_dir = os.path.dirname(backend_dir)
    workspace_dir = os.path.dirname(localclip_dir)
    ai_editing_dir = os.path.dirname(workspace_dir)
    model_path = os.path.join(ai_editing_dir, "models", "Qwen3-1.7B")

    print(f"[INFO] 计算的模型路径: {model_path}")

    if os.path.exists(model_path):
        print("[OK] 模型路径存在")
        return True
    else:
        print("[ERROR] 模型路径不存在")
        return False


def main():
    print("=" * 60)
    print("批量重新翻译 - 简单测试")
    print("=" * 60)

    tests = [
        ("Python 环境检查", test_python_env),
        ("模型路径检查", test_model_path),
        ("模块导入测试", test_import),
        ("配置解析测试", test_config_parse),
    ]

    results = []
    for name, test_func in tests:
        print(f"\n[测试] {name}")
        print("-" * 60)
        result = test_func()
        results.append((name, result))
        print()

    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {name}")

    all_pass = all(r for _, r in results)
    print()
    print(f"总体结果: {'全部通过' if all_pass else '部分失败'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
