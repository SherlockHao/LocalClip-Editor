"""
文本处理工具模块
提供文本规范化、长度计算等功能
"""
import re
import json
import os
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
        language: 语言类型 ("中文", "英文", "韩文", "日文", "法文", "德文", "西班牙文", "English", "Korean", "Japanese", "French", "German", "Spanish" 等)

    Returns:
        int: 文本长度（中文/韩文/日文为字符数，英文/法文/德文/西班牙文为单词数）
    """
    language_lower = language.lower()

    # 判断语言类型
    if any(keyword in language_lower for keyword in ['英', 'english', 'en']):
        return count_english_length(text)
    elif any(keyword in language_lower for keyword in ['法', 'french', 'français', 'fr']):
        return count_english_length(text)  # 法语和英语一样，按单词计数
    elif any(keyword in language_lower for keyword in ['德', 'german', 'deutsch', 'de']):
        return count_english_length(text)  # 德语和英语一样，按单词计数
    elif any(keyword in language_lower for keyword in ['西班牙', 'spanish', 'español', 'es']):
        return count_english_length(text)  # 西班牙语和英语一样，按单词计数
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


def load_digits_mapping() -> dict:
    """
    加载数字映射配置文件

    Returns:
        dict: 数字映射字典
    """
    try:
        mapping_file = os.path.join(os.path.dirname(__file__), 'digits_mapping.json')
        with open(mapping_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('data', {})
    except Exception as e:
        print(f"[警告] 加载数字映射文件失败: {e}")
        return {}


# 用于跟踪已警告过的不支持语言，避免重复打印
_warned_languages = set()

def replace_digits_in_text(text: str, language_code: str) -> str:
    """
    将文本中的阿拉伯数字替换为指定语言的发音

    Args:
        text: 原始文本
        language_code: 语言代码 (en, ko, ja, fr, de, es)

    Returns:
        str: 替换后的文本

    Examples:
        >>> replace_digits_in_text("I have 3 apples", "en")
        "I have three apples"
        >>> replace_digits_in_text("나는 5개를 가지고 있다", "ko")
        "나는 오개를 가지고 있다"
    """
    # 加载映射
    digits_mapping = load_digits_mapping()

    # 检查语言代码是否存在
    lang_code = language_code.lower()
    if lang_code not in digits_mapping:
        # 只在第一次遇到不支持的语言时打印警告
        if lang_code not in _warned_languages:
            print(f"[信息] 语言 '{language_code}' 不需要数字替换，跳过")
            _warned_languages.add(lang_code)
        return text

    language_map = digits_mapping[lang_code]

    # 全角数字到半角数字的映射
    fullwidth_to_halfwidth = {
        '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
        '５': '5', '６': '6', '７': '7', '８': '8', '９': '9'
    }

    # 第一步：将全角数字转换为半角数字
    result = text
    for fullwidth, halfwidth in fullwidth_to_halfwidth.items():
        result = result.replace(fullwidth, halfwidth)

    # 第二步：替换所有半角数字
    def replace_digit(match):
        digit = match.group(0)
        return language_map.get(digit, digit)

    result = re.sub(r'\d', replace_digit, result)

    return result


def process_translations_digits(translations: list, language_code: str) -> list:
    """
    批量处理翻译中的数字替换

    Args:
        translations: 翻译列表，每个元素是字典，包含译文
        language_code: 目标语言代码

    Returns:
        list: 处理后的翻译列表
    """
    processed = []

    for item in translations:
        # 复制原始数据
        processed_item = item.copy()

        # 获取译文（可能在不同的键中）
        target_text = item.get('target_text') or item.get('translation') or item.get('text', '')

        if target_text:
            # 替换数字
            new_text = replace_digits_in_text(target_text, language_code)

            # 如果发生了替换，记录日志
            if new_text != target_text:
                print(f"[数字替换] '{target_text}' -> '{new_text}'")

            # 更新所有可能的字段
            if 'target_text' in processed_item:
                processed_item['target_text'] = new_text
            if 'translation' in processed_item:
                processed_item['translation'] = new_text
            if 'text' in processed_item:
                processed_item['text'] = new_text

        processed.append(processed_item)

    return processed


def extract_and_replace_chinese(text: str, target_language: str, to_kana: bool = False) -> str:
    """
    提取文本中的中文部分并替换为目标语言

    优化：批量处理所有中文片段，只加载一次模型

    Args:
        text: 原始文本
        target_language: 目标语言名称
        to_kana: 如果为True且目标语言是日语，将中文转换为假名

    Returns:
        str: 替换后的文本

    Examples:
        >>> extract_and_replace_chinese("Hello 你好 World", "English")
        "Hello ni hao World"
        >>> extract_and_replace_chinese("こんにちは世界", "日语", to_kana=True)
        "こんにちはせかい"
    """
    import requests

    # 查找所有中文字符段落
    chinese_pattern = r'[\u4e00-\u9fff]+'
    chinese_segments = re.findall(chinese_pattern, text)

    if not chinese_segments:
        return text

    # 去重中文片段（同样的中文只翻译一次）
    unique_chinese = list(dict.fromkeys(chinese_segments))  # 保持顺序去重

    print(f"[中文替换] 找到 {len(chinese_segments)} 个中文片段，去重后 {len(unique_chinese)} 个")

    # 批量翻译所有中文片段（一次性加载模型）
    translation_map = {}

    if to_kana:
        # 日语：批量转换为假名
        translation_map = batch_translate_chinese_to_kana(unique_chinese)
    else:
        # 其他语言：批量翻译
        translation_map = batch_translate_chinese_to_target(unique_chinese, target_language)

    # 替换所有中文片段
    result_text = text
    for chinese_text in chinese_segments:
        replacement = translation_map.get(chinese_text, chinese_text)
        # 只替换第一个匹配的（按出现顺序）
        result_text = result_text.replace(chinese_text, replacement, 1)

    return result_text


def translate_chinese_to_kana(chinese_text: str) -> str:
    """
    将中文文本转换为日语假名

    Args:
        chinese_text: 中文文本

    Returns:
        str: 日语假名
    """
    import requests

    try:
        # 使用 Ollama API 将中文转换为日语假名（平假名）
        # 使用更严格的prompt
        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': f'Convert this Chinese word to Japanese hiragana only. Return ONLY hiragana characters, no explanations, no kanji, no other text.\n\nChinese: {chinese_text}\nHiragana:',
                'stream': False,
                'options': {
                    'temperature': 0.1,  # 降低温度，减少随机性
                    'num_predict': 20,   # 减少生成长度
                    'stop': ['\n', '注', '：', 'Note', '。', '、']  # 遇到这些字符就停止
                },
                'keep_alive': 0  # 立即释放GPU
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            kana = result.get('response', '').strip()

            # 只保留平假名和片假名字符
            # 平假名: \u3040-\u309F
            # 片假名: \u30A0-\u30FF
            kana = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF]', '', kana)

            # 如果清理后为空或太短，返回原文
            if not kana or len(kana) < len(chinese_text) * 0.5:
                print(f"[警告] 转换假名结果异常，保留原文: '{chinese_text}'")
                return chinese_text

            return kana
        else:
            return chinese_text

    except Exception as e:
        print(f"[警告] Ollama转换假名失败: {e}")
        return chinese_text


def translate_chinese_to_target(chinese_text: str, target_language: str) -> str:
    """
    将中文文本翻译为目标语言

    Args:
        chinese_text: 中文文本
        target_language: 目标语言名称

    Returns:
        str: 翻译后的文本
    """
    import requests

    try:
        # 使用 Ollama API 翻译，使用英文prompt提高准确性
        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': f'Translate this Chinese word to {target_language}. Return ONLY the translation, no explanations.\n\nChinese: {chinese_text}\n{target_language}:',
                'stream': False,
                'options': {
                    'temperature': 0.1,  # 降低温度
                    'num_predict': 30,   # 减少生成长度
                    'stop': ['\n', '注', '：', 'Note', '。']  # 停止标记
                },
                'keep_alive': 0  # 立即释放GPU
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            translation = result.get('response', '').strip()

            # 移除可能的引号、句号等
            translation = re.sub(r'^["\']|["\']$', '', translation)
            translation = re.sub(r'[。、\.\,]$', '', translation)
            translation = translation.strip()

            # 如果翻译结果为空，返回原文
            if not translation:
                print(f"[警告] 翻译结果为空，保留原文: '{chinese_text}'")
                return chinese_text

            return translation
        else:
            return chinese_text

    except Exception as e:
        print(f"[警告] Ollama翻译失败: {e}")
        return chinese_text


def batch_translate_chinese_to_kana(chinese_texts: list) -> dict:
    """
    批量将中文文本转换为日语假名（只加载一次模型）

    Args:
        chinese_texts: 中文文本列表

    Returns:
        dict: {中文: 假名} 的映射字典
    """
    import requests

    if not chinese_texts:
        return {}

    translation_map = {}

    try:
        # 构建批量翻译的prompt
        # 格式：中文1\t假名1\n中文2\t假名2
        examples = "\n".join([f"{i+1}. {text}" for i, text in enumerate(chinese_texts)])

        prompt = f"""Convert these Chinese words to Japanese hiragana. Return ONLY the results in this format:
