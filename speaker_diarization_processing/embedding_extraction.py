"""
说话人Embedding提取器 - 用于从音频片段中提取说话人嵌入向量
"""
import sys
import os
import numpy as np
from typing import List

# 添加SpeakerDiarization目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'SpeakerDiarization'))

try:
    from emb_extractor import initialize_extractor
except ImportError as e:
    print(f"无法导入emb_extractor: {e}")
    print("请确保speaker_diarization目录中的文件存在")
    raise


class SpeakerEmbeddingExtractor:
    def __init__(self, api_key=None, offline_mode=True):
        """
        初始化说话人嵌入提取器
        
        Args:
            api_key (str, optional): Hugging Face API密钥
            offline_mode (bool): 是否使用离线模式
        """
        try:
            self.extractor = initialize_extractor(api_key=api_key, offline_mode=offline_mode)
        except Exception as e:
            print(f"初始化嵌入提取器失败: {e}")
            raise

    def extract_embeddings(self, audio_paths: List[str]) -> List[np.ndarray]:
        """
        从多个音频文件路径提取嵌入向量
        
        Args:
            audio_paths (List[str]): 音频文件路径列表
            
        Returns:
            List[np.ndarray]: 嵌入向量列表
        """
        embeddings = []
        
        for audio_path in audio_paths:
            if not os.path.exists(audio_path):
                print(f"音频文件不存在: {audio_path}")
                embeddings.append(None)  # 对应位置添加None，保持索引一致性
                continue
            
            try:
                embedding = self.extractor.extract_embedding(audio_path)
                embeddings.append(embedding)
                print(f"成功提取音频嵌入: {os.path.basename(audio_path)}")
            except Exception as e:
                print(f"提取音频嵌入失败 {audio_path}: {e}")
                embeddings.append(None)
        
        return embeddings

    def extract_single_embedding(self, audio_path: str) -> np.ndarray:
        """
        从单个音频文件路径提取嵌入向量
        
        Args:
            audio_path (str): 音频文件路径
            
        Returns:
            np.ndarray: 嵌入向量
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        return self.extractor.extract_embedding(audio_path)


if __name__ == "__main__":
    # 示例用法
    # extractor = SpeakerEmbeddingExtractor(offline_mode=True)
    # audio_paths = ["audio1.wav", "audio2.wav"]
    # embeddings = extractor.extract_embeddings(audio_paths)
    # print(f"提取了 {len([e for e in embeddings if e is not None])} 个有效嵌入")
    pass