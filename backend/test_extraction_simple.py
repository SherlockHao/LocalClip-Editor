# -*- coding: utf-8 -*-
"""
简单测试 JSON 提取逻辑（独立版本）
"""
import re
import json
import sys
import io

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def extract_translation_from_json(text: str, fallback: str = "") -> str:
    """
    从JSON格式的模型输出中提取翻译结果（复制自 batch_retranslate_ollama.py）
    """
    try:
        # 首先尝试直接解析整个文本为JSON
        data = json.loads(text)
        if isinstance(data, dict) and "tr" in data:
            result = data["tr"].strip()
            # 过滤掉无效的关键词（如 "translation", "tr" 等）
            if result.lower() not in ['translation', 'tr', 'key', 'value', '']:
                return result
    except:
        pass

    # 尝试从文本中提取JSON对象
    json_patterns = [
        r'\{["\']tr["\']\s*:\s*["\']([^"\']+)["\']\s*\}',
        r'\{\s*"tr"\s*:\s*"([^"]+)"\s*\}',
        r'\{["\']tr["\']\s*:\s*["\']([^"\']*?)["\']\s*[,\}]',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            # 过滤掉无效的关键词
            if result and result.lower() not in ['translation', 'tr', 'key', 'value']:
                return result

    # 如果没有找到JSON格式，尝试查找引号中的内容
    quote_patterns = [
        r'"([^"]{2,})"',
        r"'([^']{2,})'",
    ]

    for pattern in quote_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 过滤掉 "tr", "translation" 等关键词
            filtered_matches = [
                m for m in matches
                if m.lower() not in ['tr', 'translation', 'key', 'value']
            ]
            if filtered_matches:
                # 返回最长的匹配（通常是翻译结果）
                longest = max(filtered_matches, key=len)
                if len(longest) > len(fallback) / 2:
                    return longest.strip()

    # 最后的回退：如果什么都没提取到，使用 fallback
    # 不要盲目返回原始文本，因为可能包含无效内容（如JSON结构、关键词等）
    return fallback


def test():
    """测试函数"""
    print("=" * 70)
    print("JSON 提取功能测试")
    print("=" * 70)

    test_cases = [
        # (模型输出, 回退值, 期望结果, 描述)
        ('{"tr": "こんにちは"}', "你好", "こんにちは", "✓ 标准 JSON"),
        ('{"tr":"こんにちは"}', "你好", "こんにちは", "✓ 紧凑 JSON"),
        ('{ "tr" : "こんにちは" }', "你好", "こんにちは", "✓ 宽松 JSON"),

        # 关键问题：返回 "translation" 关键词的情况
        ('{"tr": "translation"}', "你好", "你好", "✗ 关键词 translation（应回退到原文）"),
        ('"translation"', "你好", "你好", "✗ 只有关键词（应回退）"),
        ('The result is "translation"', "你好", "你好", "✗ 描述+关键词（应回退）"),

        # 正常的包含translation的情况
        ('{"tr": "translation guide"}', "你好", "translation guide", "✓ translation 作为词组"),

        # 其他正常情况
        ('{"tr": "きょうはいいてんきですね"}', "今天天气真好", "きょうはいいてんきですね", "✓ 日语假名"),
        ('{"tr": "オレノモモヲオル"}', "我打断他的腿", "オレノモモヲオル", "✓ 日语片假名"),
        ('"こんにちは"', "你好", "こんにちは", "✓ 纯引号格式"),

        # 边缘情况
        ('', "你好", "你好", "✓ 空输出（回退）"),
        ('invalid', "你好", "你好", "✓ 无效格式（回退）"),
    ]

    print("\n测试结果：\n")

    passed = 0
    failed = 0

    for model_output, fallback, expected, description in test_cases:
        result = extract_translation_from_json(model_output, fallback)

        # 判断是否通过
        is_pass = result == expected
        status = "PASS" if is_pass else "FAIL"

        if is_pass:
            passed += 1
            icon = "✓"
        else:
            failed += 1
            icon = "✗"

        # 显示测试结果
        output_short = model_output[:35] + "..." if len(model_output) > 35 else model_output

        print(f"{icon} [{status}] {description}")
        print(f"  输入: {output_short}")
        print(f"  期望: '{expected}' | 实际: '{result}'")

        if not is_pass:
            print(f"  ❌ 测试失败！")
        print()

    print("=" * 70)
    print(f"测试完成: ✓ {passed} 通过 | ✗ {failed} 失败 | 总计 {len(test_cases)}")
    print("=" * 70)

    if failed == 0:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")

    return failed == 0


if __name__ == "__main__":
    import sys
    success = test()
    sys.exit(0 if success else 1)
