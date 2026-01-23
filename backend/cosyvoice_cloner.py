# -*- coding: utf-8 -*-
"""
CosyVoice3 语音克隆器
基于 Fun-CosyVoice3-0.5B 模型，支持多语言语音克隆

通过子进程调用 cosyvoice 环境中的脚本，类似于 xtts_cloner

特点：
- 无需预编码，直接使用参考音频
- 支持 GPU 加速
- 支持多语言（中、英、日、韩、法、德、西班牙语等）
- 支持双 GPU 并行处理

作者：Claude
"""
import os
import sys
import subprocess
import json
import tempfile
import platform
import threading
import math
from typing import Dict, List, Optional, Callable
from loguru import logger


class CosyVoiceCloner:
    """
    CosyVoice3 语音克隆器

    特点：
    - 通过子进程调用 cosyvoice 环境
    - 直接使用参考音频，无需预编码
    - 支持 GPU 加速
    - 支持双 GPU 并行处理
    """

    def __init__(
        self,
        cosyvoice_python: str = None,
        use_gpu: bool = True,
        gpu_ids: List[int] = None
    ):
        """
        初始化 CosyVoice 克隆器

        Args:
            cosyvoice_python: cosyvoice 环境的 Python 可执行文件路径
            use_gpu: 是否使用 GPU
            gpu_ids: 可用的 GPU ID 列表，例如 [0, 1] 表示使用两块 GPU
        """
        self.use_gpu = use_gpu
        self.gpu_ids = gpu_ids or [0]  # 默认使用 GPU 0

        # 根据平台设置默认路径
        if platform.system() == "Windows":
            self.cosyvoice_python = cosyvoice_python or os.environ.get(
                "COSYVOICE_PYTHON",
                r"C:\Miniconda3\envs\cosyvoice\python.exe"
            )
        else:
            self.cosyvoice_python = cosyvoice_python or os.environ.get(
                "COSYVOICE_PYTHON",
                "/Users/yiya_workstation/miniconda3/envs/cosyvoice/bin/python"
            )

        logger.info(f"CosyVoice3 克隆器初始化")
        logger.info(f"  Python 路径: {self.cosyvoice_python}")
        logger.info(f"  GPU: {'启用' if use_gpu else '禁用'}")
        logger.info(f"  GPU IDs: {self.gpu_ids}")

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        speaker_references: Dict[int, Dict],
        output_dir: str,
        target_language: str = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """
        批量生成音频（支持双 GPU 并行）

        Args:
            tasks: 任务列表 [{"speaker_id": 0, "target_text": "...", "segment_index": 0}, ...]
            speaker_references: 说话人参考数据 {speaker_id: {reference_audio, reference_text, target_language, ...}}
            output_dir: 输出目录
            target_language: 目标语言（如果 tasks 中没有指定）
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            {segment_index: output_file_path, ...}
        """
        logger.info(f"\n🎵 [CosyVoice] 批量生成 {len(tasks)} 个语音片段...")
        print(f"\n🎵 [CosyVoice] 批量生成 {len(tasks)} 个语音片段...", flush=True)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 验证任务，构建有效任务列表
        valid_tasks = []
        for task in tasks:
            speaker_id = task["speaker_id"]
            segment_index = task["segment_index"]
            target_text = task["target_text"]

            # 获取说话人参考信息
            ref_info = speaker_references.get(speaker_id)
            if not ref_info:
                logger.warning(f"[CosyVoice] ⚠️ 说话人 {speaker_id} 没有参考数据，跳过片段 {segment_index}")
                continue

            reference_audio = ref_info.get("reference_audio")
            if not reference_audio or not os.path.exists(reference_audio):
                logger.warning(f"[CosyVoice] ⚠️ 说话人 {speaker_id} 的参考音频不存在: {reference_audio}")
                continue

            # 确定目标语言
            lang = target_language or ref_info.get("target_language", "en")

            valid_tasks.append({
                "segment_index": segment_index,
                "speaker_id": speaker_id,
                "target_text": target_text,
                "reference_audio": os.path.abspath(reference_audio),
                "target_language": lang,
                "output_file": os.path.abspath(
                    os.path.join(output_dir, f"segment_{segment_index}.wav")
                )
            })

        if not valid_tasks:
            logger.warning("[CosyVoice] 没有有效的任务")
            return {}

        # 如果只有一个 GPU 或任务数较少，使用单 GPU
        if len(self.gpu_ids) == 1 or len(valid_tasks) <= 5:
            return self._generate_on_single_gpu(
                valid_tasks, output_dir, target_language, self.gpu_ids[0], progress_callback
            )
        else:
            # 使用双 GPU 并行处理
            return self._generate_on_dual_gpu(
                valid_tasks, output_dir, target_language, progress_callback
            )

    def _generate_on_single_gpu(
        self,
        tasks: List[Dict],
        output_dir: str,
        target_language: str,
        gpu_id: int,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """在单个 GPU 上生成音频"""
        print(f"[CosyVoice] 使用 GPU {gpu_id} 生成 {len(tasks)} 个片段", flush=True)

        generate_config = {
            "mode": "generate",
            "use_gpu": self.use_gpu,
            "gpu_id": gpu_id,
            "output_dir": os.path.abspath(output_dir),
            "target_language": target_language,
            "tasks": tasks
        }

        return self._run_generation_subprocess(generate_config, progress_callback)

    def _generate_on_dual_gpu(
        self,
        tasks: List[Dict],
        output_dir: str,
        target_language: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """在双 GPU 上并行生成音频"""
        print(f"[CosyVoice] 使用双 GPU {self.gpu_ids} 并行生成 {len(tasks)} 个片段", flush=True)

        # 将任务分成两半
        mid = len(tasks) // 2
        tasks_gpu0 = tasks[:mid]
        tasks_gpu1 = tasks[mid:]

        print(f"[CosyVoice] GPU {self.gpu_ids[0]}: {len(tasks_gpu0)} 个任务", flush=True)
        print(f"[CosyVoice] GPU {self.gpu_ids[1]}: {len(tasks_gpu1)} 个任务", flush=True)

        # 创建两个配置
        config_gpu0 = {
            "mode": "generate",
            "use_gpu": self.use_gpu,
            "gpu_id": self.gpu_ids[0],
            "output_dir": os.path.abspath(output_dir),
            "target_language": target_language,
            "tasks": tasks_gpu0
        }

        config_gpu1 = {
            "mode": "generate",
            "use_gpu": self.use_gpu,
            "gpu_id": self.gpu_ids[1],
            "output_dir": os.path.abspath(output_dir),
            "target_language": target_language,
            "tasks": tasks_gpu1
        }

        # 用于存储结果
        results = [{}, {}]
        completed = [0, 0]
        total_tasks = len(tasks)
        lock = threading.Lock()

        def run_on_gpu(config, result_idx):
            def local_progress(current, total):
                with lock:
                    completed[result_idx] = current
                    total_completed = sum(completed)
                    if progress_callback:
                        progress_callback(total_completed, total_tasks)

            results[result_idx] = self._run_generation_subprocess(config, local_progress)

        # 启动两个线程
        thread0 = threading.Thread(target=run_on_gpu, args=(config_gpu0, 0))
        thread1 = threading.Thread(target=run_on_gpu, args=(config_gpu1, 1))

        thread0.start()
        thread1.start()

        thread0.join()
        thread1.join()

        # 合并结果
        merged_results = {}
        merged_results.update(results[0])
        merged_results.update(results[1])

        return merged_results

    def _run_generation_subprocess(
        self,
        config: Dict,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """运行生成子进程"""
        # 写入临时配置
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            config_file = f.name

        try:
            # 调用生成脚本
            script_path = os.path.join(
                os.path.dirname(__file__),
                "cosyvoice_batch_generate.py"
            )

            cmd = [self.cosyvoice_python, script_path, config_file]

            gpu_id = config.get("gpu_id", 0)
            logger.info(f"执行生成命令 (GPU {gpu_id}): {' '.join(cmd)}")
            print(f"[CosyVoice] GPU {gpu_id} 执行: {' '.join(cmd)}", flush=True)

            # 设置 CUDA 设备环境变量
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)

            # 使用 Popen 实时显示输出
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1,
                env=env
            )

            # 实时读取并显示输出
            output_lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    # 显示进度信息
                    if '[CosyVoice]' in line or 'INFO' in line:
                        print(f"[GPU {gpu_id}] {line}", flush=True)

                    # 解析进度
                    import re
                    try:
                        if '[CosyVoice]' in line and ('进度' in line or 'Progress' in line or '/' in line):
                            match = re.search(r'(\d+)/(\d+)', line)
                            if match:
                                current = int(match.group(1))
                                total = int(match.group(2))
                                if progress_callback:
                                    progress_callback(current, total)
                    except Exception:
                        pass

                    output_lines.append(line)

            # 等待进程结束
            proc.wait()

            if proc.returncode != 0:
                logger.error(f"[CosyVoice] GPU {gpu_id} 生成失败！返回码: {proc.returncode}")
                for line in output_lines[-20:]:
                    logger.error(line)
                raise RuntimeError(f"CosyVoice 生成失败，返回码: {proc.returncode}")

            # 解析结果 - 从后向前查找有效的 JSON 对象行
            try:
                json_line = "{}"
                for line in reversed(output_lines):
                    line = line.strip()
                    if line.startswith('{') and line.endswith('}'):
                        try:
                            json.loads(line)  # 验证是有效 JSON
                            json_line = line
                            break
                        except json.JSONDecodeError:
                            continue

                result_data = json.loads(json_line)

                # 将字符串键转换为整数键
                result_data = {int(k): v for k, v in result_data.items()}

                logger.info(f"✅ [CosyVoice] GPU {gpu_id} 完成！生成 {len(result_data)} 个音频文件")
                print(f"✅ [CosyVoice] GPU {gpu_id} 完成！生成 {len(result_data)} 个音频文件", flush=True)
                return result_data

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"解析 CosyVoice 结果失败: {e}")
                logger.error(f"输出最后10行: {output_lines[-10:] if output_lines else []}")
                raise

        finally:
            # 清理临时文件
            try:
                os.remove(config_file)
            except:
                pass


# 全局单例
_global_cosyvoice_cloner: Optional[CosyVoiceCloner] = None


def get_cosyvoice_cloner(use_gpu: bool = True, gpu_ids: List[int] = None) -> CosyVoiceCloner:
    """
    获取全局 CosyVoice 克隆器实例（单例模式）

    Args:
        use_gpu: 是否使用 GPU
        gpu_ids: GPU ID 列表，例如 [0, 1] 使用双 GPU

    Returns:
        CosyVoiceCloner 实例
    """
    global _global_cosyvoice_cloner

    if _global_cosyvoice_cloner is None:
        _global_cosyvoice_cloner = CosyVoiceCloner(use_gpu=use_gpu, gpu_ids=gpu_ids)

    return _global_cosyvoice_cloner


def reset_cosyvoice_cloner():
    """重置全局 CosyVoice 克隆器"""
    global _global_cosyvoice_cloner
    _global_cosyvoice_cloner = None
