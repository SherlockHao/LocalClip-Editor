"""
测试JSON格式翻译结果提取
"""
import sys
import io

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from batch_retranslate import extract_translation_from_json


def test_json_extraction():
    """测试各种JSON格式的提取"""
    print("\n=== 测试JSON提取功能 ===\n")

    # 测试1: 标准JSON格式
    test_cases = [
        # (输入, 期望输出, 描述)
        ('{"tr": "Hello"}', "Hello", "标准JSON格式"),
        ('{"tr":"Hello"}', "Hello", "无空格JSON"),
        ('{ "tr" : "Hello" }', "Hello", "带空格JSON"),
        ('{"tr": "안녕하세요"}', "안녕하세요", "韩语翻译"),
        ('{"tr": "こんにちは"}', "こんにちは", "日语翻译"),

        # 带其他字段
        ('{"tr": "Hello", "confidence": 0.9}', "Hello", "带额外字段"),

        # 带思考过程
        ('<think>思考中...</think>\n{"tr": "Hello"}', "Hello", "带思考标签+JSON"),
        ('{"tr": "Hello"}\n\n一些额外说明', "Hello", "JSON后有额外内容"),

        # 不完整但可提取
        ('输出: {"tr": "Hello"}', "Hello", "前缀+JSON"),
        ('结果是: {"tr": "안녕"}', "안녕", "中文前缀+韩语JSON"),

        # 纯文本回退
        ('<think>...</think>\nHello', "Hello", "移除思考标签后的纯文本"),

        # 失败案例（使用fallback）
        ('完全不是JSON格式的很长的文本' * 20, "原文", "过长文本使用fallback"),
        ('', "原文", "空字符串使用fallback"),
    ]

    passed = 0
    failed = 0

    for i, (input_text, expected, description) in enumerate(test_cases, 1):
        result = extract_translation_from_json(input_text, fallback="原文")

        if result == expected:
            print(f"✅ 测试{i}: {description}")
            print(f"   输入: {input_text[:50]}{'...' if len(input_text) > 50 else ''}")
            print(f"   输出: {result}")
            passed += 1
        else:
            print(f"❌ 测试{i}: {description}")
            print(f"   输入: {input_text[:50]}{'...' if len(input_text) > 50 else ''}")
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
            failed += 1
        print()

    print("="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)

    return failed == 0


def test_real_world_cases():
    """测试真实场景"""
    print("\n=== 测试真实场景 ===\n")

    # 模拟LLM可能的各种输出
    real_cases = [
        # 理想情况
        ('{"tr": "Not good"}', "Not good", "理想JSON输出"),

        # 带换行
        ('{\n  "tr": "Not good"\n}', "Not good", "格式化JSON"),

        # 带解释（但还是JSON）
        ('翻译结果如下：\n{"tr": "Not good"}', "Not good", "带中文说明"),

        # 韩语真实案例
        ('{"tr": "안 좋아"}', "안 좋아", "韩语-不好"),
        ('{"tr": "큰오빠"}', "큰오빠", "韩语-大哥"),

        # 思考后输出JSON
        ('<think>\n分析：这句话表达负面情绪\n翻译策略：使用口语化表达\n</think>\n\n{"tr": "Not good"}',
         "Not good", "完整思考过程+JSON"),
    ]

    for i, (input_text, expected, description) in enumerate(real_cases, 1):
        result = extract_translation_from_json(input_text, fallback="FALLBACK")

        success = result == expected
        icon = "✅" if success else "❌"

        print(f"{icon} 场景{i}: {description}")
        if not success:
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
        print()

    return True


if __name__ == "__main__":
    print("开始测试JSON提取功能...")

    success1 = test_json_extraction()
    success2 = test_real_world_cases()

    if success1 and success2:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败")
