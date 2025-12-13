"""
简单生成脚本 - 批量生成语音
在 fish-speech 环境中运行
完全参照 batch_inference.py 的实现
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python fish_simple_generate.py <config_file>", file=sys.stderr)
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

    print(f"[Generate] Loading from {fish_speech_dir}", file=sys.stderr)

    # 导入模块
    from fish_speech.models.text2semantic.inference import init_model, generate_long
    from fish_speech.models.dac.inference import load_model as load_dac_model

    # 确定设备和精度
    device = "cuda" if torch.cuda.is_available() else "cpu"
    precision = torch.bfloat16 if device == "cuda" else torch.float32
    print(f"[Generate] Using device: {device}, precision: {precision}", file=sys.stderr)

    # 加载模型（只加载一次！）
    print(f"[Generate] Loading Text2Semantic model...", file=sys.stderr)
    llama_model, decode_one_token = init_model(
        checkpoint_path=checkpoint_dir,
        device=device,
        precision=precision,
        compile=False
    )
    print(f"[Generate] Text2Semantic model loaded", file=sys.stderr)

    print(f"[Generate] Loading DAC model...", file=sys.stderr)
    dac_model = load_dac_model(
        config_name="modded_dac_vq",
        checkpoint_path=os.path.join(checkpoint_dir, "codec.pth"),
        device=device
    )
    print(f"[Generate] DAC model loaded", file=sys.stderr)

    # 逐个生成（完全参照 batch_inference.py）
    results = {}
    for i, task in enumerate(tasks):
        segment_index = task["segment_index"]
        target_text = task["target_text"]
        npy_file = task["npy_file"]
        reference_text = task["reference_text"]
        output_file = task["output_file"]

        print(f"\n[Generate] Processing segment {segment_index} ({i+1}/{len(tasks)})", file=sys.stderr)
        print(f"[Generate]   Text: {target_text[:50]}...", file=sys.stderr)

        try:
            # 加载 prompt tokens
            prompt_tokens = np.load(npy_file)
            prompt_tokens = torch.from_numpy(prompt_tokens).to(device).long()
            if prompt_tokens.ndim == 3:
                prompt_tokens = prompt_tokens[0]

            # 生成语义 tokens（与 batch_inference.py 完全一致）
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
                print(f"[Generate]   ❌ No codes generated", file=sys.stderr)
                continue

            # DAC 解码（与 batch_inference.py 完全一致）
            if codes.ndim == 2:
                codes = codes.unsqueeze(0)

            codes_lens = torch.tensor([codes.shape[-1]], device=device, dtype=torch.long)

            with torch.no_grad():
                fake_audios, _ = dac_model.decode(codes, codes_lens)

            # 保存音频
            audio_array = fake_audios[0, 0].float().cpu().numpy()
            sf.write(output_file, audio_array, dac_model.sample_rate)

            print(f"[Generate]   ✅ Saved: {output_file}", file=sys.stderr)
            print(f"[Generate]   Duration: {len(audio_array) / dac_model.sample_rate:.2f}s", file=sys.stderr)

            results[f"segment_{segment_index}"] = output_file

            # 清理显存
            del codes, fake_audios, audio_array, prompt_tokens
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception as e:
            print(f"[Generate]   ❌ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            continue

    print(f"\n[Generate] Completed: {len(results)}/{len(tasks)} segments", file=sys.stderr)

    # 输出结果（JSON 格式）
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
