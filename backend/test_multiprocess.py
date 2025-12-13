"""
测试多进程语音克隆功能
"""
import os
import sys

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from fish_simple_cloner import SimpleFishCloner

def test_multiprocess():
    """测试多进程模式"""

    print("=" * 70)
    print("多进程语音克隆测试")
    print("=" * 70)

    # 创建克隆器（启用多进程）
    cloner = SimpleFishCloner(use_multiprocess=True)

    # 模拟说话人数据
    speaker_references = {
        0: {
            "reference_audio": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\audio_segments\8431222a-f812-40bf-8c78-27dad65311f2\references\speaker_0_reference.wav",
            "reference_text": "我是你大哥 是个小包工头",
            "speaker_name": "说话人0",
            "gender": "unknown"
        },
        1: {
            "reference_audio": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\audio_segments\8431222a-f812-40bf-8c78-27dad65311f2\references\speaker_1_reference.wav",
            "reference_text": "对啊 除了你大哥呢",
            "speaker_name": "说话人1",
            "gender": "unknown"
        }
    }

    # 测试编码
    print("\n步骤 1: 编码说话人参考音频...")
    output_dir = r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_multiprocess_output"
    os.makedirs(output_dir, exist_ok=True)

    speaker_npy_files = cloner.batch_encode_speakers(
        speaker_references,
        os.path.join(output_dir, "encoded")
    )

    print(f"编码完成！生成 {len(speaker_npy_files)} 个 npy 文件")
    for speaker_id, npy_file in speaker_npy_files.items():
        print(f"  说话人 {speaker_id}: {npy_file}")

    # 测试生成（每个说话人2个文本，测试并行）
    print("\n步骤 2: 批量生成音频（多进程模式）...")
    tasks = [
        {"speaker_id": 0, "target_text": "Hello, this is a test.", "segment_index": 0},
        {"speaker_id": 0, "target_text": "Another test for speaker 0.", "segment_index": 1},
        {"speaker_id": 1, "target_text": "Test for speaker 1.", "segment_index": 2},
        {"speaker_id": 1, "target_text": "Second test for speaker 1.", "segment_index": 3},
    ]

    result = cloner.batch_generate_audio(
        tasks,
        speaker_npy_files,
        speaker_references,
        os.path.join(output_dir, "cloned")
    )

    print(f"\n生成完成！生成 {len(result)} 个音频文件")
    for segment_index, audio_file in result.items():
        print(f"  片段 {segment_index}: {audio_file}")

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


def test_singleprocess():
    """测试单进程模式（对比）"""

    print("=" * 70)
    print("单进程语音克隆测试（对比）")
    print("=" * 70)

    # 创建克隆器（单进程）
    cloner = SimpleFishCloner(use_multiprocess=False)

    # 模拟说话人数据
    speaker_references = {
        0: {
            "reference_audio": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\audio_segments\8431222a-f812-40bf-8c78-27dad65311f2\references\speaker_0_reference.wav",
            "reference_text": "我是你大哥 是个小包工头",
            "speaker_name": "说话人0",
            "gender": "unknown"
        },
        1: {
            "reference_audio": r"C:\workspace\ai_editing\workspace\LocalClip-Editor\audio_segments\8431222a-f812-40bf-8c78-27dad65311f2\references\speaker_1_reference.wav",
            "reference_text": "对啊 除了你大哥呢",
            "speaker_name": "说话人1",
            "gender": "unknown"
        }
    }

    # 测试编码
    print("\n步骤 1: 编码说话人参考音频...")
    output_dir = r"C:\workspace\ai_editing\workspace\LocalClip-Editor\backend\test_singleprocess_output"
    os.makedirs(output_dir, exist_ok=True)

    speaker_npy_files = cloner.batch_encode_speakers(
        speaker_references,
        os.path.join(output_dir, "encoded")
    )

    print(f"编码完成！生成 {len(speaker_npy_files)} 个 npy 文件")

    # 测试生成
    print("\n步骤 2: 批量生成音频（单进程模式）...")
    tasks = [
        {"speaker_id": 0, "target_text": "Hello, this is a test.", "segment_index": 0},
        {"speaker_id": 0, "target_text": "Another test for speaker 0.", "segment_index": 1},
        {"speaker_id": 1, "target_text": "Test for speaker 1.", "segment_index": 2},
        {"speaker_id": 1, "target_text": "Second test for speaker 1.", "segment_index": 3},
    ]

    result = cloner.batch_generate_audio(
        tasks,
        speaker_npy_files,
        speaker_references,
        os.path.join(output_dir, "cloned")
    )

    print(f"\n生成完成！生成 {len(result)} 个音频文件")

    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    import time

    # 测试单进程
    print("\n\n🔵 测试 1: 单进程模式")
    start_time = time.time()
    try:
        test_singleprocess()
    except Exception as e:
        print(f"❌ 单进程测试失败: {e}")
        import traceback
        traceback.print_exc()
    single_time = time.time() - start_time
    print(f"\n单进程耗时: {single_time:.2f} 秒")

    # 测试多进程
    print("\n\n🟢 测试 2: 多进程模式")
    start_time = time.time()
    try:
        test_multiprocess()
    except Exception as e:
        print(f"❌ 多进程测试失败: {e}")
        import traceback
        traceback.print_exc()
    multi_time = time.time() - start_time
    print(f"\n多进程耗时: {multi_time:.2f} 秒")

    # 对比
    if single_time > 0 and multi_time > 0:
        speedup = single_time / multi_time
        print(f"\n" + "=" * 70)
        print(f"性能对比:")
        print(f"  单进程: {single_time:.2f} 秒")
        print(f"  多进程: {multi_time:.2f} 秒")
        print(f"  加速比: {speedup:.2f}x")
        print("=" * 70)
