import os
import shutil
import stat
import time
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
        """删除任务所有文件（Windows兼容，支持重试和只读文件处理）"""
        task_dir = self.get_task_dir(task_id)
        if not task_dir.exists():
            return

        def handle_remove_readonly(func, path, exc):
            """处理只读文件删除错误"""
            import errno
            excvalue = exc[1]
            if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
                # 尝试移除只读属性
                os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                func(path)
            else:
                raise

        # 尝试删除，最多重试3次（处理文件暂时被占用的情况）
        max_retries = 3
        for attempt in range(max_retries):
            try:
                shutil.rmtree(task_dir, onerror=handle_remove_readonly)
                print(f"[文件管理] ✅ 删除任务目录: {task_dir}")
                return
            except PermissionError as e:
                if attempt < max_retries - 1:
                    print(f"[文件管理] ⚠️ 删除失败（文件被占用），重试 {attempt + 1}/{max_retries - 1}...", flush=True)
                    time.sleep(0.5)  # 等待0.5秒后重试
                else:
                    # 最后一次尝试失败，抛出更友好的错误信息
                    print(f"[文件管理] ❌ 删除任务失败: {e}", flush=True)
                    raise RuntimeError(
                        f"无法删除任务 {task_id}。某些文件正被其他程序占用，请关闭所有相关程序后重试。\n"
                        f"被占用的文件: {e.filename if hasattr(e, 'filename') else '未知'}"
                    )
            except Exception as e:
                print(f"[文件管理] ❌ 删除任务时发生错误: {e}", flush=True)
                raise

# 全局文件管理器实例
file_manager = TaskFileManager()
