"""
测试标点符号清理功能
"""
import sys
import io

# 强制使用UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from text_utils import clean_punctuation_in_sentence

# 测试用例 - 基于新规则
# 新规则：
# 1. 在第一个单词或字出来之前，任何标点都去掉
# 2. 保留句号/逗号/感叹号/问号（半角和全角：.,?!，。？！），其他的全去掉
# 3. 如果有两个或两个以上标点相邻，则只保留第一个
test_cases = [
    # 格式: (输入, 预期输出, 描述)
    ("，你好，世界。", "你好，世界。", "规则1+2: 删除句首逗号，保留句中句末标点"),
    ("Hello, world!", "Hello, world!", "保留逗号和感叹号"),
    ("...测试，文本...", "测试，文本.", "规则1+2: 删除句首省略号，句中保留逗号，省略号转为句号"),
    ("？这是，一个。测试？", "这是，一个。测试？", "规则1: 删除句首问号，保留其他"),
    ("こんにちは、世界。", "こんにちは世界。", "规则2: 删除顿号，保留句号"),
    ("안녕하세요, 세계!", "안녕하세요, 세계!", "保留逗号和感叹号"),
    ("test", "test", "无标点：保持不变"),
    ("...,...", "", "规则1: 只有标点全部删除"),
    ("   ，  test  ，  。  ", "  test  ，  。", "保留空格和允许的标点"),
    ("a.b.c.", "a.b.c.", "保留所有句号（都是允许的标点）"),
    ("！！！测试！！！", "测试！", "规则1+3: 删除句首，连续标点只保留第一个"),
    ("你好~世界@测试#", "你好世界测试", "规则2: 删除特殊符号"),
    ("这是、、一个；；测试！！！", "这是一个测试！", "规则2+3: 删除顿号/分号，连续感叹号只留一个"),
    ("...，，你好？？！！", "你好？", "规则1+3: 句首删除所有，连续标点只留第一个"),
    ("测试:文本：内容", "测试文本内容", "规则2: 删除冒号"),
    ("，，，开头标点测试。。。", "开头标点测试。", "规则1+3: 删除句首多个逗号，句末去重"),
    ("Hello...world", "Hello.world", "规则2+3: 省略号只保留一个句号"),
    ("你好，，世界", "你好，世界", "规则3: 连续逗号只保留第一个"),
    # 西班牙语特殊标点测试
    ("¿No es tarde para volver a comprometerse?", "No es tarde para volver a comprometerse?", "规则1+2: 删除西班牙语倒问号"),
    ("¡Hola! ¿Cómo estás?", "Hola! Cómo estás?", "规则1+2: 删除西班牙语倒感叹号和倒问号"),
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
