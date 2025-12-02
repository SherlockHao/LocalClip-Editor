"""
说话人识别主处理脚本
整合音频提取、嵌入提取和聚类功能
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 添加必要的路径
sys.path.append(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'speaker_diarization'))

from audio_extraction import AudioExtractor
from embedding_extraction import SpeakerEmbeddingExtractor
from speaker_clustering import SpeakerClusterer


class SpeakerDiarizationProcessor:
    def __init__(self, audio_cache_dir: str = "audio_segments"):
        """
        初始化说话人识别处理器
        
        Args:
            audio_cache_dir (str): 音频缓存目录
        """
        self.audio_cache_dir = audio_cache_dir
        self.audio_extractor = AudioExtractor(cache_dir=audio_cache_dir)
        self.embedding_extractor = SpeakerEmbeddingExtractor(offline_mode=True)
        self.clusterer = SpeakerClusterer()
    
    def process_video_speaker_diarization(self, video_path: str, srt_path: str) -> Dict:
        """
        执行完整的说话人识别流程
        
        Args:
            video_path (str): 视频文件路径
            srt_path (str): SRT字幕文件路径
            
        Returns:
            Dict: 包含处理结果的字典
        """
        try:
            # 1. 提取音频片段
            print("步骤1: 正在提取音频片段...")
            audio_paths = self.audio_extractor.extract_audio_segments(video_path, srt_path)
            print(f"成功提取 {len(audio_paths)} 个音频片段")
            
            # 2. 提取嵌入向量
            print("步骤2: 正在提取说话人嵌入...")
            embeddings = self.embedding_extractor.extract_embeddings(audio_paths)
            print(f"成功提取 {len([e for e in embeddings if e is not None])} 个嵌入向量")
            
            # 3. 聚类识别说话人
            print("步骤3: 正在聚类识别说话人...")
            speaker_labels = self.clusterer.cluster_embeddings(embeddings)
            unique_speakers = self.clusterer.get_unique_speakers_count(speaker_labels)
            print(f"识别出 {unique_speakers} 个不同说话人")
            
            # 4. 返回结果
            result = {
                "success": True,
                "audio_paths": audio_paths,
                "speaker_labels": speaker_labels,
                "unique_speakers": unique_speakers,
                "total_segments": len(audio_paths)
            }
            
            return result
            
        except Exception as e:
            print(f"处理过程中出现错误: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "audio_paths": [],
                "speaker_labels": [],
                "unique_speakers": 0,
                "total_segments": 0
            }
    
    def get_audio_cache_dir(self) -> str:
        """获取音频缓存目录路径"""
        return str(self.audio_extractor.get_cache_dir())


if __name__ == "__main__":
    # 示例用法
    # processor = SpeakerDiarizationProcessor()
    # result = processor.process_video_speaker_diarization(
    #     "path/to/video.mp4", 
    #     "path/to/subtitle.srt"
    # )
    # print(result)
    pass