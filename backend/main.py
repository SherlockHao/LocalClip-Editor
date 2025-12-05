from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
import os
import uuid
from pathlib import Path
from typing import Optional
import json
import re

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

# 自定义视频路由，支持 Range 请求
@app.get("/uploads/{filename}")
async def serve_video(filename: str, request: Request):
    """提供支持 HTTP Range 请求的视频流式传输"""
    file_path = UPLOADS_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件未找到")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    # 如果没有 Range 请求头，返回整个文件
    if not range_header:
        return FileResponse(
            file_path,
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            }
        )

    # 解析 Range 请求头
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        raise HTTPException(status_code=416, detail="Invalid range")

    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

    # 确保范围有效
    if start >= file_size or end >= file_size or start > end:
        raise HTTPException(status_code=416, detail="Range not satisfiable")

    chunk_size = end - start + 1

    # 读取文件的指定范围
    def iterfile():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                chunk = f.read(min(8192, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    # 返回 206 Partial Content
    return StreamingResponse(
        iterfile(),
        status_code=206,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
        }
    )

# 挂载静态文件目录（用于其他非视频文件）
# 注意：视频文件会被上面的路由优先处理
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")

# 初始化处理器
video_processor = VideoProcessor()
srt_parser = SRTParser()

# 全局变量用于存储说话人识别处理状态
speaker_processing_status = {}

# 全局变量用于存储语音克隆处理状态
voice_cloning_status = {}

# 全局缓存：存储已提取的音频片段信息，避免重复提取
# key: (video_filename, subtitle_filename), value: {"audio_paths": [...], "speaker_labels": [...], "audio_dir": "..."}
audio_extraction_cache = {}

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
        audio_dir = os.path.join("..", "audio_segments", task_id)
        extractor = AudioExtractor(cache_dir=audio_dir)
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

        # 更新状态：计算音频质量评分
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "正在计算音频质量评分...",
            "progress": 85
        }

        # 按说话人分组音频
        speaker_segments = {}
        for audio_path, speaker_id in zip(audio_paths, speaker_labels):
            if speaker_id is not None:
                if speaker_id not in speaker_segments:
                    speaker_segments[speaker_id] = []
                speaker_segments[speaker_id].append(audio_path)

        # 计算MOS分数
        from mos_scorer import MOSScorer
        mos_scorer = MOSScorer()
        scored_segments = mos_scorer.score_speaker_audios(audio_dir, speaker_segments)

        print(f"已完成MOS评分，共 {len(scored_segments)} 个说话人")

        # 保存到全局缓存，供语音克隆复用
        video_filename = os.path.basename(video_path)
        subtitle_filename = os.path.basename(subtitle_path)
        cache_key = (video_filename, subtitle_filename)
        audio_extraction_cache[cache_key] = {
            "audio_paths": audio_paths,
            "speaker_labels": speaker_labels,
            "audio_dir": audio_dir,
            "task_id": task_id,
            "scored_segments": scored_segments  # 保存MOS评分结果
        }
        print(f"已缓存音频提取结果和MOS评分: {cache_key}")

        # 更新状态为完成
        speaker_processing_status[task_id] = {
            "status": "completed",
            "message": "说话人识别和音频质量评分完成",
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


class VoiceCloningRequest(BaseModel):
    video_filename: str
    source_subtitle_filename: str
    target_language: str
    target_subtitle_filename: str


@app.post("/voice-cloning/process")
async def process_voice_cloning(request: VoiceCloningRequest):
    """启动语音克隆处理流程（当前为空实现）"""
    try:
        video_path = UPLOADS_DIR / request.video_filename
        source_subtitle_path = UPLOADS_DIR / request.source_subtitle_filename
        target_subtitle_path = UPLOADS_DIR / request.target_subtitle_filename

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="视频文件不存在")
        if not source_subtitle_path.exists():
            raise HTTPException(status_code=404, detail="源字幕文件不存在")
        if not target_subtitle_path.exists():
            raise HTTPException(status_code=404, detail="目标字幕文件不存在")

        # 生成唯一的处理任务ID
        task_id = str(uuid.uuid4())

        # 设置处理状态
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在准备语音克隆...",
            "progress": 0
        }

        # 在后台执行处理
        import asyncio
        asyncio.create_task(run_voice_cloning_process(
            task_id,
            str(video_path),
            str(source_subtitle_path),
            request.target_language,
            str(target_subtitle_path)
        ))

        return {
            "task_id": task_id,
            "message": "语音克隆任务已启动",
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_voice_cloning_process(
    task_id: str,
    video_path: str,
    source_subtitle_path: str,
    target_language: str,
    target_subtitle_path: str
):
    """后台执行语音克隆处理"""
    try:
        import asyncio
        from mos_scorer import MOSScorer
        from speaker_audio_processor import SpeakerAudioProcessor
        from subtitle_text_extractor import SubtitleTextExtractor

        # 检查是否可以复用已提取的音频
        video_filename = os.path.basename(video_path)
        subtitle_filename = os.path.basename(source_subtitle_path)
        cache_key = (video_filename, subtitle_filename)

        # 默认值
        scored_segments = None
        has_cached_mos = False

        if cache_key in audio_extraction_cache:
            # 复用已提取的音频和MOS评分
            print(f"复用已缓存的音频提取结果和MOS评分: {cache_key}")
            cached_data = audio_extraction_cache[cache_key]
            audio_paths = cached_data["audio_paths"]
            speaker_labels = cached_data["speaker_labels"]
            audio_dir = cached_data["audio_dir"]
            scored_segments = cached_data.get("scored_segments")  # 获取缓存的MOS评分
            has_cached_mos = scored_segments is not None

            # 更新状态：复用已提取的音频
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在复用已提取的音频、说话人识别和MOS评分结果...",
                "progress": 35
            }
        else:
            # 需要重新提取音频
            print(f"未找到缓存，重新提取音频: {cache_key}")

            # 更新状态：提取音频片段
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在提取音频片段...",
                "progress": 5
            }

            # 1. 提取音频片段
            audio_dir = os.path.join("audio_segments", task_id)
            extractor = AudioExtractor(cache_dir=audio_dir)
            audio_paths = extractor.extract_audio_segments(video_path, source_subtitle_path)

            # 更新状态：提取说话人嵌入
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在提取说话人嵌入...",
                "progress": 15
            }

            # 2. 提取嵌入
            embedding_extractor = SpeakerEmbeddingExtractor(offline_mode=True)
            embeddings = embedding_extractor.extract_embeddings(audio_paths)

            # 更新状态：识别说话人
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在识别说话人...",
                "progress": 25
            }

            # 3. 聚类识别说话人
            clusterer = SpeakerClusterer()
            speaker_labels = clusterer.cluster_embeddings(embeddings)

        # 4. 如果没有缓存的MOS评分，则需要计算
        if not has_cached_mos:
            # 按说话人分组音频
            speaker_segments = {}
            for audio_path, speaker_id in zip(audio_paths, speaker_labels):
                if speaker_id is not None:
                    if speaker_id not in speaker_segments:
                        speaker_segments[speaker_id] = []
                    speaker_segments[speaker_id].append(audio_path)

            # 更新状态：MOS评分
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在对音频片段进行质量评分...",
                "progress": 35
            }

            # 5. MOS打分
            mos_scorer = MOSScorer()
            scored_segments = mos_scorer.score_speaker_audios(audio_dir, speaker_segments)
            print(f"已完成MOS评分")
        else:
            print(f"使用缓存的MOS评分结果")

        # 更新状态：筛选和拼接音频
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在筛选和拼接说话人音频...",
            "progress": 50
        }

        # 6. 筛选、排序、拼接音频
        audio_processor = SpeakerAudioProcessor(target_duration=10.0, silence_duration=1.0)
        # 使用audio_dir对应的references目录
        reference_output_dir = os.path.join(audio_dir, "references")
        speaker_audio_results = audio_processor.process_all_speakers(
            scored_segments, reference_output_dir
        )

        # 更新状态：提取字幕文本
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在提取参考字幕文本...",
            "progress": 65
        }

        # 7. 提取字幕文本
        text_extractor = SubtitleTextExtractor()
        speaker_segments_for_text = {
            speaker_id: selected_segments
            for speaker_id, (_, selected_segments) in speaker_audio_results.items()
        }
        speaker_texts = text_extractor.process_all_speakers(
            speaker_segments_for_text, source_subtitle_path
        )

        # 8. 保存说话人参考数据
        speaker_references = {}
        for speaker_id in speaker_audio_results.keys():
            audio_path, _ = speaker_audio_results[speaker_id]
            reference_text = speaker_texts.get(speaker_id, "")

            speaker_references[speaker_id] = {
                "reference_audio": audio_path,
                "reference_text": reference_text,
                "target_language": target_language
            }

        # 保存到状态中
        voice_cloning_status[task_id]["speaker_references"] = speaker_references

        # 更新状态：准备语音克隆（这里暂时完成准备阶段）
        voice_cloning_status[task_id] = {
            "status": "completed",
            "message": "已完成说话人参考数据准备，待实现语音克隆算法",
            "progress": 100,
            "speaker_references": speaker_references,
            "unique_speakers": len(speaker_references)
        }

        print(f"\n语音克隆准备完成！")
        print(f"识别到 {len(speaker_references)} 个说话人")
        for speaker_id, ref_data in speaker_references.items():
            print(f"\n说话人 {speaker_id}:")
            print(f"  参考音频: {ref_data['reference_audio']}")
            print(f"  参考文本: {ref_data['reference_text'][:100]}...")

    except Exception as e:
        # 更新状态为失败
        import traceback
        error_detail = traceback.format_exc()
        print(f"语音克隆处理失败: {error_detail}")
        voice_cloning_status[task_id] = {
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "progress": 0
        }


@app.get("/voice-cloning/status/{task_id}")
async def get_voice_cloning_status(task_id: str):
    """获取语音克隆处理状态"""
    if task_id not in voice_cloning_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return voice_cloning_status[task_id]


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