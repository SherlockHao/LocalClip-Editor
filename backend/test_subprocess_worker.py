"""
测试 subprocess worker 脚本
"""
import json
import tempfile
import os

# 创建一个测试任务配置
test_config = {
    "speaker_id": 0,
    "tasks": [
        {
            "segment_index": 0,
            "text": "这是一个测试文本。"
        }
    ],
    "npy_file": "test_codes.npy",  # 这个文件需要存在
    "reference": {
        "reference_text": "参考文本",
        "reference_audio": "test.wav"
    },
    "output_dir": "test_output",
    "checkpoint_path": r"C:\workspace\ai_editing\fish-speech-win\checkpoints\openaudio-s1-mini",
    "batch_size": 5,
    "fish_speech_dir": r"C:\workspace\ai_editing\fish-speech-win"
}

# 写入临时文件
fd, task_file = tempfile.mkstemp(suffix='.json', prefix='test_task_')
with os.fdopen(fd, 'w', encoding='utf-8') as f:
    json.dump(test_config, f, ensure_ascii=False, indent=2)

print(f"Created test task file: {task_file}")
print(f"\nTo test the worker, run:")
print(f'"{os.environ.get("FISH_SPEECH_PYTHON", "python")}" fish_subprocess_worker.py "{task_file}"')

# 清理
input("\nPress Enter to delete the task file...")
os.remove(task_file)
print("Task file deleted.")
