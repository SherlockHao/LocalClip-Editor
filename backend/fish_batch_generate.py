"""
批量生成脚本 - 按说话人分组批量处理
完全按照 batch_inference.py 的逻辑实现
在 fish-speech 环境中运行
"""
import os
import sys
import json

# CUDA 优化配置
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
os.environ['CUDA_MODULE_LOADING'] = 'LAZY'
os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0+PTX'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

import torch
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

import numpy as np
import soundfile as sf
from collections import defaultdict


def main():
    if len(sys.argv) < 2:
        print("Usage: python fish_batch_generate.py <config_file>", file=sys.stderr)
        sys.exit(1)

    # 读取配置
    config_file = sys.argv[1]
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    fish_speech_dir = config["fish_speech_dir"]
    checkpoint_dir = config["checkpoint_dir"]
    tasks = config["tasks"]

    # 添加 fish-speech 到路径
    if fish_speech_dir not in sys.path:
        sys.path.insert(0, fish_speech_dir)

    print(f"[BatchGen] Loading from {fish_speech_dir}", file=sys.stderr)

    # 导入模块
    from fish_speech.models.text2semantic.inference import init_model, generate_long
    from fish_speech.models.dac.inference import load_model as load_dac_model

    # 确定设备和精度
    device = "cuda" if torch.cuda.is_available() else "cpu"
    precision = torch.bfloat16 if device == "cuda" else torch.float32
    print(f"[BatchGen] Using device: {device}, precision: {precision}", file=sys.stderr)

    # 加载模型（只加载一次！）
    print(f"[BatchGen] Loading Text2Semantic model...", file=sys.stderr)
    llama_model, decode_one_token = init_model(
        checkpoint_path=checkpoint_dir,
        device=device,
        precision=precision,
        compile=False
    )
    print(f"[BatchGen] Text2Semantic model loaded", file=sys.stderr)

    print(f"[BatchGen] Loading DAC model...", file=sys.stderr)
    dac_model = load_dac_model(
        config_name="modded_dac_vq",
        checkpoint_path=os.path.join(checkpoint_dir, "codec.pth"),
        device=device
    )
    print(f"[BatchGen] DAC model loaded", file=sys.stderr)

    # 按说话人分组任务
    tasks_by_speaker = defaultdict(list)
    for task in tasks:
        speaker_id = task["speaker_id"]
        tasks_by_speaker[speaker_id].append(task)

    print(f"\n[BatchGen] Total tasks: {len(tasks)}", file=sys.stderr)
    print(f"[BatchGen] Speakers: {len(tasks_by_speaker)}", file=sys.stderr)
    for speaker_id, speaker_tasks in tasks_by_speaker.items():
        print(f"  Speaker {speaker_id}: {len(speaker_tasks)} texts", file=sys.stderr)

    # 逐个说话人批量处理
    all_results = {}
    completed_tasks = 0  # 总体已完成任务数
    total_tasks_count = len(tasks)  # 总任务数

    for speaker_idx, (speaker_id, speaker_tasks) in enumerate(tasks_by_speaker.items()):
        print(f"\n{'='*70}", file=sys.stderr)
        print(f"[BatchGen] Processing Speaker {speaker_id} ({speaker_idx+1}/{len(tasks_by_speaker)})", file=sys.stderr)
        print(f"[BatchGen] Total texts for this speaker: {len(speaker_tasks)}", file=sys.stderr)
        print(f"{'='*70}", file=sys.stderr)

        # 获取该说话人的 npy 文件和参考文本
        npy_file = speaker_tasks[0]["npy_file"]
        reference_text = speaker_tasks[0]["reference_text"]

        # 加载 prompt tokens（每个说话人加载一次）
        print(f"\n[BatchGen] Loading prompt tokens: {npy_file}", file=sys.stderr)
        prompt_tokens = np.load(npy_file)
        prompt_tokens = torch.from_numpy(prompt_tokens).to(device).long()
        if prompt_tokens.ndim == 3:
            prompt_tokens = prompt_tokens[0]
        print(f"[BatchGen] Prompt tokens shape: {prompt_tokens.shape}", file=sys.stderr)

        # 批量生成该说话人的所有文本（完全按照 batch_inference.py 的逻辑）
        for i, task in enumerate(speaker_tasks):
            segment_index = task["segment_index"]
            target_text = task["target_text"]
            output_file = task["output_file"]

            print(f"\n[BatchGen] [{i+1}/{len(speaker_tasks)}] Segment {segment_index}", file=sys.stderr)
            print(f"[BatchGen] Text: {target_text[:60]}...", file=sys.stderr)

            try:
                # 步骤 A: 文本转语义 Token (完全照搬 batch_inference.py)
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
                    print(f"[BatchGen] ❌ No codes generated", file=sys.stderr)
                    continue

                # 步骤 B: 语义 Token 转语音 (完全照搬 batch_inference.py)
                if codes.ndim == 2:
                    codes = codes.unsqueeze(0)

                codes_lens = torch.tensor([codes.shape[-1]], device=device, dtype=torch.long)

                with torch.no_grad():
                    fake_audios, _ = dac_model.decode(codes, codes_lens)

                # 保存音频
                fake_audio = fake_audios[0, 0].float().cpu().numpy()
                sf.write(output_file, fake_audio, dac_model.sample_rate)

                duration = len(fake_audio) / dac_model.sample_rate
                print(f"[BatchGen] ✅ Saved: {output_file}", file=sys.stderr)
                print(f"[BatchGen] Duration: {duration:.2f}s", file=sys.stderr)

                all_results[segment_index] = output_file  # 使用整数作为键

                # 更新总体进度
                completed_tasks += 1
                print(f"[BatchGen] 进度: {completed_tasks}/{total_tasks_count}", file=sys.stderr, flush=True)

                # 清理显存
                del codes, fake_audios, fake_audio
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            except Exception as e:
                print(f"[BatchGen] ❌ Error: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                # 即使失败也更新进度计数
                completed_tasks += 1
                print(f"[BatchGen] 进度: {completed_tasks}/{total_tasks_count}", file=sys.stderr, flush=True)
                continue

        # 清理该说话人的 prompt tokens
        del prompt_tokens
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    print(f"\n{'='*70}", file=sys.stderr)
    print(f"[BatchGen] All done! Generated {len(all_results)}/{len(tasks)} segments", file=sys.stderr)
    print(f"{'='*70}", file=sys.stderr)

    # 输出结果（JSON 格式）
    print(json.dumps(all_results, ensure_ascii=False))


if __name__ == "__main__":
    main()
