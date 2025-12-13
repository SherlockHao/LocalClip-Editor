"""
简单批量语音克隆器
完全参照 batch_inference.py 的实现方式
- 不使用多进程/并行
- 模型只加载一次
- 逐个处理所有音频片段

作者：Claude
"""
import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List
from loguru import logger


class SimpleFishCloner:
    """
    简单批量克隆器

    特点：
    - 单进程顺序处理
    - 模型只加载一次
    - 简单可靠
    """

    def __init__(
        self,
        fish_speech_dir: str = None,
        checkpoint_dir: str = None,
        fish_python: str = None
    ):
        """初始化"""
        import platform

        if platform.system() == "Windows":
            self.fish_speech_dir = fish_speech_dir or os.environ.get(
                "FISH_SPEECH_DIR",
                r"C:\workspace\ai_editing\fish-speech-win"
            )
            self.fish_python = fish_python or os.environ.get(
                "FISH_SPEECH_PYTHON",
                r"C:\Users\7\miniconda3\envs\fish-speech\python.exe"
            )
        else:
            self.fish_speech_dir = fish_speech_dir or os.environ.get(
                "FISH_SPEECH_DIR",
                "/Users/yiya_workstation/Documents/ai_editing/fish-speech"
            )
            self.fish_python = fish_python or os.environ.get(
                "FISH_SPEECH_PYTHON",
                "/Users/yiya_workstation/miniconda3/envs/fish-speech/bin/python"
            )

        self.checkpoint_dir = checkpoint_dir or os.path.join(
            self.fish_speech_dir, "checkpoints", "openaudio-s1-mini"
        )

        logger.info(f"Fish-Speech 目录: {self.fish_speech_dir}")
        logger.info(f"检查点目录: {self.checkpoint_dir}")
        logger.info(f"Python 路径: {self.fish_python}")

    def batch_encode_speakers(
        self,
        speaker_references: Dict[int, Dict],
        output_dir: str
    ) -> Dict[int, str]:
        """
        批量编码说话人参考音频

        Args:
            speaker_references: {speaker_id: {reference_audio, reference_text, ...}}
            output_dir: 输出目录

        Returns:
            {speaker_id: npy_file_path}
        """
        logger.info(f"\n🎤 批量编码 {len(speaker_references)} 个说话人的参考音频...")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 创建临时配置文件
        encode_config = {
            "mode": "encode",
            "fish_speech_dir": self.fish_speech_dir,
            "checkpoint_dir": self.checkpoint_dir,
            "output_dir": os.path.abspath(output_dir),
            "speakers": []
        }

        for speaker_id, ref_info in speaker_references.items():
            encode_config["speakers"].append({
                "speaker_id": speaker_id,
                "reference_audio": os.path.abspath(ref_info["reference_audio"]),
                "reference_text": ref_info["reference_text"],
                "output_npy": os.path.abspath(
                    os.path.join(output_dir, f"speaker_{speaker_id}_codes.npy")
                )
            })

        # 写入临时配置
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as f:
            json.dump(encode_config, f, ensure_ascii=False, indent=2)
            config_file = f.name

        try:
            # 调用编码脚本
            script_path = os.path.join(
                os.path.dirname(__file__),
                "fish_simple_encode.py"
            )

            cmd = [self.fish_python, script_path, config_file]

            logger.info(f"执行编码命令: {' '.join(cmd)}")
            logger.info("正在编码，请查看下方进度...")

            # 使用 Popen 实时显示输出
            import sys
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                cwd=self.fish_speech_dir,
                bufsize=1
            )

            # 实时读取并显示输出
            output_lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    # 显示进度信息
                    if '[Encode]' in line or 'INFO' in line:
                        print(line, flush=True)
                    output_lines.append(line)

            # 等待进程结束
            proc.wait()

            if proc.returncode != 0:
                logger.error(f"编码失败！返回码: {proc.returncode}")
                for line in output_lines[-20:]:
                    logger.error(line)
                raise RuntimeError(f"编码失败，返回码: {proc.returncode}")

            # 解析结果
            try:
                json_line = output_lines[-1] if output_lines else "[]"
                result_data = json.loads(json_line)

                speaker_npy_files = {}
                for item in result_data:
                    speaker_npy_files[item['speaker_id']] = item['npy_file']

                logger.info(f"✅ 编码完成！生成 {len(speaker_npy_files)} 个 npy 文件")
                return speaker_npy_files

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"解析编码结果失败: {e}")
                logger.error(f"输出: {result.stdout}")
                raise

        finally:
            # 清理临时文件
            try:
                os.remove(config_file)
            except:
                pass

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        speaker_npy_files: Dict[int, str],
        speaker_references: Dict[int, Dict],
        output_dir: str,
        script_dir: str = None  # 兼容参数
    ) -> Dict[str, str]:
        """
        批量生成音频

        Args:
            tasks: [{"speaker_id": 0, "target_text": "...", "segment_index": 0}, ...]
            speaker_npy_files: {speaker_id: npy_file_path}
            speaker_references: {speaker_id: {reference_text, ...}}
            output_dir: 输出目录

        Returns:
            {"segment_0": "path/to/segment_0.wav", ...}
        """
        logger.info(f"\n🎵 批量生成 {len(tasks)} 个语音片段...")

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 创建临时配置文件
        generate_config = {
            "mode": "generate",
            "fish_speech_dir": self.fish_speech_dir,
            "checkpoint_dir": self.checkpoint_dir,
            "output_dir": os.path.abspath(output_dir),
            "tasks": []
        }

        for task in tasks:
            speaker_id = task["speaker_id"]
            segment_index = task["segment_index"]
            target_text = task["target_text"]

            npy_file = speaker_npy_files.get(speaker_id)
            if not npy_file:
                logger.warning(f"⚠️ 说话人 {speaker_id} 没有 npy 文件，跳过片段 {segment_index}")
                continue

            reference_text = speaker_references[speaker_id]["reference_text"]

            generate_config["tasks"].append({
                "segment_index": segment_index,
                "speaker_id": speaker_id,
                "target_text": target_text,
                "npy_file": os.path.abspath(npy_file),
                "reference_text": reference_text,
                "output_file": os.path.abspath(
                    os.path.join(output_dir, f"segment_{segment_index}.wav")
                )
            })

        # 写入临时配置
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as f:
            json.dump(generate_config, f, ensure_ascii=False, indent=2)
            config_file = f.name

        try:
            # 调用批量生成脚本（按说话人分组批量处理）
            script_path = os.path.join(
                os.path.dirname(__file__),
                "fish_batch_generate.py"
            )

            cmd = [self.fish_python, script_path, config_file]

            logger.info(f"执行生成命令: {' '.join(cmd)}")
            logger.info(f"预计时间: 约 {len(tasks) * 20 // 60} 分钟")
            logger.info("正在生成，请查看下方进度...")

            # 使用 Popen 实时显示输出
            import sys
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                encoding='utf-8',
                errors='ignore',
                cwd=self.fish_speech_dir,
                bufsize=1  # 行缓冲
            )

            # 实时读取并显示输出
            output_lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    # 显示进度信息
                    if '[BatchGen]' in line or 'tokens/sec' in line or 'INFO' in line:
                        print(line, flush=True)
                    output_lines.append(line)

            # 等待进程结束
            proc.wait()

            if proc.returncode != 0:
                logger.error(f"生成失败！返回码: {proc.returncode}")
                # 显示最后几行输出
                for line in output_lines[-20:]:
                    logger.error(line)
                raise RuntimeError(f"生成失败，返回码: {proc.returncode}")

            # 解析结果（最后一行是 JSON）
            try:
                json_line = output_lines[-1] if output_lines else "{}"
                result_data = json.loads(json_line)

                # 将字符串键转换为整数键（JSON 会将整数键转为字符串）
                result_data = {int(k): v for k, v in result_data.items()}

                logger.info(f"✅ 生成完成！生成 {len(result_data)} 个音频文件")
                return result_data

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"解析生成结果失败: {e}")
                logger.error(f"输出: {result.stdout}")
                raise

        finally:
            # 清理临时文件
            try:
                os.remove(config_file)
            except:
                pass