1. [hiragana]
2. [hiragana]
...

Chinese words:
{examples}

Hiragana:"""

        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': len(chinese_texts) * 30,  # 根据数量调整
                    'stop': ['\n\n', 'Note', '注']
                },
                'keep_alive': 0  # 完成后立即释放GPU
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            output = result.get('response', '').strip()

            # 解析输出，按行分割
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if i >= len(chinese_texts):
                    break

                # 移除行号和点号 "1. "
                line = re.sub(r'^\d+\.\s*', '', line.strip())

                # 只保留假名字符
                kana = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF]', '', line)

                if kana and len(kana) >= len(chinese_texts[i]) * 0.5:
                    translation_map[chinese_texts[i]] = kana
                else:
                    # 如果转换失败，保留原文
                    translation_map[chinese_texts[i]] = chinese_texts[i]
                    print(f"[警告] 假名转换失败，保留原文: '{chinese_texts[i]}'")

        # 对于没有成功转换的，保留原文
        for text in chinese_texts:
            if text not in translation_map:
                translation_map[text] = text

    except Exception as e:
        print(f"[警告] 批量假名转换失败: {e}")
        # 失败时所有都保留原文
        for text in chinese_texts:
            translation_map[text] = text

    return translation_map


def batch_translate_chinese_to_target(chinese_texts: list, target_language: str) -> dict:
    """
    批量将中文文本翻译为目标语言（只加载一次模型）

    Args:
        chinese_texts: 中文文本列表
        target_language: 目标语言名称

    Returns:
        dict: {中文: 译文} 的映射字典
    """
    import requests

    if not chinese_texts:
        return {}

    translation_map = {}

    try:
        # 构建批量翻译的prompt
        examples = "\n".join([f"{i+1}. {text}" for i, text in enumerate(chinese_texts)])

        prompt = f"""Translate these Chinese words to {target_language}. Return ONLY the translations in this format:
