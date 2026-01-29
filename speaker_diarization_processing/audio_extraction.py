"""
音频提取工具 - 从视频中按SRT时间段提取音频片段
"""
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import librosa
import soundfile as sf
from srt_parser import SRTParser
from audio_silence_trimmer import AudioSilenceTrimmer


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

        # 初始化语音检测工具
        self.trimmer = AudioSilenceTrimmer(
            threshold_db=-40.0,
            frame_length_ms=25.0,
            hop_length_ms=10.0
        )
        self.sample_rate = 16000

    def _detect_speech_segments(self, audio_data: np.ndarray, sr: int) -> List[Dict]:
        """
        检测音频中的语音段

        Args:
            audio_data: 音频数据
            sr: 采样率

        Returns:
            语音段列表 [{'start': float, 'end': float}, ...]
        """
        return self.trimmer.detect_speech_segments(audio_data, sr)

    def _remove_long_silences(self, audio_data: np.ndarray, sr: int,
                               min_silence_duration: float = 2.0,
                               keep_left: float = 0.5) -> Tuple[np.ndarray, List[Dict]]:
        """
        去除长静音段（保留左侧部分）

        Args:
            audio_data: 音频数据
            sr: 采样率
            min_silence_duration: 最小静音时长（秒）
            keep_left: 保留静音左侧的时长（秒）

        Returns:
            处理后的音频数据, 以及新的语音段信息
        """
        # 1. 检测语音段
        speech_segments = self._detect_speech_segments(audio_data, sr)

        if len(speech_segments) == 0:
            return audio_data, []

        # 2. 找出所有静音段
        silence_segments = []
        for i in range(len(speech_segments) - 1):
            silence_start = speech_segments[i]['end']
            silence_end = speech_segments[i + 1]['start']
            silence_duration = silence_end - silence_start

            if silence_duration >= min_silence_duration:
                silence_segments.append({
                    'start': silence_start,
                    'end': silence_end,
                    'duration': silence_duration
                })

        if len(silence_segments) == 0:
            return audio_data, speech_segments

        # 3. 构建需要保留的音频段
        keep_segments = []
        current_time = 0.0

        for i, speech_seg in enumerate(speech_segments):
            # 添加当前语音段
            keep_segments.append({
                'original_start': speech_seg['start'],
                'original_end': speech_seg['end'],
                'new_start': current_time,
                'new_end': current_time + (speech_seg['end'] - speech_seg['start'])
            })
            current_time = keep_segments[-1]['new_end']

            # 检查后面是否有长静音
            if i < len(speech_segments) - 1:
                next_speech = speech_segments[i + 1]
                silence_duration = next_speech['start'] - speech_seg['end']

                if silence_duration >= min_silence_duration:
                    # 保留左侧 keep_left 秒
                    keep_segments.append({
                        'original_start': speech_seg['end'],
                        'original_end': speech_seg['end'] + keep_left,
                        'new_start': current_time,
                        'new_end': current_time + keep_left
                    })
                    current_time += keep_left
                else:
                    # 短静音，全部保留
                    keep_segments.append({
                        'original_start': speech_seg['end'],
                        'original_end': next_speech['start'],
                        'new_start': current_time,
                        'new_end': current_time + silence_duration
                    })
                    current_time += silence_duration

        # 4. 拼接音频
        audio_parts = []
        for seg in keep_segments:
            start_sample = int(seg['original_start'] * sr)
            end_sample = int(seg['original_end'] * sr)
            audio_parts.append(audio_data[start_sample:end_sample])

        processed_audio = np.concatenate(audio_parts) if audio_parts else np.array([])

        # 5. 重新计算语音段时间（基于新音频）
        new_speech_segments = self._detect_speech_segments(processed_audio, sr)

        return processed_audio, new_speech_segments

    def _find_split_point(self, audio_data: np.ndarray, sr: int,
                          max_duration: float = 30.0) -> Optional[float]:
        """
        在音频中查找合适的切分点（静音位置）

        Args:
            audio_data: 音频数据
            sr: 采样率
            max_duration: 最大时长（秒）

        Returns:
            切分点时间（秒），如果没找到合适的静音则返回 None
        """
        audio_duration = len(audio_data) / sr

        if audio_duration <= max_duration:
            return None

        # 检测语音段
        speech_segments = self._detect_speech_segments(audio_data, sr)

        if len(speech_segments) <= 1:
            # 没有明显的静音段，强制在 max_duration 处切分
            return None

        # 找出所有静音段
        silence_segments = []
        for i in range(len(speech_segments) - 1):
            silence_start = speech_segments[i]['end']
            silence_end = speech_segments[i + 1]['start']
            silence_segments.append({
                'start': silence_start,
                'end': silence_end,
                'mid': (silence_start + silence_end) / 2
            })

        # 找出 max_duration 以内最后一个静音段的中点
        valid_silences = [s for s in silence_segments if s['mid'] <= max_duration]

        if valid_silences:
            # 返回最后一个符合条件的静音段的中点
            return valid_silences[-1]['mid']
        else:
            # 没有找到合适的静音，返回 None（强制硬切）
            return None

    def _process_long_audio(self, audio_path: Path, max_duration: float = 30.0) -> Path:
        """
        处理长音频：去除长静音、智能切分

        Args:
            audio_path: 音频文件路径
            max_duration: 最大时长（秒）

        Returns:
            处理后的音频路径（原地覆盖）
        """
        # 1. 加载音频
        audio_data, sr = librosa.load(str(audio_path), sr=self.sample_rate, mono=True)
        original_duration = len(audio_data) / sr

        print(f"  [智能处理] 原始时长: {original_duration:.2f}s")

        # 2. 去除长静音（>2s），保留左侧0.5s
        processed_audio, speech_segments = self._remove_long_silences(
            audio_data, sr,
            min_silence_duration=2.0,
            keep_left=0.5
        )

        processed_duration = len(processed_audio) / sr
        print(f"  [智能处理] 去除长静音后: {processed_duration:.2f}s")

        # 3. 如果还是超过 max_duration，智能切分
        if processed_duration > max_duration:
            split_point = self._find_split_point(processed_audio, sr, max_duration)

            if split_point is not None:
                # 在静音处切分
                split_sample = int(split_point * sr)
                processed_audio = processed_audio[:split_sample]
                print(f"  [智能处理] 在静音处切分 {split_point:.2f}s")
            else:
                # 强制硬切
                split_sample = int(max_duration * sr)
                processed_audio = processed_audio[:split_sample]
                print(f"  [智能处理] 强制硬切在 {max_duration:.2f}s")

        final_duration = len(processed_audio) / sr
        print(f"  [智能处理] 最终时长: {final_duration:.2f}s")

        # 4. 保存处理后的音频（覆盖原文件）
        sf.write(str(audio_path), processed_audio, sr)

        return audio_path

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

            # 文件名保持原始时间戳
            audio_filename = f"segment_{i+1:03d}_{start_time:.3f}_{end_time:.3f}.wav"
            audio_path = self.cache_dir / audio_filename

            # 如果片段超过最大时长，使用智能处理
            if duration > max_duration:
                print(f"[智能处理] 字幕 #{i+1} 时长过长 ({duration:.1f}秒)，应用智能切分")

                # 先提取完整音频
                self._extract_single_segment(
                    video_path, audio_path,
                    start_time, duration
                )

                # 然后应用智能处理：去除长静音、智能切分
                self._process_long_audio(audio_path, max_duration)

                audio_paths.append(str(audio_path))
            else:
                # 正常处理
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