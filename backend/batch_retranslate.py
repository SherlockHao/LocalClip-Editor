"""
批量重新翻译脚本
用于处理长度超标的译文，使用 LLM 重新翻译为更简洁的版本
在 qwen_inference 环境中运行
"""
import sys
import os

# 强制 UTF-8 输出，避免 Windows 控制台编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import json
import multiprocessing as mp
from multiprocessing import Process, Queue
import time
import threading
from typing import List, Dict, Any
import re


def load_model(model_path: str):
    """
    加载模型和分词器

    Args:
        model_path: 模型路径

    Returns:
        tuple: (tokenizer, model)
    """
    print(f"[PID {os.getpid()}] Loading model from {model_path}...")

    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    print(f"[PID {os.getpid()}] Model loaded on device: {model.device}")
    return tokenizer, model


def translate_task(
    tokenizer,
    model,
    source_text: str,
    target_language: str,
    task_id: str
) -> Dict[str, Any]:
    """
    执行单个翻译任务

    Args:
        tokenizer: 分词器
        model: 模型
        source_text: 原文（中文）
        target_language: 目标语言代码（如 "en", "ja" 等）
        task_id: 任务ID

    Returns:
        dict: 翻译结果
    """
    # 语言代码到中文名称的映射
    language_map = {
        "en": "英文",
        "english": "英文",
        "ja": "日文",
        "japanese": "日文",
        "ko": "韩文",
        "korean": "韩文",
        "fr": "法文",
        "french": "法文",
        "de": "德文",
        "german": "德文",
        "es": "西班牙文",
        "spanish": "西班牙文",
        "ru": "俄文",
        "russian": "俄文",
        "zh": "中文",
        "chinese": "中文",
    }

    # 转换语言代码为中文名称
    target_language_lower = target_language.lower()
    language_name = language_map.get(target_language_lower, target_language)

    # 简洁的 prompt - 直接要求翻译，不要思考过程
    prompt = f"请将以下中文翻译成{language_name}，要求简洁且口语化，直接输出翻译结果，不要解释：\n\n{source_text}"
    messages = [{"role": "user", "content": prompt}]

    print(f"\n[Task {task_id}] Target language: {target_language} -> {language_name}")
    print(f"[Task {task_id}] Prompt: {prompt}")

    # 准备输入
    formatted_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    model_inputs = tokenizer([formatted_text], return_tensors="pt").to(model.device)

    print(f"[Task {task_id}] Formatted input length: {len(model_inputs.input_ids[0])}")

    # 生成翻译
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=128,
        do_sample=True,
        temperature=0.7
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
    raw_translation = tokenizer.decode(output_ids, skip_special_tokens=True).strip("\n")

    # 打印原始翻译（调试）
    print(f"\n[Task {task_id}] 原始翻译: '{raw_translation}'")

    # 后处理：移除思考过程
    translation = remove_thinking_process(raw_translation)

    # 打印清理后的翻译（调试）
    print(f"[Task {task_id}] 清理后翻译: '{translation}'")

    # 如果翻译为空，使用原文
    if not translation or translation.strip() == "":
        print(f"[Task {task_id}] ⚠️  翻译结果为空，使用原文")
        translation = source_text

    return {
        "task_id": task_id,
        "source": source_text,
        "translation": translation,
        "pid": os.getpid()
    }


def remove_thinking_process(text: str) -> str:
    """
    移除模型输出中的思考过程
    处理 <think>...</think> 或 <thinking>...</thinking> 标签

    Args:
        text: 原始文本

    Returns:
        str: 清理后的文本
    """
    # 移除 <think>...</think> 标签及其内容
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 移除未闭合的 <think> 或 <thinking> 标签及其后面的所有内容
    text = re.sub(r'<think>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thinking>.*', '', text, flags=re.DOTALL | re.IGNORECASE)

    # 清理多余的空白
    text = text.strip()

    return text


def worker_process(
    process_id: int,
    task_queue: Queue,
    result_queue: Queue,
    model_path: str
):
    """
    工作进程函数
    每个进程加载一次模型，然后处理分配给它的所有任务

    Args:
        process_id: 进程ID
        task_queue: 任务队列
        result_queue: 结果队列
        model_path: 模型路径
    """
    print(f"\n{'='*60}")
    print(f"Process {process_id} (PID {os.getpid()}) starting...")
    print(f"{'='*60}")

    # 在进程内加载模型（每个进程只加载一次）
    tokenizer, model = load_model(model_path)

    task_count = 0

    # 从队列中获取任务并处理
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task is None:  # 结束信号
                break

            task_id = task["task_id"]
            source_text = task["source"]
            target_language = task["target_language"]

            task_count += 1

            print(f"[Process {process_id}] Processing task {task_id}...")
            start_time = time.time()

            result = translate_task(tokenizer, model, source_text, target_language, task_id)
            elapsed = time.time() - start_time

            result["process_id"] = process_id
            result["time"] = elapsed
            result["target_language"] = target_language

            # 立即将结果放入队列
            result_queue.put(result)

            print(f"[Process {process_id}] Task {task_id} completed in {elapsed:.2f}s")

        except Exception as e:
            print(f"[Process {process_id}] Error: {e}")
            import traceback
            traceback.print_exc()
            break

    print(f"\n[Process {process_id}] Finished processing {task_count} tasks")


