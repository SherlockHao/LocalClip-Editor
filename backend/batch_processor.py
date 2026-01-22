# -*- coding: utf-8 -*-
"""
批量处理控制器 - 管理批量任务处理流程

功能:
1. 控制批量处理的开始和停止
2. 按顺序执行任务：说话人识别 -> 各语言(翻译->语音克隆->拼接->导出)
3. 跳过已完成的任务
4. 支持任务取消和状态回滚
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
            "error": self._progress.error
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
        self._progress = BatchProgress(
            state=BatchProcessorState.RUNNING,
            total_tasks=len(task_ids),
            completed_tasks=0,
            message="开始批量处理所有任务...",
            started_at=datetime.utcnow()
        )

        print(f"[BatchProcessor] ✅ 开始多任务批量处理, 共 {len(task_ids)} 个任务", flush=True)

        failed_tasks = []

        for i, task_id in enumerate(task_ids):
            if self._cancel_requested:
                print(f"[BatchProcessor] ⚠️ 批量处理被取消，已完成 {i}/{len(task_ids)} 个任务", flush=True)
                break

            self._progress.current_task_id = task_id
            self._progress.message = f"处理任务 {i+1}/{len(task_ids)}: {task_id}"

            try:
                # 获取任务的语言列表
                languages = await self._get_task_languages(task_id, callbacks)

                success = await self._process_single_task(task_id, languages, callbacks)
                if not success:
                    failed_tasks.append(task_id)

            except Exception as e:
                # 单个任务失败，记录错误但继续处理下一个任务
                print(f"[BatchProcessor] ❌ 任务 {task_id} 处理异常: {e}", flush=True)
                failed_tasks.append(task_id)

            if not self._cancel_requested:
                self._progress.completed_tasks = i + 1

        if not self._cancel_requested:
            self._progress.state = BatchProcessorState.IDLE
            if failed_tasks:
                self._progress.message = f"批量处理完成，{len(failed_tasks)} 个任务失败"
                self._progress.error = f"失败的任务: {', '.join(failed_tasks)}"
            else:
                self._progress.message = "所有任务批量处理完成"
            print(f"[BatchProcessor] ✅ 批量处理完成，成功: {len(task_ids) - len(failed_tasks)}, 失败: {len(failed_tasks)}", flush=True)
        else:
            self._progress.state = BatchProcessorState.STOPPED
            self._progress.message = "批量处理已停止"

        return len(failed_tasks) == 0

    async def _get_task_languages(self, task_id: str, callbacks: Dict[str, Callable]) -> List[str]:
        """获取任务配置的语言列表"""
        if 'get_task_languages' in callbacks:
            return await callbacks['get_task_languages'](task_id)
        return self.SUPPORTED_LANGUAGES

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
