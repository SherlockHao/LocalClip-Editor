"""
NISQA MOS 评分模块
使用 NISQA 模型进行音频质量评估，替换 DNSMOS
"""
import os
import sys
import glob
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import tempfile
import json


class NISQAScorer:
    """NISQA 音频质量评分器（批量处理优化版）"""

    def __init__(
        self,
        nisqa_dir: str = None,
        pretrained_model: str = None,
        num_workers: int = 0,
        batch_size: int = 1
    ):
        """
        初始化 NISQA 评分器

        Args:
            nisqa_dir: NISQA 仓库路径，默认从环境变量 NISQA_DIR 读取
            pretrained_model: 预训练模型路径，默认使用 weights/nisqa_mos_only.tar
            num_workers: DataLoader 的 worker 数量
            batch_size: 批处理大小
        """
        import platform

        if platform.system() == "Windows":
            self.nisqa_dir = nisqa_dir or os.environ.get(
                "NISQA_DIR",
                r"C:\workspace\ai_editing\NISQA"
            )
        else:
            self.nisqa_dir = nisqa_dir or os.environ.get(
                "NISQA_DIR",
                "/workspace/ai_editing/NISQA"
            )

        if not os.path.exists(self.nisqa_dir):
            raise FileNotFoundError(f"NISQA 目录不存在: {self.nisqa_dir}")

        # 预训练模型路径
        self.pretrained_model = pretrained_model or os.path.join(
            self.nisqa_dir, "weights", "nisqa_mos_only.tar"
        )

        if not os.path.exists(self.pretrained_model):
            raise FileNotFoundError(f"NISQA 模型不存在: {self.pretrained_model}")

        self.num_workers = num_workers
        self.batch_size = batch_size

        # 添加 NISQA 到 Python 路径
        if self.nisqa_dir not in sys.path:
            sys.path.insert(0, self.nisqa_dir)

        print(f"[NISQA] NISQA 目录: {self.nisqa_dir}")
        print(f"[NISQA] 模型路径: {self.pretrained_model}")

        # 延迟加载模型（第一次调用时加载）
        self._model = None

    def _get_model_args(self, data_dir: str = None):
        """获取模型参数"""
        # 如果没有提供 data_dir，使用临时目录
        if data_dir is None:
            import tempfile
            data_dir = tempfile.gettempdir()

        return {
            'mode': 'predict_dir',
            'pretrained_model': self.pretrained_model,
            'data_dir': data_dir,
            'output_dir': None,
            'csv_file': None,
            'csv_deg': None,
            'deg': None,
            'num_workers': self.num_workers,
            'bs': self.batch_size,
            'ms_channel': None,
            'tr_bs_val': self.batch_size,
            'tr_num_workers': self.num_workers,
            'dim': False,
            'tr_parallel': False
        }

    def _ensure_model_loaded(self, data_dir: str = None):
        """
        确保模型已加载（只加载一次）

        注意：NISQA 模型初始化时需要 data_dir，所以第一次调用时必须提供
        """
        if self._model is None:
            print("[NISQA] 加载 NISQA 模型...")
            from nisqa.NISQA_model import nisqaModel

            args = self._get_model_args(data_dir)
            self._model = nisqaModel(args)
            print("[NISQA] 模型加载完成")

    def score_audio(self, audio_path: str) -> float:
        """
        对单个音频文件进行 MOS 打分

        Args:
            audio_path: 音频文件路径

        Returns:
            float: MOS 分数（范围 1-5）
        """
        # 使用批量方法处理单个文件
        results = self.score_audio_batch([audio_path])
        if results:
            return results[0][1]
        return 0.0

    def score_audio_batch(
        self,
        audio_paths: List[str],
        temp_dir: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        批量对多个音频文件进行 MOS 打分（核心优化方法）

        Args:
            audio_paths: 音频文件路径列表
            temp_dir: 临时目录，用于存放符号链接（如果需要）

        Returns:
            List[Tuple[str, float]]: 列表，每个元素为 (音频路径, MOS分数)
        """
        if not audio_paths:
            return []

        try:
            # 创建临时目录，存放所有音频文件的符号链接或拷贝
            # NISQA 需要所有音频在同一个目录下
            use_temp_dir = temp_dir is None
            if use_temp_dir:
                temp_dir = tempfile.mkdtemp(prefix="nisqa_batch_")

            try:
                # 准备音频文件：创建符号链接或复制到临时目录
                # 必须在加载模型之前完成，因为 NISQA 初始化时会检查目录
                audio_map = {}  # {临时文件名: 原始路径}

                for i, audio_path in enumerate(audio_paths):
                    if not os.path.exists(audio_path):
                        print(f"[NISQA] 警告：音频文件不存在: {audio_path}")
                        continue

                    # 使用原始文件名
                    original_name = os.path.basename(audio_path)
                    # 如果文件名重复，添加索引
                    temp_name = original_name
                    counter = 1
                    while temp_name in audio_map:
                        name, ext = os.path.splitext(original_name)
                        temp_name = f"{name}_{counter}{ext}"
                        counter += 1

                    temp_path = os.path.join(temp_dir, temp_name)

                    # 在 Windows 上创建硬链接或复制文件
                    # 在 Unix 上创建符号链接
                    try:
                        import platform
                        if platform.system() == "Windows":
                            # Windows: 尝试硬链接，失败则复制
                            try:
                                os.link(audio_path, temp_path)
                            except:
                                import shutil
                                shutil.copy2(audio_path, temp_path)
                        else:
                            # Unix: 符号链接
                            os.symlink(audio_path, temp_path)

                        audio_map[temp_name] = audio_path
                    except Exception as e:
                        print(f"[NISQA] 警告：无法链接文件 {audio_path}: {e}")
                        continue

                if not audio_map:
                    print("[NISQA] 没有有效的音频文件可以评分")
                    return []

                # 加载模型（在文件链接完成后）
                self._ensure_model_loaded(temp_dir)

                print(f"[NISQA] 准备评分 {len(audio_map)} 个音频文件...")

                # 更新模型的 data_dir
                self._model.args['data_dir'] = temp_dir

                # 执行批量预测
                results_df = self._model.predict()

                # 解析结果
                results = []
                for _, row in results_df.iterrows():
                    # NISQA 返回的文件名（可能包含路径）
                    deg_file = row.get('deg', row.get('filename', ''))
                    # 提取文件名
                    temp_name = os.path.basename(deg_file)

                    # 查找原始路径
                    if temp_name in audio_map:
                        original_path = audio_map[temp_name]
                        mos_score = float(row.get('mos_pred', 0.0))
                        results.append((original_path, mos_score))

                print(f"[NISQA] 完成评分，共 {len(results)} 个文件")

                return results

            finally:
                # 清理临时文件
                if use_temp_dir:
                    import shutil
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass

        except Exception as e:
            print(f"[NISQA] 批量评分失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def score_speaker_audios(
        self,
        audio_dir: str,
        speaker_segments: Dict[int, List[str]]
    ) -> Dict[int, List[Tuple[str, float]]]:
        """
        对每个说话人的音频片段进行 MOS 打分（批量优化版）

        Args:
            audio_dir: 音频片段所在目录（可以为None，如果segment_files已经是完整路径）
            speaker_segments: 字典，key为说话人ID，value为该说话人的音频文件路径列表

        Returns:
            Dict[int, List[Tuple[str, float]]]: 字典，key为说话人ID，
                value为列表，每个元素为(音频路径, MOS分数)
        """
        results = {}

        # 收集所有音频文件路径
        all_audio_paths = []
        path_to_speaker = {}  # {音频路径: 说话人ID}

        for speaker_id, segment_files in speaker_segments.items():
            # 检查segment_files是否已经是完整路径
            first_path = segment_files[0] if segment_files else ""
            has_dir_separator = '/' in first_path or '\\' in first_path

            if segment_files and (Path(first_path).is_absolute() or has_dir_separator):
                # 已经是完整路径
                full_paths = segment_files
            else:
                # 需要拼接audio_dir
                full_paths = [str(Path(audio_dir) / f) for f in segment_files]

            for path in full_paths:
                all_audio_paths.append(path)
                path_to_speaker[path] = speaker_id

        if not all_audio_paths:
            print("[NISQA] 没有音频文件需要评分")
            return results

        print(f"[NISQA] 开始批量评分 {len(all_audio_paths)} 个音频文件...")

        # 批量评分（一次性处理所有音频，模型只加载一次）
        all_scores = self.score_audio_batch(all_audio_paths)

        # 按说话人分组结果
        for audio_path, score in all_scores:
            speaker_id = path_to_speaker.get(audio_path)
            if speaker_id is not None:
                if speaker_id not in results:
                    results[speaker_id] = []
                results[speaker_id].append((audio_path, score))

        # 打印统计信息
        for speaker_id, scores in results.items():
            if scores:
                avg_score = np.mean([s for _, s in scores])
                print(f"[NISQA] 说话人 {speaker_id}: {len(scores)} 个片段, 平均MOS分数: {avg_score:.2f}")

        return results


# 向后兼容：保留旧的 MOSScorer 接口
class MOSScorer(NISQAScorer):
    """向后兼容的 MOS 评分器（使用 NISQA）"""
    pass
