"""
跨平台工具模块
支持 Windows (NVIDIA GPU), macOS (MPS), Linux (CUDA)
"""

import os
import sys
import platform
import subprocess
from typing import Optional, Dict, Literal


DeviceType = Literal["cuda", "mps", "cpu"]
VideoEncoderType = Literal["h264_nvenc", "hevc_nvenc", "h264_videotoolbox", "libx264"]


def get_platform() -> str:
    """
    获取当前平台

    Returns:
        "windows", "macos", "linux"
    """
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    else:
        return "linux"


def detect_gpu_device() -> DeviceType:
    """
    检测可用的 GPU 设备

    优先级:
    1. CUDA (NVIDIA GPU) - Windows/Linux
    2. MPS (Apple Silicon) - macOS
    3. CPU (fallback)

    Returns:
        "cuda", "mps", 或 "cpu"
    """
    try:
        import torch

        # 1. 检查 CUDA (NVIDIA GPU)
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ 检测到 NVIDIA GPU: {gpu_name}")
            return "cuda"

        # 2. 检查 MPS (Apple Silicon)
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            print(f"✅ 检测到 Apple Silicon GPU (MPS)")
            return "mps"

        # 3. Fallback to CPU
        print(f"ℹ️  未检测到 GPU，使用 CPU")
        return "cpu"

    except ImportError:
        print(f"⚠️  PyTorch 未安装，默认使用 CPU")
        return "cpu"


def get_optimal_device() -> DeviceType:
    """
    获取最优设备（兼容旧代码）

    Returns:
        设备名称: "cuda", "mps", 或 "cpu"
    """
    return detect_gpu_device()


def clear_gpu_cache(device: DeviceType):
    """
    清理 GPU 缓存

    Args:
        device: 设备类型
    """
    try:
        import torch

        if device == "cuda":
            torch.cuda.empty_cache()
            print("🧹 已清理 CUDA 缓存")
        elif device == "mps":
            torch.mps.empty_cache()
            print("🧹 已清理 MPS 缓存")

    except Exception as e:
        print(f"⚠️  清理缓存失败: {e}")


def get_gpu_info() -> Dict[str, any]:
    """
    获取 GPU 信息

    Returns:
        包含 GPU 信息的字典
    """
    info = {
        "platform": get_platform(),
        "device": detect_gpu_device(),
        "gpu_available": False,
        "gpu_name": None,
        "gpu_memory": None,
        "cuda_version": None
    }

    try:
        import torch

        if torch.cuda.is_available():
            info["gpu_available"] = True
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_memory"] = torch.cuda.get_device_properties(0).total_memory / 1024**3  # GB
            info["cuda_version"] = torch.version.cuda

        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            info["gpu_available"] = True
            info["gpu_name"] = "Apple Silicon (MPS)"

    except ImportError:
        pass

    return info


def detect_video_encoder() -> VideoEncoderType:
    """
    检测可用的视频硬件编码器

    优先级:
    1. h264_nvenc (NVIDIA GPU) - Windows/Linux
    2. h264_videotoolbox (Apple Silicon) - macOS
    3. libx264 (软件编码，通用 fallback)

    Returns:
        编码器名称
    """
    platform_name = get_platform()

    # 检查 ffmpeg 是否可用
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5
        )
        available_encoders = result.stdout

    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  ffmpeg 未找到，使用软件编码")
        return "libx264"

    # 根据平台和可用编码器选择
    if platform_name == "windows" or platform_name == "linux":
        # NVIDIA GPU 编码器
        if "h264_nvenc" in available_encoders:
            print("✅ 使用 NVIDIA GPU 硬件编码器: h264_nvenc")
            return "h264_nvenc"
        elif "hevc_nvenc" in available_encoders:
            print("✅ 使用 NVIDIA GPU 硬件编码器: hevc_nvenc")
            return "hevc_nvenc"

    elif platform_name == "macos":
        # Apple VideoToolbox 编码器
        if "h264_videotoolbox" in available_encoders:
            print("✅ 使用 Apple 硬件编码器: h264_videotoolbox")
            return "h264_videotoolbox"

    # Fallback: 软件编码
    print("ℹ️  使用软件编码器: libx264")
    return "libx264"


def check_hardware_encoder_support(encoder: str) -> bool:
    """
    检查指定的硬件编码器是否支持

    Args:
        encoder: 编码器名称 (如 "h264_nvenc", "h264_videotoolbox")

    Returns:
        是否支持
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return encoder in result.stdout

    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_ffmpeg_encoder_args(encoder: Optional[VideoEncoderType] = None) -> list:
    """
    获取 FFmpeg 编码器参数

    Args:
        encoder: 指定编码器，如果为 None 则自动检测

    Returns:
        FFmpeg 命令行参数列表
    """
    if encoder is None:
        encoder = detect_video_encoder()

    args = ["-c:v", encoder]

    # NVIDIA GPU 编码器的额外参数
    if encoder in ["h264_nvenc", "hevc_nvenc"]:
        args.extend([
            "-preset", "p4",  # 平衡质量和速度
            "-tune", "hq",    # 高质量
            "-rc", "vbr",     # 可变比特率
            "-cq", "23",      # 质量控制
            "-b:v", "0"       # 让编码器自动选择比特率
        ])

    # Apple VideoToolbox 编码器的参数
    elif encoder == "h264_videotoolbox":
        args.extend([
            "-b:v", "5M"      # 5 Mbps 比特率
        ])

    # 软件编码器 (libx264)
    elif encoder == "libx264":
        args.extend([
            "-preset", "medium",  # 平衡速度和质量
            "-crf", "23"          # 质量控制
        ])

    return args


def print_platform_info():
    """打印平台和硬件信息（调试用）"""
    print("\n" + "=" * 60)
    print("🖥️  平台信息")
    print("=" * 60)

    info = get_gpu_info()

    print(f"操作系统: {info['platform'].upper()}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"设备: {info['device'].upper()}")

    if info['gpu_available']:
        print(f"GPU 名称: {info['gpu_name']}")
        if info['gpu_memory']:
            print(f"GPU 内存: {info['gpu_memory']:.2f} GB")
        if info['cuda_version']:
            print(f"CUDA 版本: {info['cuda_version']}")
    else:
        print("GPU: 不可用")

    # 视频编码器
    encoder = detect_video_encoder()
    print(f"视频编码器: {encoder}")

    print("=" * 60)


# 兼容旧代码的函数
def get_device():
    """兼容旧代码：获取设备"""
    return detect_gpu_device()


if __name__ == "__main__":
    # 测试
    print_platform_info()
