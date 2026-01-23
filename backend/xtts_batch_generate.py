# -*- coding: utf-8 -*-
"""
XTTS-v2 批量生成脚本
在 xtts 环境中运行，通过子进程调用

输入：JSON 配置文件
输出：生成的音频文件 + JSON 结果（最后一行）

作者：Claude
"""
import os
import sys
import io
import json
import time

# 设置标准输出编码为 UTF-8（Windows 兼容）
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 自动同意 XTTS 许可证条款
os.environ["COQUI_TOS_AGREED"] = "1"


def patch_torchaudio():
    """修复 torchaudio.load 使用 soundfile 替代 torchcodec"""
    import soundfile as sf
    import numpy as np
    import torch
    import torchaudio

    def patched_torchaudio_load(filepath, **kwargs):
        audio, sr = sf.read(filepath)
        if audio.ndim == 1:
            audio = audio[np.newaxis, :]
        else:
            audio = audio.T
        return torch.from_numpy(audio.astype(np.float32)), sr

    torchaudio.load = patched_torchaudio_load


# XTTS-v2 语言代码映射
XTTS_LANGUAGE_MAP = {
    "en": "en", "zh": "zh-cn", "ja": "ja", "ko": "ko",
    "fr": "fr", "de": "de", "es": "es", "pt": "pt",
    "pl": "pl", "it": "it", "nl": "nl", "ru": "ru",
    "tr": "tr", "ar": "ar", "cs": "cs", "hu": "hu",
    "英语": "en", "英文": "en", "english": "en",
    "中文": "zh-cn", "chinese": "zh-cn",
    "日语": "ja", "日文": "ja", "japanese": "ja",
    "韩语": "ko", "韩文": "ko", "korean": "ko",
    "法语": "fr", "法文": "fr", "french": "fr",
    "德语": "de", "德文": "de", "german": "de",
    "西班牙语": "es", "spanish": "es",
}


def map_language_code(language: str) -> str:
    """将语言名称/代码映射到 XTTS-v2 支持的语言代码"""
    if not language:
        return "en"
    lang_lower = language.lower().strip()
    return XTTS_LANGUAGE_MAP.get(lang_lower, "en")


def main():
    if len(sys.argv) < 2:
        print("[XTTS] 错误: 需要提供配置文件路径", flush=True)
        sys.exit(1)

    config_file = sys.argv[1]

    print(f"[XTTS] 读取配置: {config_file}", flush=True)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    use_gpu = config.get("use_gpu", True)
    output_dir = config.get("output_dir", ".")
    tasks = config.get("tasks", [])
    target_language = config.get("target_language", "en")

    if not tasks:
        print("[XTTS] 没有任务", flush=True)
        print("{}", flush=True)
        return

    print(f"[XTTS] 任务数: {len(tasks)}", flush=True)
    print(f"[XTTS] 输出目录: {output_dir}", flush=True)
    print(f"[XTTS] GPU: {'启用' if use_gpu else '禁用'}", flush=True)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 修复 torchaudio
    print("[XTTS] 正在初始化...", flush=True)
    patch_torchaudio()

    # 加载模型
    print("[XTTS] 正在加载模型...", flush=True)
    load_start = time.time()

    from TTS.api import TTS
    tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=use_gpu)

    load_time = time.time() - load_start
    print(f"[XTTS] 模型加载完成，耗时: {load_time:.2f}s", flush=True)

    # 处理任务
    import soundfile as sf
    results = {}
    total = len(tasks)
    successful = 0
    failed = 0

    for idx, task in enumerate(tasks):
        segment_index = task["segment_index"]
        target_text = task["target_text"]
        reference_audio = task["reference_audio"]
        lang = task.get("target_language", target_language)
        output_file = task["output_file"]

        # 映射语言代码
        xtts_lang = map_language_code(lang)

        # 显示进度
        display_text = target_text[:40] + "..." if len(target_text) > 40 else target_text
        print(f"[XTTS] 进度: {idx+1}/{total} | 片段 {segment_index}: {display_text}", flush=True)

        try:
            gen_start = time.time()

            tts.tts_to_file(
                text=target_text,
                file_path=output_file,
                speaker_wav=reference_audio,
                language=xtts_lang
            )

            gen_time = time.time() - gen_start

            # 计算音频时长
            audio, sr = sf.read(output_file)
            audio_duration = len(audio) / sr
            rtf = gen_time / audio_duration if audio_duration > 0 else float('inf')

            print(f"[XTTS]   → 耗时: {gen_time:.2f}s | 时长: {audio_duration:.2f}s | RTF: {rtf:.3f}", flush=True)

            results[segment_index] = output_file
            successful += 1

        except Exception as e:
            print(f"[XTTS] ❌ 片段 {segment_index} 失败: {e}", flush=True)
            failed += 1

    print(f"[XTTS] 完成! 成功: {successful}, 失败: {failed}", flush=True)

    # 输出 JSON 结果（最后一行，供调用者解析）
    print(json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
