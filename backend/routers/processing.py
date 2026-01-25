# -*- coding: utf-8 -*-
"""
任务处理路由 - 说话人识别、翻译、语音克隆等处理流程
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio
import os
import sys
import json

# 确保 speaker_diarization_processing 模块路径在 sys.path 中
_speaker_diarization_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'speaker_diarization_processing')
if _speaker_diarization_dir not in sys.path:
    sys.path.insert(0, _speaker_diarization_dir)

from database import get_db
from models.task import Task
from progress_manager import update_task_progress, mark_task_failed, mark_task_completed
from path_utils import task_path_manager
from running_task_tracker import running_task_tracker

router = APIRouter(prefix="/api/tasks", tags=["processing"])


# ==================== Pydantic 模型 ====================

class SpeakerDiarizationRequest(BaseModel):
    """说话人识别请求"""
    pass  # 不需要额外参数，从任务中获取


class TranslationRequest(BaseModel):
    """翻译请求"""
    pass  # 不需要额外参数，从任务中获取


class VoiceCloningRequest(BaseModel):
    """语音克隆请求"""
    speaker_voice_mapping: Dict[str, str]  # {"Speaker 0": "voice1", "Speaker 1": "voice2"}


class ExportRequest(BaseModel):
    """导出请求"""
    pass  # 不需要额外参数


class StitchAudioRequest(BaseModel):
    """音频拼接请求"""
    pass  # 不需要额外参数，从任务中获取


class RegenerateSegmentRequest(BaseModel):
    """重新生成单个片段请求"""
    segment_index: int
    new_speaker_id: int
    new_text: Optional[str] = None  # 新的原文（如果修改了）
    new_target_text: Optional[str] = None  # 新的译文（如果修改了）


# ==================== 说话人识别 API ====================

@router.post("/{task_id}/speaker-diarization")
async def process_speaker_diarization(
    task_id: str,
    request: SpeakerDiarizationRequest,
    db: Session = Depends(get_db)
):
    """
    启动说话人识别处理

    工作流程:
    1. 从视频提取音频
    2. 根据字幕切分音频片段
    3. 提取说话人特征
    4. 聚类识别说话人
    """
    print(f"\n[说话人识别] 收到请求: {task_id}", flush=True)

    # 验证任务存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证文件存在
    video_path = task_path_manager.get_input_video_path(task_id, task.video_filename)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail=f"视频文件不存在: {video_path}")

    # 检查是否有原始字幕
    subtitle_path = task_path_manager.get_source_subtitle_path(task_id)
    if not subtitle_path.exists():
        raise HTTPException(
            status_code=400,
            detail="请先上传原始字幕文件。说话人识别需要字幕来切分音频。"
        )

    print(f"[说话人识别] 视频路径: {video_path}", flush=True)
    print(f"[说话人识别] 字幕路径: {subtitle_path}", flush=True)

    # 检查是否有正在运行的任务
    if running_task_tracker.has_running_task(task_id):
        running = running_task_tracker.get_running_task(task_id)
        raise HTTPException(
            status_code=409,
            detail=f"任务 {task_id} 已有正在运行的任务: {running.language}/{running.stage}"
        )

    # 注册运行任务
    running_task_tracker.start_task(task_id, "default", "speaker_diarization")

    # 启动后台任务，并添加异常回调以捕获错误
    task = asyncio.create_task(run_speaker_diarization_task(
        task_id=task_id,
        video_path=str(video_path),
        subtitle_path=str(subtitle_path)
    ))

    # 添加异常回调，确保异常被打印
    def handle_task_exception(t):
        if t.exception():
            import traceback
            print(f"[说话人识别] ❌ 后台任务异常: {t.exception()}", flush=True)
            traceback.print_exception(type(t.exception()), t.exception(), t.exception().__traceback__)

    task.add_done_callback(handle_task_exception)

    return {
        "message": "说话人识别任务已启动",
        "task_id": task_id
    }


@router.get("/{task_id}/speaker-diarization/status")
async def get_speaker_diarization_status(
    task_id: str,
    db: Session = Depends(get_db)
):
    """
    获取说话人识别任务的状态
    """
    import json

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 从 language_status 中获取 speaker_diarization 状态
    language_status = task.language_status or {}
    default_status = language_status.get("default", {})
    speaker_status = default_status.get("speaker_diarization", {})

    status = speaker_status.get("status", "pending")
    response = {
        "task_id": task_id,
        "status": status,
        "progress": speaker_status.get("progress", 0),
        "message": speaker_status.get("message", "等待中"),
        "updated_at": speaker_status.get("updated_at")
    }

    # 如果已完成，返回说话人标签数据
    if status == "completed":
        speaker_data_path = task_path_manager.get_speaker_data_path(task_id)
        if speaker_data_path.exists():
            try:
                with open(speaker_data_path, 'r', encoding='utf-8') as f:
                    speaker_data = json.load(f)
                response["speaker_labels"] = speaker_data.get("speaker_labels", [])
                response["unique_speakers"] = speaker_data.get("num_speakers", 0)
                response["speaker_name_mapping"] = speaker_data.get("speaker_name_mapping", {})
                response["gender_stats"] = speaker_data.get("gender_stats", {})
                response["gender_dict"] = speaker_data.get("gender_dict", {})
                response["duration_str"] = speaker_data.get("duration_str", "")
                response["total_duration"] = speaker_data.get("total_duration", 0)
            except Exception as e:
                print(f"[说话人识别状态] 读取 speaker_data 失败: {e}", flush=True)

    return response


async def run_speaker_diarization_task(
    task_id: str,
    video_path: str,
    subtitle_path: str
):
    """
    后台执行说话人识别任务

    完整流程包括:
    1. 音频切分 (0-25%)
    2. 说话人特征提取和聚类 (25-60%)
    3. MOS 音频质量评分 (60-80%)
    4. 性别识别 (80-100%)
    """
    import time
    import json
    start_time = time.time()

    try:
        print(f"\n========== 开始说话人识别任务: {task_id} ==========", flush=True)
        print(f"视频路径: {video_path}", flush=True)
        print(f"字幕路径: {subtitle_path}", flush=True)

        # 导入现有的处理模块
        from audio_extraction import AudioExtractor
        from embedding_extraction import SpeakerEmbeddingExtractor
        from cluster_processor import SpeakerClusterer
        from srt_parser import SRTParser

        # ==================== 任务1: 音频切分 (0-25%) ====================
        await update_task_progress(
            task_id, "default", "speaker_diarization",
            5, "音频切分中...", "processing"
        )

        # 使用 AudioExtractor 直接从视频按字幕时间段提取音频
        segments_dir = task_path_manager.get_speaker_segments_dir(task_id)
        extractor = AudioExtractor(cache_dir=str(segments_dir))
        audio_paths = extractor.extract_audio_segments(video_path, subtitle_path)

        print(f"[说话人识别] 提取了 {len(audio_paths)} 个音频片段", flush=True)

        # ==================== 任务2: 说话人特征提取和聚类 (25-60%) ====================
        await update_task_progress(
            task_id, "default", "speaker_diarization",
            30, "说话人特征提取中...", "processing"
        )

        # 提取嵌入向量
        embedding_extractor = SpeakerEmbeddingExtractor(offline_mode=True)
        embeddings = embedding_extractor.extract_embeddings(audio_paths)

        print(f"[说话人识别] 提取了 {len([e for e in embeddings if e is not None])} 个有效特征", flush=True)

        await update_task_progress(
            task_id, "default", "speaker_diarization",
            55, "说话人聚类分析中...", "processing"
        )

        # 获取视频时长以确定聚类数量
        import subprocess
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
                capture_output=True, text=True, timeout=10
            )
            video_duration = float(result.stdout.strip())
            print(f"[说话人识别] 视频时长: {video_duration:.2f}秒 ({video_duration/60:.2f}分钟)", flush=True)
        except Exception as e:
            print(f"[说话人识别] 无法获取视频时长: {e}，使用默认聚类数 5", flush=True)
            video_duration = 300  # 默认5分钟

        # 根据视频时长计算说话人聚类数量
        duration_minutes = video_duration / 60
        if duration_minutes <= 2:
            n_clusters = 4
        elif duration_minutes <= 5:
            n_clusters = 5
        elif duration_minutes <= 10:
            n_clusters = 6
        elif duration_minutes <= 20:
            n_clusters = 7
        else:
            n_clusters = 8

        print(f"[说话人识别] 根据视频时长 {duration_minutes:.2f}分钟，设置聚类数量为 {n_clusters}", flush=True)

        # 聚类识别说话人
        clusterer = SpeakerClusterer(n_clusters=n_clusters, distance_threshold=None)
        speaker_labels = clusterer.cluster_embeddings(embeddings)
        num_speakers = clusterer.get_unique_speakers_count(speaker_labels)

        print(f"[说话人识别] 识别到 {num_speakers} 个说话人", flush=True)

        # ==================== 任务3: MOS音频质量评分 (60-80%) ====================
        await update_task_progress(
            task_id, "default", "speaker_diarization",
            65, "音频质量评估中...", "processing"
        )

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
        scored_segments = mos_scorer.score_speaker_audios(str(segments_dir), speaker_segments)

        print(f"[说话人识别] 已完成MOS评分（NISQA），共 {len(scored_segments)} 个说话人", flush=True)

        # ==================== 任务4: 性别识别 (80-100%) ====================
        await update_task_progress(
            task_id, "default", "speaker_diarization",
            85, "性别识别分析中...", "processing"
        )

        # 性别识别
        from gender_classifier import GenderClassifier, rename_speakers_by_gender
        gender_classifier = GenderClassifier()

        # 使用静音切割预处理，临时文件保存在segments_dir
        gender_dict = gender_classifier.classify_speakers(
            scored_segments,
            min_duration=2.0,
            use_silence_trimming=True,
            min_final_duration=1.5,
            temp_dir=str(segments_dir)
        )

        # 根据性别和出现次数重新命名说话人
        print(f"[说话人识别] 根据性别和出现次数重新命名说话人...", flush=True)
        speaker_name_mapping, gender_stats = rename_speakers_by_gender(speaker_labels, gender_dict)

        print(f"[说话人识别] 性别统计: 男性 {gender_stats['male']} 人, 女性 {gender_stats['female']} 人", flush=True)

        # ==================== 保存结果 ====================
        await update_task_progress(
            task_id, "default", "speaker_diarization",
            95, "保存结果中...", "processing"
        )

        # 解析字幕以获取文本信息
        srt_parser = SRTParser()
        subtitles = srt_parser.parse_srt(subtitle_path)

        # 构建 audio_segments 列表
        audio_segments = []
        for i, (audio_path, subtitle) in enumerate(zip(audio_paths, subtitles)):
            audio_segments.append({
                'filename': os.path.basename(audio_path),
                'path': audio_path,
                'subtitle_index': i,
                'text': subtitle['text']
            })

        # 计算总耗时
        end_time = time.time()
        total_duration = end_time - start_time

        # 格式化时间显示
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

        duration_str = format_duration(total_duration)

        # 保存完整结果
        speaker_data = {
            'segments': audio_segments,
            'speaker_labels': speaker_labels,
            'num_speakers': num_speakers,
            'scored_segments': scored_segments,
            'gender_dict': gender_dict,
            'speaker_name_mapping': speaker_name_mapping,
            'gender_stats': gender_stats,
            'total_duration': total_duration,
            'duration_str': duration_str,
            'audio_dir': str(segments_dir)
        }

        speaker_data_path = task_path_manager.get_speaker_data_path(task_id)
        with open(speaker_data_path, 'w', encoding='utf-8') as f:
            json.dump(speaker_data, f, ensure_ascii=False, indent=2)

        await mark_task_completed(task_id, "default", "speaker_diarization")
        # 完成时停止追踪
        running_task_tracker.complete_task(task_id, "default", "speaker_diarization")
        print(f"[说话人识别] ✅ 任务完成: {task_id}", flush=True)
        print(f"[说话人识别] ⏱️  总耗时: {duration_str}", flush=True)

    except Exception as e:
        # 计算失败时的耗时
        end_time = time.time()
        total_duration = end_time - start_time
        duration_str = f"{total_duration:.1f}秒"

        print(f"[说话人识别] ❌ 任务失败: {str(e)}", flush=True)
        print(f"[说话人识别] ⏱️  失败前耗时: {duration_str}", flush=True)
        import traceback
        traceback.print_exc()
        await mark_task_failed(task_id, "default", "speaker_diarization", str(e))
        # 失败时停止追踪
        running_task_tracker.fail_task(task_id, str(e))


# ==================== 翻译 API ====================

@router.post("/{task_id}/languages/{language}/translate")
async def process_translation(
    task_id: str,
    language: str,
    request: TranslationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    启动翻译处理

    Args:
        task_id: 任务 ID
        language: 目标语言 (English, Korean, Japanese, etc.)
    """
    print(f"\n[翻译] 收到请求: {task_id} -> {language}", flush=True)

    # 验证任务存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证原始字幕存在
    source_subtitle_path = task_path_manager.get_source_subtitle_path(task_id)
    if not source_subtitle_path.exists():
        raise HTTPException(status_code=400, detail="原始字幕文件不存在")

    # 检查是否有正在运行的任务
    if running_task_tracker.has_running_task(task_id):
        running = running_task_tracker.get_running_task(task_id)
        raise HTTPException(
            status_code=409,
            detail=f"任务 {task_id} 已有正在运行的任务: {running.language}/{running.stage}"
        )

    # 添加到目标语言列表
    config = task.config or {}
    target_languages = config.get('target_languages', [])
    if language not in target_languages:
        target_languages.append(language)
        config['target_languages'] = target_languages
        task.config = config
        db.commit()

    # 注册运行任务
    running_task_tracker.start_task(task_id, language, "translation")

    # 启动后台任务
    background_tasks.add_task(
        run_translation_task,
        task_id,
        language,
        str(source_subtitle_path)
    )

    return {
        "message": f"翻译任务已启动: {language}",
        "task_id": task_id,
        "language": language
    }


