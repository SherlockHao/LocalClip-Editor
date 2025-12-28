# -*- coding: utf-8 -*-
# 设置环境变量禁用torch dynamo（在导入任何库之前）
import os
os.environ["TORCH_DYNAMO_DISABLE"] = "1"

# 加载 .env 配置文件
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
project_root = Path(__file__).parent.parent
dotenv_path = project_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    print(f"[OK] 已加载环境配置: {dotenv_path}")
else:
    print(f"[WARNING] 未找到 .env 文件: {dotenv_path}")

from fastapi import FastAPI, File, UploadFile, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
import uuid
from pathlib import Path
from typing import Optional, List, Dict
import json
import re
import time

from video_processor import VideoProcessor
from srt_parser import SRTParser

# 语言代码到中文名称的映射
def get_language_name(language_code: str) -> str:
    """
    将语言代码转换为中文名称（用于LLM prompt）

    Args:
        language_code: 语言代码 (en, ko, ja 等)

    Returns:
        str: 语言的中文名称
    """
    language_map = {
        'en': '英语',
        'ko': '韩语',
        'ja': '日语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语'
    }
    return language_map.get(language_code.lower(), language_code)

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

# 自定义音频路由，支持 Range 请求（用于拼接音频）
@app.get("/exports/stitched_{task_id}.wav")
async def serve_stitched_audio(task_id: str, request: Request):
    """提供支持 HTTP Range 请求的拼接音频流式传输"""
    file_path = EXPORTS_DIR / f"stitched_{task_id}.wav"

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音频文件未找到")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    # 如果没有 Range 请求头，返回整个文件
    if not range_header:
        return FileResponse(
            file_path,
            media_type="audio/wav",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
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
        media_type="audio/wav",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# 挂载静态文件目录（用于其他非视频文件）
# 注意：视频和拼接音频文件会被上面的路由优先处理
app.mount("/exports", StaticFiles(directory=EXPORTS_DIR), name="exports")

# 初始化处理器
video_processor = VideoProcessor()
srt_parser = SRTParser()

# 全局变量用于存储说话人识别处理状态
speaker_processing_status = {}

# 全局变量用于存储语音克隆处理状态
voice_cloning_status = {}

# 全局变量用于存储翻译处理状态
translation_status = {}

# 全局缓存：存储已提取的音频片段信息，避免重复提取
# key: (video_filename, subtitle_filename), value: {"audio_paths": [...], "speaker_labels": [...], "audio_dir": "..."}
audio_extraction_cache = {}

# 默认音色库配置
DEFAULT_VOICES_DIR = Path(__file__).parent / "default_seed"
DEFAULT_VOICES = [
    {
        "id": "voice_1",
        "name": "沉稳绅士",
        "npy_file": "沉稳绅士_codes.npy",
        "audio_file": "沉稳绅士.wav",
        "reference_text": "今天早晨市中心的主要道路因突发事故造成了严重堵塞，请驾驶员朋友们注意绕行并听从现场交警的指挥。"
    },
    {
        "id": "voice_2",
        "name": "清爽少年",
        "npy_file": "清爽少年_codes.npy",
        "audio_file": "清爽少年.wav",
        "reference_text": "今天早晨市中心的主要道路因突发事故造成了严重堵塞，请驾驶员朋友们注意绕行并听从现场交警的指挥。"
    },
    {
        "id": "voice_3",
        "name": "甜美女声",
        "npy_file": "甜美女声_codes.npy",
        "audio_file": "甜美女声.wav",
        "reference_text": "今天早晨市中心的主要道路因突发事故造成了严重堵塞，请驾驶员朋友们注意绕行并听从现场交警的指挥。"
    },
    {
        "id": "voice_4",
        "name": "知性御姐",
        "npy_file": "知性御姐_codes.npy",
        "audio_file": "知性御姐.wav",
        "reference_text": "今天早晨市中心的主要道路因突发事故造成了严重堵塞，请驾驶员朋友们注意绕行并听从现场交警的指挥。"
    }
]

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
        print(f"\n===== 收到说话人识别请求 =====")
        print(f"视频文件名: {request.video_filename}")
        print(f"字幕文件名: {request.subtitle_filename}")

        video_path = UPLOADS_DIR / request.video_filename
        subtitle_path = UPLOADS_DIR / request.subtitle_filename

        print(f"检查文件是否存在...")
        print(f"视频路径: {video_path}, 存在: {video_path.exists()}")
        print(f"字幕路径: {subtitle_path}, 存在: {subtitle_path.exists()}")

        if not video_path.exists():
            raise HTTPException(status_code=404, detail="视频文件不存在")
        if not subtitle_path.exists():
            raise HTTPException(status_code=404, detail="字幕文件不存在")

        # 生成唯一的处理任务ID
        task_id = str(uuid.uuid4())
        print(f"生成任务ID: {task_id}")

        # 设置初始处理状态
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "任务启动中...",
            "progress": 0
        }
        print(f"设置初始状态: {speaker_processing_status[task_id]}")

        # 在后台执行处理
        import asyncio
        print(f"创建后台任务...")
        task = asyncio.create_task(run_speaker_diarization_process(task_id, str(video_path), str(subtitle_path)))

        # 添加异常处理回调
        def handle_task_exception(t):
            try:
                t.result()
            except Exception as e:
                import traceback
                print(f"❌ 后台任务异常: {traceback.format_exc()}")

        task.add_done_callback(handle_task_exception)
        print(f"后台任务已创建")

        return {
            "task_id": task_id,
            "message": "说话人识别任务已启动",
            "status": "processing"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def run_speaker_diarization_process(task_id: str, video_path: str, subtitle_path: str):
    """后台执行说话人识别和聚类处理"""
    import time
    start_time = time.time()

    try:
        import asyncio

        print(f"\n========== 开始执行说话人识别任务: {task_id} ==========")
        print(f"视频路径: {video_path}")
        print(f"字幕路径: {subtitle_path}")

        # 等待2秒，确保前端开始轮询
        await asyncio.sleep(2)

        # 任务1：音频切分 (0-25%)
        print(f"[任务1] 更新状态: 音频切分中... (5%)")
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "音频切分中...",
            "progress": 5
        }
        await asyncio.sleep(1.5)  # 延迟1.5秒，让前端看到这个状态

        # 提取音频片段
        audio_dir = os.path.join("..", "audio_segments", task_id)
        extractor = AudioExtractor(cache_dir=audio_dir)
        audio_paths = extractor.extract_audio_segments(video_path, subtitle_path)

        # 任务2：说话人识别 (25-60%)
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "说话人特征提取中...",
            "progress": 30
        }
        await asyncio.sleep(1.5)  # 延迟1.5秒

        # 提取嵌入
        embedding_extractor = SpeakerEmbeddingExtractor(offline_mode=True)
        embeddings = embedding_extractor.extract_embeddings(audio_paths)

        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "说话人聚类分析中...",
            "progress": 55
        }
        await asyncio.sleep(1.5)  # 延迟1.5秒

        # 聚类识别说话人
        clusterer = SpeakerClusterer()
        speaker_labels = clusterer.cluster_embeddings(embeddings)

        # 任务3：MOS音频质量评分 (60-80%)
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "音频质量评估中...",
            "progress": 65
        }
        await asyncio.sleep(1.5)  # 延迟1.5秒

        # 按说话人分组音频
        speaker_segments = {}
        for audio_path, speaker_id in zip(audio_paths, speaker_labels):
            if speaker_id is not None:
                if speaker_id not in speaker_segments:
                    speaker_segments[speaker_id] = []
                speaker_segments[speaker_id].append(audio_path)

        # 计算MOS分数（使用 NISQA）
        from nisqa_scorer import NISQAScorer
        mos_scorer = NISQAScorer()
        scored_segments = mos_scorer.score_speaker_audios(audio_dir, speaker_segments)

        print(f"已完成MOS评分（NISQA），共 {len(scored_segments)} 个说话人")

        # 任务4：性别识别 (80-100%)
        speaker_processing_status[task_id] = {
            "status": "processing",
            "message": "性别识别分析中...",
            "progress": 85
        }
        await asyncio.sleep(1.5)  # 延迟1.5秒

        # 性别识别
        from gender_classifier import GenderClassifier, rename_speakers_by_gender
        gender_classifier = GenderClassifier()
        gender_dict = gender_classifier.classify_speakers(scored_segments, min_duration=2.0)

        # 根据性别和出现次数重新命名说话人
        print(f"\n根据性别和出现次数重新命名说话人...")
        speaker_name_mapping, gender_stats = rename_speakers_by_gender(speaker_labels, gender_dict)

        print(f"\n性别统计: 男性 {gender_stats['male']} 人, 女性 {gender_stats['female']} 人")

        # 保存到全局缓存，供语音克隆复用
        video_filename = os.path.basename(video_path)
        subtitle_filename = os.path.basename(subtitle_path)
        cache_key = (video_filename, subtitle_filename)
        audio_extraction_cache[cache_key] = {
            "audio_paths": audio_paths,
            "speaker_labels": speaker_labels,
            "audio_dir": audio_dir,
            "task_id": task_id,
            "scored_segments": scored_segments,  # 保存MOS评分结果
            "gender_dict": gender_dict,  # 保存性别识别结果
            "speaker_name_mapping": speaker_name_mapping,  # 保存说话人名称映射
            "gender_stats": gender_stats  # 保存性别统计
        }
        print(f"已缓存音频提取结果、MOS评分和性别识别: {cache_key}")

        # 计算总耗时
        end_time = time.time()
        total_duration = end_time - start_time

        # 格式化时间显示
        def format_duration(seconds):
            """将秒数格式化为易读的时间字符串"""
            if seconds < 60:
                return f"{seconds:.1f}秒"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}分{secs}秒"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}小时{minutes}分钟"

        duration_str = format_duration(total_duration)

        # 更新状态为完成
        speaker_processing_status[task_id] = {
            "status": "completed",
            "message": f"全部任务已完成 (耗时: {duration_str})",
            "progress": 100,
            "speaker_labels": speaker_labels,
            "unique_speakers": clusterer.get_unique_speakers_count(speaker_labels),
            "speaker_name_mapping": speaker_name_mapping,
            "gender_stats": gender_stats,
            "total_duration": total_duration,
            "duration_str": duration_str
        }

        print(f"\n✅ 说话人识别任务 {task_id} 成功完成！")
        print(f"⏱️  总耗时: {duration_str}")

    except Exception as e:
        # 计算失败时的耗时
        end_time = time.time()
        total_duration = end_time - start_time
        duration_str = f"{total_duration:.1f}秒"

        # 更新状态为失败
        import traceback
        error_detail = traceback.format_exc()
        print(f"\n========== 说话人识别任务失败: {task_id} ==========")
        print(f"错误信息: {str(e)}")
        print(f"详细堆栈:\n{error_detail}")
        print(f"⏱️  失败前耗时: {duration_str}")

        speaker_processing_status[task_id] = {
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "progress": 0,
            "total_duration": total_duration,
            "duration_str": duration_str
        }


@app.get("/speaker-diarization/status/{task_id}")
async def get_speaker_diarization_status(task_id: str):
    """获取说话人识别处理状态"""
    print(f"[状态查询] task_id: {task_id}")
    if task_id not in speaker_processing_status:
        print(f"[状态查询] 任务不存在")
        raise HTTPException(status_code=404, detail="任务不存在")

    status = speaker_processing_status[task_id]
    print(f"[状态查询] 返回状态: {status}")
    return status


