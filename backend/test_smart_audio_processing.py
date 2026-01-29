"""
测试智能音频处理功能
验证长音频的智能切分、静音去除和语音段检测
"""
import sys
import os
import io
import numpy as np
import soundfile as sf
from pathlib import Path

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 确保可以导入模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "speaker_diarization_processing"))
sys.path.insert(0, str(project_root / "backend"))

from audio_extraction import AudioExtractor


def create_test_audio(duration: float, speech_segments: list, sample_rate: int = 16000) -> np.ndarray:
    """
    创建测试音频

    Args:
        duration: 总时长（秒）
        speech_segments: 语音段列表 [(start, end), ...]
        sample_rate: 采样率

    Returns:
        音频数据
    """
    total_samples = int(duration * sample_rate)
    audio = np.zeros(total_samples, dtype=np.float32)

    # 在语音段添加正弦波信号
    for start, end in speech_segments:
        start_sample = int(start * sample_rate)
        end_sample = int(end * sample_rate)
        t = np.linspace(0, end - start, end_sample - start_sample)
        # 生成 440Hz 的正弦波（A音）
        signal = 0.5 * np.sin(2 * np.pi * 440 * t)
        audio[start_sample:end_sample] = signal

    return audio


def test_speech_detection():
    """测试语音段检测"""
    print("=" * 60)
    print("测试 1: 语音段检测")
    print("=" * 60)

    extractor = AudioExtractor()

    # 创建测试音频：10秒，有3个语音段
    speech_segments = [
        (0.5, 2.0),    # 第1个语音段
        (4.0, 6.5),    # 第2个语音段（中间有2秒静音）
        (7.0, 9.0),    # 第3个语音段（中间有0.5秒静音）
    ]
    audio = create_test_audio(10.0, speech_segments)

    # 检测语音段
    detected = extractor._detect_speech_segments(audio, 16000)

    print(f"预期语音段数: {len(speech_segments)}")
    print(f"检测到语音段数: {len(detected)}")
    print(f"\n检测到的语音段:")
    for seg in detected:
        print(f"  {seg['start']:.2f}s - {seg['end']:.2f}s")

    if len(detected) >= 2:
        print("\n[OK] 语音段检测基本正常")
        return True
    else:
        print("\n[FAIL] 语音段检测失败")
        return False


def test_silence_removal():
    """测试长静音去除"""
    print("\n" + "=" * 60)
    print("测试 2: 长静音去除（保留左侧0.5秒）")
    print("=" * 60)

    extractor = AudioExtractor()

    # 创建测试音频：有一个3秒的长静音
    speech_segments = [
        (0.5, 2.0),    # 第1个语音段
        (5.0, 7.0),    # 第2个语音段（中间有3秒静音）
    ]
    audio = create_test_audio(10.0, speech_segments)
    original_duration = len(audio) / 16000

    print(f"原始音频时长: {original_duration:.2f}s")
    print(f"预期去除静音: 3.0s - 0.5s = 2.5s")

    # 去除长静音
    processed, new_segments = extractor._remove_long_silences(audio, 16000, min_silence_duration=2.0, keep_left=0.5)
    processed_duration = len(processed) / 16000

    print(f"处理后音频时长: {processed_duration:.2f}s")
    print(f"实际减少时长: {original_duration - processed_duration:.2f}s")

    # 预期时长 = 原始时长 - (长静音 - 保留的0.5秒)
    # 10.0s - (3.0s - 0.5s) = 7.5s
    expected_duration = 7.5
    if abs(processed_duration - expected_duration) < 0.5:
        print(f"\n[OK] 长静音去除正确（预期约 {expected_duration:.1f}s）")
        return True
    else:
        print(f"\n[FAIL] 长静音去除异常（预期约 {expected_duration:.1f}s）")
        return False


def test_split_point_finding():
    """测试切分点查找"""
    print("\n" + "=" * 60)
    print("测试 3: 智能切分点查找")
    print("=" * 60)

    extractor = AudioExtractor()

    # 创建测试音频：40秒，有多个语音段和静音段
    speech_segments = [
        (0.5, 10.0),   # 第1个语音段
        (12.0, 20.0),  # 第2个语音段（第11秒有静音）
        (22.0, 28.0),  # 第3个语音段（第21秒有静音）
        (30.0, 39.0),  # 第4个语音段（第29秒有静音）
    ]
    audio = create_test_audio(40.0, speech_segments)

    print(f"音频总时长: 40.0s")
    print(f"需要在 30s 内找到切分点")

    # 查找切分点
    split_point = extractor._find_split_point(audio, 16000, max_duration=30.0)

    if split_point is not None:
        print(f"\n找到切分点: {split_point:.2f}s")
        if split_point <= 30.0:
            print("[OK] 切分点在30秒以内")
            return True
        else:
            print("[FAIL] 切分点超过30秒")
            return False
    else:
        print("\n未找到合适的切分点（将强制硬切）")
        print("[OK] 返回None表示需要硬切")
        return True


def test_complete_workflow():
    """测试完整工作流程"""
    print("\n" + "=" * 60)
    print("测试 4: 完整智能处理流程")
    print("=" * 60)

    extractor = AudioExtractor(cache_dir="test_audio_cache")

    # 创建测试音频文件：50秒，包含长静音和多个语音段
    speech_segments = [
        (0.5, 10.0),   # 10秒语音
        (13.0, 20.0),  # 7秒语音（前面3秒静音）
        (22.0, 35.0),  # 13秒语音（前面2秒静音）
        (38.0, 49.0),  # 11秒语音（前面3秒静音）
    ]
    audio = create_test_audio(50.0, speech_segments)

    # 保存测试文件
    test_file = Path("test_audio_cache") / "test_long_audio.wav"
    test_file.parent.mkdir(exist_ok=True)
    sf.write(str(test_file), audio, 16000)

    original_duration = len(audio) / 16000
    print(f"原始音频: {original_duration:.2f}s")

    # 应用智能处理
    processed_file = extractor._process_long_audio(test_file, max_duration=30.0)

    # 检查处理结果
    processed_audio, sr = sf.read(str(processed_file))
    processed_duration = len(processed_audio) / sr

    print(f"\n处理结果:")
    print(f"  - 原始时长: {original_duration:.2f}s")
    print(f"  - 处理后时长: {processed_duration:.2f}s")
    print(f"  - 是否在30秒内: {'是' if processed_duration <= 30.0 else '否'}")

    # 清理测试文件
    try:
        test_file.unlink()
        test_file.parent.rmdir()
    except:
        pass

    if processed_duration <= 30.0:
        print("\n[OK] 完整流程处理成功")
        return True
    else:
        print("\n[FAIL] 处理后仍超过30秒")
        return False


def main():
    """运行所有测试"""
    print("开始测试智能音频处理功能\n")

    results = []

    # 测试 1: 语音段检测
    results.append(("语音段检测", test_speech_detection()))

    # 测试 2: 长静音去除
    results.append(("长静音去除", test_silence_removal()))

    # 测试 3: 切分点查找
    results.append(("切分点查找", test_split_point_finding()))

    # 测试 4: 完整流程
    results.append(("完整流程", test_complete_workflow()))

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