async def run_translation_task(
    task_id: str,
    target_language: str,
    source_subtitle_path: str
):
    """
    后台执行翻译任务

    使用 translation_service 模块进行翻译
    """
    try:
        print(f"\n========== 开始翻译任务: {task_id} -> {target_language} ==========", flush=True)

        await update_task_progress(
            task_id, target_language, "translation",
            0, "正在准备翻译...", "processing"
        )

        # 获取翻译目标路径
        translated_subtitle_path = task_path_manager.get_translated_subtitle_path(
            task_id, target_language
        )

        # 导入翻译服务
        from translation_service import batch_translate_subtitles
        from pathlib import Path

        # 定义进度回调函数
        async def progress_callback(progress: int, message: str):
            await update_task_progress(
                task_id, target_language, "translation",
                progress, message, "processing"
            )

        # 执行批量翻译
        result = await batch_translate_subtitles(
            source_subtitle_path=Path(source_subtitle_path),
            target_subtitle_path=translated_subtitle_path,
            target_language=target_language,
            progress_callback=progress_callback
        )

        # 等待确保所有异步进度更新都已完成，然后再标记完成
        await asyncio.sleep(1.0)

        # 检查是否被取消
        if result.get('cancelled', False):
            print(f"[翻译] ⚠️ 任务已取消，当前翻译已完成: {task_id} -> {target_language}", flush=True)
            # 清除取消请求标志
            running_task_tracker.clear_cancel_request()
            # 停止追踪
            running_task_tracker.complete_task(task_id, target_language, "translation")
            # 标记任务完成（虽然被取消，但翻译部分已完成）
            await mark_task_completed(
                task_id, target_language, "translation",
                extra_data={
                    "elapsed_time": result['elapsed_time'],
                    "total_items": result['total_items'],
                    "cancelled": True
                }
            )
            print(f"[翻译] 任务已停止，翻译部分已完成", flush=True)
            print(f"[翻译] 翻译文件: {result['target_file']}", flush=True)
            print(f"[翻译] 总条数: {result['total_items']}, 耗时: {result['elapsed_time']}秒", flush=True)
        else:
            # 正常完成，标记翻译阶段完成
            print(f"[翻译] 正在标记任务完成...", flush=True)
            await mark_task_completed(
                task_id, target_language, "translation",
                extra_data={
                    "elapsed_time": result['elapsed_time'],
                    "total_items": result['total_items']
                }
            )
            # 完成时停止追踪
            running_task_tracker.complete_task(task_id, target_language, "translation")
            print(f"[翻译] ✅ 任务完成: {task_id} -> {target_language}", flush=True)
            print(f"[翻译] 翻译文件: {result['target_file']}", flush=True)
            print(f"[翻译] 总条数: {result['total_items']}, 耗时: {result['elapsed_time']}秒", flush=True)

    except Exception as e:
        print(f"[翻译] ❌ 任务失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        await mark_task_failed(task_id, target_language, "translation", str(e))
        # 失败时停止追踪
        running_task_tracker.fail_task(task_id, str(e))


# ==================== 翻译状态查询 API ====================

@router.get("/{task_id}/languages/{language}/translate/status")
async def get_translation_status(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """
    获取翻译任务状态

    Args:
        task_id: 任务 ID
        language: 目标语言
    """
    # 刷新 session 以获取最新数据
    db.expire_all()

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取翻译状态
    language_status = task.language_status or {}
    lang_data = language_status.get(language, {})
    translation_status = lang_data.get("translation", {})

    status = translation_status.get("status", "pending")
    progress = translation_status.get("progress", 0)
    message = translation_status.get("message", "")

    # 调试日志
    print(f"[翻译状态查询] task_id={task_id}, language={language}, status={status}, progress={progress}", flush=True)

    response = {
        "status": status,
        "progress": progress,
        "message": message
    }

    # 如果完成，添加翻译文件路径和额外信息
    if status == "completed":
        translated_subtitle_path = task_path_manager.get_translated_subtitle_path(task_id, language)
        if translated_subtitle_path.exists():
            response["target_srt_filename"] = str(translated_subtitle_path.name)

        # 添加耗时和条数信息
        if "elapsed_time" in translation_status:
            response["elapsed_time"] = translation_status["elapsed_time"]
        if "total_items" in translation_status:
            response["total_items"] = translation_status["total_items"]

        print(f"[翻译状态查询] ✅ 翻译已完成，文件: {translated_subtitle_path}", flush=True)

    return response


# ==================== 语音克隆 API ====================

@router.post("/{task_id}/languages/{language}/voice-cloning")
async def process_voice_cloning(
    task_id: str,
    language: str,
    request: VoiceCloningRequest,
    db: Session = Depends(get_db)
):
    """
    启动语音克隆处理

    Args:
        task_id: 任务 ID
        language: 目标语言
        request: 包含 speaker_voice_mapping
    """
    print(f"\n[语音克隆] 收到请求: {task_id} -> {language}", flush=True)

    # 验证任务存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 验证翻译字幕存在
    translated_subtitle_path = task_path_manager.get_translated_subtitle_path(task_id, language)
    if not translated_subtitle_path.exists():
        raise HTTPException(status_code=400, detail="请先完成翻译")

    # 验证说话人数据存在
    speaker_data_path = task_path_manager.get_speaker_data_path(task_id)
    if not speaker_data_path.exists():
        raise HTTPException(status_code=400, detail="请先完成说话人识别")

    # 检查是否有正在运行的任务
    if running_task_tracker.has_running_task(task_id):
        running = running_task_tracker.get_running_task(task_id)
        raise HTTPException(
            status_code=409,
            detail=f"任务 {task_id} 已有正在运行的任务: {running.language}/{running.stage}"
        )

    # 注册运行任务
    running_task_tracker.start_task(task_id, language, "voice_cloning")

    # 启动后台任务
    asyncio.create_task(run_voice_cloning_task(
        task_id=task_id,
        language=language,
        speaker_voice_mapping=request.speaker_voice_mapping
    ))

    return {
        "message": f"语音克隆任务已启动: {language}",
        "task_id": task_id,
        "language": language
    }


async def run_voice_cloning_task(
    task_id: str,
    language: str,
    speaker_voice_mapping: Dict[str, str]
):
    """
    后台执行语音克隆任务

    使用 voice_cloning_service 模块进行语音克隆
    """
    try:
        print(f"\n========== 开始语音克隆任务: {task_id} -> {language} ==========", flush=True)

        await update_task_progress(
            task_id, language, "voice_cloning",
            0, "正在准备语音克隆...", "processing"
        )

        # 获取路径
        translated_subtitle_path = task_path_manager.get_translated_subtitle_path(task_id, language)
        cloned_audio_output_dir = task_path_manager.get_cloned_audio_dir(task_id, language)
        cloned_audio_output_dir.mkdir(exist_ok=True, parents=True)

        # 导入语音克隆服务
        from voice_cloning_service import clone_voices_for_language

        # 定义进度回调
        async def progress_callback(progress: int, message: str):
            await update_task_progress(
                task_id, language, "voice_cloning",
                progress, message, "processing"
            )

        # 执行语音克隆
        result = await clone_voices_for_language(
            task_id=task_id,
            language=language,
            translated_subtitle_path=translated_subtitle_path,
            speaker_voice_mapping=speaker_voice_mapping,
            cloned_audio_output_dir=cloned_audio_output_dir,
            progress_callback=progress_callback
        )

        # 保存克隆结果到文件
        cloned_results = result.get('cloned_results', [])
        cloned_results_path = cloned_audio_output_dir / "cloned_results.json"
        with open(cloned_results_path, 'w', encoding='utf-8') as f:
            json.dump(cloned_results, f, ensure_ascii=False, indent=2)

        # 标记完成，包含额外数据
        await mark_task_completed(
            task_id, language, "voice_cloning",
            extra_data={
                "elapsed_time": result.get('total_duration', 0),
                "total_items": result.get('total_segments', 0),
                "successful_items": result.get('successful_segments', 0)
            }
        )
        # 完成时停止追踪
        running_task_tracker.complete_task(task_id, language, "voice_cloning")
        print(f"[语音克隆] ✅ 任务完成: {task_id} -> {language}", flush=True)
        print(f"[语音克隆] 输出目录: {result['output_dir']}", flush=True)
        print(f"[语音克隆] 成功生成 {result.get('successful_segments', 0)}/{result.get('total_segments', 0)} 个音频", flush=True)

    except Exception as e:
        print(f"[语音克隆] ❌ 任务失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        await mark_task_failed(task_id, language, "voice_cloning", str(e))
        # 失败时停止追踪
        running_task_tracker.fail_task(task_id, str(e))


@router.get("/{task_id}/languages/{language}/voice-cloning/status")
async def get_voice_cloning_status(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """
    获取语音克隆任务的状态

    Returns:
        status, progress, message, 以及完成时的 cloned_results
    """
    db.expire_all()  # 确保获取最新数据

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 从 language_status 中获取 voice_cloning 状态
    language_status = task.language_status or {}
    lang_data = language_status.get(language, {})
    voice_cloning_status = lang_data.get("voice_cloning", {})

    status = voice_cloning_status.get("status", "pending")
    response = {
        "task_id": task_id,
        "language": language,
        "status": status,
        "progress": voice_cloning_status.get("progress", 0),
        "message": voice_cloning_status.get("message", "")
    }

    # 如果完成，添加额外数据
    if status == "completed":
        response["elapsed_time"] = voice_cloning_status.get("elapsed_time", 0)
        response["total_items"] = voice_cloning_status.get("total_items", 0)

        # 尝试从克隆结果文件读取详细数据
        cloned_results_path = task_path_manager.get_cloned_audio_dir(task_id, language) / "cloned_results.json"
        if cloned_results_path.exists():
            try:
                with open(cloned_results_path, 'r', encoding='utf-8') as f:
                    cloned_results = json.load(f)
                response["cloned_results"] = cloned_results
            except Exception as e:
                print(f"[语音克隆状态] 读取 cloned_results 失败: {e}", flush=True)

    return response


@router.get("/{task_id}/languages/{language}/cloned-audio/{filename}")
async def serve_cloned_audio(
    task_id: str,
    language: str,
    filename: str,
    request: Request
):
    """
    提供克隆音频文件的流式传输，支持 HTTP Range 请求
    """
    import re
    from fastapi.responses import FileResponse, StreamingResponse

    cloned_audio_dir = task_path_manager.get_cloned_audio_dir(task_id, language)
    file_path = cloned_audio_dir / filename

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
        with open(file_path, 'rb') as f:
            f.seek(start)
            remaining = chunk_size
            while remaining > 0:
                read_size = min(8192, remaining)
                data = f.read(read_size)
                if not data:
                    break
                remaining -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_size),
        "Cache-Control": "no-cache, no-store, must-revalidate"
    }

    return StreamingResponse(
        iterfile(),
        status_code=206,
        headers=headers,
        media_type="audio/wav"
    )


# 兼容旧路径格式的路由
@router.get("/{task_id}/outputs/{language}/cloned_audio/{filename}")
async def serve_cloned_audio_legacy(
    task_id: str,
    language: str,
    filename: str,
    request: Request
):
    """
    提供克隆音频文件的流式传输（兼容旧路径格式）
    重定向到新的路由处理
    """
    # 重用新路由的逻辑
    return await serve_cloned_audio(task_id, language, filename, request)


# ==================== 导出 API ====================

@router.post("/{task_id}/languages/{language}/export")
async def export_video(
    task_id: str,
    language: str,
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    导出指定语言的最终视频

    Args:
        task_id: 任务 ID
        language: 目标语言
    """
    print(f"\n[导出] 收到请求: {task_id} -> {language}", flush=True)

    # 验证任务存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # TODO: 验证所有必需文件存在

    # 启动后台任务
    asyncio.create_task(run_export_task(task_id, language))

    return {
        "message": f"导出任务已启动: {language}",
        "task_id": task_id,
        "language": language
    }


async def run_export_task(task_id: str, language: str):
    """后台执行导出任务"""
    try:
        print(f"\n========== 开始导出任务: {task_id} -> {language} ==========", flush=True)

        await update_task_progress(
            task_id, language, "export",
            0, "正在准备导出...", "processing"
        )

        import subprocess
        import os
        from pathlib import Path

        # 获取任务路径
        paths = task_path_manager.get_task_paths(task_id)

        # 获取输入视频路径
        from database import SessionLocal
        from models.task import Task as TaskModel

        db = SessionLocal()
        task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
        if not task:
            raise Exception("任务不存在")

        input_video_path = paths["input"] / task.video_filename
        if not input_video_path.exists():
            raise Exception(f"视频文件不存在: {input_video_path}")

        await update_task_progress(
            task_id, language, "export",
            10, "正在拼接克隆音频...", "processing"
        )

        # 步骤1: 拼接克隆音频（如果存在）
        cloned_audio_dir = task_path_manager.get_cloned_audio_dir(task_id, language)
        stitched_audio_path = task_path_manager.get_task_paths(task_id)["outputs"] / language / "stitched_audio.wav"

        if cloned_audio_dir.exists() and list(cloned_audio_dir.glob("*.wav")):
            # 拼接音频文件
            from audio_stitcher import AudioStitcher
            from srt_parser import SRTParser

            srt_parser = SRTParser()
            translated_subtitle_path = task_path_manager.get_translated_subtitle_path(task_id, language)
            subtitles = srt_parser.parse_srt(translated_subtitle_path)

            audio_segments = []
            for i, subtitle in enumerate(subtitles):
                segment_path = cloned_audio_dir / f"cloned_{i}.wav"
                if segment_path.exists():
                    audio_segments.append({
                        'path': str(segment_path),
                        'start_time': subtitle['start_time'],
                        'end_time': subtitle['end_time']
                    })

            if audio_segments:
                stitcher = AudioStitcher()
                stitched_audio_path.parent.mkdir(exist_ok=True, parents=True)
                stitcher.stitch_audio_segments(audio_segments, str(stitched_audio_path))
                print(f"[导出] 音频拼接完成: {stitched_audio_path}", flush=True)

        await update_task_progress(
            task_id, language, "export",
            40, "正在合并视频和音频...", "processing"
        )

        # 步骤2: 合并视频和音频
        output_video_path = task_path_manager.get_task_paths(task_id)["outputs"] / language / "final_video.mp4"
        output_video_path.parent.mkdir(exist_ok=True, parents=True)

        if stitched_audio_path.exists():
            # 使用 ffmpeg 合并视频和音频
            cmd = [
                'ffmpeg',
                '-i', str(input_video_path),  # 输入视频
                '-i', str(stitched_audio_path),  # 输入音频
                '-c:v', 'copy',  # 复制视频流（不重新编码）
                '-c:a', 'aac',  # 音频编码为 AAC
                '-b:a', '192k',  # 音频比特率
                '-map', '0:v:0',  # 使用第一个输入的视频流
                '-map', '1:a:0',  # 使用第二个输入的音频流
                '-shortest',  # 以最短的流为准
                '-y',  # 覆盖输出文件
                str(output_video_path)
            ]
        else:
            # 如果没有克隆音频，直接复制原视频
            cmd = [
                'ffmpeg',
                '-i', str(input_video_path),
                '-c', 'copy',
                '-y',
                str(output_video_path)
            ]

        print(f"[导出] 执行 ffmpeg 命令: {' '.join(cmd)}", flush=True)

        # 运行 ffmpeg
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"[导出] ffmpeg 错误: {stderr}", flush=True)
            raise Exception(f"ffmpeg 执行失败: {stderr}")

        await update_task_progress(
            task_id, language, "export",
            80, "正在嵌入字幕...", "processing"
        )

        # 步骤3: 嵌入字幕（可选）
        # 这里可以添加硬字幕嵌入逻辑

        await update_task_progress(
            task_id, language, "export",
            95, "导出完成...", "processing"
        )

        print(f"[导出] ✅ 导出完成: {output_video_path}", flush=True)

        await mark_task_completed(task_id, language, "export")
        print(f"[导出] ✅ 任务完成: {task_id} -> {language}", flush=True)

        db.close()

    except Exception as e:
        print(f"[导出] ❌ 任务失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        await mark_task_failed(task_id, language, "export", str(e))


# ==================== 音频拼接 API ====================

def _remove_silence_by_volume(
    audio_data,
    sample_rate: int,
    window_ms: int = 50,
    db_threshold: float = -50.0,
    min_silence_windows: int = 2
):
    """
    基于音量检测并移除静音段
    """
    import numpy as np

    if len(audio_data) == 0:
        return audio_data

    window_samples = int(sample_rate * window_ms / 1000.0)

    if window_samples == 0 or len(audio_data) < window_samples:
        return audio_data

    num_windows = len(audio_data) // window_samples
    db_values = []

    for i in range(num_windows):
        start = i * window_samples
        end = start + window_samples
        window = audio_data[start:end]
        rms = np.sqrt(np.mean(window ** 2))
        if rms > 1e-10:
            db = 20 * np.log10(rms)
        else:
            db = -100.0
        db_values.append(db)

    is_speech = []
    for i in range(len(db_values)):
        silence_count = 0
        for j in range(min_silence_windows):
            if i + j < len(db_values) and db_values[i + j] < db_threshold:
                silence_count += 1
        is_speech.append(silence_count < min_silence_windows)

    speech_segments = []
    for i, speech in enumerate(is_speech):
        if speech:
            start = i * window_samples
            end = min((i + 1) * window_samples, len(audio_data))
            speech_segments.append(audio_data[start:end])

    remaining_start = num_windows * window_samples
    if remaining_start < len(audio_data):
        speech_segments.append(audio_data[remaining_start:])

    if speech_segments:
        result = np.concatenate(speech_segments)
        reduction_ratio = (1 - len(result) / len(audio_data)) * 100
        print(f"  [静音移除] 移除 {reduction_ratio:.1f}% 的静音段")
        return result

    return audio_data


def _apply_fade_in_out(
    audio_data,
    sample_rate: int,
    fade_ms: int = 10
):
    """
    在音频首尾应用淡入淡出效果
    """
    import numpy as np

    if len(audio_data) == 0:
        return audio_data

    fade_samples = int(sample_rate * fade_ms / 1000.0)
    fade_samples = min(fade_samples, len(audio_data) // 2)

    if fade_samples == 0:
        return audio_data

    result = audio_data.copy()
    fade_in_curve = np.linspace(0, 1, fade_samples)
    result[:fade_samples] *= fade_in_curve
    fade_out_curve = np.linspace(1, 0, fade_samples)
    result[-fade_samples:] *= fade_out_curve

    return result


def _replan_audio_timeline(
    cloned_results: List[Dict],
    cloned_audio_dir: str,
    optimized_files: Dict[int, str]
) -> Dict[int, Dict]:
    """
    重新规划音频时间轴，为超长片段借用相邻空闲时间
    """
    import soundfile as sf

    replanned = {}
    segments_info = []

    for idx, result in enumerate(cloned_results):
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

    segments_info.sort(key=lambda x: x['start_time'])

    for i, seg in enumerate(segments_info):
        excess = seg['actual_duration'] - seg['target_duration']

        if excess <= 0.001:
            continue

        idx = seg['index']
        max_borrow = seg['target_duration'] * 0.5

        gap_before = 0
        if i > 0:
            prev_seg = segments_info[i - 1]
            gap_before = seg['start_time'] - prev_seg['end_time']

        gap_after = 0
        if i < len(segments_info) - 1:
            next_seg = segments_info[i + 1]
            gap_after = next_seg['start_time'] - seg['end_time']

        half_excess = excess / 2
        borrow_before = min(gap_before, max_borrow, half_excess)
        borrow_after = min(gap_after, max_borrow, half_excess)

        total_borrowed = borrow_before + borrow_after
        if total_borrowed < excess:
            remaining_needed = excess - total_borrowed
            can_borrow_more_before = min(gap_before - borrow_before, max_borrow - borrow_before)
            can_borrow_more_after = min(gap_after - borrow_after, max_borrow - borrow_after)

            if can_borrow_more_before > 0:
                extra_before = min(can_borrow_more_before, remaining_needed)
                borrow_before += extra_before
                remaining_needed -= extra_before

            if remaining_needed > 0 and can_borrow_more_after > 0:
                extra_after = min(can_borrow_more_after, remaining_needed)
                borrow_after += extra_after

        if borrow_before > 0.001 or borrow_after > 0.001:
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


@router.post("/{task_id}/languages/{language}/stitch-audio")
async def stitch_cloned_audio(
    task_id: str,
    language: str,
    request: StitchAudioRequest,
    db: Session = Depends(get_db)
):
    """
    拼接克隆的音频片段为完整音频
    """
    import soundfile as sf
    import numpy as np
    import time
    from scipy.io import wavfile
    from audio_optimizer import AudioOptimizer

    start_time = time.time()

    try:
        # 验证任务存在
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 检查是否有正在运行的任务
        if running_task_tracker.has_running_task(task_id):
            running = running_task_tracker.get_running_task(task_id)
            raise HTTPException(
                status_code=409,
                detail=f"任务 {task_id} 已有正在运行的任务: {running.language}/{running.stage}"
            )

        # 注册运行任务
        running_task_tracker.start_task(task_id, language, "stitch")

        # 获取路径
        cloned_audio_dir = task_path_manager.get_cloned_audio_dir(task_id, language)
        stitched_audio_path = task_path_manager.get_stitched_audio_path(task_id, language)
        translated_subtitle_path = task_path_manager.get_translated_subtitle_path(task_id, language)

        # 检查克隆音频目录是否存在
        if not cloned_audio_dir.exists():
            raise HTTPException(status_code=400, detail="克隆音频目录不存在")

        # 读取翻译字幕获取时间信息
        from srt_parser import SRTParser
        srt_parser = SRTParser()
        subtitles = srt_parser.parse_srt(str(translated_subtitle_path))

        if not subtitles:
            raise HTTPException(status_code=400, detail="没有字幕数据")

        print(f"[音频拼接] 开始拼接任务 {task_id} / {language} 的音频片段...", flush=True)

        # 构建 cloned_results
        cloned_results = []
        for i, subtitle in enumerate(subtitles):
            # 尝试多种文件名格式
            possible_names = [f"cloned_{i}.wav", f"segment_{i}.wav"]
            audio_path = None
            for name in possible_names:
                path = cloned_audio_dir / name
                if path.exists():
                    audio_path = str(path)
                    break

            cloned_results.append({
                "index": i,
                "start_time": subtitle.get("start_time", 0),
                "end_time": subtitle.get("end_time", 0),
                "cloned_audio_path": audio_path,
                "target_text": subtitle.get("text", "")
            })

        # 步骤1: 优化过长的音频片段
        optimizer = AudioOptimizer(use_vad=False)
        optimized_files = optimizer.optimize_segments_for_stitching(
            cloned_results,
            str(cloned_audio_dir),
            threshold_ratio=1.02
        )

        # 步骤2: 重新规划时间轴
        replanned_segments = _replan_audio_timeline(
            cloned_results,
            str(cloned_audio_dir),
            optimized_files
        )

        # 步骤3: 获取原视频音量（用于音量匹配）
        original_audio_volumes = {}
        input_video_path = None
        task_paths = task_path_manager.get_task_paths(task_id)
        input_dir = task_paths["input"]

        # 查找输入视频
        for ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            for video_file in input_dir.glob(f'*{ext}'):
                input_video_path = video_file
                break
            if input_video_path:
                break

        if input_video_path and input_video_path.exists():
            try:
                import subprocess
                temp_audio_path = str(task_paths["processed"] / f"temp_original_audio_{language}.wav")
                cmd = [
                    'ffmpeg', '-i', str(input_video_path),
                    '-vn', '-acodec', 'pcm_s16le',
                    '-ar', '44100', '-ac', '1',
                    '-y', temp_audio_path
                ]
                subprocess.run(cmd, capture_output=True, check=True)

                original_audio, orig_sr = sf.read(temp_audio_path)

                for idx, result in enumerate(cloned_results):
                    start_t = result.get("start_time", 0)
                    end_t = result.get("end_time", 0)
                    start_sample = int(start_t * orig_sr)
                    end_sample = int(end_t * orig_sr)

                    if end_sample <= len(original_audio):
                        segment_audio = original_audio[start_sample:end_sample]
                        rms = np.sqrt(np.mean(segment_audio**2))
                        original_audio_volumes[idx] = rms

                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)

            except Exception as e:
                print(f"[音频拼接] 警告: 无法提取原视频音频音量: {e}", flush=True)

        # 步骤4: 读取所有音频片段
        segments_with_timing = []
        sample_rate = None

        for idx, result in enumerate(cloned_results):
            cloned_audio_path = result.get("cloned_audio_path")
            if not cloned_audio_path:
                print(f"[音频拼接] 跳过片段 {idx}: 没有克隆音频", flush=True)
                continue

            # 优先使用优化后的音频
            if idx in optimized_files:
                audio_file_path = optimized_files[idx]
            else:
                audio_file_path = cloned_audio_path

            if not os.path.exists(audio_file_path):
                print(f"[音频拼接] 跳过片段 {idx}: 文件不存在 {audio_file_path}", flush=True)
                continue

            audio_data, sr = sf.read(audio_file_path)
            if sample_rate is None:
                sample_rate = sr

            start_t = result.get("start_time", 0)
            end_t = result.get("end_time", 0)
            timestamp_duration = end_t - start_t
            actual_duration = len(audio_data) / sample_rate

            segments_with_timing.append({
                "index": idx,
                "audio_data": audio_data,
                "start_time": start_t,
                "end_time": end_t,
                "timestamp_duration": timestamp_duration,
                "actual_duration": actual_duration,
                "original_volume": original_audio_volumes.get(idx, None)
            })

        if not segments_with_timing:
            raise HTTPException(status_code=400, detail="没有有效的音频片段可拼接")

        segments_with_timing.sort(key=lambda x: x["start_time"])

        print(f"[音频拼接] 开始处理 {len(segments_with_timing)} 个音频片段...", flush=True)

        # 步骤5: 处理每个片段
        processed_segments = []

        for seg in segments_with_timing:
            audio_data = seg["audio_data"]
            timestamp_duration = seg["timestamp_duration"]
            original_volume = seg.get("original_volume")
            idx = seg["index"]

            # 检查是否有重新规划的时间轴
            if idx in replanned_segments:
                replan_info = replanned_segments[idx]
                target_duration = replan_info['actual_duration']
                actual_start = replan_info['actual_start']
                actual_end = replan_info['actual_end']
            else:
                target_duration = timestamp_duration
                actual_start = seg["start_time"]
                actual_end = seg["end_time"]

            # 静音移除（跳过已优化的片段）
            if idx not in optimized_files and len(audio_data) / sample_rate > target_duration * 1.05:
                original_duration = len(audio_data) / sample_rate
                audio_data = _remove_silence_by_volume(
                    audio_data, sample_rate,
                    window_ms=50, db_threshold=-50.0, min_silence_windows=2
                )
                new_duration = len(audio_data) / sample_rate
                if new_duration < original_duration:
                    print(f"  [片段 {idx}] 移除静音: {original_duration:.3f}s → {new_duration:.3f}s", flush=True)

            # 精确计算目标样本数
            target_start_sample = int(actual_start * sample_rate + 0.5)
            target_end_sample = int(actual_end * sample_rate + 0.5)
            target_samples = target_end_sample - target_start_sample
            actual_samples = len(audio_data)

            if actual_samples > target_samples:
                # 裁剪
                excess_samples = actual_samples - target_samples
                trim_left = excess_samples // 2
                trim_right = excess_samples - trim_left
                processed_audio = audio_data[trim_left:actual_samples - trim_right]
            elif actual_samples < target_samples:
                # 补零
                pad_samples = target_samples - actual_samples
                pad_left = pad_samples // 2
                pad_right = pad_samples - pad_left
                processed_audio = np.pad(audio_data, (pad_left, pad_right), mode='constant', constant_values=0)
            else:
                processed_audio = audio_data

            # 确保长度精确匹配
            if len(processed_audio) != target_samples:
                if len(processed_audio) > target_samples:
                    processed_audio = processed_audio[:target_samples]
                else:
                    diff = target_samples - len(processed_audio)
                    processed_audio = np.pad(processed_audio, (0, diff), mode='constant', constant_values=0)

            # 应用淡入淡出
            processed_audio = _apply_fade_in_out(processed_audio, sample_rate, fade_ms=10)

            # 音量匹配
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

        # 步骤6: 拼接所有片段
        final_audio_parts = []
        current_sample_position = 0

        for i, seg in enumerate(processed_segments):
            target_start_sample = int(seg["start_time"] * sample_rate + 0.5)
            gap_samples = target_start_sample - current_sample_position

            if gap_samples > 0:
                silence = np.zeros(gap_samples, dtype=seg["audio"].dtype)
                final_audio_parts.append(silence)
                current_sample_position += gap_samples

            audio_segment = seg["audio"]
            final_audio_parts.append(audio_segment)
            current_sample_position += len(audio_segment)

        if not final_audio_parts:
            raise HTTPException(status_code=400, detail="没有音频部分可以拼接")

        final_audio = np.concatenate(final_audio_parts)

        # 数据清理
        if np.isnan(final_audio).any() or np.isinf(final_audio).any():
            final_audio = np.nan_to_num(final_audio, nan=0.0, posinf=1.0, neginf=-1.0)

        # 归一化并转换为 int16
        max_val = np.max(np.abs(final_audio))
        if max_val > 0:
            final_audio = final_audio / max_val
        final_audio_int16 = (final_audio * 32767).astype(np.int16)

        # 保存最终音频
        stitched_audio_path.parent.mkdir(exist_ok=True, parents=True)
        wavfile.write(str(stitched_audio_path), sample_rate, final_audio_int16)

        total_duration = len(final_audio) / sample_rate
        end_time = time.time()
        stitch_duration = end_time - start_time

        print(f"[音频拼接] ✅ 完成! 总时长: {total_duration:.3f}s, 耗时: {stitch_duration:.1f}s", flush=True)

        # 更新 cloned_results 中的时间轴
        for idx, replan_info in replanned_segments.items():
            if idx < len(cloned_results):
                cloned_results[idx]['actual_start_time'] = replan_info['actual_start']
                cloned_results[idx]['actual_end_time'] = replan_info['actual_end']

        # 保存更新后的 cloned_results 到文件（包含 actual_start_time 和 actual_end_time）
        cloned_results_path = cloned_audio_dir / "cloned_results.json"
        with open(cloned_results_path, 'w', encoding='utf-8') as f:
            json.dump(cloned_results, f, ensure_ascii=False, indent=2)
        print(f"[音频拼接] 已保存更新后的 cloned_results 到: {cloned_results_path}", flush=True)

        # 更新数据库中的拼接状态
        await mark_task_completed(
            task_id, language, "stitch",
            extra_data={
                "total_duration": total_duration,
                "segments_count": len(processed_segments),
                "stitch_duration": stitch_duration
            }
        )
        # 完成时停止追踪
        running_task_tracker.complete_task(task_id, language, "stitch")

        return {
            "success": True,
            "stitched_audio_path": f"/api/tasks/{task_id}/languages/{language}/stitched-audio",
            "total_duration": total_duration,
            "segments_count": len(processed_segments),
            "message": f"音频拼接完成 (耗时: {stitch_duration:.1f}秒)",
            "replanned_segments": len(replanned_segments),
            "stitch_duration": stitch_duration,
            "cloned_results": cloned_results
        }

    except HTTPException:
        # 失败时停止追踪
        running_task_tracker.fail_task(task_id, "HTTPException")
        raise
    except Exception as e:
        print(f"[音频拼接] ❌ 失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        # 失败时停止追踪
        running_task_tracker.fail_task(task_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}/languages/{language}/stitch-audio/status")
async def get_stitch_audio_status(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """
    获取音频拼接状态
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 从 language_status 获取拼接状态
    language_status = task.language_status or {}
    lang_data = language_status.get(language, {})
    stitch_status = lang_data.get("stitch", {})

    status = stitch_status.get("status", "pending")

    # 同时检查文件是否存在
    stitched_audio_path = task_path_manager.get_stitched_audio_path(task_id, language)
    file_exists = stitched_audio_path.exists()

    response = {
        "status": status,
        "progress": stitch_status.get("progress", 0),
        "message": stitch_status.get("message", ""),
        "file_exists": file_exists
    }

    # 如果文件存在但状态不是 completed，更新状态
    if file_exists and status != "completed":
        response["status"] = "completed"
        response["progress"] = 100

    if file_exists or status == "completed":
        response["stitched_audio_path"] = f"/api/tasks/{task_id}/languages/{language}/stitched-audio"
        response["total_duration"] = stitch_status.get("total_duration", 0)
        response["segments_count"] = stitch_status.get("segments_count", 0)

        # 尝试从 cloned_results.json 读取详细数据（包含 actual_start_time 和 actual_end_time）
        cloned_results_path = task_path_manager.get_cloned_audio_dir(task_id, language) / "cloned_results.json"
        if cloned_results_path.exists():
            try:
                with open(cloned_results_path, 'r', encoding='utf-8') as f:
                    cloned_results = json.load(f)
                # 如果没有 actual_start_time/actual_end_time，使用 start_time/end_time 作为默认值
                for item in cloned_results:
                    if 'actual_start_time' not in item and 'start_time' in item:
                        item['actual_start_time'] = item['start_time']
                    if 'actual_end_time' not in item and 'end_time' in item:
                        item['actual_end_time'] = item['end_time']
                response["cloned_results"] = cloned_results
                print(f"[拼接状态查询] 已加载 cloned_results，共 {len(cloned_results)} 条记录", flush=True)
            except Exception as e:
                print(f"[拼接状态查询] 读取 cloned_results 失败: {e}", flush=True)

    print(f"[拼接状态查询] task_id={task_id}, language={language}, status={response['status']}, file_exists={file_exists}", flush=True)

    return response


@router.get("/{task_id}/languages/{language}/stitched-audio")
async def serve_stitched_audio(
    task_id: str,
    language: str,
    request: Request
):
    """
    提供拼接后的音频文件（支持 Range 请求以实现 seek 功能）
    """
    from fastapi.responses import Response, StreamingResponse
    import os

    stitched_audio_path = task_path_manager.get_stitched_audio_path(task_id, language)

    if not stitched_audio_path.exists():
        raise HTTPException(status_code=404, detail="拼接音频不存在")

    file_path = str(stitched_audio_path)
    file_size = os.path.getsize(file_path)

    # 获取 Range 请求头
    range_header = request.headers.get("range")

    if range_header:
        # 解析 Range 头，格式: bytes=start-end
        try:
            range_spec = range_header.replace("bytes=", "")
            parts = range_spec.split("-")
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if parts[1] else file_size - 1

            # 确保范围有效
            if start >= file_size:
                raise HTTPException(status_code=416, detail="Range Not Satisfiable")

            end = min(end, file_size - 1)
            content_length = end - start + 1

            def iter_file():
                with open(file_path, "rb") as f:
                    f.seek(start)
                    remaining = content_length
                    chunk_size = 8192
                    while remaining > 0:
                        chunk = f.read(min(chunk_size, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        yield chunk

            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
                "Content-Type": "audio/wav",
            }

            return StreamingResponse(
                iter_file(),
                status_code=206,
                headers=headers,
                media_type="audio/wav"
            )

        except (ValueError, IndexError) as e:
            print(f"[音频服务] Range 解析失败: {range_header}, 错误: {e}")
            # Range 解析失败，返回完整文件

    # 没有 Range 请求或解析失败，返回完整文件（带 Accept-Ranges 头）
    def iter_full_file():
        with open(file_path, "rb") as f:
            chunk_size = 8192
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
        "Content-Type": "audio/wav",
    }

    return StreamingResponse(
        iter_full_file(),
        headers=headers,
        media_type="audio/wav"
    )


# ==================== 重新生成单个片段 API ====================

@router.post("/{task_id}/languages/{language}/regenerate-segment")
async def regenerate_segment(
    task_id: str,
    language: str,
    request: RegenerateSegmentRequest,
    db: Session = Depends(get_db)
):
    """
    重新生成单个字幕片段的克隆语音（使用不同的说话人音色）
    """
    try:
        segment_index = request.segment_index
        new_speaker_id = request.new_speaker_id

        print(f"[重新生成片段] task_id={task_id}, language={language}, segment_index={segment_index}, new_speaker_id={new_speaker_id}", flush=True)

        # 验证任务存在
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 获取路径
        cloned_audio_dir = task_path_manager.get_cloned_audio_dir(task_id, language)
        translated_subtitle_path = task_path_manager.get_translated_subtitle_path(task_id, language)
        speaker_data_path = task_path_manager.get_speaker_data_path(task_id)
        processed_dir = task_path_manager.get_task_paths(task_id)["processed"]

        # 检查克隆音频目录是否存在
        if not cloned_audio_dir.exists():
            raise HTTPException(status_code=400, detail="克隆音频目录不存在，请先运行语音克隆")

        # 读取翻译字幕
        from srt_parser import SRTParser
        srt_parser = SRTParser()
        subtitles = srt_parser.parse_srt(str(translated_subtitle_path))

        if segment_index < 0 or segment_index >= len(subtitles):
            raise HTTPException(status_code=400, detail="片段索引无效")

        # 获取目标文本
        if request.new_target_text:
            target_text = request.new_target_text
            print(f"[重新生成片段] 使用新的译文: {target_text}", flush=True)
        else:
            target_text = subtitles[segment_index]["text"]
            print(f"[重新生成片段] 使用原译文: {target_text}", flush=True)

        # 加载说话人数据
        if not speaker_data_path.exists():
            raise HTTPException(status_code=400, detail="说话人数据不存在")

        with open(speaker_data_path, 'r', encoding='utf-8') as f:
            speaker_data = json.load(f)

        scored_segments = speaker_data.get('scored_segments', {})
        audio_dir = speaker_data.get('audio_dir', str(processed_dir))

        # 查找编码文件
        encoded_dir = os.path.join(audio_dir, "encoded")
        fake_npy_path = None

        # 尝试查找已编码的文件
        if os.path.exists(encoded_dir):
            npy_file = os.path.join(encoded_dir, f"speaker_{new_speaker_id}_codes.npy")
            if os.path.exists(npy_file):
                fake_npy_path = npy_file
                print(f"[重新生成片段] ✅ 找到编码文件: {fake_npy_path}", flush=True)

        if not fake_npy_path:
            # 尝试旧格式
            old_encoded_dir = os.path.join(audio_dir, f"speaker_{new_speaker_id}_encoded")
            old_npy_file = os.path.join(old_encoded_dir, "fake.npy")
            if os.path.exists(old_npy_file):
                fake_npy_path = old_npy_file
                print(f"[重新生成片段] ✅ 找到旧格式编码文件: {fake_npy_path}", flush=True)

        if not fake_npy_path:
            # 需要重新编码
            print(f"[重新生成片段] ❌ 未找到编码文件，需要重新编码...", flush=True)

            # 获取参考音频
            from speaker_audio_processor import SpeakerAudioProcessor
            audio_processor = SpeakerAudioProcessor(target_duration=10.0, silence_duration=1.0)
            reference_output_dir = os.path.join(audio_dir, "references")

            # 将 scored_segments 的键转换为整数
            scored_segments_int = {}
            for k, v in scored_segments.items():
                try:
                    scored_segments_int[int(k)] = v
                except (ValueError, TypeError):
                    scored_segments_int[k] = v

            if new_speaker_id not in scored_segments_int:
                raise HTTPException(status_code=400, detail=f"说话人 {new_speaker_id} 不存在")

            # 处理单个说话人的音频
            speaker_segments = scored_segments_int[new_speaker_id]
            ref_audio_path = os.path.join(reference_output_dir, f"speaker_{new_speaker_id}_reference.wav")

            if not os.path.exists(ref_audio_path):
                raise HTTPException(status_code=400, detail=f"说话人 {new_speaker_id} 的参考音频不存在")

            # 编码参考音频
            from fish_voice_cloner import FishVoiceCloner
            cloner = FishVoiceCloner()

            speaker_encoded_dir = os.path.join(audio_dir, f"speaker_{new_speaker_id}_encoded")
            os.makedirs(speaker_encoded_dir, exist_ok=True)

            fake_npy_path = cloner.encode_reference_audio(ref_audio_path, speaker_encoded_dir)
            print(f"[重新生成片段] ✅ 编码完成: {fake_npy_path}", flush=True)

        # 获取参考文本
        from subtitle_text_extractor import SubtitleTextExtractor
        source_subtitle_path = task_path_manager.get_source_subtitle_path(task_id)
        text_extractor = SubtitleTextExtractor()

        # 将 scored_segments 的键转换为整数
        scored_segments_int = {}
        for k, v in scored_segments.items():
            try:
                scored_segments_int[int(k)] = v
            except (ValueError, TypeError):
                scored_segments_int[k] = v

        if new_speaker_id in scored_segments_int:
            # scored_segments 的格式是 List[Tuple[str, float]] 即 (音频路径, MOS分数)
            # 但 SubtitleTextExtractor 期望 List[Tuple[str, float, float]] 即 (音频路径, MOS分数, 时长)
            # 所以需要转换格式，添加一个占位时长 0.0
            segments_for_text = []
            for item in scored_segments_int[new_speaker_id]:
                if len(item) == 2:
                    # 二元组格式：(音频路径, MOS分数)
                    segments_for_text.append((item[0], item[1], 0.0))
                elif len(item) >= 3:
                    # 已经是三元组或更多
                    segments_for_text.append(item)
                else:
                    # 其他格式，跳过
                    continue

            speaker_texts = text_extractor.process_all_speakers(
                {new_speaker_id: segments_for_text},
                str(source_subtitle_path)
            )
            ref_text = speaker_texts.get(new_speaker_id, "")
        else:
            ref_text = ""

        print(f"[重新生成片段] 参考文本: {ref_text[:50]}...", flush=True)

        # 生成输出路径
        audio_filename = f"cloned_{segment_index}.wav"
        output_audio = str(cloned_audio_dir / audio_filename)
        work_dir = os.path.join(audio_dir, f"regen_{segment_index}_{new_speaker_id}")
        os.makedirs(work_dir, exist_ok=True)

        print(f"[重新生成片段] 开始生成: segment_index={segment_index}, new_speaker_id={new_speaker_id}", flush=True)
        print(f"[重新生成片段] 目标文本: {target_text[:50]}...", flush=True)

        # 使用 FishVoiceCloner 生成语音
        from fish_voice_cloner import FishVoiceCloner
        cloner = FishVoiceCloner()

        # 生成语义 token
        codes_path = cloner.generate_semantic_tokens(
            target_text=target_text,
            ref_text=ref_text,
            fake_npy_path=fake_npy_path,
            output_dir=work_dir
        )

        # 解码为音频
        cloner.decode_to_audio(codes_path, output_audio)

        print(f"[重新生成片段] ✅ 生成完成: {output_audio}", flush=True)

        # 生成 API 路径
        api_path = f"/api/tasks/{task_id}/languages/{language}/cloned-audio/{audio_filename}"

        return {
            "success": True,
            "segment_index": segment_index,
            "new_speaker_id": new_speaker_id,
            "cloned_audio_path": api_path,
            "target_text": target_text
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[重新生成片段] ❌ 失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 视频导出 API ====================

class ExportVideoRequest(BaseModel):
    """视频导出请求"""
    pass  # 不需要额外参数


@router.post("/{task_id}/languages/{language}/export-video")
async def export_video(
    task_id: str,
    language: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    导出视频 - 将原视频画面与拼接音频合成为新视频
    """
    try:
        print(f"[视频导出] 开始导出: task_id={task_id}, language={language}", flush=True)

        # 验证任务存在
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 检查拼接音频是否存在
        stitched_audio_path = task_path_manager.get_stitched_audio_path(task_id, language)
        if not stitched_audio_path.exists():
            raise HTTPException(status_code=400, detail="拼接音频不存在，请先完成音频拼接")

        # 获取输入视频路径
        input_video_path = task_path_manager.get_input_video_path(task_id, task.video_filename)
        if not input_video_path.exists():
            raise HTTPException(status_code=400, detail="输入视频不存在")

        # 获取导出视频路径（使用原始文件名）
        output_video_path = task_path_manager.get_exported_video_path(
            task_id, language, task.video_original_name
        )

        print(f"[视频导出] 输入视频: {input_video_path}", flush=True)
        print(f"[视频导出] 拼接音频: {stitched_audio_path}", flush=True)
        print(f"[视频导出] 输出视频: {output_video_path}", flush=True)

        # 检查是否有正在运行的任务
        if running_task_tracker.has_running_task(task_id):
            running = running_task_tracker.get_running_task(task_id)
            raise HTTPException(
                status_code=409,
                detail=f"任务 {task_id} 已有正在运行的任务: {running.language}/{running.stage}"
            )

        # 注册运行任务
        running_task_tracker.start_task(task_id, language, "export")

        # 更新状态为处理中
        await update_task_progress(task_id, language, "export", 0, "开始导出视频...")

        # 在后台执行导出
        background_tasks.add_task(
            export_video_task,
            task_id,
            language,
            str(input_video_path),
            str(stitched_audio_path),
            str(output_video_path)
        )

        return {
            "status": "started",
            "message": "视频导出已开始",
            "output_path": str(output_video_path)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[视频导出] ❌ 失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def export_video_task(
    task_id: str,
    language: str,
    input_video_path: str,
    stitched_audio_path: str,
    output_video_path: str
):
    """
    后台执行视频导出任务
    """
    import subprocess
    import time

    try:
        start_time = time.time()
        print(f"[视频导出] 开始处理...", flush=True)

        await update_task_progress(task_id, language, "export", 10, "准备视频编码...")

        # 使用 ffmpeg 合成视频
        # -c:v copy: 直接复制视频流（保持原质量）
        # -map 0:v: 使用第一个输入的视频流
        # -map 1:a: 使用第二个输入的音频流
        # -shortest: 以较短的流为准
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # 覆盖输出文件
            "-i", input_video_path,  # 输入视频
            "-i", stitched_audio_path,  # 输入音频
            "-map", "0:v:0",  # 使用视频的视频流
            "-map", "1:a:0",  # 使用音频文件的音频流
            "-c:v", "copy",  # 视频流直接复制（保持原质量）
            "-c:a", "aac",  # 音频编码为 AAC
            "-b:a", "192k",  # 音频比特率
            "-shortest",  # 以较短的为准
            output_video_path
        ]

        print(f"[视频导出] FFmpeg 命令: {' '.join(ffmpeg_cmd)}", flush=True)

        await update_task_progress(task_id, language, "export", 30, "正在合成视频...")

        # 执行 ffmpeg
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            print(f"[视频导出] FFmpeg 错误: {stderr}", flush=True)
            await mark_task_failed(task_id, language, "export", f"FFmpeg 错误: {stderr[:500]}")
            # 失败时停止追踪
            running_task_tracker.fail_task(task_id, f"FFmpeg 错误")
            return

        # 验证输出文件
        from pathlib import Path
        output_path = Path(output_video_path)
        if not output_path.exists():
            await mark_task_failed(task_id, language, "export", "输出视频文件未生成")
            # 失败时停止追踪
            running_task_tracker.fail_task(task_id, "输出视频文件未生成")
            return

        file_size = output_path.stat().st_size
        if file_size == 0:
            await mark_task_failed(task_id, language, "export", "输出视频文件为空")
            # 失败时停止追踪
            running_task_tracker.fail_task(task_id, "输出视频文件为空")
            return

        # 计算耗时
        duration = time.time() - start_time
        file_size_mb = file_size / (1024 * 1024)

        print(f"[视频导出] ✅ 完成! 文件大小: {file_size_mb:.2f}MB, 耗时: {duration:.1f}s", flush=True)

        # 标记完成
        await mark_task_completed(
            task_id, language, "export",
            extra_data={
                "output_path": output_video_path,
                "file_size": file_size,
                "duration": duration
            }
        )
        # 完成时停止追踪
        running_task_tracker.complete_task(task_id, language, "export")

    except Exception as e:
        print(f"[视频导出] ❌ 任务失败: {str(e)}", flush=True)
        import traceback
        traceback.print_exc()
        await mark_task_failed(task_id, language, "export", str(e))
        # 失败时停止追踪
        running_task_tracker.fail_task(task_id, str(e))


@router.get("/{task_id}/languages/{language}/export-video/status")
async def get_export_video_status(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """
    获取视频导出状态
    """
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 从 language_status 获取导出状态
    language_status = task.language_status or {}
    lang_data = language_status.get(language, {})
    export_status = lang_data.get("export", {})

    status = export_status.get("status", "pending")

    # 检查导出文件是否存在
    exported_video_path = task_path_manager.get_exported_video_path(
        task_id, language, task.video_original_name
    )
    file_exists = exported_video_path.exists()

    response = {
        "status": status,
        "progress": export_status.get("progress", 0),
        "message": export_status.get("message", ""),
        "file_exists": file_exists
    }

    # 如果文件存在但状态不是 completed，更新状态
    if file_exists and status != "completed":
        response["status"] = "completed"
        response["progress"] = 100

    if file_exists or status == "completed":
        response["output_path"] = str(exported_video_path)
        response["output_filename"] = exported_video_path.name
        response["output_dir"] = str(exported_video_path.parent)
        response["file_size"] = export_status.get("file_size", 0)

    print(f"[导出状态查询] task_id={task_id}, language={language}, status={response['status']}, file_exists={file_exists}", flush=True)

    return response


@router.get("/{task_id}/languages/{language}/exported-video")
async def serve_exported_video(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """
    提供导出的视频文件下载
    """
    from fastapi.responses import FileResponse

    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    exported_video_path = task_path_manager.get_exported_video_path(
        task_id, language, task.video_original_name
    )

    if not exported_video_path.exists():
        raise HTTPException(status_code=404, detail="导出视频不存在")

    return FileResponse(
        str(exported_video_path),
        media_type="video/mp4",
        filename=exported_video_path.name
    )
