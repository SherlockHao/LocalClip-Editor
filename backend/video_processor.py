import os
import subprocess
import json
from pathlib import Path
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


class VideoProcessor:
    def __init__(self):
        pass

    def get_video_info(self, video_path: str) -> dict:
        """获取视频信息"""
        try:
            # 使用FFmpeg获取视频信息
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            info = json.loads(result.stdout)
            
            # 查找视频流
            video_stream = None
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            if video_stream:
                width = int(video_stream.get("width", 0))
                height = int(video_stream.get("height", 0))
                duration = float(info["format"].get("duration", 0))
                bitrate = info["format"].get("bit_rate", "N/A")
                
                return {
                    "width": width,
                    "height": height,
                    "resolution": f"{width}x{height}",
                    "duration": duration,
                    "duration_formatted": self.format_duration(duration),
                    "bitrate": bitrate,
                    "codec": video_stream.get("codec_name", "N/A")
                }
            else:
                return {"error": "未找到视频流"}
        except Exception as e:
            return {"error": str(e)}

    def format_duration(self, seconds: float) -> str:
        """格式化时长为 HH:MM:SS 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def export_video(
        self, 
        video_path: str, 
        export_path: str, 
        subtitle_filename: str = None, 
        export_hard_subtitles: bool = False
    ) -> dict:
        """导出视频"""
        try:
            if export_hard_subtitles and subtitle_filename:
                # 添加硬字幕到视频
                return self._export_with_hard_subtitles(video_path, export_path, subtitle_filename)
            else:
                # 简单复制视频或添加软字幕
                return self._export_basic_video(video_path, export_path)

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _export_basic_video(self, video_path: str, export_path: str) -> dict:
        """基础视频导出（无字幕）"""
        try:
            # 使用FFmpeg进行快速复制
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-c", "copy",  # 快速复制，不做重新编码
                "-y",  # 覆盖输出文件
                export_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                file_size = os.path.getsize(export_path)
                return {
                    "export_path": export_path,
                    "file_size": file_size,
                    "success": True
                }
            else:
                return {
                    "success": False,
                    "error": result.stderr
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _export_with_hard_subtitles(self, video_path: str, export_path: str, subtitle_filename: str) -> dict:
        """导出带硬字幕的视频"""
        try:
            # 使用FFmpeg添加硬字幕
            uploads_dir = Path("uploads")
            subtitle_path = uploads_dir / subtitle_filename
            
            if not subtitle_path.exists():
                return {"success": False, "error": "字幕文件不存在"}
            
            # 使用FFmpeg添加硬字幕
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vf", f"subtitles={subtitle_path}",
                "-c:a", "copy",  # 保持音频不变
                "-y",  # 覆盖输出文件
                export_path
            ]
            
            # 尝试使用硬件加速
            if self._has_hardware_encoder():
                cmd = [
                    "ffmpeg",
                    "-hwaccel", "auto",
                    "-i", video_path,
                    "-vf", f"subtitles={subtitle_path}",
                    "-c:a", "copy",
                    "-c:v", "h264_videotoolbox",  # 使用苹果的硬件编码器
                    "-y",
                    export_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                file_size = os.path.getsize(export_path)
                return {
                    "export_path": export_path,
                    "file_size": file_size,
                    "success": True
                }
            else:
                # 如果硬件加速失败，回退到软件编码
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vf", f"subtitles={subtitle_path}",
                    "-c:a", "copy",
                    "-y",
                    export_path
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    file_size = os.path.getsize(export_path)
                    return {
                        "export_path": export_path,
                        "file_size": file_size,
                        "success": True
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr
                    }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _has_hardware_encoder(self) -> bool:
        """检查是否有硬件编码器"""
        try:
            cmd = ["ffmpeg", "-encoders"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return "h264_videotoolbox" in result.stdout
        except:
            return False