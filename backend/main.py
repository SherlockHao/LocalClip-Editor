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

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
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
            str(target_subtitle_path)
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
    target_subtitle_path: str
):
    """后台执行语音克隆处理"""
    import time
    start_time = time.time()  # 记录开始时间

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
            audio_dir = os.path.join("..", "audio_segments", task_id)
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

            # 5. MOS打分（使用 NISQA）
            mos_scorer = NISQAScorer()
            scored_segments = mos_scorer.score_speaker_audios(audio_dir, speaker_segments)
            print(f"已完成MOS评分（NISQA）")
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
        print("[Voice Clone] Using simple batch cloner (based on batch_inference.py)")
        from fish_simple_cloner import SimpleFishCloner
        batch_cloner = SimpleFishCloner()

        # 9. 批量编码所有说话人的参考音频
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在批量编码说话人参考音频...",
            "progress": 70
        }
        await asyncio.sleep(0.5)

        encode_output_dir = os.path.join(audio_dir, "encoded")
        os.makedirs(encode_output_dir, exist_ok=True)

        print(f"\n🚀 批量编码 {len(speaker_references)} 个说话人的参考音频...")
        speaker_npy_files = batch_cloner.batch_encode_speakers(
            speaker_references,
            encode_output_dir
        )

        # 10. 读取目标语言字幕
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在读取目标语言字幕...",
            "progress": 75
        }
        await asyncio.sleep(0.5)

        from srt_parser import SRTParser
        srt_parser = SRTParser()
        target_subtitles = srt_parser.parse_srt(target_subtitle_path)
        source_subtitles = srt_parser.parse_srt(source_subtitle_path)

        # 10.5 验证译文长度并批量重新翻译超长文本
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在验证译文长度...",
            "progress": 76
        }
        await asyncio.sleep(0.5)

        from text_utils import check_translation_length

        # 检查每句译文长度
        too_long_items = []
        for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
            source_text = source_sub["text"]
            target_text = target_sub["text"]

            is_too_long, source_len, target_len, ratio = check_translation_length(
                source_text, target_text, target_language, max_ratio=1.2
            )

            if is_too_long:
                too_long_items.append({
                    "index": idx,
                    "source": source_text,
                    "target": target_text,
                    "source_length": source_len,
                    "target_length": target_len,
                    "ratio": ratio
                })

        # 如果有超长译文，进行批量重新翻译
        if too_long_items:
            print(f"\n⚠️  发现 {len(too_long_items)} 条超长译文，准备批量重新翻译...")

            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": f"正在批量重新翻译 {len(too_long_items)} 条超长文本...",
                "progress": 77
            }
            await asyncio.sleep(0.5)

            # 准备重新翻译任务
            import tempfile
            import json
            import subprocess

            retranslate_tasks = []
            for item in too_long_items:
                retranslate_tasks.append({
                    "task_id": f"retrans-{item['index']}",
                    "source": item["source"],
                    "target_language": target_language
                })

            # 写入配置文件
            config_file = os.path.join(audio_dir, "retranslate_config.json")

            # 获取模型路径
            # 模型在 C:\workspace\ai_editing\models\Qwen3-1.7B
            # 从 backend 目录向上 4 级到达 ai_editing 目录
            backend_dir = os.path.dirname(os.path.abspath(__file__))  # backend
            localclip_dir = os.path.dirname(backend_dir)  # LocalClip-Editor
            workspace_dir = os.path.dirname(localclip_dir)  # workspace
            ai_editing_dir = os.path.dirname(workspace_dir)  # ai_editing
            model_path = os.path.join(ai_editing_dir, "models", "Qwen3-1.7B")

            retranslate_config = {
                "tasks": retranslate_tasks,
                "model_path": model_path,
                "num_processes": 1  # 使用单进程，避免显存冲突
            }

            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(retranslate_config, f, ensure_ascii=False, indent=2)

            # 调用批量重新翻译脚本
            # 使用 qwen_inference conda 环境
            qwen_env_python = os.environ.get("QWEN_INFERENCE_PYTHON")
            if not qwen_env_python:
                # 默认路径
                import platform
                if platform.system() == "Windows":
                    qwen_env_python = r"C:\Users\7\miniconda3\envs\qwen_inference\python.exe"
                else:
                    qwen_env_python = os.path.expanduser("~/miniconda3/envs/qwen_inference/bin/python")

            batch_retranslate_script = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "batch_retranslate.py"
            )

            print(f"[Retranslate] 使用 Python: {qwen_env_python}")
            print(f"[Retranslate] 脚本: {batch_retranslate_script}")
            print(f"[Retranslate] 配置: {config_file}")
            print(f"[Retranslate] 模型路径: {model_path}")

            # 检查 Python 环境和模型是否存在
            if not os.path.exists(qwen_env_python):
                print(f"⚠️  Qwen Python 环境不存在: {qwen_env_python}")
                print(f"使用原译文继续...")
            elif not os.path.exists(model_path):
                print(f"⚠️  模型路径不存在: {model_path}")
                print(f"使用原译文继续...")
            else:
                try:
                    print(f"[Retranslate] 启动批量重新翻译进程...")

                    # 使用 Popen，不指定编码以避免 UnicodeDecodeError
                    process = subprocess.Popen(
                        [qwen_env_python, batch_retranslate_script, config_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        # 使用 bytes 模式，手动解码
                    )

                    # 读取输出（带超时）
                    try:
                        stdout_bytes, stderr_bytes = process.communicate(timeout=600)
                        returncode = process.returncode

                        # 手动解码，使用 errors='replace' 避免解码错误
                        stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
                        stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""

                    except subprocess.TimeoutExpired:
                        process.kill()
                        print("⚠️  重新翻译超时，使用原译文继续...")
                        stdout, stderr = "", ""
                        returncode = -1

                    # 打印 stderr（如果有，忽略空白）
                    if stderr and stderr.strip():
                        # 过滤掉 UnicodeDecodeError 相关的无关警告
                        stderr_lines = stderr.strip().split('\n')
                        filtered_stderr = '\n'.join([line for line in stderr_lines if 'UnicodeDecodeError' not in line and '_readerthread' not in line])
                        if filtered_stderr:
                            print(f"[Retranslate] stderr:\n{filtered_stderr}")

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

        # 11. 准备批量生成任务
        voice_cloning_status[task_id] = {
            "status": "processing",
            "message": "正在批量生成克隆语音...",
            "progress": 80
        }
        await asyncio.sleep(0.5)

        cloned_audio_dir = os.path.join("exports", f"cloned_{task_id}")
        os.makedirs(cloned_audio_dir, exist_ok=True)

        # 准备任务列表
        tasks = []
        cloned_results = []

        print(f"\n[DEBUG] 准备任务列表，target_subtitles 中前3条文本:")
        for i in range(min(3, len(target_subtitles))):
            print(f"  [{i}] {target_subtitles[i]['text']}")

        for idx, (speaker_id, target_sub) in enumerate(zip(speaker_labels, target_subtitles)):
            target_text = target_sub["text"]

            if speaker_id is None or speaker_id not in speaker_npy_files:
                # 没有分配说话人或说话人编码失败的片段，记录但不生成
                cloned_results.append({
                    "index": idx,
                    "speaker_id": speaker_id,
                    "target_text": target_text,
                    "cloned_audio_path": None
                })
            else:
                # 添加到批量生成任务
                tasks.append({
                    "speaker_id": speaker_id,
                    "target_text": target_text,
                    "segment_index": idx
                })

        # 批量生成所有语音
        print(f"\n🚀 批量生成 {len(tasks)} 个语音片段...")
        # 将生成脚本保存到audio_dir下的scripts目录，避免触发uvicorn reload
        script_dir = os.path.join(audio_dir, "scripts")
        generated_audio_files = batch_cloner.batch_generate_audio(
            tasks,
            speaker_npy_files,
            speaker_references,
            cloned_audio_dir,
            script_dir=script_dir
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
                    "cloned_audio_path": api_path
                })
            else:
                cloned_results.append({
                    "index": segment_index,
                    "speaker_id": task["speaker_id"],
                    "target_text": task["target_text"],
                    "cloned_audio_path": None,
                    "error": "生成失败"
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
            "cloned_audio_dir": cloned_audio_dir,
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

    return voice_cloning_status[task_id]


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
        }
    )


class RegenerateSegmentRequest(BaseModel):
    task_id: str
    segment_index: int
    new_speaker_id: int


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

        # 获取目标文本
        segment_data = cloned_results[segment_index]
        target_text = segment_data["target_text"]

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

        found_npy = None
        for base_dir in possible_dirs:
            if not os.path.exists(base_dir):
                continue

            # 遍历该目录下的所有任务文件夹
            for task_folder in os.listdir(base_dir):
                task_path = os.path.join(base_dir, task_folder)
                if not os.path.isdir(task_path):
                    continue

                # 检查该任务文件夹中是否有此说话人的编码
                encoded_path = os.path.join(task_path, f"speaker_{new_speaker_id}_encoded", "fake.npy")
                if os.path.exists(encoded_path):
                    found_npy = encoded_path
                    print(f"[查找编码] ✅ 找到编码文件: {encoded_path}")
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

        # 步骤2: 生成语义token
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