"""
性别识别模块
使用Wav2Vec2模型对音频进行男女声识别
"""
import os
import torch
import librosa
from typing import Dict, List, Tuple, Optional
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
from audio_silence_trimmer import AudioSilenceTrimmer


class GenderClassifier:
    """音频性别分类器"""

    def __init__(self, model_path=None):
        """初始化性别分类器

        Args:
            model_path: 本地模型路径，如果为 None 则尝试自动检测
        """
        # 自动检测本地模型路径
        if model_path is None:
            model_path = self._get_local_model_path()

        self.model_name = model_path
        self.model = None
        self.processor = None
        self.id2label = {
            "0": "female",
            "1": "male"
        }

    def _get_local_model_path(self):
        """获取本地模型路径"""
        # 尝试几个可能的路径
        possible_paths = [
            # Windows: 相对于 backend 目录的路径
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "models", "models--prithivMLmods--Common-Voice-Geneder-Detection")),
            # HuggingFace 缓存路径
            os.path.expanduser("~/.cache/huggingface/hub/models--prithivMLmods--Common-Voice-Geneder-Detection"),
            # Fallback: 使用 HuggingFace hub 名称
            "prithivMLmods/Common-Voice-Geneder-Detection"
        ]

        for path in possible_paths:
            if os.path.exists(path):
                # 检查是否是 HuggingFace 格式的目录
                snapshots_dir = os.path.join(path, "snapshots")
                if os.path.exists(snapshots_dir):
                    # 使用最新的 snapshot
                    snapshot_dirs = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
                    if snapshot_dirs:
                        latest = sorted(snapshot_dirs, key=lambda x: os.path.getmtime(os.path.join(snapshots_dir, x)), reverse=True)[0]
                        return os.path.join(snapshots_dir, latest)
                # 直接使用这个路径
                return path

        # 如果都找不到，返回 HuggingFace hub 名称（会自动下载）
        return "prithivMLmods/Common-Voice-Geneder-Detection"

    def load_model(self):
        """懒加载模型"""
        if self.model is None:
            print(f"加载性别识别模型: {self.model_name}")
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(
                self.model_name,
                local_files_only=os.path.exists(self.model_name) and os.path.isdir(self.model_name)
            )
            self.processor = Wav2Vec2FeatureExtractor.from_pretrained(
                self.model_name,
                local_files_only=os.path.exists(self.model_name) and os.path.isdir(self.model_name)
            )
            print("性别识别模型加载完成")

    def classify_audio(self, audio_path: str) -> Dict[str, float]:
        """
        对音频文件进行性别分类

        Args:
            audio_path: 音频文件路径

        Returns:
            Dict[str, float]: 性别预测结果，格式: {"female": 0.123, "male": 0.877}
        """
        self.load_model()

        # 加载并重采样音频到16kHz
        speech, sample_rate = librosa.load(audio_path, sr=16000)

        # 处理音频
        inputs = self.processor(
            speech,
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=1).squeeze().tolist()

        prediction = {
            self.id2label[str(i)]: round(probs[i], 3) for i in range(len(probs))
        }

        return prediction

    def get_gender(self, audio_path: str) -> str:
        """
        获取音频的性别标签（male或female）

        Args:
            audio_path: 音频文件路径

        Returns:
            str: "male" 或 "female"
        """
        prediction = self.classify_audio(audio_path)
        # 返回概率更高的性别
        return "male" if prediction["male"] > prediction["female"] else "female"

    def select_best_audio_for_gender_classification(
        self,
        scored_segments: List[Tuple[str, float]],
        min_duration: float = 2.0
    ) -> str:
        """
        为性别识别选择最佳音频片段（原始版本，无静音切割）
        优先选择MOS分最高且时长>min_duration的音频，否则选择MOS分最高的

        Args:
            scored_segments: MOS评分后的片段列表，每个元素为(音频路径, MOS分数)
            min_duration: 最小时长阈值（秒）

        Returns:
            str: 选中的音频路径
        """
        if not scored_segments:
            raise ValueError("没有可用的音频片段")

        # 按MOS分数从高到低排序
        sorted_segments = sorted(scored_segments, key=lambda x: x[1], reverse=True)

        # 优先查找时长>min_duration且MOS最高的
        for audio_path, mos_score in sorted_segments:
            try:
                duration = librosa.get_duration(path=audio_path)
                if duration >= min_duration:
                    print(f"  选择音频: {audio_path} (时长: {duration:.2f}s, MOS: {mos_score:.3f})")
                    return audio_path
            except Exception as e:
                print(f"  获取音频时长失败 {audio_path}: {e}")
                continue

        # 如果没有满足时长要求的，选择MOS最高的
        best_audio, best_mos = sorted_segments[0]
        try:
            duration = librosa.get_duration(path=best_audio)
            print(f"  选择音频: {best_audio} (时长: {duration:.2f}s < {min_duration}s, MOS: {best_mos:.3f})")
        except:
            print(f"  选择音频: {best_audio} (MOS: {best_mos:.3f})")
        return best_audio

    def select_best_audio_with_silence_trimming(
        self,
        scored_segments: List[Tuple[str, float]],
        min_duration: float = 2.0,
        min_final_duration: float = 1.5,
        temp_dir: Optional[str] = None
    ) -> str:
        """
        为性别识别选择最佳音频片段，并进行静音切割预处理

        优化后的流程：
        1. 按MOS分数从高到低排序
        2. 循环处理每个片段：
           a. 对音频进行静音切割
           b. 如果切割后时长>0，保存到累积列表
           c. 计算累计时长
           d. 如果累计时长≥min_final_duration，停止，拼接所有片段并返回
           e. 否则继续下一个片段
        3. 如果遍历完所有片段仍不足，拼接所有已有片段（作为fallback）

        Args:
            scored_segments: MOS评分后的片段列表，每个元素为(音频路径, MOS分数)
            min_duration: 原始音频的最小时长阈值（秒）
            min_final_duration: 切割后音频的最小可接受时长（秒）
            temp_dir: 临时文件目录

        Returns:
            str: 选中并处理后的音频路径
        """
        if not scored_segments:
            raise ValueError("没有可用的音频片段")

        print(f"\n[音频选择] 开始累积式选择并预处理音频，共 {len(scored_segments)} 个候选片段")
        print(f"[音频选择] 目标累计时长: ≥{min_final_duration}s")

        # 按MOS分数从高到低排序
        sorted_segments = sorted(scored_segments, key=lambda x: x[1], reverse=True)

        # 初始化静音切割器
        trimmer = AudioSilenceTrimmer(
            threshold_db=-40.0,
            frame_length_ms=25.0,
            hop_length_ms=10.0
        )

        # 累积的音频片段列表
        accumulated_audios = []
        accumulated_duration = 0.0

        # 优先处理时长≥min_duration的片段
        print(f"\n[音频选择] 阶段1: 处理时长≥{min_duration}s的高质量片段")
        for audio_path, mos_score in sorted_segments:
            try:
                duration = librosa.get_duration(path=audio_path)

                if duration >= min_duration:
                    print(f"\n[音频选择] 尝试片段 {len(accumulated_audios)+1}: {os.path.basename(audio_path)} (时长: {duration:.2f}s, MOS: {mos_score:.3f})")

                    # 尝试静音切割（不验证最小时长，因为我们会累积）
                    result = trimmer.process_audio_for_gender_classification(
                        audio_path,
                        min_final_duration=0.0,  # 设置为0，允许任何长度
                        temp_dir=temp_dir
                    )

                    if result is not None:
                        trimmed_path, trimmed_duration = result

                        if trimmed_duration > 0:
                            accumulated_audios.append(trimmed_path)
                            accumulated_duration += trimmed_duration
                            print(f"[音频选择] ✓ 已累积: {trimmed_duration:.2f}s，总计: {accumulated_duration:.2f}s")

                            # 检查是否达到目标时长
                            if accumulated_duration >= min_final_duration:
                                print(f"\n[音频选择] ✓ 达到目标时长 {accumulated_duration:.2f}s ≥ {min_final_duration}s")

                                # 如果只有一个片段，直接返回
                                if len(accumulated_audios) == 1:
                                    return accumulated_audios[0]

                                # 多个片段，需要拼接
                                if temp_dir is None:
                                    import tempfile
                                    temp_dir = tempfile.gettempdir()

                                final_path = os.path.join(temp_dir, f"gender_classification_concatenated.wav")
                                final_path, final_duration = trimmer.concatenate_multiple_audios(
                                    accumulated_audios,
                                    final_path,
                                    silence_duration=0.2
                                )
                                print(f"[音频选择] 已拼接 {len(accumulated_audios)} 个片段，最终时长: {final_duration:.2f}s")
                                return final_path
                        else:
                            print(f"[音频选择] ✗ 切割后时长为0，跳过")
                    else:
                        print(f"[音频选择] ✗ 处理失败，跳过")

            except Exception as e:
                print(f"[音频选择] ✗ 处理失败 {audio_path}: {e}")
                continue

        # 如果时长≥min_duration的还不够，继续处理其他片段
        if accumulated_duration < min_final_duration:
            print(f"\n[音频选择] 阶段2: 处理时长<{min_duration}s的片段（当前累计: {accumulated_duration:.2f}s）")

            for audio_path, mos_score in sorted_segments:
                try:
                    duration = librosa.get_duration(path=audio_path)

                    # 跳过已处理过的长片段
                    if duration >= min_duration:
                        continue

                    print(f"\n[音频选择] 尝试片段 {len(accumulated_audios)+1}: {os.path.basename(audio_path)} (时长: {duration:.2f}s, MOS: {mos_score:.3f})")

                    # 尝试静音切割
                    result = trimmer.process_audio_for_gender_classification(
                        audio_path,
                        min_final_duration=0.0,  # 设置为0，允许任何长度
                        temp_dir=temp_dir
                    )

                    if result is not None:
                        trimmed_path, trimmed_duration = result

                        if trimmed_duration > 0:
                            accumulated_audios.append(trimmed_path)
                            accumulated_duration += trimmed_duration
                            print(f"[音频选择] ✓ 已累积: {trimmed_duration:.2f}s，总计: {accumulated_duration:.2f}s")

                            # 检查是否达到目标时长
                            if accumulated_duration >= min_final_duration:
                                print(f"\n[音频选择] ✓ 达到目标时长 {accumulated_duration:.2f}s ≥ {min_final_duration}s")

                                # 如果只有一个片段，直接返回
                                if len(accumulated_audios) == 1:
                                    return accumulated_audios[0]

                                # 多个片段，需要拼接
                                if temp_dir is None:
                                    import tempfile
                                    temp_dir = tempfile.gettempdir()

                                final_path = os.path.join(temp_dir, f"gender_classification_concatenated.wav")
                                final_path, final_duration = trimmer.concatenate_multiple_audios(
                                    accumulated_audios,
                                    final_path,
                                    silence_duration=0.2
                                )
                                print(f"[音频选择] 已拼接 {len(accumulated_audios)} 个片段，最终时长: {final_duration:.2f}s")
                                return final_path
                        else:
                            print(f"[音频选择] ✗ 切割后时长为0，跳过")
                    else:
                        print(f"[音频选择] ✗ 处理失败，跳过")

                except Exception as e:
                    print(f"[音频选择] ✗ 处理失败 {audio_path}: {e}")
                    continue

        # 如果遍历完所有片段仍不足min_final_duration
        if accumulated_audios:
            print(f"\n[音频选择] 警告: 所有片段累计时长 {accumulated_duration:.2f}s < {min_final_duration}s")
            print(f"[音频选择] 使用已累积的 {len(accumulated_audios)} 个片段")

            # 如果只有一个片段，直接返回
            if len(accumulated_audios) == 1:
                return accumulated_audios[0]

            # 多个片段，拼接
            if temp_dir is None:
                import tempfile
                temp_dir = tempfile.gettempdir()

            final_path = os.path.join(temp_dir, f"gender_classification_concatenated.wav")
            final_path, final_duration = trimmer.concatenate_multiple_audios(
                accumulated_audios,
                final_path,
                silence_duration=0.2
            )
            print(f"[音频选择] 已拼接 {len(accumulated_audios)} 个片段，最终时长: {final_duration:.2f}s")
            return final_path
        else:
            # 完全没有可用的片段，使用原始方法作为fallback
            print(f"\n[音频选择] 警告: 没有任何可用的切割后片段，使用原始方法fallback")
            return self.select_best_audio_for_gender_classification(
                scored_segments,
                min_duration=min_duration
            )

    def classify_speakers(
        self,
        scored_segments_dict: Dict[int, List[Tuple[str, float]]],
        min_duration: float = 2.0,
        use_silence_trimming: bool = True,
        min_final_duration: float = 1.5,
        temp_dir: Optional[str] = None
    ) -> Dict[int, str]:
        """
        对所有说话人进行性别分类

        Args:
            scored_segments_dict: 字典，key为说话人ID，value为MOS评分后的片段列表
            min_duration: 最小时长阈值
            use_silence_trimming: 是否使用静音切割预处理
            min_final_duration: 切割后的最小可接受时长
            temp_dir: 临时文件目录

        Returns:
            Dict[int, str]: 字典，key为说话人ID，value为性别（"male"或"female"）
        """
        results = {}

        for speaker_id, scored_segments in scored_segments_dict.items():
            print(f"\n对说话人 {speaker_id} 进行性别识别...")

            try:
                # 选择最佳音频
                if use_silence_trimming:
                    best_audio = self.select_best_audio_with_silence_trimming(
                        scored_segments,
                        min_duration=min_duration,
                        min_final_duration=min_final_duration,
                        temp_dir=temp_dir
                    )
                else:
                    best_audio = self.select_best_audio_for_gender_classification(
                        scored_segments,
                        min_duration=min_duration
                    )

                # 进行性别识别
                gender = self.get_gender(best_audio)
                prediction = self.classify_audio(best_audio)

                print(f"  识别结果: {gender} (male: {prediction['male']:.3f}, female: {prediction['female']:.3f})")
                results[speaker_id] = gender

            except Exception as e:
                print(f"  识别失败: {str(e)}")
                import traceback
                traceback.print_exc()
                # 默认为male
                results[speaker_id] = "male"

        return results


