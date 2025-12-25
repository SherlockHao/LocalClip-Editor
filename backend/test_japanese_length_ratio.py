# -*- coding: utf-8 -*-
"""
测试日语翻译长度比例限制
验证日语使用1.8倍而非1.2倍的限制
"""
import sys
import io

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from text_utils import check_translation_length


def test_japanese_length_ratio():
    """测试日语和其他语言的长度比例限制"""
    print("=" * 70)
    print("日语翻译长度比例测试")
    print("=" * 70)

    test_cases = [
        # (原文, 译文, 语言, max_ratio, 期望是否超长, 描述)

        # 日语测试（使用2.5倍限制）
        ("你好", "こんにちは", "日语", 2.5, False, "日语-正常长度 (2:5=2.5 = 2.5倍边界)"),
        ("你好", "こんにちは", "ja", 2.5, False, "日语-正常长度 (ja代码)"),
        ("今天", "きょう", "日语", 2.5, False, "日语-假名 (2:3=1.5 < 2.5倍)"),
        ("今天天气好", "きょうはいいてんきですね", "日语", 2.5, False, "日语-正常 (5:12=2.4 < 2.5倍)"),
        ("我", "わたし", "日语", 2.5, True, "日语-超长 (1:3=3.0 > 2.5倍)"),
        ("你好啊", "こんにちは", "日语", 2.5, False, "日语-常见问候 (3:5=1.67 < 2.5倍)"),

        # 如果用1.2倍限制（旧限制），这些应该被误判为超长
        ("你好", "こんにちは", "日语", 1.2, True, "用1.2倍会误判-こんにちは (2:5=2.5 > 1.2)"),
        ("吃饭", "ごはんをたべる", "日语", 1.2, True, "用1.2倍会误判-ごはんをたべる (2:7=3.5 > 1.2)"),

        # 英语测试（使用1.2倍限制）
        ("你好", "Hello", "英语", 1.2, False, "英语-正常 (2:1=0.5 < 1.2倍)"),
        ("今天天气好", "Nice weather today", "English", 1.2, False, "英语-正常 (5:3=0.6 < 1.2倍)"),
        ("你好", "Hello there my friend", "英语", 1.2, True, "英语-超长 (2:4=2.0 > 1.2倍)"),

        # 韩语测试（使用2.5倍限制）
        ("你好", "안녕하세요", "韩语", 2.5, False, "韩语-正常 (2:5=2.5 = 2.5倍边界)"),
        ("吃饭", "밥먹어", "ko", 2.5, False, "韩语-正常 (2:3=1.5 < 2.5倍)"),
    ]

    print("\n测试结果：\n")

    passed = 0
    failed = 0

    for source, target, language, max_ratio, expected_too_long, description in test_cases:
        is_too_long, source_len, target_len, ratio = check_translation_length(
            source, target, language, max_ratio=max_ratio
        )

        status = "PASS" if is_too_long == expected_too_long else "FAIL"
        icon = "✓" if status == "PASS" else "✗"

        if status == "PASS":
            passed += 1
        else:
            failed += 1

        print(f"{icon} [{status}] {description}")
        print(f"  原文: '{source}' ({source_len}) -> 译文: '{target}' ({target_len})")
        print(f"  比例: {ratio:.2f} / 限制: {max_ratio} / 超长: {is_too_long} (期望: {expected_too_long})")

        if status == "FAIL":
            print(f"  ❌ 测试失败！")
        print()

    print("=" * 70)
    print(f"测试完成: ✓ {passed} 通过 | ✗ {failed} 失败 | 总计 {len(test_cases)}")
    print("=" * 70)

    return failed == 0


def test_real_world_japanese_examples():
    """测试真实日语翻译案例"""
    print("\n" + "=" * 70)
    print("真实日语翻译案例")
    print("=" * 70)

    real_cases = [
        # (原文, 译文, 描述)
        ("我打断他的腿", "オレノモモヲオル", "片假名翻译"),
        ("你好啊", "こんにちは", "常见问候"),
        ("今天天气真好", "きょうはほんとうにいいてんきですね", "完整句子-假名"),
        ("吃饭了吗", "ごはんたべた", "口语化"),
        ("我是你大哥", "オレハキミノアニキダ", "片假名翻译"),
    ]

    print("\n使用新的2.5倍限制：\n")

    for source, target, description in real_cases:
        is_too_long_new, source_len, target_len, ratio = check_translation_length(
            source, target, "日语", max_ratio=2.5
        )

        is_too_long_old, _, _, _ = check_translation_length(
            source, target, "日语", max_ratio=1.2
        )

        print(f"📝 {description}")
        print(f"   原文: '{source}' ({source_len}字) -> 译文: '{target}' ({target_len}字)")
        print(f"   比例: {ratio:.2f}")
        print(f"   旧限制(1.2倍): {'❌ 超长' if is_too_long_old else '✓ 正常'}")
        print(f"   新限制(2.5倍): {'❌ 超长' if is_too_long_new else '✓ 正常'}")
        print()

    print("=" * 70)


if __name__ == "__main__":
    success = test_japanese_length_ratio()
    test_real_world_japanese_examples()

    if success:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试失败")

    sys.exit(0 if success else 1)