def result_collector(result_queue: Queue, total_tasks: int) -> List[Dict[str, Any]]:
    """
    结果收集函数
    实时从结果队列中获取结果

    Args:
        result_queue: 结果队列
        total_tasks: 总任务数

    Returns:
        list: 所有结果
    """
    all_results = []
    collected_count = 0

    print("\n" + "="*60)
    print("RE-TRANSLATION RESULTS (Real-time)")
    print("="*60)

    while collected_count < total_tasks:
        try:
            result = result_queue.get(timeout=1)
            all_results.append(result)
            collected_count += 1

            # 立即打印结果
            print(f"\n[{result['task_id']}] (Process {result['process_id']}, {result['time']:.2f}s)")
            print(f"原文: {result['source']}")
            print(f"译文: {result['translation']}")
            print("-"*60)

        except:
            continue

    return all_results


def run_batch_retranslation(
    tasks: List[Dict[str, Any]],
    model_path: str,
    num_processes: int = 1
) -> List[Dict[str, Any]]:
    """
    执行批量重新翻译

    Args:
        tasks: 任务列表，每个任务包含 {"task_id": "...", "source": "...", "target_language": "..."}
        model_path: 模型路径
        num_processes: 使用的进程数

    Returns:
        list: 翻译结果列表
    """
    if not tasks:
        print("No tasks to process")
        return []

    print("="*60)
    print("BATCH RE-TRANSLATION WITH MULTIPROCESSING")
    print("="*60)
    print(f"Total tasks: {len(tasks)}")
    print(f"Number of processes: {num_processes}")
    print(f"Model path: {model_path}")
    print("="*60)

    # 创建任务队列和结果队列
    task_queue = Queue()
    result_queue = Queue()

    # 将任务放入队列
    for task in tasks:
        task_queue.put(task)

    # 为每个进程添加结束信号
    for _ in range(num_processes):
        task_queue.put(None)

    # 启动结果收集线程
    start_time = time.time()
    result_list = []

    def collect_results():
        nonlocal result_list
        result_list = result_collector(result_queue, len(tasks))

    collector_thread = threading.Thread(target=collect_results)
    collector_thread.start()

    # 启动工作进程
    processes = []

    for i in range(num_processes):
        p = Process(
            target=worker_process,
            args=(i+1, task_queue, result_queue, model_path)
        )
        p.start()
        processes.append(p)

    # 等待所有进程完成
    for p in processes:
        p.join()

    # 等待结果收集线程完成
    collector_thread.join()

    total_time = time.time() - start_time
    all_results = result_list

    # 统计信息
    print(f"\n{'='*60}")
    print("STATISTICS")
    print("="*60)
    print(f"Total tasks: {len(all_results)}")
    print(f"Total time: {total_time:.2f}s")
    if tasks:
        print(f"Average time per task: {total_time/len(tasks):.2f}s")

    # 按进程统计
    process_stats = {}
    for result in all_results:
        pid = result['process_id']
        if pid not in process_stats:
            process_stats[pid] = []
        process_stats[pid].append(result['time'])

    for pid, times in sorted(process_stats.items()):
        avg_time = sum(times)/len(times) if times else 0
        print(f"Process {pid}: {len(times)} tasks, avg {avg_time:.2f}s per task")

    print("="*60)

    return all_results


def retranslate_from_config(config_file: str) -> List[Dict[str, Any]]:
    """
    从配置文件读取任务并执行批量重新翻译

    Args:
        config_file: 配置文件路径（JSON格式）

    Returns:
        list: 翻译结果列表
    """
    # 读取配置
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    tasks = config["tasks"]
    model_path = config.get("model_path")
    num_processes = config.get("num_processes", 1)

    # 如果没有指定模型路径，使用默认路径
    if not model_path:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        models_dir = os.path.join(script_dir, "models")
        model_path = os.path.join(models_dir, "Qwen3-1.7B")

    return run_batch_retranslation(tasks, model_path, num_processes)


if __name__ == "__main__":
    import sys

    # 设置multiprocessing启动方法
    mp.set_start_method('spawn', force=True)

    if len(sys.argv) < 2:
        print("Usage: python batch_retranslate.py <config_file>")
        print("Config file format (JSON):")
        print("""
{
    "tasks": [
        {
            "task_id": "task-1",
            "source": "原文（中文）",
            "target_language": "英文"
        }
    ],
    "model_path": "path/to/model",
    "num_processes": 1
}
        """)
        sys.exit(1)

    config_file = sys.argv[1]
    results = retranslate_from_config(config_file)

    # 输出结果（JSON格式）
    print("\n" + "="*60)
    print("FINAL RESULTS (JSON)")
    print("="*60)
    print(json.dumps(results, ensure_ascii=False, indent=2))
