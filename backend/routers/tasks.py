from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import shutil
import os

from database import get_db
from models.task import Task as TaskModel
from file_manager import file_manager
from task_queue import task_queue
from path_utils import task_path_manager
from video_processor import VideoProcessor

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Pydantic 模型
class TaskCreate(BaseModel):
    target_languages: List[str] = []

class TaskResponse(BaseModel):
    id: int
    task_id: str
    video_filename: str
    video_original_name: str
    status: str
    language_status: dict
    config: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LanguageProcessRequest(BaseModel):
    stage: str  # speaker_diarization, translation, voice_cloning, export

@router.post("/", response_model=TaskResponse)
async def create_task(
    video: UploadFile = File(...),
    subtitle: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """创建新任务并上传视频和字幕（必须，支持 SRT 和 ASS 格式）"""
    try:
        print(f"[任务API] 收到上传请求, 文件名: {video.filename}, 类型: {video.content_type}", flush=True)
        print(f"[任务API] 包含字幕文件: {subtitle.filename}", flush=True)

        # 验证字幕文件格式 - 支持 SRT 和 ASS/SSA 格式
        subtitle_filename_lower = subtitle.filename.lower()
        is_ass_format = subtitle_filename_lower.endswith('.ass') or subtitle_filename_lower.endswith('.ssa')
        is_srt_format = subtitle_filename_lower.endswith('.srt')

        if not (is_srt_format or is_ass_format):
            raise HTTPException(status_code=400, detail="仅支持 SRT 和 ASS 字幕文件")

        # 生成任务ID
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        print(f"[任务API] 生成任务ID: {task_id}", flush=True)

        # 创建目录结构
        structure = file_manager.create_task_structure(task_id)
        print(f"[任务API] 创建目录结构: {structure['root']}", flush=True)

        # 保存视频文件
        video_filename = f"{task_id}_{video.filename}"
        video_path = structure["input"] / video_filename
        print(f"[任务API] 保存视频到: {video_path}", flush=True)

        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)

        file_size = os.path.getsize(video_path)
        print(f"[任务API] 视频保存成功, 大小: {file_size} bytes", flush=True)

        # 验证视频编码格式
        video_processor = VideoProcessor()
        codec_validation = video_processor.validate_video_codec(str(video_path))

        if not codec_validation.get("valid"):
            # 删除已上传的文件
            file_manager.delete_task(task_id)
            error_msg = codec_validation.get("error", "视频编码格式不支持")
            print(f"[任务API] ❌ 视频编码验证失败: {error_msg}", flush=True)
            raise HTTPException(status_code=400, detail=error_msg)

        print(f"[任务API] ✅ 视频编码验证通过: {codec_validation.get('video_codec')}", flush=True)

        # 初始化配置
        config = {"target_languages": []}

        # 保存字幕文件
        subtitle_path = task_path_manager.get_source_subtitle_path(task_id)
        subtitle_path.parent.mkdir(exist_ok=True, parents=True)

        if is_ass_format:
            # ASS 格式：先保存为临时文件，然后解析转换为 SRT
            import tempfile
            from srt_parser import SRTParser
            srt_parser = SRTParser()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.ass') as temp_file:
                shutil.copyfileobj(subtitle.file, temp_file)
                temp_path = temp_file.name

            print(f"[任务API] ASS 文件已保存到临时位置: {temp_path}", flush=True)

            # 解析 ASS 文件
            subtitles = srt_parser.parse_ass(temp_path)

            if not subtitles:
                os.unlink(temp_path)
                # 清理已创建的目录
                file_manager.delete_task(task_id)
                raise HTTPException(status_code=400, detail="ASS 字幕文件解析失败")

            # 转换并保存为 SRT 格式
            srt_parser.save_srt(subtitles, str(subtitle_path))

            # 清理临时文件
            os.unlink(temp_path)
            print(f"[任务API] ASS 已转换为 SRT: {subtitle_path}", flush=True)
        else:
            # SRT 格式：直接保存
            print(f"[任务API] 保存字幕到: {subtitle_path}", flush=True)
            with open(subtitle_path, "wb") as buffer:
                shutil.copyfileobj(subtitle.file, buffer)

        subtitle_size = os.path.getsize(subtitle_path)
        print(f"[任务API] 字幕保存成功, 大小: {subtitle_size} bytes", flush=True)

        config['source_subtitle_filename'] = 'source_subtitle.srt'

        # 创建数据库记录
        db_task = TaskModel(
            task_id=task_id,
            video_filename=video_filename,
            video_original_name=video.filename,
            status="pending",
            language_status={},
            config=config
        )

        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        print(f"[任务API] 数据库记录创建成功: {task_id}", flush=True)

        return db_task

    except HTTPException:
        raise
    except Exception as e:
        print(f"[任务API] ❌ 创建任务失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取任务列表（按创建时间升序，最早的在前）"""
    tasks = db.query(TaskModel).order_by(TaskModel.created_at.asc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 删除文件
    file_manager.delete_task(task_id)

    # 删除数据库记录
    db.delete(task)
    db.commit()

    print(f"[任务] 删除任务: {task_id}")

    return {"message": "Task deleted successfully"}

@router.get("/{task_id}/video-info")
async def get_video_info(task_id: str, db: Session = Depends(get_db)):
    """获取任务的视频信息"""
    try:
        task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取视频文件路径
        paths = task_path_manager.get_task_paths(task_id)
        video_path = paths["input"] / task.video_filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="视频文件不存在")

        # 获取视频信息 (可以使用 ffprobe 获取详细信息，这里先返回基本信息)
        import subprocess
        import json

        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(video_path)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                probe_data = json.loads(result.stdout)
                format_info = probe_data.get('format', {})
                video_stream = next((s for s in probe_data.get('streams', []) if s.get('codec_type') == 'video'), {})

                return {
                    "size": int(format_info.get('size', 0)),
                    "duration": float(format_info.get('duration', 0)),
                    "duration_formatted": format_info.get('duration', '0'),
                    "width": video_stream.get('width', 0),
                    "height": video_stream.get('height', 0),
                    "resolution": f"{video_stream.get('width', 0)}x{video_stream.get('height', 0)}",
                    "bitrate": format_info.get('bit_rate', '0'),
                    "codec": video_stream.get('codec_name', 'unknown')
                }
        except Exception as e:
            print(f"[视频信息] FFprobe 失败: {str(e)}", flush=True)

        # 如果 ffprobe 失败，返回基本信息
        file_size = os.path.getsize(video_path)
        return {
            "size": file_size,
            "duration": 0,
            "duration_formatted": "0",
            "width": 0,
            "height": 0,
            "resolution": "unknown",
            "bitrate": "0",
            "codec": "unknown"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[视频信息] 获取失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取视频信息失败: {str(e)}")

@router.get("/{task_id}/subtitle")
async def get_subtitle(task_id: str, db: Session = Depends(get_db)):
    """获取任务的字幕数据"""
    try:
        task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        subtitle_path = task_path_manager.get_source_subtitle_path(task_id)

        if not subtitle_path.exists():
            return {"subtitles": [], "filename": None}

        # 解析 SRT 文件
        import pysrt
        subs = pysrt.open(str(subtitle_path), encoding='utf-8')

        subtitles = []
        for sub in subs:
            subtitles.append({
                "start_time": sub.start.ordinal / 1000.0,
                "end_time": sub.end.ordinal / 1000.0,
                "start_time_formatted": str(sub.start),
                "end_time_formatted": str(sub.end),
                "text": sub.text
            })

        return {
            "subtitles": subtitles,
            "filename": task.config.get('source_subtitle_filename') if task.config else None
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[字幕获取] 获取失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取字幕失败: {str(e)}")

@router.post("/{task_id}/subtitle")
async def upload_subtitle(
    task_id: str,
    subtitle: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传字幕文件到任务 (支持 SRT 和 ASS 格式)"""
    try:
        print(f"[字幕上传] 收到请求: {task_id}, 文件名: {subtitle.filename}", flush=True)

        # 验证任务存在
        task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 验证文件类型 - 支持 SRT 和 ASS/SSA 格式
        filename_lower = subtitle.filename.lower()
        is_ass_format = filename_lower.endswith('.ass') or filename_lower.endswith('.ssa')
        is_srt_format = filename_lower.endswith('.srt')

        if not (is_srt_format or is_ass_format):
            raise HTTPException(status_code=400, detail="仅支持 SRT 和 ASS 字幕文件")

        # 保存字幕到 processed 目录
        subtitle_path = task_path_manager.get_source_subtitle_path(task_id)
        subtitle_path.parent.mkdir(exist_ok=True, parents=True)

        if is_ass_format:
            # ASS 格式：先保存为临时文件，然后解析转换为 SRT
            import tempfile
            from srt_parser import SRTParser
            srt_parser = SRTParser()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.ass') as temp_file:
                shutil.copyfileobj(subtitle.file, temp_file)
                temp_path = temp_file.name

            print(f"[字幕上传] ASS 文件已保存到临时位置: {temp_path}", flush=True)

            # 解析 ASS 文件
            subtitles = srt_parser.parse_ass(temp_path)

            if not subtitles:
                os.unlink(temp_path)
                raise HTTPException(status_code=400, detail="ASS 字幕文件解析失败")

            # 转换并保存为 SRT 格式
            srt_parser.save_srt(subtitles, str(subtitle_path))

            # 清理临时文件
            os.unlink(temp_path)
            print(f"[字幕上传] ASS 已转换为 SRT: {subtitle_path}", flush=True)
        else:
            # SRT 格式：直接保存
            print(f"[字幕上传] 保存字幕到: {subtitle_path}", flush=True)
            with open(subtitle_path, "wb") as buffer:
                shutil.copyfileobj(subtitle.file, buffer)

        file_size = os.path.getsize(subtitle_path)
        print(f"[字幕上传] 字幕保存成功, 大小: {file_size} bytes", flush=True)

        # 更新任务配置
        config = task.config or {}
        config['source_subtitle_filename'] = 'source_subtitle.srt'
        task.config = config
        db.commit()

        return {
            "message": "字幕上传成功",
            "task_id": task_id,
            "subtitle_path": str(subtitle_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[字幕上传] ❌ 上传失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"字幕上传失败: {str(e)}")
