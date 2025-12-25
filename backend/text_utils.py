"""
文本处理工具模块
提供文本规范化、长度计算等功能
"""
import re
from typing import Tuple


def normalize_chinese(text: str) -> str:
    """
    规范化中文文本，移除符号和空格

    Args:
        text: 原始中文文本

    Returns:
        str: 只包含中文字符的文本
    """
    # 只保留中文字符（包括中文标点符号范围内的字符）
    # Unicode 范围: 0x4E00-0x9FFF (CJK统一汉字)
    normalized = re.sub(r'[^\u4e00-\u9fff]', '', text)
    return normalized


def normalize_english(text: str) -> str:
    """
    规范化英文文本，移除符号和空格，处理缩写

    特殊处理：
    - "I'm", "don't", "can't" 等缩写算作一个单词
    - 移除所有标点符号和空格

    Args:
        text: 原始英文文本

    Returns:
        str: 规范化后的文本（用空格分隔单词）
    """
    # 将缩写中的撇号替换为特殊标记，避免被分割
    # 常见缩写: 'm, 't, 's, 're, 've, 'll, 'd
    text = re.sub(r"(\w)'(\w)", r"\1APOSTROPHE\2", text)

    # 移除所有标点符号和特殊字符，只保留字母、数字和空格
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    # 恢复撇号（作为单词的一部分）
    text = text.replace('APOSTROPHE', '')

    # 移除多余空格，标准化为单个空格
    text = ' '.join(text.split())

    return text


def normalize_korean(text: str) -> str:
    """
    规范化韩文文本，移除符号和空格

    Args:
        text: 原始韩文文本

    Returns:
        str: 只包含韩文字符的文本
    """
    # 韩文字符 Unicode 范围:
    # - 0xAC00-0xD7AF: 谚文音节 (완성형 한글)
    # - 0x1100-0x11FF: 谚文字母 (자모)
    # - 0x3130-0x318F: 谚文兼容字母
    normalized = re.sub(r'[^\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', '', text)
    return normalized


def normalize_japanese(text: str) -> str:
    """
    规范化日文文本，移除符号和空格

    Args:
        text: 原始日文文本

    Returns:
        str: 只包含日文字符的文本
    """
    # 日文字符 Unicode 范围:
    # - 0x3040-0x309F: 平假名 (ひらがな)
    # - 0x30A0-0x30FF: 片假名 (カタカナ)
    # - 0x4E00-0x9FFF: CJK统一汉字 (日文中使用的汉字)
    # - 0x3400-0x4DBF: CJK扩展A (罕用汉字)
    normalized = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF]', '', text)
    return normalized


def contains_chinese_characters(text: str) -> bool:
    """
    检测文本中是否包含中文字（汉字）

    注意：此函数检测CJK统一汉字，日文中也使用汉字，但比例较低。
    主要用于检测日文翻译中是否有过多汉字（应该用假名代替）。

    Args:
        text: 待检测文本

    Returns:
        bool: 如果包含汉字返回 True，否则返回 False
    """
    # CJK统一汉字 Unicode 范围: 0x4E00-0x9FFF
    # 这个范围包括了中文、日文、韩文中使用的汉字
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def count_chinese_length(text: str) -> int:
    """
    计算中文文本的长度（只统计汉字）

    Args:
        text: 中文文本

    Returns:
        int: 汉字数量
    """
    normalized = normalize_chinese(text)
    return len(normalized)


def count_english_length(text: str) -> int:
    """
    计算英文文本的长度（统计单词数）

    Args:
        text: 英文文本

    Returns:
        int: 单词数量
    """
    normalized = normalize_english(text)
    if not normalized:
        return 0
    return len(normalized.split())


def count_korean_length(text: str) -> int:
    """
    计算韩文文本的长度（统计字符数）

    Args:
        text: 韩文文本

    Returns:
        int: 韩文字符数量
    """
    normalized = normalize_korean(text)
    return len(normalized)


def count_japanese_length(text: str) -> int:
    """
    计算日文文本的长度（统计字符数）

    Args:
        text: 日文文本

    Returns:
        int: 日文字符数量
    """
    normalized = normalize_japanese(text)
    return len(normalized)


def count_text_length(text: str, language: str) -> int:
    """
    根据语言类型计算文本长度

    Args:
        text: 文本内容
        language: 语言类型 ("中文", "英文", "韩文", "日文", "English", "Korean", "Japanese" 等)

    Returns:
        int: 文本长度（中文/韩文/日文为字符数，英文为单词数）
    """
    language_lower = language.lower()

    # 判断语言类型
    if any(keyword in language_lower for keyword in ['英', 'english', 'en']):
        return count_english_length(text)
    elif any(keyword in language_lower for keyword in ['韩', 'korean', 'ko', '한국']):
        return count_korean_length(text)
    elif any(keyword in language_lower for keyword in ['日', 'japanese', 'ja', '日本']):
        return count_japanese_length(text)
    else:
        # 默认按中文处理
        return count_chinese_length(text)


def check_translation_length(
    source_text: str,
    target_text: str,
    target_language: str,
    max_ratio: float = 1.1
) -> Tuple[bool, int, int, float]:
    """
    检查译文长度是否超过原文的指定倍数

    Args:
        source_text: 原文（中文）
        target_text: 译文
        target_language: 目标语言
        max_ratio: 最大长度比例（默认1.2倍）

    Returns:
        Tuple[bool, int, int, float]: (是否超长, 原文长度, 译文长度, 实际比例)
    """
    # 计算原文长度（中文字数）
    source_length = count_chinese_length(source_text)

    # 计算译文长度（根据目标语言）
    target_length = count_text_length(target_text, target_language)

    # 计算实际比例
    if source_length == 0:
        ratio = 0.0
    else:
        ratio = target_length / source_length

    # 判断是否超长
    is_too_long = ratio > max_ratio

    return is_too_long, source_length, target_length, ratio


def validate_translations(
    translations: list,
    target_language: str,
    max_ratio: float = 1.2
) -> Tuple[list, list]:
    """
    批量验证译文长度

    Args:
        translations: 翻译列表，每个元素包含 {"source": "原文", "target": "译文", ...}
        target_language: 目标语言
        max_ratio: 最大长度比例

    Returns:
        Tuple[list, list]: (合格的翻译列表, 超长的翻译列表)
    """
    valid_translations = []
    too_long_translations = []

    for translation in translations:
        source_text = translation.get("source", "")
        target_text = translation.get("target", "")

        is_too_long, source_len, target_len, ratio = check_translation_length(
            source_text, target_text, target_language, max_ratio
        )

        # 添加统计信息
        translation_info = {
            **translation,
            "source_length": source_len,
            "target_length": target_len,
            "length_ratio": ratio
        }

        if is_too_long:
            too_long_translations.append(translation_info)
        else:
            valid_translations.append(translation_info)

    return valid_translations, too_long_translations
