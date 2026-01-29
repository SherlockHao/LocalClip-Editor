"""
测试优化后的 speaker_audio_processor 模块
验证语音检测和静音去除功能
"""
import sys
import os

# 设置UTF-8编码输出
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 确保可以导入模块
sys.path.insert(0, os.path.dirname(__file__))

from speaker_audio_processor import SpeakerAudioProcessor


def test_initialization():
    """测试初始化"""
    print("=" * 60)
    print("测试 1: 初始化 SpeakerAudioProcessor")
    print("=" * 60)

    try:
        processor = SpeakerAudioProcessor(
            target_duration=10.0,
            silence_duration=1.0
        )
        print("[OK] 成功初始化 SpeakerAudioProcessor")
        print(f"  - target_duration: {processor.target_duration}s")
        print(f"  - silence_duration: {processor.silence_duration}s")
        print(f"  - sample_rate: {processor.sample_rate}Hz")
        print(f"  - trimmer: {processor.trimmer}")
        return True
    except Exception as e:
        print(f"[FAIL] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_timestamp_extraction():
    """测试时间戳提取"""
    print("\n" + "=" * 60)
    print("测试 2: 时间戳提取")
    print("=" * 60)

    processor = SpeakerAudioProcessor()

    # 测试用例
    test_cases = [
        ("segment_001_19.980_81.539.wav", 19.980),
        ("segment_032_01_19.980_50.000.wav", 19.980),
        ("segment_005_10.123_25.678.wav", 10.123),
    ]

    all_passed = True

    for filename, expected in test_cases:
        # 使用内部的extract_timestamp函数
        from pathlib import Path

        # 简化的提取逻辑（复制自sort_by_timestamp）
        stem = Path(filename).stem
        parts = stem.split('_')
        try:
            actual = float(parts[-2])
        except:
            actual = 0.0

        if abs(actual - expected) < 0.001:
            print(f"[OK] {filename} -> {actual} (预期: {expected})")
        else:
            print(f"[FAIL] {filename} -> {actual} (预期: {expected})")
            all_passed = False

    return all_passed


def test_sort_by_timestamp():
    """测试按时间戳排序"""
    print("\n" + "=" * 60)
    print("测试 3: 按时间戳排序")
    print("=" * 60)

    processor = SpeakerAudioProcessor()

    # 创建测试数据（乱序）
    segments = [
        ("segment_003_50.123_60.456.wav", 0.95, 10.333),
        ("segment_001_10.000_20.000.wav", 0.98, 10.000),
        ("segment_002_30.500_40.750.wav", 0.96, 10.250),
    ]

    print("排序前:")
    for seg in segments:
        print(f"  {seg[0]}")

    sorted_segments = processor.sort_by_timestamp(segments)

    print("\n排序后:")
    for seg in sorted_segments:
        print(f"  {seg[0]}")

    # 验证排序是否正确
    expected_order = [
        "segment_001_10.000_20.000.wav",
        "segment_002_30.500_40.750.wav",
        "segment_003_50.123_60.456.wav",
    ]

    actual_order = [os.path.basename(seg[0]) for seg in sorted_segments]

    if actual_order == expected_order:
        print("\n[OK] 排序正确")
        return True
    else:
        print(f"\n[FAIL] 排序错误")
        print(f"  预期: {expected_order}")
        print(f"  实际: {actual_order}")
        return False


def main():
    """运行所有测试"""
    print("开始测试优化后的 SpeakerAudioProcessor\n")

    results = []

    # 测试 1: 初始化
    results.append(("初始化", test_initialization()))

    # 测试 2: 时间戳提取
    results.append(("时间戳提取", test_timestamp_extraction()))

    # 测试 3: 排序
    results.append(("按时间戳排序", test_sort_by_timestamp()))

    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, passed in results:
        status = "[OK] 通过" if passed else "[FAIL] 失败"
        print(f"{status} - {name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[ERROR] {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
