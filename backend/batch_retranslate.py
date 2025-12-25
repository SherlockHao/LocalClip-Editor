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
import queue
import time
import threading
from typing import List, Dict, Any, Tuple
import re


def get_gpu_memory_gb() -> float:
    """
    获取GPU可用显存（GB）

    Returns:
        float: 可用显存大小（GB），如果没有GPU返回0
    """
    if not torch.cuda.is_available():
        print("[GPU检测] 没有检测到可用的CUDA设备", flush=True)
        return 0.0

    try:
        # 获取第一个GPU的总显存
        gpu_memory = torch.cuda.get_device_properties(0).total_memory
        gpu_memory_gb = gpu_memory / (1024 ** 3)

        # 获取已用显存
        allocated = torch.cuda.memory_allocated(0) / (1024 ** 3)
        reserved = torch.cuda.memory_reserved(0) / (1024 ** 3)

        available_gb = gpu_memory_gb - reserved

        print(f"[GPU检测] GPU显存信息:", flush=True)
        print(f"  总显存: {gpu_memory_gb:.2f} GB", flush=True)
        print(f"  已分配: {allocated:.2f} GB", flush=True)
        print(f"  已保留: {reserved:.2f} GB", flush=True)
        print(f"  可用: {available_gb:.2f} GB", flush=True)

        return available_gb
    except Exception as e:
        print(f"[GPU检测] 获取GPU信息失败: {e}", flush=True)
        return 0.0


def check_model_files(model_path: str) -> bool:
    """
    检查模型文件是否完整

    Args:
        model_path: 模型目录路径

    Returns:
        bool: 文件完整返回True，否则返回False
    """
    required_files = ["config.json", "tokenizer_config.json"]

    for file in required_files:
        file_path = os.path.join(model_path, file)
        if not os.path.exists(file_path):
            return False

        # 检查文件大小（至少应该大于0）
        if os.path.getsize(file_path) == 0:
            return False

    # 检查是否有模型权重文件
    has_weights = False
    for file in os.listdir(model_path):
        if file.endswith('.safetensors') or file.endswith('.bin'):
            # 检查文件大小（至少10MB）
            file_path = os.path.join(model_path, file)
            if os.path.getsize(file_path) > 10 * 1024 * 1024:
                has_weights = True
                break

    return has_weights


def select_model_by_gpu(models_dir: str) -> str:
    """
    根据GPU显存自动选择合适的模型

    优先级：
    1. Qwen3-1.7B (稳定，需要约4GB显存) - 优先使用
    2. Qwen3-4B-FP8 (需要约6GB显存)
    3. Qwen3-4B (需要约8GB显存)

    Args:
        models_dir: 模型根目录

    Returns:
        str: 选择的模型路径
    """
    available_memory = get_gpu_memory_gb()

    # 定义模型及其显存需求（GB）
    # 优先使用 4B FP8 模型以获得最佳翻译质量
    models = [
        ("Qwen3-4B-FP8", 6.0),      # 4B FP8模型，翻译质量最优
        ("Qwen3-4B", 8.0),          # 4B FP16模型
        ("Qwen3-1.7B", 4.0),        # 1.7B模型，显存不足时的回退选项
    ]

    print(f"\n[模型选择] 可用显存: {available_memory:.2f} GB", flush=True)

    # 按优先级选择
    for model_name, required_memory in models:
        model_path = os.path.join(models_dir, model_name)

        # 检查模型是否存在
        if not os.path.exists(model_path):
            print(f"[模型选择] ✗ {model_name} 不存在 (路径: {model_path})", flush=True)
            continue

        # 检查模型文件完整性
        if not check_model_files(model_path):
            print(f"[模型选择] ✗ {model_name} 文件不完整或损坏", flush=True)
            continue

        # 检查显存是否足够
        if available_memory >= required_memory:
            print(f"[模型选择] ✓ 选择 {model_name} (需要 {required_memory:.1f} GB, 可用 {available_memory:.2f} GB)", flush=True)
            return model_path
        else:
            print(f"[模型选择] ✗ {model_name} 显存不足 (需要 {required_memory:.1f} GB, 可用 {available_memory:.2f} GB)", flush=True)

    # 如果所有模型都不满足，使用最小的模型作为回退
    fallback_model = os.path.join(models_dir, "Qwen3-1.7B")
    print(f"[模型选择] ⚠ 没有可用模型，尝试使用: Qwen3-1.7B", flush=True)
    return fallback_model


