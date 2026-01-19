import os
import shutil
from pathlib import Path
from typing import Dict

class TaskFileManager:
    def __init__(self, base_dir: str = "./tasks"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def get_task_dir(self, task_id: str) -> Path:
        """获取任务根目录"""
        return self.base_dir / task_id

    def create_task_structure(self, task_id: str) -> Dict[str, Path]:
        """创建任务目录结构"""
        task_dir = self.get_task_dir(task_id)

        structure = {
            "root": task_dir,
            "input": task_dir / "input",
            "processed": task_dir / "processed",
            "outputs": task_dir / "outputs",
        }

        for path in structure.values():
            path.mkdir(parents=True, exist_ok=True)

        return structure

    def get_language_output_dir(self, task_id: str, language: str) -> Path:
        """获取语言输出目录"""
        output_dir = self.get_task_dir(task_id) / "outputs" / language
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def get_cloned_audio_dir(self, task_id: str, language: str) -> Path:
        """获取克隆音频目录"""
        audio_dir = self.get_language_output_dir(task_id, language) / "cloned_audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    def get_export_path(self, task_id: str, language: str) -> Path:
        """获取导出视频路径"""
        return self.get_language_output_dir(task_id, language) / f"export_{language}.mp4"

    def get_video_path(self, task_id: str) -> Path:
        """获取视频文件路径（查找 input 目录中的视频文件）"""
        input_dir = self.get_task_dir(task_id) / "input"
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found for task {task_id}")

        # 查找视频文件
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        for file in input_dir.iterdir():
            if file.suffix.lower() in video_extensions:
                return file

        raise FileNotFoundError(f"No video file found in task {task_id} input directory")

    def delete_task(self, task_id: str):
        """删除任务所有文件"""
        task_dir = self.get_task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)
            print(f"[文件管理] 删除任务目录: {task_dir}")

# 全局文件管理器实例
file_manager = TaskFileManager()
