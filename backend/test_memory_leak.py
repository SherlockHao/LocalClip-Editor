"""
内存泄漏检测测试脚本

此脚本用于监控后端服务在执行任务时的内存使用情况。
不修改原代码，只进行监控和检测。

使用方法：
1. 在一个终端启动后端服务
2. 在另一个终端运行此脚本: python test_memory_leak.py

测试项目：
1. 进程内存监控 (RSS)
2. 临时文件泄漏检测
3. GPU 内存监控 (如果可用)
4. API 调用前后内存对比
"""

import os
import sys
import time
import json
import psutil
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import requests


class MemoryMonitor:
    """内存监控器"""

    def __init__(self, process_name: str = "python"):
        self.process_name = process_name
        self.samples: List[Dict] = []
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None

    def find_backend_process(self) -> Optional[psutil.Process]:
        """查找后端进程"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('main.py' in arg or 'uvicorn' in arg for arg in cmdline if arg):
                    return psutil.Process(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def get_memory_info(self, proc: psutil.Process) -> Dict:
        """获取进程内存信息"""
        try:
            mem_info = proc.memory_info()
            return {
                'timestamp': datetime.now().isoformat(),
                'rss_mb': mem_info.rss / 1024 / 1024,  # 常驻内存
                'vms_mb': mem_info.vms / 1024 / 1024,  # 虚拟内存
                'percent': proc.memory_percent(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}

    def start_monitoring(self, interval: float = 1.0):
        """开始后台监控"""
        self.monitoring = True
        self.samples = []

        def monitor_loop():
            proc = self.find_backend_process()
            if not proc:
                print("[警告] 未找到后端进程，请确保后端服务正在运行")
                return

            print(f"[监控] 开始监控进程 PID: {proc.pid}")
            while self.monitoring:
                mem_info = self.get_memory_info(proc)
                if mem_info:
                    self.samples.append(mem_info)
                time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> List[Dict]:
        """停止监控并返回采样数据"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        return self.samples

    def analyze_samples(self) -> Dict:
        """分析采样数据"""
        if not self.samples:
            return {'error': '没有采样数据'}

        rss_values = [s['rss_mb'] for s in self.samples]
        return {
            'sample_count': len(self.samples),
            'rss_min_mb': min(rss_values),
            'rss_max_mb': max(rss_values),
            'rss_avg_mb': sum(rss_values) / len(rss_values),
            'rss_start_mb': rss_values[0],
            'rss_end_mb': rss_values[-1],
            'rss_diff_mb': rss_values[-1] - rss_values[0],
            'potential_leak': rss_values[-1] - rss_values[0] > 100,  # 超过100MB增长视为可疑
        }


class TempFileMonitor:
    """临时文件监控器"""

    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
        self.initial_files: set = set()
        self.patterns = ['*.json', 'tmp*', '*.wav', '*.mp3']

    def snapshot(self) -> set:
        """获取当前临时文件快照"""
        files = set()
        temp_path = Path(self.temp_dir)
        for pattern in self.patterns:
            files.update(str(f) for f in temp_path.glob(pattern))
        return files

    def start(self):
        """记录初始状态"""
        self.initial_files = self.snapshot()
        print(f"[临时文件] 初始临时文件数: {len(self.initial_files)}")

    def check_leaks(self) -> Dict:
        """检查泄漏的临时文件"""
        current_files = self.snapshot()
        new_files = current_files - self.initial_files

        # 过滤出可能与本项目相关的文件
        project_related = []
        for f in new_files:
            fname = os.path.basename(f).lower()
            if any(keyword in fname for keyword in ['speaker', 'segment', 'cloned', 'translate', 'fish', 'cosy']):
                project_related.append(f)

        return {
            'initial_count': len(self.initial_files),
            'current_count': len(current_files),
            'new_files_count': len(new_files),
            'project_related_count': len(project_related),
            'project_related_files': project_related[:20],  # 只显示前20个
            'potential_leak': len(project_related) > 0,
        }


