"""
说话人聚类器 - 对提取的嵌入向量进行聚类以识别不同说话人
"""
import sys
import os
import numpy as np
from typing import List

# 添加speaker_diarization目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'speaker_diarization'))

try:
    from speaker_clustering import initialize_clustering as original_initialize_clustering
except ImportError as e:
    print(f"无法导入speaker_clustering: {e}")
    print("请确保speaker_diarization目录中的文件存在")
    raise


class SpeakerClusterer:
    def __init__(self, n_clusters=None, metric='cosine', linkage='average', distance_threshold=0.9):
        """
        初始化说话人聚类器
        
        Args:
            n_clusters (int, optional): 聚类数量，如果为None则使用distance_threshold
            metric (str): 距离度量方法
            linkage (str): 链接准则
            distance_threshold (float): 距离阈值，用于确定聚类数量
        """
        self.clusterer = original_initialize_clustering(
            n_clusters=n_clusters,
            metric=metric,
            linkage=linkage,
            distance_threshold=distance_threshold
        )

    def cluster_embeddings(self, embeddings: List[np.ndarray]) -> List[int]:
        """
        对嵌入向量进行聚类
        
        Args:
            embeddings (List[np.ndarray]): 嵌入向量列表
            
        Returns:
            List[int]: 聚类标签列表，每个数字代表一个说话人
        """
        # 过滤掉None值并保留原始索引映射
        valid_embeddings = []
        valid_indices = []
        
        for i, emb in enumerate(embeddings):
            if emb is not None:
                valid_embeddings.append(emb)
                valid_indices.append(i)
        
        if len(valid_embeddings) == 0:
            return [None] * len(embeddings)
        
        # 执行聚类
        cluster_labels = self.clusterer.cluster_embeddings(valid_embeddings)
        
        # 将聚类结果映射回原始索引
        result = [None] * len(embeddings)
        for i, label in enumerate(cluster_labels):
            original_idx = valid_indices[i]
            result[original_idx] = int(label)
        
        return result

    def get_unique_speakers_count(self, cluster_labels: List[int]) -> int:
        """
        获取唯一说话人数量
        
        Args:
            cluster_labels (List[int]): 聚类标签列表
            
        Returns:
            int: 唯一说话人数量
        """
        valid_labels = [label for label in cluster_labels if label is not None]
        if not valid_labels:
            return 0
        return len(set(valid_labels))


if __name__ == "__main__":
    # 示例用法
    # clusterer = SpeakerClusterer()
    # embeddings = [np.random.rand(256), np.random.rand(256)]  # 示例嵌入向量
    # labels = clusterer.cluster_embeddings(embeddings)
    # print(f"聚类标签: {labels}")
    # print(f"说话人数量: {clusterer.get_unique_speakers_count(labels)}")
    pass