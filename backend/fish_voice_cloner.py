"""
Fish-Speech 语音克隆模块
基于 fish-speech/example.py 实现
"""
import os
import subprocess
import shutil
from pathlib import Path
import torch

# fish-speech 仓库路径
FISH_SPEECH_DIR = "/Users/yiya_workstation/Documents/ai_editing/fish-speech"
CHECKPOINT_DIR = os.path.join(FISH_SPEECH_DIR, "checkpoints/openaudio-s1-mini")


class FishVoiceCloner:
    """Fish-Speech 语音克隆器"""

    def __init__(self, fish_speech_dir=FISH_SPEECH_DIR, checkpoint_dir=CHECKPOINT_DIR):
        self.fish_speech_dir = fish_speech_dir
        self.checkpoint_dir = checkpoint_dir
        self.device = self._detect_device()
        # 使用fish-speech环境的Python解释器
        self.python_executable = "/Users/yiya_workstation/miniconda3/envs/fish-speech/bin/python"

    def _detect_device(self):
        """检测可用设备（支持 CUDA/MPS/CPU）"""
        try:
            from platform_utils import detect_gpu_device
            return detect_gpu_device()
        except ImportError:
            # Fallback: 传统方式
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"

    def encode_reference_audio(self, ref_audio_path, output_dir):
        """
        步骤1: 编码参考音频为 VQ Token

        Args:
            ref_audio_path: 参考音频路径 (.wav)
            output_dir: 输出目录

        Returns:
            fake_npy_path: 生成的 fake.npy 文件路径
        """
        print(f"[Step 1/3] 正在编码参考音频: {ref_audio_path}")

        # 转换为绝对路径
        ref_audio_path = os.path.abspath(ref_audio_path)
        output_dir = os.path.abspath(output_dir)

        os.makedirs(output_dir, exist_ok=True)
        fake_npy_path = os.path.join(output_dir, "fake.npy")
        fake_wav_path = os.path.join(output_dir, "fake.wav")

        script_path = os.path.join(self.fish_speech_dir, "fish_speech/models/dac/inference.py")

        cmd = [
            self.python_executable, script_path,
            "-i", ref_audio_path,
            "--checkpoint-path", os.path.join(self.checkpoint_dir, "codec.pth"),
            "--device", self.device,
            "-o", fake_wav_path
        ]

        # 设置 PYTHONPATH 以便能导入 fish_speech 模块
        env = os.environ.copy()
        env["PYTHONPATH"] = self.fish_speech_dir + (f":{env.get('PYTHONPATH', '')}" if env.get('PYTHONPATH') else '')

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=self.fish_speech_dir, env=env)

            # 检查并移动生成的文件
            if os.path.exists("fake.npy"):
                shutil.move("fake.npy", fake_npy_path)
            elif not os.path.exists(fake_npy_path):
                # 有时候文件会在 fish-speech 根目录下生成
                root_fake_npy = os.path.join(self.fish_speech_dir, "fake.npy")
                if os.path.exists(root_fake_npy):
                    shutil.move(root_fake_npy, fake_npy_path)
                else:
                    raise FileNotFoundError(f"未找到生成的 fake.npy 文件")

            print(f"✅ 参考音频编码成功: {fake_npy_path}")
            return fake_npy_path

        except subprocess.CalledProcessError as e:
            print(f"❌ 编码失败: {e.stderr}")
            raise

    def generate_semantic_tokens(self, target_text, ref_text, fake_npy_path, output_dir):
        """
        步骤2: 从文本生成语义 Token

        Args:
            target_text: 目标文本（要生成的内容）
            ref_text: 参考文本（参考音频的文本内容）
            fake_npy_path: 参考音频的 VQ Token 路径
            output_dir: 输出目录

        Returns:
            codes_path: 生成的 codes_0.npy 文件路径
        """
        print(f"[Step 2/3] 正在生成语义 Token...")
        print(f"  目标文本: {target_text}")
        print(f"  参考文本: {ref_text}")

        # 转换为绝对路径
        fake_npy_path = os.path.abspath(fake_npy_path)
        output_dir = os.path.abspath(output_dir)

        os.makedirs(output_dir, exist_ok=True)
        codes_path = os.path.join(output_dir, "codes_0.npy")

        script_path = os.path.join(self.fish_speech_dir, "fish_speech/models/text2semantic/inference.py")

        cmd = [
            self.python_executable, script_path,
            "--text", target_text,
            "--prompt-text", ref_text,
            "--prompt-tokens", fake_npy_path,
            "--checkpoint-path", self.checkpoint_dir,
            "--device", self.device
        ]

        # 设置 PYTHONPATH 以便能导入 fish_speech 模块
        env = os.environ.copy()
        env["PYTHONPATH"] = self.fish_speech_dir + (f":{env.get('PYTHONPATH', '')}" if env.get('PYTHONPATH') else '')

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=self.fish_speech_dir, env=env)

            # 检查并移动生成的文件
            temp_codes = os.path.join(self.fish_speech_dir, "temp/codes_0.npy")
            root_codes = os.path.join(self.fish_speech_dir, "codes_0.npy")

            if os.path.exists(temp_codes):
                shutil.move(temp_codes, codes_path)
            elif os.path.exists(root_codes):
                shutil.move(root_codes, codes_path)
            elif not os.path.exists(codes_path):
                raise FileNotFoundError(f"未找到生成的 codes_0.npy 文件")

            print(f"✅ 语义 Token 生成成功: {codes_path}")
            return codes_path

        except subprocess.CalledProcessError as e:
            print(f"❌ 生成失败: {e.stderr}")
            raise

    def decode_to_audio(self, codes_path, output_audio_path):
        """
        步骤3: 将语义 Token 解码为音频

        Args:
            codes_path: codes_0.npy 文件路径
            output_audio_path: 输出音频路径 (.wav)

        Returns:
            output_audio_path: 生成的音频文件路径
        """
        print(f"[Step 3/3] 正在解码为音频...")

        # 转换为绝对路径
        codes_path = os.path.abspath(codes_path)
        output_audio_path = os.path.abspath(output_audio_path)

        os.makedirs(os.path.dirname(output_audio_path), exist_ok=True)

        script_path = os.path.join(self.fish_speech_dir, "fish_speech/models/dac/inference.py")

        cmd = [
            self.python_executable, script_path,
            "-i", codes_path,
            "--checkpoint-path", os.path.join(self.checkpoint_dir, "codec.pth"),
            "--device", self.device,
            "-o", output_audio_path
        ]

        # 设置 PYTHONPATH 以便能导入 fish_speech 模块
        env = os.environ.copy()
        env["PYTHONPATH"] = self.fish_speech_dir + (f":{env.get('PYTHONPATH', '')}" if env.get('PYTHONPATH') else '')

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True, cwd=self.fish_speech_dir, env=env)

            if not os.path.exists(output_audio_path):
                raise FileNotFoundError(f"未找到生成的音频文件: {output_audio_path}")

            print(f"✅ 音频解码成功: {output_audio_path}")
            return output_audio_path

        except subprocess.CalledProcessError as e:
            print(f"❌ 解码失败: {e.stderr}")
            raise

    def clone_voice(self, ref_audio_path, ref_text, target_text, output_audio_path, work_dir):
        """
        完整的语音克隆流程

        Args:
            ref_audio_path: 参考音频路径
            ref_text: 参考音频的文本内容
            target_text: 目标文本
            output_audio_path: 输出音频路径
            work_dir: 工作目录（存放中间文件）

        Returns:
            output_audio_path: 生成的音频文件路径
        """
        print(f"\n🐟 开始语音克隆...")
        print(f"  参考音频: {ref_audio_path}")
        print(f"  参考文本: {ref_text}")
        print(f"  目标文本: {target_text}")
        print(f"  输出路径: {output_audio_path}")

        try:
            # Step 1: 编码参考音频
            fake_npy_path = self.encode_reference_audio(ref_audio_path, work_dir)

            # Step 2: 生成语义 Token
            codes_path = self.generate_semantic_tokens(target_text, ref_text, fake_npy_path, work_dir)

            # Step 3: 解码为音频
            result_path = self.decode_to_audio(codes_path, output_audio_path)

            print(f"🎉 语音克隆成功！")
            return result_path

        except Exception as e:
            print(f"❌ 语音克隆失败: {str(e)}")
            raise
