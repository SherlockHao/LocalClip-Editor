"""
打包环境工具模块
用于处理 PyInstaller 打包后的路径和资源访问
"""

import os
import sys
from pathlib import Path
from typing import Optional


def is_packaged() -> bool:
    """
    检测是否在 PyInstaller 打包环境中运行

    Returns:
        bool: 如果在打包环境中返回 True，否则返回 False
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path() -> Path:
    """
    获取应用程序的基础路径

    在打包环境中，返回可执行文件所在目录的父目录
    在开发环境中，返回项目根目录

    Returns:
        Path: 基础路径
    """
    if is_packaged():
        # PyInstaller 打包环境
        # sys.executable 是 .exe 文件路径
        # 返回 exe 所在目录的父目录（应用根目录）
        return Path(sys.executable).parent.parent
    else:
        # 开发环境
        # 返回 backend 目录的父目录
        return Path(__file__).parent.parent


def get_resource_path(relative_path: str) -> Path:
    """
    获取资源文件的绝对路径

    在 PyInstaller 打包环境中，资源文件会被解压到临时目录
    在开发环境中，直接使用相对路径

    Args:
        relative_path: 相对于项目根目录的路径

    Returns:
        Path: 资源文件的绝对路径
    """
    if is_packaged():
        # PyInstaller 临时目录
        base_path = Path(getattr(sys, '_MEIPASS', '.'))
        return base_path / relative_path
    else:
        # 开发环境
        return get_base_path() / relative_path


def get_data_path(relative_path: str) -> Path:
    """
    获取数据文件路径（可写）

    数据文件（上传、导出、缓存等）需要放在可写目录

    Args:
        relative_path: 相对路径

    Returns:
        Path: 数据文件的绝对路径
    """
    base_path = get_base_path()
    data_path = base_path / relative_path

    # 确保目录存在
    data_path.parent.mkdir(parents=True, exist_ok=True)

    return data_path


def get_model_path(model_name: str) -> Path:
    """
    获取 AI 模型路径

    Args:
        model_name: 模型名称 (如 'fish_speech', 'pyannote', 'wav2vec2')

    Returns:
        Path: 模型目录路径
    """
    models_dir = get_base_path() / "models" / model_name

    if not models_dir.exists():
        # 如果打包环境中的模型不存在，尝试使用系统缓存
        if model_name == "pyannote":
            cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
            if cache_dir.exists():
                return cache_dir
        elif model_name == "wav2vec2":
            cache_dir = Path.home() / ".cache" / "huggingface" / "transformers"
            if cache_dir.exists():
                return cache_dir

    return models_dir


def get_ffmpeg_path() -> Optional[Path]:
    """
    获取 FFmpeg 可执行文件路径

    Returns:
        Path: FFmpeg 路径，如果未找到返回 None
    """
    # 1. 检查打包目录中的 ffmpeg
    ffmpeg_dir = get_base_path() / "ffmpeg"
    ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe" if os.name == 'nt' else ffmpeg_dir / "ffmpeg"

    if ffmpeg_exe.exists():
        return ffmpeg_exe

    # 2. 检查系统 PATH
    import shutil
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg)

    # 3. 检查常见安装位置（Windows）
    if os.name == 'nt':
        common_paths = [
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "ffmpeg" / "bin" / "ffmpeg.exe",
        ]
        for path in common_paths:
            if path.exists():
                return path

    return None


def setup_environment():
    """
    设置打包环境的环境变量
    在应用启动时调用
    """
    base_path = get_base_path()

    # 设置环境变量
    os.environ["LOCALCLIP_BASE_PATH"] = str(base_path)
    os.environ["LOCALCLIP_PACKAGED"] = "1" if is_packaged() else "0"

    # FFmpeg 路径
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        os.environ["FFMPEG_BINARY"] = str(ffmpeg_path)
        os.environ["FFPROBE_BINARY"] = str(ffmpeg_path.parent / ("ffprobe.exe" if os.name == 'nt' else "ffprobe"))

    # 模型路径
    models_dir = base_path / "models"
    if models_dir.exists():
        # HuggingFace 缓存目录
        os.environ["HF_HOME"] = str(models_dir)
        os.environ["TRANSFORMERS_CACHE"] = str(models_dir)
        os.environ["HF_DATASETS_CACHE"] = str(models_dir)

    # Fish-Speech 路径
    fish_speech_dir = models_dir / "fish_speech"
    if fish_speech_dir.exists():
        os.environ["FISH_SPEECH_PATH"] = str(fish_speech_dir)

        # 添加到 Python 路径
        if str(fish_speech_dir) not in sys.path:
            sys.path.insert(0, str(fish_speech_dir))

    # 打印环境信息（仅开发模式）
    if not is_packaged():
        print("=" * 60)
        print("🔧 LocalClip Editor 环境信息")
        print("=" * 60)
        print(f"运行模式: {'打包模式' if is_packaged() else '开发模式'}")
        print(f"基础路径: {base_path}")
        print(f"FFmpeg: {ffmpeg_path or '未找到'}")
        print(f"模型目录: {models_dir}")
        print(f"Fish-Speech: {fish_speech_dir if fish_speech_dir.exists() else '未找到'}")
        print("=" * 60)


def get_upload_dir() -> Path:
    """获取上传目录"""
    return get_data_path("uploads")


def get_export_dir() -> Path:
    """获取导出目录"""
    return get_data_path("exports")


def get_audio_segments_dir() -> Path:
    """获取音频片段缓存目录"""
    return get_data_path("audio_segments")


def get_logs_dir() -> Path:
    """获取日志目录"""
    return get_data_path("logs")


# 路径配置类
class PathConfig:
    """路径配置单例"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 初始化所有路径
        self.base_path = get_base_path()
        self.is_packaged = is_packaged()

        # 数据目录
        self.uploads_dir = get_upload_dir()
        self.exports_dir = get_export_dir()
        self.audio_segments_dir = get_audio_segments_dir()
        self.logs_dir = get_logs_dir()

        # 模型目录
        self.models_dir = self.base_path / "models"
        self.fish_speech_dir = self.models_dir / "fish_speech"
        self.pyannote_dir = self.models_dir / "pyannote"
        self.wav2vec2_dir = self.models_dir / "wav2vec2"

        # FFmpeg
        self.ffmpeg_path = get_ffmpeg_path()

        # 前端静态文件目录
        if self.is_packaged:
            self.frontend_dist = get_resource_path("frontend/dist")
        else:
            self.frontend_dist = self.base_path / "frontend" / "dist"

        # 确保所有必要目录存在
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.audio_segments_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def __repr__(self):
        return (
            f"PathConfig(\n"
            f"  base_path={self.base_path},\n"
            f"  is_packaged={self.is_packaged},\n"
            f"  uploads_dir={self.uploads_dir},\n"
            f"  exports_dir={self.exports_dir},\n"
            f"  models_dir={self.models_dir},\n"
            f"  ffmpeg_path={self.ffmpeg_path}\n"
            f")"
        )


# 在模块导入时自动设置环境
setup_environment()