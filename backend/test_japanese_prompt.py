# -*- coding: utf-8 -*-
"""
测试日语翻译 Prompt 特殊处理
验证日语翻译时会添加"使用假名"要求
"""


def test_prompt_generation():
    """测试不同语言的 prompt 生成"""
    print("=" * 60)
    print("日语翻译 Prompt 特殊处理测试")
    print("=" * 60)

    # 模拟 batch_retranslate_ollama.py 中的逻辑
    def generate_prompt(sentence: str, target_language: str) -> str:
        """生成翻译 prompt"""
        # 针对日语添加特殊要求：使用假名
        if '日' in target_language or 'ja' in target_language.lower():
            prompt = f'请将以下中文翻译成{target_language}（口语化、极简、使用假名），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
        else:
            prompt = f'请将以下中文翻译成{target_language}（口语化、极简），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
        return prompt

    test_cases = [
        # (句子, 目标语言, 是否应包含"使用假名")
        ("你好", "日语", True),
        ("你好", "日文", True),
        ("你好", "Japanese", True),
        ("你好", "ja", True),
        ("你好", "JA", True),
        ("你好", "英语", False),
        ("你好", "韩语", False),
        ("你好", "Korean", False),
        ("你好", "en", False),
        ("你好", "ko", False),
    ]

    print("\n测试结果：\n")

    for sentence, target_language, should_include_kana in test_cases:
        prompt = generate_prompt(sentence, target_language)
        has_kana = "使用假名" in prompt

        status = "OK" if has_kana == should_include_kana else "FAIL"

        print(f"{status} 语言: {target_language:12s} | 包含'使用假名': {has_kana}")

        if status == "FAIL":
            print(f"   期望: {should_include_kana}, 实际: {has_kana}")
            print(f"   Prompt: {prompt[:80]}...")

    print("\n" + "=" * 60)

    # 详细展示日语和英语的完整 prompt 对比
    print("\n完整 Prompt 对比：\n")

    japanese_prompt = generate_prompt("今天天气真好", "日语")
    english_prompt = generate_prompt("今天天气真好", "英语")
    korean_prompt = generate_prompt("今天天气真好", "韩语")

    print("【日语 Prompt】")
    print(japanese_prompt)
    print("\n" + "-" * 60 + "\n")

    print("【英语 Prompt】")
    print(english_prompt)
    print("\n" + "-" * 60 + "\n")

    print("【韩语 Prompt】")
    print(korean_prompt)
    print("\n" + "=" * 60)

    # 关键差异分析
    print("\n关键差异分析：\n")

    print("✓ 日语 Prompt 包含：'口语化、极简、使用假名'")
    print("✓ 英语 Prompt 包含：'口语化、极简'")
    print("✓ 韩语 Prompt 包含：'口语化、极简'")
    print("\n只有日语添加了'使用假名'要求！")

    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    test_prompt_generation()
