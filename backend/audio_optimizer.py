# -*- coding: utf-8 -*-
"""
音频优化模块
用于优化克隆音频的长度，使其更接近原音频片段的长度
"""

import soundfile as sf
import numpy as np
import torch
import librosa
import os
from typing import List, Dict, Tuple, Optional

# 配置 rubberband 路径（Windows）
RUBBERBAND_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..",
    "tools", "rubberband", "rubberband-4.0.0-gpl-executable-windows"
)
RUBBERBAND_PATH = os.path.abspath(RUBBERBAND_PATH)

# 将 rubberband 添加到 PATH（如果存在）
if os.path.exists(RUBBERBAND_PATH):
    current_path = os.environ.get("PATH", "")
    if RUBBERBAND_PATH not in current_path:
        os.environ["PATH"] = RUBBERBAND_PATH + os.pathsep + current_path
        print(f"[音频优化] 添加 rubberband 到 PATH: {RUBBERBAND_PATH}")


class AudioOptimizer:
    """音频优化器，用于缩短过长的克隆音频"""

    # 加速比例上限
    MAX_SPEED_RATIO = 1.8

    # 变速时的目标时长缓冲（秒），使变速后的音频略短于目标时长，避免拼接时跳跃
    SPEED_TARGET_BUFFER = 0.1

    def __init__(self, use_vad: bool = True):
        """
        初始化音频优化器

        Args:
            use_vad: 是否使用 VAD 模型，False 则使用基于音量的静音检测
        """
        self.vad_model = None
        self.use_vad = use_vad
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

    def speed_up_audio(
        self,
        audio_data: np.ndarray,
        sampling_rate: int,
        speed_ratio: float
    ) -> np.ndarray:
        """
        对音频进行变速不变调处理（使用 pyrubberband）

        Args:
            audio_data: 音频数据
            sampling_rate: 采样率
            speed_ratio: 加速比例（>1 表示加速，如 1.2 表示加速 20%）

        Returns:
            加速后的音频数据
        """
        # 限制加速比例上限
        speed_ratio = min(speed_ratio, self.MAX_SPEED_RATIO)

        # 使用 pyrubberband 进行变速不变调（音质最好）
        try:
            import pyrubberband as pyrb

            # pyrubberband 的 time_stretch 参数 rate 是播放速率
            # rate > 1 表示加速播放（音频变短）
            # speed_ratio = 1.2 表示加速 20%，直接传入 1.2

            # 执行变速不变调
            stretched_audio = pyrb.time_stretch(audio_data, sampling_rate, speed_ratio)
            print(f"[音频优化] pyrubberband 变速成功: {speed_ratio:.2f}x")
            return stretched_audio

        except Exception as e:
            print(f"[音频优化] pyrubberband 变速失败: {e}")
            print(f"[音频优化] 请确保 rubberband-cli 已安装并在 PATH 中")
            return audio_data

    def _load_vad_model(self):
        """加载 Silero VAD 模型（只加载一次）"""
        if self.vad_model is None:
            print("[音频优化] 加载 Silero VAD 模型...")
            try:
                import sys

                # 尝试多个可能的路径
                possible_paths = [
                    # 方法1: 尝试直接导入（如果已安装在当前环境）
                    None,
                    # 方法2: ../../../silero-vad/src (从 LocalClip-Editor/backend)
                    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'silero-vad', 'src')),
                    # 方法3: ../../silero-vad/src (从 workspace/LocalClip-Editor/backend)
                    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'silero-vad', 'src')),
                ]

                imported = False
                for path in possible_paths:
                    try:
                        if path is None:
                            # 直接导入
                            from silero_vad import load_silero_vad, get_speech_timestamps
                            print("[音频优化] 从已安装的包中导入 silero_vad")
                            imported = True
                            break
                        elif os.path.exists(path):
                            if path not in sys.path:
                                sys.path.insert(0, path)
                                print(f"[音频优化] 添加 silero-vad/src 路径: {path}")
                            from silero_vad import load_silero_vad, get_speech_timestamps
                            imported = True
                            break
                    except ImportError:
                        continue

                if not imported:
                    raise ImportError("无法导入 silero_vad，请确保已安装或本地路径存在")

                self.vad_model = load_silero_vad()
                self.get_speech_timestamps = get_speech_timestamps
                print("[音频优化] VAD 模型加载成功")
            except Exception as e:
                print(f"[音频优化] 警告: 无法加载 Silero VAD 模型: {e}")
                print("[音频优化] 将使用基于音量的静音检测")
                self.use_vad = False
                return False
        return True

    def detect_speech_by_volume(
        self,
        audio_data: np.ndarray,
        sampling_rate: int,
        threshold_db: float = -40.0,
        min_silence_duration: float = 0.1,
        min_speech_duration: float = 0.05
    ) -> List[Dict]:
        """
        基于音量的语音检测（VAD 的替代方案）

        Args:
            audio_data: 音频数据
            sampling_rate: 采样率
            threshold_db: 静音阈值（dB），低于此值视为静音
            min_silence_duration: 最小静音时长（秒）
            min_speech_duration: 最小语音时长（秒）

        Returns:
            语音时间戳列表 [{'start': float, 'end': float}, ...]
        """
        # 计算帧级别的 RMS 能量
        frame_length = int(0.025 * sampling_rate)  # 25ms 帧
        hop_length = int(0.010 * sampling_rate)    # 10ms 步长

        # 确保音频是一维的
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)

        # 计算 RMS 能量
        rms = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]

        # 转换为 dB
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)

        # 检测语音帧（高于阈值）
        is_speech = rms_db > threshold_db

        # 转换为时间戳
        frame_times = librosa.frames_to_time(np.arange(len(is_speech)), sr=sampling_rate, hop_length=hop_length)

        # 合并连续的语音帧
        speech_timestamps = []
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

                if silence_duration >= min_silence_duration:
                    # 静音足够长，结束当前语音段
                    speech_end = t
                    if speech_end - speech_start >= min_speech_duration:
                        speech_timestamps.append({
                            'start': speech_start,
                            'end': speech_end
                        })
                    in_speech = False

        # 处理最后一个语音段
        if in_speech:
            speech_end = frame_times[-1] if len(frame_times) > 0 else len(audio_data) / sampling_rate
            if speech_end - speech_start >= min_speech_duration:
                speech_timestamps.append({
                    'start': speech_start,
                    'end': speech_end
                })

        return speech_timestamps

    def concatenate_speech_by_volume(
        self,
        audio_data: np.ndarray,
        sampling_rate: int
    ) -> Optional[np.ndarray]:
        """
        使用基于音量的检测提取语音段并拼接

        Args:
            audio_data: 音频数据
            sampling_rate: 采样率

        Returns:
            拼接后的语音段，如果没有检测到语音则返回 None
        """
        try:
            speech_timestamps = self.detect_speech_by_volume(audio_data, sampling_rate)

            if not speech_timestamps:
                return None

            # 拼接语音段
            speech_segments = []
            for i, segment in enumerate(speech_timestamps):
                start_sample = int(segment['start'] * sampling_rate)
                end_sample = int(segment['end'] * sampling_rate)
                start_sample = min(start_sample, len(audio_data))
                end_sample = min(end_sample, len(audio_data))

                if start_sample < end_sample:
                    # 计算当前语音段的5%时长
                    segment_duration_samples = end_sample - start_sample
                    five_percent_samples = int(segment_duration_samples * 0.05)

                    # 语音段前扩展5%（但不超过音频开头）
                    extended_start = max(0, start_sample - five_percent_samples)
                    # 语音段后扩展5%（但不超过音频结尾）
                    extended_end = min(len(audio_data), end_sample + five_percent_samples)

                    # 如果是第一段，不向前扩展
                    if i == 0:
                        extended_start = start_sample
                    # 如果是最后一段，不向后扩展
                    if i == len(speech_timestamps) - 1:
                        extended_end = end_sample

                    speech_segment = audio_data[extended_start:extended_end]
                    speech_segments.append(speech_segment)

            if speech_segments:
                concatenated = np.concatenate(speech_segments)
                print(f"  [Volume] 拼接 {len(speech_timestamps)} 个语音段，每段前后保留5%，中间去除静音")
                return concatenated
            return None

        except Exception as e:
            print(f"[音频优化] 音量检测处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def concatenate_speech_segments(
        self,
        audio_data: np.ndarray,
        sampling_rate: int
    ) -> Optional[np.ndarray]:
        """
        使用 VAD 提取语音段并拼接

        Args:
            audio_data: 音频数据
            sampling_rate: 采样率

        Returns:
            拼接后的语音段，如果没有检测到语音则返回 None
        """
        if not self._load_vad_model():
            return None

        try:
            # Silero VAD 要求音频采样率为 16000 Hz
            original_sr = sampling_rate
            target_sr = 16000

            # 如果采样率不是 16000，需要重采样
            if original_sr != target_sr:
                audio_data_resampled = librosa.resample(audio_data, orig_sr=original_sr, target_sr=target_sr)
                vad_audio = audio_data_resampled
                vad_sr = target_sr
            else:
                vad_audio = audio_data
                vad_sr = original_sr

            # 转换为 tensor
            audio_tensor = torch.from_numpy(vad_audio).float()

            # 处理音频维度
            if audio_tensor.ndim == 1:
                pass
            elif audio_tensor.ndim > 1:
                audio_tensor = audio_tensor[:, 0] if audio_tensor.shape[1] < audio_tensor.shape[0] else audio_tensor[0, :]

            # 获取语音时间戳
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.vad_model,
                return_seconds=True
            )

            if not speech_timestamps:
                return None

            # 拼接语音段（在语音段前后各保留5%的间隙，中间非语音段去掉90%）
            speech_segments = []

            for i, segment in enumerate(speech_timestamps):
                start_sample = int(segment['start'] * original_sr)
                end_sample = int(segment['end'] * original_sr)
                start_sample = min(start_sample, len(audio_data))
                end_sample = min(end_sample, len(audio_data))

                if start_sample < end_sample:
                    # 计算当前语音段的5%时长
                    segment_duration_samples = end_sample - start_sample
                    five_percent_samples = int(segment_duration_samples * 0.05)

                    # 语音段前扩展5%（但不超过音频开头）
                    extended_start = max(0, start_sample - five_percent_samples)
                    # 语音段后扩展5%（但不超过音频结尾）
                    extended_end = min(len(audio_data), end_sample + five_percent_samples)

                    # 如果是第一段，不向前扩展（从语音开始处开始）
                    if i == 0:
                        extended_start = start_sample

                    # 如果是最后一段，不向后扩展（到语音结束处结束）
                    if i == len(speech_timestamps) - 1:
                        extended_end = end_sample

                    speech_segment = audio_data[extended_start:extended_end]
                    speech_segments.append(speech_segment)

            if speech_segments:
                concatenated = np.concatenate(speech_segments)
                print(f"  [VAD] 拼接 {len(speech_timestamps)} 个语音段，每段前后保留5%，中间去除90%非语音")
                return concatenated
            return None

        except Exception as e:
            print(f"[音频优化] VAD 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None


    def optimize_audio_segments(
        self,
        segments_info: List[Dict],
        cloned_audio_dir: str
    ) -> Dict[int, str]:
        """
        批量优化过长的克隆音频片段

        Args:
            segments_info: 片段信息列表，每个元素包含:
                - index: 片段索引
                - audio_file_path: 音频文件路径
                - target_duration: 目标时长（原音频片段的时长）
                - actual_duration: 实际时长
            cloned_audio_dir: 克隆音频目录

        Returns:
            {segment_index: new_file_path} 字典，包含被优化的片段
        """
        print(f"[音频优化] 开始优化 {len(segments_info)} 个音频片段...")

        # 尝试加载 VAD 模型（如果 use_vad=True）
        vad_available = False
        if self.use_vad:
            vad_available = self._load_vad_model()

        if vad_available:
            print("[音频优化] 使用 Silero VAD 进行语音检测")
        else:
            print("[音频优化] 使用基于音量的静音检测")

        optimized_segments = {}

        for seg_info in segments_info:
            index = seg_info['index']
            audio_file_path = seg_info['audio_file_path']
            target_duration = seg_info['target_duration']
            actual_duration = seg_info['actual_duration']

            try:
                # 读取音频
                audio_data, sr = sf.read(audio_file_path)

                # 步骤1: 去除静音
                if vad_available:
                    # 使用 VAD 去除静音
                    processed_audio = self.concatenate_speech_segments(audio_data, sr)
                    method_name = "VAD"
                else:
                    # 使用基于音量的检测
                    processed_audio = self.concatenate_speech_by_volume(audio_data, sr)
                    method_name = "Volume"

                # 如果去静音失败，使用原始音频
                if processed_audio is None:
                    processed_audio = audio_data

                processed_duration = len(processed_audio) / sr

                # 步骤2: 如果去静音后仍超过目标时长，使用变速加速
                speed_applied = False
                if processed_duration > target_duration:
                    # 计算调整后的目标时长（略小于原目标时长，留出0.1秒缓冲）
                    adjusted_target_duration = max(target_duration - self.SPEED_TARGET_BUFFER, target_duration * 0.9)

                    # 计算需要的加速比例（基于调整后的目标时长）
                    required_speed_ratio = processed_duration / adjusted_target_duration

                    # 只有在加速比例不超过上限时才进行变速
                    if required_speed_ratio <= self.MAX_SPEED_RATIO:
                        print(f"[音频优化] 片段 {index}: 去静音后 {processed_duration:.3f}s 仍超过目标 {target_duration:.3f}s，应用 {required_speed_ratio:.2f}x 加速（目标: {adjusted_target_duration:.3f}s）")
                        processed_audio = self.speed_up_audio(processed_audio, sr, required_speed_ratio)
                        speed_applied = True
                        final_duration = len(processed_audio) / sr
                    else:
                        # 加速比例超过上限，使用最大加速比例
                        print(f"[音频优化] 片段 {index}: 需要 {required_speed_ratio:.2f}x 加速超过上限 {self.MAX_SPEED_RATIO}x，使用最大加速")
                        processed_audio = self.speed_up_audio(processed_audio, sr, self.MAX_SPEED_RATIO)
                        speed_applied = True
                        final_duration = len(processed_audio) / sr
                else:
                    final_duration = processed_duration

                # 保存优化后的音频
                output_path = os.path.join(
                    cloned_audio_dir,
                    f"segment_{index}_optimized.wav"
                )
                sf.write(output_path, processed_audio, sr)
                optimized_segments[index] = output_path

                # 打印优化结果
                if final_duration <= target_duration:
                    if speed_applied:
                        print(f"[音频优化] 片段 {index}: {method_name}+变速 优化成功，{actual_duration:.3f}s → {final_duration:.3f}s (目标 {target_duration:.3f}s)")
                    else:
                        print(f"[音频优化] 片段 {index}: {method_name} 优化成功，{actual_duration:.3f}s → {final_duration:.3f}s")
                else:
                    print(f"[音频优化] 片段 {index}: {method_name}+变速 部分成功，{actual_duration:.3f}s → {final_duration:.3f}s (仍超过目标 {target_duration:.3f}s)")

            except Exception as e:
                print(f"[音频优化] 片段 {index} 优化失败: {e}")
                import traceback
                traceback.print_exc()
                continue

        if optimized_segments:
            print(f"[音频优化] 优化完成，共优化 {len(optimized_segments)} 个片段")
        return optimized_segments

    def optimize_segments_for_stitching(
        self,
        cloned_results: List[Dict],
        cloned_audio_dir: str,
        threshold_ratio: float = 1.1
    ) -> Dict[int, str]:
        """
        为拼接准备优化音频片段

        Args:
            cloned_results: 克隆结果列表
            cloned_audio_dir: 克隆音频目录
            threshold_ratio: 触发优化的长度比例阈值（实际/目标）

        Returns:
            {segment_index: new_file_path} 字典
        """
        segments_to_optimize = []

        # 遍历所有片段，找出过长的
        for idx, result in enumerate(cloned_results):
            cloned_audio_path = result.get("cloned_audio_path")
            if not cloned_audio_path:
                continue

            # 构建文件路径
            audio_filename = f"segment_{idx}.wav"
            audio_file_path = os.path.join(cloned_audio_dir, audio_filename)

            if not os.path.exists(audio_file_path):
                continue

            # 获取时间戳信息
            start_time = result.get("start_time", 0)
            end_time = result.get("end_time", 0)
            target_duration = end_time - start_time

            if target_duration <= 0:
                continue

            # 读取实际音频长度
            try:
                audio_data, sr = sf.read(audio_file_path)
                actual_duration = len(audio_data) / sr

                # 如果超过阈值，加入优化列表
                if actual_duration / target_duration > threshold_ratio:
                    segments_to_optimize.append({
                        'index': idx,
                        'audio_file_path': audio_file_path,
                        'target_duration': target_duration,
                        'actual_duration': actual_duration,
                        'target_text': result.get('target_text', ''),  # 添加目标文字
                        'text': result.get('text', '')  # 添加原文字
                    })

            except Exception as e:
                print(f"[音频优化] 读取片段 {idx} 失败: {e}")
                continue

        if not segments_to_optimize:
            print("[音频优化] 没有需要优化的片段")
            return {}

        print(f"[音频优化] 发现 {len(segments_to_optimize)} 个过长的片段需要优化")

        # 批量优化
        return self.optimize_audio_segments(segments_to_optimize, cloned_audio_dir)