def load_model(model_path: str):
    """
    加载模型和分词器

    Args:
        model_path: 模型路径

    Returns:
        tuple: (tokenizer, model)
    """
    # 设置环境变量禁用 HuggingFace Hub（在导入之前设置）
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TRANSFORMERS_OFFLINE'] = '1'
    os.environ['HF_DATASETS_OFFLINE'] = '1'

    print(f"[PID {os.getpid()}] Loading model from {model_path}...", flush=True)

    # 确保路径存在
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model path does not exist: {model_path}")

    # 检查必需的文件是否存在
    tokenizer_config = os.path.join(model_path, "tokenizer_config.json")
    if not os.path.exists(tokenizer_config):
        raise FileNotFoundError(f"tokenizer_config.json not found in {model_path}")

    try:
        # 尝试使用本地路径加载（禁用所有远程调用）
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=True,
            use_fast=True
        )
        print(f"[PID {os.getpid()}] Tokenizer loaded, loading model...", flush=True)

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            local_files_only=True
        )

        print(f"[PID {os.getpid()}] Model loaded on device: {model.device}", flush=True)
        return tokenizer, model

    except Exception as e:
        print(f"[PID {os.getpid()}] Error loading model: {str(e)}", flush=True)
        print(f"[PID {os.getpid()}] Model path: {model_path}", flush=True)
        print(f"[PID {os.getpid()}] Path exists: {os.path.exists(model_path)}", flush=True)
        print(f"[PID {os.getpid()}] Files in directory:", flush=True)
        if os.path.exists(model_path):
            for f in os.listdir(model_path):
                print(f"  - {f}", flush=True)
        raise


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

    # JSON格式 prompt - 强制JSON输出避免思考过程
    prompt = f'请将以下中文翻译成{language_name}（口语化、极简），以 JSON 格式输出，Key 为 "tr"：\n\n{source_text}'
    messages = [{"role": "user", "content": prompt}]

    print(f"\n[Task {task_id}] Prompt: {prompt}", flush=True)

    # 准备输入
    formatted_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([formatted_text], return_tensors="pt").to(model.device)

    # 生成翻译
    print(f"[Task {task_id}] 开始生成...", flush=True)
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=128,
        do_sample=True,
        temperature=0.7
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
    raw_translation = tokenizer.decode(output_ids, skip_special_tokens=True).strip()

    print(f"[Task {task_id}] 模型输出: '{raw_translation}'", flush=True)

    # 后处理：从JSON中提取翻译结果
    translation = extract_translation_from_json(raw_translation, source_text)

    print(f"[Task {task_id}] 最终输出: '{translation}'", flush=True)

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


