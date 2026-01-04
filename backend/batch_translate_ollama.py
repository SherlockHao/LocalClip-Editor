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


def warm_up(model: str = "qwen2.5:7b"):
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


def translate_single(
    sentence: str,
    target_language: str,
    task_id: str,
    model: str = "qwen2.5:7b"
) -> Dict[str, Any]:
    """
    单个翻译任务（同步）

    Args:
        sentence: 源文本（中文）
        target_language: 目标语言（中文名称，如"英语"、"日语"等）
        task_id: 任务ID
        model: 模型名称

    Returns:
        dict: 翻译结果
    """
    # 构建 system prompt - 分离指令，效果更好
    # 所有语言都要求不含汉字（对语音克隆很重要）
    # 日语特殊要求：强制使用假名
    if '日' in target_language or 'ja' in target_language.lower():
        system_prompt = f'将中文翻译成{target_language}。要求：汉字强制用假名、语义尽量保证、输出极简、字数极少。返回 JSON 对象，Key 为 "tr"。'
    elif '韩' in target_language or 'ko' in target_language.lower():
        system_prompt = f'将中文翻译成{target_language}。要求：不含汉字、语义尽量保证、输出极简、字数极少。返回 JSON 对象，Key 为 "tr"。'
    else:
        system_prompt = f'将中文翻译成{target_language}。要求：语义尽量保证、输出极简、字数极少。返回 JSON 对象，Key 为 "tr"。'

    try:
        start_time = time.time()

        # 使用 requests 直接调用 Ollama API
        response = SESSION.post(
            OLLAMA_API_URL,
            json={
                'model': model,
                'messages': [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": sentence}
                ],
                'temperature': 0,
                'response_format': {"type": "json_object"},
                'stream': False,
                'keep_alive': -1
            },
            timeout=30
        )

        response.raise_for_status()
        result_json = response.json()
        result = result_json['choices'][0]['message']['content'].strip()

        # 提取 JSON 中的翻译结果
        translation = extract_translation_from_json(result, sentence)

        elapsed = time.time() - start_time

        return {
            "task_id": task_id,
            "source": sentence,
            "translation": translation,
            "success": True,
            "elapsed": elapsed
        }

    except Exception as e:
        print(f"[翻译错误] {task_id}: {e}", flush=True)
        return {
            "task_id": task_id,
            "source": sentence,
            "translation": sentence,  # 失败时返回原文
            "success": False,
            "error": str(e)
        }


def batch_translate(
    tasks: List[Dict[str, str]],
    model: str = "qwen2.5:7b"
) -> List[Dict[str, Any]]:
    """
    批量翻译任务

    Args:
        tasks: 任务列表，每个任务包含:
            - task_id: 任务ID
            - source: 源文本（中文）
            - target_language: 目标语言

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

    # 2. 顺序执行所有任务
    results = []
    total = len(tasks)

    print(f"\n[翻译] 开始翻译 {total} 条字幕...\n", flush=True)

    # 记录总时长
    batch_start_time = time.time()

    # 逐个翻译
    for i, task in enumerate(tasks, 1):
        result = translate_single(
            sentence=task["source"],
            target_language=task["target_language"],
            task_id=task["task_id"],
            model=model
        )
        results.append(result)

        # 实时输出进度
        status = "✓" if result["success"] else "✗"
        elapsed = result.get("elapsed", 0)
        source = result["source"][:20] + "..." if len(result["source"]) > 20 else result["source"]
        translation = result["translation"][:30] + "..." if len(result["translation"]) > 30 else result["translation"]

        print(
            f"[{i}/{total}] {status} {result['task_id']}: {source} -> {translation} "
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
    model = config.get("model", "qwen2.5:7b")

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
