"""
独立测试JSON格式翻译结果提取（不依赖transformers）
"""
import sys
import io
import re
import json

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def extract_translation_from_json(text: str, fallback: str = "") -> str:
    """
    从JSON格式的模型输出中提取翻译结果
    （复制自batch_retranslate.py）
    """
    try:
        # 首先尝试直接解析整个文本为JSON
        data = json.loads(text)
        if isinstance(data, dict) and "tr" in data:
            return data["tr"].strip()
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
            if result:
                return result

    # 如果找到 "tr": 但没有完整JSON，尝试提取引号内的内容
    tr_match = re.search(r'"tr"\s*:\s*"([^"]+)"', text, re.DOTALL)
    if tr_match:
        return tr_match.group(1).strip()

    # 移除可能的思考标签作为最后的尝试
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.strip()

    # 如果清理后有内容且不像是错误信息，返回清理后的文本
    if cleaned and not cleaned.startswith('{') and len(cleaned) < 200:
        return cleaned

    # 所有方法都失败，返回备用文本
    return fallback


def test_json_extraction():
    """测试各种JSON格式的提取"""
    print("\n=== 测试JSON提取功能 ===\n")

    test_cases = [
        # (输入, 期望输出, 描述)
        ('{"tr": "Hello"}', "Hello", "标准JSON格式"),
        ('{"tr":"Hello"}', "Hello", "无空格JSON"),
        ('{ "tr" : "Hello" }', "Hello", "带空格JSON"),
        ('{"tr": "안녕하세요"}', "안녕하세요", "韩语翻译"),
        ('{"tr": "こんにちは"}', "こんにちは", "日语翻译"),
        ('{"tr": "Hello", "confidence": 0.9}', "Hello", "带额外字段"),
        ('<think>思考中...</think>\n{"tr": "Hello"}', "Hello", "带思考标签+JSON"),
        ('{"tr": "Hello"}\n\n一些额外说明', "Hello", "JSON后有额外内容"),
        ('输出: {"tr": "Hello"}', "Hello", "前缀+JSON"),
        ('结果是: {"tr": "안녕"}', "안녕", "中文前缀+韩语JSON"),
        ('<think>...</think>\nHello', "Hello", "移除思考标签后的纯文本"),
        ('完全不是JSON格式的很长的文本' * 20, "原文", "过长文本使用fallback"),
        ('', "原文", "空字符串使用fallback"),
    ]

    passed = 0
    failed = 0

    for i, (input_text, expected, description) in enumerate(test_cases, 1):
        result = extract_translation_from_json(input_text, fallback="原文")

        if result == expected:
            print(f"✅ 测试{i}: {description}")
            passed += 1
        else:
            print(f"❌ 测试{i}: {description}")
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
            failed += 1

    print("\n" + "="*60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("="*60)

    return failed == 0


def test_real_world_cases():
    """测试真实场景"""
    print("\n=== 测试真实场景 ===\n")

    real_cases = [
        ('{"tr": "Not good"}', "Not good", "理想JSON输出"),
        ('{\n  "tr": "Not good"\n}', "Not good", "格式化JSON"),
        ('翻译结果如下：\n{"tr": "Not good"}', "Not good", "带中文说明"),
        ('{"tr": "안 좋아"}', "안 좋아", "韩语-不好"),
        ('{"tr": "큰오빠"}', "큰오빠", "韩语-大哥"),
        ('<think>\n分析：这句话表达负面情绪\n翻译策略：使用口语化表达\n</think>\n\n{"tr": "Not good"}',
         "Not good", "完整思考过程+JSON"),
    ]

    all_passed = True
    for i, (input_text, expected, description) in enumerate(real_cases, 1):
        result = extract_translation_from_json(input_text, fallback="FALLBACK")
        success = result == expected
        icon = "✅" if success else "❌"
        print(f"{icon} 场景{i}: {description}")
        if not success:
            print(f"   期望: {expected}")
            print(f"   实际: {result}")
            all_passed = False

    return all_passed


if __name__ == "__main__":
    print("开始测试JSON提取功能...")

    success1 = test_json_extraction()
    success2 = test_real_world_cases()

    if success1 and success2:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败")
        sys.exit(1)
