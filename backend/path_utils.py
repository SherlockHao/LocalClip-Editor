# -*- coding: utf-8 -*-
"""
路径工具 - 统一管理任务相关的文件路径
"""

from pathlib import Path
from typing import Dict


class TaskPathManager:
    """任务路径管理器"""

    def __init__(self, base_dir: str = "tasks"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def get_task_root(self, task_id: str) -> Path:
        """获取任务根目录"""
        return self.base_dir / task_id

    def get_task_paths(self, task_id: str) -> Dict[str, Path]:
        """
        获取任务的所有目录路径

        Returns:
            {
                "root": Path,
                "input": Path,
                "processed": Path,
                "outputs": Path
            }
        """
        task_root = self.get_task_root(task_id)
        return {
            "root": task_root,
            "input": task_root / "input",
            "processed": task_root / "processed",
            "outputs": task_root / "outputs"
        }

    def get_input_video_path(self, task_id: str, video_filename: str) -> Path:
        """获取输入视频路径"""
        return self.get_task_paths(task_id)["input"] / video_filename

    def get_processed_audio_path(self, task_id: str) -> Path:
        """获取处理后的音频路径"""
        return self.get_task_paths(task_id)["processed"] / "audio.wav"

    def get_source_subtitle_path(self, task_id: str) -> Path:
        """获取原始字幕路径"""
        return self.get_task_paths(task_id)["processed"] / "source_subtitle.srt"

    def get_speaker_segments_dir(self, task_id: str) -> Path:
        """获取说话人音频片段目录"""
        segments_dir = self.get_task_paths(task_id)["processed"] / "speaker_segments"
        segments_dir.mkdir(exist_ok=True, parents=True)
        return segments_dir

    def get_speaker_data_path(self, task_id: str) -> Path:
        """获取说话人聚类数据路径"""
        return self.get_task_paths(task_id)["processed"] / "speaker_data.json"

    def get_diarization_dir(self, task_id: str) -> Path:
        """获取说话人分离数据目录（与processed目录相同）"""
        return self.get_task_paths(task_id)["processed"]

    def get_language_output_dir(self, task_id: str, language: str) -> Path:
        """获取指定语言的输出目录"""
        lang_dir = self.get_task_paths(task_id)["outputs"] / language
        lang_dir.mkdir(exist_ok=True, parents=True)
        return lang_dir

    def get_translated_subtitle_path(self, task_id: str, language: str) -> Path:
        """获取翻译后的字幕路径"""
        return self.get_language_output_dir(task_id, language) / "translated.srt"

    def get_cloned_audio_dir(self, task_id: str, language: str) -> Path:
        """获取克隆音频目录"""
        cloned_dir = self.get_language_output_dir(task_id, language) / "cloned_audio"
        cloned_dir.mkdir(exist_ok=True, parents=True)
        return cloned_dir

    def get_stitched_audio_path(self, task_id: str, language: str) -> Path:
        """获取拼接音频路径"""
        return self.get_language_output_dir(task_id, language) / "stitched_audio.wav"

    def get_final_video_path(self, task_id: str, language: str) -> Path:
        """获取最终视频路径"""
        return self.get_language_output_dir(task_id, language) / "final_video.mp4"

    def get_exported_video_path(self, task_id: str, language: str, original_video_name: str) -> Path:
        """
        获取导出视频路径
        命名格式: 原始视频名_语言.mp4
        """
        # 移除原始文件的扩展名
        base_name = Path(original_video_name).stem
        export_filename = f"{base_name}_{language}.mp4"
        return self.get_language_output_dir(task_id, language) / export_filename

    def get_export_dir(self, task_id: str, language: str) -> Path:
        """获取导出目录"""
        return self.get_language_output_dir(task_id, language)

    def ensure_task_structure(self, task_id: str):
        """确保任务目录结构存在"""
        paths = self.get_task_paths(task_id)
        for path in paths.values():
            path.mkdir(exist_ok=True, parents=True)

    def task_exists(self, task_id: str) -> bool:
        """检查任务目录是否存在"""
        return self.get_task_root(task_id).exists()


# 全局实例
task_path_manager = TaskPathManager()
