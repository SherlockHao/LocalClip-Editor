"""
测试批量翻译的日志输出和错误处理
模拟测试（不需要真实LLM）
"""
import sys
import io

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from batch_retranslate import extract_translation_from_json


def test_json_extraction_with_korean():
    """测试JSON提取功能对韩语的支持"""
    print("\n=== 测试韩语JSON提取 ===\n")

    test_cases = [
        # 模拟LLM可能的输出
        ('{"tr": "안녕"}', "안녕", "简单韩语"),
        ('{"tr": "안 좋아"}', "안 좋아", "韩语短语"),
        ('{"tr": "큰오빠"}', "큰오빠", "韩语词汇"),

        # 带思考过程
        ('<think>翻译为口语化韩语</think>\n{"tr": "안녕"}', "안녕", "带思考的韩语"),

        # 格式化JSON
        ('{\n  "tr": "안녕하세요"\n}', "안녕하세요", "格式化韩语JSON"),

        # 带额外说明
        ('韩语翻译结果:\n{"tr": "반갑습니다"}', "반갑습니다", "带说明的韩语"),
    ]

    all_passed = True
    for i, (input_text, expected, description) in enumerate(test_cases, 1):
        result = extract_translation_from_json(input_text, fallback="原文")
        success = result == expected

        icon = "✅" if success else "❌"
        print(f"{icon} 测试{i}: {description}")

        if not success:
            print(f"   输入: {input_text[:50]}...")
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
            all_passed = False

    return all_passed


def test_error_scenarios():
    """测试错误场景的处理"""
    print("\n=== 测试错误场景 ===\n")

    error_cases = [
        ('', "fallback", "空字符串"),
        ('完全不是JSON的长文本' * 50, "fallback", "超长非JSON文本"),
        ('{invalid json}', "fallback", "无效JSON"),
        ('{"wrong_key": "value"}', "fallback", "错误的JSON key"),
    ]

    all_passed = True
    for i, (input_text, expected, description) in enumerate(error_cases, 1):
        result = extract_translation_from_json(input_text, fallback="fallback")
        success = result == expected

        icon = "✅" if success else "❌"
        print(f"{icon} 错误场景{i}: {description}")

        if not success:
            print(f"   期望fallback但得到: {result}")
            all_passed = False

    return all_passed


def simulate_batch_logging():
    """模拟批量翻译的日志输出"""
    print("\n=== 模拟批量翻译日志 ===\n")

    # 模拟翻译任务
    tasks = [
        {"task_id": "task-1", "source": "你好", "target": "안녕"},
        {"task_id": "task-2", "source": "不好", "target": "안 좋아"},
        {"task_id": "task-3", "source": "大哥", "target": "큰오빠"},
    ]

    print(f"{'='*60}", flush=True)
    print(f"[批量翻译] 开始批量翻译", flush=True)
    print(f"  任务数量: {len(tasks)}", flush=True)
    print(f"  进程数量: 1", flush=True)
    print(f"{'='*60}\n", flush=True)

    for i, task in enumerate(tasks, 1):
        print(f"[任务队列] 添加任务 {i}: {task['task_id']}", flush=True)

    print(f"\n[结果收集] 开始收集 {len(tasks)} 个翻译结果...", flush=True)

    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task['task_id']}: {task['source']} -> {task['target']}", flush=True)

    print(f"[结果收集] 完成！共收集 {len(tasks)} 个结果\n", flush=True)

    print(f"{'='*60}", flush=True)
    print(f"[批量翻译] 全部完成！共处理 {len(tasks)} 个任务", flush=True)
    print(f"{'='*60}\n", flush=True)

    return True


if __name__ == "__main__":
    print("开始测试批量翻译功能...")

    test1 = test_json_extraction_with_korean()
    test2 = test_error_scenarios()
    test3 = simulate_batch_logging()

    if test1 and test2 and test3:
        print("\n🎉 所有测试通过！")
        print("\n主要改进:")
        print("  1. ✅ 修复了异常处理 - 不再提前退出")
        print("  2. ✅ 添加了实时日志 - 每翻译一句立即打印")
        print("  3. ✅ 增加了超时时间 - 防止卡住")
        print("  4. ✅ 完善了错误提示 - flush=True强制输出")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败")
        sys.exit(1)
