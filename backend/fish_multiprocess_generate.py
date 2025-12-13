"""
多进程批量生成脚本 - 按说话人并行处理
充分利用多GPU或单GPU的显存，每个进程处理一个说话人
在 fish-speech 环境中运行
"""
import os
import sys
import json
import torch
import multiprocessing as mp
from typing import Dict, List, Any

# CUDA 优化配置
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
os.environ['CUDA_MODULE_LOADING'] = 'LAZY'
os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0+PTX'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

import numpy as np
import soundfile as sf


def worker_process(
    worker_id: int,
    gpu_id: int,
    assigned_speakers: List[tuple],  # [(speaker_id, speaker_tasks), ...]
    fish_speech_dir: str,
    checkpoint_dir: str,
    result_queue: mp.Queue
):
    """
    工作进程：加载模型一次，处理分配给它的所有说话人

    Args:
        worker_id: 工作进程 ID
        gpu_id: 分配的 GPU ID
        assigned_speakers: 分配给该 worker 的说话人列表 [(speaker_id, speaker_tasks), ...]
        fish_speech_dir: fish-speech 目录
        checkpoint_dir: 模型检查点目录
        result_queue: 结果队列
    """
    try:
        # 直接使用指定的 GPU 设备（不使用 CUDA_VISIBLE_DEVICES，支持同一 GPU 多进程）
        device = f"cuda:{gpu_id}" if torch.cuda.is_available() else "cpu"

        total_tasks = sum(len(tasks) for _, tasks in assigned_speakers)
        print(f"[Worker {worker_id}] Starting on {device}", file=sys.stderr, flush=True)
        print(f"[Worker {worker_id}] Assigned {len(assigned_speakers)} speakers, {total_tasks} texts total", file=sys.stderr, flush=True)

        # 设置当前进程的默认设备
        if torch.cuda.is_available():
            torch.cuda.set_device(gpu_id)

        # 添加 fish-speech 到路径
        if fish_speech_dir not in sys.path:
            sys.path.insert(0, fish_speech_dir)

        # 导入模块
        from fish_speech.models.text2semantic.inference import init_model, generate_long
        from fish_speech.models.dac.inference import load_model as load_dac_model

        # 加载模型（只加载一次！）
        precision = torch.bfloat16
        print(f"[Worker {worker_id}] Loading Text2Semantic model...", file=sys.stderr, flush=True)
        llama_model, decode_one_token = init_model(
            checkpoint_path=checkpoint_dir,
            device=device,
            precision=precision,
            compile=False
        )

        print(f"[Worker {worker_id}] Loading DAC model...", file=sys.stderr, flush=True)
        dac_model = load_dac_model(
            config_name="modded_dac_vq",
            checkpoint_path=os.path.join(checkpoint_dir, "codec.pth"),
            device=device
        )

        print(f"[Worker {worker_id}] Models loaded! Starting generation...", file=sys.stderr, flush=True)

        # 处理分配的所有说话人
        results = {}
        processed_count = 0

        for speaker_idx, (speaker_id, speaker_tasks) in enumerate(assigned_speakers):
            print(f"\n[Worker {worker_id}] Processing Speaker {speaker_id} ({speaker_idx+1}/{len(assigned_speakers)})", file=sys.stderr, flush=True)
            print(f"[Worker {worker_id}] This speaker has {len(speaker_tasks)} texts", file=sys.stderr, flush=True)

            # 获取该说话人的 npy 文件和参考文本
            npy_file = speaker_tasks[0]["npy_file"]
            reference_text = speaker_tasks[0]["reference_text"]

            # 加载 prompt tokens（每个说话人加载一次）
            prompt_tokens = np.load(npy_file)
            prompt_tokens = torch.from_numpy(prompt_tokens).to(device).long()
            if prompt_tokens.ndim == 3:
                prompt_tokens = prompt_tokens[0]

            # 处理该说话人的所有文本
            for i, task in enumerate(speaker_tasks):
                segment_index = task["segment_index"]
                target_text = task["target_text"]
                output_file = task["output_file"]

                if (i + 1) % 5 == 0 or i == 0:
                    print(f"[Worker {worker_id}] Speaker {speaker_id} progress: {i+1}/{len(speaker_tasks)}", file=sys.stderr, flush=True)

                try:
                    # 文本转语义 Token
                    codes = None
                    for response in generate_long(
                        model=llama_model,
                        device=device,
                        decode_one_token=decode_one_token,
                        text=target_text,
                        prompt_text=reference_text,
                        prompt_tokens=prompt_tokens,
                        max_new_tokens=1024,
                        top_p=0.7,
                        temperature=0.7,
                        repetition_penalty=1.2,
                        num_samples=1
                    ):
                        if response.action == "sample":
                            codes = response.codes
                            break

                    if codes is None:
                        print(f"[Worker {worker_id}] ❌ No codes for segment {segment_index}", file=sys.stderr, flush=True)
                        continue

                    # 语义 Token 转语音
                    if codes.ndim == 2:
                        codes = codes.unsqueeze(0)

                    codes_lens = torch.tensor([codes.shape[-1]], device=device, dtype=torch.long)

                    with torch.no_grad():
                        fake_audios, _ = dac_model.decode(codes, codes_lens)

                    # 保存音频
                    fake_audio = fake_audios[0, 0].float().cpu().numpy()
                    sf.write(output_file, fake_audio, dac_model.sample_rate)

                    results[segment_index] = output_file
                    processed_count += 1

                    # 清理显存
                    del codes, fake_audios, fake_audio
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

                except Exception as e:
                    print(f"[Worker {worker_id}] ❌ Error on segment {segment_index}: {e}", file=sys.stderr, flush=True)
                    import traceback
                    traceback.print_exc(file=sys.stderr)
                    continue

            # 清理该说话人的 prompt tokens
            del prompt_tokens
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

            print(f"[Worker {worker_id}] ✅ Completed Speaker {speaker_id}: {len([r for r in results.values() if r])} segments", file=sys.stderr, flush=True)

        # 清理模型
        del llama_model, decode_one_token, dac_model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        print(f"[Worker {worker_id}] ✅ All done! Processed {processed_count}/{total_tasks} segments", file=sys.stderr, flush=True)

        # 将结果放入队列
        result_queue.put(results)

    except Exception as e:
        print(f"[Worker {worker_id}] ❌ Fatal error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        result_queue.put({})


def get_gpu_info():
    """获取 GPU 信息，返回可用的 GPU 数量和每个 GPU 的显存"""
    if not torch.cuda.is_available():
        return 0, []

    gpu_count = torch.cuda.device_count()
    gpu_memory = []

    for i in range(gpu_count):
        props = torch.cuda.get_device_properties(i)
        total_memory_gb = props.total_memory / 1024**3
        gpu_memory.append(total_memory_gb)
        print(f"[GPU {i}] {props.name}, Total Memory: {total_memory_gb:.2f} GB", file=sys.stderr)

    return gpu_count, gpu_memory


def calculate_worker_count(gpu_count: int, gpu_memory: List[float], speaker_count: int):
    """
    计算可以并行的 worker 数量

    策略：
    - 每个 GPU 根据显存大小运行多个 worker
    - 模型大约需要 6-8 GB 显存
    - 自动计算每个 GPU 可以容纳的 worker 数量
    """
    if gpu_count == 0:
        return 1, [0]  # CPU 模式，只用 1 个进程，返回 (worker_count, gpu_assignment)

    # 估算每个模型实例需要的显存 (可以从环境变量配置)
    model_memory_gb = float(os.environ.get("FISH_MODEL_MEMORY_GB", "8.0"))

    # 计算每个 GPU 可以运行的 worker 数
    workers_per_gpu = []
    total_workers = 0

    for i, memory_gb in enumerate(gpu_memory):
        # 留 10% 余量
        available_memory = memory_gb * 0.9
        max_workers_on_gpu = max(1, int(available_memory / model_memory_gb))
        workers_per_gpu.append(max_workers_on_gpu)
        total_workers += max_workers_on_gpu
        print(f"[GPU {i}] Can run {max_workers_on_gpu} workers (Available: {available_memory:.2f} GB)", file=sys.stderr)

    # 限制总 worker 数不超过说话人数量
    if total_workers > speaker_count:
        # 按比例缩减
        scale_factor = speaker_count / total_workers
        workers_per_gpu = [max(1, int(w * scale_factor)) for w in workers_per_gpu]
        total_workers = sum(workers_per_gpu)

    # 创建 GPU 分配方案 (worker_id -> gpu_id)
    gpu_assignment = []
    for gpu_id, num_workers in enumerate(workers_per_gpu):
        gpu_assignment.extend([gpu_id] * num_workers)

    # 限制到说话人数量
    gpu_assignment = gpu_assignment[:speaker_count]
    actual_workers = len(gpu_assignment)

    return actual_workers, gpu_assignment


def main():
    if len(sys.argv) < 2:
        print("Usage: python fish_multiprocess_generate.py <config_file>", file=sys.stderr)
        sys.exit(1)

    # 读取配置
    config_file = sys.argv[1]
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    fish_speech_dir = config["fish_speech_dir"]
    checkpoint_dir = config["checkpoint_dir"]
    tasks = config["tasks"]

    print(f"[Main] Total tasks: {len(tasks)}", file=sys.stderr)

    # 获取 GPU 信息
    gpu_count, gpu_memory = get_gpu_info()

    # 按说话人分组任务
    from collections import defaultdict
    tasks_by_speaker = defaultdict(list)
    for task in tasks:
        speaker_id = task["speaker_id"]
        tasks_by_speaker[speaker_id].append(task)

    speaker_count = len(tasks_by_speaker)
    print(f"[Main] Speakers: {speaker_count}", file=sys.stderr)

    # 计算 worker 数量和 GPU 分配
    worker_count, gpu_assignment = calculate_worker_count(gpu_count, gpu_memory, speaker_count)
    print(f"[Main] Using {worker_count} parallel workers across {gpu_count} GPU(s)", file=sys.stderr)

    # 显示 GPU 分配详情
    if gpu_count > 0:
        from collections import Counter
        gpu_distribution = Counter(gpu_assignment)
        for gpu_id, count in sorted(gpu_distribution.items()):
            print(f"[Main] GPU {gpu_id}: {count} workers", file=sys.stderr)

    # 创建结果队列
    result_queue = mp.Queue()

    # 创建进程池
    processes = []
    all_results = {}

    speaker_items = list(tasks_by_speaker.items())

    # 按工作量（文本数量）智能分配说话人给 workers
    # 使用贪心算法：总是分配给当前工作量最少的 worker
    worker_assignments = [[] for _ in range(worker_count)]
    worker_loads = [0] * worker_count  # 每个 worker 的总文本数

    # 先按文本数量降序排序说话人（大任务优先分配）
    speaker_items_sorted = sorted(speaker_items, key=lambda x: len(x[1]), reverse=True)

    print(f"\n[Main] Speaker workload analysis:", file=sys.stderr)
    for speaker_id, speaker_tasks in speaker_items_sorted:
        print(f"  Speaker {speaker_id}: {len(speaker_tasks)} texts", file=sys.stderr)

    # 贪心分配：每次将当前说话人分配给工作量最少的 worker
    for speaker_id, speaker_tasks in speaker_items_sorted:
        # 找到当前工作量最少的 worker
        min_load_worker = worker_loads.index(min(worker_loads))

        # 分配给该 worker
        worker_assignments[min_load_worker].append((speaker_id, speaker_tasks))
        worker_loads[min_load_worker] += len(speaker_tasks)

    # 显示分配详情
    print(f"\n[Main] Speaker assignment (load-balanced):", file=sys.stderr)
    for worker_idx, assigned in enumerate(worker_assignments):
        speaker_ids = [sid for sid, _ in assigned]
        total_texts = sum(len(tasks) for _, tasks in assigned)
        print(f"  Worker {worker_idx}: {len(assigned)} speakers (IDs: {speaker_ids}), {total_texts} texts", file=sys.stderr)

    # 启动所有 worker 进程
    print(f"\n[Main] Launching {worker_count} workers...", file=sys.stderr)
    processes = []
    for worker_id in range(worker_count):
        gpu_id = gpu_assignment[worker_id] if worker_id < len(gpu_assignment) else 0
        assigned_speakers = worker_assignments[worker_id]

        if not assigned_speakers:
            # 没有分配任何说话人，跳过
            continue

        print(f"[Main] Launching Worker {worker_id} on GPU {gpu_id}", file=sys.stderr, flush=True)

        p = mp.Process(
            target=worker_process,
            args=(worker_id, gpu_id, assigned_speakers, fish_speech_dir, checkpoint_dir, result_queue)
        )
        p.start()
        processes.append(p)

    # 等待所有进程完成
    print(f"\n[Main] Waiting for all workers to complete...", file=sys.stderr)
    for p in processes:
        p.join()

    # 收集结果
    print(f"[Main] Collecting results...", file=sys.stderr)
    for _ in range(len(processes)):
        result = result_queue.get()
        all_results.update(result)

    print(f"\n[Main] All done! Generated {len(all_results)}/{len(tasks)} segments", file=sys.stderr)

    # 输出结果（JSON 格式）
    print(json.dumps(all_results, ensure_ascii=False))


if __name__ == "__main__":
    # 设置启动方法为 spawn（Windows 必须）
    mp.set_start_method('spawn', force=True)
    main()
