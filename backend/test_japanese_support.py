# -*- coding: utf-8 -*-
"""
测试日语支持
验证日语文本处理和翻译功能
"""

from text_utils import (
    normalize_japanese,
    count_japanese_length,
    count_text_length,
    check_translation_length
)


def test_normalize_japanese():
    """测试日语文本规范化"""
    print("\n=== 测试日语文本规范化 ===")

    test_cases = [
        ("こんにちは！", "こんにちは"),  # 平假名 + 标点
        ("カタカナ", "カタカナ"),  # 片假名
        ("日本語", "日本語"),  # 汉字
        ("こんにちは、世界！", "こんにちは世界"),  # 混合 + 标点
        ("Hello こんにちは 123", "こんにちは"),  # 混合英文和数字
        ("これは　テスト　です。", "これはテストです"),  # 全角空格
    ]

    for original, expected in test_cases:
        result = normalize_japanese(original)
        status = "OK" if result == expected else "FAIL"
        print(f"{status} '{original}' -> '{result}' (期望: '{expected}')")


def test_count_japanese_length():
    """测试日语文本长度计算"""
    print("\n=== 测试日语文本长度计算 ===")

    test_cases = [
        ("こんにちは", 5),  # 平假名
        ("カタカナ", 4),  # 片假名
        ("日本語", 3),  # 汉字
        ("こんにちは、世界！", 8),  # 混合（标点被移除）
        ("これは　テスト　です。", 10),  # 全角空格（被移除）
    ]

    for text, expected in test_cases:
        result = count_japanese_length(text)
        status = "OK" if result == expected else "FAIL"
        print(f"{status} '{text}' -> {result} (期望: {expected})")


def test_count_text_length_with_language():
    """测试根据语言类型计算长度"""
    print("\n=== 测试多语言长度计算 ===")

    test_cases = [
        ("こんにちは", "ja", 5),
        ("こんにちは", "日语", 5),
        ("こんにちは", "Japanese", 5),
        ("안녕하세요", "ko", 5),
        ("안녕하세요", "韩语", 5),
        ("Hello world", "en", 2),
        ("Hello world", "英语", 2),
        ("你好世界", "zh", 4),
    ]

    for text, language, expected in test_cases:
        result = count_text_length(text, language)
        status = "OK" if result == expected else "FAIL"
        print(f"{status} '{text}' ({language}) -> {result} (期望: {expected})")


def test_check_translation_length():
    """测试翻译长度检查"""
    print("\n=== 测试翻译长度检查 ===")

    test_cases = [
        # (原文, 译文, 目标语言, 最大比例, 是否超长)
        ("你好", "こんにちは", "日语", 1.2, False),  # 2:5 = 2.5 > 1.2，应该超长
        ("你好世界", "こんにちは世界", "日语", 1.2, False),  # 4:7 = 1.75 > 1.2，应该超长
        ("你好", "こんにちは", "日语", 3.0, False),  # 2:5 = 2.5 < 3.0，不超长
        ("今天天气真不错", "今日は本当にいい天気ですね", "ja", 2.0, False),  # 7:14 = 2.0，刚好
    ]

    for source, target, language, max_ratio, expected_too_long in test_cases:
        is_too_long, source_len, target_len, ratio = check_translation_length(
            source, target, language, max_ratio
        )
        status = "OK" if is_too_long == expected_too_long else "FAIL"
        print(f"{status} '{source}' -> '{target}' ({language})")
        print(f"   长度: {source_len} -> {target_len}, 比例: {ratio:.2f}, 最大: {max_ratio}")
        print(f"   超长: {is_too_long} (期望: {expected_too_long})")


def test_language_code_mapping():
    """测试语言代码映射"""
    print("\n=== 测试语言代码映射 ===")

    # 导入 main.py 中的函数
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    from main import get_language_name

    test_cases = [
        ("en", "英语"),
        ("EN", "英语"),
        ("ko", "韩语"),
        ("KO", "韩语"),
        ("ja", "日语"),
        ("JA", "日语"),
        ("zh", "zh"),  # 不在映射表中，返回原值
    ]

    for code, expected in test_cases:
        result = get_language_name(code)
        status = "OK" if result == expected else "FAIL"
        print(f"{status} '{code}' -> '{result}' (期望: '{expected}')")


if __name__ == "__main__":
    print("=" * 60)
    print("日语支持测试")
    print("=" * 60)

    test_normalize_japanese()
    test_count_japanese_length()
    test_count_text_length_with_language()
    test_check_translation_length()
    test_language_code_mapping()

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
