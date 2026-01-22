# -*- coding: utf-8 -*-
"""
进度管理器 - 统一管理任务进度更新和 WebSocket 推送
"""

from database import SessionLocal
from models.task import Task
from routers.websocket import manager
from sqlalchemy.orm.attributes import flag_modified
import json
from datetime import datetime
from running_task_tracker import running_task_tracker


async def update_task_progress(
    task_id: str,
    language: str,
    stage: str,
    progress: int,
    message: str,
    status: str = "processing",
    extra_data: dict = None
):
    """
    更新任务进度并推送 WebSocket

    Args:
        task_id: 任务 ID
        language: 语言 (English, Korean, Japanese, etc.)
        stage: 处理阶段 (speaker_diarization, translation, voice_cloning, export)
        progress: 进度百分比 (0-100)
        message: 进度描述信息
        status: 状态 (processing, completed, failed)
        extra_data: 额外数据 (如 elapsed_time, total_items 等)
    """
    db = SessionLocal()
    try:
        print(f"[进度更新] {task_id} - {language} - {stage}: {progress}% - {message}", flush=True)

        # 0. 更新运行任务追踪器的进度
        running_task_tracker.update_progress(task_id, progress, message)

        # 1. 更新数据库
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            # 初始化 language_status
            language_status = task.language_status or {}
            if language not in language_status:
                language_status[language] = {}

            # 更新指定阶段的状态
            stage_data = {
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow().isoformat()
            }

            # 添加额外数据
            if extra_data:
                stage_data.update(extra_data)

            language_status[language][stage] = stage_data

            task.language_status = language_status
            flag_modified(task, "language_status")  # 标记 JSON 字段已修改
            task.updated_at = datetime.utcnow()

            # 如果所有阶段都完成，更新任务总状态
            if language in language_status:
                all_stages = ['speaker_diarization', 'translation', 'voice_cloning', 'export']
                lang_data = language_status[language]

                # 检查是否有失败
                has_failed = any(
                    lang_data.get(s, {}).get('status') == 'failed'
                    for s in all_stages
                )

                # 检查是否全部完成
                all_completed = all(
                    lang_data.get(s, {}).get('status') == 'completed'
                    for s in all_stages
                )

                if has_failed:
                    task.status = "failed"
                elif all_completed:
                    task.status = "completed"
                else:
                    task.status = "processing"

            db.commit()
            print(f"[进度更新] 数据库更新成功", flush=True)
        else:
            print(f"[进度更新] ⚠️ 任务不存在: {task_id}", flush=True)

        # 2. 推送 WebSocket（即使数据库更新失败也尝试推送）
        try:
            await manager.broadcast_to_task(task_id, {
                "type": "progress_update",
                "task_id": task_id,
                "language": language,
                "stage": stage,
                "progress": progress,
                "message": message,
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"[进度更新] WebSocket 推送成功", flush=True)
        except Exception as ws_error:
            print(f"[进度更新] ⚠️ WebSocket 推送失败: {str(ws_error)}", flush=True)
            # WebSocket 失败不影响主流程

    except Exception as e:
        print(f"[进度更新] ❌ 更新失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def update_task_progress_sync(
    task_id: str,
    language: str,
    stage: str,
    progress: int,
    message: str,
    status: str = "processing"
):
    """
    同步版本的进度更新（用于非异步上下文）

    注意: 此函数只更新数据库，不推送 WebSocket
    """
    db = SessionLocal()
    try:
        print(f"[进度更新-同步] {task_id} - {language} - {stage}: {progress}% - {message}", flush=True)

        task = db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            language_status = task.language_status or {}
            if language not in language_status:
                language_status[language] = {}

            language_status[language][stage] = {
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": datetime.utcnow().isoformat()
            }

            task.language_status = language_status
            flag_modified(task, "language_status")  # 标记 JSON 字段已修改
            task.updated_at = datetime.utcnow()
            db.commit()
            print(f"[进度更新-同步] 数据库更新成功", flush=True)
        else:
            print(f"[进度更新-同步] ⚠️ 任务不存在: {task_id}", flush=True)

    except Exception as e:
        print(f"[进度更新-同步] ❌ 更新失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def mark_task_failed(task_id: str, language: str, stage: str, error_message: str):
    """
    标记任务失败

    Args:
        task_id: 任务 ID
        language: 语言
        stage: 失败的阶段
        error_message: 错误信息
    """
    await update_task_progress(
        task_id=task_id,
        language=language,
        stage=stage,
        progress=0,
        message=f"失败: {error_message}",
        status="failed"
    )

    # 同时更新任务的 error_message
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            task.error_message = f"{language}/{stage}: {error_message}"
            task.status = "failed"
            db.commit()
    except Exception as e:
        print(f"[标记失败] ❌ 更新失败: {str(e)}", flush=True)
    finally:
        db.close()


async def mark_task_completed(task_id: str, language: str, stage: str, extra_data: dict = None):
    """
    标记任务阶段完成

    Args:
        task_id: 任务 ID
        language: 语言
        stage: 完成的阶段
        extra_data: 额外数据 (如 elapsed_time, total_items 等)
    """
    print(f"[mark_task_completed] 开始标记完成: {task_id} - {language} - {stage}", flush=True)
    await update_task_progress(
        task_id=task_id,
        language=language,
        stage=stage,
        progress=100,
        message="完成",
        status="completed",
        extra_data=extra_data
    )
    print(f"[mark_task_completed] ✅ 已标记完成: {task_id} - {language} - {stage}", flush=True)
