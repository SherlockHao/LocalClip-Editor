"""
简单编码脚本 - 批量编码参考音频
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python fish_simple_encode.py <config_file>", file=sys.stderr)
        sys.exit(1)

    # 读取配置
    config_file = sys.argv[1]
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    fish_speech_dir = config["fish_speech_dir"]
    checkpoint_dir = config["checkpoint_dir"]
    speakers = config["speakers"]

    # 添加 fish-speech 到路径
    if fish_speech_dir not in sys.path:
        sys.path.insert(0, fish_speech_dir)

    print(f"[Encode] Loading from {fish_speech_dir}", file=sys.stderr)

    # 导入模块
    from fish_speech.models.dac.inference import load_model as load_dac_model

    # 确定设备
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[Encode] Using device: {device}", file=sys.stderr)

    # 加载 DAC 模型（只加载一次！）
    print(f"[Encode] Loading DAC model...", file=sys.stderr)
    dac_model = load_dac_model(
        config_name="modded_dac_vq",
        checkpoint_path=os.path.join(checkpoint_dir, "codec.pth"),
        device=device
    )
    print(f"[Encode] DAC model loaded", file=sys.stderr)

    # 逐个编码
    results = []
    for i, speaker in enumerate(speakers):
        speaker_id = speaker["speaker_id"]
        ref_audio = speaker["reference_audio"]
        output_npy = speaker["output_npy"]

        print(f"[Encode] Processing speaker {speaker_id} ({i+1}/{len(speakers)})", file=sys.stderr)
        print(f"[Encode]   Audio: {ref_audio}", file=sys.stderr)

        try:
            # 加载音频（使用 soundfile）
            audio_np, sr = sf.read(ref_audio)

            # 转换为 torch tensor
            audio = torch.from_numpy(audio_np).float()

            # 转置并处理通道
            if audio.ndim == 1:
                audio = audio.unsqueeze(0)  # [1, T]
            else:
                audio = audio.T  # [channels, T]
                if audio.shape[0] > 1:
                    audio = audio.mean(0, keepdim=True)  # 转为单声道

            # 重采样
            if sr != dac_model.sample_rate:
                import torchaudio
                audio = torchaudio.functional.resample(audio, sr, dac_model.sample_rate)

            # 编码
            audios = audio[None].to(device)
            audio_lengths = torch.tensor([audios.shape[2]], device=device, dtype=torch.long)

            with torch.no_grad():
                indices, _ = dac_model.encode(audios, audio_lengths)

            if indices.ndim == 3:
                indices = indices[0]

            # 保存
            np.save(output_npy, indices.cpu().numpy())
            print(f"[Encode]   ✅ Saved: {output_npy}", file=sys.stderr)

            results.append({
                "speaker_id": speaker_id,
                "npy_file": output_npy
            })

            # 清理显存
            del audio, audios, indices
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception as e:
            print(f"[Encode]   ❌ Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            continue

    # 输出结果（JSON 格式）
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