class GPUMemoryMonitor:
    """GPU 内存监控器"""

    def __init__(self):
        self.available = False
        self.initial_memory = 0
        try:
            import torch
            self.available = torch.cuda.is_available()
            if self.available:
                self.torch = torch
        except ImportError:
            pass

    def get_gpu_memory(self) -> Dict:
        """获取 GPU 内存使用情况"""
        if not self.available:
            return {'available': False}

        try:
            allocated = self.torch.cuda.memory_allocated() / 1024 / 1024
            reserved = self.torch.cuda.memory_reserved() / 1024 / 1024
            max_allocated = self.torch.cuda.max_memory_allocated() / 1024 / 1024

            return {
                'available': True,
                'allocated_mb': allocated,
                'reserved_mb': reserved,
                'max_allocated_mb': max_allocated,
            }
        except Exception as e:
            return {'available': True, 'error': str(e)}

    def start(self):
        """记录初始状态"""
        info = self.get_gpu_memory()
        if info.get('available'):
            self.initial_memory = info.get('allocated_mb', 0)
            print(f"[GPU] 初始 GPU 内存: {self.initial_memory:.2f} MB")

    def check_leaks(self) -> Dict:
        """检查 GPU 内存泄漏"""
        info = self.get_gpu_memory()
        if not info.get('available'):
            return {'available': False, 'message': 'GPU 不可用或 PyTorch 未安装'}

        current = info.get('allocated_mb', 0)
        diff = current - self.initial_memory

        return {
            'available': True,
            'initial_mb': self.initial_memory,
            'current_mb': current,
            'diff_mb': diff,
            'max_mb': info.get('max_allocated_mb', 0),
            'potential_leak': diff > 500,  # 超过500MB视为可疑
        }


