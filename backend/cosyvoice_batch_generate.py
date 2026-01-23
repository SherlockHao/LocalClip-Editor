# -*- coding: utf-8 -*-
"""
CosyVoice3 批量生成脚本
在 cosyvoice 环境中运行，通过子进程调用

输入：JSON 配置文件
输出：生成的音频文件 + JSON 结果（最后一行）

使用 Fun-CosyVoice3-0.5B 模型的 inference_cross_lingual API

重要依赖说明：
- 需要 transformers==4.51.3（更高版本会导致生成质量问题）
- 需要 soundfile 替代 torchaudio.load

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


# CosyVoice3 语言代码映射
COSYVOICE_LANGUAGE_MAP = {
    "en": "en", "zh": "zh", "ja": "ja", "ko": "ko",
    "fr": "fr", "de": "de", "es": "es", "pt": "pt",
    "英语": "en", "英文": "en", "english": "en",
    "中文": "zh", "chinese": "zh",
    "日语": "ja", "日文": "ja", "japanese": "ja",
    "韩语": "ko", "韩文": "ko", "korean": "ko",
    "法语": "fr", "法文": "fr", "french": "fr",
    "德语": "de", "德文": "de", "german": "de",
    "西班牙语": "es", "spanish": "es",
}


def map_language_code(language: str) -> str:
    """将语言名称/代码映射到 CosyVoice3 支持的语言代码"""
    if not language:
        return "en"
    lang_lower = language.lower().strip()
    return COSYVOICE_LANGUAGE_MAP.get(lang_lower, "en")


def main():
    if len(sys.argv) < 2:
        print("[CosyVoice] 错误: 需要提供配置文件路径", flush=True)
        sys.exit(1)

    config_file = sys.argv[1]

    print(f"[CosyVoice] 读取配置: {config_file}", flush=True)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    use_gpu = config.get("use_gpu", True)
    gpu_id = config.get("gpu_id", 0)
    output_dir = config.get("output_dir", ".")
    tasks = config.get("tasks", [])
    target_language = config.get("target_language", "en")

    if not tasks:
        print("[CosyVoice] 没有任务", flush=True)
        print("{}", flush=True)
        return

    print(f"[CosyVoice] 任务数: {len(tasks)}", flush=True)
    print(f"[CosyVoice] 输出目录: {output_dir}", flush=True)
    print(f"[CosyVoice] GPU: {'启用' if use_gpu else '禁用'} (GPU {gpu_id})", flush=True)

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 设置 CosyVoice 路径
    # 默认路径，可通过环境变量覆盖
    cosyvoice_dir = os.environ.get("COSYVOICE_DIR")

    if not cosyvoice_dir or not os.path.exists(cosyvoice_dir):
        # 尝试多个默认路径
        possible_paths = [
            r"D:\ai_editing\cosyvoice\CosyVoice",
            os.path.join(os.path.dirname(__file__), "..", "..", "cosyvoice", "CosyVoice"),
            os.path.expanduser("~/cosyvoice/CosyVoice"),
        ]
        for path in possible_paths:
            path = os.path.abspath(path)
            if os.path.exists(path):
                cosyvoice_dir = path
                break

    if not cosyvoice_dir or not os.path.exists(cosyvoice_dir):
        print(f"[CosyVoice] 错误: 找不到 CosyVoice 目录", flush=True)
        print(f"[CosyVoice] 请设置 COSYVOICE_DIR 环境变量", flush=True)
        sys.exit(1)

    print(f"[CosyVoice] CosyVoice 目录: {cosyvoice_dir}", flush=True)

    # 添加 CosyVoice 和 Matcha-TTS 路径
    sys.path.insert(0, cosyvoice_dir)
    sys.path.insert(0, os.path.join(cosyvoice_dir, "third_party", "Matcha-TTS"))

    # 模型目录
    model_dir = os.environ.get("COSYVOICE_MODEL_DIR")
    if not model_dir:
        model_dir = os.path.join(cosyvoice_dir, "pretrained_models", "Fun-CosyVoice3-0.5B")

    print(f"[CosyVoice] 模型目录: {model_dir}", flush=True)

    # 加载模型
    print("[CosyVoice] 正在加载模型...", flush=True)
    load_start = time.time()

    from cosyvoice.cli.cosyvoice import AutoModel
    import soundfile as sf

    cosyvoice = AutoModel(model_dir=model_dir)

    load_time = time.time() - load_start
    print(f"[CosyVoice] 模型加载完成，耗时: {load_time:.2f}s", flush=True)
    print(f"[CosyVoice] 采样率: {cosyvoice.sample_rate} Hz", flush=True)

    # 处理任务
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
        cosyvoice_lang = map_language_code(lang)

        # 显示进度
        display_text = target_text[:40] + "..." if len(target_text) > 40 else target_text
        print(f"[CosyVoice] 进度: {idx+1}/{total} | 片段 {segment_index}: {display_text}", flush=True)

        try:
            gen_start = time.time()

            # CosyVoice3 cross_lingual 格式：需要在文本前加入 prompt prefix
            cross_lingual_text = f"You are a helpful assistant.<|endofprompt|>{target_text}"

            # 使用 inference_cross_lingual 生成（跨语言克隆）
            for i, result in enumerate(cosyvoice.inference_cross_lingual(
                cross_lingual_text,
                reference_audio,
                stream=False
            )):
                audio_np = result['tts_speech'].squeeze().cpu().numpy()
                sf.write(output_file, audio_np, cosyvoice.sample_rate)

            gen_time = time.time() - gen_start

            # 计算音频时长
            audio, sr = sf.read(output_file)
            audio_duration = len(audio) / sr
            rtf = gen_time / audio_duration if audio_duration > 0 else float('inf')

            print(f"[CosyVoice]   → 耗时: {gen_time:.2f}s | 时长: {audio_duration:.2f}s | RTF: {rtf:.3f}", flush=True)

            results[segment_index] = output_file
            successful += 1

        except Exception as e:
            print(f"[CosyVoice] ❌ 片段 {segment_index} 失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"[CosyVoice] 完成! 成功: {successful}, 失败: {failed}", flush=True)

    # 输出 JSON 结果（最后一行，供调用者解析）
    print(json.dumps(results, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
