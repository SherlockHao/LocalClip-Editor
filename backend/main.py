from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import uuid
from pathlib import Path
from typing import Optional
import json

from video_processor import VideoProcessor
from srt_parser import SRTParser

# 添加对说话人识别功能的支持
import sys
import os
# 添加项目根目录到路径，以便导入speaker_diarization_processing模块
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'speaker_diarization_processing'))
from audio_extraction import AudioExtractor
from embedding_extraction import SpeakerEmbeddingExtractor
from cluster_processor import SpeakerClusterer

app = FastAPI(title="LocalClip Editor API", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应限制为具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保上传和导出目录存在
UPLOADS_DIR = Path("uploads")
EXPORTS_DIR = Path("exports")

UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# 挂载静态文件目录
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")

# 初始化处理器
video_processor = VideoProcessor()
srt_parser = SRTParser()

# 全局变量用于存储说话人识别处理状态
speaker_processing_status = {}

@app.get("/")
async def root():
    return {"message": "LocalClip Editor API"}

@app.post("/upload/video")
async def upload_video(file: UploadFile = File(...)):
    try:
        # 检查文件类型
        allowed_types = [".mp4", ".mov", ".avi", ".mkv"]
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in allowed_types:
            raise HTTPException(status_code=400, detail="不支持的视频格式")
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = UPLOADS_DIR / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 获取视频信息
        video_info = video_processor.get_video_info(str(file_path))
        
        return {
            "filename": unique_filename,
            "original_name": file.filename,
            "size": os.path.getsize(file_path),
            "video_info": video_info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/subtitle")
async def upload_subtitle(file: UploadFile = File(...)):
    try:
        # 检查文件类型
        if not file.filename.lower().endswith('.srt'):
            raise HTTPException(status_code=400, detail="仅支持SRT字幕文件")
        
        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4()}.srt"
        file_path = UPLOADS_DIR / unique_filename
        
        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 解析SRT文件
        subtitles = srt_parser.parse_srt(str(file_path))
        
        return {
            "filename": unique_filename,
            "original_name": file.filename,
            "size": os.path.getsize(file_path),
            "subtitles": subtitles
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/videos")
async def get_videos():
    video_extensions = {".mp4", ".mov", ".avi", ".mkv"}
    videos = []
    
    for file_path in UPLOADS_DIR.iterdir():
        if file_path.suffix.lower() in video_extensions:
            video_info = video_processor.get_video_info(str(file_path))
            videos.append({
                "filename": file_path.name,
                "size": os.path.getsize(file_path),
                "video_info": video_info
            })
    
    # 按修改时间排序
    videos.sort(key=lambda x: UPLOADS_DIR.joinpath(x["filename"]).stat().st_mtime, reverse=True)
    
    return {"videos": videos}

from pydantic import BaseModel

class SpeakerDiarizationRequest(BaseModel):
    video_filename: str
    subtitle_filename: str

@app.post("/speaker-diarization/process")
async def process_speaker_diarization(request: SpeakerDiarizationRequest):
    """启动说话人识别和聚类处理流程"""
    try:
        video_path = UPLOADS_DIR / request.video_filename
        subtitle_path = UPLOADS_DIR / request.subtitle_filename
        
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="视频文件不存在")
        if not subtitle_path.exists():
            raise HTTPException(status_code=404, detail="字幕文件不存在")
        
        # 生成唯一的处理任务ID
        task_id = str(uuid.uuid4())
        
        # 设置处理状态
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "正在提取音频片段...",
            "progress": 0
        }
        
        # 在后台执行处理
        import asyncio
        asyncio.create_task(run_speaker_diarization_process(task_id, str(video_path), str(subtitle_path)))
        
        return {
            "task_id": task_id,
            "message": "说话人识别任务已启动",
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_speaker_diarization_process(task_id: str, video_path: str, subtitle_path: str):
    """后台执行说话人识别和聚类处理"""
    try:
        # 更新状态
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "正在提取音频片段...",
            "progress": 10
        }
        
        # 提取音频片段
        extractor = AudioExtractor(cache_dir=os.path.join("..", "audio_segments", task_id))
        audio_paths = extractor.extract_audio_segments(video_path, subtitle_path)
        
        # 更新状态
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "正在提取说话人嵌入...",
            "progress": 40
        }
        
        # 提取嵌入
        embedding_extractor = SpeakerEmbeddingExtractor(offline_mode=True)
        embeddings = embedding_extractor.extract_embeddings(audio_paths)
        
        # 更新状态
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "正在聚类识别说话人...",
            "progress": 70
        }
        
        # 聚类识别说话人
        clusterer = SpeakerClusterer()
        speaker_labels = clusterer.cluster_embeddings(embeddings)
        
        # 更新状态为完成
        speaker_processing_status[task_id] = {
            "status": "completed",
            "message": "说话人识别完成",
            "progress": 100,
            "speaker_labels": speaker_labels,
            "unique_speakers": clusterer.get_unique_speakers_count(speaker_labels)
        }
        
    except Exception as e:
        # 更新状态为失败
        speaker_processing_status[task_id] = {
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "progress": 0
        }


@app.get("/speaker-diarization/status/{task_id}")
async def get_speaker_diarization_status(task_id: str):
    """获取说话人识别处理状态"""
    if task_id not in speaker_processing_status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return speaker_processing_status[task_id]


@app.post("/export")
async def export_video(
    video_filename: str,
    subtitle_filename: Optional[str] = None,
    export_hard_subtitles: bool = False
):
    try:
        video_path = UPLOADS_DIR / video_filename
        
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
        # 生成导出文件名
        export_filename = f"export_{uuid.uuid4()}.mp4"
        export_path = EXPORTS_DIR / export_filename
        
        # 执行导出
        result = video_processor.export_video(
            str(video_path),
            str(export_path),
            subtitle_filename,
            export_hard_subtitles
        )
        
        return {
            "export_filename": export_filename,
            "success": True,
            "message": "视频导出成功",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)