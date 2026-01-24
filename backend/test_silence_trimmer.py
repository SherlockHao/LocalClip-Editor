"""
音频静音切割功能测试脚本
"""
import numpy as np
import soundfile as sf
from audio_silence_trimmer import AudioSilenceTrimmer
import os
import tempfile


def create_test_audio(
    speech_segments,
    silence_segments,
    sr=16000,
    speech_amplitude=0.5,
    silence_amplitude=0.01
):
    """
    创建测试音频

    Args:
        speech_segments: 语音段列表 [(start, end), ...]，单位秒
        silence_segments: 静音段列表 [(start, end), ...]，单位秒
        sr: 采样率
        speech_amplitude: 语音段振幅
        silence_amplitude: 静音段振幅

    Returns:
        音频数据
    """
    # 计算总时长
    total_duration = max(
        max([end for _, end in speech_segments]),
        max([end for _, end in silence_segments])
    )

    # 初始化音频数组（静音）
    audio = np.ones(int(total_duration * sr)) * silence_amplitude

    # 添加语音段（高振幅）
    for start, end in speech_segments:
        start_sample = int(start * sr)
        end_sample = int(end * sr)
        # 生成简单的正弦波模拟语音
        t = np.linspace(0, end - start, end_sample - start_sample)
        audio[start_sample:end_sample] = speech_amplitude * np.sin(2 * np.pi * 440 * t)

    return audio.astype(np.float32)


def test_case_1_leading_silence():
    """
    测试用例1: 开头有长静音（2秒）
    预期：保留最后0.5秒
    """
    print("\n=== 测试用例1: 开头有2秒静音 ===")

    # 创建测试音频：2秒静音 + 3秒语音 + 1秒静音
    speech_segments = [(2.0, 5.0)]
    silence_segments = [(0.0, 2.0), (5.0, 6.0)]

    audio = create_test_audio(speech_segments, silence_segments)
    sr = 16000

    print(f"原始音频时长: {len(audio) / sr:.2f}s")

    # 初始化trimmer
    trimmer = AudioSilenceTrimmer()

    # 检测语音段
    detected_segments = trimmer.detect_speech_segments(audio, sr)
    print(f"检测到 {len(detected_segments)} 个语音段:")
    for seg in detected_segments:
        print(f"  {seg['start']:.2f}s - {seg['end']:.2f}s")

    # 切割静音
    trimmed_audio = trimmer.trim_silence(audio, sr, detected_segments)
    trimmed_duration = len(trimmed_audio) / sr

    print(f"切割后时长: {trimmed_duration:.2f}s")

    # 预期：应该去掉前1.5秒，保留最后0.5秒静音 + 3秒语音 + 1秒静音 = 4.5秒
    expected_duration = 0.5 + 3.0 + 1.0
    assert abs(trimmed_duration - expected_duration) < 0.1, \
        f"时长不符预期: 实际{trimmed_duration:.2f}s, 预期{expected_duration:.2f}s"

    print("✓ 测试通过")


def test_case_2_trailing_silence():
    """
    测试用例2: 结尾有长静音（2秒）
    预期：保留最前0.5秒
    """
    print("\n=== 测试用例2: 结尾有2秒静音 ===")

    # 创建测试音频：1秒静音 + 3秒语音 + 2秒静音
    speech_segments = [(1.0, 4.0)]
    silence_segments = [(0.0, 1.0), (4.0, 6.0)]

    audio = create_test_audio(speech_segments, silence_segments)
    sr = 16000

    print(f"原始音频时长: {len(audio) / sr:.2f}s")

    trimmer = AudioSilenceTrimmer()
    detected_segments = trimmer.detect_speech_segments(audio, sr)
    print(f"检测到 {len(detected_segments)} 个语音段")

    trimmed_audio = trimmer.trim_silence(audio, sr, detected_segments)
    trimmed_duration = len(trimmed_audio) / sr

    print(f"切割后时长: {trimmed_duration:.2f}s")

    # 预期：1秒静音 + 3秒语音 + 0.5秒静音 = 4.5秒
    expected_duration = 1.0 + 3.0 + 0.5
    assert abs(trimmed_duration - expected_duration) < 0.1, \
        f"时长不符预期: 实际{trimmed_duration:.2f}s, 预期{expected_duration:.2f}s"

    print("✓ 测试通过")


def test_case_3_middle_long_silence():
    """
    测试用例3: 中间有长静音（2.5秒）
    预期：保留前后各0.5秒
    """
    print("\n=== 测试用例3: 中间有2.5秒静音 ===")

    # 创建测试音频：1秒语音 + 2.5秒静音 + 1秒语音
    speech_segments = [(0.0, 1.0), (3.5, 4.5)]
    silence_segments = [(1.0, 3.5)]

    audio = create_test_audio(speech_segments, silence_segments)
    sr = 16000

    print(f"原始音频时长: {len(audio) / sr:.2f}s")

    trimmer = AudioSilenceTrimmer()
    detected_segments = trimmer.detect_speech_segments(audio, sr)
    print(f"检测到 {len(detected_segments)} 个语音段")

    trimmed_audio = trimmer.trim_silence(audio, sr, detected_segments)
    trimmed_duration = len(trimmed_audio) / sr

    print(f"切割后时长: {trimmed_duration:.2f}s")

    # 预期：1秒语音 + 0.5秒静音 + 0.5秒静音 + 1秒语音 = 3.0秒
    expected_duration = 1.0 + 0.5 + 0.5 + 1.0
    assert abs(trimmed_duration - expected_duration) < 0.1, \
        f"时长不符预期: 实际{trimmed_duration:.2f}s, 预期{expected_duration:.2f}s"

    print("✓ 测试通过")