1. [translation]
2. [translation]
...

Chinese:
{examples}

{target_language}:"""

        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': len(chinese_texts) * 40,
                    'stop': ['\n\n', 'Note', '注']
                },
                'keep_alive': 0  # 完成后立即释放GPU
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            output = result.get('response', '').strip()

            # 解析输出
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if i >= len(chinese_texts):
                    break

                # 移除行号和点号
                line = re.sub(r'^\d+\.\s*', '', line.strip())

                # 清理引号和句号
                line = re.sub(r'^["\']|["\']$', '', line)
                line = re.sub(r'[。、\.\,]$', '', line)
                line = line.strip()

                if line:
                    translation_map[chinese_texts[i]] = line
                else:
                    translation_map[chinese_texts[i]] = chinese_texts[i]
                    print(f"[警告] 翻译失败，保留原文: '{chinese_texts[i]}'")

        # 对于没有成功翻译的，保留原文
        for text in chinese_texts:
            if text not in translation_map:
                translation_map[text] = text

    except Exception as e:
        print(f"[警告] 批量翻译失败: {e}")
        for text in chinese_texts:
            translation_map[text] = text

    return translation_map


def is_english_text(text: str) -> bool:
    """
    检查文本是否完全是英文（包括字母、数字、标点、空格）

    Args:
        text: 要检查的文本

    Returns:
        bool: 如果完全是英文返回True，否则返回False
    """
    if not text:
        return False

    # 允许的字符：英文字母、数字、常见标点、空格
    pattern = r'^[a-zA-Z0-9\s\.,!?\'";\:\-\(\)\[\]]+$'
    return bool(re.match(pattern, text.strip()))


def contains_english(text: str) -> bool:
    """
    检查文本是否包含英文字母

    Args:
        text: 要检查的文本

    Returns:
        bool: 如果包含英文字母返回True，否则返回False
    """
    if not text:
        return False

    # 检查是否包含英文字母
    return bool(re.search(r'[a-zA-Z]', text))


def is_only_symbols(text: str) -> bool:
    """
    检查文本是否只包含符号、数字、空格，没有实际文字

    Args:
        text: 要检查的文本

    Returns:
        bool: 如果只有符号返回True，否则返回False
    """
    if not text:
        return True

    # 移除所有符号、数字、空格后，如果为空则说明只有符号
    # 允许的符号：标点、空格、数字
    text_without_symbols = re.sub(r'[0-9\s\.,!?\'";\:\-\(\)\[\]~`@#$%^&*+=<>{}|/\\]', '', text)
    return len(text_without_symbols.strip()) == 0


def extract_and_replace_english(text: str, to_kana: bool = False) -> str:
    """
    提取文本中的英文部分并替换为目标语言

    类似于 extract_and_replace_chinese，但处理英文
    批量处理所有英文片段，只加载一次模型

    Args:
        text: 原始文本
        to_kana: 如果为True则转换为日语假名，否则转换为韩文

    Returns:
        str: 替换后的文本

    Examples:
        >>> extract_and_replace_english("こんにちは Hello World です", to_kana=True)
        "こんにちは はろー わーるど です"
    """
    # 提取所有英文单词和短语
    # 匹配连续的英文字母、数字、空格、连字符
    english_segments = re.findall(r'[a-zA-Z][a-zA-Z0-9\s\-]*[a-zA-Z0-9]|[a-zA-Z]', text)

    if not english_segments:
        return text

    # 去重，保持顺序
    unique_english = list(dict.fromkeys(english_segments))

    # 批量翻译
    if to_kana:
        translation_map = batch_translate_english_to_kana(unique_english)
    else:
        translation_map = batch_translate_english_to_korean(unique_english)

    # 替换所有英文片段
    result_text = text
    for english_text in english_segments:
        replacement = translation_map.get(english_text, english_text)
        # 只替换第一次出现（按顺序替换）
        result_text = result_text.replace(english_text, replacement, 1)

    return result_text


def batch_translate_english_to_kana(english_texts: list) -> dict:
    """
    批量将英文文本转换为日语假名（只加载一次模型）

    Args:
        english_texts: 英文文本列表

    Returns:
        dict: {英文: 假名} 的映射字典
    """
    import requests

    if not english_texts:
        return {}

    translation_map = {}

    try:
        # 构建批量转换的prompt - 强制要求输出假名
        examples = "\n".join([f"{i+1}. {text}" for i, text in enumerate(english_texts)])

        prompt = f"""Translate these English sentences to Japanese. You MUST output ONLY Japanese hiragana or katakana characters. Do NOT output English, romaji, or any other characters.

