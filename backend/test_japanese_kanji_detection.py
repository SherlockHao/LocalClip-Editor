# -*- coding: utf-8 -*-
"""
测试日语汉字检测功能
验证系统能够检测到日文译文中的汉字，并触发重新翻译
"""

from text_utils import contains_chinese_characters


def test_contains_chinese_characters():
    """测试汉字检测函数"""
    print("=" * 60)
    print("日语汉字检测测试")
    print("=" * 60)

    test_cases = [
        # (文本, 是否包含汉字, 描述)
        ("こんにちは", False, "纯平假名"),
        ("カタカナ", False, "纯片假名"),
        ("ひらがなとカタカナ", False, "平假名+片假名混合"),
        ("日本語", True, "包含汉字"),
        ("今日はいい天気ですね", True, "假名+汉字混合"),
        ("こんにちは、世界！", True, "假名+汉字（'世界'）"),
        ("きょう", False, "纯假名（'今天'的假名写法）"),
        ("今日", True, "纯汉字"),
        ("ごはん", False, "假名（'饭'的假名写法）"),
        ("食事", True, "汉字（'饭'的汉字写法）"),
        ("きれい", False, "假名（'漂亮'的假名写法）"),
        ("綺麗", True, "汉字（'漂亮'的汉字写法）"),
        ("Hello", False, "英文"),
        ("123", False, "数字"),
        ("Hello世界", True, "英文+汉字"),
    ]

    print("\n测试结果：\n")

    passed = 0
    failed = 0

    for text, expected, description in test_cases:
        result = contains_chinese_characters(text)
        status = "OK" if result == expected else "FAIL"

        if status == "OK":
            passed += 1
        else:
            failed += 1

        print(f"{status:4s} | '{text:20s}' | 包含汉字: {str(result):5s} | 期望: {str(expected):5s} | {description}")

    print("\n" + "=" * 60)
    print(f"测试完成: 通过 {passed} / 失败 {failed} / 总计 {len(test_cases)}")
    print("=" * 60)


def test_japanese_retranslation_logic():
    """测试日语重新翻译逻辑"""
    print("\n" + "=" * 60)
    print("日语重新翻译逻辑测试")
    print("=" * 60)

    # 模拟 main.py 中的逻辑
    def should_retranslate(target_language: str, target_text: str, is_too_long: bool) -> tuple:
        """判断是否需要重新翻译"""
        needs_retranslation = is_too_long

        # 日语特殊规则：如果译文中包含汉字，需要重新翻译
        reason = ""
        if not needs_retranslation:
            target_language_lower = target_language.lower()
            is_japanese = ('日' in target_language or 'ja' in target_language_lower)
            if is_japanese and contains_chinese_characters(target_text):
                needs_retranslation = True
                reason = "包含汉字"
        else:
            reason = "超长"

        return needs_retranslation, reason

    test_cases = [
        # (目标语言, 译文, 是否超长, 期望是否重新翻译, 描述)
        ("日语", "こんにちは", False, False, "日语纯假名，不超长 → 不需要"),
        ("日语", "今日はいい天気ですね", False, True, "日语包含汉字 → 需要重新翻译"),
        ("日语", "きょうはいいてんきですね", False, False, "日语纯假名 → 不需要"),
        ("日语", "世界", False, True, "日语纯汉字 → 需要重新翻译"),
        ("ja", "こんにちは", False, False, "日语代码，纯假名 → 不需要"),
        ("ja", "日本", False, True, "日语代码，包含汉字 → 需要重新翻译"),
        ("英语", "Hello world", False, False, "英语 → 不需要"),
        ("英语", "Hello 世界", False, False, "英语包含汉字（不触发日语规则） → 不需要"),
        ("韩语", "안녕하세요", False, False, "韩语 → 不需要"),
        ("日语", "非常に長いテキストで超長", True, True, "日语超长 → 需要重新翻译"),
    ]

    print("\n测试结果：\n")

    passed = 0
    failed = 0

    for target_language, target_text, is_too_long, expected, description in test_cases:
        needs_retranslation, reason = should_retranslate(target_language, target_text, is_too_long)
        status = "OK" if needs_retranslation == expected else "FAIL"

        if status == "OK":
            passed += 1
        else:
            failed += 1

        reason_str = f"({reason})" if reason else ""
        print(f"{status:4s} | {target_language:6s} | '{target_text:25s}' | 重新翻译: {str(needs_retranslation):5s} {reason_str:8s} | {description}")

    print("\n" + "=" * 60)
    print(f"测试完成: 通过 {passed} / 失败 {failed} / 总计 {len(test_cases)}")
    print("=" * 60)


if __name__ == "__main__":
    test_contains_chinese_characters()
    test_japanese_retranslation_logic()

    print("\n" + "=" * 60)
    print("全部测试完成！")
    print("=" * 60)