def test_case_4_short_silence():
    """
    测试用例4: 所有静音都很短
    预期：保留全部
    """
    print("\n=== 测试用例4: 所有静音都很短 ===")

    # 创建测试音频：0.5秒静音 + 2秒语音 + 1秒静音 + 2秒语音 + 0.5秒静音
    speech_segments = [(0.5, 2.5), (3.5, 5.5)]
    silence_segments = [(0.0, 0.5), (2.5, 3.5), (5.5, 6.0)]

    audio = create_test_audio(speech_segments, silence_segments)
    sr = 16000

    print(f"原始音频时长: {len(audio) / sr:.2f}s")

    trimmer = AudioSilenceTrimmer()
    detected_segments = trimmer.detect_speech_segments(audio, sr)
    print(f"检测到 {len(detected_segments)} 个语音段")

    trimmed_audio = trimmer.trim_silence(audio, sr, detected_segments)
    trimmed_duration = len(trimmed_audio) / sr

    print(f"切割后时长: {trimmed_duration:.2f}s")

    # 预期：保留全部，约6秒
    expected_duration = 6.0
    assert abs(trimmed_duration - expected_duration) < 0.2, \
        f"时长不符预期: 实际{trimmed_duration:.2f}s, 预期{expected_duration:.2f}s"

    print("✓ 测试通过")


def test_case_5_duration_validation():
    """
    测试用例5: 处理后时长不足1.5秒
    预期：返回None
    """
    print("\n=== 测试用例5: 时长验证 ===")

    # 创建测试音频：2秒静音 + 0.8秒语音 + 2秒静音
    speech_segments = [(2.0, 2.8)]
    silence_segments = [(0.0, 2.0), (2.8, 4.8)]

    audio = create_test_audio(speech_segments, silence_segments)
    sr = 16000

    print(f"原始音频时长: {len(audio) / sr:.2f}s")

    # 保存为临时文件
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, "test_short.wav")
    sf.write(temp_path, audio, sr)

    trimmer = AudioSilenceTrimmer()
    result = trimmer.process_audio_for_gender_classification(
        temp_path,
        min_final_duration=1.5
    )

    # 预期：应该返回None（时长不足）
    assert result is None, "应该返回None，因为时长不足1.5秒"

    print("✓ 测试通过")

    # 清理
    os.remove(temp_path)
    os.rmdir(temp_dir)


def test_case_6_complete_workflow():
    """
    测试用例6: 完整工作流程
    """
    print("\n=== 测试用例6: 完整工作流程 ===")

    # 创建测试音频：2秒静音 + 3秒语音 + 2秒静音
    speech_segments = [(2.0, 5.0)]
    silence_segments = [(0.0, 2.0), (5.0, 7.0)]

    audio = create_test_audio(speech_segments, silence_segments)
    sr = 16000

    print(f"原始音频时长: {len(audio) / sr:.2f}s")

    # 保存为临时文件
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, "test_complete.wav")
    sf.write(temp_path, audio, sr)

    trimmer = AudioSilenceTrimmer()
    result = trimmer.process_audio_for_gender_classification(
        temp_path,
        min_final_duration=1.5,
        temp_dir=temp_dir
    )

    # 预期：应该返回处理后的文件路径
    assert result is not None, "应该返回处理后的文件路径"
    trimmed_path, trimmed_duration = result

    print(f"处理后文件: {trimmed_path}")
    print(f"处理后时长: {trimmed_duration:.2f}s")

    # 验证文件存在
    assert os.path.exists(trimmed_path), "处理后的文件应该存在"

    # 验证时长
    assert trimmed_duration >= 1.5, "时长应该≥1.5秒"

    # 预期时长：0.5秒静音 + 3秒语音 + 0.5秒静音 = 4秒
    expected_duration = 4.0
    assert abs(trimmed_duration - expected_duration) < 0.2, \
        f"时长不符预期: 实际{trimmed_duration:.2f}s, 预期{expected_duration:.2f}s"

    print("✓ 测试通过")

    # 清理
    os.remove(temp_path)
    if os.path.exists(trimmed_path):
        os.remove(trimmed_path)
    os.rmdir(temp_dir)


if __name__ == "__main__":
    print("开始测试音频静音切割功能...")

    try:
        test_case_1_leading_silence()
        test_case_2_trailing_silence()
        test_case_3_middle_long_silence()
        test_case_4_short_silence()
        test_case_5_duration_validation()
        test_case_6_complete_workflow()

        print("\n" + "=" * 50)
        print("所有测试通过！✓")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n✗ 运行错误: {e}")
        import traceback
        traceback.print_exc()
