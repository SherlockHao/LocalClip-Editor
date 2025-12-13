"""
Worker 进程模块 - Layer 1 优化
实现持久化模型加载和任务处理

作者：Claude (第二阶段优化)
"""
import os
import sys
import platform
import torch
import numpy as np
from typing import Dict, List, Tuple
from loguru import logger
from fish_batch_processor import BatchProcessor

# 添加 fish-speech 目录到 Python 路径
if platform.system() == "Windows":
    FISH_SPEECH_DIR = os.environ.get("FISH_SPEECH_DIR", r"C:\workspace\ai_editing\fish-speech-win")
else:
    FISH_SPEECH_DIR = os.environ.get("FISH_SPEECH_DIR", "/Users/yiya_workstation/Documents/ai_editing/fish-speech")

# 确保 fish_speech 模块可以被导入
if FISH_SPEECH_DIR not in sys.path:
    sys.path.insert(0, FISH_SPEECH_DIR)


# ==============================================================================
# 全局变量 - 进程级持久化模型
# ==============================================================================
# 在 worker 进程首次调用时加载，之后复用
_WORKER_MODELS = None
_WORKER_DEVICE = None


def _get_device() -> str:
    """
    检测可用设备

    Returns:
        设备名称: "cuda", "mps", 或 "cpu"
    """
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "mps"
    else:
        return "cpu"


def _load_models(checkpoint_path: str, device: str) -> Dict:
    """
    加载 Fish-Speech 模型（DAC + Text2Semantic）

    Args:
        checkpoint_path: 模型检查点路径
        device: 计算设备

    Returns:
        模型字典，包含:
        - "dac": DAC 解码模型
        - "text2semantic": Text2Semantic 模型
        - "decode_one_token": 解码函数
    """
    # 导入 Fish-Speech 模块（延迟导入，避免主进程加载）
    from fish_speech.models.dac.inference import load_model as load_dac_model
    from fish_speech.models.text2semantic.inference import init_model

    logger.info(f"🔧 正在加载模型到设备: {device}")

    # 设置精度
    if device == "cuda":
        precision = torch.bfloat16
    else:
        precision = torch.float32

    # 加载 DAC 模型
    logger.info("  📦 加载 DAC 模型...")
    dac_model = load_dac_model(
        config_name="modded_dac_vq",
        checkpoint_path=os.path.join(checkpoint_path, "codec.pth"),
        device=device
    )
    logger.info("  ✅ DAC 模型加载完成")

    # 加载 Text2Semantic 模型
    logger.info("  📦 加载 Text2Semantic 模型...")
    text2semantic_model, decode_one_token = init_model(
        checkpoint_path=checkpoint_path,
        device=device,
        precision=precision,
        compile=False  # MPS 不支持 torch.compile
    )
    logger.info("  ✅ Text2Semantic 模型加载完成")

    return {
        "dac": dac_model,
        "text2semantic": text2semantic_model,
        "decode_one_token": decode_one_token
    }


