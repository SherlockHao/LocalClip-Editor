"""
直接测试 worker 脚本，查看实时输出
"""
import subprocess
import sys

# 直接运行一个 worker
task_file = r"C:\Users\7\AppData\Local\Temp\speaker_3_jqjytfg4.json"
fish_python = r"C:\Users\7\miniconda3\envs\fish-speech\python.exe"
worker_script = r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\fish_subprocess_worker.py"

print(f"运行命令: {fish_python} {worker_script} {task_file}")
print("=" * 80)

# 直接运行，输出到控制台
proc = subprocess.run(
    [fish_python, worker_script, task_file],
    cwd=r"C:\workspace\ai_editing\fish-speech-win",
    capture_output=False,  # 直接输出到控制台
    text=True
)

print("=" * 80)
print(f"返回码: {proc.returncode}")
