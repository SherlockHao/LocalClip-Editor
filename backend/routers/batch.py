# -*- coding: utf-8 -*-
"""
批量处理路由 - 批量任务处理 API
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

from database import get_db
from models.task import Task
from batch_processor import batch_processor, BatchProcessorState
from running_task_tracker import running_task_tracker
from path_utils import task_path_manager
from progress_manager import update_task_progress, mark_task_failed, mark_task_completed

router = APIRouter(prefix="/api/batch", tags=["batch"])


# ==================== Pydantic 模型 ====================

class BatchStartRequest(BaseModel):
    """批量处理启动请求"""
    task_ids: Optional[List[str]] = None  # 如果为空，处理所有任务
    languages: Optional[List[str]] = None  # 如果为空，使用默认语言列表


class SingleTaskBatchRequest(BaseModel):
    """单任务批量处理请求"""
    languages: List[str]  # 要处理的语言列表
    speaker_voice_mapping: Dict[str, str] = {}  # 说话人到音色的映射


# ==================== 批量处理状态 API ====================

@router.get("/status")
async def get_batch_status():
    """
    获取批量处理状态
    """
    return batch_processor.get_status()


# ==================== 批量处理控制 API ====================

@router.post("/start")
async def start_batch_processing(
    request: BatchStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    启动批量处理（任务看板使用）

    处理所有任务或指定任务列表
    """
    if batch_processor.is_running:
        raise HTTPException(status_code=409, detail="批量处理已在运行中")

    # 获取要处理的任务
    if request.task_ids:
        tasks = db.query(Task).filter(Task.task_id.in_(request.task_ids)).all()
    else:
        tasks = db.query(Task).order_by(Task.created_at.asc()).all()

    if not tasks:
        raise HTTPException(status_code=404, detail="没有找到任务")

    task_ids = [task.task_id for task in tasks]
    languages = request.languages or batch_processor.SUPPORTED_LANGUAGES

    print(f"[批量处理] 准备处理 {len(task_ids)} 个任务, 语言: {languages}", flush=True)

    # 创建回调函数
    callbacks = _create_callbacks(db, languages)

    # 在后台启动批量处理
    background_tasks.add_task(
        _run_batch_all_tasks,
        task_ids,
        callbacks,
        db
    )

    return {
        "success": True,
        "message": f"已启动批量处理，共 {len(task_ids)} 个任务",
        "task_count": len(task_ids)
    }