def rename_speakers_by_gender(
    speaker_labels: List[int],
    gender_dict: Dict[int, str]
) -> Tuple[Dict[int, str], Dict[str, int]]:
    """
    根据性别和出现次数重新命名说话人

    Args:
        speaker_labels: 说话人标签列表
        gender_dict: 说话人性别字典，key为原始speaker_id，value为性别

    Returns:
        Tuple[Dict[int, str], Dict[str, int]]:
            - 说话人新名称字典：{原始ID: "男1", "女1", ...}
            - 性别统计：{"male": count, "female": count}
    """
    # 统计每个说话人的出现次数
    speaker_counts = {}
    for speaker_id in speaker_labels:
        if speaker_id is not None:
            speaker_counts[speaker_id] = speaker_counts.get(speaker_id, 0) + 1

    # 按性别分组，并按出现次数排序
    male_speakers = []
    female_speakers = []

    for speaker_id, count in speaker_counts.items():
        gender = gender_dict.get(speaker_id, "male")
        if gender == "male":
            male_speakers.append((speaker_id, count))
        else:
            female_speakers.append((speaker_id, count))

    # 按出现次数降序排序
    male_speakers.sort(key=lambda x: x[1], reverse=True)
    female_speakers.sort(key=lambda x: x[1], reverse=True)

    # 生成新名称
    speaker_name_mapping = {}

    for idx, (speaker_id, count) in enumerate(male_speakers, 1):
        speaker_name_mapping[speaker_id] = f"男{idx}"
        print(f"说话人 {speaker_id} -> {speaker_name_mapping[speaker_id]} (出现 {count} 次)")

    for idx, (speaker_id, count) in enumerate(female_speakers, 1):
        speaker_name_mapping[speaker_id] = f"女{idx}"
        print(f"说话人 {speaker_id} -> {speaker_name_mapping[speaker_id]} (出现 {count} 次)")

    gender_stats = {
        "male": len(male_speakers),
        "female": len(female_speakers)
    }

    return speaker_name_mapping, gender_stats
