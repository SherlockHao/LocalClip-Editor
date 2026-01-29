import os
import subprocess
import json
from pathlib import Path
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


class VideoProcessor:
    # 支持的视频编码格式
    SUPPORTED_VIDEO_CODECS = {
        # H.264/AVC - 最常用的编码
        'h264', 'avc1', 'avc',
        # H.265/HEVC - 高效编码
        'hevc', 'h265', 'hvc1',
        # VP8/VP9 - Google 开发的编码
        'vp8', 'vp9',
        # AV1 - 开源新一代编码
        'av1', 'av01',
        # MPEG-4
        'mpeg4', 'mp4v',
        # ProRes - Apple 专业视频编码
        'prores', 'prores_ks', 'prores_aw',
        # Motion JPEG
        'mjpeg',
        # MPEG-2
        'mpeg2video',
        # MPEG-1
        'mpeg1video',
        # Windows Media Video
        'wmv1', 'wmv2', 'wmv3', 'vc1',
        # DV 格式
        'dvvideo',
        # DNxHD - Avid 专业编码
        'dnxhd',
        # Theora
        'theora',
    }

    # 支持的音频编码格式
    SUPPORTED_AUDIO_CODECS = {
        'aac', 'mp3', 'ac3', 'eac3', 'flac', 'opus', 'vorbis',
        'pcm_s16le', 'pcm_s24le', 'pcm_s32le', 'pcm_f32le',
        'wmav1', 'wmav2', 'alac', 'dts',
    }

    def __init__(self):
        pass

    def validate_video_codec(self, video_path: str) -> dict:
        """
        验证视频编码格式是否支持

        返回:
            {
                "valid": bool,
                "video_codec": str,
                "audio_codec": str,
                "error": str (如果不支持)
            }
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                video_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

            if result.returncode != 0:
                return {
                    "valid": False,
                    "error": "无法读取视频文件，文件可能已损坏"
                }

            info = json.loads(result.stdout)
            streams = info.get("streams", [])

            video_codec = None
            audio_codec = None

            for stream in streams:
                codec_type = stream.get("codec_type")
                codec_name = stream.get("codec_name", "").lower()

                if codec_type == "video" and not video_codec:
                    video_codec = codec_name
                elif codec_type == "audio" and not audio_codec:
                    audio_codec = codec_name

            # 检查是否有视频流
            if not video_codec:
                return {
                    "valid": False,
                    "error": "文件中未找到视频流"
                }

            # 检查视频编码是否支持
            if video_codec not in self.SUPPORTED_VIDEO_CODECS:
                return {
                    "valid": False,
                    "video_codec": video_codec,
                    "audio_codec": audio_codec,
                    "error": f"不支持的视频编码格式: {video_codec}。支持的格式: H.264, H.265/HEVC, VP9, AV1, MPEG-4, ProRes 等"
                }

            # 检查音频编码（如果有）
            if audio_codec and audio_codec not in self.SUPPORTED_AUDIO_CODECS:
                # 音频编码不支持时只警告，不阻止上传
                print(f"[视频验证] ⚠️ 音频编码 {audio_codec} 可能不被完全支持", flush=True)

            return {
                "valid": True,
                "video_codec": video_codec,
                "audio_codec": audio_codec
            }

        except json.JSONDecodeError:
            return {
                "valid": False,
                "error": "无法解析视频信息，文件可能已损坏"
            }
        except FileNotFoundError:
            return {
                "valid": False,
                "error": "FFprobe 未安装或不在系统路径中"
            }
        except Exception as e:
            return {
                "valid": False,
                "error": f"验证视频时出错: {str(e)}"
            }

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
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
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
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

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
            
            # 使用跨平台的编码器检测（支持 NVIDIA GPU, Apple Silicon, CPU）
            from platform_utils import get_ffmpeg_encoder_args

            # 获取最优编码器参数
            encoder_args = get_ffmpeg_encoder_args()

            # 构建命令
            cmd = [
                "ffmpeg",
                "-hwaccel", "auto",
                "-i", video_path,
                "-vf", f"subtitles={subtitle_path}",
                "-c:a", "copy",
            ] + encoder_args + [
                "-y",
                export_path
            ]

            print(f"🎬 使用编码器: {encoder_args[1]}")

            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

            if result.returncode == 0:
                file_size = os.path.getsize(export_path)
                return {
                    "export_path": export_path,
                    "file_size": file_size,
                    "success": True
                }
            else:
                # 如果硬件加速失败，回退到软件编码
                print(f"⚠️  硬件编码失败，回退到软件编码")
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vf", f"subtitles={subtitle_path}",
                    "-c:a", "copy",
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "23",
                    "-y",
                    export_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')

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
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return "h264_videotoolbox" in result.stdout
        except:
            return False