@router.post("/start/{task_id}")
async def start_single_task_batch(
    task_id: str,
    request: SingleTaskBatchRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    启动单个任务的批量处理（编辑页面使用）

    按顺序执行：说话人识别 -> 各语言(翻译->语音克隆->拼接->导出)
    """
    if batch_processor.is_running:
        raise HTTPException(status_code=409, detail="批量处理已在运行中")

    # 检查任务是否存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    languages = request.languages
    if not languages:
        raise HTTPException(status_code=400, detail="请指定要处理的语言列表")

    print(f"[批量处理] 准备处理单个任务 {task_id}, 语言: {languages}", flush=True)

    # 保存说话人音色映射到任务配置
    if request.speaker_voice_mapping:
        config = task.config or {}
        config['speaker_voice_mapping'] = request.speaker_voice_mapping
        task.config = config
        db.commit()

    # 创建回调函数
    callbacks = _create_callbacks(db, languages)

    # 在后台启动批量处理
    background_tasks.add_task(
        _run_batch_single_task,
        task_id,
        languages,
        callbacks,
        db
    )

    return {
        "success": True,
        "message": f"已启动任务 {task_id} 的批量处理",
        "languages": languages
    }


@router.post("/stop")
async def stop_batch_processing():
    """
    停止批量处理
    """
    # 请求取消批量处理
    batch_canceled = batch_processor.request_cancel()

    # 同时请求取消当前运行的任务
    task_canceled = running_task_tracker.request_cancel()

    if batch_canceled or task_canceled:
        return {
            "success": True,
            "message": "已请求停止批量处理"
        }
    else:
        return {
            "success": False,
            "message": "没有正在运行的批量处理"
        }


# ==================== 动态队列 API ====================

class QueueTaskRequest(BaseModel):
    """添加任务到队列请求"""
    languages: Optional[List[str]] = None  # 如果为空，使用默认语言列表


@router.post("/queue/{task_id}")
async def add_task_to_queue(
    task_id: str,
    request: QueueTaskRequest = None,
    db: Session = Depends(get_db)
):
    """
    添加任务到批量处理队列

    如果批量处理正在运行，任务将在当前任务完成后执行
    如果批量处理未运行，返回错误（需要先启动批量处理）

    Args:
        task_id: 要添加的任务ID
        request: 可选的语言配置
    """
    # 检查任务是否存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查批量处理是否在运行
    if not batch_processor.is_running:
        raise HTTPException(
            status_code=409,
            detail="批量处理未运行，请先启动批量处理"
        )

    # 获取语言列表
    languages = None
    if request and request.languages:
        languages = request.languages

    # 添加到队列
    success = batch_processor.add_task_to_queue(task_id, languages)

    if success:
        return {
            "success": True,
            "message": f"任务 {task_id} 已添加到队列",
            "queued_count": batch_processor.queued_task_count,
            "queued_tasks": batch_processor.get_queued_tasks()
        }
    else:
        raise HTTPException(
            status_code=409,
            detail="无法添加任务到队列（任务可能已在队列中或正在处理）"
        )


@router.delete("/queue/{task_id}")
async def remove_task_from_queue(task_id: str):
    """
    从批量处理队列中移除任务

    只能移除尚未开始处理的队列任务

    Args:
        task_id: 要移除的任务ID
    """
    success = batch_processor.remove_task_from_queue(task_id)

    if success:
        return {
            "success": True,
            "message": f"任务 {task_id} 已从队列移除",
            "queued_count": batch_processor.queued_task_count,
            "queued_tasks": batch_processor.get_queued_tasks()
        }
    else:
        raise HTTPException(
            status_code=404,
            detail="任务不在队列中"
        )


@router.get("/queue")
async def get_queue_status():
    """
    获取队列状态

    返回当前队列中等待的任务列表
    """
    return {
        "is_running": batch_processor.is_running,
        "queued_count": batch_processor.queued_task_count,
        "queued_tasks": batch_processor.get_queued_tasks(),
        "current_task_id": batch_processor.progress.current_task_id
    }


# ==================== 内部函数 ====================

def _create_callbacks(db: Session, default_languages: List[str]) -> Dict:
    """创建批量处理所需的回调函数"""

    async def get_task_languages(task_id: str) -> List[str]:
        """获取任务配置的语言列表"""
        return default_languages

    async def check_stage_completed(task_id: str, language: str, stage: str) -> bool:
        """
        检查某个阶段是否已完成

        不仅检查数据库状态，还验证实际输出文件是否存在
        """
        from database import SessionLocal

        db_session = SessionLocal()
        try:
            task = db_session.query(Task).filter(Task.task_id == task_id).first()
            if not task:
                return False

            language_status = task.language_status or {}
            lang_data = language_status.get(language, {})
            stage_data = lang_data.get(stage, {})

            # 首先检查数据库状态
            if stage_data.get("status") != "completed":
                return False

            # 然后验证实际文件是否存在
            if stage == "speaker_diarization":
                # 说话人识别：检查 speaker_data.json 和 source_subtitle.srt 是否存在
                speaker_data_path = task_path_manager.get_speaker_data_path(task_id)
                source_subtitle_path = task_path_manager.get_source_subtitle_path(task_id)

                if not speaker_data_path.exists():
                    print(f"[批量处理] ⚠️ speaker_data.json 不存在，标记为未完成: {task_id}", flush=True)
                    return False

                if not source_subtitle_path.exists():
                    print(f"[批量处理] ⚠️ source_subtitle.srt 不存在，标记为未完成: {task_id}", flush=True)
                    return False

            elif stage == "translation":
                # 翻译：检查 translated.srt 是否存在
                translated_path = task_path_manager.get_translated_subtitle_path(task_id, language)
                if not translated_path.exists():
                    print(f"[批量处理] ⚠️ translated.srt 不存在，标记为未完成: {task_id}/{language}", flush=True)
                    return False

            elif stage == "voice_cloning":
                # 语音克隆：检查 cloned_audio 目录是否存在且有文件
                cloned_audio_dir = task_path_manager.get_cloned_audio_dir(task_id, language)
                if not cloned_audio_dir.exists():
                    print(f"[批量处理] ⚠️ cloned_audio 目录不存在，标记为未完成: {task_id}/{language}", flush=True)
                    return False
                # 检查目录中是否有音频文件
                audio_files = list(cloned_audio_dir.glob("*.wav"))
                if len(audio_files) == 0:
                    print(f"[批量处理] ⚠️ cloned_audio 目录为空，标记为未完成: {task_id}/{language}", flush=True)
                    return False

            elif stage == "stitch":
                # 音频拼接：检查 stitched_audio.wav 是否存在
                stitched_path = task_path_manager.get_stitched_audio_path(task_id, language)
                if not stitched_path.exists():
                    print(f"[批量处理] ⚠️ stitched_audio.wav 不存在，标记为未完成: {task_id}/{language}", flush=True)
                    return False

            elif stage == "export":
                # 视频导出：检查 final_video.mp4 或导出视频是否存在
                final_video_path = task_path_manager.get_final_video_path(task_id, language)
                lang_output_dir = task_path_manager.get_language_output_dir(task_id, language)
                exported_videos = list(lang_output_dir.glob("*_" + language + ".mp4"))

                if not final_video_path.exists() and len(exported_videos) == 0:
                    print(f"[批量处理] ⚠️ 导出视频不存在，标记为未完成: {task_id}/{language}", flush=True)
                    return False

            return True
        finally:
            db_session.close()

    async def run_speaker_diarization(task_id: str, language: str) -> bool:
        """执行说话人识别"""
        from database import SessionLocal
        import httpx

        # 检查是否已取消
        if running_task_tracker.is_cancel_requested() or batch_processor.is_cancel_requested:
            return False

        try:
            # 调用说话人识别 API
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"http://localhost:8000/api/tasks/{task_id}/speaker-diarization",
                    json={}
                )

                if response.status_code != 200:
                    print(f"[批量处理] 说话人识别启动失败: {response.text}", flush=True)
                    return False

            # 轮询等待完成
            return await _wait_for_stage_completion(task_id, "default", "speaker_diarization")

        except Exception as e:
            print(f"[批量处理] 说话人识别失败: {e}", flush=True)
            return False

    async def run_translation(task_id: str, language: str) -> bool:
        """执行翻译"""
        if running_task_tracker.is_cancel_requested() or batch_processor.is_cancel_requested:
            return False

        try:
            import httpx
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"http://localhost:8000/api/tasks/{task_id}/languages/{language}/translate",
                    json={}
                )

                if response.status_code != 200:
                    print(f"[批量处理] 翻译启动失败: {response.text}", flush=True)
                    return False

            return await _wait_for_stage_completion(task_id, language, "translation")

        except Exception as e:
            print(f"[批量处理] 翻译失败: {e}", flush=True)
            return False

    async def run_voice_cloning(task_id: str, language: str) -> bool:
        """执行语音克隆"""
        if running_task_tracker.is_cancel_requested() or batch_processor.is_cancel_requested:
            return False

        try:
            from database import SessionLocal
            db_session = SessionLocal()

            # 获取说话人音色映射
            task = db_session.query(Task).filter(Task.task_id == task_id).first()
            config = task.config or {}
            speaker_voice_mapping = config.get('speaker_voice_mapping', {})
            db_session.close()

            if not speaker_voice_mapping:
                # 使用默认映射（所有说话人使用默认音色）
                speaker_voice_mapping = {}

            import httpx
            async with httpx.AsyncClient(timeout=1800.0) as client:  # 语音克隆可能需要更长时间
                response = await client.post(
                    f"http://localhost:8000/api/tasks/{task_id}/languages/{language}/voice-cloning",
                    json={"speaker_voice_mapping": speaker_voice_mapping}
                )

                if response.status_code != 200:
                    print(f"[批量处理] 语音克隆启动失败: {response.text}", flush=True)
                    return False

            return await _wait_for_stage_completion(task_id, language, "voice_cloning")

        except Exception as e:
            print(f"[批量处理] 语音克隆失败: {e}", flush=True)
            return False

    async def run_stitch(task_id: str, language: str) -> bool:
        """执行音频拼接"""
        if running_task_tracker.is_cancel_requested() or batch_processor.is_cancel_requested:
            return False

        try:
            import httpx
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    f"http://localhost:8000/api/tasks/{task_id}/languages/{language}/stitch-audio",
                    json={}
                )

                if response.status_code != 200:
                    print(f"[批量处理] 音频拼接启动失败: {response.text}", flush=True)
                    return False

            return await _wait_for_stage_completion(task_id, language, "stitch")

        except Exception as e:
            print(f"[批量处理] 音频拼接失败: {e}", flush=True)
            return False

    async def run_export(task_id: str, language: str) -> bool:
        """执行视频导出"""
        if running_task_tracker.is_cancel_requested() or batch_processor.is_cancel_requested:
            return False

        try:
            import httpx
            async with httpx.AsyncClient(timeout=1200.0) as client:
                response = await client.post(
                    f"http://localhost:8000/api/tasks/{task_id}/languages/{language}/export-video",
                    json={}
                )

                if response.status_code != 200:
                    print(f"[批量处理] 视频导出启动失败: {response.text}", flush=True)
                    return False

            return await _wait_for_stage_completion(task_id, language, "export")

        except Exception as e:
            print(f"[批量处理] 视频导出失败: {e}", flush=True)
            return False

    return {
        'get_task_languages': get_task_languages,
        'check_stage_completed': check_stage_completed,
        'run_speaker_diarization': run_speaker_diarization,
        'run_translation': run_translation,
        'run_voice_cloning': run_voice_cloning,
        'run_stitch': run_stitch,
        'run_export': run_export
    }


async def _wait_for_stage_completion(task_id: str, language: str, stage: str, timeout: int = 3600) -> bool:
    """
    等待某个阶段完成

    Args:
        task_id: 任务ID
        language: 语言
        stage: 阶段
        timeout: 超时时间（秒）

    Returns:
        是否成功完成
    """
    import time
    start_time = time.time()

    # 确定状态查询的 API 路径
    # 阶段名称到 API 路径的映射
    stage_to_api_path = {
        "speaker_diarization": "speaker-diarization",
        "translation": "translate",
        "voice_cloning": "voice-cloning",
        "stitch": "stitch-audio",
        "export": "export-video"
    }

    if stage == "speaker_diarization":
        status_url = f"http://localhost:8000/api/tasks/{task_id}/speaker-diarization/status"
    else:
        api_path = stage_to_api_path.get(stage, stage.replace('_', '-'))
        status_url = f"http://localhost:8000/api/tasks/{task_id}/languages/{language}/{api_path}/status"

    import httpx
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            # 检查是否超时
            if time.time() - start_time > timeout:
                print(f"[批量处理] 等待 {stage} 完成超时", flush=True)
                return False

            # 注意：这里不检查取消请求，让当前阶段完成后再停止
            # 取消检查在阶段之间进行

            try:
                response = await client.get(status_url)
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status", "pending")

                    if status == "completed":
                        print(f"[批量处理] {stage} 完成", flush=True)
                        return True
                    elif status == "failed":
                        print(f"[批量处理] {stage} 失败", flush=True)
                        return False
                    # 其他状态继续等待

            except Exception as e:
                print(f"[批量处理] 查询 {stage} 状态失败: {e}", flush=True)

            # 等待一段时间再查询
            await asyncio.sleep(2)


async def _run_batch_all_tasks(task_ids: List[str], callbacks: Dict, db: Session):
    """后台运行多任务批量处理"""
    try:
        await batch_processor.start_batch_for_all_tasks(task_ids, callbacks)
    except Exception as e:
        print(f"[批量处理] 多任务批量处理异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        # 清理状态
        running_task_tracker.clear_cancel_request()


async def _run_batch_single_task(task_id: str, languages: List[str], callbacks: Dict, db: Session):
    """后台运行单任务批量处理"""
    try:
        await batch_processor.start_batch_for_task(task_id, languages, callbacks)
    except Exception as e:
        print(f"[批量处理] 单任务批量处理异常: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        # 清理状态
        running_task_tracker.clear_cancel_request()
