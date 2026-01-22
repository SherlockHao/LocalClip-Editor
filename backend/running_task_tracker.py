# -*- coding: utf-8 -*-
"""
运行任务追踪器 - 追踪正在后台运行的任务

用于:
1. 追踪每个task_id下正在运行的任务(阶段和语言)
2. 检查是否有正在运行的任务
3. 页面导航和语言切换时恢复任务状态
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import threading


@dataclass
class RunningTask:
    """正在运行的任务信息"""
    task_id: str
    language: str
    stage: str  # speaker_diarization, translation, voice_cloning, stitch, export
    started_at: datetime
    message: str = ""
    progress: int = 0


class RunningTaskTracker:
    """
    全局运行任务追踪器

    全局只能有一个正在运行的任务（跨所有task_id）
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._running_tasks: Dict[str, RunningTask] = {}
        return cls._instance

    def start_task(self, task_id: str, language: str, stage: str) -> bool:
        """
        开始追踪一个任务

        Args:
            task_id: 任务ID
            language: 语言代码 (如 "en", "ko", "default")
            stage: 处理阶段

        Returns:
            True 如果成功开始追踪, False 如果已有任务正在运行（全局）
        """
        with self._lock:
            # 全局检查：是否有任何任务在运行
            if len(self._running_tasks) > 0:
                # 获取正在运行的任务信息
                existing_task_id = list(self._running_tasks.keys())[0]
                existing = self._running_tasks[existing_task_id]
                print(f"[RunningTaskTracker] ⚠️ 全局已有任务正在运行: "
                      f"{existing_task_id} - {existing.language}/{existing.stage}", flush=True)
                return False

            self._running_tasks[task_id] = RunningTask(
                task_id=task_id,
                language=language,
                stage=stage,
                started_at=datetime.utcnow()
            )
            print(f"[RunningTaskTracker] ✅ 开始追踪任务: {task_id} - {language}/{stage}", flush=True)
            return True

    def has_any_running_task(self) -> bool:
        """检查是否有任何任务正在运行（全局）"""
        with self._lock:
            return len(self._running_tasks) > 0

    def get_global_running_task(self) -> Optional[RunningTask]:
        """获取全局正在运行的任务（如果有）"""
        with self._lock:
            if len(self._running_tasks) > 0:
                task_id = list(self._running_tasks.keys())[0]
                return self._running_tasks[task_id]
            return None

    def update_progress(self, task_id: str, progress: int, message: str = ""):
        """更新运行任务的进度"""
        with self._lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].progress = progress
                self._running_tasks[task_id].message = message

    def complete_task(self, task_id: str, language: str = None, stage: str = None):
        """
        标记任务完成,停止追踪

        Args:
            task_id: 任务ID
            language: 可选,用于验证
            stage: 可选,用于验证
        """
        with self._lock:
            if task_id in self._running_tasks:
                running = self._running_tasks[task_id]
                # 验证是否是同一个任务 (可选)
                if language and language != running.language:
                    print(f"[RunningTaskTracker] ⚠️ 语言不匹配: {language} vs {running.language}", flush=True)
                if stage and stage != running.stage:
                    print(f"[RunningTaskTracker] ⚠️ 阶段不匹配: {stage} vs {running.stage}", flush=True)

                del self._running_tasks[task_id]
                print(f"[RunningTaskTracker] ✅ 任务完成,停止追踪: {task_id} - {running.language}/{running.stage}", flush=True)

    def fail_task(self, task_id: str, error_message: str = ""):
        """标记任务失败,停止追踪"""
        with self._lock:
            if task_id in self._running_tasks:
                running = self._running_tasks[task_id]
                del self._running_tasks[task_id]
                print(f"[RunningTaskTracker] ❌ 任务失败,停止追踪: {task_id} - {running.language}/{running.stage} - {error_message}", flush=True)

    def get_running_task(self, task_id: str) -> Optional[RunningTask]:
        """
        获取指定task_id正在运行的任务

        Returns:
            RunningTask 如果有正在运行的任务, 否则 None
        """
        with self._lock:
            return self._running_tasks.get(task_id)

    def has_running_task(self, task_id: str) -> bool:
        """检查指定task_id是否有正在运行的任务"""
        with self._lock:
            return task_id in self._running_tasks

    def get_all_running_tasks(self) -> Dict[str, RunningTask]:
        """获取所有正在运行的任务"""
        with self._lock:
            return dict(self._running_tasks)

    def to_dict(self, running_task: RunningTask) -> dict:
        """将RunningTask转换为可JSON序列化的字典"""
        return {
            "task_id": running_task.task_id,
            "language": running_task.language,
            "stage": running_task.stage,
            "started_at": running_task.started_at.isoformat(),
            "message": running_task.message,
            "progress": running_task.progress
        }


# 全局单例实例
running_task_tracker = RunningTaskTracker()