class VoiceCloningRequest(BaseModel):
    video_filename: str
    source_subtitle_filename: str
    target_language: str
    target_subtitle_filename: str
    speaker_voice_mapping: Optional[Dict[str, str]] = None  # {speaker_id: voice_id}, voice_id可以是"default"或默认音色的id


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
        task = asyncio.create_task(run_voice_cloning_process(
            task_id,
            str(video_path),
            str(source_subtitle_path),
            request.target_language,
            str(target_subtitle_path),
            request.speaker_voice_mapping
        ))

        # 添加异常处理回调
        def handle_task_exception(t):
            try:
                t.result()
            except Exception as e:
                import traceback
                print(f"❌ 后台任务异常: {traceback.format_exc()}")

        task.add_done_callback(handle_task_exception)

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
    target_subtitle_path: str,
    speaker_voice_mapping: Optional[Dict[str, str]] = None
):
    """后台执行语音克隆处理"""
    import time
    start_time = time.time()  # 记录开始时间

    # 设置默认值
    if speaker_voice_mapping is None:
        speaker_voice_mapping = {}

    try:
        import asyncio
        from nisqa_scorer import NISQAScorer
        from speaker_audio_processor import SpeakerAudioProcessor
        from subtitle_text_extractor import SubtitleTextExtractor

        # 检查是否可以复用已提取的音频
        video_filename = os.path.basename(video_path)
        subtitle_filename = os.path.basename(source_subtitle_path)
        cache_key = (video_filename, subtitle_filename)

        # 默认值
        scored_segments = None
        has_cached_mos = False
        gender_dict = {}
        speaker_name_mapping = {}

        if cache_key in audio_extraction_cache:
            # 复用已提取的音频、MOS评分和性别识别
            print(f"复用已缓存的音频提取结果、MOS评分和性别识别: {cache_key}")
            cached_data = audio_extraction_cache[cache_key]
            audio_paths = cached_data["audio_paths"]
            speaker_labels = cached_data["speaker_labels"]
            audio_dir = cached_data["audio_dir"]
            scored_segments = cached_data.get("scored_segments")  # 获取缓存的MOS评分
            gender_dict = cached_data.get("gender_dict", {})  # 获取性别识别结果
            speaker_name_mapping = cached_data.get("speaker_name_mapping", {})  # 获取说话人名称映射
            has_cached_mos = scored_segments is not None

            # 更新状态：复用已提取的音频
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在复用已提取的音频、说话人识别、MOS评分和性别识别结果...",
                "progress": 3
            }
        else:
            # 需要重新提取音频
            print(f"未找到缓存，重新提取音频: {cache_key}")

            # 更新状态：提取音频片段
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在提取音频片段...",
                "progress": 2
            }

            # 1. 提取音频片段
            audio_dir = os.path.join("..", "audio_segments", task_id)
            extractor = AudioExtractor(cache_dir=audio_dir)
            audio_paths = extractor.extract_audio_segments(video_path, source_subtitle_path)

            # 更新状态：提取说话人嵌入
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在提取说话人嵌入...",
                "progress": 4
            }

            # 2. 提取嵌入
            embedding_extractor = SpeakerEmbeddingExtractor(offline_mode=True)
            embeddings = embedding_extractor.extract_embeddings(audio_paths)

            # 更新状态：识别说话人
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": "正在识别说话人...",
                "progress": 7
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
                "progress": 9
            }

            # 5. MOS打分（使用 NISQA）
            mos_scorer = NISQAScorer()
            scored_segments = mos_scorer.score_speaker_audios(audio_dir, speaker_segments)
            print(f"已完成MOS评分（NISQA）")
        else:
            print(f"使用缓存的MOS评分结果")

        # 更新状态：筛选和拼接音频（无缓存：11%，有缓存：7%）
        current_progress = 11 if not has_cached_mos else 7
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在筛选和拼接说话人音频...",
            "progress": current_progress
        }

        # 6. 筛选、排序、拼接音频
        audio_processor = SpeakerAudioProcessor(target_duration=10.0, silence_duration=1.0)
        # 使用audio_dir对应的references目录
        reference_output_dir = os.path.join(audio_dir, "references")
        speaker_audio_results = audio_processor.process_all_speakers(
            scored_segments, reference_output_dir
        )

        # 更新状态：提取字幕文本（无缓存：13%，有缓存：10%）
        current_progress = 13 if not has_cached_mos else 10
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在提取参考字幕文本...",
            "progress": current_progress
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
            # 转换为绝对路径
            audio_path = os.path.abspath(audio_path)
            reference_text = speaker_texts.get(speaker_id, "")
            speaker_name = speaker_name_mapping.get(speaker_id, f"说话人{speaker_id}")
            gender = gender_dict.get(speaker_id, "unknown")

            speaker_references[speaker_id] = {
                "reference_audio": audio_path,
                "reference_text": reference_text,
                "target_language": target_language,
                "speaker_name": speaker_name,
                "gender": gender
            }

        # 保存到状态中
        voice_cloning_status[task_id]["speaker_references"] = speaker_references

        # ========== 开始语音克隆流程（批量处理） ==========
        await asyncio.sleep(1)  # 给前端时间轮询

        # 使用新的简单批量克隆器（参照 batch_inference.py）
        # 使用单进程模式以获得准确的进度信息
        print("[Voice Clone] Using simple batch cloner (single-process mode for accurate progress)")
        from fish_simple_cloner import SimpleFishCloner
        batch_cloner = SimpleFishCloner(use_multiprocess=False)

        # 9. 批量编码所有说话人的参考音频（无缓存：15%，有缓存：13%）
        current_progress = 15 if not has_cached_mos else 13
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在批量编码说话人参考音频...",
            "progress": current_progress
        }
        await asyncio.sleep(0.5)

        encode_output_dir = os.path.join(audio_dir, "encoded")
        os.makedirs(encode_output_dir, exist_ok=True)

        # 处理音色映射：使用默认音色或说话人自己的音色（已通过函数参数传入）
        print(f"\n🚀 批量编码 {len(speaker_references)} 个说话人的参考音频...")
        print(f"   音色映射: {speaker_voice_mapping}")

        # 分离需要编码的说话人和使用默认音色的说话人
        speakers_to_encode = {}
        speaker_npy_files = {}

        print(f"\n📋 处理音色映射：")
        for speaker_id, ref_data in speaker_references.items():
            # speaker_id是整数，需要转换为字符串来查找映射
            speaker_id_str = str(speaker_id)
            selected_voice = speaker_voice_mapping.get(speaker_id_str, "default")
            print(f"  说话人 {speaker_id}: 映射key='{speaker_id_str}', 选择音色='{selected_voice}'")

            if selected_voice == "default":
                # 使用说话人自己的音色，需要编码
                speakers_to_encode[speaker_id] = ref_data
                print(f"    → 使用原音色，需要编码")
            else:
                # 使用默认音色库中的音色
                default_voice = next((v for v in DEFAULT_VOICES if v["id"] == selected_voice), None)
                if default_voice:
                    npy_path = str(DEFAULT_VOICES_DIR / default_voice["npy_file"])
                    speaker_npy_files[speaker_id] = npy_path
                    print(f"    → 使用默认音色: {default_voice['name']}")
                    print(f"    → NPY文件: {npy_path}")
                    # 更新参考文本为默认音色的参考文本
                    speaker_references[speaker_id]["reference_text"] = default_voice["reference_text"]
                else:
                    # 如果找不到指定的默认音色，回退到说话人自己的音色
                    print(f"    ⚠️ 未找到音色 {selected_voice}，使用原音色")
                    speakers_to_encode[speaker_id] = ref_data

        # 批量编码需要编码的说话人
        print(f"\n📊 处理结果：")
        print(f"  使用默认音色: {len(speaker_npy_files)} 个说话人")
        print(f"  需要编码: {len(speakers_to_encode)} 个说话人")

        if speakers_to_encode:
            encoded_npy_files = batch_cloner.batch_encode_speakers(
                speakers_to_encode,
                encode_output_dir
            )
            speaker_npy_files.update(encoded_npy_files)
        else:
            print(f"  所有说话人都使用默认音色，无需编码")

        # 10. 读取目标语言字幕（无缓存：18%，有缓存：17%）
        current_progress = 18 if not has_cached_mos else 17
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在读取目标语言字幕...",
            "progress": current_progress
        }
        await asyncio.sleep(0.5)

        from srt_parser import SRTParser
        srt_parser = SRTParser()
        target_subtitles = srt_parser.parse_srt(target_subtitle_path)
        source_subtitles = srt_parser.parse_srt(source_subtitle_path)

        # 10.5 验证译文长度并批量重新翻译超长文本（保持在同一进度）
        # current_progress 已在上一步设置，这里不再更新进度
        voice_cloning_status[task_id]["message"] = "正在验证译文长度..."
        await asyncio.sleep(0.5)

        from text_utils import check_translation_length, contains_chinese_characters

        # 检查每句译文长度
        # 日语、韩语因为使用假名/谚文，字符数会比汉字多，所以放宽限制
        # 法语、德语、西班牙语等欧洲语言也需要适当放宽，因为拉丁字母表达相同意思需要更多字符
        target_language_lower = target_language.lower()
        is_japanese = ('日' in target_language or 'ja' in target_language_lower)
        is_korean = ('韩' in target_language or 'ko' in target_language_lower or '한국' in target_language)
        is_french = ('法' in target_language or 'fr' in target_language_lower or 'français' in target_language_lower)
        is_german = ('德' in target_language or 'de' in target_language_lower or 'deutsch' in target_language_lower)
        is_spanish = ('西班牙' in target_language or 'es' in target_language_lower or 'español' in target_language_lower or 'spanish' in target_language_lower)

        # 不同语言使用不同的长度比例限制
        if is_japanese or is_korean:
            max_ratio = 3  # 日语/韩语：假名/谚文字符多
        elif is_french or is_german or is_spanish:
            max_ratio = 1.5  # 法语/德语/西班牙语：拉丁字母比英语略长
        else:
            max_ratio = 1.2  # 英语等其他语言

        too_long_items = []
        chinese_replacement_items = []

        for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
            source_text = source_sub["text"]
            target_text = target_sub["text"]

            is_too_long, source_len, target_len, ratio = check_translation_length(
                source_text, target_text, target_language, max_ratio=max_ratio
            )

            # 汉字检测规则：所有非中文语言的译文都不应包含汉字
            # 这对于语音克隆非常重要，因为汉字会影响发音准确性
            has_chinese = contains_chinese_characters(target_text)

            if is_too_long:
                # 如果过长，需要完全重新翻译
                too_long_items.append({
                    "index": idx,
                    "source": source_text,
                    "target": target_text,
                    "source_length": source_len,
                    "target_length": target_len,
                    "ratio": ratio,
                    "reason": "too_long"
                })
                language_display = target_language if target_language else "目标语言"
                print(f"  [长度检查] 第 {idx} 条 {language_display} 译文过长，需要重新翻译: {target_len}/{source_len} = {ratio:.1f}x")
            elif has_chinese:
                # 如果只是包含中文，只需要替换中文部分
                chinese_replacement_items.append({
                    "index": idx,
                    "target": target_text
                })
                language_display = target_language if target_language else "目标语言"
                print(f"  [汉字检查] 第 {idx} 条 {language_display} 译文包含汉字，将替换中文部分: '{target_text}'")

        # 如果有超长译文，进行批量重新翻译
        if too_long_items:
            print(f"\n⚠️  发现 {len(too_long_items)} 条超长译文，准备批量重新翻译...")

            # 无缓存：19%，有缓存：18%
            current_progress = 19 if not has_cached_mos else 18
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": f"正在批量重新翻译 {len(too_long_items)} 条超长文本...",
                "progress": current_progress
            }
            await asyncio.sleep(0.5)

            # 准备重新翻译任务
            import tempfile
            import json
            import subprocess

            # 将语言代码转换为中文名称（用于LLM prompt）
            target_language_name = get_language_name(target_language)

            retranslate_tasks = []
            for item in too_long_items:
                retranslate_tasks.append({
                    "task_id": f"retrans-{item['index']}",
                    "source": item["source"],
                    "target_language": target_language_name
                })

            # 写入配置文件
            config_file = os.path.join(audio_dir, "retranslate_config.json")

            # 不指定模型路径，让 batch_retranslate.py 根据 GPU 显存自动选择
            # 会在 Qwen3-4B-FP8, Qwen3-4B, Qwen3-1.7B 中选择
            retranslate_config = {
                "tasks": retranslate_tasks,
                "num_processes": 1  # 使用单进程，避免显存冲突
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(retranslate_config, f, ensure_ascii=False, indent=2)

            # 调用批量重新翻译脚本
            # 使用 ui conda 环境（Ollama 方案）
            ui_env_python = os.environ.get("UI_PYTHON")
            if not ui_env_python:
                # 默认路径
                import platform
                if platform.system() == "Windows":
                    ui_env_python = r"C:\Users\7\miniconda3\envs\ui\python.exe"
                else:
                    ui_env_python = os.path.expanduser("~/miniconda3/envs/ui/bin/python")

            batch_retranslate_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "batch_retranslate_ollama.py"
            )

            print(f"[Retranslate] 使用 Python: {ui_env_python}")
            print(f"[Retranslate] 脚本: {batch_retranslate_script}")
            print(f"[Retranslate] 配置: {config_file}")
            print(f"[Retranslate] 模型: Ollama qwen3:4b（异步并发）")

            # 检查 Python 环境是否存在
            if not os.path.exists(ui_env_python):
                print(f"⚠️  UI Python 环境不存在: {ui_env_python}")
                print(f"使用原译文继续...")
            else:
                try:
                    print(f"[Retranslate] 启动批量重新翻译进程...\n")
                    print(f"[Retranslate] 命令: {ui_env_python} {batch_retranslate_script} {config_file}\n")

                    # 在线程池中运行重新翻译subprocess（避免阻塞事件循环）
                    def run_retranslation_subprocess():
                        """在线程中运行重新翻译子进程"""
                        import subprocess
                        import time

                        try:
                            process = subprocess.Popen(
                                [ui_env_python, batch_retranslate_script, config_file],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                                text=True,  # 文本模式
                                encoding='utf-8',
                                errors='replace',  # 忽略解码错误
                                bufsize=1,  # 行缓冲
                                universal_newlines=True
                            )
                            print(f"[Retranslate] 进程已启动，PID: {process.pid}\n")
                        except Exception as e:
                            print(f"❌ 启动进程失败: {e}")
                            raise

                        # 实时读取输出
                        stdout_lines = []
                        print("[Retranslate] ===== 开始实时输出 =====")

                        try:
                            start_time = time.time()
                            timeout = 600  # 10分钟超时

                            while True:
                                # 检查超时
                                if time.time() - start_time > timeout:
                                    process.kill()
                                    print("\n⚠️  重新翻译超时（10分钟），使用原译文继续...")
                                    break

                                # 读取一行
                                line = process.stdout.readline()

                                if line:
                                    # 实时打印
                                    print(line, end='', flush=True)
                                    stdout_lines.append(line)
                                else:
                                    # 检查进程是否结束
                                    if process.poll() is not None:
                                        break
                                    time.sleep(0.1)

                            # 读取剩余输出
                            remaining = process.stdout.read()
                            if remaining:
                                print(remaining, end='', flush=True)
                                stdout_lines.append(remaining)

                            returncode = process.wait()
                            stdout = ''.join(stdout_lines)

                        except Exception as e:
                            process.kill()
                            print(f"\n⚠️  读取输出时出错: {e}")
                            stdout = ''.join(stdout_lines)
                            returncode = -1

                        print("[Retranslate] ===== 实时输出结束 =====\n")
                        return returncode, stdout

                    # 在线程池中执行
                    loop = asyncio.get_event_loop()
                    returncode, stdout = await loop.run_in_executor(
                        None,  # 使用默认线程池
                        run_retranslation_subprocess
                    )

                    if returncode == 0 and stdout:
                        # 解析输出中的 JSON 结果
                        output_lines = stdout.strip().split('\n')
                        # 查找最后一个 JSON 块
                        json_start = -1
                        for i in range(len(output_lines) - 1, -1, -1):
                            if output_lines[i].strip().startswith('['):
                                json_start = i
                                break

                        if json_start >= 0:
                            json_output = '\n'.join(output_lines[json_start:])
                            retranslate_results = json.loads(json_output)

                            print(f"\n[Retranslate] 解析到 {len(retranslate_results)} 条重新翻译结果:")
                            print(json.dumps(retranslate_results, ensure_ascii=False, indent=2))

                            # 更新目标字幕
                            for result_item in retranslate_results:
                                task_id_str = result_item["task_id"]
                                # 提取索引: "retrans-123" -> 123
                                idx = int(task_id_str.split('-')[1])
                                new_translation = result_item["translation"]

                                old_translation = target_subtitles[idx]["text"]

                                # 如果新翻译为空，保留旧翻译
                                if not new_translation or new_translation.strip() == "":
                                    print(f"  [更新 {idx}] ⚠️  翻译结果为空，保留原译文")
                                    print(f"    原译文: '{old_translation}'")
                                    # 不更新，保持原文
                                else:
                                    target_subtitles[idx]["text"] = new_translation
                                    print(f"  [更新 {idx}]")
                                    print(f"    旧: '{old_translation}'")
                                    print(f"    新: '{new_translation}'")

                            print(f"\n✅ 成功重新翻译 {len(retranslate_results)} 条文本")

                            # 保存更新后的字幕到文件
                            print(f"\n[Retranslate] 保存更新后的字幕到: {target_subtitle_path}")
                            srt_parser.save_srt(target_subtitles, target_subtitle_path)
                            print(f"✅ 字幕文件已更新")

                            # 验证保存：读取文件查看是否真的更新了
                            print(f"\n[Retranslate] 验证保存结果...")
                            print(f"[Retranslate] 读取文件: {target_subtitle_path}")
                            saved_subtitles = srt_parser.parse_srt(target_subtitle_path)
                            print(f"[Retranslate] 文件中共有 {len(saved_subtitles)} 条字幕")
                            for result_item in retranslate_results:
                                idx = int(result_item["task_id"].split('-')[1])
                                if idx < len(saved_subtitles):
                                    saved_text = saved_subtitles[idx]["text"]
                                    expected_text = result_item["translation"]
                                    match = "✅" if saved_text == expected_text else "❌"
                                    print(f"  {match} [{idx}]")
                                    print(f"      期待: '{expected_text}'")
                                    print(f"      文件: '{saved_text}'")
                                else:
                                    print(f"  ❌ [{idx}] 索引超出范围（文件只有 {len(saved_subtitles)} 条）")
                        else:
                            print("⚠️  未找到重新翻译结果，使用原译文")
                    elif returncode != 0:
                        print(f"⚠️  重新翻译失败 (返回码: {returncode})")
                        if stdout and stdout.strip():
                            print(f"[Retranslate] stdout:\n{stdout[:500]}")  # 只打印前500字符
                        print("使用原译文继续...")
                    else:
                        print("⚠️  重新翻译返回成功但没有输出，使用原译文继续...")

                except Exception as e:
                    print(f"⚠️  重新翻译出错: {e}")
                    import traceback
                    traceback.print_exc()
                    print("使用原译文继续...")

        # 10.4. 中文替换：将译文中的中文部分替换为目标语言
        if chinese_replacement_items:
            print(f"\n[中文替换] 发现 {len(chinese_replacement_items)} 条包含中文的译文，准备替换...")

            from text_utils import extract_and_replace_chinese

            # 判断是否是日语
            is_japanese = ('日' in target_language or 'ja' in target_language.lower())

            replaced_count = 0
            for item in chinese_replacement_items:
                idx = item["index"]
                original_text = item["target"]

                # 提取并替换中文部分
                replaced_text = extract_and_replace_chinese(
                    original_text,
                    target_language,
                    to_kana=is_japanese  # 如果是日语，转换为假名
                )

                if replaced_text != original_text:
                    target_subtitles[idx]["text"] = replaced_text
                    replaced_count += 1
                    print(f"  [{idx}] '{original_text}' -> '{replaced_text}'")

            if replaced_count > 0:
                print(f"\n✅ 成功替换 {replaced_count} 条译文中的中文")
                # 保存更新后的字幕文件
                print(f"[中文替换] 保存更新后的字幕到: {target_subtitle_path}")
                srt_parser.save_srt(target_subtitles, target_subtitle_path)
                print(f"✅ 字幕文件已更新")
            else:
                print(f"ℹ️  所有中文都已成功替换")

        # 10.4.5. 英文检测：如果目标语言是日语或韩语，检测纯英文句子并转换
        is_japanese = ('日' in target_language or 'ja' in target_language.lower())
        is_korean = ('韩' in target_language or 'ko' in target_language.lower())

        if is_japanese or is_korean:
            print(f"\n[英文检测] 检查译文中的纯英文句子...")
            from text_utils import is_english_text, batch_translate_english_to_kana, batch_translate_english_to_korean

            # 收集所有纯英文句子
            english_items = []
            for idx, target_sub in enumerate(target_subtitles):
                target_text = target_sub.get("text", "").strip()
                if is_english_text(target_text):
                    english_items.append({
                        "index": idx,
                        "text": target_text
                    })

            if english_items:
                print(f"[英文检测] 发现 {len(english_items)} 条纯英文句子，准备转换...")

                # 提取所有英文文本并去重
                english_texts = [item["text"] for item in english_items]
                unique_english = list(dict.fromkeys(english_texts))  # 保持顺序的去重

                # 批量转换
                if is_japanese:
                    print(f"[英文检测] 批量转换为日语假名...")
                    translation_map = batch_translate_english_to_kana(unique_english)
                else:  # is_korean
                    print(f"[英文检测] 批量转换为韩文...")
                    translation_map = batch_translate_english_to_korean(unique_english)

                # 替换所有英文句子
                converted_count = 0
                for item in english_items:
                    idx = item["index"]
                    original_text = item["text"]

                    converted_text = translation_map.get(original_text, original_text)

                    if converted_text != original_text:
                        target_subtitles[idx]["text"] = converted_text
                        converted_count += 1
                        print(f"  [{idx}] '{original_text}' -> '{converted_text}'")

                if converted_count > 0:
                    print(f"\n✅ 成功转换 {converted_count} 条纯英文句子")
                    # 保存更新后的字幕文件
                    print(f"[英文检测] 保存更新后的字幕到: {target_subtitle_path}")
                    srt_parser.save_srt(target_subtitles, target_subtitle_path)
                    print(f"✅ 字幕文件已更新")
                else:
                    print(f"ℹ️  所有英文句子都已成功转换")
            else:
                print(f"[英文检测] 未发现纯英文句子")

        # 10.5. 数字替换：将阿拉伯数字转换为目标语言的发音
        print(f"\n[数字替换] 开始检测并替换译文中的阿拉伯数字...")
        from text_utils import replace_digits_in_text

        # 获取目标语言代码（从语言名称映射回代码）
        language_code_map = {
            '英语': 'en',
            '韩语': 'ko',
            '日语': 'ja',
            '法语': 'fr',
            '德语': 'de',
            '西班牙语': 'es'
        }
        target_lang_code = language_code_map.get(target_language, target_language.lower())

        # 遍历所有译文，检测并替换数字
        digits_replaced_count = 0
        for idx, subtitle in enumerate(target_subtitles):
            original_text = subtitle["text"]
            replaced_text = replace_digits_in_text(original_text, target_lang_code)

            if replaced_text != original_text:
                subtitle["text"] = replaced_text
                digits_replaced_count += 1
                print(f"  [{idx}] '{original_text}' -> '{replaced_text}'")

        if digits_replaced_count > 0:
            print(f"\n✅ 成功替换 {digits_replaced_count} 条译文中的数字")
            # 保存更新后的字幕文件
            print(f"[数字替换] 保存更新后的字幕到: {target_subtitle_path}")
            srt_parser.save_srt(target_subtitles, target_subtitle_path)
            print(f"✅ 字幕文件已更新")
        else:
            print(f"ℹ️  未发现需要替换的数字")

        # 11. 准备批量生成任务
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在批量生成克隆语音...",
            "progress": 20
        }
        await asyncio.sleep(0.5)

        cloned_audio_dir = os.path.join("exports", f"cloned_{task_id}")
        os.makedirs(cloned_audio_dir, exist_ok=True)

        # 准备任务列表
        tasks = []
        cloned_results = []

        print(f"\n[DEBUG] 准备任务列表")
        print(f"  speaker_labels 长度: {len(speaker_labels)}")
        print(f"  target_subtitles 长度: {len(target_subtitles)}")
        print(f"  target_subtitles 中前3条文本:")
        for i in range(min(3, len(target_subtitles))):
            print(f"    [{i}] {target_subtitles[i]['text']}")

        # 检查长度不一致的情况
        if len(speaker_labels) != len(target_subtitles):
            error_msg = (
                f"❌ 字幕文件行数不匹配！\n"
                f"   原语言字幕: {len(speaker_labels)} 条\n"
                f"   目标语言字幕: {len(target_subtitles)} 条\n"
                f"   💡 请确保两个字幕文件的行数完全一致（每一行原文对应一行译文）"
            )
            print(f"\n{error_msg}")

            # 更新状态为失败
            voice_cloning_status[task_id] = {
                "status": "failed",
                "message": f"字幕文件行数不匹配: 原文{len(speaker_labels)}条 vs 译文{len(target_subtitles)}条",
                "progress": 0
            }

            raise ValueError(error_msg)

        for idx, (speaker_id, target_sub) in enumerate(zip(speaker_labels, target_subtitles)):
            target_text = target_sub["text"]

            if speaker_id is None or speaker_id not in speaker_npy_files:
                # 没有分配说话人或说话人编码失败的片段，记录但不生成
                cloned_results.append({
                    "index": idx,
                    "speaker_id": speaker_id,
                    "target_text": target_text,
                    "cloned_audio_path": None,
                    "start_time": target_sub.get("start_time", 0),
                    "end_time": target_sub.get("end_time", 0)
                })
            else:
                # 添加到批量生成任务
                tasks.append({
                    "speaker_id": speaker_id,
                    "target_text": target_text,
                    "segment_index": idx,
                    "start_time": target_sub.get("start_time", 0),
                    "end_time": target_sub.get("end_time", 0)
                })

        # 批量生成所有语音
        print(f"\n🚀 批量生成 {len(tasks)} 个语音片段...")

        # 定义进度回调函数
        def voice_cloning_progress_callback(current, total):
            # 20-95% 的进度用于语音生成（前20%给前置操作，后80%给克隆）
            progress = 20 + int((current / total) * 75)
            voice_cloning_status[task_id]["progress"] = progress
            voice_cloning_status[task_id]["message"] = f"正在生成语音... ({current}/{total})"
            # 调试日志已移除 - 减少日志输出

        # 将生成脚本保存到audio_dir下的scripts目录，避免触发uvicorn reload
        script_dir = os.path.join(audio_dir, "scripts")

        # 在线程池中运行语音生成（避免阻塞事件循环）
        def run_batch_generation():
            return batch_cloner.batch_generate_audio(
                tasks,
                speaker_npy_files,
                speaker_references,
                cloned_audio_dir,
                script_dir=script_dir,
                progress_callback=voice_cloning_progress_callback
            )

        loop = asyncio.get_event_loop()
        generated_audio_files = await loop.run_in_executor(
            None,  # 使用默认线程池
            run_batch_generation
        )

        # 调试：打印生成结果
        print(f"\n[DEBUG] generated_audio_files 类型: {type(generated_audio_files)}")
        print(f"[DEBUG] generated_audio_files 键示例 (前3个): {list(generated_audio_files.keys())[:3]}")
        print(f"[DEBUG] generated_audio_files 示例:")
        for key in list(generated_audio_files.keys())[:3]:
            print(f"  key={key} (type={type(key)}), value={generated_audio_files[key]}")

        # 更新结果，添加生成成功的音频路径
        for task in tasks:
            segment_index = task["segment_index"]
            if segment_index in generated_audio_files:
                # 生成API路径（与 fish_simple_cloner.py 中的文件名格式一致）
                audio_filename = f"segment_{segment_index}.wav"
                api_path = f"/cloned-audio/{task_id}/{audio_filename}"

                cloned_results.append({
                    "index": segment_index,
                    "speaker_id": task["speaker_id"],
                    "target_text": task["target_text"],
                    "cloned_audio_path": api_path,
                    "start_time": task.get("start_time", 0),
                    "end_time": task.get("end_time", 0)
                })
            else:
                cloned_results.append({
                    "index": segment_index,
                    "speaker_id": task["speaker_id"],
                    "target_text": task["target_text"],
                    "cloned_audio_path": None,
                    "error": "生成失败",
                    "start_time": task.get("start_time", 0),
                    "end_time": task.get("end_time", 0)
                })

        # 按索引排序结果
        cloned_results.sort(key=lambda x: x["index"])

        # 调试：打印前几个结果（包含 target_text）
        print(f"\n[DEBUG] cloned_results 示例 (前3个):")
        for i, result in enumerate(cloned_results[:3]):
            print(f"  [{i}] index={result['index']}, speaker_id={result['speaker_id']}")
            print(f"      target_text='{result['target_text']}'")
            print(f"      cloned_audio_path={result.get('cloned_audio_path', 'None')}")

        # 计算总耗时
        end_time = time.time()
        total_duration = end_time - start_time

        # 格式化时间显示
        def format_duration(seconds):
            """将秒数格式化为易读的时间字符串"""
            if seconds < 60:
                return f"{seconds:.1f}秒"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}分{secs}秒"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}小时{minutes}分钟"

        duration_str = format_duration(total_duration)

        # 创建完整的初始音色映射（为所有说话人设置默认值）
        complete_initial_mapping = {}
        for speaker_id in speaker_references.keys():
            speaker_id_str = str(speaker_id)
            complete_initial_mapping[speaker_id_str] = speaker_voice_mapping.get(speaker_id_str, "default")

        # 更新状态：完成
        voice_cloning_status[task_id] = {
            "status": "completed",
            "message": f"语音克隆完成 (耗时: {duration_str})",
            "progress": 100,
            "speaker_references": speaker_references,
            "unique_speakers": len(speaker_references),
            "speaker_name_mapping": speaker_name_mapping,
            "gender_dict": gender_dict,
            "cloned_results": cloned_results,
            "audio_dir": audio_dir,  # 保存音频片段目录
            "cloned_audio_dir": cloned_audio_dir,  # 保存克隆音频目录
            "initial_speaker_voice_mapping": complete_initial_mapping,  # 保存完整的初始音色映射
            "total_duration": total_duration,  # 原始秒数
            "duration_str": duration_str  # 格式化的时间字符串
        }

        print(f"\n语音克隆准备完成！")
        print(f"识别到 {len(speaker_references)} 个说话人")
        for speaker_id, ref_data in speaker_references.items():
            print(f"\n{ref_data['speaker_name']} (ID: {speaker_id}, 性别: {ref_data['gender']}):")
            print(f"  参考音频: {ref_data['reference_audio']}")
            print(f"  参考文本: {ref_data['reference_text'][:100]}...")

        print(f"\n✅ 语音克隆任务 {task_id} 成功完成！")
        print(f"⏱️  总耗时: {duration_str}")
        return  # 显式返回，确保函数正常结束

    except Exception as e:
        # 计算失败时的耗时
        end_time = time.time()
        total_duration = end_time - start_time

        # 更新状态为失败
        import traceback
        error_detail = traceback.format_exc()
        print(f"语音克隆处理失败: {error_detail}")
        print(f"⏱️  失败前耗时: {total_duration:.1f}秒")

        voice_cloning_status[task_id] = {
            "status": "failed",
            "message": f"处理失败: {str(e)}",
            "progress": 0,
            "total_duration": total_duration,
            "duration_str": f"{total_duration:.1f}秒"
        }


