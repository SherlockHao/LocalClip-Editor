"""
简单翻译测试 - 验证模型加载和翻译功能
需要在 qwen_inference 环境中运行
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
print("简单翻译测试")
print("="*70)

# 添加路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from batch_retranslate import retranslate_from_config
    print("✅ 已导入 batch_retranslate 模块")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("⚠️  请在 qwen_inference 环境中运行:")
    print("     conda activate qwen_inference")
    print("     python test_translation_simple.py")
    sys.exit(1)

# 创建简单的翻译任务
print("\n[测试任务]")
print("原文: 你好")
print("目标语言: 韩文")
print("")

test_config = {
    "tasks": [
        {
            "task_id": "simple-test-1",
            "source": "你好",
            "target_language": "韩文"
        }
    ],
    "num_processes": 1
}

# 创建临时配置文件
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json.dump(test_config, f, ensure_ascii=False, indent=2)
    config_file = f.name

print(f"配置文件: {config_file}")
print("")

try:
    print("="*70)
    print("开始翻译...")
    print("="*70 + "\n")

    # 执行翻译
    results = retranslate_from_config(config_file)

    print("\n" + "="*70)
    print("翻译结果")
    print("="*70)

    if results and len(results) > 0:
        for result in results:
            print(f"\n任务ID: {result.get('task_id')}")
            print(f"原文: {result.get('source')}")
            print(f"译文: {result.get('translation')}")
            print(f"状态: {'✅ 成功' if result.get('success') else '❌ 失败'}")

            if not result.get('success'):
                print(f"错误: {result.get('error')}")

        print("\n✅ 翻译测试完成")
    else:
        print("\n❌ 没有返回结果")

except Exception as e:
    print(f"\n❌ 翻译失败: {e}")
    import traceback
    traceback.print_exc()

finally:
    # 清理临时文件
    try:
        os.unlink(config_file)
        print(f"\n已清理临时配置文件")
    except:
        pass

    print("\n" + "="*70)
    print("测试结束")
    print("="*70 + "\n")
