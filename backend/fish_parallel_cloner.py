"""
并行克隆引擎 - Layer 1 优化
使用进程池实现跨说话人并行处理

作者：Claude (第二阶段优化)
"""
import os
import psutil
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Dict, List
from loguru import logger
from fish_worker_process import worker_process_main, init_worker_process


# fish-speech 仓库路径
FISH_SPEECH_DIR = "/Users/yiya_workstation/Documents/ai_editing/fish-speech"
CHECKPOINT_DIR = os.path.join(FISH_SPEECH_DIR, "checkpoints/openaudio-s1-mini")


class ParallelFishCloner:
    """
    并行语音克隆器 - 第二阶段优化

    核心优势：
    - ✅ 消除模型重复加载（每个 worker 仅加载一次）
    - ✅ 跨说话人并行处理（3 个 worker 同时工作）
    - ✅ 智能负载均衡（任务均匀分配）
    - ✅ 集成 Layer 2 和 Layer 3 优化
    - ✅ 自动内存管理和降级

    预期加速：5-7x（相比原始顺序模式）
    """

    def __init__(
        self,
        num_workers: int = None,
        checkpoint_path: str = CHECKPOINT_DIR,
        batch_size: int = 10,
        io_threads: int = 2
    ):
        """
        初始化并行克隆器

        Args:
            num_workers: Worker 进程数，None 表示自动检测
            checkpoint_path: Fish-Speech 模型检查点路径
            batch_size: DAC 批量解码大小
            io_threads: 每个 worker 的 I/O 线程数
        """
        self.checkpoint_path = checkpoint_path
        self.batch_size = batch_size
        self.io_threads = io_threads

        # 自动检测最优 worker 数量
        if num_workers is None:
            self.num_workers = self._auto_detect_workers()
        else:
            self.num_workers = num_workers

        logger.info(f"🚀 并行克隆器初始化: {self.num_workers} 个 worker 进程")

    def _auto_detect_workers(self) -> int:
        """
        根据可用内存自动检测最优 worker 数量

        估算：
        - 每个 worker 需要约 5-6GB 内存（模型 + 推理）
        - Mac mini M4 (24GB)：最多 3 个 worker
        - 预留 9GB 系统内存

        Returns:
            推荐的 worker 数量
        """
        available_mem_gb = psutil.virtual_memory().available / (1024**3)

        logger.info(f"💾 可用内存: {available_mem_gb:.1f} GB")

        if available_mem_gb >= 15:
            # 充足内存：3 个 worker
            num_workers = 3
        elif available_mem_gb >= 10:
            # 中等内存：2 个 worker
            num_workers = 2
        else:
            # 内存紧张：1 个 worker（降级但仍比原始模式快）
            num_workers = 1

        logger.info(
            f"⚙️  自动检测: 使用 {num_workers} 个 worker "
            f"(每个约占用 5GB, 预留 9GB 系统内存)"
        )

        return num_workers

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        speaker_npy_files: Dict[int, str],
        speaker_references: Dict[int, Dict],
        output_dir: str,
        script_dir: str = None  # 为了兼容原接口，但不使用
    ) -> Dict[int, str]:
        """
        批量生成所有语音片段（并行模式）

        Args:
            tasks: 任务列表 [{"speaker_id": int, "target_text": str, "segment_index": int}, ...]
            speaker_npy_files: 说话人 npy 文件字典 {speaker_id: npy_path}
            speaker_references: 说话人参考信息字典 {speaker_id: {"reference_text": str, ...}}
            output_dir: 输出目录
            script_dir: 脚本目录（兼容参数，并行模式不使用）

        Returns:
            生成的音频文件字典 {segment_index: file_path}
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"🐟 [并行生成] 开始批量生成 {len(tasks)} 个语音片段")
        logger.info(f"🚀 使用 {self.num_workers} 个 worker 进程并行处理")
        logger.info(f"{'='*80}\n")

        os.makedirs(output_dir, exist_ok=True)

        # ==================================================================
        # Step 1: 按说话人分组任务
        # ==================================================================
        tasks_by_speaker = self._group_by_speaker(tasks)
        logger.info(f"📊 共有 {len(tasks_by_speaker)} 个说话人")

        for speaker_id, speaker_tasks in tasks_by_speaker.items():
            logger.info(f"  - 说话人 {speaker_id}: {len(speaker_tasks)} 个片段")

        # ==================================================================
        # Step 2: 负载均衡分配任务
        # ==================================================================
        worker_assignments = self._balance_workload(
            tasks_by_speaker,
            self.num_workers
        )

        logger.info(f"\n📋 任务分配方案:")
        for worker_id, speaker_ids in enumerate(worker_assignments):
            total_tasks = sum(
                len(tasks_by_speaker[sid]) for sid in speaker_ids
            )
            logger.info(
                f"  Worker #{worker_id}: 说话人 {speaker_ids} "
                f"({total_tasks} 个片段)"
            )

        # ==================================================================
        # Step 3: 创建进程池并并行执行
        # ==================================================================
        logger.info(f"\n🚀 启动 {self.num_workers} 个 worker 进程...\n")

        all_generated_files = {}

        # 使用 spawn 方式创建进程（MPS 要求）
        import multiprocessing
        ctx = multiprocessing.get_context('spawn')

        with ProcessPoolExecutor(
            max_workers=self.num_workers,
            mp_context=ctx,
            initializer=init_worker_process
        ) as executor:
            # 提交所有 worker 任务
            futures = []
            for worker_id, speaker_ids in enumerate(worker_assignments):
                if not speaker_ids:
                    continue  # 跳过空分配

                future = executor.submit(
                    worker_process_main,
                    worker_id=worker_id,
                    assigned_speaker_ids=speaker_ids,
                    tasks=tasks,
                    speaker_npy_files=speaker_npy_files,
                    speaker_references=speaker_references,
                    output_dir=output_dir,
                    checkpoint_path=self.checkpoint_path,
                    batch_size=self.batch_size,
                    io_threads=self.io_threads
                )
                futures.append((worker_id, future))

            # 等待所有 worker 完成并收集结果
            for worker_id, future in futures:
                try:
                    generated_files = future.result()
                    all_generated_files.update(generated_files)
                    logger.info(
                        f"✅ Worker #{worker_id} 完成: "
                        f"生成 {len(generated_files)} 个音频文件"
                    )
                except Exception as e:
                    logger.error(f"❌ Worker #{worker_id} 失败: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

        logger.info(f"\n{'='*80}")
        logger.info(f"🎉 并行生成完成！共生成 {len(all_generated_files)} 个音频文件")
        logger.info(f"{'='*80}\n")

        return all_generated_files

    def _group_by_speaker(self, tasks: List[Dict]) -> Dict[int, List[Dict]]:
        """
        按说话人分组任务

        Args:
            tasks: 任务列表

        Returns:
            分组后的任务字典 {speaker_id: [task1, task2, ...]}
        """
        tasks_by_speaker = {}
        for task in tasks:
            speaker_id = task['speaker_id']
            if speaker_id not in tasks_by_speaker:
                tasks_by_speaker[speaker_id] = []
            tasks_by_speaker[speaker_id].append(task)

        return tasks_by_speaker

    def _balance_workload(
        self,
        tasks_by_speaker: Dict[int, List[Dict]],
        num_workers: int
    ) -> List[List[int]]:
        """
        负载均衡算法 - 贪心策略

        目标：将说话人分配给各个 worker，使各 worker 的任务数尽量均衡

        策略：
        1. 按任务数量对说话人降序排序
        2. 每次将任务最多的说话人分配给当前负载最小的 worker

        Args:
            tasks_by_speaker: 按说话人分组的任务
            num_workers: Worker 数量

        Returns:
            分配方案 [[speaker_id1, speaker_id2], [speaker_id3], ...]
        """
        # 按任务数量降序排序说话人
        sorted_speakers = sorted(
            tasks_by_speaker.keys(),
            key=lambda sid: len(tasks_by_speaker[sid]),
            reverse=True
        )

        # 初始化 worker 分配和负载统计
        worker_assignments = [[] for _ in range(num_workers)]
        worker_loads = [0] * num_workers

        # 贪心分配
        for speaker_id in sorted_speakers:
            task_count = len(tasks_by_speaker[speaker_id])

            # 找到当前负载最小的 worker
            min_load_worker = worker_loads.index(min(worker_loads))

            # 分配给该 worker
            worker_assignments[min_load_worker].append(speaker_id)
            worker_loads[min_load_worker] += task_count

        return worker_assignments

    # ==================================================================
    # 兼容接口 - 支持批量编码
    # ==================================================================
    def batch_encode_speakers(
        self,
        speaker_references: Dict,
        output_dir: str
    ) -> Dict[int, str]:
        """
        批量编码所有说话人的参考音频

        注意：编码阶段不需要并行（速度已经很快）
        复用原有的 FishBatchCloner 实现

        Args:
            speaker_references: 说话人参考信息
            output_dir: 输出目录

        Returns:
            编码结果 {speaker_id: npy_file_path}
        """
        from fish_batch_cloner import FishBatchCloner

        logger.info("🔄 使用顺序模式进行批量编码（编码速度已足够快）")
        cloner = FishBatchCloner(
            fish_speech_dir=FISH_SPEECH_DIR,
            checkpoint_dir=self.checkpoint_path
        )
        return cloner.batch_encode_speakers(speaker_references, output_dir)
