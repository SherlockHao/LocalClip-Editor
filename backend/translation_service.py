"""
翻译服务模块

从 main.py 中提取的翻译逻辑，用于任务系统调用
包含完整的质量检查和优化流程
"""

import os
import re
import json
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Callable, Awaitable


def get_language_name(language: str) -> str:
    """将语言代码转换为中文名称"""
    language_map = {
        'en': '英语',
        'English': '英语',
        'ko': '韩语',
        'Korean': '韩语',
        'ja': '日语',
        'Japanese': '日语',
        'fr': '法语',
        'French': '法语',
        'de': '德语',
        'German': '德语',
        'es': '西班牙语',
        'Spanish': '西班牙语',
        'id': '印尼语',
        'Indonesian': '印尼语'
    }
    return language_map.get(language, language)


def get_language_code(language: str) -> str:
    """将语言名称转换为语言代码"""
    language_code_map = {
        '英语': 'en',
        '韩语': 'ko',
        '日语': 'ja',
        '法语': 'fr',
        '德语': 'de',
        '西班牙语': 'es',
        '印尼语': 'id',
        'English': 'en',
        'Korean': 'ko',
        'Japanese': 'ja',
        'French': 'fr',
        'German': 'de',
        'Spanish': 'es',
        'Indonesian': 'id'
    }
    return language_code_map.get(language, language.lower())


