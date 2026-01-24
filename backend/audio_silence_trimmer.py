"""
音频静音切割模块
用于性别识别前的音频预处理，去除过长的非语音段
"""
import numpy as np
import librosa
import soundfile as sf
from typing import List, Dict, Optional, Tuple
import os
import tempfile


class AudioSilenceTrimmer:
    """音频静音切割器，用于性别识别的音频预处理"""

    def __init__(
        self,
        threshold_db: float = -40.0,
        frame_length_ms: float = 25.0,
        hop_length_ms: float = 10.0,
        min_silence_duration: float = 0.1,
        min_speech_duration: float = 0.05
    ):
        """
        初始化音频静音切割器

        Args:
            threshold_db: 静音阈值（dB），低于此值视为静音
            frame_length_ms: 帧长度（毫秒）
            hop_length_ms: 步长（毫秒）
            min_silence_duration: 最小静音时长（秒）
            min_speech_duration: 最小语音时长（秒）
        """
        self.threshold_db = threshold_db
        self.frame_length_ms = frame_length_ms
        self.hop_length_ms = hop_length_ms
        self.min_silence_duration = min_silence_duration
        self.min_speech_duration = min_speech_duration

    def detect_speech_segments(
        self,
        audio_data: np.ndarray,
        sampling_rate: int
    ) -> List[Dict]:
        """
        使用RMS能量检测语音段

        Args:
            audio_data: 音频数据
            sampling_rate: 采样率

        Returns:
            语音段列表 [{'start': float, 'end': float}, ...]
        """
        # 计算帧长度和步长（样本数）
        frame_length = int(self.frame_length_ms / 1000 * sampling_rate)
        hop_length = int(self.hop_length_ms / 1000 * sampling_rate)

        # 确保音频是一维的
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        # 计算 RMS 能量
        rms = librosa.feature.rms(
            y=audio_data,
            frame_length=frame_length,
            hop_length=hop_length
        )[0]

        # 转换为 dB
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        # 检测语音帧（高于阈值）
        is_speech = rms_db > self.threshold_db

        # 转换为时间戳
        frame_times = librosa.frames_to_time(
            np.arange(len(is_speech)),
            sr=sampling_rate,
            hop_length=hop_length
        )

        # 合并连续的语音帧
        speech_segments = []
        in_speech = False
        speech_start = 0

        for i, (is_s, t) in enumerate(zip(is_speech, frame_times)):
            if is_s and not in_speech:
                # 语音开始
                in_speech = True
                speech_start = t
            elif not is_s and in_speech:
                # 检查静音是否足够长
                silence_start = t
                silence_end = t

                # 向前查找静音结束点
                for j in range(i, len(is_speech)):
                    if is_speech[j]:
                        break
                    silence_end = frame_times[j] if j < len(frame_times) else frame_times[-1]

                silence_duration = silence_end - silence_start

                if silence_duration >= self.min_silence_duration:
                    # 静音足够长，结束当前语音段
                    speech_end = t
                    if speech_end - speech_start >= self.min_speech_duration:
                        speech_segments.append({
                            'start': speech_start,
                            'end': speech_end
                        })
                    in_speech = False

        # 处理最后一个语音段
        if in_speech:
            speech_end = frame_times[-1] if len(frame_times) > 0 else len(audio_data) / sampling_rate
            if speech_end - speech_start >= self.min_speech_duration:
                speech_segments.append({
                    'start': speech_start,
                    'end': speech_end
                })

        return speech_segments

    def trim_silence(
        self,
        audio_data: np.ndarray,
        sampling_rate: int,
        speech_segments: List[Dict],
        leading_threshold: float = 1.5,
        trailing_threshold: float = 1.5,
        middle_threshold: float = 2.0,
        keep_duration: float = 0.5
    ) -> np.ndarray:
        """
        根据规则切割非语音段

        规则：
        1. 开头非语音段 >1.5秒 → 保留最后0.5秒
        2. 结尾非语音段 >1.5秒 → 保留最前0.5秒
        3. 中间非语音段 >2.0秒  → 保留前后各0.5秒

        Args:
            audio_data: 音频数据
            sampling_rate: 采样率
            speech_segments: 语音段列表
            leading_threshold: 开头非语音段阈值（秒）
            trailing_threshold: 结尾非语音段阈值（秒）
            middle_threshold: 中间非语音段阈值（秒）
            keep_duration: 保留的边界时长（秒）

        Returns:
            处理后的音频数据
        """
        if not speech_segments:
            # 没有检测到语音段，返回原音频
            return audio_data

        audio_duration = len(audio_data) / sampling_rate
        segments_to_keep = []

        # === 规则1: 处理开头非语音段 ===
        first_speech_start = speech_segments[0]['start']
        leading_silence = first_speech_start

        if leading_silence > leading_threshold:
            # 保留最后0.5秒
            trim_start = max(0, first_speech_start - keep_duration)
            print(f"  [Trim] 开头非语音段 {leading_silence:.2f}s > {leading_threshold}s，去掉前面部分，保留最后{keep_duration}s")
        else:
            # 全部保留
            trim_start = 0
            if leading_silence > 0:
                print(f"  [Trim] 开头非语音段 {leading_silence:.2f}s <= {leading_threshold}s，保留全部")

        # === 规则2: 处理结尾非语音段 ===
        last_speech_end = speech_segments[-1]['end']
        trailing_silence = audio_duration - last_speech_end

        if trailing_silence > trailing_threshold:
            # 保留最前0.5秒
            trim_end = min(audio_duration, last_speech_end + keep_duration)
            print(f"  [Trim] 结尾非语音段 {trailing_silence:.2f}s > {trailing_threshold}s，去掉后面部分，保留最前{keep_duration}s")
        else:
            # 全部保留
            trim_end = audio_duration
            if trailing_silence > 0:
                print(f"  [Trim] 结尾非语音段 {trailing_silence:.2f}s <= {trailing_threshold}s，保留全部")

        # === 规则3: 处理中间非语音段并构建要保留的片段 ===
        for i, seg in enumerate(speech_segments):
            # 第一个语音段：从trim_start开始
            if i == 0:
                segment_start = trim_start
            else:
                # 中间语音段：从上一个片段结束处开始
                segment_start = seg['start']

            # 最后一个语音段：到trim_end结束
            if i == len(speech_segments) - 1:
                segment_end = min(trim_end, audio_duration)
            else:
                # 非最后一个语音段：检查与下一个语音段的间隔
                next_seg = speech_segments[i + 1]
                current_end = seg['end']
                next_start = next_seg['start']
                silence_duration = next_start - current_end

                if silence_duration > middle_threshold:
                    # 中间静音段过长，切割
                    # 保留当前语音段结束后0.5秒
                    segment_end = min(current_end + keep_duration, audio_duration)

                    # 下一个片段将从下一个语音段开始前0.5秒开始
                    # 但这部分逻辑会在下一次循环中通过segment_start处理
                    print(f"  [Trim] 中间非语音段 {silence_duration:.2f}s > {middle_threshold}s，保留前后各{keep_duration}s")

                    # 添加当前片段
                    segments_to_keep.append({
                        'start': segment_start,
                        'end': segment_end
                    })

                    # 添加下一个语音段开始前的0.5秒片段
                    next_segment_start = max(0, next_start - keep_duration)
                    # 这个片段会在下一次循环开始时与下一个语音段合并
                    # 所以我们需要调整下一个循环的segment_start
                    # 但这需要修改循环逻辑，我们采用另一种方式

                    # 实际上我们需要重新构建逻辑
                    continue
                else:
                    # 中间静音段不长，保留全部
                    segment_end = next_start
                    if silence_duration > 0:
                        print(f"  [Trim] 中间非语音段 {silence_duration:.2f}s <= {middle_threshold}s，保留全部")

            # 添加片段
            if i < len(speech_segments) - 1:
                # 非最后一个片段，需要检查是否已经在上面处理过
                next_seg = speech_segments[i + 1]
                silence_duration = next_seg['start'] - seg['end']

                if silence_duration > middle_threshold:
                    # 已在上面处理，跳过segment_end的重新赋值
                    pass

            segments_to_keep.append({
                'start': segment_start,
                'end': segment_end
            })

        # === 重新构建逻辑，更清晰地处理中间段 ===
        # 重写segments_to_keep的构建
        segments_to_keep = []

        for i, seg in enumerate(speech_segments):
            # 确定当前语音段的实际起止时间
            if i == 0:
                # 第一个语音段：应用开头规则
                actual_start = trim_start
            else:
                # 中间语音段：检查与前一个的间隔
                prev_seg = speech_segments[i - 1]
                silence_duration = seg['start'] - prev_seg['end']

                if silence_duration > middle_threshold:
                    # 间隔过长，从当前语音段前0.5秒开始
                    actual_start = max(0, seg['start'] - keep_duration)
                else:
                    # 间隔正常，从前一个语音段结束处开始（已包含在前一个片段中）
                    actual_start = seg['start']

            # 确定当前语音段的结束时间
            if i == len(speech_segments) - 1:
                # 最后一个语音段：应用结尾规则
                actual_end = min(trim_end, audio_duration)
            else:
                # 中间语音段：检查与下一个的间隔
                next_seg = speech_segments[i + 1]
                silence_duration = next_seg['start'] - seg['end']

                if silence_duration > middle_threshold:
                    # 间隔过长，到当前语音段后0.5秒结束
                    actual_end = min(seg['end'] + keep_duration, audio_duration)
                else:
                    # 间隔正常，到下一个语音段开始处结束
                    actual_end = next_seg['start']

            segments_to_keep.append({
                'start': actual_start,
                'end': actual_end
            })

        # === 拼接音频片段 ===
        audio_segments = []
        for seg in segments_to_keep:
            start_sample = int(seg['start'] * sampling_rate)
            end_sample = int(seg['end'] * sampling_rate)
            start_sample = min(start_sample, len(audio_data))
            end_sample = min(end_sample, len(audio_data))

            if start_sample < end_sample:
                audio_segments.append(audio_data[start_sample:end_sample])

        if audio_segments:
            trimmed_audio = np.concatenate(audio_segments)
            return trimmed_audio
        else:
            # 没有可保留的片段，返回原音频
            return audio_data

    def process_audio_for_gender_classification(
        self,
        audio_path: str,
        min_final_duration: float = 1.5,
        temp_dir: Optional[str] = None
    ) -> Optional[Tuple[str, float]]:
        """
        完整的音频预处理流程：加载 → 检测 → 切割 → 验证时长 → 保存

        Args:
            audio_path: 原始音频路径
            min_final_duration: 最小可接受的最终时长（秒）
            temp_dir: 临时文件目录，None则使用系统临时目录

        Returns:
            (处理后的临时文件路径, 时长) 或 None（时长不足）
        """
        try:
            # 加载音频
            audio_data, sr = librosa.load(audio_path, sr=16000)
            original_duration = len(audio_data) / sr

            print(f"  [处理音频] {os.path.basename(audio_path)}, 原始时长: {original_duration:.2f}s")

            # 检测语音段
            speech_segments = self.detect_speech_segments(audio_data, sr)

            if not speech_segments:
                print(f"  [处理音频] 未检测到语音段，使用原音频")
                # 没有检测到语音，检查原音频时长
                if original_duration >= min_final_duration:
                    # 直接返回原音频路径
                    return audio_path, original_duration
                else:
                    return None

            print(f"  [处理音频] 检测到 {len(speech_segments)} 个语音段")

            # 切割非语音段
            trimmed_audio = self.trim_silence(audio_data, sr, speech_segments)
            trimmed_duration = len(trimmed_audio) / sr

            print(f"  [处理音频] 切割后时长: {trimmed_duration:.2f}s")

            # 验证时长
            if trimmed_duration < min_final_duration:
                print(f"  [处理音频] 时长不足 {min_final_duration}s，丢弃此片段")
                return None

            # 保存临时文件
            if temp_dir is None:
                temp_dir = tempfile.gettempdir()

            os.makedirs(temp_dir, exist_ok=True)

            # 生成临时文件名
            base_name = os.path.basename(audio_path)
            name_without_ext = os.path.splitext(base_name)[0]
            temp_path = os.path.join(temp_dir, f"{name_without_ext}_trimmed.wav")

            # 保存
            sf.write(temp_path, trimmed_audio, sr)
            print(f"  [处理音频] 已保存临时文件: {temp_path}")

            return temp_path, trimmed_duration

        except Exception as e:
            print(f"  [处理音频] 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def concatenate_multiple_audios(
        self,
        audio_paths: List[str],
        output_path: str,
        silence_duration: float = 0.2
    ) -> Tuple[str, float]:
        """
        拼接多个音频文件，中间插入短暂静音

        Args:
            audio_paths: 音频文件路径列表
            output_path: 输出文件路径
            silence_duration: 音频之间的静音时长（秒）

        Returns:
            (输出文件路径, 总时长)
        """
        if not audio_paths:
            raise ValueError("没有音频文件可拼接")

        sr = 16000
        audio_segments = []

        # 生成静音片段
        silence_samples = int(silence_duration * sr)
        silence = np.zeros(silence_samples, dtype=np.float32)

        # 加载所有音频
        for i, audio_path in enumerate(audio_paths):
            try:
                audio_data, _ = librosa.load(audio_path, sr=sr)
                audio_segments.append(audio_data)

                # 除了最后一个片段，都添加静音
                if i < len(audio_paths) - 1:
                    audio_segments.append(silence)

            except Exception as e:
                print(f"  [拼接] 加载音频失败 {audio_path}: {e}")
                continue

        if not audio_segments:
            raise ValueError("没有成功加载的音频片段")

        # 拼接所有音频
        concatenated = np.concatenate(audio_segments)
        total_duration = len(concatenated) / sr

        # 保存
        sf.write(output_path, concatenated, sr)
        print(f"  [拼接] 已拼接 {len(audio_paths)} 个片段，总时长: {total_duration:.2f}s")

        return output_path, total_duration