@app.get("/voice-cloning/status/{task_id}")
async def get_voice_cloning_status(task_id: str):
    """获取语音克隆处理状态"""
    if task_id not in voice_cloning_status:
        raise HTTPException(status_code=404, detail="任务不存在")

    status = voice_cloning_status[task_id]
    # 调试日志已移除 - 减少日志输出
    return status


@app.get("/voice-cloning/default-voices")
async def get_default_voices():
    """获取默认音色库列表"""
    voices = []
    for voice in DEFAULT_VOICES:
        voice_info = {
            "id": voice["id"],
            "name": voice["name"],
            "audio_url": f"/default-voices/{voice['audio_file']}",
            "reference_text": voice["reference_text"]
        }
        voices.append(voice_info)
    return {"voices": voices}


@app.get("/default-voices/{filename}")
async def serve_default_voice_audio(filename: str):
    """提供默认音色的音频文件"""
    file_path = DEFAULT_VOICES_DIR / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音频文件未找到")

    return FileResponse(file_path, media_type="audio/wav")


@app.get("/cloned-audio/{task_id}/{filename}")
async def serve_cloned_audio(task_id: str, filename: str, request: Request):
    """提供克隆音频文件的流式传输，支持 HTTP Range 请求"""
    file_path = EXPORTS_DIR / f"cloned_{task_id}" / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="音频文件未找到")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    # 如果没有 Range 请求头，返回整个文件
    if not range_header:
        return FileResponse(
            file_path,
            media_type="audio/wav",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
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
    async def iterfile():
        # 延迟一小段时间，确保文件写入完成
        import asyncio
        await asyncio.sleep(0.01)

        # 重新检查文件大小，防止文件还在写入
        current_size = file_path.stat().st_size
        if current_size != file_size:
            print(f"⚠️  警告：文件 {filename} 大小变化: {file_size} -> {current_size}")

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
        media_type="audio/wav",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_size),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