def extract_translation_from_json(text: str, fallback: str = "") -> str:
    """
    从JSON格式的模型输出中提取翻译结果

    支持多种格式：
    - {"tr": "翻译结果"}
    - {"tr":"翻译结果"}
    - { "tr" : "翻译结果" }
    - 带有其他内容的JSON

    Args:
        text: 模型输出的文本
        fallback: 解析失败时的备用文本

    Returns:
        str: 提取的翻译结果，失败时返回fallback
    """
    try:
        # 首先尝试直接解析整个文本为JSON
        data = json.loads(text)
        if isinstance(data, dict) and "tr" in data:
            return data["tr"].strip()
    except:
        pass

    # 尝试从文本中提取JSON对象
    # 查找 {"tr": "..."} 或 {'tr': '...'} 格式
    json_patterns = [
        r'\{["\']tr["\']\s*:\s*["\']([^"\']+)["\']\s*\}',  # {"tr": "xxx"} 或 {'tr': 'xxx'}
        r'\{\s*"tr"\s*:\s*"([^"]+)"\s*\}',                  # { "tr" : "xxx" }
        r'\{["\']tr["\']\s*:\s*["\']([^"\']*?)["\']\s*[,\}]',  # 带逗号的情况
    ]

    for pattern in json_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            result = match.group(1).strip()
            if result:
                return result

    # 如果找到 "tr": 但没有完整JSON，尝试提取引号内的内容
    tr_match = re.search(r'"tr"\s*:\s*"([^"]+)"', text, re.DOTALL)
    if tr_match:
        return tr_match.group(1).strip()

    # 移除可能的思考标签作为最后的尝试
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'<thinking>.*?</thinking>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = cleaned.strip()

    # 如果清理后有内容且不像是错误信息，返回清理后的文本
    if cleaned and not cleaned.startswith('{') and len(cleaned) < 200:
        return cleaned

    # 所有方法都失败，返回备用文本
    print(f"⚠️  无法从输出中提取翻译: {text[:100]}...", flush=True)
    return fallback


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
    print(f"[Worker {process_id}] 进程启动，准备加载模型...", flush=True)
    # 在进程内加载模型（每个进程只加载一次）
    tokenizer, model = load_model(model_path)
    print(f"[Worker {process_id}] 模型加载完成，开始处理任务", flush=True)

    task_count = 0

    # 从队列中获取任务并处理
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task is None:  # 结束信号
                print(f"[Worker {process_id}] 收到结束信号，退出", flush=True)
                break

            task_id = task["task_id"]
            source_text = task["source"]
            target_language = task["target_language"]

            task_count += 1
            start_time = time.time()

            print(f"[Worker {process_id}] 开始处理任务 {task_id}: {source_text[:20]}...", flush=True)
            result = translate_task(tokenizer, model, source_text, target_language, task_id)
            elapsed = time.time() - start_time

            result["process_id"] = process_id
            result["time"] = elapsed
            result["target_language"] = target_language

            # 立即将结果放入队列
            result_queue.put(result)
            print(f"[Worker {process_id}] 完成任务 {task_id}，耗时 {elapsed:.2f}秒", flush=True)

        except queue.Empty:
            # 队列超时，继续等待
            continue
        except Exception as e:
            print(f"[Worker {process_id}] 任务处理出错: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # 不要break，继续处理下一个任务
            continue


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

    print(f"\n[结果收集] 开始收集 {total_tasks} 个翻译结果...", flush=True)

    while collected_count < total_tasks:
        try:
            result = result_queue.get(timeout=30)  # 增加超时时间
            all_results.append(result)
            collected_count += 1

            # 实时打印每一条翻译结果
            print(f"[{collected_count}/{total_tasks}] {result['task_id']}: {result['source']} -> {result['translation']}", flush=True)

        except queue.Empty:
            print(f"[结果收集] 等待中... 已收集 {collected_count}/{total_tasks}", flush=True)
            continue
        except Exception as e:
            print(f"[结果收集] 错误: {e}", flush=True)
            continue

    print(f"[结果收集] 完成！共收集 {len(all_results)} 个结果\n", flush=True)
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
        print("[批量翻译] 没有任务需要处理", flush=True)
        return []

    print(f"\n{'='*60}", flush=True)
    print(f"[批量翻译] 开始批量翻译", flush=True)
    print(f"  任务数量: {len(tasks)}", flush=True)
    print(f"  进程数量: {num_processes}", flush=True)
    print(f"  模型路径: {model_path}", flush=True)
    print(f"{'='*60}\n", flush=True)

    # 创建任务队列和结果队列
    task_queue = Queue()
    result_queue = Queue()

    # 将任务放入队列
    for i, task in enumerate(tasks, 1):
        task_queue.put(task)
        print(f"[任务队列] 添加任务 {i}: {task.get('task_id', 'unknown')}", flush=True)

    # 为每个进程添加结束信号
    for _ in range(num_processes):
        task_queue.put(None)

    # 启动结果收集线程
    result_list = []

    def collect_results():
        nonlocal result_list
        result_list = result_collector(result_queue, len(tasks))

    collector_thread = threading.Thread(target=collect_results)
    collector_thread.daemon = False
    collector_thread.start()

    # 启动工作进程
    processes = []
    print(f"\n[进程管理] 启动 {num_processes} 个工作进程...", flush=True)

    for i in range(num_processes):
        p = Process(
            target=worker_process,
            args=(i+1, task_queue, result_queue, model_path)
        )
        p.start()
        processes.append(p)
        print(f"[进程管理] Worker {i+1} 已启动 (PID: {p.pid})", flush=True)

    # 等待所有进程完成
    print(f"\n[进程管理] 等待所有工作进程完成...", flush=True)
    for i, p in enumerate(processes, 1):
        p.join()
        print(f"[进程管理] Worker {i} 已结束", flush=True)

    # 等待结果收集线程完成
    print(f"[进程管理] 等待结果收集线程完成...", flush=True)
    collector_thread.join()

    all_results = result_list
    print(f"\n{'='*60}", flush=True)
    print(f"[批量翻译] 全部完成！共处理 {len(all_results)} 个任务", flush=True)
    print(f"{'='*60}\n", flush=True)

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

    # 如果没有指定模型路径，根据GPU显存自动选择
    if not model_path:
        # 路径: backend -> LocalClip-Editor -> workspace -> ai_editing
        backend_dir = os.path.dirname(os.path.abspath(__file__))  # backend
        localclip_dir = os.path.dirname(backend_dir)  # LocalClip-Editor
        workspace_dir = os.path.dirname(localclip_dir)  # workspace
        ai_editing_dir = os.path.dirname(workspace_dir)  # ai_editing
        models_dir = os.path.join(ai_editing_dir, "models")
        model_path = select_model_by_gpu(models_dir)

    return run_batch_retranslation(tasks, model_path, num_processes)


if __name__ == "__main__":
    import sys

    print("[batch_retranslate.py] 脚本启动", flush=True)

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
    print(f"[batch_retranslate.py] 读取配置文件: {config_file}", flush=True)
    results = retranslate_from_config(config_file)
    print(f"[batch_retranslate.py] 翻译完成，结果数量: {len(results)}", flush=True)

    # 输出结果（JSON格式）
    print("\n" + "="*60)
    print("FINAL RESULTS (JSON)")
    print("="*60)
    print(json.dumps(results, ensure_ascii=False, indent=2))