Return in this format:
1. [Japanese hiragana/katakana only]
2. [Japanese hiragana/katakana only]
...

English sentences:
{examples}

Japanese (hiragana/katakana ONLY):"""

        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': len(english_texts) * 50,
                    'stop': ['\n\n', 'Note', '注', 'English']
                },
                'keep_alive': 0  # 完成后立即释放GPU
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            output = result.get('response', '').strip()

            # 解析输出
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if i >= len(english_texts):
                    break

                # 移除行号和点号
                line = re.sub(r'^\d+\.\s*', '', line.strip())

                # 清理引号
                line = re.sub(r'^["\']|["\']$', '', line)
                line = line.strip()

                # 只保留假名字符（平假名和片假名）
                kana = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF]', '', line)

                if kana:
                    translation_map[english_texts[i]] = kana
                else:
                    # 如果没有假名，说明翻译失败，标记为需要重试
                    translation_map[english_texts[i]] = None
                    print(f"[警告] 英文转假名失败: '{english_texts[i]}'")

        # 对于翻译失败的文本（值为None），使用单独的翻译请求
        failed_texts = [text for text, result in translation_map.items() if result is None]

        if failed_texts:
            print(f"[英文转假名] 对 {len(failed_texts)} 条失败文本进行第二次翻译...")
            for text in failed_texts:
                try:
                    retry_prompt = f"""Translate this English text to Japanese. You MUST use ONLY hiragana or katakana characters in your response. Do NOT use English letters or romaji.

