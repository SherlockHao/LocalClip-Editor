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

    def extract_audio_segments(self, video_path: str, srt_path: str) -> List[str]:
        """
        根据SRT文件的时间段提取音频片段
        
        Args:
            video_path (str): 视频文件路径
            srt_path (str): SRT字幕文件路径
            
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
            
            # 生成音频文件名
            audio_filename = f"segment_{i+1:03d}_{start_time:.3f}_{end_time:.3f}.wav"
            audio_path = self.cache_dir / audio_filename
            
            # 使用FFmpeg从视频中提取指定时间段的音频
            cmd = [
                "ffmpeg",
                "-ss", str(start_time),  # 开始时间
                "-t", str(duration),     # 持续时间
                "-i", video_path,        # 输入视频
                "-ab", "16k",            # 音频比特率
                "-ac", "1",              # 单声道
                "-ar", "16000",          # 采样率
                "-y",                    # 覆盖输出文件
                str(audio_path)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    audio_paths.append(str(audio_path))
                    print(f"成功提取音频片段: {audio_filename}")
                else:
                    print(f"提取音频片段失败: {audio_filename}, 错误: {result.stderr}")
            except Exception as e:
                print(f"提取音频片段异常: {audio_filename}, 错误: {str(e)}")
        
        return audio_paths

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