"""
跨环境并行克隆引擎
使用 subprocess 启动 fish-speech 环境的 worker 进程

这个方案解决了环境依赖冲突：
- ui 环境：运行 FastAPI 和协调器
- fish-speech 环境：运行 worker 进程（有完整依赖）

作者：Claude
"""
import os
import sys
import json
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List
from loguru import logger


# 获取环境配置
if platform.system() == "Windows":
    FISH_SPEECH_DIR = os.environ.get("FISH_SPEECH_DIR", r"d:/ai_editing\fish-speech-win")
    FISH_PYTHON = os.environ.get("FISH_SPEECH_PYTHON", r"C:\Users\7\miniconda3\envs\fish-speech\python.exe")
else:
    FISH_SPEECH_DIR = os.environ.get("FISH_SPEECH_DIR", "/Users/yiya_workstation/Documents/ai_editing/fish-speech")
    FISH_PYTHON = os.environ.get("FISH_SPEECH_PYTHON", "/Users/yiya_workstation/miniconda3/envs/fish-speech/bin/python")

CHECKPOINT_DIR = os.path.join(FISH_SPEECH_DIR, "checkpoints", "openaudio-s1-mini")


class SubprocessParallelCloner:
    """
    使用 subprocess 的并行克隆器

    优势：
    - 跨说话人真正并行
    - 模型只加载一次（每个 worker）
    - 避免环境依赖冲突
    """

    def __init__(
        self,
        num_workers: int = 2,
        checkpoint_path: str = CHECKPOINT_DIR,
        batch_size: int = 10
    ):
        self.num_workers = num_workers
        self.checkpoint_path = checkpoint_path
        self.batch_size = batch_size
        self.fish_python = FISH_PYTHON
        self.fish_speech_dir = FISH_SPEECH_DIR

    def batch_encode_speakers(
        self,
        speaker_references: Dict[int, Dict],
        output_dir: str
    ) -> Dict[int, str]:
        """
        批量编码说话人参考音频
        使用 FishBatchCloner 的实现（编码速度已足够快，不需要并行）

        Args:
            speaker_references: 说话人参考信息
            output_dir: 输出目录

        Returns:
            说话人编码文件映射 {speaker_id: npy_file_path}
        """
        from fish_batch_cloner import FishBatchCloner

        logger.info("🔄 使用批量编码模式（通过 fish-speech 环境）")
        cloner = FishBatchCloner(
            fish_speech_dir=self.fish_speech_dir,
            checkpoint_dir=self.checkpoint_path
        )
        return cloner.batch_encode_speakers(speaker_references, output_dir)

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        speaker_npy_files: Dict[int, str],
        speaker_references: Dict[int, Dict],
        output_dir: str,
        script_dir: str = None  # 兼容参数，不使用（subprocess模式不需要脚本目录）
    ) -> Dict[str, str]:
        """
        并行生成音频

        Args:
            tasks: 任务列表
            speaker_npy_files: 说话人编码文件映射
            speaker_references: 说话人参考信息
            output_dir: 输出目录

        Returns:
            生成的音频文件映射
        """
        # 按说话人分组任务
        tasks_by_speaker = self._group_by_speaker(tasks)

        logger.info(f"\n📊 任务统计:")
        for speaker_id, speaker_tasks in tasks_by_speaker.items():
            logger.info(f"  说话人 {speaker_id}: {len(speaker_tasks)} 个片段")

        # 创建临时任务文件
        task_files = []
        for speaker_id, speaker_tasks in tasks_by_speaker.items():
            task_file = self._create_task_file(
                speaker_id,
                speaker_tasks,
                speaker_npy_files[speaker_id],
                speaker_references[speaker_id],
                output_dir
            )
            task_files.append((speaker_id, task_file))

        # 并行处理所有说话人（使用 worker 池）
        logger.info(f"\n🚀 使用 {self.num_workers} 个并行 worker 处理 {len(task_files)} 个说话人...")

        all_generated_files = {}
        active_processes = []
        task_queue = list(task_files)
        completed = 0

        # 启动初始的 worker 批次
        while len(active_processes) < self.num_workers and task_queue:
            speaker_id, task_file = task_queue.pop(0)
            proc = self._start_worker(speaker_id, task_file)
            active_processes.append((speaker_id, task_file, proc))

        # 处理所有任务
        while active_processes:
            # 检查已完成的进程
            for i in range(len(active_processes) - 1, -1, -1):
                speaker_id, task_file, proc = active_processes[i]

                # 非阻塞检查进程是否完成
                retcode = proc.poll()
                if retcode is not None:
                    # 进程已完成
                    completed += 1
                    active_processes.pop(i)

                    try:
                        stdout, stderr = proc.communicate(timeout=1)
                        stderr_text = stderr.decode('utf-8', errors='ignore')

                        if retcode == 0:
                            # 解析 JSON 输出
                            stdout_text = stdout.decode('utf-8', errors='ignore')
                            # 只解析最后一行（JSON 输出）
                            json_line = stdout_text.strip().split('\n')[-1] if stdout_text.strip() else "{}"
                            result = json.loads(json_line)
                            all_generated_files.update(result)
                            logger.info(f"✅ 说话人 {speaker_id} 完成 ({completed}/{len(task_files)}): {len(result)} 个文件")

                            # 显示 worker 日志
                            if stderr_text.strip():
                                logger.debug(f"Worker {speaker_id} 日志:\n{stderr_text}")
                        else:
                            logger.error(f"❌ 说话人 {speaker_id} 失败 (返回码: {retcode})")
                            logger.error(f"Worker stderr:\n{stderr_text}")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ 说话人 {speaker_id} JSON 解析失败: {e}")
                        logger.error(f"Worker output: {stdout.decode('utf-8', errors='ignore')}")
                    except Exception as e:
                        logger.error(f"❌ 说话人 {speaker_id} 错误: {e}")

                    # 启动新的 worker（如果还有待处理任务）
                    if task_queue:
                        next_speaker_id, next_task_file = task_queue.pop(0)
                        next_proc = self._start_worker(next_speaker_id, next_task_file)
                        active_processes.append((next_speaker_id, next_task_file, next_proc))

            # 短暂休眠避免忙等待
            import time
            time.sleep(0.1)

        # 清理临时文件
        for _, task_file in task_files:
            try:
                os.remove(task_file)
            except:
                pass

        logger.info(f"\n🎉 并行生成完成！共生成 {len(all_generated_files)} 个音频文件")
        return all_generated_files

    def _group_by_speaker(self, tasks: List[Dict]) -> Dict[int, List[Dict]]:
        """按说话人分组任务"""
        tasks_by_speaker = {}
        for task in tasks:
            speaker_id = task["speaker_id"]
            if speaker_id not in tasks_by_speaker:
                tasks_by_speaker[speaker_id] = []
            tasks_by_speaker[speaker_id].append(task)
        return tasks_by_speaker

    def _create_task_file(
        self,
        speaker_id: int,
        tasks: List[Dict],
        npy_file: str,
        reference: Dict,
        output_dir: str
    ) -> str:
        """创建任务配置文件"""
        # 确保所有路径都是绝对路径（worker 进程工作目录是 fish-speech-win）
        npy_file_abs = os.path.abspath(npy_file)
        output_dir_abs = os.path.abspath(output_dir)

        task_data = {
            "speaker_id": speaker_id,
            "tasks": tasks,
            "npy_file": npy_file_abs,
            "reference": reference,
            "output_dir": output_dir_abs,
            "checkpoint_path": self.checkpoint_path,
            "batch_size": self.batch_size,
            "fish_speech_dir": self.fish_speech_dir
        }

        # 创建临时文件
        fd, path = tempfile.mkstemp(suffix='.json', prefix=f'speaker_{speaker_id}_')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, ensure_ascii=False, indent=2)

        return path

    def _start_worker(self, speaker_id: int, task_file: str) -> subprocess.Popen:
        """启动 worker 进程"""
        # 创建 worker 脚本
        worker_script = self._get_worker_script_path()

        # 启动进程
        cmd = [self.fish_python, worker_script, task_file]

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.fish_speech_dir
        )

        logger.info(f"  启动 worker for 说话人 {speaker_id} (PID: {proc.pid})")
        return proc

    def _get_worker_script_path(self) -> str:
        """获取 worker 脚本路径"""
        backend_dir = Path(__file__).parent
        return str(backend_dir / "fish_subprocess_worker.py")
