# -*- coding: utf-8 -*-
"""
批量处理控制器 - 管理批量任务处理流程

功能:
1. 控制批量处理的开始和停止
2. 按顺序执行任务：说话人识别 -> 各语言(翻译->语音克隆->拼接->导出)
3. 跳过已完成的任务
4. 支持任务取消和状态回滚
5. 支持动态添加任务到队列（批量处理运行中也可添加新任务）
"""

import asyncio
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class BatchProcessorState(Enum):
    """批量处理器状态"""
    IDLE = "idle"  # 空闲
    RUNNING = "running"  # 运行中
    STOPPING = "stopping"  # 正在停止
    STOPPED = "stopped"  # 已停止


@dataclass
class QueuedTask:
    """队列中的任务"""
    task_id: str
    languages: List[str]
    added_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "languages": self.languages,
            "added_at": self.added_at.isoformat()
        }


@dataclass
class BatchProgress:
    """批量处理进度"""
    state: BatchProcessorState = BatchProcessorState.IDLE
    current_task_id: Optional[str] = None
    current_language: Optional[str] = None
    current_stage: Optional[str] = None
    total_tasks: int = 0
    completed_tasks: int = 0
    total_stages: int = 0
    completed_stages: int = 0
    message: str = ""
    started_at: Optional[datetime] = None
    error: Optional[str] = None
    queued_tasks: List[QueuedTask] = field(default_factory=list)  # 等待队列中的任务


