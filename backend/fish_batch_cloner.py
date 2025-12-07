"""
Fish-Speech 批量语音克隆模块
使用 fish-speech/batch_inference.py 的批量推理能力
"""
import os
import json
import subprocess
import shutil
from pathlib import Path

# fish-speech 仓库路径
FISH_SPEECH_DIR = "/Users/yiya_workstation/Documents/ai_editing/fish-speech"
CHECKPOINT_DIR = os.path.join(FISH_SPEECH_DIR, "checkpoints/openaudio-s1-mini")
FISH_AUDIO_PYTHON = "/Users/yiya_workstation/miniconda3/envs/fish-speech/bin/python"


class FishBatchCloner:
    """Fish-Speech 批量语音克隆器"""

    def __init__(self, fish_speech_dir=FISH_SPEECH_DIR, checkpoint_dir=CHECKPOINT_DIR):
        self.fish_speech_dir = fish_speech_dir
        self.checkpoint_dir = checkpoint_dir
        self.python_executable = FISH_AUDIO_PYTHON

    def batch_encode_speakers(self, speaker_references, output_dir):
        """
        批量编码所有说话人的参考音频为 VQ codes

        Args:
            speaker_references: dict, {speaker_id: {"reference_audio": path, "reference_text": text, ...}}
            output_dir: 输出目录

        Returns:
            dict: {speaker_id: npy_file_path}
        """
        print(f"\n🐟 [批量编码] 开始批量编码 {len(speaker_references)} 个说话人的参考音频...")

        os.makedirs(output_dir, exist_ok=True)

        # 准备批量编码脚本
        batch_script = self._create_batch_encode_script(speaker_references, output_dir)
        script_path = os.path.abspath(os.path.join(output_dir, "batch_encode.py"))

        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(batch_script)

        # 执行批量编码脚本
        cmd = [self.python_executable, script_path]

        env = os.environ.copy()
        env["PYTHONPATH"] = self.fish_speech_dir + (f":{env.get('PYTHONPATH', '')}" if env.get('PYTHONPATH') else '')

        try:
            print(f"执行批量编码脚本: {script_path}")
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                cwd=self.fish_speech_dir,
                env=env
            )
            print(result.stdout)

            # 读取生成的.npy文件路径
            speaker_npy_files = {}
            for speaker_id in speaker_references.keys():
                npy_path = os.path.join(output_dir, f"speaker_{speaker_id}_codes.npy")
                if os.path.exists(npy_path):
                    speaker_npy_files[speaker_id] = npy_path
                    print(f"✅ 说话人 {speaker_id} 编码完成: {npy_path}")
                else:
                    print(f"❌ 说话人 {speaker_id} 编码失败: 未找到 {npy_path}")

            return speaker_npy_files

        except subprocess.CalledProcessError as e:
            print(f"❌ 批量编码失败: {e.stderr}")
            raise

    def batch_generate_audio(self, tasks, speaker_npy_files, speaker_references, output_dir, script_dir=None):
        """
        批量生成所有语音片段

        Args:
            tasks: list of dict, [{"speaker_id": int, "target_text": str, "segment_index": int}, ...]
            speaker_npy_files: dict, {speaker_id: npy_file_path}
            speaker_references: dict, {speaker_id: {"reference_text": text, ...}}
            output_dir: 输出目录
            script_dir: 脚本保存目录（如果为None，则使用output_dir）

        Returns:
            dict: {segment_index: audio_file_path}
        """
        print(f"\n🐟 [批量生成] 开始批量生成 {len(tasks)} 个语音片段...")

        os.makedirs(output_dir, exist_ok=True)

        # 如果未指定脚本目录，使用output_dir
        if script_dir is None:
            script_dir = output_dir
        else:
            os.makedirs(script_dir, exist_ok=True)

        # 按说话人分组任务，以提高批量处理效率
        tasks_by_speaker = {}
        for task in tasks:
            speaker_id = task['speaker_id']
            if speaker_id not in tasks_by_speaker:
                tasks_by_speaker[speaker_id] = []
            tasks_by_speaker[speaker_id].append(task)

        generated_audio_files = {}

        # 对每个说话人批量生成其所有片段
        for speaker_id, speaker_tasks in tasks_by_speaker.items():
            if speaker_id not in speaker_npy_files:
                print(f"⚠️ 说话人 {speaker_id} 没有.npy文件，跳过")
                continue

            print(f"\n处理说话人 {speaker_id} 的 {len(speaker_tasks)} 个片段...")

            # 创建该说话人的批量生成脚本
            batch_script = self._create_batch_generate_script(
                speaker_id,
                speaker_tasks,
                speaker_npy_files[speaker_id],
                speaker_references[speaker_id]["reference_text"],
                output_dir
            )

            # 脚本保存到script_dir，避免触发uvicorn reload
            script_path = os.path.abspath(os.path.join(script_dir, f"batch_generate_speaker_{speaker_id}.py"))
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(batch_script)

            # 执行批量生成脚本
            cmd = [self.python_executable, script_path]

            env = os.environ.copy()
            env["PYTHONPATH"] = self.fish_speech_dir + (f":{env.get('PYTHONPATH', '')}" if env.get('PYTHONPATH') else '')

            try:
                print(f"执行批量生成脚本: {script_path}")
                result = subprocess.run(
                    cmd,
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=self.fish_speech_dir,
                    env=env,
                    timeout=600  # 10分钟超时
                )
                print(result.stdout)

                # 收集生成的音频文件
                for task in speaker_tasks:
                    segment_index = task['segment_index']
                    audio_path = os.path.join(output_dir, f"segment_{segment_index:04d}.wav")
                    if os.path.exists(audio_path):
                        generated_audio_files[segment_index] = audio_path
                        print(f"✅ 片段 {segment_index} 生成完成")
                    else:
                        print(f"❌ 片段 {segment_index} 生成失败")

            except subprocess.CalledProcessError as e:
                print(f"❌ 说话人 {speaker_id} 批量生成失败: {e.stderr}")
                continue
            except subprocess.TimeoutExpired:
                print(f"❌ 说话人 {speaker_id} 批量生成超时")
                continue

        return generated_audio_files

    def _create_batch_encode_script(self, speaker_references, output_dir):
        """创建批量编码脚本"""
        # 准备参考音频和文本列表
        ref_audio_list = []
        ref_text_list = []
        speaker_ids = []

        for speaker_id, ref_data in speaker_references.items():
            # 转换为绝对路径
            audio_path = os.path.abspath(ref_data["reference_audio"])
            ref_audio_list.append(audio_path)
            ref_text_list.append(ref_data["reference_text"])
            speaker_ids.append(speaker_id)

        # 确保输出目录也是绝对路径
        output_dir = os.path.abspath(output_dir)

        script = f'''#!/usr/bin/env python3
import os
import sys
import torch
import numpy as np
import torchaudio
from loguru import logger

# 导入 Fish Speech 的推理模块
from fish_speech.models.dac.inference import load_model as load_dac_model

# 配置
CHECKPOINT_PATH = "{self.checkpoint_dir}"
OUTPUT_DIR = "{output_dir}"

REF_AUDIO_PATH_LIST = {json.dumps(ref_audio_list)}
REF_TEXT_LIST = {json.dumps(ref_text_list)}
SPEAKER_IDS = {json.dumps(speaker_ids)}

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"

def main():
    device = get_device()
    logger.info(f"使用设备: {{device}}")

    # 加载 DAC 模型
    logger.info("正在加载 DAC 模型...")
    dac_model = load_dac_model(
        config_name="modded_dac_vq",
        checkpoint_path=os.path.join(CHECKPOINT_PATH, "codec.pth"),
        device=device
    )
    logger.info("✅ DAC 模型加载完成")

    # 批量编码
    for i, (speaker_id, ref_audio, ref_text) in enumerate(zip(SPEAKER_IDS, REF_AUDIO_PATH_LIST, REF_TEXT_LIST)):
        logger.info(f"\\n正在编码说话人 {{speaker_id}}: {{ref_audio}}")

        try:
            # 加载音频
            audio, sr = torchaudio.load(str(ref_audio))

            # 转换为单声道
            if audio.shape[0] > 1:
                audio = audio.mean(0, keepdim=True)

            # 重采样
            audio = torchaudio.functional.resample(audio, sr, dac_model.sample_rate)

            # 编码为 VQ codes
            audios = audio[None].to(device)
            audio_lengths = torch.tensor([audios.shape[2]], device=device, dtype=torch.long)

            with torch.no_grad():
                indices, _ = dac_model.encode(audios, audio_lengths)

            if indices.ndim == 3:
                indices = indices[0]

            # 保存 .npy 文件
            npy_filename = os.path.join(OUTPUT_DIR, f"speaker_{{speaker_id}}_codes.npy")
            np.save(npy_filename, indices.cpu().numpy())
            logger.info(f"✅ 已保存: {{npy_filename}}")

            # 清理显存
            del audio, audios, indices
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception as e:
            logger.error(f"❌ 编码说话人 {{speaker_id}} 失败: {{e}}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
'''
        return script

    def _create_batch_generate_script(self, speaker_id, tasks, npy_file, ref_text, output_dir):
        """创建批量生成脚本"""
        # 准备文本列表和输出文件名列表
        text_list = [task['target_text'] for task in tasks]
        segment_indices = [task['segment_index'] for task in tasks]

        # 转换为绝对路径
        npy_file = os.path.abspath(npy_file)
        output_dir = os.path.abspath(output_dir)

        script = f'''#!/usr/bin/env python3
import os
import sys
import torch
import numpy as np
import soundfile as sf
from loguru import logger

# 导入 Fish Speech 的推理模块
from fish_speech.models.text2semantic.inference import init_model, generate_long
from fish_speech.models.dac.inference import load_model as load_dac_model

# 配置
CHECKPOINT_PATH = "{self.checkpoint_dir}"
OUTPUT_DIR = "{output_dir}"
PROMPT_TOKENS_PATH = "{npy_file}"
REF_TEXT = {json.dumps(ref_text)}
TEXT_LIST = {json.dumps(text_list)}
SEGMENT_INDICES = {json.dumps(segment_indices)}

# 生成参数
MAX_NEW_TOKENS = 1024
TOP_P = 0.7
TEMPERATURE = 0.7
REPETITION_PENALTY = 1.2

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"

def main():
    device = get_device()
    logger.info(f"使用设备: {{device}}")

    # 设置精度
    if device == "cuda":
        precision = torch.bfloat16
    else:
        precision = torch.float32

    # 加载 DAC 模型
    logger.info("正在加载 DAC 模型...")
    dac_model = load_dac_model(
        config_name="modded_dac_vq",
        checkpoint_path=os.path.join(CHECKPOINT_PATH, "codec.pth"),
        device=device
    )
    logger.info("✅ DAC 模型加载完成")

    # 加载 Text2Semantic 模型
    logger.info("正在加载 Text2Semantic 模型...")
    llama_model, decode_one_token = init_model(
        checkpoint_path=CHECKPOINT_PATH,
        device=device,
        precision=precision,
        compile=False
    )
    logger.info("✅ Text2Semantic 模型加载完成")

    # 加载 Prompt Tokens
    logger.info(f"加载 Prompt Tokens: {{PROMPT_TOKENS_PATH}}")
    prompt_tokens = np.load(PROMPT_TOKENS_PATH)
    prompt_tokens = torch.from_numpy(prompt_tokens).to(device).long()
    if prompt_tokens.ndim == 3:
        prompt_tokens = prompt_tokens[0]
    logger.info(f"✅ Prompt Tokens 加载完成")

    # 批量生成
    logger.info(f"\\n开始批量生成 {{len(TEXT_LIST)}} 个片段...")

    for i, (text, segment_idx) in enumerate(zip(TEXT_LIST, SEGMENT_INDICES)):
        logger.info(f"\\n[{{i+1}}/{{len(TEXT_LIST)}}] 生成片段 {{segment_idx}}: {{text[:50]}}...")

        try:
            # 生成语义 tokens
            codes = None
            for response in generate_long(
                model=llama_model,
                device=device,
                decode_one_token=decode_one_token,
                text=text,
                prompt_text=REF_TEXT,
                prompt_tokens=prompt_tokens,
                max_new_tokens=MAX_NEW_TOKENS,
                top_p=TOP_P,
                temperature=TEMPERATURE,
                repetition_penalty=REPETITION_PENALTY,
                num_samples=1
            ):
                if response.action == "sample":
                    codes = response.codes

            if codes is None:
                logger.error(f"❌ 未能生成语义 tokens")
                continue

            # 解码为音频
            if codes.ndim == 2:
                codes = codes.unsqueeze(0)

            codes_lens = torch.tensor([codes.shape[-1]], device=device, dtype=torch.long)

            with torch.no_grad():
                fake_audios, _ = dac_model.decode(codes, codes_lens)

            # 保存音频
            output_filename = os.path.join(OUTPUT_DIR, f"segment_{{segment_idx:04d}}.wav")
            fake_audio = fake_audios[0, 0].float().cpu().numpy()
            sf.write(output_filename, fake_audio, dac_model.sample_rate)

            logger.info(f"✅ 已保存: {{output_filename}}")

            # 清理显存
            del codes, fake_audios, fake_audio
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        except Exception as e:
            logger.error(f"❌ 生成片段 {{segment_idx}} 失败: {{e}}")
            import traceback
            traceback.print_exc()

    logger.info("\\n🎉 批量生成完成！")

if __name__ == "__main__":
    main()
'''
        return script