async def batch_translate_subtitles(
    source_subtitle_path: Path,
    target_subtitle_path: Path,
    target_language: str,
    progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None
) -> Dict:
    """
    批量翻译字幕文件（包含完整的质量检查和优化流程）

    Args:
        source_subtitle_path: 源字幕文件路径
        target_subtitle_path: 目标字幕文件路径
        target_language: 目标语言
        progress_callback: 进度回调函数 (progress: int, message: str) -> None

    Returns:
        Dict 包含翻译结果的信息
    """
    try:
        import asyncio

        async def update_progress(progress: int, message: str):
            """异步更新进度"""
            if progress_callback:
                try:
                    await progress_callback(progress, message)
                except Exception as e:
                    print(f"[翻译服务] 进度更新失败: {e}", flush=True)

        print(f"\n[翻译服务] 开始翻译任务", flush=True)
        print(f"[翻译服务] 源文件: {source_subtitle_path}", flush=True)
        print(f"[翻译服务] 目标语言: {target_language}", flush=True)

        await update_progress(5, "正在读取原文字幕...")

        # 读取原文字幕
        if not os.path.exists(source_subtitle_path):
            raise FileNotFoundError(f"原文字幕文件不存在: {source_subtitle_path}")

        # 解析SRT文件
        with open(source_subtitle_path, 'r', encoding='utf-8') as f:
            source_content = f.read()

        # 提取所有字幕文本
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*\n?)+?)(?=\n\d+\n|\n*$)'
        matches = re.findall(subtitle_pattern, source_content)

        if not matches:
            raise ValueError("无法解析SRT文件")

        subtitles = []
        for index, start_time, end_time, text in matches:
            text = text.strip()
            subtitles.append({
                "index": int(index) - 1,  # 转为0基索引
                "start_time": start_time,
                "end_time": end_time,
                "text": text
            })

        print(f"[翻译服务] 共 {len(subtitles)} 条字幕需要翻译", flush=True)
        translation_start_time = time.time()

        await update_progress(10, f"正在翻译 {len(subtitles)} 条字幕...")

        # 将语言代码转换为中文名称
        target_language_name = get_language_name(target_language)
        print(f"[翻译服务] 目标语言: {target_language} -> {target_language_name}", flush=True)

        # 创建翻译任务列表
        translate_tasks = []
        for sub in subtitles:
            translate_tasks.append({
                "task_id": f"tr-{sub['index']}",
                "source": sub["text"],
                "target_language": target_language_name,
                "start_time": sub["start_time"],
                "end_time": sub["end_time"],
                "index": sub["index"]
            })

        # 创建临时配置文件
        config_data = {
            "tasks": translate_tasks,
            "model": "qwen2.5:32b"  # 使用 qwen2.5:32b 避免 qwen3 的思考延迟
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False)
            config_file = f.name

        print(f"[翻译服务] 配置文件: {config_file}", flush=True)

        try:
            # 获取Python可执行文件路径
            ui_env_python = os.environ.get("UI_PYTHON")
            if not ui_env_python:
                import sys
                ui_env_python = sys.executable

            # 调用翻译脚本
            batch_translate_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "batch_translate_ollama.py"
            )

            print(f"[翻译服务] 调用翻译脚本...", flush=True)
            print(f"[翻译服务] Python: {ui_env_python}", flush=True)
            print(f"[翻译服务] 脚本: {batch_translate_script}", flush=True)

            # 启动翻译进程
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            # 用于在子线程中更新进度的队列
            progress_queue = asyncio.Queue()

            def run_translation_subprocess():
                """在线程中运行翻译子进程"""
                process = subprocess.Popen(
                    [ui_env_python, batch_translate_script, config_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    cwd=os.path.dirname(__file__),
                    bufsize=1,
                    env=env
                )

                stdout_lines = []
                stderr_lines = []

                # 实时读取输出
                for line in process.stdout:
                    line = line.rstrip('\n')
                    print(f"[翻译脚本] {line}", flush=True)
                    stdout_lines.append(line)

                # 等待进程结束
                return_code = process.wait()

                # 读取 stderr
                if return_code != 0:
                    stderr_output = process.stderr.read()
                    stderr_lines.append(stderr_output)

                return return_code, stdout_lines, stderr_lines

            # 在线程池中运行子进程
            loop = asyncio.get_event_loop()
            return_code, stdout_lines, stderr_lines = await loop.run_in_executor(
                None,
                run_translation_subprocess
            )

            if return_code != 0:
                stderr_output = '\n'.join(stderr_lines)
                print(f"[翻译服务] 错误: {stderr_output}", flush=True)
                raise Exception(f"翻译脚本失败: {stderr_output}")

            await update_progress(80, "正在保存翻译结果...")

            # 解析翻译结果
            json_started = False
            json_lines = []

            for line in stdout_lines:
                if '翻译结果（JSON）' in line or 'FINAL RESULTS' in line:
                    json_started = True
                    continue
                if json_started:
                    if line.strip().startswith('='):
                        continue
                    if line.strip().startswith('['):
                        json_lines.append(line)
                    elif len(json_lines) > 0:
                        json_lines.append(line)
                        if line.strip().endswith(']'):
                            break

            json_text = '\n'.join(json_lines).strip()
            results = json.loads(json_text)

            print(f"[翻译服务] 解析到 {len(results)} 条翻译结果", flush=True)

            # 创建翻译后的字幕列表
            translated_subtitles = []
            for result in results:
                task_index = int(result["task_id"].split('-')[-1])
                original_sub = subtitles[task_index]

                translated_subtitles.append({
                    "index": original_sub["index"],
                    "start_time": original_sub["start_time"],
                    "end_time": original_sub["end_time"],
                    "text": result["translation"]
                })

            # 按索引排序
            translated_subtitles.sort(key=lambda x: x["index"])

            # 生成SRT内容并保存
            def save_srt(subs, path):
                srt_content = ""
                for sub in subs:
                    srt_content += f"{sub['index'] + 1}\n"
                    srt_content += f"{sub['start_time']} --> {sub['end_time']}\n"
                    srt_content += f"{sub['text']}\n\n"
                path.parent.mkdir(exist_ok=True, parents=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(srt_content)

            save_srt(translated_subtitles, target_subtitle_path)
            print(f"[翻译服务] 翻译完成，保存到: {target_subtitle_path}", flush=True)

            # ===== 质量检查和优化 =====
            print(f"\n[翻译服务] ===== 开始质量检查和优化 =====", flush=True)
            await update_progress(82, "正在进行质量检查...")

            # 导入质量检查工具
            from srt_parser import SRTParser
            from text_utils import check_translation_length, contains_chinese_characters
            from text_utils import extract_and_replace_chinese

            srt_parser = SRTParser()

            # 重新读取字幕用于检查
            target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)
            source_subtitles_for_check = srt_parser.parse_srt(source_subtitle_path)

            # 判断目标语言类型
            target_language_lower = target_language.lower()
            is_japanese = ('日' in target_language or 'ja' in target_language_lower)
            is_korean = ('韩' in target_language or 'ko' in target_language_lower or '한국' in target_language)
            is_french = ('法' in target_language or 'fr' in target_language_lower or 'français' in target_language_lower)
            is_german = ('德' in target_language or 'de' in target_language_lower or 'deutsch' in target_language_lower)
            is_spanish = ('西班牙' in target_language or 'es' in target_language_lower or 'español' in target_language_lower or 'spanish' in target_language_lower)

            if is_japanese or is_korean:
                max_ratio = 3
            elif is_french or is_german or is_spanish:
                max_ratio = 1.5
            else:
                max_ratio = 1.2

            # 1. 第一轮检查：收集问题项（长度、中文、英文）
            too_long_items = []
            chinese_replacement_items = []

            for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles_for_check, target_subtitles_for_check)):
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
                        "source_length": source_len,
                        "target_length": target_len,
                        "ratio": ratio,
                        "reason": "too_long"
                    })
                    print(f"  [长度检查] 第 {idx} 条译文过长: {target_len}/{source_len} = {ratio:.1f}x", flush=True)
                elif has_chinese:
                    chinese_replacement_items.append({
                        "index": idx,
                        "target": target_text
                    })
                    print(f"  [汉字检查] 第 {idx} 条译文包含汉字: '{target_text}'", flush=True)

            # 2. 替换中文字符（先处理字符替换，减少需要重新翻译的数量）
            if chinese_replacement_items:
                print(f"\n[翻译服务] 发现 {len(chinese_replacement_items)} 条包含中文的译文，准备替换...", flush=True)
                await update_progress(85, f"正在替换 {len(chinese_replacement_items)} 条译文中的中文...")

                target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)
                replaced_count = 0
                for item in chinese_replacement_items:
                    idx = item["index"]
                    original_text = item["target"]

                    replaced_text = extract_and_replace_chinese(
                        original_text,
                        target_language,
                        to_kana=is_japanese
                    )

                    if replaced_text != original_text:
                        target_subtitles_for_check[idx]["text"] = replaced_text
                        replaced_count += 1
                        print(f"  [{idx}] '{original_text}' -> '{replaced_text}'", flush=True)

                if replaced_count > 0:
                    srt_parser.save_srt(target_subtitles_for_check, target_subtitle_path)
                    print(f"✅ 成功替换 {replaced_count} 条译文中的中文", flush=True)

            # 3. 英文检测和替换（日语/韩语）- 收集符号问题项
            only_symbols_items = []
            if is_japanese or is_korean:
                print(f"\n[翻译服务] 检查包含英文的句子...", flush=True)
                await update_progress(88, "正在替换英文部分...")

                target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)

                from text_utils import contains_english, extract_and_replace_english, is_only_symbols

                english_items = []
                for idx, target_sub in enumerate(target_subtitles_for_check):
                    target_text = target_sub.get("text", "").strip()
                    if contains_english(target_text):
                        english_items.append({
                            "index": idx,
                            "text": target_text
                        })

                if english_items:
                    print(f"[翻译服务] 发现 {len(english_items)} 条包含英文的句子，准备替换英文部分...", flush=True)

                    replaced_count = 0

                    for item in english_items:
                        idx = item["index"]
                        original_text = item["text"]

                        replaced_text = extract_and_replace_english(
                            original_text,
                            to_kana=is_japanese
                        )

                        if replaced_text != original_text:
                            if is_only_symbols(replaced_text):
                                print(f"  [警告] [{idx}] 替换后只剩符号: '{original_text}' -> '{replaced_text}'", flush=True)
                                only_symbols_items.append({
                                    "index": idx,
                                    "source": source_subtitles_for_check[idx]["text"] if idx < len(source_subtitles_for_check) else "",
                                    "target": replaced_text
                                })
                            else:
                                target_subtitles_for_check[idx]["text"] = replaced_text
                                replaced_count += 1
                                print(f"  [{idx}] '{original_text}' -> '{replaced_text}'", flush=True)

                    if replaced_count > 0:
                        srt_parser.save_srt(target_subtitles_for_check, target_subtitle_path)
                        print(f"✅ 成功替换 {replaced_count} 条译文中的英文", flush=True)

            # 4. 合并所有需要重新翻译的项，一次性处理（优化：减少模型加载次数）
            all_retranslate_items = []

            # 添加超长文本项
            if too_long_items:
                print(f"[翻译服务] 收集到 {len(too_long_items)} 条超长译文需要重新翻译", flush=True)
                all_retranslate_items.extend(too_long_items)

            # 添加符号问题项
            if only_symbols_items:
                print(f"[翻译服务] 收集到 {len(only_symbols_items)} 条符号问题需要重新翻译", flush=True)
                all_retranslate_items.extend(only_symbols_items)

            # 统一进行重新翻译
            if all_retranslate_items:
                print(f"\n[翻译服务] 🔄 开始批量重新翻译 {len(all_retranslate_items)} 条问题文本（优化：一次性处理）", flush=True)
                await update_progress(90, f"正在重新翻译 {len(all_retranslate_items)} 条文本...")

                retranslate_tasks = []
                for item in all_retranslate_items:
                    idx = item["index"]
                    source_text = item.get("source", source_subtitles_for_check[idx]["text"] if idx < len(source_subtitles_for_check) else "")

                    if source_text:
                        # 计算最大长度
                        if "source_length" in item:
                            max_length = int(item["source_length"] * max_ratio * 0.8)
                        else:
                            max_length = int(len(source_text) * max_ratio * 0.8)

                        retranslate_tasks.append({
                            "task_id": f"item-{idx}",
                            "source": source_text,
                            "target_language": target_language,
                            "max_length": max_length
                        })

                if retranslate_tasks:
                    retranslate_config = {
                        "tasks": retranslate_tasks,
                        "model": "qwen2.5:32b",
                        "output_file": str(target_subtitle_path)
                    }

                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                        json.dump(retranslate_config, f, ensure_ascii=False, indent=2)
                        retranslate_config_file = f.name

                    try:
                        retranslate_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "batch_retranslate_ollama.py")
                        process = subprocess.Popen(
                            [ui_env_python, retranslate_script, retranslate_config_file],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            encoding='utf-8',
                            bufsize=1
                        )

                        stdout_lines = []
                        for line in process.stdout:
                            print(line, end='', flush=True)
                            stdout_lines.append(line)

                        returncode = process.wait()
                        stdout = ''.join(stdout_lines)

                        if returncode == 0 and stdout:
                            results_match = re.search(r'\[Results\](.*?)\[/Results\]', stdout, re.DOTALL)
                            if results_match:
                                results_json = results_match.group(1).strip()
                                retranslate_results = json.loads(results_json)

                                target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)
                                for result_item in retranslate_results:
                                    idx = int(result_item["task_id"].split('-')[1])
                                    target_subtitles_for_check[idx]["text"] = result_item["translation"]

                                srt_parser.save_srt(target_subtitles_for_check, target_subtitle_path)
                                print(f"✅ 成功重新翻译 {len(retranslate_results)} 条文本（超长+符号问题）", flush=True)
                    except Exception as e:
                        print(f"⚠️ 重新翻译出错: {e}", flush=True)
                    finally:
                        if os.path.exists(retranslate_config_file):
                            os.remove(retranslate_config_file)

            # 5. 数字替换：将阿拉伯数字转换为目标语言的发音
            print(f"\n[翻译服务] 开始检测并替换译文中的阿拉伯数字...", flush=True)
            await update_progress(93, "正在替换数字...")

            from text_utils import replace_digits_in_text

            target_lang_code = get_language_code(target_language)
            target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)

            digits_replaced_count = 0
            for idx, subtitle in enumerate(target_subtitles_for_check):
                original_text = subtitle["text"]
                replaced_text = replace_digits_in_text(original_text, target_lang_code)

                if replaced_text != original_text:
                    subtitle["text"] = replaced_text
                    digits_replaced_count += 1
                    print(f"  [{idx}] '{original_text}' -> '{replaced_text}'", flush=True)

            if digits_replaced_count > 0:
                print(f"\n✅ 成功替换 {digits_replaced_count} 条译文中的数字", flush=True)
                srt_parser.save_srt(target_subtitles_for_check, target_subtitle_path)
            else:
                print(f"ℹ️  未发现需要替换的数字", flush=True)

            # 6. 标点符号清理：删除句首和句中的标点，保留句末标点
            print(f"\n[翻译服务] 开始清理译文中的多余标点符号...", flush=True)
            await update_progress(95, "正在清理标点...")

            from text_utils import clean_punctuation_in_sentence

            target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)

            punctuation_cleaned_count = 0
            for idx, subtitle in enumerate(target_subtitles_for_check):
                original_text = subtitle["text"]
                cleaned_text = clean_punctuation_in_sentence(original_text)

                if cleaned_text != original_text:
                    subtitle["text"] = cleaned_text
                    punctuation_cleaned_count += 1
                    print(f"  [{idx}] '{original_text}' -> '{cleaned_text}'", flush=True)

            if punctuation_cleaned_count > 0:
                print(f"\n✅ 成功清理 {punctuation_cleaned_count} 条译文中的标点", flush=True)
                srt_parser.save_srt(target_subtitles_for_check, target_subtitle_path)
            else:
                print(f"ℹ️  未发现需要清理的标点", flush=True)

            # 7. 最终检查：处理空文本字幕
            print(f"\n[翻译服务] 开始检查空文本字幕...", flush=True)
            await update_progress(99, "正在检查空文本...")

            target_subtitles_for_check = srt_parser.parse_srt(target_subtitle_path)

            empty_text_count = 0
            for idx, subtitle in enumerate(target_subtitles_for_check):
                if not subtitle["text"] or not subtitle["text"].strip():
                    # 用 "hmm" 替代空文本（适用于各种语言）
                    subtitle["text"] = "hmm"
                    empty_text_count += 1
                    print(f"  [{idx}] 空文本 -> 'hmm'", flush=True)

            if empty_text_count > 0:
                print(f"\n✅ 成功处理 {empty_text_count} 条空文本字幕", flush=True)
                srt_parser.save_srt(target_subtitles_for_check, target_subtitle_path)
            else:
                print(f"ℹ️  未发现空文本字幕", flush=True)

            print(f"\n[翻译服务] ===== 质量检查和优化完成 =====\n", flush=True)

            # 计算总耗时
            translation_elapsed = time.time() - translation_start_time
            print(f"[翻译服务] ✓ 翻译完成！总耗时: {translation_elapsed:.2f}秒", flush=True)

            # 注意：不要在这里调用 update_progress(100, ...) 或设置 completed 状态
            # 最终的 completed 状态由 run_translation_task 中的 mark_task_completed 设置

            return {
                "status": "completed",
                "target_file": str(target_subtitle_path),
                "total_items": len(subtitles),
                "elapsed_time": round(translation_elapsed, 2)
            }

        finally:
            # 删除临时配置文件
            if os.path.exists(config_file):
                os.remove(config_file)

    except Exception as e:
        print(f"[翻译服务] 失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise
