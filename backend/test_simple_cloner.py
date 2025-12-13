"""
测试简单批量克隆器
"""
import os
import tempfile
from fish_simple_cloner import SimpleFishCloner

# 测试配置
test_speaker_references = {
    0: {
        "reference_audio": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\audio_segments\bde6f37d-a683-4f62-bd1a-995210fd4ad4\references\speaker_0_reference.wav",
        "reference_text": "对啊 除了你大哥呢 你还有4个哥哥 总共5个哥哥 吃饭去 欣欣 你是不是 不喜欢这些菜啊 吃吧"
    }
}

test_tasks = [
    {
        "speaker_id": 0,
        "target_text": "Hello, this is a test.",
        "segment_index": 0
    },
    {
        "speaker_id": 0,
        "target_text": "Another test sentence.",
        "segment_index": 1
    }
]

print("=" * 80)
print("测试简单批量克隆器")
print("=" * 80)

# 创建临时输出目录
output_dir = tempfile.mkdtemp(prefix="test_cloner_")
print(f"\n输出目录: {output_dir}")

try:
    # 初始化克隆器
    cloner = SimpleFishCloner()

    # 测试编码
    print("\n[1/2] Test encoding...")
    speaker_npy_files = cloner.batch_encode_speakers(
        test_speaker_references,
        output_dir
    )
    print(f"[OK] Encoding success: {speaker_npy_files}")

    # 测试生成
    print("\n[2/2] Test generation...")
    generated_files = cloner.batch_generate_audio(
        test_tasks,
        speaker_npy_files,
        test_speaker_references,
        output_dir
    )
    print(f"[OK] Generation success: {generated_files}")

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)

    print(f"\n生成的文件:")
    for key, path in generated_files.items():
        if os.path.exists(path):
            size = os.path.getsize(path) / 1024
            print(f"  {key}: {path} ({size:.1f} KB)")
        else:
            print(f"  {key}: 文件不存在！")

except Exception as e:
    print(f"\n[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