English: {text}

Japanese (hiragana/katakana ONLY):"""

                    retry_response = requests.post(
                        'http://127.0.0.1:11434/api/generate',
                        json={
                            'model': 'qwen2.5:7b',
                            'prompt': retry_prompt,
                            'stream': False,
                            'options': {
                                'temperature': 0.2,
                                'num_predict': 100,
                                'stop': ['\n\n', 'Note', 'English']
                            },
                            'keep_alive': 0
                        },
                        timeout=30
                    )

                    if retry_response.status_code == 200:
                        retry_result = retry_response.json()
                        retry_output = retry_result.get('response', '').strip()

                        # 清理并提取假名
                        retry_output = re.sub(r'^["\']|["\']$', '', retry_output)
                        kana = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF]', '', retry_output)

                        if kana:
                            translation_map[text] = kana
                            print(f"  ✓ 重试成功: '{text}' -> '{kana}'")
                        else:
                            translation_map[text] = text
                            print(f"  ✗ 重试仍失败，保留原文: '{text}'")
                    else:
                        translation_map[text] = text
                except Exception as e:
                    print(f"  ✗ 重试出错: {e}")
                    translation_map[text] = text

        # 对于没有成功转换的，保留原文
        for text in english_texts:
            if text not in translation_map or translation_map[text] is None:
                translation_map[text] = text

    except Exception as e:
        print(f"[警告] 批量英文转假名失败: {e}")
        for text in english_texts:
            translation_map[text] = text

    return translation_map


def batch_translate_english_to_korean(english_texts: list) -> dict:
    """
    批量将英文文本翻译为韩语（只加载一次模型）

    Args:
        english_texts: 英文文本列表

    Returns:
        dict: {英文: 韩文} 的映射字典
    """
    import requests

    if not english_texts:
        return {}

    translation_map = {}

    try:
        # 构建批量翻译的prompt - 强制要求输出韩文
        examples = "\n".join([f"{i+1}. {text}" for i, text in enumerate(english_texts)])

        prompt = f"""Translate these English sentences to Korean. You MUST output ONLY Korean Hangul characters (한글). Do NOT output English, romanization, or any other characters.

Return in this format:
1. [Korean Hangul only]
2. [Korean Hangul only]
...

English sentences:
{examples}

Korean (Hangul ONLY):"""

        response = requests.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': 'qwen2.5:7b',
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.1,
                    'num_predict': len(english_texts) * 50,
                    'stop': ['\n\n', 'Note', '注', 'English']
                },
                'keep_alive': 0  # 完成后立即释放GPU
            },
            timeout=60
        )

        if response.status_code == 200:
            result = response.json()
            output = result.get('response', '').strip()

            # 解析输出
            lines = output.split('\n')
            for i, line in enumerate(lines):
                if i >= len(english_texts):
                    break

                # 移除行号和点号
                line = re.sub(r'^\d+\.\s*', '', line.strip())

                # 清理引号和句号
                line = re.sub(r'^["\']|["\']$', '', line)
                line = re.sub(r'[。、\.\,]$', '', line)
                line = line.strip()

                # 只保留韩文字符（Hangul）
                korean = re.sub(r'[^\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', '', line)

                if korean:
                    translation_map[english_texts[i]] = korean
                else:
                    # 如果没有韩文，说明翻译失败，标记为需要重试
                    translation_map[english_texts[i]] = None
                    print(f"[警告] 英文转韩文失败: '{english_texts[i]}'")

        # 对于翻译失败的文本（值为None），使用单独的翻译请求
        failed_texts = [text for text, result in translation_map.items() if result is None]

        if failed_texts:
            print(f"[英文转韩文] 对 {len(failed_texts)} 条失败文本进行第二次翻译...")
            for text in failed_texts:
                try:
                    retry_prompt = f"""Translate this English text to Korean. You MUST use ONLY Korean Hangul characters (한글) in your response. Do NOT use English letters or romanization.

