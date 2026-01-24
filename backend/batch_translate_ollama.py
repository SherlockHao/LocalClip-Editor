"""
基于 Ollama 的批量翻译脚本
将中文字幕翻译为目标语言
使用同步调用，优化性能
"""
import sys
import os
import json
import time
from typing import List, Dict, Any
import requests

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


# JSON 提取函数
def extract_translation_from_json(text: str, fallback: str = "") -> str:
    """从JSON格式的模型输出中提取翻译结果"""
    import re
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "tr" in data:
            result = data["tr"].strip()
            if result.lower() not in ['translation', 'tr', 'key', 'value', '']:
                return result
    except:
        pass

    # 尝试从文本中提取JSON对象
    json_patterns = [
        r'\{["\']tr["\']\s*:\s*["\']([^"\']+)["\']\s*\}',
        r'\{\s*"tr"\s*:\s*"([^"]+)"\s*\}',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            if result and result.lower() not in ['translation', 'tr', 'key', 'value']:
                return result

    return fallback if fallback else text

# 使用 127.0.0.1 避免 Windows 下 localhost 的 IPv6 解析延迟
OLLAMA_API_URL = 'http://127.0.0.1:11434/v1/chat/completions'

# 创建一个session以复用连接
SESSION = requests.Session()
SESSION.headers.update({'Content-Type': 'application/json'})


def start_ollama_service():
    """
    自动启动 Ollama 服务
    """
    import subprocess
    import platform

    print("🚀 正在启动 Ollama 服务...", flush=True)

    try:
        if platform.system() == "Windows":
            # Windows: 使用 START 命令在新窗口中启动 ollama serve
            subprocess.Popen(
                ["cmd", "/c", "start", "ollama", "serve"],
                shell=False,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Linux/Mac: 后台启动
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

        # 等待服务启动
        print("⏳ 等待 Ollama 服务启动...", flush=True)
        max_retries = 10
        for i in range(max_retries):
            time.sleep(2)
            try:
                response = SESSION.get("http://127.0.0.1:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    print(f"✅ Ollama 服务已启动！", flush=True)
                    return True
            except:
                pass
            print(f"  等待中... ({i+1}/{max_retries})", flush=True)

        print("❌ Ollama 服务启动超时", flush=True)
        return False

    except Exception as e:
        print(f"❌ 启动 Ollama 服务失败: {e}", flush=True)
        return False


def warm_up(model: str = "qwen2.5:32b"):
    """
    热启动函数：发送一个空请求，确保模型从硬盘加载到了显存中。
    如果 Ollama 未启动，会自动启动服务。
    """
    print(f"🔥 正在进行热启动 (加载模型 {model} 到显存)...", flush=True)
    start = time.time()

    # 先尝试连接
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            # 设置 keep_alive=-1 让模型永久保持在显存中
            response = SESSION.post(
                OLLAMA_API_URL,
                json={
                    'model': model,
                    'messages': [{"role": "user", "content": "hi"}],
                    'max_tokens': 1,
                    'keep_alive': -1
                },
                timeout=30
            )
            response.raise_for_status()
            elapsed = time.time() - start
            print(f"✅ 热启动完成！加载耗时: {elapsed:.2f}s", flush=True)
            print(f"✅ 模型已锁定在显存中（不会自动卸载）", flush=True)
            print("-" * 60, flush=True)
            return

        except requests.exceptions.ConnectionError as e:
            if attempt == 0:
                # 第一次失败，尝试启动 Ollama
                print(f"⚠️ 无法连接到 Ollama 服务 (尝试 {attempt+1}/{max_attempts})", flush=True)
                if start_ollama_service():
                    # 重新计时
                    start = time.time()
                    continue
                else:
                    print(f"❌ 连接 Ollama 失败，请检查服务是否开启。错误信息: {e}", flush=True)
                    raise
            else:
                # 第二次还是失败，抛出异常
                print(f"❌ 连接 Ollama 失败，请检查服务是否开启。错误信息: {e}", flush=True)
                raise
        except Exception as e:
            print(f"❌ 连接 Ollama 失败，请检查服务是否开启。错误信息: {e}", flush=True)
            raise


def translate_batch_group(
    sentences: List[str],
    target_language: str,
    task_id_prefix: str,
    model: str = "qwen2.5:32b"
) -> List[Dict[str, Any]]:
    """
    批量翻译任务，提供上下文感知能力

    Args:
        sentences: 源文本列表（有顺序的上下文）
        target_language: 目标语言
        task_id_prefix: 任务前缀
        model: 模型名称
    """
    if not sentences:
        return []

    # 1. 根据语言特性构建指令
    if '日' in target_language or 'ja' in target_language.lower():
        lang_rule = "全假名无汉字"
    elif '韩' in target_language or 'ko' in target_language.lower():
        lang_rule = "纯韩文无汉字"
    else:
        lang_rule = "地道简洁"

    # 2. 构建 System Prompt：精简有力
    system_prompt = (
        f"你是配音字幕压缩专家。翻译为{target_language}。这是连续对话片段，需保持:\n"
        f"1. 上下文连贯(代词/指代/语气统一)\n"
        f"2. {lang_rule}\n"
        f"3. 极简表达(最口语的缩略形式/去冗余)，字数极少\n"
        f"4. 宁可漏译也不要长译\n"
        f"返回JSON: {{\"translations\": [\"译文1\", \"译文2\", ...]}}"
    )

    # 3. 构建 User Prompt：明确标注这是连续对话
    user_content = "【连续对话】请根据上下文翻译:\n"
    for i, s in enumerate(sentences):
        user_content += f"{i}. {s}\n"

    try:
        start_time = time.time()

        response = SESSION.post(
            OLLAMA_API_URL,
            json={
                'model': model,
                'messages': [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                'temperature': 0.3,  # 适当提升一点点随机性，有助于上下文衔接更自然
                'response_format': {"type": "json_object"},
                'stream': False,
                'keep_alive': -1
            },
            timeout=60  # 批量翻译耗时较长，增加超时时间
        )

        response.raise_for_status()
        result_json = response.json()
        raw_content = result_json['choices'][0]['message']['content'].strip()

        # 解析返回的 JSON 数组
        parsed_data = json.loads(raw_content)
        translated_list = parsed_data.get("translations", [])

        # 4. 结果校验与组装
        results = []
        elapsed = (time.time() - start_time) / len(sentences)  # 平均单句耗时

        for i, original_text in enumerate(sentences):
            # 如果模型漏译了（虽然 json_object 模式下概率低），则兜底返回原文
            tr_text = translated_list[i] if i < len(translated_list) else original_text

            results.append({
                "task_id": f"{task_id_prefix}_{i}",
                "source": original_text,
                "translation": tr_text,
                "success": i < len(translated_list),
                "elapsed": elapsed
            })

        return results

    except Exception as e:
        print(f"[批量翻译错误] {task_id_prefix}: {e}", flush=True)
        # 失败全量兜底
        return [{
            "task_id": f"{task_id_prefix}_{i}",
            "source": s,
            "translation": s,
            "success": False,
            "error": str(e)
        } for i, s in enumerate(sentences)]


def translate_single(
    sentence: str,
    target_language: str,
    task_id: str,
    model: str = "qwen2.5:32b"
) -> Dict[str, Any]:
    """
    单个翻译任务（同步）- 保留用于单句翻译

    Args:
        sentence: 源文本（中文）
        target_language: 目标语言（中文名称，如"英语"、"日语"等）
        task_id: 任务ID
        model: 模型名称

    Returns:
        dict: 翻译结果
    """
    # 直接调用批量翻译，传入单个句子
    results = translate_batch_group([sentence], target_language, task_id, model)
    if results:
        return results[0]
    else:
        return {
            "task_id": task_id,
            "source": sentence,
            "translation": sentence,
            "success": False,
            "error": "Translation failed"
        }


def parse_time_to_seconds(time_str: str) -> float:
    """将 SRT 时间戳转换为秒数"""
    try:
        # 格式: 00:00:01,500
        parts = time_str.replace(',', '.').split(':')
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0.0


def group_tasks_by_time(tasks: List[Dict], max_gap_seconds: float = 1.0, max_group_size: int = 5) -> List[List[Dict]]:
    """
    根据时间间隔对任务进行分组

    Args:
        tasks: 任务列表（需包含 start_time, end_time）
        max_gap_seconds: 最大时间间隔（秒）
        max_group_size: 每组最大任务数

    Returns:
        分组后的任务列表
    """
    if not tasks:
        return []

    # 按 index 排序确保顺序正确
    sorted_tasks = sorted(tasks, key=lambda t: t.get('index', 0))

    groups = []
    current_group = []

    for task in sorted_tasks:
        if not current_group:
            # 第一个任务，直接加入
            current_group.append(task)
        else:
            # 检查时间间隔
            prev_task = current_group[-1]
            prev_end = parse_time_to_seconds(prev_task.get('end_time', '00:00:00,000'))
            curr_start = parse_time_to_seconds(task.get('start_time', '00:00:00,000'))
            gap = curr_start - prev_end

            # 如果间隔小于阈值且组内任务数未达上限，加入当前组
            if gap <= max_gap_seconds and len(current_group) < max_group_size:
                current_group.append(task)
            else:
                # 否则，开始新组
                groups.append(current_group)
                current_group = [task]

    # 添加最后一组
    if current_group:
        groups.append(current_group)

    return groups


def batch_translate(
    tasks: List[Dict[str, str]],
    model: str = "qwen2.5:32b"
) -> List[Dict[str, Any]]:
    """
    批量翻译任务（支持上下文感知分组）

    Args:
        tasks: 任务列表，每个任务包含:
            - task_id: 任务ID
            - source: 源文本（中文）
            - target_language: 目标语言
            - start_time: 开始时间（可选，用于分组）
            - end_time: 结束时间（可选，用于分组）
            - index: 索引（用于排序）

        model: 使用的模型名称

    Returns:
        List[Dict]: 翻译结果列表
    """
    # 1. 热启动（会自动检测 Ollama 是否运行）
    try:
        warm_up(model=model)
    except Exception as e:
        print(f"❌ 无法连接到 Ollama 服务器: {e}", flush=True)
        print("请确保 Ollama 已启动（运行 'ollama serve'）", flush=True)
        return []

    total = len(tasks)
    print(f"\n[翻译] 开始翻译 {total} 条字幕...\n", flush=True)

    # 2. 根据时间间隔分组
    task_groups = group_tasks_by_time(tasks, max_gap_seconds=1.0, max_group_size=5)
    print(f"[翻译] 分组策略: {len(task_groups)} 组（时间间隔≤1秒，每组≤5句）\n", flush=True)

    # 记录总时长
    batch_start_time = time.time()
    results = []
    processed_count = 0

    # 3. 按组翻译
    for group_idx, group in enumerate(task_groups, 1):
        # 提取该组的所有句子
        sentences = [t["source"] for t in group]
        target_language = group[0]["target_language"]  # 同一组的目标语言应该相同
        group_prefix = f"group-{group_idx}"

        # 批量翻译该组
        group_results = translate_batch_group(sentences, target_language, group_prefix, model)

        # 将结果映射回原始 task_id
        for i, task in enumerate(group):
            if i < len(group_results):
                # 保留原始 task_id
                group_results[i]["task_id"] = task["task_id"]
                results.append(group_results[i])

                # 实时输出进度
                processed_count += 1
                status = "✓" if group_results[i]["success"] else "✗"
                elapsed = group_results[i].get("elapsed", 0)
                source = group_results[i]["source"][:20] + "..." if len(group_results[i]["source"]) > 20 else group_results[i]["source"]
                translation = group_results[i]["translation"][:30] + "..." if len(group_results[i]["translation"]) > 30 else group_results[i]["translation"]

                print(
                    f"[{processed_count}/{total}] {status} {group_results[i]['task_id']}: {source} -> {translation} "
                    f"({elapsed:.2f}s)",
                    flush=True
                )

    # 计算总时长
    total_elapsed = time.time() - batch_start_time
    avg_elapsed = total_elapsed / total if total > 0 else 0

    print(f"\n[翻译] ✓ 完成所有翻译", flush=True)
    print(f"[翻译] 总耗时: {total_elapsed:.2f}秒 | 平均: {avg_elapsed:.2f}秒/条\n", flush=True)

    # 卸载模型，释放GPU
    try:
        print(f"[翻译] 正在卸载模型 {model}，释放GPU...", flush=True)
        unload_response = SESSION.post(
            'http://127.0.0.1:11434/api/generate',
            json={
                'model': model,
                'keep_alive': 0
            },
            timeout=10
        )
        if unload_response.status_code == 200:
            print(f"[翻译] ✓ 模型已卸载，GPU已释放", flush=True)
    except Exception as e:
        print(f"[翻译] ⚠ 卸载模型失败: {e}", flush=True)

    return results


def main(config_path: str):
    """
    主函数

    Args:
        config_path: 配置文件路径（JSON格式）
    """
    # 读取配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    tasks = config.get("tasks", [])
    model = config.get("model", "qwen2.5:32b")

    if not tasks:
        print("❌ 没有翻译任务", flush=True)
        return

    # 执行批量翻译
    results = batch_translate(tasks, model=model)

    # 输出结果到标准输出（JSON格式）
    print("\n" + "="*60, flush=True)
    print("翻译结果（JSON）:", flush=True)
    print("="*60, flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python batch_translate_ollama.py <config.json>")
        sys.exit(1)

    config_path = sys.argv[1]

    if not os.path.exists(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        sys.exit(1)

    # 运行主函数
    main(config_path)
