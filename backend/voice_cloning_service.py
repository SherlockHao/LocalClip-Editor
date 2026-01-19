# -*- coding: utf-8 -*-
"""
语音克隆服务模块

从 main.py 中提取的完整语音克隆逻辑，用于任务系统
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Callable

# 确保模块路径
_backend_dir = os.path.dirname(os.path.abspath(__file__))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

_speaker_diarization_dir = os.path.join(_backend_dir, '..', 'speaker_diarization_processing')
if _speaker_diarization_dir not in sys.path:
    sys.path.insert(0, _speaker_diarization_dir)

# 默认音色目录
DEFAULT_VOICES_DIR = Path(_backend_dir) / "default_voices"

# 默认音色列表
DEFAULT_VOICES = [
    {
        "id": "chinese_female",
        "name": "中文女声",
        "npy_file": "chinese_female.npy",
        "audio_file": "chinese_female.wav",
        "reference_text": "我觉得这个观点很有道理，也许我们应该深入讨论一下。"
    },
    {
        "id": "chinese_male",
        "name": "中文男声",
        "npy_file": "chinese_male.npy",
        "audio_file": "chinese_male.wav",
        "reference_text": "这个问题确实值得我们认真思考，让我来分析一下。"
    },
    {
        "id": "english_female",
        "name": "英文女声",
        "npy_file": "english_female.npy",
        "audio_file": "english_female.wav",
        "reference_text": "I think this is a very interesting perspective that deserves more attention."
    },
    {
        "id": "english_male",
        "name": "英文男声",
        "npy_file": "english_male.npy",
        "audio_file": "english_male.wav",
        "reference_text": "Let me explain this concept in more detail for better understanding."
    }
]

# 印尼语默认音色
INDONESIAN_VOICES = [
    {
        "id": "indonesian_male",
        "name": "印尼男声 (Ardi)",
        "speaker_name": "ardi"
    },
    {
        "id": "indonesian_female",
        "name": "印尼女声 (Gadis)",
        "speaker_name": "gadis"
    }
]


def get_language_name(language_code: str) -> str:
    """将语言代码转换为中文名称"""
    lang_map = {
        'en': '英语',
        'ko': '韩语',
        'ja': '日语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语',
        'id': '印尼语',
        'english': '英语',
        'korean': '韩语',
        'japanese': '日语',
        'french': '法语',
        'german': '德语',
        'spanish': '西班牙语',
        'indonesian': '印尼语'
    }
    return lang_map.get(language_code.lower(), language_code)


def map_speakers_to_indonesian_voices(speaker_references: dict, speaker_diarization_result: dict) -> dict:
    """根据说话人性别映射到印尼语音色"""
    gender_dict = speaker_diarization_result.get("gender_dict", {})

    mapping = {}
    for speaker_id in speaker_references.keys():
        # 尝试多种键格式
        gender = gender_dict.get(speaker_id) or gender_dict.get(str(speaker_id), "unknown")

        if gender == "female":
            mapping[speaker_id] = "gadis"
        else:
            mapping[speaker_id] = "ardi"

    return mapping


async def clone_voices_for_language(
    task_id: str,
    language: str,
    translated_subtitle_path: Path,
    speaker_voice_mapping: Dict[str, str],
    cloned_audio_output_dir: Path,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict:
    """
    为指定语言克隆所有字幕段落的语音

    Args:
        task_id: 任务 ID
        language: 目标语言
        translated_subtitle_path: 翻译后的字幕文件路径
        speaker_voice_mapping: 说话人到音色的映射
        cloned_audio_output_dir: 克隆音频输出目录
        progress_callback: 进度回调函数

    Returns:
        Dict 包含克隆结果的信息
    """
    from path_utils import task_path_manager
    from srt_parser import SRTParser

    start_time = time.time()

    try:
        print(f"\n========== 语音克隆服务启动 ==========", flush=True)
        print(f"[语音克隆服务] 任务 ID: {task_id}", flush=True)
        print(f"[语音克隆服务] 目标语言: {language}", flush=True)
        print(f"[语音克隆服务] 翻译字幕: {translated_subtitle_path}", flush=True)
        print(f"[语音克隆服务] 输出目录: {cloned_audio_output_dir}", flush=True)
        print(f"[语音克隆服务] 音色映射: {speaker_voice_mapping}", flush=True)

        if progress_callback:
            await progress_callback(2, "正在加载说话人数据...")

        # 1. 加载说话人数据
        speaker_data_path = task_path_manager.get_speaker_data_path(task_id)
        if not speaker_data_path.exists():
            raise FileNotFoundError(f"说话人数据不存在: {speaker_data_path}")

        with open(speaker_data_path, 'r', encoding='utf-8') as f:
            speaker_data = json.load(f)

        # 提取所需数据
        speaker_labels = speaker_data['speaker_labels']
        scored_segments = speaker_data['scored_segments']
        gender_dict = speaker_data.get('gender_dict', {})
        speaker_name_mapping = speaker_data.get('speaker_name_mapping', {})
        audio_dir = speaker_data.get('audio_dir', '')
        segments = speaker_data.get('segments', [])

        num_speakers = speaker_data.get('num_speakers', len(set(speaker_labels)))

        print(f"[语音克隆服务] 加载 {len(speaker_labels)} 个片段, {num_speakers} 个说话人", flush=True)
        print(f"[语音克隆服务] scored_segments 类型: {type(scored_segments)}", flush=True)
        print(f"[语音克隆服务] scored_segments 内容: {scored_segments}", flush=True)
        print(f"[语音克隆服务] gender_dict: {gender_dict}", flush=True)
        print(f"[语音克隆服务] speaker_name_mapping: {speaker_name_mapping}", flush=True)

        if progress_callback:
            await progress_callback(5, "正在读取字幕...")

        # 2. 读取翻译字幕和原始字幕
        srt_parser = SRTParser()
        target_subtitles = srt_parser.parse_srt(str(translated_subtitle_path))

        source_subtitle_path = task_path_manager.get_source_subtitle_path(task_id)
        source_subtitles = srt_parser.parse_srt(str(source_subtitle_path))

        print(f"[语音克隆服务] 加载 {len(target_subtitles)} 条翻译字幕", flush=True)

        # 检查字幕行数是否匹配
        if len(speaker_labels) != len(target_subtitles):
            error_msg = (
                f"字幕文件行数不匹配: 原文 {len(speaker_labels)} 条 vs 译文 {len(target_subtitles)} 条"
            )
            print(f"[语音克隆服务] ❌ {error_msg}", flush=True)
            raise ValueError(error_msg)

        if progress_callback:
            await progress_callback(8, "正在准备说话人参考音频...")

        # 3. 筛选和拼接说话人参考音频
        from speaker_audio_processor import SpeakerAudioProcessor
        from subtitle_text_extractor import SubtitleTextExtractor

        audio_processor = SpeakerAudioProcessor(target_duration=10.0, silence_duration=1.0)
        reference_output_dir = os.path.join(audio_dir, "references")
        os.makedirs(reference_output_dir, exist_ok=True)

        speaker_audio_results = audio_processor.process_all_speakers(
            scored_segments, reference_output_dir
        )

        print(f"[语音克隆服务] speaker_audio_results: {speaker_audio_results}", flush=True)
        print(f"[语音克隆服务] speaker_audio_results 长度: {len(speaker_audio_results)}", flush=True)

        if progress_callback:
            await progress_callback(10, "正在提取参考文本...")

        # 4. 提取参考文本（键统一转换为整数类型）
        text_extractor = SubtitleTextExtractor()
        speaker_segments_for_text = {}
        for speaker_id, (_, selected_segments) in speaker_audio_results.items():
            try:
                speaker_id_int = int(speaker_id)
            except (ValueError, TypeError):
                speaker_id_int = speaker_id
            speaker_segments_for_text[speaker_id_int] = selected_segments

        speaker_texts = text_extractor.process_all_speakers(
            speaker_segments_for_text, str(source_subtitle_path)
        )
        print(f"[DEBUG] speaker_texts keys: {list(speaker_texts.keys())}", flush=True)

        # 5. 构建说话人参考数据（键统一转换为整数类型）
        speaker_references = {}
        for speaker_id in speaker_audio_results.keys():
            # 将 speaker_id 转换为整数（JSON 解析后可能是字符串）
            try:
                speaker_id_int = int(speaker_id)
            except (ValueError, TypeError):
                speaker_id_int = speaker_id

            audio_path, _ = speaker_audio_results[speaker_id]
            audio_path = os.path.abspath(audio_path)
            # speaker_texts 的键也可能是字符串，尝试两种方式获取
            reference_text = speaker_texts.get(speaker_id, speaker_texts.get(speaker_id_int, ""))
            speaker_name = speaker_name_mapping.get(str(speaker_id), f"说话人{speaker_id}")
            gender = gender_dict.get(str(speaker_id), gender_dict.get(speaker_id, "unknown"))

            # 使用整数键存储
            speaker_references[speaker_id_int] = {
                "reference_audio": audio_path,
                "reference_text": reference_text,
                "target_language": language,
                "speaker_name": speaker_name,
                "gender": gender
            }

        print(f"[语音克隆服务] 已准备 {len(speaker_references)} 个说话人的参考数据", flush=True)
        print(f"[DEBUG] speaker_references keys: {list(speaker_references.keys())}", flush=True)
        print(f"[DEBUG] speaker_references keys types: {[type(k).__name__ for k in speaker_references.keys()]}", flush=True)

        # 6. 执行译文质量检查（与翻译流程中相同的检查）
        if progress_callback:
            await progress_callback(12, "正在验证译文质量...")

        target_subtitles = await _validate_and_fix_translations(
            target_subtitles,
            source_subtitles,
            language,
            str(translated_subtitle_path),
            audio_dir
        )

        if progress_callback:
            await progress_callback(18, "译文验证完成，准备语音克隆...")

        # 7. 检测是否为印尼语
        is_indonesian = ('印尼' in language or
                         'indonesian' in language.lower() or
                         'indonesia' in language.lower() or
                         'id' == language.lower())

        if is_indonesian:
            # ========== 印尼语 TTS 分支 ==========
            result = await _clone_indonesian_voices(
                task_id=task_id,
                language=language,
                target_subtitles=target_subtitles,
                speaker_labels=speaker_labels,
                speaker_references=speaker_references,
                gender_dict=gender_dict,
                speaker_name_mapping=speaker_name_mapping,
                cloned_audio_output_dir=cloned_audio_output_dir,
                progress_callback=progress_callback,
                start_time=start_time
            )
        else:
            # ========== Fish-Speech 分支 ==========
            result = await _clone_fish_speech_voices(
                task_id=task_id,
                language=language,
                target_subtitles=target_subtitles,
                speaker_labels=speaker_labels,
                speaker_references=speaker_references,
                speaker_voice_mapping=speaker_voice_mapping,
                audio_dir=audio_dir,
                cloned_audio_output_dir=cloned_audio_output_dir,
                progress_callback=progress_callback,
                start_time=start_time
            )

        return result

    except Exception as e:
        end_time = time.time()
        total_duration = end_time - start_time

        print(f"[语音克隆服务] ❌ 失败: {str(e)}", flush=True)
        print(f"[语音克隆服务] ⏱️ 失败前耗时: {total_duration:.1f}秒", flush=True)
        import traceback
        traceback.print_exc()
        raise


async def _validate_and_fix_translations(
    target_subtitles: List[Dict],
    source_subtitles: List[Dict],
    target_language: str,
    target_subtitle_path: str,
    audio_dir: str
) -> List[Dict]:
    """
    验证并修复译文质量问题

    包括：长度检查、中文替换、英文替换（日韩语）、数字替换、标点清理
    """
    from text_utils import (
        check_translation_length,
        contains_chinese_characters,
        extract_and_replace_chinese,
        contains_english,
        extract_and_replace_english,
        is_only_symbols,
        replace_digits_in_text,
        clean_punctuation_in_sentence
    )
    from srt_parser import SRTParser

    srt_parser = SRTParser()

    # 语言判断
    target_language_lower = target_language.lower()
    is_japanese = ('日' in target_language or 'ja' in target_language_lower)
    is_korean = ('韩' in target_language or 'ko' in target_language_lower or '한국' in target_language)
    is_french = ('法' in target_language or 'fr' in target_language_lower)
    is_german = ('德' in target_language or 'de' in target_language_lower)
    is_spanish = ('西班牙' in target_language or 'es' in target_language_lower)
    is_indonesian = ('印尼' in target_language or 'id' in target_language_lower)

    # 不同语言使用不同的长度比例限制
    if is_japanese or is_korean:
        max_ratio = 3.0
    elif is_french or is_german or is_spanish or is_indonesian:
        max_ratio = 1.5
    else:
        max_ratio = 1.2

    # 1. 长度检查
    too_long_items = []
    chinese_replacement_items = []

    for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
        source_text = source_sub["text"]
        target_text = target_sub["text"]

        is_too_long, source_len, target_len, ratio = check_translation_length(
            source_text, target_text, target_language, max_ratio=max_ratio
        )

        has_chinese = contains_chinese_characters(target_text)

        if is_too_long:
            too_long_items.append({
                "index": idx,
                "source": source_text,
                "target": target_text,
                "ratio": ratio,
                "reason": "too_long"
            })
            print(f"  [长度检查] 第 {idx} 条译文过长: {ratio:.1f}x", flush=True)
        elif has_chinese:
            chinese_replacement_items.append({
                "index": idx,
                "target": target_text
            })
            print(f"  [汉字检查] 第 {idx} 条译文包含汉字", flush=True)

    # 2. 重新翻译过长的文本
    if too_long_items:
        print(f"\n⚠️ 发现 {len(too_long_items)} 条超长译文，准备批量重新翻译...", flush=True)
        target_subtitles = await _retranslate_too_long_items(
            too_long_items, target_subtitles, target_language,
            target_subtitle_path, audio_dir
        )

    # 3. 中文替换
    if chinese_replacement_items:
        print(f"\n[中文替换] 发现 {len(chinese_replacement_items)} 条包含中文的译文", flush=True)
        replaced_count = 0
        for item in chinese_replacement_items:
            idx = item["index"]
            original_text = item["target"]
            replaced_text = extract_and_replace_chinese(
                original_text, target_language, to_kana=is_japanese
            )
            if replaced_text != original_text:
                target_subtitles[idx]["text"] = replaced_text
                replaced_count += 1
                print(f"  [{idx}] '{original_text}' -> '{replaced_text}'", flush=True)

        if replaced_count > 0:
            print(f"✅ 成功替换 {replaced_count} 条译文中的中文", flush=True)
            srt_parser.save_srt(target_subtitles, target_subtitle_path)

    # 4. 英文替换（仅日语/韩语）
    if is_japanese or is_korean:
        print(f"\n[英文检测] 检查译文中包含英文的句子...", flush=True)
        english_items = []
        for idx, target_sub in enumerate(target_subtitles):
            target_text = target_sub.get("text", "").strip()
            if contains_english(target_text):
                english_items.append({"index": idx, "text": target_text})

        if english_items:
            print(f"[英文检测] 发现 {len(english_items)} 条包含英文的句子", flush=True)
            replaced_count = 0
            for item in english_items:
                idx = item["index"]
                original_text = item["text"]
                replaced_text = extract_and_replace_english(original_text, to_kana=is_japanese)
                if replaced_text != original_text and not is_only_symbols(replaced_text):
                    target_subtitles[idx]["text"] = replaced_text
                    replaced_count += 1
                    print(f"  [{idx}] '{original_text}' -> '{replaced_text}'", flush=True)

            if replaced_count > 0:
                print(f"✅ 成功替换 {replaced_count} 条译文中的英文", flush=True)
                srt_parser.save_srt(target_subtitles, target_subtitle_path)

    # 5. 数字替换
    print(f"\n[数字替换] 开始检测并替换译文中的阿拉伯数字...", flush=True)
    language_code_map = {
        '英语': 'en', '韩语': 'ko', '日语': 'ja',
        '法语': 'fr', '德语': 'de', '西班牙语': 'es', '印尼语': 'id'
    }
    target_lang_code = language_code_map.get(target_language, target_language.lower())

    digits_replaced_count = 0
    for idx, subtitle in enumerate(target_subtitles):
        original_text = subtitle["text"]
        replaced_text = replace_digits_in_text(original_text, target_lang_code)
        if replaced_text != original_text:
            subtitle["text"] = replaced_text
            digits_replaced_count += 1
            print(f"  [{idx}] '{original_text}' -> '{replaced_text}'", flush=True)

    if digits_replaced_count > 0:
        print(f"✅ 成功替换 {digits_replaced_count} 条译文中的数字", flush=True)
        srt_parser.save_srt(target_subtitles, target_subtitle_path)

    # 6. 标点符号清理
    print(f"\n[标点清理] 开始清理译文中的多余标点符号...", flush=True)
    punctuation_cleaned_count = 0
    for idx, subtitle in enumerate(target_subtitles):
        original_text = subtitle["text"]
        cleaned_text = clean_punctuation_in_sentence(original_text)
        if cleaned_text != original_text:
            subtitle["text"] = cleaned_text
            punctuation_cleaned_count += 1
            print(f"  [{idx}] '{original_text}' -> '{cleaned_text}'", flush=True)

    if punctuation_cleaned_count > 0:
        print(f"✅ 成功清理 {punctuation_cleaned_count} 条译文中的标点", flush=True)
        srt_parser.save_srt(target_subtitles, target_subtitle_path)

    return target_subtitles


async def _retranslate_too_long_items(
    too_long_items: List[Dict],
    target_subtitles: List[Dict],
    target_language: str,
    target_subtitle_path: str,
    audio_dir: str
) -> List[Dict]:
    """重新翻译过长的文本"""
    import subprocess
    from srt_parser import SRTParser

    srt_parser = SRTParser()
    target_language_name = get_language_name(target_language)

    # 准备重新翻译任务
    retranslate_tasks = []
    for item in too_long_items:
        retranslate_tasks.append({
            "task_id": f"retrans-{item['index']}",
            "source": item["source"],
            "target_language": target_language_name
        })

    # 写入配置文件
    config_file = os.path.join(audio_dir, "voice_clone_retranslate_config.json")
    retranslate_config = {
        "tasks": retranslate_tasks,
        "num_processes": 1
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(retranslate_config, f, ensure_ascii=False, indent=2)

    # 获取 Python 环境
    ui_env_python = os.environ.get("UI_PYTHON")
    if not ui_env_python:
        ui_env_python = sys.executable

    batch_retranslate_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "batch_retranslate_ollama.py"
    )

    if not os.path.exists(ui_env_python):
        print(f"⚠️ UI Python 环境不存在: {ui_env_python}", flush=True)
        return target_subtitles

    if not os.path.exists(batch_retranslate_script):
        print(f"⚠️ 重新翻译脚本不存在: {batch_retranslate_script}", flush=True)
        return target_subtitles

    try:
        print(f"[Retranslate] 启动批量重新翻译进程...", flush=True)

        def run_retranslation_subprocess():
            import time as _time
            process = subprocess.Popen(
                [ui_env_python, batch_retranslate_script, config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            stdout_lines = []
            start = _time.time()
            timeout = 600

            while True:
                if _time.time() - start > timeout:
                    process.kill()
                    print("\n⚠️ 重新翻译超时", flush=True)
                    break

                line = process.stdout.readline()
                if line:
                    print(line, end='', flush=True)
                    stdout_lines.append(line)
                else:
                    if process.poll() is not None:
                        break
                    _time.sleep(0.1)

            remaining = process.stdout.read()
            if remaining:
                stdout_lines.append(remaining)

            return process.wait(), ''.join(stdout_lines)

        loop = asyncio.get_event_loop()
        returncode, stdout = await loop.run_in_executor(None, run_retranslation_subprocess)

        if returncode == 0 and stdout:
            output_lines = stdout.strip().split('\n')
            json_start = -1
            for i in range(len(output_lines) - 1, -1, -1):
                if output_lines[i].strip().startswith('['):
                    json_start = i
                    break

            if json_start >= 0:
                json_output = '\n'.join(output_lines[json_start:])
                retranslate_results = json.loads(json_output)

                for result_item in retranslate_results:
                    idx = int(result_item["task_id"].split('-')[1])
                    new_translation = result_item["translation"]
                    if new_translation and new_translation.strip():
                        target_subtitles[idx]["text"] = new_translation
                        print(f"  [更新 {idx}] 新译文: '{new_translation}'", flush=True)

                srt_parser.save_srt(target_subtitles, target_subtitle_path)
                print(f"✅ 成功重新翻译 {len(retranslate_results)} 条文本", flush=True)

    except Exception as e:
        print(f"⚠️ 重新翻译出错: {e}", flush=True)
        import traceback
        traceback.print_exc()

    return target_subtitles


async def _clone_indonesian_voices(
    task_id: str,
    language: str,
    target_subtitles: List[Dict],
    speaker_labels: List[int],
    speaker_references: Dict,
    gender_dict: Dict,
    speaker_name_mapping: Dict,
    cloned_audio_output_dir: Path,
    progress_callback: Optional[Callable],
    start_time: float
) -> Dict:
    """印尼语 TTS 语音克隆"""
    print("\n" + "=" * 70, flush=True)
    print("[印尼语TTS] 检测到印尼语，使用 VITS-TTS-ID 模型...", flush=True)
    print("=" * 70, flush=True)

    if progress_callback:
        await progress_callback(20, "正在准备印尼语TTS...")

    # 说话人到印尼语音色的映射
    speaker_diarization_result = {
        "gender_dict": gender_dict,
        "speaker_name_mapping": speaker_name_mapping
    }

    speaker_to_indonesian = map_speakers_to_indonesian_voices(
        speaker_references, speaker_diarization_result
    )

    print(f"\n[印尼语TTS] 说话人音色映射:", flush=True)
    for speaker_id, indo_voice in speaker_to_indonesian.items():
        speaker_name = speaker_name_mapping.get(str(speaker_id), f"说话人{speaker_id}")
        gender = gender_dict.get(speaker_id) or gender_dict.get(str(speaker_id), "unknown")
        print(f"  {speaker_name} (性别: {gender}) → {indo_voice}", flush=True)

    # 准备批量生成任务
    cloned_audio_dir = str(cloned_audio_output_dir)
    os.makedirs(cloned_audio_dir, exist_ok=True)

    indonesian_tasks = []
    for idx, (speaker_id, target_sub) in enumerate(zip(speaker_labels, target_subtitles)):
        indonesian_speaker = speaker_to_indonesian.get(speaker_id, "ardi")
        target_text = target_sub["text"]
        output_file = os.path.join(cloned_audio_dir, f"segment_{idx}.wav")

        indonesian_tasks.append({
            "segment_index": idx,
            "speaker_name": indonesian_speaker,
            "target_text": target_text,
            "output_file": output_file
        })

    print(f"\n[印尼语TTS] 准备生成 {len(indonesian_tasks)} 个音频片段", flush=True)

    if progress_callback:
        await progress_callback(25, f"正在生成 {len(indonesian_tasks)} 个印尼语音频...")

    # 调用印尼语 TTS
    from indonesian_tts_cloner import IndonesianTTSCloner

    tts_id_env_python = os.environ.get("TTS_ID_PYTHON")
    if not tts_id_env_python:
        import platform
        if platform.system() == "Windows":
            tts_id_env_python = "C:/Users/7/miniconda3/envs/tts-id-py311/python.exe"
        else:
            tts_id_env_python = os.path.expanduser("~/miniconda3/envs/tts-id-py311/bin/python")

    model_dir = os.environ.get("VITS_TTS_ID_MODEL_DIR")
    if not model_dir:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        model_dir = os.path.join(backend_dir, "..", "..", "..", "models", "vits-tts-id")
        model_dir = os.path.abspath(model_dir)

    if not os.path.exists(tts_id_env_python):
        raise FileNotFoundError(f"TTS-ID Python环境不存在: {tts_id_env_python}")

    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"印尼语TTS模型不存在: {model_dir}")

    cloner = IndonesianTTSCloner(model_dir, tts_id_env_python)

    def update_indonesian_progress(current, total):
        if progress_callback:
            progress = 25 + int((current / total) * 65)  # 25-90%
            asyncio.create_task(progress_callback(progress, f"正在生成印尼语语音 ({current}/{total})..."))

    config_file = os.path.join(cloned_audio_dir, "indonesian_tts_config.json")
    segment_files = cloner.batch_generate_audio(
        indonesian_tasks, config_file, progress_callback=update_indonesian_progress
    )

    print(f"\n[印尼语TTS] ✅ 成功生成 {len(segment_files)} 个音频片段", flush=True)

    # 准备结果
    cloned_results = []
    for idx, (speaker_id, target_sub) in enumerate(zip(speaker_labels, target_subtitles)):
        if idx in segment_files:
            audio_filename = f"segment_{idx}.wav"
            api_path = f"/api/tasks/{task_id}/languages/{language}/cloned-audio/{audio_filename}"

            cloned_results.append({
                "index": idx,
                "speaker_id": speaker_id,
                "target_text": target_sub["text"],
                "cloned_audio_path": api_path,
                "start_time": target_sub.get("start_time", 0),
                "end_time": target_sub.get("end_time", 0)
            })
        else:
            cloned_results.append({
                "index": idx,
                "speaker_id": speaker_id,
                "target_text": target_sub["text"],
                "cloned_audio_path": None,
                "error": "生成失败",
                "start_time": target_sub.get("start_time", 0),
                "end_time": target_sub.get("end_time", 0)
            })

    # 计算耗时
    end_time = time.time()
    total_duration = end_time - start_time
    duration_str = _format_duration(total_duration)

    if progress_callback:
        await progress_callback(100, f"印尼语语音克隆完成 (耗时: {duration_str})")

    print(f"\n✅ 印尼语语音克隆任务 {task_id} 成功完成！", flush=True)
    print(f"⏱️ 总耗时: {duration_str}", flush=True)

    return {
        "status": "completed",
        "output_dir": cloned_audio_dir,
        "total_segments": len(indonesian_tasks),
        "successful_segments": len(segment_files),
        "cloned_results": cloned_results,
        "total_duration": total_duration,
        "duration_str": duration_str
    }


async def _clone_fish_speech_voices(
    task_id: str,
    language: str,
    target_subtitles: List[Dict],
    speaker_labels: List[int],
    speaker_references: Dict,
    speaker_voice_mapping: Dict[str, str],
    audio_dir: str,
    cloned_audio_output_dir: Path,
    progress_callback: Optional[Callable],
    start_time: float
) -> Dict:
    """Fish-Speech 语音克隆"""
    print("\n" + "=" * 70, flush=True)
    print("[Fish-Speech] 使用 Fish-Speech 进行语音克隆...", flush=True)
    print("=" * 70, flush=True)

    if progress_callback:
        await progress_callback(20, "正在初始化 Fish-Speech...")

    from fish_simple_cloner import SimpleFishCloner
    batch_cloner = SimpleFishCloner()

    # 批量编码说话人参考音频
    if progress_callback:
        await progress_callback(22, "正在编码说话人参考音频...")

    encode_output_dir = os.path.join(audio_dir, "encoded")
    os.makedirs(encode_output_dir, exist_ok=True)

    # 分离需要编码的说话人和使用默认音色的说话人
    speakers_to_encode = {}
    speaker_npy_files = {}

    print(f"\n📋 处理音色映射:", flush=True)
    for speaker_id, ref_data in speaker_references.items():
        speaker_id_str = str(speaker_id)
        selected_voice = speaker_voice_mapping.get(speaker_id_str, "default")
        print(f"  说话人 {speaker_id}: 选择音色='{selected_voice}'", flush=True)

        if selected_voice == "default":
            speakers_to_encode[speaker_id] = ref_data
            print(f"    → 使用原音色，需要编码", flush=True)
        else:
            default_voice = next((v for v in DEFAULT_VOICES if v["id"] == selected_voice), None)
            if default_voice:
                npy_path = str(DEFAULT_VOICES_DIR / default_voice["npy_file"])
                speaker_npy_files[speaker_id] = npy_path
                print(f"    → 使用默认音色: {default_voice['name']}", flush=True)
                speaker_references[speaker_id]["reference_text"] = default_voice["reference_text"]
            else:
                speakers_to_encode[speaker_id] = ref_data
                print(f"    ⚠️ 未找到音色 {selected_voice}，使用原音色", flush=True)

    print(f"\n📊 处理结果:", flush=True)
    print(f"  使用默认音色: {len(speaker_npy_files)} 个说话人", flush=True)
    print(f"  需要编码: {len(speakers_to_encode)} 个说话人", flush=True)

    if speakers_to_encode:
        encoded_npy_files = batch_cloner.batch_encode_speakers(
            speakers_to_encode, encode_output_dir
        )
        speaker_npy_files.update(encoded_npy_files)

    if progress_callback:
        await progress_callback(25, "正在准备克隆任务...")

    # 准备批量生成任务
    cloned_audio_dir = str(cloned_audio_output_dir)
    os.makedirs(cloned_audio_dir, exist_ok=True)

    tasks = []
    cloned_results = []

    # 修复类型不匹配问题：将 speaker_npy_files 的键统一转换为整数
    # 因为 speaker_labels 中的 speaker_id 是整数，而编码器返回的键可能是字符串
    speaker_npy_files_int_keys = {}
    for k, v in speaker_npy_files.items():
        try:
            speaker_npy_files_int_keys[int(k)] = v
        except (ValueError, TypeError):
            speaker_npy_files_int_keys[k] = v

    print(f"[DEBUG] speaker_npy_files keys (已转换为整数): {list(speaker_npy_files_int_keys.keys())}", flush=True)
    print(f"[DEBUG] speaker_labels sample: {speaker_labels[:5] if speaker_labels else []}", flush=True)

    for idx, (speaker_id, target_sub) in enumerate(zip(speaker_labels, target_subtitles)):
        target_text = target_sub["text"]

        if speaker_id is None or speaker_id not in speaker_npy_files_int_keys:
            cloned_results.append({
                "index": idx,
                "speaker_id": speaker_id,
                "target_text": target_text,
                "cloned_audio_path": None,
                "start_time": target_sub.get("start_time", 0),
                "end_time": target_sub.get("end_time", 0)
            })
        else:
            tasks.append({
                "speaker_id": speaker_id,
                "target_text": target_text,
                "segment_index": idx,
                "start_time": target_sub.get("start_time", 0),
                "end_time": target_sub.get("end_time", 0)
            })

    print(f"\n🚀 批量生成 {len(tasks)} 个语音片段...", flush=True)

    # 进度回调
    def voice_cloning_progress_callback(current, total):
        if progress_callback:
            progress = 25 + int((current / total) * 70)  # 25-95%
            asyncio.create_task(progress_callback(progress, f"正在生成语音... ({current}/{total})"))

    # 生成脚本目录
    script_dir = os.path.join(audio_dir, "scripts")

    # 在线程池中运行语音生成
    def run_batch_generation():
        return batch_cloner.batch_generate_audio(
            tasks,
            speaker_npy_files_int_keys,  # 使用转换后的整数键字典
            speaker_references,
            cloned_audio_dir,
            script_dir=script_dir,
            progress_callback=voice_cloning_progress_callback
        )

    loop = asyncio.get_event_loop()
    generated_audio_files = await loop.run_in_executor(None, run_batch_generation)

    # 更新结果
    for task in tasks:
        segment_index = task["segment_index"]
        if segment_index in generated_audio_files:
            audio_filename = f"segment_{segment_index}.wav"
            api_path = f"/api/tasks/{task_id}/languages/{language}/cloned-audio/{audio_filename}"

            cloned_results.append({
                "index": segment_index,
                "speaker_id": task["speaker_id"],
                "target_text": task["target_text"],
                "cloned_audio_path": api_path,
                "start_time": task.get("start_time", 0),
                "end_time": task.get("end_time", 0)
            })
        else:
            cloned_results.append({
                "index": segment_index,
                "speaker_id": task["speaker_id"],
                "target_text": task["target_text"],
                "cloned_audio_path": None,
                "error": "生成失败",
                "start_time": task.get("start_time", 0),
                "end_time": task.get("end_time", 0)
            })

    # 按索引排序
    cloned_results.sort(key=lambda x: x["index"])

    # 计算耗时
    end_time = time.time()
    total_duration = end_time - start_time
    duration_str = _format_duration(total_duration)

    if progress_callback:
        await progress_callback(100, f"语音克隆完成 (耗时: {duration_str})")

    print(f"\n✅ 语音克隆任务 {task_id} 成功完成！", flush=True)
    print(f"⏱️ 总耗时: {duration_str}", flush=True)

    return {
        "status": "completed",
        "output_dir": cloned_audio_dir,
        "total_segments": len(tasks),
        "successful_segments": len(generated_audio_files),
        "cloned_results": cloned_results,
        "total_duration": total_duration,
        "duration_str": duration_str
    }


def _format_duration(seconds: float) -> str:
    """将秒数格式化为易读的时间字符串"""
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}分{secs}秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}小时{minutes}分钟"
