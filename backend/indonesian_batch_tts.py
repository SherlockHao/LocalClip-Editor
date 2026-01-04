"""
印尼语TTS批量生成脚本
基于 VITS-TTS-ID 模型批量生成印尼语语音

输入配置 (JSON):
{
  "model_dir": "c:/workspace/ai_editing/model/vits-tts-id",
  "tasks": [
    {
      "segment_index": 0,
      "speaker_name": "ardi",
      "target_text": "Selamat pagi",
      "output_file": "exports/cloned_xxx/segment_0.wav"
    }
  ]
}

输出结果 (JSON):
[
  {
    "segment_index": 0,
    "status": "success",
    "output_file": "exports/cloned_xxx/segment_0.wav",
    "inference_time": 0.045
  }
]
"""
import os
import sys
import json
import time
from collections import defaultdict
from typing import List, Dict

# 为新GPU设置向后兼容模式（在导入torch之前设置）
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
os.environ['CUDA_MODULE_LOADING'] = 'LAZY'
os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0+PTX'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

import torch

# 强制使用较旧的GPU架构代码（向后兼容）
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True


def get_device():
    """自动检测可用设备"""
    if torch.cuda.is_available():
        try:
            test_tensor = torch.zeros(1).cuda()
            del test_tensor
            return "cuda"
        except Exception as e:
            print(f"[WARNING] CUDA detected but not available: {e}", file=sys.stderr)
            return "cpu"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def load_model(model_dir: str, device: str):
    """
    加载 VITS-TTS-ID 模型（仅加载一次）

    Args:
        model_dir: 模型目录路径
        device: 设备 (cuda/cpu/mps)

    Returns:
        Synthesizer 对象
    """
    from TTS.utils.synthesizer import Synthesizer

    checkpoint_file = os.path.join(model_dir, "checkpoint_1260000-inference.pth")
    config_file = os.path.join(model_dir, "config.json")

    if not os.path.exists(checkpoint_file):
        raise FileNotFoundError(f"Model checkpoint not found: {checkpoint_file}")
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Model config not found: {config_file}")

    # 切换到模型目录（config.json中使用相对路径）
    original_dir = os.getcwd()
    os.chdir(model_dir)

    try:
        synthesizer = Synthesizer(
            tts_checkpoint=checkpoint_file,
            tts_config_path=config_file,
            use_cuda=(device == "cuda")
        )
        return synthesizer
    finally:
        os.chdir(original_dir)


def batch_generate(
    synthesizer,
    tasks: List[Dict],
    device: str
) -> List[Dict]:
    """
    批量生成印尼语语音

    Args:
        synthesizer: TTS Synthesizer 对象
        tasks: 任务列表
        device: 设备

    Returns:
        结果列表
    """
    # 按说话人分组（优化：同一说话人的任务连续生成）
    tasks_by_speaker = defaultdict(list)
    for task in tasks:
        speaker_name = task["speaker_name"]
        tasks_by_speaker[speaker_name].append(task)

    results = []
    total_tasks = len(tasks)
    current_task = 0

    for speaker_name, speaker_tasks in tasks_by_speaker.items():
        print(f"[BatchGen] Processing speaker: {speaker_name} ({len(speaker_tasks)} tasks)", file=sys.stderr)

        for task in speaker_tasks:
            current_task += 1
            segment_index = task["segment_index"]
            target_text = task["target_text"]
            output_file = task["output_file"]

            # 确保输出目录存在
            output_dir = os.path.dirname(output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            try:
                # 生成语音
                inference_start = time.time()
                wav = synthesizer.tts(text=target_text, speaker_name=speaker_name)
                inference_time = time.time() - inference_start

                # 保存音频
                synthesizer.save_wav(wav, output_file)

                # 清理显存
                del wav
                if device == "cuda":
                    torch.cuda.empty_cache()

                results.append({
                    "segment_index": segment_index,
                    "status": "success",
                    "output_file": output_file,
                    "inference_time": round(inference_time, 3)
                })

                # 输出进度
                print(f"[BatchGen] 进度: {current_task}/{total_tasks}", file=sys.stderr)

            except Exception as e:
                results.append({
                    "segment_index": segment_index,
                    "status": "error",
                    "error_message": str(e),
                    "inference_time": 0
                })
                print(f"[ERROR] Segment {segment_index} failed: {e}", file=sys.stderr)

    return results


def main():
    """主函数"""
    # 读取配置
    if len(sys.argv) < 2:
        print("Usage: python indonesian_batch_tts.py <config_file>", file=sys.stderr)
        sys.exit(1)

    config_file = sys.argv[1]
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    model_dir = config["model_dir"]
    tasks = config["tasks"]

    print(f"[BatchGen] Model directory: {model_dir}", file=sys.stderr)
    print(f"[BatchGen] Total tasks: {len(tasks)}", file=sys.stderr)

    # 检测设备
    device = get_device()
    print(f"[BatchGen] Device: {device}", file=sys.stderr)

    # 加载模型
    print(f"[BatchGen] Loading model...", file=sys.stderr)
    load_start = time.time()
    synthesizer = load_model(model_dir, device)
    load_time = time.time() - load_start
    print(f"[BatchGen] Model loaded in {load_time:.2f}s", file=sys.stderr)

    # 批量生成
    print(f"[BatchGen] Starting batch generation...", file=sys.stderr)
    generation_start = time.time()
    results = batch_generate(synthesizer, tasks, device)
    generation_time = time.time() - generation_start
    print(f"[BatchGen] Generation completed in {generation_time:.2f}s", file=sys.stderr)

    # 输出结果（JSON格式，输出到stdout）
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
