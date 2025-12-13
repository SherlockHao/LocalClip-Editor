"""
检查 worker 进程状态的调试脚本
"""
import psutil
import os
import glob

# 检查进程
worker_pids = [22348, 18996]

print("=" * 80)
print("检查 Worker 进程状态")
print("=" * 80)

for pid in worker_pids:
    try:
        proc = psutil.Process(pid)
        print(f"\nPID {pid}:")
        print(f"  状态: {proc.status()}")
        print(f"  CPU使用率: {proc.cpu_percent(interval=0.5):.1f}%")
        print(f"  内存: {proc.memory_info().rss / 1024 / 1024:.1f} MB")
        print(f"  命令行: {' '.join(proc.cmdline())}")

        # 检查打开的文件
        try:
            open_files = [f.path for f in proc.open_files() if 'segment_' in f.path or '.json' in f.path]
            if open_files:
                print(f"  打开的文件: {open_files[:3]}")
        except:
            pass

    except psutil.NoSuchProcess:
        print(f"\nPID {pid}: 进程已结束")
    except Exception as e:
        print(f"\nPID {pid}: 检查失败 - {e}")

# 检查任务文件
print("\n" + "=" * 80)
print("检查临时任务文件")
print("=" * 80)

temp_files = glob.glob(r"C:\Users\7\AppData\Local\Temp\speaker_*.json")
print(f"\n找到 {len(temp_files)} 个任务文件:")
for f in temp_files[:5]:
    size = os.path.getsize(f)
    print(f"  {os.path.basename(f)} - {size} bytes")

# 检查输出目录
print("\n" + "=" * 80)
print("检查输出文件")
print("=" * 80)

audio_dirs = glob.glob(r"c:\workspace\ai_editing\workspace\LocalClip-Editor\audio_segments\*\cloned")
for dir_path in audio_dirs[:2]:
    print(f"\n目录: {dir_path}")
    wav_files = glob.glob(os.path.join(dir_path, "*.wav"))
    print(f"  WAV 文件数量: {len(wav_files)}")
    if wav_files:
        for f in wav_files[:3]:
            size = os.path.getsize(f)
            print(f"    {os.path.basename(f)} - {size / 1024:.1f} KB")
