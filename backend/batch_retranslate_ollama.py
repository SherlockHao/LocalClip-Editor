"""
基于 Ollama 的批量重新翻译脚本
使用异步并发，充分利用 GPU 性能
在 ui 环境中运行
"""
import sys
import os
import asyncio
import json
import time
import subprocess
import psutil
from typing import List, Dict, Any
from openai import AsyncOpenAI

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def check_ollama_running() -> bool:
    """
    检查 Ollama 服务是否在运行

    Returns:
        bool: True 如果运行中，False 如果未运行
    """
    for proc in psutil.process_iter(['name']):
        try:
            if 'ollama' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def start_ollama_server():
    """
    启动 Ollama 服务器（后台运行）
    """
    print("[Ollama] 检测到 Ollama 未运行，正在启动...", flush=True)

    try:
        # 在后台启动 ollama serve
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                ['ollama', 'serve'],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:  # Linux/Mac
            subprocess.Popen(
                ['ollama', 'serve'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

        # 等待服务器启动
        print("[Ollama] 等待服务器启动...", flush=True)
        time.sleep(3)

        # 验证是否启动成功
        if check_ollama_running():
            print("[Ollama] ✓ 服务器启动成功", flush=True)
            return True
        else:
            print("[Ollama] ⚠️  服务器启动可能失败，但继续尝试连接", flush=True)
            return True

    except FileNotFoundError:
        print("[Ollama] ❌ 错误: 找不到 ollama 命令", flush=True)
        print("[Ollama] 请确保已安装 Ollama: https://ollama.com/download", flush=True)
        return False
    except Exception as e:
        print(f"[Ollama] ⚠️  启动时出错: {e}", flush=True)
        print("[Ollama] 继续尝试连接...", flush=True)
        return True


def ensure_ollama_running():
    """
    确保 Ollama 服务正在运行
    如果未运行，则启动它
    """
    if not check_ollama_running():
        return start_ollama_server()
    else:
        print("[Ollama] ✓ 服务器已在运行", flush=True)
        return True


def unload_ollama_model(model: str = "qwen3:4b"):
    """
    卸载 Ollama 模型，释放 GPU 显存

    Args:
        model: 要卸载的模型名称
    """
    print(f"\n[Ollama] 正在卸载模型 {model}，释放 GPU 显存...", flush=True)

    try:
        # 使用 ollama 命令行工具卸载模型
        result = subprocess.run(
            ['ollama', 'stop', model],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"[Ollama] ✓ 模型 {model} 已卸载", flush=True)
        else:
            # 即使失败也继续，因为模型可能已经卸载
            print(f"[Ollama] ⚠️  卸载命令返回: {result.returncode}", flush=True)

    except FileNotFoundError:
        print("[Ollama] ⚠️  找不到 ollama 命令", flush=True)
    except subprocess.TimeoutExpired:
        print("[Ollama] ⚠️  卸载超时", flush=True)
    except Exception as e:
        print(f"[Ollama] ⚠️  卸载时出错: {e}", flush=True)

    # 额外等待确保 GPU 内存释放
    print("[Ollama] 等待 GPU 内存释放...", flush=True)
    time.sleep(2)
    print("[Ollama] ✓ GPU 清理完成\n", flush=True)


async def translate_sentence(
    client: AsyncOpenAI,
    sentence: str,
    target_language: str,
    task_id: str,
    model: str = "qwen3:4b"
) -> Dict[str, Any]:
    """
    单个翻译任务（异步）

    Args:
        client: OpenAI 客户端
        sentence: 源文本
        target_language: 目标语言
        task_id: 任务ID
        model: 模型名称

    Returns:
        dict: 翻译结果
    """
    # 构建 prompt - 使用 JSON 格式输出
    prompt = f'请将以下中文翻译成{target_language}（口语化、极简），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'

    try:
        start_time = time.time()

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 低随机性，保证翻译准确
        )

        elapsed = time.time() - start_time
        result = response.choices[0].message.content.strip()

        # 提取 JSON 中的翻译结果
        translation = extract_translation_from_json(result, sentence)

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


def extract_translation_from_json(text: str, fallback: str = "") -> str:
    """
    从JSON格式的模型输出中提取翻译结果

    支持多种格式：
    - {"tr": "翻译结果"}
    - {"tr":"翻译结果"}
    - { "tr" : "翻译结果" }
    """
    import re

    try:
        # 首先尝试直接解析整个文本为JSON
        data = json.loads(text)
        if isinstance(data, dict) and "tr" in data:
            return data["tr"].strip()
    except:
        pass

    # 尝试从文本中提取JSON对象
    json_patterns = [
        r'\{["\']tr["\']\s*:\s*["\']([^"\']+)["\']\s*\}',
        r'\{\s*"tr"\s*:\s*"([^"]+)"\s*\}',
        r'\{["\']tr["\']\s*:\s*["\']([^"\']*?)["\']\s*[,\}]',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            if result:
                return result

    # 如果没有找到JSON格式，尝试查找引号中的内容
    quote_patterns = [
        r'"([^"]{2,})"',
        r"'([^']{2,})'",
    ]

    for pattern in quote_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # 返回最长的匹配（通常是翻译结果）
            longest = max(matches, key=len)
            if len(longest) > len(fallback) / 2:
                return longest.strip()

    # 最后的回退：返回整个文本（去除可能的前缀）
    cleaned = text.replace("翻译:", "").replace("译文:", "").strip()
    if cleaned:
        return cleaned

    return fallback


async def batch_translate(
    tasks: List[Dict[str, str]],
    model: str = "qwen3:4b"
) -> List[Dict[str, Any]]:
    """
    批量翻译（异步并发）

    Args:
        tasks: 任务列表，每个任务包含 task_id, source, target_language
        model: 模型名称

    Returns:
        list: 翻译结果列表
    """
    # 创建 OpenAI 客户端（连接到本地 Ollama）
    client = AsyncOpenAI(
        base_url='http://localhost:11434/v1',
        api_key='ollama'
    )

    print(f"\n{'='*60}", flush=True)
    print(f"[批量翻译] 开始批量翻译", flush=True)
    print(f"  任务数量: {len(tasks)}", flush=True)
    print(f"  模型: {model}", flush=True)
    print(f"  并发模式: 异步", flush=True)
    print(f"{'='*60}\n", flush=True)

    # 创建所有异步任务
    start_time = time.time()

    async_tasks = [
        translate_sentence(
            client,
            task["source"],
            task["target_language"],
            task["task_id"],
            model
        )
        for task in tasks
    ]

    # 并发执行所有任务，并实时打印结果
    print("[批量翻译] 并发执行所有翻译任务...\n", flush=True)
    print("[翻译结果] 实时输出：\n", flush=True)

    results = []
    completed_count = 0

    # 使用 as_completed 实现实时输出
    for coro in asyncio.as_completed(async_tasks):
        result = await coro
        completed_count += 1
        results.append(result)

        # 立即打印当前完成的结果
        status = "✓" if result["success"] else "✗"
        elapsed = result.get("elapsed", 0)
        print(
            f"[{completed_count}/{len(async_tasks)}] {status} {result['task_id']}: "
            f"{result['source']} -> {result['translation']} "
            f"({elapsed:.2f}s)",
            flush=True
        )

    total_time = time.time() - start_time

    print(f"\n{'='*60}", flush=True)
    print(f"[批量翻译] 全部完成！", flush=True)
    print(f"  总计: {len(results)} 个任务", flush=True)
    print(f"  总耗时: {total_time:.2f} 秒", flush=True)
    print(f"  平均速度: {total_time/len(results):.2f} 秒/句", flush=True)
    print(f"{'='*60}\n", flush=True)

    return results


def retranslate_from_config(config_file: str) -> List[Dict[str, Any]]:
    """
    从配置文件读取任务并执行批量翻译

    Args:
        config_file: 配置文件路径

    Returns:
        list: 翻译结果列表
    """
    # 确保 Ollama 运行
    if not ensure_ollama_running():
        print("❌ 无法启动 Ollama，翻译终止", flush=True)
        return []

    # 读取配置
    print(f"[batch_retranslate_ollama.py] 读取配置文件: {config_file}", flush=True)

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    tasks = config["tasks"]
    model = config.get("model", "qwen3:4b")

    # 执行异步批量翻译
    results = asyncio.run(batch_translate(tasks, model))

    # 卸载模型，释放 GPU 显存
    unload_ollama_model(model)

    # 输出 JSON 结果（供 main.py 解析）
    print(json.dumps(results, ensure_ascii=False))

    return results


if __name__ == "__main__":
    print("[batch_retranslate_ollama.py] 脚本启动", flush=True)

    if len(sys.argv) < 2:
        print("Usage: python batch_retranslate_ollama.py <config_file>", flush=True)
        print("Config file format (JSON):", flush=True)
        print("""
{
    "tasks": [
        {
            "task_id": "task-1",
            "source": "原文（中文）",
            "target_language": "韩文"
        }
    ],
    "model": "qwen3:4b"
}
        """, flush=True)
        sys.exit(1)

    config_file = sys.argv[1]
    retranslate_from_config(config_file)