def worker_process_main(
    worker_id: int,
    assigned_speaker_ids: List[int],
    tasks: List[Dict],
    speaker_npy_files: Dict[int, str],
    speaker_references: Dict[int, Dict],
    output_dir: str,
    checkpoint_path: str,
    batch_size: int = 10,
    io_threads: int = 2
) -> Dict[int, str]:
    """
    Worker 进程主函数 - 处理分配的说话人任务

    Args:
        worker_id: Worker 进程 ID
        assigned_speaker_ids: 分配给此 worker 的说话人 ID 列表
        tasks: 所有任务列表 [{"speaker_id": int, "target_text": str, "segment_index": int}, ...]
        speaker_npy_files: 说话人 npy 文件字典 {speaker_id: npy_path}
        speaker_references: 说话人参考信息字典 {speaker_id: {"reference_text": str, ...}}
        output_dir: 输出目录
        checkpoint_path: 模型检查点路径
        batch_size: DAC 批量解码大小
        io_threads: I/O 线程数

    Returns:
        生成的音频文件字典 {segment_index: file_path}
    """
    global _WORKER_MODELS, _WORKER_DEVICE

    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Worker #{worker_id} 启动")
    logger.info(f"分配的说话人: {assigned_speaker_ids}")
    logger.info(f"{'='*60}\n")

    # ==============================================================================
    # Step 1: 初始化模型（首次调用时加载，之后复用）
    # ==============================================================================
    if _WORKER_MODELS is None:
        logger.info(f"⚙️  Worker #{worker_id}: 首次运行，正在加载模型...")
        _WORKER_DEVICE = _get_device()
        _WORKER_MODELS = _load_models(checkpoint_path, _WORKER_DEVICE)
        logger.info(f"✅ Worker #{worker_id}: 模型加载完成，可复用于后续任务")
    else:
        logger.info(f"♻️  Worker #{worker_id}: 复用已加载的模型")

    device = _WORKER_DEVICE

    # ==============================================================================
    # Step 2: 创建批处理器
    # ==============================================================================
    processor = BatchProcessor(
        models=_WORKER_MODELS,
        batch_size=batch_size,
        io_threads=io_threads
    )

    # ==============================================================================
    # Step 3: 处理分配的说话人任务
    # ==============================================================================
    all_generated_files = {}

    for speaker_id in assigned_speaker_ids:
        logger.info(f"\n{'='*60}")
        logger.info(f"🎤 Worker #{worker_id}: 处理说话人 {speaker_id}")
        logger.info(f"{'='*60}")

        # 检查 npy 文件是否存在
        if speaker_id not in speaker_npy_files:
            logger.warning(f"⚠️  说话人 {speaker_id} 没有 .npy 文件，跳过")
            continue

        # 获取该说话人的所有任务
        speaker_tasks = [t for t in tasks if t["speaker_id"] == speaker_id]
        if not speaker_tasks:
            logger.warning(f"⚠️  说话人 {speaker_id} 没有分配任务，跳过")
            continue

        logger.info(f"📋 说话人 {speaker_id} 共有 {len(speaker_tasks)} 个片段")

        # 提取文本和索引
        texts = [task["target_text"] for task in speaker_tasks]
        segment_indices = [task["segment_index"] for task in speaker_tasks]

        # 加载该说话人的 prompt tokens
        npy_file = speaker_npy_files[speaker_id]
        logger.info(f"📂 加载 Prompt Tokens: {npy_file}")
        prompt_tokens = np.load(npy_file)
        prompt_tokens = torch.from_numpy(prompt_tokens).to(device).long()
        if prompt_tokens.ndim == 3:
            prompt_tokens = prompt_tokens[0]

        # 获取参考文本
        ref_text = speaker_references[speaker_id]["reference_text"]

        # 批量生成该说话人的所有音频
        try:
            generated_files = processor.batch_generate_for_speaker(
                texts=texts,
                segment_indices=segment_indices,
                prompt_tokens=prompt_tokens,
                ref_text=ref_text,
                output_dir=output_dir,
                device=device,
                max_new_tokens=4096,
                top_p=0.7,
                temperature=0.7,
                repetition_penalty=1.2
            )

            # 合并到总结果
            all_generated_files.update(generated_files)

            logger.info(
                f"✅ Worker #{worker_id}: 说话人 {speaker_id} "
                f"完成 {len(generated_files)} 个片段"
            )

        except Exception as e:
            logger.error(
                f"❌ Worker #{worker_id}: 说话人 {speaker_id} 处理失败: {e}"
            )
            import traceback
            logger.error(traceback.format_exc())
            continue

    # ==============================================================================
    # Step 4: 关闭批处理器（等待所有 I/O 完成）
    # ==============================================================================
    processor.shutdown()

    logger.info(f"\n{'='*60}")
    logger.info(
        f"🎉 Worker #{worker_id} 完成！共生成 {len(all_generated_files)} 个音频文件"
    )
    logger.info(f"{'='*60}\n")

    return all_generated_files


# ==============================================================================
# 进程初始化函数（用于 ProcessPoolExecutor 的 initializer）
# ==============================================================================
def init_worker_process():
    """
    Worker 进程初始化函数

    在每个 worker 进程启动时调用（仅一次）
    设置必要的环境变量和配置
    """
    # 添加 fish-speech 目录到 Python 路径（关键！）
    fish_speech_dir = "/Users/yiya_workstation/Documents/ai_editing/fish-speech"
    if fish_speech_dir not in sys.path:
        sys.path.insert(0, fish_speech_dir)

    # 设置日志级别
    logger.remove()  # 移除默认处理器
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # 禁用 tokenizers 并行（避免多进程警告）
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    logger.info("🔧 Worker 进程初始化完成")