class BatchProcessor:
    """
    批量处理控制器（单例模式）

    管理多个任务的批量处理流程
    """

    _instance = None
    _lock = threading.Lock()

    # 支持的语言列表（按顺序）
    SUPPORTED_LANGUAGES = ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id']

    # 每个语言的处理阶段（按顺序）
    LANGUAGE_STAGES = ['translation', 'voice_cloning', 'stitch', 'export']

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._progress = BatchProgress()
        self._cancel_requested = False
        self._processing_lock = None  # 延迟初始化，避免在非异步上下文中创建
        self._current_task = None  # 当前正在执行的 asyncio Task
        self._task_queue: List[QueuedTask] = []  # 动态任务队列
        self._queue_lock = threading.Lock()  # 队列操作锁
        self._callbacks: Optional[Dict[str, Callable]] = None  # 保存回调函数供队列任务使用

    @property
    def progress(self) -> BatchProgress:
        """获取当前进度"""
        return self._progress

    @property
    def is_running(self) -> bool:
        """是否正在运行（包括正在停止中）"""
        return self._progress.state in (BatchProcessorState.RUNNING, BatchProcessorState.STOPPING)

    @property
    def is_cancel_requested(self) -> bool:
        """是否请求了取消"""
        return self._cancel_requested

    @property
    def queued_task_count(self) -> int:
        """获取队列中等待的任务数量"""
        with self._queue_lock:
            return len(self._task_queue)

    def get_queued_tasks(self) -> List[Dict]:
        """获取队列中等待的任务列表"""
        with self._queue_lock:
            return [task.to_dict() for task in self._task_queue]

    def add_task_to_queue(self, task_id: str, languages: List[str] = None) -> bool:
        """
        添加任务到批量处理队列

        如果批量处理正在运行，任务会在当前任务完成后执行
        如果批量处理未运行，返回 False（需要先启动批量处理）

        Args:
            task_id: 任务ID
            languages: 要处理的语言列表，None 表示使用默认语言列表

        Returns:
            是否成功添加到队列
        """
        if not self.is_running:
            print(f"[BatchProcessor] ⚠️ 批量处理未运行，无法添加任务到队列: {task_id}", flush=True)
            return False

        with self._queue_lock:
            # 检查任务是否已在队列中
            for queued_task in self._task_queue:
                if queued_task.task_id == task_id:
                    print(f"[BatchProcessor] ⚠️ 任务已在队列中: {task_id}", flush=True)
                    return False

            # 检查是否是当前正在处理的任务
            if self._progress.current_task_id == task_id:
                print(f"[BatchProcessor] ⚠️ 任务正在处理中: {task_id}", flush=True)
                return False

            # 添加到队列
            queued_task = QueuedTask(
                task_id=task_id,
                languages=languages or self.SUPPORTED_LANGUAGES
            )
            self._task_queue.append(queued_task)

            # 更新进度信息
            self._progress.total_tasks += 1
            self._progress.queued_tasks = list(self._task_queue)

            print(f"[BatchProcessor] ✅ 任务已添加到队列: {task_id}, 队列长度: {len(self._task_queue)}", flush=True)
            return True

    def remove_task_from_queue(self, task_id: str) -> bool:
        """
        从队列中移除任务

        Args:
            task_id: 任务ID

        Returns:
            是否成功移除
        """
        with self._queue_lock:
            for i, queued_task in enumerate(self._task_queue):
                if queued_task.task_id == task_id:
                    self._task_queue.pop(i)
                    self._progress.total_tasks -= 1
                    self._progress.queued_tasks = list(self._task_queue)
                    print(f"[BatchProcessor] ✅ 任务已从队列移除: {task_id}", flush=True)
                    return True

            print(f"[BatchProcessor] ⚠️ 任务不在队列中: {task_id}", flush=True)
            return False

    def _pop_next_task(self) -> Optional[QueuedTask]:
        """从队列中取出下一个任务"""
        with self._queue_lock:
            if self._task_queue:
                task = self._task_queue.pop(0)
                self._progress.queued_tasks = list(self._task_queue)
                return task
            return None

    def get_status(self) -> Dict:
        """获取批量处理状态"""
        return {
            "state": self._progress.state.value,
            "is_running": self.is_running,
            "current_task_id": self._progress.current_task_id,
            "current_language": self._progress.current_language,
            "current_stage": self._progress.current_stage,
            "total_tasks": self._progress.total_tasks,
            "completed_tasks": self._progress.completed_tasks,
            "total_stages": self._progress.total_stages,
            "completed_stages": self._progress.completed_stages,
            "message": self._progress.message,
            "started_at": self._progress.started_at.isoformat() if self._progress.started_at else None,
            "error": self._progress.error,
            "queued_tasks": self.get_queued_tasks(),
            "queued_count": self.queued_task_count
        }

    async def start_batch_for_task(self, task_id: str, languages: List[str], callbacks: Dict[str, Callable]) -> bool:
        """
        为单个任务启动批量处理（编辑页面使用）

        Args:
            task_id: 任务ID
            languages: 要处理的语言列表
            callbacks: 回调函数字典，包含各阶段的处理函数

        Returns:
            是否成功启动
        """
        if self.is_running:
            print(f"[BatchProcessor] ⚠️ 批量处理已在运行中", flush=True)
            return False

        self._cancel_requested = False
        self._progress = BatchProgress(
            state=BatchProcessorState.RUNNING,
            current_task_id=task_id,
            total_tasks=1,
            completed_tasks=0,
            message="开始批量处理...",
            started_at=datetime.utcnow()
        )

        print(f"[BatchProcessor] ✅ 开始单任务批量处理: {task_id}, 语言: {languages}", flush=True)

        try:
            success = await self._process_single_task(task_id, languages, callbacks)

            if self._cancel_requested:
                self._progress.state = BatchProcessorState.STOPPED
                self._progress.message = "批量处理已停止"
                print(f"[BatchProcessor] ⚠️ 单任务批量处理被取消: {task_id}", flush=True)
            elif success:
                self._progress.state = BatchProcessorState.IDLE
                self._progress.completed_tasks = 1
                self._progress.message = "批量处理完成"
                print(f"[BatchProcessor] ✅ 单任务批量处理完成: {task_id}", flush=True)
            else:
                self._progress.state = BatchProcessorState.IDLE
                self._progress.error = "任务处理失败"
                self._progress.message = "批量处理失败"
                print(f"[BatchProcessor] ❌ 单任务批量处理失败: {task_id}", flush=True)

            return success

        except Exception as e:
            self._progress.state = BatchProcessorState.IDLE
            self._progress.error = str(e)
            self._progress.message = f"批量处理异常: {str(e)}"
            print(f"[BatchProcessor] ❌ 单任务批量处理异常: {task_id}, 错误: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    async def start_batch_for_all_tasks(self, task_ids: List[str], callbacks: Dict[str, Callable]) -> bool:
        """
        为多个任务启动批量处理（任务看板使用）

        支持动态队列：处理过程中新添加的任务会自动加入处理队列

        Args:
            task_ids: 任务ID列表
            callbacks: 回调函数字典

        Returns:
            是否成功启动
        """
        if self.is_running:
            print(f"[BatchProcessor] ⚠️ 批量处理已在运行中", flush=True)
            return False

        self._cancel_requested = False
        self._callbacks = callbacks  # 保存回调函数供队列任务使用

        # 初始化队列（将初始任务列表加入队列）
        # 检查每个任务是否已完成，只将未完成的任务加入队列
        with self._queue_lock:
            self._task_queue = []
            for task_id in task_ids:
                # 快速检查任务是否完全完成（所有语言的所有阶段）
                is_fully_completed = await self._is_task_fully_completed(task_id, self.SUPPORTED_LANGUAGES, callbacks)
                if not is_fully_completed:
                    self._task_queue.append(QueuedTask(
                        task_id=task_id,
                        languages=self.SUPPORTED_LANGUAGES
                    ))
                else:
                    print(f"[BatchProcessor] ⏭️  跳过已完成的任务: {task_id}", flush=True)

        # total_tasks 只计算实际需要处理的任务数
        actual_task_count = len(self._task_queue)

        self._progress = BatchProgress(
            state=BatchProcessorState.RUNNING,
            total_tasks=actual_task_count,
            completed_tasks=0,
            message="开始批量处理所有任务...",
            started_at=datetime.utcnow(),
            queued_tasks=list(self._task_queue)
        )

        print(f"[BatchProcessor] ✅ 开始多任务批量处理, 初始队列: {actual_task_count} 个任务 (共 {len(task_ids)} 个，{len(task_ids) - actual_task_count} 个已完成)", flush=True)

        failed_tasks = []
        processed_count = 0

        # 循环处理队列中的任务，支持动态添加
        while True:
            if self._cancel_requested:
                print(f"[BatchProcessor] ⚠️ 批量处理被取消，已完成 {processed_count} 个任务", flush=True)
                break

            # 从队列中获取下一个任务
            queued_task = self._pop_next_task()
            if queued_task is None:
                # 队列为空，等待新任务添加（每2秒检查一次）
                # 最多等待10次（20秒），如果仍然没有新任务则停止
                wait_count = 0
                max_wait_count = 10

                while wait_count < max_wait_count:
                    if self._cancel_requested:
                        break

                    # 更新状态显示等待中
                    self._progress.message = f"队列为空，等待新任务... ({wait_count + 1}/{max_wait_count})"
                    print(f"[BatchProcessor] 📭 队列为空，等待新任务添加... ({wait_count + 1}/{max_wait_count})", flush=True)

                    await asyncio.sleep(2)
                    wait_count += 1

                    # 检查是否有新任务添加到队列
                    queued_task = self._pop_next_task()
                    if queued_task is not None:
                        print(f"[BatchProcessor] 📬 检测到新任务: {queued_task.task_id}", flush=True)
                        break

                # 如果等待超时仍没有新任务，则停止
                if queued_task is None:
                    print(f"[BatchProcessor] ✅ 队列已清空且无新任务，批量处理完成", flush=True)
                    break

            task_id = queued_task.task_id
            languages = queued_task.languages

            self._progress.current_task_id = task_id
            self._progress.message = f"处理任务 {processed_count + 1}/{self._progress.total_tasks}: {task_id} (队列剩余: {self.queued_task_count})"

            print(f"[BatchProcessor] 📋 开始处理任务: {task_id}, 语言: {languages}, 队列剩余: {self.queued_task_count}", flush=True)

            try:
                # 获取任务的语言列表（如果回调提供）
                if 'get_task_languages' in callbacks:
                    languages = await callbacks['get_task_languages'](task_id)

                success = await self._process_single_task(task_id, languages, callbacks)
                if not success:
                    failed_tasks.append(task_id)

            except Exception as e:
                # 单个任务失败，记录错误但继续处理下一个任务
                print(f"[BatchProcessor] ❌ 任务 {task_id} 处理异常: {e}", flush=True)
                import traceback
                traceback.print_exc()
                failed_tasks.append(task_id)

            if not self._cancel_requested:
                processed_count += 1
                self._progress.completed_tasks = processed_count

        # 清理
        self._callbacks = None

        # 清空队列（确保没有遗留任务）
        with self._queue_lock:
            self._task_queue = []

        if not self._cancel_requested:
            # 批量处理正常完成，重置状态
            self._progress.state = BatchProcessorState.IDLE
            self._progress.current_task_id = None
            self._progress.current_language = None
            self._progress.current_stage = None
            self._progress.queued_tasks = []

            if failed_tasks:
                self._progress.message = f"批量处理完成，{len(failed_tasks)} 个任务失败"
                self._progress.error = f"失败的任务: {', '.join(failed_tasks)}"
            else:
                self._progress.message = f"所有任务批量处理完成 (共 {processed_count} 个)"

            print(f"[BatchProcessor] ✅ 批量处理完成，成功: {processed_count - len(failed_tasks)}, 失败: {len(failed_tasks)}", flush=True)
            print(f"[BatchProcessor] ✅ 批量处理已自动停止", flush=True)
        else:
            self._progress.state = BatchProcessorState.STOPPED
            self._progress.current_task_id = None
            self._progress.current_language = None
            self._progress.current_stage = None
            self._progress.queued_tasks = []
            self._progress.message = "批量处理已停止"

        return len(failed_tasks) == 0

    async def _get_task_languages(self, task_id: str, callbacks: Dict[str, Callable]) -> List[str]:
        """获取任务配置的语言列表"""
        if 'get_task_languages' in callbacks:
            return await callbacks['get_task_languages'](task_id)
        return self.SUPPORTED_LANGUAGES

    async def _is_task_fully_completed(self, task_id: str, languages: List[str], callbacks: Dict[str, Callable]) -> bool:
        """
        检查任务是否完全完成（所有语言的所有阶段都已完成）

        Args:
            task_id: 任务ID
            languages: 要检查的语言列表
            callbacks: 回调函数字典

        Returns:
            True 如果所有阶段都已完成，False 否则
        """
        if 'check_stage_completed' not in callbacks:
            return False

        # 检查说话人识别是否完成
        speaker_completed = await callbacks['check_stage_completed'](task_id, "default", "speaker_diarization")
        if not speaker_completed:
            return False

        # 检查所有语言的所有阶段是否完成
        for language in languages:
            for stage in self.LANGUAGE_STAGES:
                stage_completed = await callbacks['check_stage_completed'](task_id, language, stage)
                if not stage_completed:
                    return False

        return True

    async def _process_single_task(self, task_id: str, languages: List[str], callbacks: Dict[str, Callable]) -> bool:
        """
        处理单个任务的完整流程

        顺序：说话人识别 -> 各语言(翻译->语音克隆->拼接->导出)

        Returns:
            True 如果任务成功完成（至少说话人识别成功），False 如果任务失败
        """
        # 计算总阶段数：1(说话人识别) + 语言数 * 4(每语言4个阶段)
        total_stages = 1 + len(languages) * len(self.LANGUAGE_STAGES)
        self._progress.total_stages = total_stages
        self._progress.completed_stages = 0

        # 1. 说话人识别
        if self._cancel_requested:
            return True  # 取消不算失败

        self._progress.current_stage = "speaker_diarization"
        self._progress.current_language = "default"
        self._progress.message = "执行说话人识别..."

        # 检查是否已完成
        is_completed = await self._check_stage_completed(task_id, "default", "speaker_diarization", callbacks)

        if not is_completed:
            print(f"[BatchProcessor] 执行说话人识别: {task_id}", flush=True)
            success = await self._run_stage(task_id, "default", "speaker_diarization", callbacks)
            if not success and not self._cancel_requested:
                # 说话人识别失败，跳过该任务的所有后续阶段
                print(f"[BatchProcessor] ⚠️ 说话人识别失败，跳过任务: {task_id}", flush=True)
                # 更新已完成阶段数（跳过所有语言的所有阶段）
                self._progress.completed_stages += len(languages) * len(self.LANGUAGE_STAGES)
                return False  # 任务失败
        else:
            print(f"[BatchProcessor] 跳过已完成的说话人识别: {task_id}", flush=True)

        self._progress.completed_stages += 1

        # 2. 遍历每种语言
        for language in languages:
            if self._cancel_requested:
                return True  # 取消不算失败

            self._progress.current_language = language

            # 遍历每个阶段
            for stage in self.LANGUAGE_STAGES:
                if self._cancel_requested:
                    return True  # 取消不算失败

                self._progress.current_stage = stage
                self._progress.message = f"执行 {language} 的 {self._get_stage_name(stage)}..."

                # 检查是否已完成
                is_completed = await self._check_stage_completed(task_id, language, stage, callbacks)

                if not is_completed:
                    print(f"[BatchProcessor] 执行 {language}/{stage}: {task_id}", flush=True)
                    success = await self._run_stage(task_id, language, stage, callbacks)
                    if not success and not self._cancel_requested:
                        # 某个阶段失败，跳过该语言的后续阶段
                        print(f"[BatchProcessor] ⚠️ {language}/{stage} 失败，跳过该语言后续阶段", flush=True)
                        # 跳过该语言剩余的阶段
                        remaining_stages = len(self.LANGUAGE_STAGES) - self.LANGUAGE_STAGES.index(stage) - 1
                        self._progress.completed_stages += remaining_stages
                        break
                else:
                    print(f"[BatchProcessor] 跳过已完成的 {language}/{stage}: {task_id}", flush=True)

                self._progress.completed_stages += 1

        return True  # 任务成功完成

    async def _check_stage_completed(self, task_id: str, language: str, stage: str, callbacks: Dict[str, Callable]) -> bool:
        """检查某个阶段是否已完成"""
        if 'check_stage_completed' in callbacks:
            return await callbacks['check_stage_completed'](task_id, language, stage)
        return False

    async def _run_stage(self, task_id: str, language: str, stage: str, callbacks: Dict[str, Callable]) -> bool:
        """
        执行某个阶段

        Returns:
            是否成功
        """
        callback_name = f'run_{stage}'
        if callback_name not in callbacks:
            print(f"[BatchProcessor] ⚠️ 未找到回调函数: {callback_name}", flush=True)
            return False

        try:
            return await callbacks[callback_name](task_id, language)
        except Exception as e:
            print(f"[BatchProcessor] ❌ 执行 {stage} 失败: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return False

    def request_cancel(self) -> bool:
        """
        请求取消批量处理（当前阶段完成后停止）

        Returns:
            是否成功请求取消
        """
        if not self.is_running:
            print(f"[BatchProcessor] ⚠️ 没有正在运行的批量处理", flush=True)
            return False

        self._cancel_requested = True
        self._progress.state = BatchProcessorState.STOPPING
        # 更新消息，告知用户当前阶段完成后停止
        current_stage_name = self._get_stage_name(self._progress.current_stage) if self._progress.current_stage else "当前任务"
        self._progress.message = f"等待 {current_stage_name} 完成后停止..."
        print(f"[BatchProcessor] ⚠️ 已请求取消批量处理，将在当前阶段完成后停止", flush=True)
        return True

    def reset(self):
        """重置批量处理器状态"""
        self._cancel_requested = False
        with self._queue_lock:
            self._task_queue = []
        self._callbacks = None
        self._progress = BatchProgress()
        print(f"[BatchProcessor] 已重置批量处理器状态", flush=True)

    def _get_stage_name(self, stage: str) -> str:
        """获取阶段的中文名称"""
        stage_names = {
            'speaker_diarization': '说话人识别',
            'translation': '翻译',
            'voice_cloning': '语音克隆',
            'stitch': '音频拼接',
            'export': '视频导出'
        }
        return stage_names.get(stage, stage)


# 全局单例实例
batch_processor = BatchProcessor()
