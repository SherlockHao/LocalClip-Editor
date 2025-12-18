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


class AudioOptimizer:
    """音频优化器，用于缩短过长的克隆音频"""

    def __init__(self):
        """初始化音频优化器"""
        self.vad_model = None
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

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
                print("[音频优化] 将跳过 VAD 优化步骤")
                import traceback
                traceback.print_exc()
                return False
        return True

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

            # 拼接语音段
            speech_segments = []
            for segment in speech_timestamps:
                start_sample = int(segment['start'] * original_sr)
                end_sample = int(segment['end'] * original_sr)
                start_sample = min(start_sample, len(audio_data))
                end_sample = min(end_sample, len(audio_data))

                if start_sample < end_sample:
                    speech_segment = audio_data[start_sample:end_sample]
                    speech_segments.append(speech_segment)

            if speech_segments:
                concatenated = np.concatenate(speech_segments)
                return concatenated
            return None

        except Exception as e:
            print(f"[音频优化] VAD 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def time_stretch_audio(
        self,
        audio_data: np.ndarray,
        rate: float = 1.05
    ) -> np.ndarray:
        """
        对音频进行变速不变调处理

        Args:
            audio_data: 音频数据
            rate: 变速倍率（>1 加速，<1 减速）

        Returns:
            变速后的音频数据
        """
        try:
            stretched_audio = librosa.effects.time_stretch(audio_data, rate=rate)
            return stretched_audio
        except Exception as e:
            print(f"[音频优化] 变速处理失败: {e}")
            return audio_data

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

        # 加载 VAD 模型（只加载一次）
        vad_available = self._load_vad_model()

        optimized_segments = {}

        for seg_info in segments_info:
            index = seg_info['index']
            audio_file_path = seg_info['audio_file_path']
            target_duration = seg_info['target_duration']
            actual_duration = seg_info['actual_duration']

            try:
                # 读取音频
                audio_data, sr = sf.read(audio_file_path)

                # 步骤1: 尝试使用 VAD 去除静音
                if vad_available:
                    vad_audio = self.concatenate_speech_segments(audio_data, sr)

                    if vad_audio is not None:
                        vad_duration = len(vad_audio) / sr

                        # 如果 VAD 后长度符合要求，保存并使用
                        if vad_duration <= target_duration:
                            output_path = os.path.join(
                                cloned_audio_dir,
                                f"segment_{index}_vad.wav"
                            )
                            sf.write(output_path, vad_audio, sr)
                            optimized_segments[index] = output_path
                            continue

                        # VAD 后仍然过长，使用 VAD 结果继续处理
                        audio_data = vad_audio
                        actual_duration = vad_duration

                # 步骤2: 如果 VAD 后仍然过长，使用变速
                if actual_duration > target_duration:
                    rate = actual_duration / target_duration
                    rate = min(max(rate, 1.0), 2.0)

                    stretched_audio = self.time_stretch_audio(audio_data, rate=rate)

                    output_path = os.path.join(
                        cloned_audio_dir,
                        f"segment_{index}_optimized.wav"
                    )
                    sf.write(output_path, stretched_audio, sr)
                    optimized_segments[index] = output_path

            except Exception as e:
                print(f"[音频优化] 片段 {index} 优化失败: {e}")
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
