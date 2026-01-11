"""
批量语音克隆器
完全参照 batch_inference.py 的实现方式

支持两种模式：
1. 单进程模式（默认）：模型只加载一次，逐个处理
2. 多进程模式：按说话人并行处理，充分利用显存

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
        fish_python: str = None,
        use_multiprocess: bool = None
    ):
        """
        初始化

        Args:
            fish_speech_dir: fish-speech 目录
            checkpoint_dir: 模型检查点目录
            fish_python: fish-speech Python 可执行文件
            use_multiprocess: 是否使用多进程模式。None 表示自动检测（从环境变量读取）
        """
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

        # 多进程模式配置
        if use_multiprocess is None:
            # 自动检测：如果有GPU且显存充足，自动启用多进程
            self.use_multiprocess = self._should_use_multiprocess()
            if not self.use_multiprocess:
                # 如果自动检测建议不使用，仍然检查环境变量覆盖
                self.use_multiprocess = os.environ.get("FISH_MULTIPROCESS_MODE", "false").lower() == "true"
        else:
            self.use_multiprocess = use_multiprocess

        logger.info(f"Fish-Speech 目录: {self.fish_speech_dir}")
        logger.info(f"检查点目录: {self.checkpoint_dir}")
        logger.info(f"Python 路径: {self.fish_python}")
        logger.info(f"多进程模式: {'启用' if self.use_multiprocess else '禁用'}")

    def _should_use_multiprocess(self) -> bool:
        """
        自动检测是否应该使用多进程模式

        策略：
        - 检测是否有可用的 GPU
        - 检测 GPU 显存是否充足（>=16GB 可以考虑多进程）
        - 如果显存 >= 16GB，启用多进程（可以运行2个worker）

        Returns:
            True 表示应该使用多进程，False 表示使用单进程
        """
        try:
            import torch

            if not torch.cuda.is_available():
                logger.info("[自动检测] 未检测到GPU，使用单进程模式")
                return False

            gpu_count = torch.cuda.device_count()
            if gpu_count == 0:
                logger.info("[自动检测] 未检测到GPU，使用单进程模式")
                return False

            # 检查第一个GPU的显存
            props = torch.cuda.get_device_properties(0)
            total_memory_gb = props.total_memory / 1024**3

            logger.info(f"[自动检测] 检测到 {gpu_count} 个GPU")
            logger.info(f"[自动检测] GPU 0: {props.name}, 显存: {total_memory_gb:.2f} GB")

            # 模型大约需要 6-8 GB，如果显存 >= 16GB，可以运行2个worker
            # 如果显存 >= 24GB，可以运行3个worker
            if total_memory_gb >= 16.0:
                logger.info(f"[自动检测] GPU显存充足 ({total_memory_gb:.2f} GB >= 16 GB)，启用多进程模式")
                return True
            else:
                logger.info(f"[自动检测] GPU显存不足 ({total_memory_gb:.2f} GB < 16 GB)，使用单进程模式")
                return False

        except Exception as e:
            logger.warning(f"[自动检测] GPU检测失败: {e}，使用单进程模式")
            return False

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
        script_dir: str = None,  # 兼容参数
        progress_callback = None  # 进度回调函数
    ) -> Dict[str, str]:
        """
        批量生成音频

        Args:
            tasks: [{"speaker_id": 0, "target_text": "...", "segment_index": 0}, ...]
            speaker_npy_files: {speaker_id: npy_file_path}
            speaker_references: {speaker_id: {reference_text, ...}}
            output_dir: 输出目录
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            {"segment_0": "path/to/segment_0.wav", ...}
        """
        logger.info(f"\n🎵 批量生成 {len(tasks)} 个语音片段...")

        total_tasks = len(tasks)

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
            # 选择使用单进程或多进程脚本
            if self.use_multiprocess:
                script_name = "fish_multiprocess_generate.py"
                mode_desc = "多进程并行"
            else:
                script_name = "fish_batch_generate.py"
                mode_desc = "单进程批量"

            script_path = os.path.join(
                os.path.dirname(__file__),
                script_name
            )

            cmd = [self.fish_python, script_path, config_file]

            logger.info(f"执行生成命令 ({mode_desc}): {' '.join(cmd)}")
            if self.use_multiprocess:
                logger.info(f"多进程模式：将自动检测GPU并行处理多个说话人")
            else:
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
                    # 显示进度信息（支持两种模式的标记）
                    if any(keyword in line for keyword in ['[BatchGen]', '[Worker', '[Main]', '[GPU', 'tokens/sec', 'INFO']):
                        print(line, flush=True)

                    # 解析进度：支持两种模式
                    # 1. 单进程模式: "[BatchGen] 进度: 5/30"
                    # 2. 多进程模式: "[Worker X] Completed Speaker Y: 23 segments" 或 "[Main] Generated 23/46"
                    import re
                    try:
                        # 模式1：单进程批量生成
                        # 支持两种格式: "[BatchGen] 进度: 44/46" 或 "[BatchGen] : 44/46"
                        if '[BatchGen]' in line and ':' in line:
                            # 先尝试匹配带"进度"的格式
                            match = re.search(r'进度:\s*(\d+)/(\d+)', line)
                            if not match:
                                # 如果没有"进度"，尝试匹配只有冒号的格式
                                match = re.search(r'\[BatchGen\]\s*(?:进度)?\s*:\s*(\d+)/(\d+)', line)
                            if match:
                                current = int(match.group(1))
                                total = int(match.group(2))
                                if progress_callback:
                                    progress_callback(current, total)
                                    # 调试日志已移除 - 减少日志输出

                        # 模式2a：Worker进行中的进度 "[Worker 1] Speaker 3 progress: 5/20"
                        elif 'Speaker' in line and 'progress:' in line:
                            # 多进程模式下的说话人进度，暂不处理（无全局总数）
                            pass

                        # 模式2b：Worker完成某个说话人 "[Worker 1] ✅ Completed Speaker 3: 23 segments"
                        elif 'Completed Speaker' in line and 'segments' in line:
                            # 多进程模式下的说话人完成，暂不处理（无全局总数）
                            pass

                        # 模式2c：Worker整体进度 "[Worker 1] ✅ All done! Processed 23/23 segments"
                        elif 'All done!' in line and 'Processed' in line and 'segments' in line:
                            match = re.search(r'Processed\s+(\d+)/(\d+)\s+segments', line)
                            if match:
                                current = int(match.group(1))
                                total = int(match.group(2))
                                if progress_callback:
                                    progress_callback(current, total)

                        # 模式2d：Main总进度 "[Main] All done! Generated 23/46 segments"
                        elif '[Main]' in line and 'Generated' in line and 'segments' in line:
                            match = re.search(r'Generated\s+(\d+)/(\d+)\s+segments', line)
                            if match:
                                current = int(match.group(1))
                                total = int(match.group(2))
                                if progress_callback:
                                    progress_callback(current, total)
                    except Exception as e:
                        print(f"[进度解析失败] {e}, 行: {line}", flush=True)

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
