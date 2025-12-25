"""
测试子进程实时输出捕获
验证 main.py 中的实时输出逻辑
"""
import subprocess
import sys
import os
import io

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("\n" + "="*70)
print("测试子进程实时输出")
print("="*70 + "\n")

# 获取测试脚本路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
test_script = os.path.join(backend_dir, "test_realtime_output.py")

print(f"测试脚本: {test_script}\n")

print("="*70)
print("开始实时输出（应该逐行出现，而不是最后一次性输出）")
print("="*70 + "\n")

# 使用与 main.py 相同的方式启动子进程
process = subprocess.Popen(
    [sys.executable, test_script],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
    text=True,  # 文本模式
    encoding='utf-8',
    errors='replace',  # 忽略解码错误
    bufsize=1,  # 行缓冲
    universal_newlines=True
)

# 实时读取输出
stdout_lines = []

try:
    import time
    start_time = time.time()

    while True:
        # 读取一行
        line = process.stdout.readline()

        if line:
            # 实时打印（带时间戳）
            elapsed = time.time() - start_time
            print(f"[{elapsed:6.2f}s] {line}", end='', flush=True)
            stdout_lines.append(line)
        else:
            # 检查进程是否结束
            if process.poll() is not None:
                break
            time.sleep(0.1)

    # 读取剩余输出
    remaining = process.stdout.read()
    if remaining:
        elapsed = time.time() - start_time
        print(f"[{elapsed:6.2f}s] {remaining}", end='', flush=True)
        stdout_lines.append(remaining)

    returncode = process.wait()

except Exception as e:
    process.kill()
    print(f"\n⚠️  出错: {e}")
    returncode = -1

print("\n" + "="*70)
print(f"子进程结束，返回码: {returncode}")
print("="*70)

if returncode == 0:
    print("\n✅ 实时输出测试成功！")
    print("\n说明:")
    print("  - 如果你看到输出是逐行出现的（带时间戳），说明实时输出工作正常")
    print("  - 如果输出是最后一次性出现的，说明输出被缓冲了")
else:
    print("\n❌ 子进程执行失败")

print("\n总共捕获 {} 行输出".format(len(stdout_lines)))