class RegenerateSegmentRequest(BaseModel):
    task_id: str
    segment_index: int
    new_speaker_id: int
    new_text: Optional[str] = None  # 新的原文（如果修改了）
    new_target_text: Optional[str] = None  # 新的译文（如果修改了）


class TranslateTextRequest(BaseModel):
    text: str
    target_language: str


class BatchTranslateRequest(BaseModel):
    source_subtitle_filename: str
    target_language: str


class StitchAudioRequest(BaseModel):
    task_id: str


class RegenerateVoicesRequest(BaseModel):
    task_id: str
    speaker_voice_mapping: Dict[str, str]  # {speaker_id: voice_id}


@app.post("/voice-cloning/regenerate-voices")
async def regenerate_voices_with_new_mapping(request: RegenerateVoicesRequest):
    """重新生成使用了不同音色的说话人的所有语音片段"""
    try:
        import asyncio
        from fish_batch_cloner import FishBatchCloner
        import time

        task_id = request.task_id

        # 检查任务是否存在
        if task_id not in voice_cloning_status:
            raise HTTPException(status_code=404, detail="任务不存在")

        status = voice_cloning_status[task_id]
        cloned_results = status.get("cloned_results", [])
        speaker_references = status.get("speaker_references", {})

        if not cloned_results or not speaker_references:
            raise HTTPException(status_code=400, detail="没有可重新生成的语音数据")

        # 记录开始时间
        start_time = time.time()

        # 设置状态为重新生成中
        voice_cloning_status[task_id]["status"] = "regenerating"
        voice_cloning_status[task_id]["message"] = "正在重新生成语音..."
        voice_cloning_status[task_id]["progress"] = 0

        # 获取音频目录
        audio_dir = status.get("audio_dir")
        cloned_audio_dir = status.get("cloned_audio_dir")

        print(f"\n[重新生成] 开始重新生成任务 {task_id} 的语音...")
        print(f"[重新生成] 新音色映射: {request.speaker_voice_mapping}")

        # 获取初始音色映射
        initial_mapping = status.get("initial_speaker_voice_mapping", {})
        print(f"[重新生成] 初始音色映射: {initial_mapping}")

        # 分析需要重新生成的说话人（对比初始映射和新映射）
        speakers_to_regenerate = set()
        for speaker_id_str in speaker_references.keys():
            speaker_id_str_key = str(speaker_id_str)
            initial_voice = initial_mapping.get(speaker_id_str_key, "default")
            new_voice = request.speaker_voice_mapping.get(speaker_id_str_key, "default")

            if initial_voice != new_voice:
                speakers_to_regenerate.add(int(speaker_id_str))
                print(f"  说话人 {speaker_id_str}: {initial_voice} -> {new_voice} (需要重新生成)")
            else:
                print(f"  说话人 {speaker_id_str}: {initial_voice} (无变化)")

        if not speakers_to_regenerate:
            print(f"[重新生成] 没有需要重新生成的说话人")
            voice_cloning_status[task_id]["status"] = "completed"
            return {"success": True, "message": "没有需要重新生成的说话人"}

        print(f"\n[重新生成] 需要重新生成的说话人: {speakers_to_regenerate}")

        # 收集需要重新生成的任务（格式与初始克隆时一致）
        tasks_to_regenerate = []
        for idx, result in enumerate(cloned_results):
            if result["speaker_id"] in speakers_to_regenerate:
                tasks_to_regenerate.append({
                    "speaker_id": result["speaker_id"],
                    "target_text": result["target_text"],
                    "segment_index": idx,
                    "start_time": result.get("start_time", 0),
                    "end_time": result.get("end_time", 0)
                })

        print(f"[重新生成] 总共需要重新生成 {len(tasks_to_regenerate)} 个片段")

        # 准备npy文件
        encode_output_dir = os.path.join(audio_dir, "encoded")
        os.makedirs(encode_output_dir, exist_ok=True)

        batch_cloner = FishBatchCloner()
        speaker_npy_files = {}

        for speaker_id in speakers_to_regenerate:
            speaker_id_str = str(speaker_id)
            selected_voice = request.speaker_voice_mapping.get(speaker_id_str, "default")

            if selected_voice == "default":
                # 使用说话人自己的音色
                ref_data = speaker_references[speaker_id]
                speakers_dict = {speaker_id: ref_data}
                encoded_npy = batch_cloner.batch_encode_speakers(speakers_dict, encode_output_dir)
                speaker_npy_files[speaker_id] = encoded_npy[speaker_id]
                print(f"  ✅ 说话人 {speaker_id} 使用自己的音色")
            else:
                # 使用默认音色
                default_voice = next((v for v in DEFAULT_VOICES if v["id"] == selected_voice), None)
                if default_voice:
                    npy_path = str(DEFAULT_VOICES_DIR / default_voice["npy_file"])
                    speaker_npy_files[speaker_id] = npy_path
                    print(f"  ✅ 说话人 {speaker_id} 使用默认音色: {default_voice['name']}")
                    # 更新参考文本
                    speaker_references[speaker_id]["reference_text"] = default_voice["reference_text"]

        # 获取脚本目录
        script_dir = os.path.join(audio_dir, "scripts")

        # 批量生成语音
        print(f"\n[重新生成] 开始批量生成...")
        generated_audio_files = batch_cloner.batch_generate_audio(
            tasks_to_regenerate,
            speaker_npy_files,
            speaker_references,
            cloned_audio_dir,
            script_dir=script_dir
        )

        # 更新 cloned_results
        print(f"\n[重新生成] 更新 cloned_results...")
        import time
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
        for task in tasks_to_regenerate:
            segment_index = task["segment_index"]
            if segment_index in generated_audio_files:
                # 生成API路径，添加时间戳参数破坏浏览器缓存
                audio_filename = f"segment_{segment_index}.wav"
                api_path = f"/cloned-audio/{task_id}/{audio_filename}?t={timestamp}"

                # 更新该片段的信息
                old_path = cloned_results[segment_index].get("cloned_audio_path")
                cloned_results[segment_index]["cloned_audio_path"] = api_path
                print(f"  ✅ 片段 {segment_index}: {old_path} -> {api_path}")
            else:
                print(f"  ❌ 片段 {segment_index} 重新生成失败")

        voice_cloning_status[task_id]["cloned_results"] = cloned_results
        print(f"[重新生成] cloned_results 已更新到 voice_cloning_status")

        # 计算耗时
        end_time = time.time()
        duration = end_time - start_time

        def format_duration(seconds):
            if seconds < 60:
                return f"{seconds:.1f}秒"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}分{secs}秒"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}小时{minutes}分钟"

        duration_str = format_duration(duration)

        voice_cloning_status[task_id]["status"] = "completed"
        voice_cloning_status[task_id]["message"] = f"重新生成完成 (耗时: {duration_str})"
        voice_cloning_status[task_id]["progress"] = 100

        # 创建完整的新音色映射（为所有说话人设置默认值）
        complete_new_mapping = {}
        for speaker_id in speaker_references.keys():
            speaker_id_str = str(speaker_id)
            complete_new_mapping[speaker_id_str] = request.speaker_voice_mapping.get(speaker_id_str, "default")

        # 更新初始音色映射为新的映射
        voice_cloning_status[task_id]["initial_speaker_voice_mapping"] = complete_new_mapping

        print(f"\n✅ 重新生成任务 {task_id} 成功完成！")
        print(f"⏱️  总耗时: {duration_str}")

        return {
            "success": True,
            "message": f"成功重新生成 {len(tasks_to_regenerate)} 个片段",
            "regenerated_count": len(tasks_to_regenerate),
            "duration": duration_str
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[重新生成] 失败: {error_detail}")

        voice_cloning_status[task_id]["status"] = "failed"
        voice_cloning_status[task_id]["message"] = f"重新生成失败: {str(e)}"

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/translate-text")
async def translate_text(request: TranslateTextRequest):
    """使用LLM翻译文本"""
    print(f"\n[翻译API] 收到请求")
    print(f"[翻译API] 原文: {request.text}")
    print(f"[翻译API] 目标语言: {request.target_language}")

    try:
        import json
        import subprocess
        import tempfile
        import os

        # 将语言代码转换为中文名称（用于LLM prompt）
        target_language_name = get_language_name(request.target_language)
        print(f"[翻译API] 语言代码: {request.target_language} -> {target_language_name}")

        # 创建临时配置文件（使用 Ollama）
        config_data = {
            "tasks": [{
                "task_id": "translate-1",
                "source": request.text,
                "target_language": target_language_name
            }],
            "model": "qwen2.5:7b"  # 使用 qwen2.5:7b 避免 qwen3 的思考延迟
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False)
            config_file = f.name

        print(f"[翻译API] 创建临时配置文件: {config_file}")

        try:
            # 使用 ui conda 环境（Ollama 方案）
            ui_env_python = os.environ.get("UI_PYTHON")
            if not ui_env_python:
                import platform
                if platform.system() == "Windows":
                    ui_env_python = r"C:\Users\7\miniconda3\envs\ui\python.exe"
                else:
                    ui_env_python = os.path.expanduser("~/miniconda3/envs/ui/bin/python")

            # 调用 Ollama 批量翻译脚本
            batch_retranslate_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "batch_retranslate_ollama.py"
            )

            print(f"[翻译API] 调用翻译脚本...")
            print(f"[翻译API] Python可执行文件: {ui_env_python}")
            print(f"[翻译API] 翻译脚本: {batch_retranslate_script}")
            print(f"[翻译API] 工作目录: {os.path.dirname(__file__)}")

            # 使用 Popen 以实时获取输出
            import sys
            import threading
            import time as time_module

            process = subprocess.Popen(
                [ui_env_python, batch_retranslate_script, config_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                cwd=os.path.dirname(__file__),
                bufsize=1  # 行缓冲
            )

            print(f"[翻译API] 进程已启动 PID={process.pid}，等待输出...")

            # 实时读取输出（使用线程）
            stdout_lines = []
            stderr_lines = []

            def read_stdout():
                for line in process.stdout:
                    line = line.rstrip('\n')
                    print(f"[翻译脚本] {line}")
                    stdout_lines.append(line)
                    sys.stdout.flush()

            def read_stderr():
                for line in process.stderr:
                    line = line.rstrip('\n')
                    print(f"[翻译脚本 STDERR] {line}")
                    stderr_lines.append(line)
                    sys.stdout.flush()

            # 启动读取线程
            stdout_thread = threading.Thread(target=read_stdout)
            stderr_thread = threading.Thread(target=read_stderr)
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()

            # 等待进程结束（带超时）
            try:
                return_code = process.wait(timeout=300)
            except subprocess.TimeoutExpired:
                print(f"[翻译API] 超时！正在终止进程...")
                process.kill()
                process.wait()
                raise

            # 等待线程结束
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            # 构建结果对象
            class Result:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr

            result = Result(
                return_code,
                '\n'.join(stdout_lines),
                '\n'.join(stderr_lines)
            )

            print(f"[翻译API] 进程结束，返回码={result.returncode}")

            if result.returncode != 0:
                print(f"[翻译API] 翻译脚本stderr: {result.stderr}")
                print(f"[翻译API] 翻译脚本stdout: {result.stdout}")
                raise HTTPException(status_code=500, detail=f"翻译脚本执行失败: {result.stderr}")

            # 解析输出中的JSON结果
            print(f"[翻译API] 解析翻译结果...")
            output_lines = result.stdout.split('\n')
            json_started = False
            json_lines = []

            for line in output_lines:
                if 'FINAL RESULTS (JSON)' in line:
                    json_started = True
                    continue
                if json_started:
                    # 跳过分隔线
                    if line.strip().startswith('='):
                        continue
                    # 开始收集JSON（从 [ 开始）
                    if line.strip().startswith('['):
                        json_lines.append(line)
                    elif len(json_lines) > 0:
                        # 已经开始收集了，继续添加
                        json_lines.append(line)

            json_text = '\n'.join(json_lines).strip()
            print(f"[翻译API] JSON文本: {json_text[:200]}...")

            results = json.loads(json_text)
            print(f"[翻译API] 解析结果数量: {len(results)}")

            if results and len(results) > 0:
                translation = results[0].get('translation', request.text)
                print(f"[翻译API] 翻译成功: {translation}")
                return {"translation": translation}
            else:
                print(f"[翻译API] 警告: 没有翻译结果，返回原文")
                return {"translation": request.text}

        finally:
            # 删除临时文件
            if os.path.exists(config_file):
                os.remove(config_file)
                print(f"[翻译API] 删除临时文件: {config_file}")

    except subprocess.TimeoutExpired:
        print(f"[翻译API] 超时: 翻译耗时超过300秒")
        # 超时时返回原文，不抛出异常
        return {"translation": request.text, "error": "timeout"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[翻译API] 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        # 异常时返回原文，不抛出HTTP异常
        return {"translation": request.text, "error": str(e)}


@app.post("/translate/batch")
async def batch_translate_subtitles(request: BatchTranslateRequest, background_tasks: BackgroundTasks):
    """批量翻译字幕文件"""
    print(f"\n[批量翻译] 收到请求")
    print(f"[批量翻译] 原文字幕: {request.source_subtitle_filename}")
    print(f"[批量翻译] 目标语言: {request.target_language}")

    try:
        import uuid

        # 生成唯一任务ID
        task_id = str(uuid.uuid4())

        # 初始化翻译状态
        translation_status[task_id] = {
            "status": "processing",
            "message": "正在准备翻译...",
            "progress": 0,
            "source_subtitle_filename": request.source_subtitle_filename,
            "target_language": request.target_language
        }

        # 在后台执行翻译任务
        print(f"[批量翻译] 添加后台任务: {task_id}", flush=True)
        background_tasks.add_task(
            run_batch_translation,
            task_id,
            request.source_subtitle_filename,
            request.target_language
        )

        print(f"[批量翻译] 返回响应给前端: {task_id}", flush=True)
        return {"task_id": task_id, "message": "翻译任务已启动"}

    except Exception as e:
        print(f"[批量翻译] 启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/translate/status/{task_id}")
async def get_translation_status(task_id: str):
    """获取翻译状态"""
    if task_id not in translation_status:
        raise HTTPException(status_code=404, detail="翻译任务不存在")

    status = translation_status[task_id]
    # 调试日志已移除 - 减少日志输出
    return status


async def run_batch_translation(task_id: str, source_subtitle_filename: str, target_language: str):
    """执行批量翻译任务（后台任务）"""
    try:
        import json
        import subprocess
        import tempfile
        import os
        import re

        print(f"\n[批量翻译-{task_id}] 开始翻译任务")

        # 更新状态
        translation_status[task_id]["message"] = "正在读取原文字幕..."
        translation_status[task_id]["progress"] = 5

        # 读取原文字幕
        source_srt_path = UPLOADS_DIR / source_subtitle_filename

        if not os.path.exists(source_srt_path):
            raise FileNotFoundError(f"原文字幕文件不存在: {source_srt_path}")

        # 解析SRT文件
        with open(source_srt_path, 'r', encoding='utf-8') as f:
            source_content = f.read()

        # 提取所有字幕文本
        subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*\n?)+?)(?=\n\d+\n|\n*$)'
        matches = re.findall(subtitle_pattern, source_content)

        if not matches:
            raise ValueError("无法解析SRT文件")

        subtitles = []
        for index, start_time, end_time, text in matches:
            text = text.strip()
            subtitles.append({
                "index": int(index) - 1,  # 转为0基索引
                "start_time": start_time,
                "end_time": end_time,
                "text": text
            })

        print(f"[批量翻译-{task_id}] 共 {len(subtitles)} 条字幕需要翻译")

        # 记录开始时间
        translation_start_time = time.time()

        # 更新状态
        translation_status[task_id]["message"] = f"正在翻译 {len(subtitles)} 条字幕..."
        translation_status[task_id]["progress"] = 10

        # 将语言代码转换为中文名称
        target_language_name = get_language_name(target_language)
        print(f"[批量翻译-{task_id}] 目标语言: {target_language} -> {target_language_name}")

        # 创建翻译任务列表
        translate_tasks = []
        for sub in subtitles:
            translate_tasks.append({
                "task_id": f"tr-{sub['index']}",
                "source": sub["text"],
                "target_language": target_language_name
            })

        # 创建临时配置文件
        config_data = {
            "tasks": translate_tasks,
            "model": "qwen2.5:7b"  # 使用 qwen2.5:7b 避免 qwen3 的思考延迟
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False)
            config_file = f.name

        print(f"[批量翻译-{task_id}] 配置文件: {config_file}")

        try:
            # 获取Python可执行文件路径
            ui_env_python = os.environ.get("UI_PYTHON")
            if not ui_env_python:
                import platform
                if platform.system() == "Windows":
                    ui_env_python = r"C:\Users\7\miniconda3\envs\ui\python.exe"
                else:
                    ui_env_python = os.path.expanduser("~/miniconda3/envs/ui/bin/python")

            # 调用翻译脚本
            batch_translate_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "batch_translate_ollama.py"
            )

            print(f"[批量翻译-{task_id}] 调用翻译脚本...")
            print(f"[批量翻译-{task_id}] Python: {ui_env_python}")
            print(f"[批量翻译-{task_id}] 脚本: {batch_translate_script}")

            # 启动翻译进程（使用线程池避免阻塞）
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            def run_translation_subprocess():
                """在线程中运行翻译子进程"""
                import subprocess
                process = subprocess.Popen(
                    [ui_env_python, batch_translate_script, config_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    cwd=os.path.dirname(__file__),
                    bufsize=1,
                    env=env
                )

                stdout_lines = []
                stderr_lines = []

                # 实时读取输出并更新进度
                for line in process.stdout:
                    line = line.rstrip('\n')
                    print(f"[翻译脚本-{task_id}] {line}", flush=True)
                    stdout_lines.append(line)

                    # 解析进度 - 匹配格式: [1/46] ✓ tr-0: ...
                    if line.startswith('[') and '/' in line and ']' in line:
                        try:
                            # 例如: [5/30] ✓ tr-4: ...
                            parts = line.split(']')[0].strip('[').split('/')
                            current = int(parts[0])
                            total = int(parts[1])
                            progress = 10 + int((current / total) * 70)  # 10-80%，为质量检查预留20%
                            translation_status[task_id]["progress"] = progress
                            translation_status[task_id]["message"] = f"正在翻译... ({current}/{total})"
                            print(f"[批量翻译-{task_id}] 更新进度: {current}/{total} -> {progress}%")
                        except Exception as e:
                            print(f"[批量翻译-{task_id}] 解析进度失败: {e}, 行内容: {line}")

                # 等待进程结束并获取返回码
                return_code = process.wait()

                # 如果有错误，读取stderr
                if return_code != 0:
                    stderr_output = process.stderr.read()
                    stderr_lines.append(stderr_output)

                return return_code, stdout_lines, stderr_lines

            # 在线程池中运行子进程（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            return_code, stdout_lines, stderr_lines = await loop.run_in_executor(
                None,  # 使用默认线程池
                run_translation_subprocess
            )

            if return_code != 0:
                stderr_output = '\n'.join(stderr_lines)
                print(f"[批量翻译-{task_id}] 错误: {stderr_output}")
                raise Exception(f"翻译脚本失败: {stderr_output}")

            # 更新状态
            translation_status[task_id]["message"] = "正在保存翻译结果..."
            translation_status[task_id]["progress"] = 80

            # 解析翻译结果
            output_text = '\n'.join(stdout_lines)

            # 查找JSON结果
            json_started = False
            json_lines = []

            for line in stdout_lines:
                if '翻译结果（JSON）' in line or 'FINAL RESULTS' in line:
                    json_started = True
                    continue
                if json_started:
                    if line.strip().startswith('='):
                        continue
                    if line.strip().startswith('['):
                        json_lines.append(line)
                    elif len(json_lines) > 0:
                        json_lines.append(line)
                        if line.strip().endswith(']'):
                            break

            json_text = '\n'.join(json_lines).strip()
            results = json.loads(json_text)

            print(f"[批量翻译-{task_id}] 解析到 {len(results)} 条翻译结果")

            # 创建翻译后的SRT文件
            translated_subtitles = []
            for result in results:
                task_index = int(result["task_id"].split('-')[-1])
                original_sub = subtitles[task_index]

                translated_subtitles.append({
                    "index": original_sub["index"],
                    "start_time": original_sub["start_time"],
                    "end_time": original_sub["end_time"],
                    "text": result["translation"]
                })

            # 按索引排序
            translated_subtitles.sort(key=lambda x: x["index"])

            # 生成SRT内容
            srt_content = ""
            for sub in translated_subtitles:
                srt_content += f"{sub['index'] + 1}\n"
                srt_content += f"{sub['start_time']} --> {sub['end_time']}\n"
                srt_content += f"{sub['text']}\n\n"

            # 保存翻译后的SRT文件
            target_srt_filename = f"translated_{target_language}_{os.path.splitext(source_subtitle_filename)[0]}.srt"
            target_srt_path = UPLOADS_DIR / target_srt_filename

            with open(target_srt_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)

            print(f"[批量翻译-{task_id}] 翻译完成，保存到: {target_srt_path}")

            # ===== 第一遍翻译后的质量检查和优化 =====
            print(f"\n[批量翻译-{task_id}] ===== 开始质量检查和优化 =====")
            translation_status[task_id]["message"] = "正在进行质量检查..."
            translation_status[task_id]["progress"] = 82

            from srt_parser import SRTParser
            from text_utils import check_translation_length, contains_chinese_characters, is_english_text
            from text_utils import extract_and_replace_chinese, batch_translate_english_to_kana, batch_translate_english_to_korean

            srt_parser = SRTParser()
            target_subtitles = srt_parser.parse_srt(target_srt_path)
            source_subtitles = srt_parser.parse_srt(source_srt_path)

            # 1. 检查译文长度和中文字符
            target_language_lower = target_language.lower()
            is_japanese = ('日' in target_language or 'ja' in target_language_lower)
            is_korean = ('韩' in target_language or 'ko' in target_language_lower or '한국' in target_language)
            is_french = ('法' in target_language or 'fr' in target_language_lower or 'français' in target_language_lower)
            is_german = ('德' in target_language or 'de' in target_language_lower or 'deutsch' in target_language_lower)
            is_spanish = ('西班牙' in target_language or 'es' in target_language_lower or 'español' in target_language_lower or 'spanish' in target_language_lower)

            if is_japanese or is_korean:
                max_ratio = 3
            elif is_french or is_german or is_spanish:
                max_ratio = 1.5
            else:
                max_ratio = 1.2

            too_long_items = []
            chinese_replacement_items = []

            for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
                source_text = source_sub["text"]
                target_text = target_sub["text"]

                is_too_long, source_len, target_len, ratio = check_translation_length(
                    source_text, target_text, target_language, max_ratio=max_ratio
                )
                has_chinese = contains_chinese_characters(target_text)

                if is_too_long:
                    too_long_items.append({
                        "index": idx,
                        "source": source_text,
                        "target": target_text,
                        "source_length": source_len,
                        "target_length": target_len,
                        "ratio": ratio,
                        "reason": "too_long"
                    })
                    print(f"  [长度检查] 第 {idx} 条译文过长: {target_len}/{source_len} = {ratio:.1f}x")
                elif has_chinese:
                    chinese_replacement_items.append({
                        "index": idx,
                        "target": target_text
                    })
                    print(f"  [汉字检查] 第 {idx} 条译文包含汉字: '{target_text}'")

            # 2. 重新翻译超长文本
            if too_long_items:
                print(f"\n[批量翻译-{task_id}] 发现 {len(too_long_items)} 条超长译文，批量重新翻译...")
                translation_status[task_id]["message"] = f"正在重新翻译 {len(too_long_items)} 条超长文本..."
                translation_status[task_id]["progress"] = 85

                retranslate_tasks = []
                for item in too_long_items:
                    retranslate_tasks.append({
                        "task_id": f"item-{item['index']}",
                        "source_text": item["source"],
                        "target_language": target_language,
                        "max_length": int(item["source_length"] * max_ratio * 0.8)
                    })

                retranslate_config = {
                    "tasks": retranslate_tasks,
                    "model": "qwen2.5:7b",
                    "output_file": target_srt_path
                }

                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                    json.dump(retranslate_config, f, ensure_ascii=False, indent=2)
                    retranslate_config_file = f.name

                try:
                    retranslate_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retranslate_ollama.py")
                    process = subprocess.Popen(
                        [ui_env_python, retranslate_script, retranslate_config_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding='utf-8',
                        bufsize=1
                    )

                    stdout_lines = []
                    for line in process.stdout:
                        print(line, end='', flush=True)
                        stdout_lines.append(line)

                    returncode = process.wait()
                    stdout = ''.join(stdout_lines)

                    if returncode == 0 and stdout:
                        import re
                        results_match = re.search(r'\[Results\](.*?)\[/Results\]', stdout, re.DOTALL)
                        if results_match:
                            results_json = results_match.group(1).strip()
                            retranslate_results = json.loads(results_json)

                            for result_item in retranslate_results:
                                idx = int(result_item["task_id"].split('-')[1])
                                target_subtitles[idx]["text"] = result_item["translation"]

                            srt_parser.save_srt(target_subtitles, target_srt_path)
                            print(f"✅ 成功重新翻译 {len(retranslate_results)} 条文本")
                except Exception as e:
                    print(f"⚠️ 重新翻译出错: {e}")
                finally:
                    if os.path.exists(retranslate_config_file):
                        os.remove(retranslate_config_file)

            # 3. 替换中文字符
            if chinese_replacement_items:
                print(f"\n[批量翻译-{task_id}] 发现 {len(chinese_replacement_items)} 条包含中文的译文，准备替换...")
                translation_status[task_id]["message"] = f"正在替换 {len(chinese_replacement_items)} 条译文中的中文..."
                translation_status[task_id]["progress"] = 90

                replaced_count = 0
                for item in chinese_replacement_items:
                    idx = item["index"]
                    original_text = item["target"]

                    replaced_text = extract_and_replace_chinese(
                        original_text,
                        target_language,
                        to_kana=is_japanese
                    )

                    if replaced_text != original_text:
                        target_subtitles[idx]["text"] = replaced_text
                        replaced_count += 1
                        print(f"  [{idx}] '{original_text}' -> '{replaced_text}'")

                if replaced_count > 0:
                    srt_parser.save_srt(target_subtitles, target_srt_path)
                    print(f"✅ 成功替换 {replaced_count} 条译文中的中文")

            # 4. 英文检测和转换（日语/韩语）
            if is_japanese or is_korean:
                print(f"\n[批量翻译-{task_id}] 检查纯英文句子...")
                translation_status[task_id]["message"] = "正在转换英文句子..."
                translation_status[task_id]["progress"] = 95

                # 重新读取最新的字幕（可能已被上一步修改）
                target_subtitles = srt_parser.parse_srt(target_srt_path)

                english_items = []
                for idx, target_sub in enumerate(target_subtitles):
                    target_text = target_sub.get("text", "").strip()
                    if is_english_text(target_text):
                        english_items.append({
                            "index": idx,
                            "text": target_text
                        })

                if english_items:
                    print(f"[批量翻译-{task_id}] 发现 {len(english_items)} 条纯英文句子，准备转换...")

                    english_texts = [item["text"] for item in english_items]
                    unique_english = list(dict.fromkeys(english_texts))

                    if is_japanese:
                        translation_map = batch_translate_english_to_kana(unique_english)
                    else:
                        translation_map = batch_translate_english_to_korean(unique_english)

                    converted_count = 0
                    for item in english_items:
                        idx = item["index"]
                        original_text = item["text"]
                        converted_text = translation_map.get(original_text, original_text)

                        if converted_text != original_text:
                            target_subtitles[idx]["text"] = converted_text
                            converted_count += 1
                            print(f"  [{idx}] '{original_text}' -> '{converted_text}'")

                    if converted_count > 0:
                        srt_parser.save_srt(target_subtitles, target_srt_path)
                        print(f"✅ 成功转换 {converted_count} 条纯英文句子")

            print(f"[批量翻译-{task_id}] ===== 质量检查和优化完成 =====\n")

            # 计算总耗时
            translation_elapsed = time.time() - translation_start_time
            print(f"[批量翻译-{task_id}] ✓ 翻译完成！总耗时: {translation_elapsed:.2f}秒")

            # 更新状态为完成
            translation_status[task_id]["status"] = "completed"
            translation_status[task_id]["message"] = "翻译完成"
            translation_status[task_id]["progress"] = 100
            translation_status[task_id]["target_srt_filename"] = target_srt_filename
            translation_status[task_id]["total_items"] = len(subtitles)
            translation_status[task_id]["elapsed_time"] = round(translation_elapsed, 2)
            translation_status[task_id]["avg_time"] = round(translation_elapsed / len(subtitles), 2) if len(subtitles) > 0 else 0

        finally:
            # 删除临时配置文件
            if os.path.exists(config_file):
                os.remove(config_file)

    except Exception as e:
        print(f"[批量翻译-{task_id}] 失败: {str(e)}")
        import traceback
        traceback.print_exc()

        translation_status[task_id]["status"] = "failed"
        translation_status[task_id]["message"] = f"翻译失败: {str(e)}"


@app.post("/voice-cloning/regenerate-segment")
async def regenerate_segment(request: RegenerateSegmentRequest):
    """重新生成单个字幕片段的克隆语音（使用不同的说话人音色）"""
    try:
        task_id = request.task_id
        segment_index = request.segment_index
        new_speaker_id = request.new_speaker_id

        # 检查任务是否存在
        if task_id not in voice_cloning_status:
            raise HTTPException(status_code=404, detail="任务不存在")

        status = voice_cloning_status[task_id]
        if status["status"] != "completed":
            raise HTTPException(status_code=400, detail="语音克隆任务尚未完成")

        # 获取克隆结果
        cloned_results = status.get("cloned_results", [])
        if segment_index < 0 or segment_index >= len(cloned_results):
            raise HTTPException(status_code=400, detail="片段索引无效")

        # 获取说话人参考数据
        speaker_references = status.get("speaker_references", {})
        if new_speaker_id not in speaker_references:
            raise HTTPException(status_code=400, detail=f"说话人 {new_speaker_id} 不存在")

        # 获取目标文本 - 优先使用新文本
        segment_data = cloned_results[segment_index]
        if request.new_target_text:
            target_text = request.new_target_text
            print(f"[重新生成片段] 使用新的译文: {target_text}")
        else:
            target_text = segment_data["target_text"]
            print(f"[重新生成片段] 使用原译文: {target_text}")

        # 查找音频提取缓存以获取audio_dir
        audio_dir = None
        print(f"[DEBUG] 查找 task_id={task_id} 的 audio_dir...")
        print(f"[DEBUG] audio_extraction_cache 中的 keys: {list(audio_extraction_cache.keys())}")

        for cache_key, cache_data in audio_extraction_cache.items():
            cache_task_id = cache_data.get("task_id")
            cache_audio_dir = cache_data.get("audio_dir", "")
            print(f"[DEBUG] 检查 cache_key={cache_key}, task_id={cache_task_id}, audio_dir={cache_audio_dir}")

            if cache_task_id == task_id or task_id in cache_audio_dir:
                audio_dir = cache_data["audio_dir"]
                print(f"[DEBUG] ✅ 找到匹配的 audio_dir: {audio_dir}")
                break

        if not audio_dir:
            # 如果找不到缓存，尝试使用默认路径
            audio_dir = f"audio_segments/{task_id}"
            print(f"[DEBUG] ⚠️  未找到缓存，使用默认路径: {audio_dir}")

            # 检查目录是否存在
            if not os.path.exists(audio_dir):
                print(f"[DEBUG] ❌ 默认路径不存在，尝试在 backend 目录下查找")
                backend_audio_dir = os.path.join("backend", audio_dir)
                if os.path.exists(backend_audio_dir):
                    audio_dir = backend_audio_dir
                    print(f"[DEBUG] ✅ 找到: {audio_dir}")
                else:
                    print(f"[DEBUG] ❌ backend 目录下也不存在")

        from fish_voice_cloner import FishVoiceCloner
        cloner = FishVoiceCloner()

        # 首先在所有可能的目录中查找已编码的文件
        print(f"[查找编码] 查找 speaker_{new_speaker_id} 的编码文件...")

        possible_dirs = [
            "audio_segments",
            "../audio_segments",
            "backend/audio_segments",
        ]

        # 可能的编码文件路径格式
        encoding_patterns = [
            ("encoded", f"speaker_{new_speaker_id}_codes.npy"),  # 新格式：批量编码
            (f"speaker_{new_speaker_id}_encoded", "fake.npy"),   # 旧格式：单独编码
        ]

        found_npy = None
        for base_dir in possible_dirs:
            if not os.path.exists(base_dir):
                continue

            # 遍历该目录下的所有任务文件夹
            for task_folder in os.listdir(base_dir):
                task_path = os.path.join(base_dir, task_folder)
                if not os.path.isdir(task_path):
                    continue

                # 尝试不同的编码文件路径格式
                for subdir, filename in encoding_patterns:
                    encoded_path = os.path.join(task_path, subdir, filename)
                    if os.path.exists(encoded_path):
                        found_npy = encoded_path
                        print(f"[查找编码] ✅ 找到编码文件: {encoded_path}")
                        break

                if found_npy:
                    break

            if found_npy:
                break

        # 如果找到了，直接使用（不复制，节省时间）
        if found_npy:
            fake_npy_path = found_npy
            print(f"[编码] ✅ 使用已存在的编码文件: {fake_npy_path}")
        else:
            # 如果没找到，需要重新编码
            print(f"[查找编码] ❌ 未找到已有编码，需要重新编码...")

            # 创建编码目录
            speaker_encoded_dir = os.path.join(audio_dir, f"speaker_{new_speaker_id}_encoded")
            os.makedirs(speaker_encoded_dir, exist_ok=True)

            ref_data = speaker_references[new_speaker_id]
            reference_audio_path = ref_data["reference_audio"]
            print(f"[编码] 参考音频: {reference_audio_path}")
            print(f"[编码] 输出目录: {speaker_encoded_dir}")

            fake_npy_path = cloner.encode_reference_audio(
                reference_audio_path,
                speaker_encoded_dir
            )

        # 获取参考文本
        ref_text = speaker_references[new_speaker_id]["reference_text"]

        # 生成输出路径（使用统一的文件名格式）
        cloned_audio_dir = status.get("cloned_audio_dir", os.path.join("exports", f"cloned_{task_id}"))
        audio_filename = f"segment_{segment_index}.wav"  # 统一使用简单格式
        output_audio = os.path.join(cloned_audio_dir, audio_filename)
        work_dir = os.path.join(audio_dir, f"regen_{segment_index}_{new_speaker_id}")
        os.makedirs(work_dir, exist_ok=True)

        print(f"重新生成片段 {segment_index}: 新说话人 {new_speaker_id}, 文本: {target_text[:30]}...")

        # 步骤2: 直接生成语义token（使用新说话人的编码）
        # 说话人改变时，即使文本相同也需要重新生成语义token
        print(f"[语义Token] 使用说话人{new_speaker_id}生成语义token...")
        codes_path = cloner.generate_semantic_tokens(
            target_text=target_text,
            ref_text=ref_text,
            fake_npy_path=fake_npy_path,
            output_dir=work_dir
        )

        # 步骤3: 解码为音频
        cloner.decode_to_audio(codes_path, output_audio)

        # 生成API路径
        api_path = f"/cloned-audio/{task_id}/{audio_filename}"

        # 更新克隆结果
        cloned_results[segment_index]["speaker_id"] = new_speaker_id
        cloned_results[segment_index]["cloned_audio_path"] = api_path
        voice_cloning_status[task_id]["cloned_results"] = cloned_results

        print(f"[重新生成] 片段 {segment_index} 已更新: speaker_id={new_speaker_id}, 文件已覆盖: {output_audio}")

        return {
            "success": True,
            "segment_index": segment_index,
            "new_speaker_id": new_speaker_id,
            "cloned_audio_path": api_path,
            "target_text": target_text
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"重新生成片段失败: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


def _replan_audio_timeline(
    cloned_results: List[Dict],
    cloned_audio_dir: str,
    optimized_files: Dict[int, str]
) -> Dict[int, Dict]:
    """
    重新规划音频时间轴，为超长片段借用相邻空闲时间

    Args:
        cloned_results: 克隆结果列表
        cloned_audio_dir: 克隆音频目录
        optimized_files: 已优化的文件字典

    Returns:
        {segment_index: {'actual_start': float, 'actual_end': float, 'borrowed_before': float, 'borrowed_after': float}}
    """
    import soundfile as sf

    replanned = {}

    # 构建所有片段的时间信息
    segments_info = []
    for idx, result in enumerate(cloned_results):
        # 优先使用优化后的文件
        if idx in optimized_files:
            audio_file_path = optimized_files[idx]
        else:
            audio_filename = f"segment_{idx}.wav"
            audio_file_path = os.path.join(cloned_audio_dir, audio_filename)

        if not os.path.exists(audio_file_path):
            continue

        try:
            audio_data, sr = sf.read(audio_file_path)
            actual_duration = len(audio_data) / sr

            start_time = result.get("start_time", 0)
            end_time = result.get("end_time", 0)
            target_duration = end_time - start_time

            segments_info.append({
                'index': idx,
                'start_time': start_time,
                'end_time': end_time,
                'target_duration': target_duration,
                'actual_duration': actual_duration,
                'audio_file_path': audio_file_path,
                'sr': sr
            })
        except Exception as e:
            print(f"[时间轴规划] 读取片段 {idx} 失败: {e}")
            continue

    # 按时间排序
    segments_info.sort(key=lambda x: x['start_time'])

    # 为每个超长片段计算可借用的时间
    for i, seg in enumerate(segments_info):
        excess = seg['actual_duration'] - seg['target_duration']

        # 使用小阈值判断，避免浮点误差导致不必要的调整
        if excess <= 0.001:
            continue  # 不超长，不需要调整

        idx = seg['index']

        # 计算最大可借用时间（原字幕时长的30%）
        max_borrow = seg['target_duration'] * 0.5

        # 计算前后的可用空闲时间
        gap_before = 0
        if i > 0:
            prev_seg = segments_info[i - 1]
            gap_before = seg['start_time'] - prev_seg['end_time']

        gap_after = 0
        if i < len(segments_info) - 1:
            next_seg = segments_info[i + 1]
            gap_after = next_seg['start_time'] - seg['end_time']

        # 优先策略：均匀借用，但不超过20%限制和可用间隙
        # 1. 先尝试平均分配
        half_excess = excess / 2
        borrow_before = min(gap_before, max_borrow, half_excess)
        borrow_after = min(gap_after, max_borrow, half_excess)

        # 2. 如果总借用不够，尝试从有剩余空间的一侧多借
        total_borrowed = borrow_before + borrow_after
        if total_borrowed < excess:
            remaining_needed = excess - total_borrowed

            # 前面还有可借用空间
            can_borrow_more_before = min(gap_before - borrow_before, max_borrow - borrow_before)
            # 后面还有可借用空间
            can_borrow_more_after = min(gap_after - borrow_after, max_borrow - borrow_after)

            if can_borrow_more_before > 0:
                extra_before = min(can_borrow_more_before, remaining_needed)
                borrow_before += extra_before
                remaining_needed -= extra_before

            if remaining_needed > 0 and can_borrow_more_after > 0:
                extra_after = min(can_borrow_more_after, remaining_needed)
                borrow_after += extra_after

        # 记录调整后的实际时间（只有真正借用了时间才记录）
        if borrow_before > 0.001 or borrow_after > 0.001:  # 使用小阈值避免浮点误差
            actual_start = seg['start_time'] - borrow_before
            actual_end = seg['end_time'] + borrow_after
            replanned[idx] = {
                'actual_start': actual_start,
                'actual_end': actual_end,
                'actual_duration': actual_end - actual_start,
                'borrowed_before': borrow_before,
                'borrowed_after': borrow_after,
                'original_start': seg['start_time'],
                'original_end': seg['end_time']
            }

    return replanned


@app.post("/voice-cloning/stitch-audio")
async def stitch_cloned_audio(request: StitchAudioRequest):
    """
    拼接所有克隆的音频片段为完整音频，处理时长不匹配的情况
    """
    try:
        import soundfile as sf
        import numpy as np
        import time

        # 记录开始时间
        start_time = time.time()

        task_id = request.task_id

        # 检查任务是否存在
        if task_id not in voice_cloning_status:
            raise HTTPException(status_code=404, detail="任务不存在")

        status = voice_cloning_status[task_id]
        cloned_results = status.get("cloned_results", [])

        if not cloned_results:
            raise HTTPException(status_code=400, detail="没有可拼接的音频片段")

        # 获取克隆音频目录
        cloned_audio_dir = status.get("cloned_audio_dir", os.path.join("exports", f"cloned_{task_id}"))

        print(f"[音频拼接] 开始拼接任务 {task_id} 的音频片段...")

        # 步骤1: 音频优化（VAD 去除静音）
        from audio_optimizer import AudioOptimizer

        print(f"[音频优化] 检查是否有需要优化的片段...")
        optimizer = AudioOptimizer()
        optimized_files = optimizer.optimize_segments_for_stitching(
            cloned_results=cloned_results,
            cloned_audio_dir=cloned_audio_dir,
            threshold_ratio=1.1  # 超过目标长度10%的片段将被优化
        )

        if optimized_files:
            print(f"[音频优化] 成功优化 {len(optimized_files)} 个片段")
        else:
            print(f"[音频优化] 无需优化")

        # 步骤2: 时间轴重新规划（VAD后仍超长的片段尝试借用相邻空闲时间）
        print(f"[时间轴规划] 开始规划音频时间轴...")
        replanned_segments = _replan_audio_timeline(
            cloned_results=cloned_results,
            cloned_audio_dir=cloned_audio_dir,
            optimized_files=optimized_files
        )
        print(f"[时间轴规划] 完成，共调整 {len(replanned_segments)} 个片段的时间轴")

        # 获取原视频文件路径，用于提取原始音频音量
        video_file = status.get("video_file")
        original_audio_volumes = {}

        if video_file:
            video_path = os.path.join("uploads", video_file)
            if os.path.exists(video_path):
                try:
                    import subprocess
                    temp_audio_path = os.path.join("exports", f"temp_original_audio_{task_id}.wav")
                    cmd = [
                        'ffmpeg', '-i', video_path,
                        '-vn', '-acodec', 'pcm_s16le',
                        '-ar', '44100', '-ac', '1',
                        '-y', temp_audio_path
                    ]
                    subprocess.run(cmd, capture_output=True, check=True)

                    original_audio, orig_sr = sf.read(temp_audio_path)

                    for idx, result in enumerate(cloned_results):
                        start_time = result.get("start_time", 0)
                        end_time = result.get("end_time", 0)
                        start_sample = int(start_time * orig_sr)
                        end_sample = int(end_time * orig_sr)

                        if end_sample <= len(original_audio):
                            segment_audio = original_audio[start_sample:end_sample]
                            rms = np.sqrt(np.mean(segment_audio**2))
                            original_audio_volumes[idx] = rms

                    if os.path.exists(temp_audio_path):
                        os.remove(temp_audio_path)

                except Exception as e:
                    print(f"[音频拼接] 警告: 无法提取原视频音频音量: {e}")

        # 读取所有音频片段
        segments_with_timing = []
        sample_rate = None

        for idx, result in enumerate(cloned_results):
            cloned_audio_path = result.get("cloned_audio_path")
            if not cloned_audio_path:
                print(f"[音频拼接] 跳过片段 {idx}: 没有克隆音频")
                continue

            # 优先使用优化后的文件路径，如果没有则使用原始文件
            if idx in optimized_files:
                audio_file_path = optimized_files[idx]
            else:
                # 构建实际文件路径
                audio_filename = f"segment_{idx}.wav"
                audio_file_path = os.path.join(cloned_audio_dir, audio_filename)

            if not os.path.exists(audio_file_path):
                print(f"[音频拼接] 跳过片段 {idx}: 文件不存在 {audio_file_path}")
                continue

            # 读取音频
            audio_data, sr = sf.read(audio_file_path)
            if sample_rate is None:
                sample_rate = sr
            elif sr != sample_rate:
                print(f"[音频拼接] 警告: 片段 {idx} 采样率不一致 ({sr} vs {sample_rate})")

            # 获取原始时间戳
            start_time = result.get("start_time", 0)
            end_time = result.get("end_time", 0)
            timestamp_duration = end_time - start_time

            # 计算实际音频时长
            actual_duration = len(audio_data) / sample_rate

            segments_with_timing.append({
                "index": idx,
                "audio_data": audio_data,
                "start_time": start_time,
                "end_time": end_time,
                "timestamp_duration": timestamp_duration,
                "actual_duration": actual_duration,
                "original_volume": original_audio_volumes.get(idx, None)
            })

        if not segments_with_timing:
            raise HTTPException(status_code=400, detail="没有有效的音频片段可拼接")

        # 按开始时间排序
        segments_with_timing.sort(key=lambda x: x["start_time"])

        # 处理每个片段的时长和音量
        processed_segments = []

        for seg in segments_with_timing:
            audio_data = seg["audio_data"]
            timestamp_duration = seg["timestamp_duration"]
            actual_duration = seg["actual_duration"]
            original_volume = seg.get("original_volume")
            idx = seg["index"]

            # 检查是否有重新规划的时间轴
            if idx in replanned_segments:
                replan_info = replanned_segments[idx]
                # 使用重新规划的时长
                target_duration = replan_info['actual_duration']
                actual_start = replan_info['actual_start']
                actual_end = replan_info['actual_end']

                print(f"[音频拼接] 片段 {idx}: 使用重新规划的时间轴 {actual_start:.3f}s - {actual_end:.3f}s")
            else:
                # 使用原始时间
                target_duration = timestamp_duration
                actual_start = seg["start_time"]
                actual_end = seg["end_time"]

            target_samples = int(target_duration * sample_rate)
            actual_samples = len(audio_data)

            if actual_samples > target_samples:
                # 情况1: 音频过长，从两端等比例裁剪
                excess_samples = actual_samples - target_samples
                trim_left = excess_samples // 2
                trim_right = excess_samples - trim_left
                processed_audio = audio_data[trim_left:actual_samples - trim_right]

            elif actual_samples < target_samples:
                # 情况2: 音频过短，居中并两端补零
                pad_samples = target_samples - actual_samples
                pad_left = pad_samples // 2
                pad_right = pad_samples - pad_left
                processed_audio = np.pad(audio_data, (pad_left, pad_right), mode='constant', constant_values=0)

            else:
                # 情况3: 时长完全匹配
                processed_audio = audio_data

            # 调整音量以匹配原视频
            if original_volume is not None and original_volume > 1e-6:
                cloned_rms = np.sqrt(np.mean(processed_audio**2))
                if cloned_rms > 1e-6:
                    volume_ratio = original_volume / cloned_rms
                    volume_ratio = np.clip(volume_ratio, 0.1, 10.0)
                    processed_audio = processed_audio * volume_ratio

            processed_segments.append({
                "audio": processed_audio,
                "start_time": actual_start,
                "end_time": actual_end
            })

        # 拼接所有片段，中间填充静音
        final_audio_parts = []
        last_end_time = 0

        for seg in processed_segments:
            # 计算与上一段的间隙
            gap_duration = seg["start_time"] - last_end_time

            if gap_duration > 0.001:  # 大于1ms才填充静音
                gap_samples = int(gap_duration * sample_rate)
                silence = np.zeros(gap_samples, dtype=audio_data.dtype)
                final_audio_parts.append(silence)

            final_audio_parts.append(seg["audio"])
            last_end_time = seg["end_time"]

        # 合并所有部分
        if not final_audio_parts:
            raise ValueError("没有音频部分可以拼接")

        final_audio = np.concatenate(final_audio_parts)

        # 数据验证和清理
        has_nan = np.isnan(final_audio).any()
        has_inf = np.isinf(final_audio).any()

        if has_nan or has_inf:
            print(f"[音频拼接] 警告: 音频数据包含 NaN 或 Inf，进行清理")
            final_audio = np.nan_to_num(final_audio, nan=0.0, posinf=1.0, neginf=-1.0)

        # 转换为 int16 PCM 格式（浏览器最兼容的格式）
        # 归一化到 [-1, 1] 范围
        max_val = np.max(np.abs(final_audio))
        if max_val > 0:
            final_audio = final_audio / max_val
        # 转换为 int16 (-32768 to 32767)
        final_audio_int16 = (final_audio * 32767).astype(np.int16)

        # 保存最终音频
        stitched_filename = f"stitched_{task_id}.wav"
        stitched_path = os.path.join(EXPORTS_DIR, stitched_filename)

        # 使用 scipy.io.wavfile 保存，生成标准 WAV 文件
        from scipy.io import wavfile
        wavfile.write(stitched_path, sample_rate, final_audio_int16)

        # 计算总时长
        total_duration = len(final_audio) / sample_rate

        print(f"[音频拼接] 完成! 总时长: {total_duration:.3f}s")

        # 更新重新规划的片段时间到 cloned_results（用于前端时间轴显示）
        for idx, replan_info in replanned_segments.items():
            if idx < len(cloned_results):
                # 保存重新规划的实际播放时间
                cloned_results[idx]['actual_start_time'] = replan_info['actual_start']
                cloned_results[idx]['actual_end_time'] = replan_info['actual_end']
                print(f"[音频拼接] 更新片段 {idx} 时间轴: {replan_info['actual_start']:.3f}s - {replan_info['actual_end']:.3f}s")

        # 计算总耗时
        end_time = time.time()
        stitch_duration = end_time - start_time

        # 格式化时间显示（使用与语音克隆相同的格式函数）
        def format_duration(seconds):
            """将秒数格式化为易读的时间字符串"""
            if seconds < 60:
                return f"{seconds:.1f}秒"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}分{secs}秒"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}小时{minutes}分钟"

        duration_str = format_duration(stitch_duration)

        # 更新状态
        voice_cloning_status[task_id]["stitched_audio_path"] = f"/exports/{stitched_filename}"
        voice_cloning_status[task_id]["cloned_results"] = cloned_results  # 更新结果

        print(f"\n✅ 音频拼接任务 {task_id} 成功完成！")
        print(f"⏱️  总耗时: {duration_str}")

        return {
            "success": True,
            "stitched_audio_path": f"/exports/{stitched_filename}",
            "total_duration": total_duration,
            "segments_count": len(processed_segments),
            "message": f"音频拼接完成 (耗时: {duration_str})",
            "replanned_segments": len(replanned_segments),  # 返回重新规划的片段数量
            "stitch_duration": stitch_duration,  # 原始秒数
            "duration_str": duration_str  # 格式化的时间字符串
        }

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"[音频拼接] 失败: {error_detail}")
        raise HTTPException(status_code=500, detail=str(e))


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