English: {text}

Korean (Hangul ONLY):"""

                    retry_response = requests.post(
                        'http://127.0.0.1:11434/api/generate',
                        json={
                            'model': 'qwen2.5:7b',
                            'prompt': retry_prompt,
                            'stream': False,
                            'options': {
                                'temperature': 0.2,
                                'num_predict': 100,
                                'stop': ['\n\n', 'Note', 'English']
                            },
                            'keep_alive': 0
                        },
                        timeout=30
                    )

                    if retry_response.status_code == 200:
                        retry_result = retry_response.json()
                        retry_output = retry_result.get('response', '').strip()

                        # 清理并提取韩文
                        retry_output = re.sub(r'^["\']|["\']$', '', retry_output)
                        retry_output = re.sub(r'[。、\.\,]$', '', retry_output)
                        korean = re.sub(r'[^\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', '', retry_output)

                        if korean:
                            translation_map[text] = korean
                            print(f"  ✓ 重试成功: '{text}' -> '{korean}'")
                        else:
                            translation_map[text] = text
                            print(f"  ✗ 重试仍失败，保留原文: '{text}'")
                    else:
                        translation_map[text] = text
                except Exception as e:
                    print(f"  ✗ 重试出错: {e}")
                    translation_map[text] = text

        # 对于没有成功翻译的，保留原文
        for text in english_texts:
            if text not in translation_map or translation_map[text] is None:
                translation_map[text] = text

    except Exception as e:
        print(f"[警告] 批量英文转韩文失败: {e}")
        for text in english_texts:
            translation_map[text] = text

    return translation_map


def clean_punctuation_in_sentence(text: str) -> str:
    """
    清理句子中的标点符号：删除句首和句中的标点，保留句末标点

    删除的标点包括：
    - 半角: , . ? ! ...
    - 全角: ，。？！…、

    规则：
    1. 删除句子开头的所有标点符号
    2. 删除句子中间的所有标点符号
    3. 保留句子末尾的标点符号
    4. 保留空格（某些语言如英语需要空格分隔单词）

    Args:
        text: 待处理文本

    Returns:
        str: 清理后的文本

    Examples:
        >>> clean_punctuation_in_sentence("，你好，世界。")
        "你好世界。"

        >>> clean_punctuation_in_sentence("Hello, world!")
        "Hello world!"

        >>> clean_punctuation_in_sentence("...测试，文本...")
        "测试文本..."
    """
    if not text or not text.strip():
        return text

    # 定义要删除的标点符号（半角和全角）
    # 不包括空格，因为某些语言（如英语）需要空格分隔单词
    # 包括：逗号、句号、问号、感叹号、省略号、顿号
    punctuation_to_remove = ',.?!…，。？！、'

    # 去除首尾空白
    text = text.strip()

    if not text:
        return text

    # 1. 删除句首的所有标点符号
    while text and text[0] in punctuation_to_remove:
        text = text[1:]

    if not text:
        return text

    # 2. 找到句末的标点符号位置（从后往前找第一个非标点字符）
    end_punctuation_start = len(text)
    for i in range(len(text) - 1, -1, -1):
        if text[i] not in punctuation_to_remove:
            end_punctuation_start = i + 1
            break

    # 3. 分离出句末标点
    main_text = text[:end_punctuation_start]
    end_punctuation = text[end_punctuation_start:]

    # 4. 删除句中的所有标点符号
    cleaned_main = ''.join(char for char in main_text if char not in punctuation_to_remove)

    # 5. 重新组合：清理后的主体 + 句末标点
    result = cleaned_main + end_punctuation

    return result
