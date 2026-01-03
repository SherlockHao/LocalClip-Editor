"""
测试标点符号清理功能
"""
import sys
import io

# 强制使用UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from text_utils import clean_punctuation_in_sentence

# 测试用例
test_cases = [
    # 格式: (输入, 预期输出, 描述)
    ("，你好，世界。", "你好世界。", "中文：删除句首和句中逗号，保留句末句号"),
    ("Hello, world!", "Hello world!", "英文：删除句中逗号，保留句末感叹号"),
    ("...测试，文本...", "测试文本...", "删除句首和句中标点，保留句末省略号"),
    ("？这是，一个。测试？", "这是一个测试？", "删除句首问号、句中逗号和句号，保留句末问号"),
    ("こんにちは、世界。", "こんにちは世界。", "日文：删除句中顿号，保留句末句号"),
    ("안녕하세요, 세계!", "안녕하세요 세계!", "韩文：删除句中逗号，保留句末感叹号"),
    ("test", "test", "无标点：保持不变"),
    ("...,...", "", "只有标点：全部删除"),
    ("   ，  test  ，  。  ", "  test    。", "含空格：保留空格（某些语言需要空格）"),
    ("a.b.c.", "abc.", "句中多个句号：只保留句末"),
    ("！！！测试！！！", "测试！！！", "多个感叹号：删除句首，保留句末"),
]

print("=" * 70)
print("标点符号清理功能测试")
print("=" * 70)

passed = 0
failed = 0

for i, (input_text, expected, description) in enumerate(test_cases, 1):
    result = clean_punctuation_in_sentence(input_text)

    # 判断是否通过
    is_pass = result == expected
    status = "[PASS]" if is_pass else "[FAIL]"

    if is_pass:
        passed += 1
    else:
        failed += 1

    print(f"\n[测试 {i}] {status} - {description}")
    print(f"  输入:   '{input_text}'")
    print(f"  预期:   '{expected}'")
    print(f"  实际:   '{result}'")

    if not is_pass:
        print(f"  [ERROR] 不匹配!")

print("\n" + "=" * 70)
print(f"测试结果: {passed} 通过, {failed} 失败 (总计 {len(test_cases)} 个)")
print("=" * 70)

if failed == 0:
    print("\n[OK] 所有测试通过!")
else:
    print(f"\n[WARNING] 有 {failed} 个测试失败")
