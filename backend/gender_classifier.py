"""
性别识别模块
使用Wav2Vec2模型对音频进行男女声识别
"""
import torch
import librosa
from typing import Dict, List, Tuple
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor


class GenderClassifier:
    """音频性别分类器"""

    def __init__(self):
        """初始化性别分类器"""
        self.model_name = "prithivMLmods/Common-Voice-Geneder-Detection"
        self.model = None
        self.processor = None
        self.id2label = {
            "0": "female",
            "1": "male"
        }

    def load_model(self):
        """懒加载模型"""
        if self.model is None:
            print("加载性别识别模型...")
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(self.model_name)
            self.processor = Wav2Vec2FeatureExtractor.from_pretrained(self.model_name)
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
        为性别识别选择最佳音频片段
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

    def classify_speakers(
        self,
        scored_segments_dict: Dict[int, List[Tuple[str, float]]],
        min_duration: float = 2.0
    ) -> Dict[int, str]:
        """
        对所有说话人进行性别分类

        Args:
            scored_segments_dict: 字典，key为说话人ID，value为MOS评分后的片段列表
            min_duration: 最小时长阈值

        Returns:
            Dict[int, str]: 字典，key为说话人ID，value为性别（"male"或"female"）
        """
        results = {}

        for speaker_id, scored_segments in scored_segments_dict.items():
            print(f"\n对说话人 {speaker_id} 进行性别识别...")

            try:
                # 选择最佳音频
                best_audio = self.select_best_audio_for_gender_classification(
                    scored_segments, min_duration
                )

                # 进行性别识别
                gender = self.get_gender(best_audio)
                prediction = self.classify_audio(best_audio)

                print(f"  识别结果: {gender} (male: {prediction['male']:.3f}, female: {prediction['female']:.3f})")
                results[speaker_id] = gender

            except Exception as e:
                print(f"  识别失败: {str(e)}")
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
