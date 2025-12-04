"""
说话人音频处理模块
用于筛选、拼接说话人音频片段
"""
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Tuple
from mos_scorer import get_audio_duration


class SpeakerAudioProcessor:
    """说话人音频处理器"""

    def __init__(self, target_duration: float = 10.0, silence_duration: float = 1.0):
        """
        初始化音频处理器

        Args:
            target_duration: 目标音频总时长（秒），默认10秒
            silence_duration: 音频片段之间的静音间隔（秒），默认1.0秒
        """
        self.target_duration = target_duration
        self.silence_duration = silence_duration
        self.sample_rate = 16000  # 统一采样率

    def select_best_segments(
        self,
        scored_segments: List[Tuple[str, float]]
    ) -> List[Tuple[str, float, float]]:
        """
        根据MOS分数筛选最佳音频片段，直到累计时长达到目标时长

        Args:
            scored_segments: 列表，每个元素为(音频路径, MOS分数)

        Returns:
            List[Tuple[str, float, float]]: 筛选后的片段列表，
                每个元素为(音频路径, MOS分数, 时长)
        """
        # 按MOS分数从高到低排序
        sorted_segments = sorted(scored_segments, key=lambda x: x[1], reverse=True)

        selected = []
        total_duration = 0.0

        for audio_path, mos_score in sorted_segments:
            # 获取音频时长
            duration = get_audio_duration(audio_path)

            if duration <= 0:
                continue

            # 添加到选中列表
            selected.append((audio_path, mos_score, duration))
            total_duration += duration

            # 如果累计时长达到目标，停止筛选
            if total_duration >= self.target_duration:
                break

        print(f"  筛选了 {len(selected)} 个片段，总时长: {total_duration:.2f}秒")
        return selected

    def sort_by_timestamp(
        self,
        segments: List[Tuple[str, float, float]]
    ) -> List[Tuple[str, float, float]]:
        """
        按照音频文件名中的时间戳排序片段

        音频文件名格式假设为: segment_XXXX.wav 或包含时间信息

        Args:
            segments: 音频片段列表

        Returns:
            List[Tuple[str, float, float]]: 排序后的片段列表
        """
        def extract_timestamp(path: str) -> float:
            """从文件名中提取时间戳"""
            filename = Path(path).stem
            try:
                # 尝试从文件名中提取数字作为时间戳
                # 例如: segment_0.wav, segment_1.wav
                parts = filename.split('_')
                if len(parts) > 1:
                    return float(parts[-1])
                return float(filename)
            except:
                return 0.0

        # 按时间戳排序
        sorted_segments = sorted(segments, key=lambda x: extract_timestamp(x[0]))
        return sorted_segments

    def concatenate_audio_segments(
        self,
        segments: List[Tuple[str, float, float]],
        output_path: str
    ) -> str:
        """
        拼接音频片段，片段之间加入静音间隔

        Args:
            segments: 音频片段列表，每个元素为(音频路径, MOS分数, 时长)
            output_path: 输出文件路径

        Returns:
            str: 输出文件路径
        """
        if not segments:
            raise ValueError("没有音频片段可以拼接")

        # 生成静音片段
        silence_samples = int(self.silence_duration * self.sample_rate)
        silence = np.zeros(silence_samples, dtype=np.float32)

        # 收集所有音频数据
        audio_data = []

        for i, (audio_path, _, _) in enumerate(segments):
            # 加载音频并重采样到目标采样率
            audio, sr = librosa.load(audio_path, sr=self.sample_rate)
            audio_data.append(audio)

            # 除了最后一个片段，都添加静音间隔
            if i < len(segments) - 1:
                audio_data.append(silence)

        # 拼接所有音频
        concatenated = np.concatenate(audio_data)

        # 保存拼接后的音频
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        sf.write(output_path, concatenated, self.sample_rate)
        print(f"  已保存拼接音频: {output_path}")

        return output_path

    def process_speaker_audio(
        self,
        speaker_id: int,
        scored_segments: List[Tuple[str, float]],
        output_dir: str
    ) -> Tuple[str, List[Tuple[str, float, float]]]:
        """
        处理单个说话人的音频：筛选、排序、拼接

        Args:
            speaker_id: 说话人ID
            scored_segments: MOS评分后的片段列表
            output_dir: 输出目录

        Returns:
            Tuple[str, List[Tuple[str, float, float]]]:
                (拼接后的音频路径, 选中的片段列表)
        """
        print(f"\n处理说话人 {speaker_id} 的音频...")

        # 1. 筛选最佳片段
        selected_segments = self.select_best_segments(scored_segments)

        if not selected_segments:
            raise ValueError(f"说话人 {speaker_id} 没有可用的音频片段")

        # 2. 按时间戳排序
        sorted_segments = self.sort_by_timestamp(selected_segments)

        # 3. 拼接音频
        output_path = str(Path(output_dir) / f"speaker_{speaker_id}_reference.wav")
        self.concatenate_audio_segments(sorted_segments, output_path)

        return output_path, sorted_segments

    def process_all_speakers(
        self,
        scored_segments_dict: Dict[int, List[Tuple[str, float]]],
        output_dir: str
    ) -> Dict[int, Tuple[str, List[Tuple[str, float, float]]]]:
        """
        处理所有说话人的音频

        Args:
            scored_segments_dict: 字典，key为说话人ID，value为MOS评分后的片段列表
            output_dir: 输出目录

        Returns:
            Dict[int, Tuple[str, List[Tuple[str, float, float]]]]:
                字典，key为说话人ID，value为(拼接后的音频路径, 选中的片段列表)
        """
        results = {}

        for speaker_id, scored_segments in scored_segments_dict.items():
            try:
                audio_path, selected_segments = self.process_speaker_audio(
                    speaker_id, scored_segments, output_dir
                )
                results[speaker_id] = (audio_path, selected_segments)
            except Exception as e:
                print(f"处理说话人 {speaker_id} 时出错: {str(e)}")
                continue

        return results
