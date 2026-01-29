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
from audio_silence_trimmer import AudioSilenceTrimmer


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

        # 初始化静音切割器（用于检测有效语音段）
        self.trimmer = AudioSilenceTrimmer(
            threshold_db=-40.0,
            frame_length_ms=25.0,
            hop_length_ms=10.0
        )

    def select_best_segments(
        self,
        scored_segments: List[Tuple[str, float]]
    ) -> List[Tuple[str, float, float]]:
        """
        根据MOS分数筛选最佳音频片段，直到累计有效语音时长达到目标时长

        Args:
            scored_segments: 列表，每个元素为(音频路径, MOS分数)

        Returns:
            List[Tuple[str, float, float]]: 筛选后的片段列表，
                每个元素为(音频路径, MOS分数, 有效语音时长)
        """
        # 按MOS分数从高到低排序
        sorted_segments = sorted(scored_segments, key=lambda x: x[1], reverse=True)

        selected = []
        total_effective_duration = 0.0

        for audio_path, mos_score in sorted_segments:
            try:
                # 加载音频
                audio_data, sr = librosa.load(audio_path, sr=self.sample_rate)

                # 检测语音段
                speech_segments = self.trimmer.detect_speech_segments(audio_data, sr)

                if not speech_segments:
                    print(f"  跳过片段 {Path(audio_path).name}：未检测到语音")
                    continue

                # 计算有效语音时长（所有语音段的总时长）
                effective_duration = sum(
                    seg['end'] - seg['start'] for seg in speech_segments
                )

                if effective_duration <= 0:
                    continue

                # 添加到选中列表
                selected.append((audio_path, mos_score, effective_duration))
                total_effective_duration += effective_duration

                print(f"  已选择: {Path(audio_path).name}, MOS: {mos_score:.3f}, "
                      f"有效语音: {effective_duration:.2f}秒 "
                      f"(检测到 {len(speech_segments)} 个语音段)")

                # 如果累计有效时长达到目标，停止筛选
                if total_effective_duration >= self.target_duration:
                    break

            except Exception as e:
                print(f"  处理片段 {audio_path} 时出错: {str(e)}")
                continue

        print(f"  筛选了 {len(selected)} 个片段，累计有效语音时长: {total_effective_duration:.2f}秒")
        return selected

    def sort_by_timestamp(
        self,
        segments: List[Tuple[str, float, float]]
    ) -> List[Tuple[str, float, float]]:
        """
        按照音频文件名中的时间戳排序片段

        音频文件名格式：segment_XXX_START_END.wav
        例如：segment_001_19.980_81.539.wav

        Args:
            segments: 音频片段列表

        Returns:
            List[Tuple[str, float, float]]: 排序后的片段列表
        """
        def extract_timestamp(path: str) -> float:
            """从文件名中提取开始时间戳"""
            filename = Path(path).stem
            try:
                # 文件名格式：segment_XXX_START_END 或 segment_XXX_YY_START_END（分割后的）
                # 例如：segment_001_19.980_81.539 或 segment_032_01_19.980_50.000
                parts = filename.split('_')

                if len(parts) >= 3:
                    # 尝试倒数第二个部分（开始时间）
                    try:
                        return float(parts[-2])
                    except ValueError:
                        pass

                # 后备方案：使用第一个数字部分
                if len(parts) > 1:
                    return float(parts[1])

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
        拼接音频片段，仅保留语音段，片段之间加入静音间隔

        Args:
            segments: 音频片段列表，每个元素为(音频路径, MOS分数, 有效语音时长)
            output_path: 输出文件路径

        Returns:
            str: 输出文件路径
        """
        if not segments:
            raise ValueError("没有音频片段可以拼接")

        # 生成静音片段
        silence_samples = int(self.silence_duration * self.sample_rate)
        silence = np.zeros(silence_samples, dtype=np.float32)

        # 收集所有音频数据（仅保留语音段）
        audio_data = []

        for i, (audio_path, _, _) in enumerate(segments):
            try:
                # 加载音频并重采样到目标采样率
                audio, sr = librosa.load(audio_path, sr=self.sample_rate)

                # 检测语音段
                speech_segments = self.trimmer.detect_speech_segments(audio, sr)

                if not speech_segments:
                    print(f"  警告: 片段 {Path(audio_path).name} 未检测到语音，使用原始音频")
                    audio_data.append(audio)
                else:
                    # 使用trim_silence提取语音段（去除冗余静音）
                    trimmed_audio = self.trimmer.trim_silence(audio, sr, speech_segments)
                    audio_data.append(trimmed_audio)

                    trimmed_duration = len(trimmed_audio) / sr
                    print(f"  已处理片段 {Path(audio_path).name}: "
                          f"原始 {len(audio)/sr:.2f}s -> 去静音后 {trimmed_duration:.2f}s")

                # 除了最后一个片段，都添加静音间隔
                if i < len(segments) - 1:
                    audio_data.append(silence)

            except Exception as e:
                print(f"  处理片段 {audio_path} 时出错: {str(e)}")
                continue

        if not audio_data:
            raise ValueError("没有可用的音频片段")

        # 拼接所有音频
        concatenated = np.concatenate(audio_data)

        # 保存拼接后的音频
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        sf.write(output_path, concatenated, self.sample_rate)

        final_duration = len(concatenated) / self.sample_rate
        print(f"  已保存拼接音频: {output_path}")
        print(f"  最终时长: {final_duration:.2f}秒 (包含 {len(segments)} 个片段)")

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
