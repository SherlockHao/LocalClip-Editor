"""
音频提取工具 - 从视频中按SRT时间段提取音频片段
"""
import os
import subprocess
from pathlib import Path
from typing import List, Dict
from srt_parser import SRTParser


class AudioExtractor:
    def __init__(self, cache_dir: str = "audio_segments"):
        """
        初始化音频提取器
        
        Args:
            cache_dir (str): 音频缓存目录
        """
        # 使用与上传文件不同的目录存储音频片段
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.srt_parser = SRTParser()

    def extract_audio_segments(self, video_path: str, srt_path: str, max_duration: float = 30.0) -> List[str]:
        """
        根据SRT文件的时间段提取音频片段

        Args:
            video_path (str): 视频文件路径
            srt_path (str): SRT字幕文件路径
            max_duration (float): 单个片段最大时长（秒），默认30秒，防止NISQA评分超限

        Returns:
            List[str]: 提取的音频文件路径列表
        """
        # 解析SRT文件
        subtitles = self.srt_parser.parse_srt(srt_path)

        audio_paths = []

        for i, subtitle in enumerate(subtitles):
            start_time = subtitle['start_time']
            end_time = subtitle['end_time']
            duration = end_time - start_time

            # 如果片段超过最大时长，分割处理
            if duration > max_duration:
                num_splits = int(duration / max_duration) + 1
                split_duration = duration / num_splits

                print(f"[警告] 字幕 #{i+1} 时长过长 ({duration:.1f}秒)，分割为 {num_splits} 段")

                for j in range(num_splits):
                    split_start = start_time + j * split_duration
                    split_end = min(split_start + split_duration, end_time)
                    split_duration_actual = split_end - split_start

                    audio_filename = f"segment_{i+1:03d}_{j+1:02d}_{split_start:.3f}_{split_end:.3f}.wav"
                    audio_path = self.cache_dir / audio_filename

                    self._extract_single_segment(
                        video_path, audio_path,
                        split_start, split_duration_actual
                    )
                    audio_paths.append(str(audio_path))
            else:
                # 正常处理
                audio_filename = f"segment_{i+1:03d}_{start_time:.3f}_{end_time:.3f}.wav"
                audio_path = self.cache_dir / audio_filename

                self._extract_single_segment(
                    video_path, audio_path,
                    start_time, duration
                )
                audio_paths.append(str(audio_path))

        return audio_paths

    def _extract_single_segment(self, video_path: str, audio_path: Path, start_time: float, duration: float):
        """
        提取单个音频片段

        Args:
            video_path: 视频文件路径
            audio_path: 输出音频路径
            start_time: 开始时间（秒）
            duration: 持续时间（秒）
        """
        audio_filename = os.path.basename(str(audio_path))

        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", video_path,
            "-ab", "16k",
            "-ac", "1",
            "-ar", "16000",
            "-y",
            str(audio_path)
        ]

        try:
            # 修复编码问题：使用 UTF-8 并忽略无法解码的字符
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode == 0:
                print(f"成功提取音频片段: {audio_filename}")
            else:
                print(f"提取音频片段失败: {audio_filename}")
        except Exception as e:
            print(f"提取音频片段异常: {audio_filename}, 错误: {str(e)}")

    def get_cache_dir(self) -> str:
        """获取音频缓存目录"""
        return str(self.cache_dir)


if __name__ == "__main__":
    # 示例用法
    extractor = AudioExtractor()
    
    # 示例路径 - 在实际使用中这些路径会作为参数传入
    # video_path = "path/to/video.mp4"
    # srt_path = "path/to/subtitle.srt"
    # audio_paths = extractor.extract_audio_segments(video_path, srt_path)
    # print(f"提取了 {len(audio_paths)} 个音频片段")
    pass