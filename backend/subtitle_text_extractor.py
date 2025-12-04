"""
字幕文本提取模块
根据音频片段提取对应的字幕文本
"""
import re
from pathlib import Path
from typing import List, Tuple, Dict
from srt_parser import SRTParser


class SubtitleTextExtractor:
    """字幕文本提取器"""

    def __init__(self):
        self.srt_parser = SRTParser()

    def extract_time_from_filename(self, audio_path: str) -> Tuple[float, float]:
        """
        从音频文件名中提取开始和结束时间

        音频文件名格式: segment_XXX_START_END.wav
        例如: segment_001_1.234_3.456.wav

        Args:
            audio_path: 音频文件路径

        Returns:
            Tuple[float, float]: (开始时间, 结束时间)
        """
        filename = Path(audio_path).stem  # 获取不带扩展名的文件名

        # 匹配格式: segment_XXX_START_END
        pattern = r'segment_\d+_(\d+\.\d+)_(\d+\.\d+)'
        match = re.search(pattern, filename)

        if match:
            start_time = float(match.group(1))
            end_time = float(match.group(2))
            return start_time, end_time
        else:
            raise ValueError(f"无法从文件名中提取时间: {filename}")

    def find_subtitle_by_time(
        self,
        subtitles: List[Dict],
        start_time: float,
        end_time: float,
        tolerance: float = 0.1
    ) -> str:
        """
        根据时间范围查找对应的字幕文本

        Args:
            subtitles: 字幕列表
            start_time: 开始时间
            end_time: 结束时间
            tolerance: 时间容差（秒）

        Returns:
            str: 对应的字幕文本
        """
        for subtitle in subtitles:
            sub_start = subtitle['start_time']
            sub_end = subtitle['end_time']

            # 检查时间是否匹配（允许一定的容差）
            if (abs(sub_start - start_time) <= tolerance and
                abs(sub_end - end_time) <= tolerance):
                return subtitle['text']

        # 如果没有精确匹配，返回空字符串或警告
        return ""

    def extract_text_for_segments(
        self,
        audio_segments: List[Tuple[str, float, float]],
        srt_path: str
    ) -> List[Tuple[str, str]]:
        """
        为音频片段提取对应的字幕文本

        Args:
            audio_segments: 音频片段列表，每个元素为(音频路径, MOS分数, 时长)
            srt_path: SRT字幕文件路径

        Returns:
            List[Tuple[str, str]]: 列表，每个元素为(音频路径, 字幕文本)
        """
        # 解析SRT文件
        subtitles = self.srt_parser.parse_srt(srt_path)

        results = []
        for audio_path, _, _ in audio_segments:
            try:
                # 从文件名提取时间
                start_time, end_time = self.extract_time_from_filename(audio_path)

                # 查找对应的字幕文本
                text = self.find_subtitle_by_time(subtitles, start_time, end_time)

                if text:
                    results.append((audio_path, text))
                else:
                    print(f"警告: 未找到音频片段对应的字幕文本: {audio_path}")

            except Exception as e:
                print(f"处理音频片段 {audio_path} 时出错: {str(e)}")
                continue

        return results

    def concatenate_texts(
        self,
        text_segments: List[Tuple[str, str]],
        separator: str = " "
    ) -> str:
        """
        拼接字幕文本

        Args:
            text_segments: 文本片段列表，每个元素为(音频路径, 字幕文本)
            separator: 文本之间的分隔符

        Returns:
            str: 拼接后的文本
        """
        texts = [text for _, text in text_segments if text.strip()]
        return separator.join(texts)

    def process_speaker_text(
        self,
        speaker_id: int,
        audio_segments: List[Tuple[str, float, float]],
        srt_path: str
    ) -> str:
        """
        处理单个说话人的文本：提取并拼接

        Args:
            speaker_id: 说话人ID
            audio_segments: 音频片段列表
            srt_path: SRT字幕文件路径

        Returns:
            str: 拼接后的参考文本
        """
        print(f"\n提取说话人 {speaker_id} 的参考文本...")

        # 提取文本
        text_segments = self.extract_text_for_segments(audio_segments, srt_path)

        if not text_segments:
            raise ValueError(f"说话人 {speaker_id} 没有可用的字幕文本")

        # 拼接文本
        reference_text = self.concatenate_texts(text_segments)

        print(f"  提取了 {len(text_segments)} 段字幕")
        print(f"  参考文本: {reference_text[:100]}...")  # 显示前100个字符

        return reference_text

    def process_all_speakers(
        self,
        speaker_segments_dict: Dict[int, List[Tuple[str, float, float]]],
        srt_path: str
    ) -> Dict[int, str]:
        """
        处理所有说话人的文本

        Args:
            speaker_segments_dict: 字典，key为说话人ID，value为音频片段列表
            srt_path: SRT字幕文件路径

        Returns:
            Dict[int, str]: 字典，key为说话人ID，value为拼接后的参考文本
        """
        results = {}

        for speaker_id, audio_segments in speaker_segments_dict.items():
            try:
                reference_text = self.process_speaker_text(
                    speaker_id, audio_segments, srt_path
                )
                results[speaker_id] = reference_text
            except Exception as e:
                print(f"处理说话人 {speaker_id} 的文本时出错: {str(e)}")
                continue

        return results
