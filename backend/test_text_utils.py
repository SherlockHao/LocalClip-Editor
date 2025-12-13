"""
测试文本工具模块
验证文本规范化、长度计算功能
"""
from text_utils import (
    normalize_chinese,
    normalize_english,
    count_chinese_length,
    count_english_length,
    count_text_length,
    check_translation_length,
    validate_translations
)


def test_normalize_chinese():
    """测试中文规范化"""
    print("=" * 60)
    print("测试中文规范化")
    print("=" * 60)

    test_cases = [
        ("你好，世界！", "你好世界"),
        ("这是一个测试。", "这是一个测试"),
        ("早上好！！！", "早上好"),
        ("123你好abc世界", "你好世界"),
        ("  空格  测试  ", "空格测试"),
    ]

    for original, expected in test_cases:
        result = normalize_chinese(original)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} '{original}' -> '{result}' (期望: '{expected}')")

    print()


def test_normalize_english():
    """测试英文规范化"""
    print("=" * 60)
    print("测试英文规范化")
    print("=" * 60)

    test_cases = [
        ("Hello, world!", "Hello world"),
        ("I'm testing this.", "Im testing this"),
        ("Don't worry, it's fine!", "Dont worry its fine"),
        ("  Multiple   spaces  ", "Multiple spaces"),
        ("123abc456", "123abc456"),
        ("You're welcome! I'll help.", "Youre welcome Ill help"),
    ]

    for original, expected in test_cases:
        result = normalize_english(original)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} '{original}' -> '{result}' (期望: '{expected}')")

    print()


def test_count_length():
    """测试长度计算"""
    print("=" * 60)
    print("测试长度计算")
    print("=" * 60)

    # 中文测试
    print("\n中文长度测试:")
    chinese_tests = [
        ("你好世界", 4),
        ("这是一个测试", 6),
        ("早上好", 3),
        ("你好，世界！", 4),  # 标点会被移除
    ]

    for text, expected in chinese_tests:
        result = count_chinese_length(text)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} '{text}' -> {result} 字 (期望: {expected})")

    # 英文测试
    print("\n英文长度测试:")
    english_tests = [
        ("Hello world", 2),
        ("This is a test", 4),
        ("I'm testing this", 3),  # I'm 算一个词
        ("Don't worry", 2),  # Don't 算一个词
        ("Good morning everyone", 3),
    ]

    for text, expected in english_tests:
        result = count_english_length(text)
        status = "[PASS]" if result == expected else "[FAIL]"
        print(f"{status} '{text}' -> {result} 词 (期望: {expected})")

    print()


def test_check_translation_length():
    """测试译文长度检查"""
    print("=" * 60)
    print("测试译文长度检查")
    print("=" * 60)

    test_cases = [
        # (原文, 译文, 目标语言, 是否超长)
        ("你好世界", "Hello world", "英文", False),  # 4字 -> 2词 = 0.5x ✅
        ("这是一个测试", "This is a test", "英文", False),  # 6字 -> 4词 = 0.67x ✅
        ("早上好", "Good morning", "英文", False),  # 3字 -> 2词 = 0.67x ✅
        ("欢迎", "Welcome to use our system", "英文", True),  # 2字 -> 5词 = 2.5x ❌
        ("谢谢", "Thank you very much for your help", "英文", True),  # 2字 -> 7词 = 3.5x ❌
    ]

    for source, target, language, should_be_long in test_cases:
        is_too_long, source_len, target_len, ratio = check_translation_length(
            source, target, language, max_ratio=1.2
        )

        if is_too_long == should_be_long:
            status = "[PASS]"
        else:
            status = "[FAIL]"

        result_str = "超长" if is_too_long else "合格"
        expected_str = "超长" if should_be_long else "合格"

        print(f"{status} '{source}' ({source_len}字) -> '{target}' ({target_len}词)")
        print(f"   比例: {ratio:.2f}x | 结果: {result_str} | 期望: {expected_str}")

    print()


def test_validate_translations():
    """测试批量验证"""
    print("=" * 60)
    print("测试批量验证")
    print("=" * 60)

    translations = [
        {"id": 1, "source": "你好", "target": "Hello"},
        {"id": 2, "source": "早上好", "target": "Good morning"},
        {"id": 3, "source": "谢谢", "target": "Thank you very much for everything"},
        {"id": 4, "source": "再见", "target": "Goodbye"},
        {"id": 5, "source": "欢迎", "target": "Welcome to our amazing platform"},
    ]

    valid, too_long = validate_translations(translations, "英文", max_ratio=1.2)

    print(f"\n合格译文: {len(valid)} 条")
    for item in valid:
        print(f"  [{item['id']}] '{item['source']}' -> '{item['target']}'")
        print(f"       {item['source_length']}字 -> {item['target_length']}词 = {item['length_ratio']:.2f}x")

    print(f"\n超长译文: {len(too_long)} 条")
    for item in too_long:
        print(f"  [{item['id']}] '{item['source']}' -> '{item['target']}'")
        print(f"       {item['source_length']}字 -> {item['target_length']}词 = {item['length_ratio']:.2f}x [TOO_LONG]")

    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("文本工具模块测试")
    print("=" * 60 + "\n")

    test_normalize_chinese()
    test_normalize_english()
    test_count_length()
    test_check_translation_length()
    test_validate_translations()

    print("=" * 60)
    print("所有测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
