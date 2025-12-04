"""
MOS (Mean Opinion Score) 评分模块
用于评估音频质量
"""
import librosa
from speechmos import dnsmos
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np


class MOSScorer:
    """音频质量评分器"""

    def __init__(self, target_sr: int = 16000):
        """
        初始化MOS评分器

        Args:
            target_sr: 目标采样率，DNSMOS使用16000Hz
        """
        self.target_sr = target_sr

    def score_audio(self, audio_path: str) -> float:
        """
        对单个音频文件进行MOS打分

        Args:
            audio_path: 音频文件路径

        Returns:
            float: MOS分数 (P.808 MOS分数，范围通常在1-5之间)
        """
        try:
            # 加载音频并重采样到16kHz
            audio, sr = librosa.load(audio_path, sr=self.target_sr)

            # 如果音频太短（小于0.1秒），返回较低分数
            if len(audio) < self.target_sr * 0.1:
                return 1.0

            # 使用DNSMOS进行评分
            mos_result = dnsmos.run(audio, sr=self.target_sr)

            # 返回P.808 MOS分数
            return mos_result['p808_mos']
        except Exception as e:
            print(f"对音频 {audio_path} 评分时出错: {str(e)}")
            return 0.0  # 出错返回0分

    def score_audio_batch(self, audio_paths: List[str]) -> List[Tuple[str, float]]:
        """
        批量对多个音频文件进行MOS打分

        Args:
            audio_paths: 音频文件路径列表

        Returns:
            List[Tuple[str, float]]: 列表，每个元素为(音频路径, MOS分数)
        """
        results = []
        for audio_path in audio_paths:
            score = self.score_audio(audio_path)
            results.append((audio_path, score))
        return results

    def score_speaker_audios(
        self,
        audio_dir: str,
        speaker_segments: Dict[int, List[str]]
    ) -> Dict[int, List[Tuple[str, float]]]:
        """
        对每个说话人的音频片段进行MOS打分

        Args:
            audio_dir: 音频片段所在目录（可以为None，如果segment_files已经是完整路径）
            speaker_segments: 字典，key为说话人ID，value为该说话人的音频文件路径列表

        Returns:
            Dict[int, List[Tuple[str, float]]]: 字典，key为说话人ID，
                value为列表，每个元素为(音频路径, MOS分数)
        """
        results = {}

        for speaker_id, segment_files in speaker_segments.items():
            print(f"正在为说话人 {speaker_id} 的音频进行MOS评分...")

            # 检查segment_files是否已经是完整路径
            # 如果第一个路径是绝对路径或包含目录分隔符，则认为已经是完整路径
            if segment_files and (Path(segment_files[0]).is_absolute() or '/' in segment_files[0]):
                # 已经是完整路径，直接使用
                full_paths = segment_files
            else:
                # 需要拼接audio_dir
                full_paths = [str(Path(audio_dir) / f) for f in segment_files]

            # 批量打分
            scores = self.score_audio_batch(full_paths)
            results[speaker_id] = scores

            # 打印统计信息
            if scores:
                avg_score = np.mean([s for _, s in scores])
                print(f"  说话人 {speaker_id}: {len(scores)} 个片段, 平均MOS分数: {avg_score:.2f}")

        return results


def get_audio_duration(audio_path: str) -> float:
    """
    获取音频时长（秒）

    Args:
        audio_path: 音频文件路径

    Returns:
        float: 音频时长（秒）
    """
    try:
        audio, sr = librosa.load(audio_path, sr=None)
        return len(audio) / sr
    except Exception as e:
        print(f"获取音频时长失败 {audio_path}: {str(e)}")
        return 0.0
