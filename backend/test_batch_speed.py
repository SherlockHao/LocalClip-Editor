"""
测试批量生成速度
验证是否达到 14+ tokens/sec
"""
import os
import json
import tempfile

# 创建测试配置
test_config = {
    "fish_speech_dir": r"C:\workspace\ai_editing\fish-speech-win",
    "checkpoint_dir": r"C:\workspace\ai_editing\fish-speech-win\checkpoints\openaudio-s1-mini",
    "tasks": [
        {
            "speaker_id": 0,
            "segment_index": 0,
            "target_text": "Hello, this is the first sentence.",
            "npy_file": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_output\speaker_0_codes.npy",
            "reference_text": "对啊 除了你大哥呢 你还有4个哥哥 总共5个哥哥 吃饭去 欣欣 你是不是 不喜欢这些菜啊 吃吧",
            "output_file": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_output\test_0.wav"
        },
        {
            "speaker_id": 0,
            "segment_index": 1,
            "target_text": "As the vocoder model has been changed, you need more room than before.",
            "npy_file": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_output\speaker_0_codes.npy",
            "reference_text": "对啊 除了你大哥呢 你还有4个哥哥 总共5个哥哥 吃饭去 欣欣 你是不是 不喜欢这些菜啊 吃吧",
            "output_file": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_output\test_1.wav"
        },
        {
            "speaker_id": 0,
            "segment_index": 2,
            "target_text": "Batch inference is very efficient and suitable for long text generation.",
            "npy_file": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_output\speaker_0_codes.npy",
            "reference_text": "对啊 除了你大哥呢 你还有4个哥哥 总共5个哥哥 吃饭去 欣欣 你是不是 不喜欢这些菜啊 吃吧",
            "output_file": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_output\test_2.wav"
        }
    ]
}

# 写入临时配置文件
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
    json.dump(test_config, f, ensure_ascii=False, indent=2)
    config_file = f.name

print(f"Config file: {config_file}")
print(f"\nRun this command to test:")
print(f'"C:\\Users\\7\\miniconda3\\envs\\fish-speech\\python.exe" fish_batch_generate.py "{config_file}"')
print(f"\n查看输出中的 'tokens/sec' 指标，应该达到 10+ tokens/sec")
