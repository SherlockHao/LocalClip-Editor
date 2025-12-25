"""
测试韩语和日语文本规范化和长度计算
"""
import sys
import io

# 强制 UTF-8 输出，避免 Windows 控制台编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from text_utils import (
    normalize_korean,
    normalize_japanese,
    count_korean_length,
    count_japanese_length,
    count_text_length,
    check_translation_length
)


def test_korean_normalization():
    """测试韩语规范化"""
    print("\n=== 测试韩语规范化 ===")

    # 测试1: 带空格的韩语
    text1 = "안녕 하세요"
    normalized1 = normalize_korean(text1)
    print(f"原文: '{text1}'")
    print(f"规范化: '{normalized1}'")
    print(f"长度: {len(normalized1)} (应该是5)")
    assert normalized1 == "안녕하세요", f"规范化失败: {normalized1}"
    assert len(normalized1) == 5, f"长度错误: {len(normalized1)}"

    # 测试2: 带标点的韩语
    text2 = "안녕하세요! 반갑습니다."
    normalized2 = normalize_korean(text2)
    print(f"\n原文: '{text2}'")
    print(f"规范化: '{normalized2}'")
    print(f"长度: {len(normalized2)}")

    # 测试3: 混合空格和标点
    text3 = "큰 오빠? 그래!"
    normalized3 = normalize_korean(text3)
    print(f"\n原文: '{text3}'")
    print(f"规范化: '{normalized3}'")
    print(f"长度: {len(normalized3)}")

    print("\n✅ 韩语规范化测试通过")


def test_japanese_normalization():
    """测试日语规范化"""
    print("\n=== 测试日语规范化 ===")

    # 测试1: 平假名
    text1 = "こんにちは 世界"
    normalized1 = normalize_japanese(text1)
    print(f"原文: '{text1}'")
    print(f"规范化: '{normalized1}'")
    print(f"长度: {len(normalized1)}")

    # 测试2: 片假名
    text2 = "コンピュータ です"
    normalized2 = normalize_japanese(text2)
    print(f"\n原文: '{text2}'")
    print(f"规范化: '{normalized2}'")
    print(f"长度: {len(normalized2)}")

    # 测试3: 混合（平假名+片假名+汉字）
    text3 = "私は学生です。"
    normalized3 = normalize_japanese(text3)
    print(f"\n原文: '{text3}'")
    print(f"规范化: '{normalized3}'")
    print(f"长度: {len(normalized3)}")

    print("\n✅ 日语规范化测试通过")


def test_count_text_length():
    """测试多语言长度计算"""
    print("\n=== 测试多语言长度计算 ===")

    # 韩语
    korean_text = "안녕 하세요"
    korean_len = count_text_length(korean_text, "ko")
    print(f"韩语: '{korean_text}' -> 长度: {korean_len}")
    assert korean_len == 5, f"韩语长度计算错误: {korean_len}"

    korean_len2 = count_text_length(korean_text, "korean")
    assert korean_len2 == 5, f"韩语长度计算错误 (关键词'korean'): {korean_len2}"

    korean_len3 = count_text_length(korean_text, "韩文")
    assert korean_len3 == 5, f"韩语长度计算错误 (关键词'韩文'): {korean_len3}"

    # 日语
    japanese_text = "こんにちは 世界"
    japanese_len = count_text_length(japanese_text, "ja")
    print(f"日语: '{japanese_text}' -> 长度: {japanese_len}")

    japanese_len2 = count_text_length(japanese_text, "japanese")
    japanese_len3 = count_text_length(japanese_text, "日文")

    # 英语
    english_text = "Hello world"
    english_len = count_text_length(english_text, "en")
    print(f"英语: '{english_text}' -> 长度: {english_len}")
    assert english_len == 2, f"英语长度计算错误: {english_len}"

    # 中文
    chinese_text = "你好 世界"
    chinese_len = count_text_length(chinese_text, "zh")
    print(f"中文: '{chinese_text}' -> 长度: {chinese_len}")
    assert chinese_len == 4, f"中文长度计算错误: {chinese_len}"

    print("\n✅ 多语言长度计算测试通过")


def test_translation_length_check():
    """测试翻译长度检查"""
    print("\n=== 测试翻译长度检查 ===")

    # 测试: 中文 -> 韩语
    source = "你好"  # 2个汉字
    target_ok = "안녕하세요"  # 5个韩文字符 (2.5倍，超过1.2倍)
    target_long = "안녕하세요 반갑습니다"  # 11个韩文字符 (5.5倍)

    is_too_long_ok, src_len, tgt_len, ratio = check_translation_length(
        source, target_ok, "ko", max_ratio=1.2
    )
    print(f"\n中文 '{source}' ({src_len}字) -> 韩语 '{target_ok}' ({tgt_len}字)")
    print(f"比例: {ratio:.2f}, 超长: {is_too_long_ok}")

    is_too_long, src_len2, tgt_len2, ratio2 = check_translation_length(
        source, target_long, "ko", max_ratio=1.2
    )
    print(f"\n中文 '{source}' ({src_len2}字) -> 韩语 '{target_long}' ({tgt_len2}字)")
    print(f"比例: {ratio2:.2f}, 超长: {is_too_long}")

    assert is_too_long == True, "应该检测到超长"

    print("\n✅ 翻译长度检查测试通过")


def test_real_korean_subtitle():
    """测试真实韩语字幕"""
    print("\n=== 测试真实韩语字幕 ===")

    # 来自 srt_kor.srt 的真实例子
    subtitles = [
        "안녕",
        "난 네 큰오빠야",
        "지금은",
        "작은 현장 소장이지",
        "큰오빠?",
        "그래"
    ]

    for subtitle in subtitles:
        length = count_korean_length(subtitle)
        print(f"'{subtitle}' -> 长度: {length}")

    print("\n✅ 真实韩语字幕测试通过")


if __name__ == "__main__":
    print("开始测试韩语和日语文本处理...")

    test_korean_normalization()
    test_japanese_normalization()
    test_count_text_length()
    test_translation_length_check()
    test_real_korean_subtitle()

    print("\n" + "="*50)
    print("🎉 所有测试通过！")
    print("="*50)
