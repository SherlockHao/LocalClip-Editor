"""
I/O 流水线模块 - Layer 3 优化
实现异步音频保存，与推理计算重叠，隐藏 I/O 时间

作者：Claude (优化方案第一阶段)
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import soundfile as sf
from pathlib import Path
from typing import List, Optional
import numpy as np


class IOPipeline:
    """
    I/O 流水线 - 异步音频保存

    核心思想：
    - 推理完成后立即提交音频保存任务到线程池
    - 不等待保存完成，继续下一批推理
    - 最后统一等待所有 I/O 完成

    优势：
    - I/O 与计算重叠，隐藏文件写入时间
    - 使用线程池处理 I/O 密集型操作（不受 GIL 限制）
    - 批量等待，减少阻塞时间
    """

    def __init__(self, num_threads: int = 2):
        """
        初始化 I/O 流水线

        Args:
            num_threads: I/O 线程数，默认 2
                        (音频文件写入相对快速，2个线程足够)
        """
        self.executor = ThreadPoolExecutor(
            max_workers=num_threads,
            thread_name_prefix="IOWorker"
        )
        self.pending_tasks = []
        self._is_shutdown = False

    def async_save_audio(
        self,
        audio: np.ndarray,
        path: str,
        sample_rate: int
    ) -> None:
        """
        异步保存音频文件

        非阻塞操作，立即返回，不等待文件写入完成

        Args:
            audio: 音频数据 (numpy array)
            path: 保存路径
            sample_rate: 采样率
        """
        if self._is_shutdown:
            raise RuntimeError("IOPipeline 已关闭，无法提交新任务")

        future = self.executor.submit(
            self._save_audio,
            audio=audio,
            path=path,
            sample_rate=sample_rate
        )
        self.pending_tasks.append(future)

    def _save_audio(
        self,
        audio: np.ndarray,
        path: str,
        sample_rate: int
    ) -> str:
        """
        实际的音频保存逻辑（在线程池中执行）

        Args:
            audio: 音频数据
            path: 保存路径
            sample_rate: 采样率

        Returns:
            保存的文件路径

        Raises:
            Exception: 保存失败时抛出异常
        """
        try:
            # 确保目录存在
            Path(path).parent.mkdir(parents=True, exist_ok=True)

            # 保存音频文件
            sf.write(path, audio, sample_rate)

            return path
        except Exception as e:
            print(f"❌ 保存音频失败 {path}: {e}")
            raise

    def wait_all(self, timeout: Optional[float] = None) -> List[str]:
        """
        等待所有待处理的 I/O 任务完成

        Args:
            timeout: 最大等待时间（秒），None 表示无限等待

        Returns:
            成功保存的文件路径列表

        Raises:
            Exception: 如果有任务失败，会抛出第一个遇到的异常
        """
        saved_files = []
        failed_count = 0

        for future in as_completed(self.pending_tasks, timeout=timeout):
            try:
                file_path = future.result()
                saved_files.append(file_path)
            except Exception as e:
                print(f"❌ I/O 任务失败: {e}")
                failed_count += 1

        # 清空已完成的任务
        self.pending_tasks.clear()

        if failed_count > 0:
            print(f"⚠️ 有 {failed_count} 个音频文件保存失败")

        return saved_files

    def get_pending_count(self) -> int:
        """
        获取待处理的任务数量

        Returns:
            待处理任务数
        """
        return len(self.pending_tasks)

    def shutdown(self, wait: bool = True) -> None:
        """
        关闭 I/O 流水线

        Args:
            wait: 是否等待所有任务完成，默认 True
        """
        if self._is_shutdown:
            return

        if wait and self.pending_tasks:
            print(f"等待 {len(self.pending_tasks)} 个 I/O 任务完成...")
            self.wait_all()

        self.executor.shutdown(wait=wait)
        self._is_shutdown = True

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown(wait=True)
        return False


# 使用示例
if __name__ == "__main__":
    import time

    # 创建测试音频数据
    sample_rate = 44100
    duration = 1.0
    test_audio = np.random.randn(int(sample_rate * duration)).astype(np.float32)

    # 使用上下文管理器
    with IOPipeline(num_threads=2) as pipeline:
        print("开始异步保存音频...")

        # 提交多个保存任务
        for i in range(5):
            pipeline.async_save_audio(
                audio=test_audio,
                path=f"/tmp/test_audio_{i}.wav",
                sample_rate=sample_rate
            )
            print(f"已提交任务 {i}")

        print(f"所有任务已提交，待处理: {pipeline.get_pending_count()}")
        print("可以继续做其他事情...")

        # 模拟其他计算
        time.sleep(0.1)

        print("等待所有 I/O 完成...")
        # 退出上下文管理器时自动等待所有任务完成

    print("✅ 所有音频保存完成！")
