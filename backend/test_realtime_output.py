"""
测试实时输出功能
模拟批量翻译的实时日志输出
"""
import sys
import time

print("[测试] 开始模拟批量翻译...")
sys.stdout.flush()

time.sleep(1)

print("[GPU检测] 检测GPU显存...")
sys.stdout.flush()

time.sleep(0.5)

print("[GPU检测] 可用显存: 12.00 GB")
sys.stdout.flush()

time.sleep(0.5)

print("[模型选择] 选择模型...")
sys.stdout.flush()

time.sleep(1)

print("[模型选择] ✓ 选择 Qwen3-4B-FP8")
sys.stdout.flush()

time.sleep(1)

print("[PID 12345] Loading model...")
sys.stdout.flush()

time.sleep(2)

print("[PID 12345] Model loaded on device: cuda:0")
sys.stdout.flush()

time.sleep(1)

print("[批量翻译] 开始批量翻译")
print("  任务数量: 3")
print("  进程数量: 1")
sys.stdout.flush()

time.sleep(1)

# 模拟翻译3句话
tasks = [
    ("test-1", "你好", "안녕"),
    ("test-2", "不好", "안 좋아"),
    ("test-3", "大哥", "큰오빠"),
]

for i, (task_id, source, translation) in enumerate(tasks, 1):
    print(f"[Worker 1] 开始处理任务 {task_id}: {source}...")
    sys.stdout.flush()
    time.sleep(1.5)

    print(f"[Worker 1] 完成任务 {task_id}，耗时 1.50秒")
    sys.stdout.flush()

    print(f"[{i}/3] {task_id}: {source} -> {translation}")
    sys.stdout.flush()

    time.sleep(0.5)

print("\n[批量翻译] 全部完成！共处理 3 个任务")
sys.stdout.flush()

time.sleep(0.5)

# 输出JSON结果
import json
results = [
    {
        "task_id": task_id,
        "source": source,
        "translation": translation,
        "success": True
    }
    for task_id, source, translation in tasks
]

print("\n" + json.dumps(results, ensure_ascii=False))
sys.stdout.flush()

print("\n[测试] 模拟完成")
