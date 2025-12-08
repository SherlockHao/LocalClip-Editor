"""
批处理核心模块 - Layer 2 优化
封装批量生成逻辑，可在 worker 进程中复用

作者：Claude (第二阶段优化)
"""
import os
import torch
import numpy as np
from typing import List, Dict, Tuple, Optional
from loguru import logger
from fish_io_pipeline import IOPipeline


class BatchProcessor:
    """
    批处理器 - 封装批量语音生成逻辑

    核心功能：
    - 批量生成一个说话人的所有音频片段
    - 集成批量 DAC 解码优化（Layer 2）
    - 集成异步 I/O 流水线（Layer 3）
    - 可在 worker 进程中复用
    """

    def __init__(
        self,
        models: Dict,
        batch_size: int = 10,
        io_threads: int = 2
    ):
        """
        初始化批处理器

        Args:
            models: 模型字典，包含:
                - "dac": DAC 解码模型
                - "text2semantic": Text2Semantic 模型
                - "decode_one_token": 解码函数
            batch_size: DAC 批量解码大小，默认 5
            io_threads: I/O 线程数，默认 2
        """
        self.dac_model = models["dac"]
        self.text2semantic_model = models["text2semantic"]
        self.decode_one_token = models["decode_one_token"]
        self.batch_size = batch_size
        self.io_pipeline = IOPipeline(num_threads=io_threads)

    def batch_generate_for_speaker(
        self,
        texts: List[str],
        segment_indices: List[int],
        prompt_tokens: torch.Tensor,
        ref_text: str,
        output_dir: str,
        device: str,
        max_new_tokens: int = 4096,
        top_p: float = 0.7,
        temperature: float = 0.7,
        repetition_penalty: float = 1.2
    ) -> Dict[int, str]:
        """
        批量生成一个说话人的所有音频片段

        Args:
            texts: 目标文本列表
            segment_indices: 片段索引列表
            prompt_tokens: 说话人参考音频的 VQ codes
            ref_text: 参考文本
            output_dir: 输出目录
            device: 计算设备
            max_new_tokens: 最大生成 token 数
            top_p: nucleus sampling 参数
            temperature: 采样温度
            repetition_penalty: 重复惩罚系数

        Returns:
            生成的音频文件字典 {segment_index: file_path}
        """
        # 导入 Fish-Speech 推理模块（延迟导入，避免进程间冲突）
        from fish_speech.models.text2semantic.inference import generate_long

        total_segments = len(texts)
        generated_files = {}

        logger.info(f"🚀 开始批量生成 {total_segments} 个片段（批大小: {self.batch_size}）...")

        try:
            # 分批处理
            for batch_start in range(0, total_segments, self.batch_size):
                batch_end = min(batch_start + self.batch_size, total_segments)
                batch_texts = texts[batch_start:batch_end]
                batch_indices = segment_indices[batch_start:batch_end]
                batch_num = batch_start // self.batch_size + 1

                logger.info(
                    f"\n📦 批次 {batch_num}: 处理片段 {batch_start}-{batch_end-1} "
                    f"({len(batch_texts)} 个)"
                )

                # Step 1: 生成所有语义 tokens（仍需循环，受 generate_long 限制）
                codes_list = []
                valid_indices = []

                for i, text in enumerate(batch_texts):
                    segment_idx = batch_indices[i]
                    logger.info(
                        f"  [{i+1}/{len(batch_texts)}] 生成语义 tokens "
                        f"(片段 {segment_idx}): {text[:30]}..."
                    )

                    try:
                        codes = None
                        for response in generate_long(
                            model=self.text2semantic_model,
                            device=device,
                            decode_one_token=self.decode_one_token,
                            text=text,
                            prompt_text=ref_text,
                            prompt_tokens=prompt_tokens,
                            max_new_tokens=max_new_tokens,
                            top_p=top_p,
                            temperature=temperature,
                            repetition_penalty=repetition_penalty,
                            num_samples=1
                        ):
                            if response.action == "sample":
                                codes = response.codes

                        if codes is not None:
                            codes_list.append(codes)
                            valid_indices.append(segment_idx)
                        else:
                            logger.error(f"  ❌ 未能生成语义 tokens (片段 {segment_idx})")

                    except Exception as e:
                        logger.error(f"  ❌ 生成失败 (片段 {segment_idx}): {e}")

                if not codes_list:
                    logger.warning(f"  ⚠️ 批次 {batch_num} 没有成功生成任何语义 tokens")
                    continue

                # Step 2: 批量 DAC 解码（关键优化！）
                logger.info(f"  🔄 批量 DAC 解码 {len(codes_list)} 个样本...")
                audios = self._batch_dac_decode(codes_list, device)
                logger.info(f"  ✅ 批量解码完成")

                # Step 3: 异步保存（Layer 3 优化）
                logger.info(f"  💾 异步保存 {len(audios)} 个音频文件...")
                for audio, segment_idx in zip(audios, valid_indices):
                    output_filename = os.path.join(
                        output_dir,
                        f"segment_{segment_idx:04d}.wav"
                    )
                    # 异步提交保存任务（不阻塞）
                    self.io_pipeline.async_save_audio(
                        audio=audio,
                        path=output_filename,
                        sample_rate=self.dac_model.sample_rate
                    )
                    generated_files[segment_idx] = output_filename

                logger.info(f"  ✅ 批次 {batch_num} 处理完成")

                # 清理显存
                del codes_list, audios
                if device == "mps":
                    torch.mps.empty_cache()
                elif torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # 等待所有 I/O 完成
            logger.info(f"\n⏳ 等待所有音频文件保存完成...")
            saved_files = self.io_pipeline.wait_all()
            logger.info(f"✅ 已保存 {len(saved_files)} 个音频文件")

        except Exception as e:
            logger.error(f"❌ 批量生成失败: {e}")
            raise

        return generated_files

    def _batch_dac_decode(
        self,
        codes_list: List[torch.Tensor],
        device: str
    ) -> List[np.ndarray]:
        """
        批量 DAC 解码 - Layer 2 核心优化

        原来：逐个解码，N 次 GPU 调用
        现在：批量解码，1 次 GPU 调用

        Args:
            codes_list: 语义 codes 列表
            device: 计算设备

        Returns:
            音频数组列表
        """
        if not codes_list:
            return []

        # 准备批量输入
        batch_codes = []
        codes_lens = []

        for codes in codes_list:
            if codes.ndim == 2:
                codes = codes.unsqueeze(0)
            batch_codes.append(codes)
            codes_lens.append(codes.shape[-1])

        # Padding 到相同长度
        max_len = max(codes_lens)
        padded_codes = []

        for codes in batch_codes:
            if codes.shape[-1] < max_len:
                # Padding
                pad_len = max_len - codes.shape[-1]
                codes = torch.nn.functional.pad(codes, (0, pad_len), value=0)
            padded_codes.append(codes)

        # 批量拼接
        batch_tensor = torch.cat(padded_codes, dim=0)  # [B, C, T]
        codes_lens_tensor = torch.tensor(codes_lens, device=device, dtype=torch.long)

        # 批量解码（一次 GPU 调用！）
        with torch.no_grad():
            batch_fake_audios, audio_lengths = self.dac_model.decode(
                batch_tensor,
                codes_lens_tensor
            )

        # 分离各个音频，并根据实际长度裁剪
        audios = []
        for i in range(len(codes_lens)):
            # 获取实际音频长度（decode 函数已经计算好了）
            actual_audio_len = audio_lengths[i].item()

            # 提取音频并裁剪到实际长度（去除 padding）
            audio = batch_fake_audios[i, 0].float().cpu().numpy()
            audio = audio[:actual_audio_len]
            audios.append(audio)

        return audios

    def shutdown(self):
        """
        关闭批处理器，等待所有 I/O 完成
        """
        self.io_pipeline.shutdown(wait=True)

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()
        return False
