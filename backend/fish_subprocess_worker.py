"""
Subprocess Worker 脚本
在 fish-speech 环境中运行，处理单个说话人的所有任务

作者：Claude
"""
import os
import sys
import json

# 为新GPU设置向后兼容模式（与 batch_inference.py 一致）
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
os.environ['CUDA_MODULE_LOADING'] = 'LAZY'
os.environ['TORCH_CUDA_ARCH_LIST'] = '9.0+PTX'
os.environ['CUDA_LAUNCH_BLOCKING'] = '0'

import torch
# 强制使用较旧的GPU架构代码（向后兼容）
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

import numpy as np
import soundfile as sf
from pathlib import Path


def main():
    try:
        if len(sys.argv) < 2:
            print("Usage: python fish_subprocess_worker.py <task_file>", file=sys.stderr)
            sys.exit(1)

        # 读取任务文件
        task_file = sys.argv[1]
        print(f"[Worker] Loading task file: {task_file}", file=sys.stderr)

        with open(task_file, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # 添加 fish-speech 到路径
        fish_speech_dir = config["fish_speech_dir"]
        if fish_speech_dir not in sys.path:
            sys.path.insert(0, fish_speech_dir)

        print(f"[Worker] Importing fish-speech modules from {fish_speech_dir}", file=sys.stderr)

        # 导入 fish-speech 模块
        from fish_speech.models.text2semantic.inference import init_model, generate_long
        from fish_speech.models.dac.inference import load_model as load_dac_model

        # 获取配置
        speaker_id = config["speaker_id"]
        tasks = config["tasks"]
        npy_file = config["npy_file"]
        reference = config["reference"]
        output_dir = config["output_dir"]
        checkpoint_path = config["checkpoint_path"]
        batch_size = config["batch_size"]

        print(f"[Worker] Speaker {speaker_id}: Processing {len(tasks)} tasks", file=sys.stderr)

        # 确定设备
        if torch.cuda.is_available():
            device = "cuda"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"

        print(f"[Worker] Using device: {device}", file=sys.stderr)

        # 确定精度
        precision = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16

        # 加载模型（只加载一次！）
        print(f"[Worker] Loading Text2Semantic model...", file=sys.stderr)
        text2semantic_model, decode_one_token = init_model(
            checkpoint_path=checkpoint_path,
            device=device,
            precision=precision,
            compile=False
        )

        print(f"[Worker] Loading DAC model...", file=sys.stderr)
        dac_model = load_dac_model(
            config_name="modded_dac_vq",
            checkpoint_path=os.path.join(checkpoint_path, "codec.pth"),
            device=device
        )

        # 加载 prompt tokens
        print(f"[Worker] Loading prompt tokens from {npy_file}", file=sys.stderr)
        prompt_tokens = torch.from_numpy(np.load(npy_file))
        prompt_tokens = prompt_tokens.to(device)

        # 处理所有任务
        generated_files = {}

        for idx, task in enumerate(tasks):
            segment_index = task["segment_index"]
            text = task["target_text"]  # 使用 target_text 字段
            output_file = os.path.join(output_dir, f"segment_{segment_index}.wav")

            print(f"[Worker] Processing segment {idx+1}/{len(tasks)}: {segment_index}", file=sys.stderr)
            print(f"[Worker] Text: {text[:50]}..." if len(text) > 50 else f"[Worker] Text: {text}", file=sys.stderr)

            try:
                # 生成语义 tokens
                prompt_text = reference["reference_text"]

                # generate_long 是一个生成器，需要迭代获取结果
                codes = None
                for response in generate_long(
                    model=text2semantic_model,
                    device=device,
                    decode_one_token=decode_one_token,
                    text=text,
                    prompt_text=prompt_text,
                    prompt_tokens=prompt_tokens,
                    max_new_tokens=1024,
                    top_p=0.7,
                    temperature=0.7,
                    repetition_penalty=1.2,
                    compile=False
                ):
                    if response.action == "sample":
                        codes = response.codes
                        break

                if codes is None:
                    print(f"[Worker] No codes generated for segment {segment_index}", file=sys.stderr)
                    continue

                generated_tokens = codes

                # DAC 解码
                if generated_tokens.ndim == 2:
                    generated_tokens = generated_tokens.unsqueeze(0)

                generated_tokens = generated_tokens.to(device)
                codes_lens = torch.tensor([generated_tokens.shape[-1]], device=device, dtype=torch.long)

                with torch.no_grad():
                    fake_audios, _ = dac_model.decode(generated_tokens, codes_lens)

                audio_array = fake_audios[0, 0].float().cpu().numpy()

                # 保存音频
                sf.write(output_file, audio_array, dac_model.sample_rate)
                generated_files[f"segment_{segment_index}"] = output_file
                print(f"[Worker] Segment {segment_index} completed", file=sys.stderr)

            except Exception as e:
                print(f"[Worker] Error processing segment {segment_index}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                continue

        # 输出结果（JSON 格式到 stdout）
        print(f"[Worker] Completed {len(generated_files)}/{len(tasks)} segments", file=sys.stderr)
        print(json.dumps(generated_files, ensure_ascii=False))

    except Exception as e:
        print(f"[Worker] Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