class APITester:
    """API 测试器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def check_health(self) -> bool:
        """检查服务是否可用"""
        try:
            resp = requests.get(f"{self.base_url}/api/tasks/", timeout=5)
            return resp.status_code == 200
        except:
            return False

    def get_tasks(self) -> List[Dict]:
        """获取任务列表"""
        try:
            resp = requests.get(f"{self.base_url}/api/tasks/", timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return []


def run_memory_leak_test():
    """运行内存泄漏测试"""
    print("=" * 60)
    print("内存泄漏检测测试")
    print("=" * 60)
    print()

    # 初始化监控器
    memory_monitor = MemoryMonitor()
    temp_monitor = TempFileMonitor()
    gpu_monitor = GPUMemoryMonitor()
    api_tester = APITester()

    # 检查后端服务
    if not api_tester.check_health():
        print("[错误] 后端服务未运行，请先启动后端服务")
        print("  命令: cd backend && python main.py")
        return False

    print("[OK] 后端服务正在运行")

    # 记录初始状态
    temp_monitor.start()
    gpu_monitor.start()

    # 查找后端进程并获取初始内存
    proc = memory_monitor.find_backend_process()
    if proc:
        initial_mem = memory_monitor.get_memory_info(proc)
        print(f"[内存] 初始 RSS 内存: {initial_mem.get('rss_mb', 0):.2f} MB")
    else:
        print("[警告] 未找到后端进程")

    print()
    print("-" * 60)
    print("开始监控... (请在此期间执行一些任务操作)")
    print("按 Ctrl+C 停止监控并查看结果")
    print("-" * 60)
    print()

    # 开始后台监控
    memory_monitor.start_monitoring(interval=2.0)

    try:
        # 持续监控，每10秒输出一次状态
        while True:
            time.sleep(10)
            if memory_monitor.samples:
                latest = memory_monitor.samples[-1]
                print(f"[监控] RSS: {latest['rss_mb']:.2f} MB, "
                      f"采样数: {len(memory_monitor.samples)}")
    except KeyboardInterrupt:
        print("\n")
        print("=" * 60)
        print("监控结束，分析结果...")
        print("=" * 60)

    # 停止监控
    memory_monitor.stop_monitoring()

    # 分析结果
    print()
    print("【内存分析】")
    mem_analysis = memory_monitor.analyze_samples()
    if 'error' not in mem_analysis:
        print(f"  采样数: {mem_analysis['sample_count']}")
        print(f"  起始内存: {mem_analysis['rss_start_mb']:.2f} MB")
        print(f"  结束内存: {mem_analysis['rss_end_mb']:.2f} MB")
        print(f"  最小内存: {mem_analysis['rss_min_mb']:.2f} MB")
        print(f"  最大内存: {mem_analysis['rss_max_mb']:.2f} MB")
        print(f"  内存变化: {mem_analysis['rss_diff_mb']:+.2f} MB")
        if mem_analysis['potential_leak']:
            print(f"  [警告] 内存增长超过100MB，可能存在泄漏!")
        else:
            print(f"  [OK] 内存使用正常")

    print()
    print("【临时文件分析】")
    temp_analysis = temp_monitor.check_leaks()
    print(f"  初始文件数: {temp_analysis['initial_count']}")
    print(f"  当前文件数: {temp_analysis['current_count']}")
    print(f"  新增文件数: {temp_analysis['new_files_count']}")
    print(f"  项目相关新增: {temp_analysis['project_related_count']}")
    if temp_analysis['potential_leak']:
        print(f"  [警告] 发现可能泄漏的临时文件:")
        for f in temp_analysis['project_related_files'][:5]:
            print(f"    - {f}")
    else:
        print(f"  [OK] 无项目相关临时文件泄漏")

    print()
    print("【GPU内存分析】")
    gpu_analysis = gpu_monitor.check_leaks()
    if not gpu_analysis.get('available'):
        print(f"  GPU 不可用")
    else:
        print(f"  初始: {gpu_analysis['initial_mb']:.2f} MB")
        print(f"  当前: {gpu_analysis['current_mb']:.2f} MB")
        print(f"  最大: {gpu_analysis['max_mb']:.2f} MB")
        print(f"  变化: {gpu_analysis['diff_mb']:+.2f} MB")
        if gpu_analysis['potential_leak']:
            print(f"  [警告] GPU内存增长超过500MB，可能存在泄漏!")
        else:
            print(f"  [OK] GPU内存使用正常")

    print()
    print("=" * 60)

    # 返回是否有潜在问题
    has_issues = (
        mem_analysis.get('potential_leak', False) or
        temp_analysis.get('potential_leak', False) or
        gpu_analysis.get('potential_leak', False)
    )

    if has_issues:
        print("检测到潜在内存问题，建议进一步排查")
    else:
        print("未检测到明显的内存泄漏问题")

    print("=" * 60)

    return not has_issues


def run_single_task_memory_test(task_id: str, language: str = "English"):
    """
    针对单个任务运行内存测试

    此函数会监控执行特定任务时的内存变化
    """
    print("=" * 60)
    print(f"单任务内存测试: {task_id} -> {language}")
    print("=" * 60)

    memory_monitor = MemoryMonitor()
    api_tester = APITester()

    if not api_tester.check_health():
        print("[错误] 后端服务未运行")
        return

    proc = memory_monitor.find_backend_process()
    if not proc:
        print("[错误] 未找到后端进程")
        return

    # 记录操作前的内存
    before = memory_monitor.get_memory_info(proc)
    print(f"[操作前] RSS: {before['rss_mb']:.2f} MB")

    # 这里可以添加触发特定任务的逻辑
    # 例如调用翻译API、语音克隆API等

    print("[提示] 请手动触发任务操作，然后按 Enter 继续...")
    input()

    # 等待任务完成
    print("[等待] 等待任务完成...")
    time.sleep(5)

    # 记录操作后的内存
    after = memory_monitor.get_memory_info(proc)
    print(f"[操作后] RSS: {after['rss_mb']:.2f} MB")
    print(f"[变化] {after['rss_mb'] - before['rss_mb']:+.2f} MB")

    # 等待GC
    print("[等待] 等待垃圾回收 (30秒)...")
    time.sleep(30)

    # 再次检查
    final = memory_monitor.get_memory_info(proc)
    print(f"[GC后] RSS: {final['rss_mb']:.2f} MB")
    print(f"[总变化] {final['rss_mb'] - before['rss_mb']:+.2f} MB")

    if final['rss_mb'] - before['rss_mb'] > 50:
        print("[警告] 任务执行后内存未完全释放")
    else:
        print("[OK] 内存使用正常")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="内存泄漏检测测试")
    parser.add_argument('--task', help="指定任务ID进行单任务测试")
    parser.add_argument('--language', default="English", help="目标语言")

    args = parser.parse_args()

    if args.task:
        run_single_task_memory_test(args.task, args.language)
    else:
        run_memory_leak_test()
