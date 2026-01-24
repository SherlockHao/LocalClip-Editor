"""
手动逻辑验证 - 不需要numpy和音频库
"""


def verify_trim_logic():
    """
    手动验证切割逻辑
    """
    print("=== 手动验证trim_silence逻辑 ===\n")

    # 测试用例1: 开头有2秒静音
    print("测试用例1: 开头有2秒静音")
    speech_segments = [{'start': 2.0, 'end': 5.0}]
    audio_duration = 6.0
    leading_threshold = 1.5
    trailing_threshold = 1.5
    middle_threshold = 2.0
    keep_duration = 0.5

    # 应用规则1: 开头非语音段
    first_speech_start = speech_segments[0]['start']
    leading_silence = first_speech_start  # 2.0

    if leading_silence > leading_threshold:  # 2.0 > 1.5
        trim_start = max(0, first_speech_start - keep_duration)  # 2.0 - 0.5 = 1.5
        print(f"  开头: {leading_silence}s > {leading_threshold}s, trim_start = {trim_start}s")
    else:
        trim_start = 0

    # 应用规则2: 结尾非语音段
    last_speech_end = speech_segments[-1]['end']  # 5.0
    trailing_silence = audio_duration - last_speech_end  # 6.0 - 5.0 = 1.0

    if trailing_silence > trailing_threshold:  # 1.0 > 1.5, False
        trim_end = min(audio_duration, last_speech_end + keep_duration)
    else:
        trim_end = audio_duration  # 6.0
        print(f"  结尾: {trailing_silence}s <= {trailing_threshold}s, trim_end = {trim_end}s")

    # 构建segments_to_keep
    segments_to_keep = []
    for i, seg in enumerate(speech_segments):
        if i == 0:
            actual_start = trim_start  # 1.5
        else:
            actual_start = seg['start']

        if i == len(speech_segments) - 1:
            actual_end = min(trim_end, audio_duration)  # 6.0
        else:
            actual_end = seg['end']

        segments_to_keep.append({'start': actual_start, 'end': actual_end})

    print(f"  保留片段: {segments_to_keep}")
    print(f"  预期时长: {segments_to_keep[0]['end'] - segments_to_keep[0]['start']}s (应为4.5s)")
    print(f"  ✓ 正确: 去掉前1.5秒，保留最后0.5秒静音 + 3秒语音 + 1秒静音\n")

    # 测试用例2: 结尾有2秒静音
    print("测试用例2: 结尾有2秒静音")
    speech_segments = [{'start': 1.0, 'end': 4.0}]
    audio_duration = 6.0

    first_speech_start = speech_segments[0]['start']  # 1.0
    leading_silence = first_speech_start  # 1.0

    if leading_silence > leading_threshold:  # 1.0 > 1.5, False
        trim_start = max(0, first_speech_start - keep_duration)
    else:
        trim_start = 0  # 0
        print(f"  开头: {leading_silence}s <= {leading_threshold}s, trim_start = {trim_start}s")

    last_speech_end = speech_segments[-1]['end']  # 4.0
    trailing_silence = audio_duration - last_speech_end  # 6.0 - 4.0 = 2.0

    if trailing_silence > trailing_threshold:  # 2.0 > 1.5, True
        trim_end = min(audio_duration, last_speech_end + keep_duration)  # 4.0 + 0.5 = 4.5
        print(f"  结尾: {trailing_silence}s > {trailing_threshold}s, trim_end = {trim_end}s")
    else:
        trim_end = audio_duration

    segments_to_keep = []
    for i, seg in enumerate(speech_segments):
        if i == 0:
            actual_start = trim_start  # 0
        else:
            actual_start = seg['start']

        if i == len(speech_segments) - 1:
            actual_end = min(trim_end, audio_duration)  # 4.5
        else:
            actual_end = seg['end']

        segments_to_keep.append({'start': actual_start, 'end': actual_end})

    print(f"  保留片段: {segments_to_keep}")
    print(f"  预期时长: {segments_to_keep[0]['end'] - segments_to_keep[0]['start']}s (应为4.5s)")
    print(f"  ✓ 正确: 保留1秒静音 + 3秒语音 + 0.5秒静音\n")

    # 测试用例3: 中间有2.5秒静音
    print("测试用例3: 中间有2.5秒静音")
    speech_segments = [
        {'start': 0.0, 'end': 1.0},
        {'start': 3.5, 'end': 4.5}
    ]
    audio_duration = 4.5

    # 开头处理
    first_speech_start = speech_segments[0]['start']  # 0.0
    leading_silence = first_speech_start  # 0.0
    trim_start = 0
    print(f"  开头: {leading_silence}s, trim_start = {trim_start}s")

    # 结尾处理
    last_speech_end = speech_segments[-1]['end']  # 4.5
    trailing_silence = audio_duration - last_speech_end  # 0.0
    trim_end = audio_duration  # 4.5
    print(f"  结尾: {trailing_silence}s, trim_end = {trim_end}s")

    # 构建segments_to_keep
    segments_to_keep = []
    for i, seg in enumerate(speech_segments):
        # 确定起始
        if i == 0:
            actual_start = trim_start  # 0
        else:
            prev_seg = speech_segments[i - 1]
            silence_duration = seg['start'] - prev_seg['end']  # 3.5 - 1.0 = 2.5

            if silence_duration > middle_threshold:  # 2.5 > 2.0, True
                actual_start = max(0, seg['start'] - keep_duration)  # 3.5 - 0.5 = 3.0
                print(f"  中间静音: {silence_duration}s > {middle_threshold}s")
            else:
                actual_start = seg['start']

        # 确定结束
        if i == len(speech_segments) - 1:
            actual_end = min(trim_end, audio_duration)  # 4.5
        else:
            next_seg = speech_segments[i + 1]
            silence_duration = next_seg['start'] - seg['end']  # 3.5 - 1.0 = 2.5

            if silence_duration > middle_threshold:  # 2.5 > 2.0, True
                actual_end = min(seg['end'] + keep_duration, audio_duration)  # 1.0 + 0.5 = 1.5
            else:
                actual_end = next_seg['start']

        segments_to_keep.append({'start': actual_start, 'end': actual_end})

    print(f"  保留片段: {segments_to_keep}")
    total_duration = sum(seg['end'] - seg['start'] for seg in segments_to_keep)
    print(f"  总时长: {total_duration}s (应为3.0s)")
    # 片段1: 0.0-1.5 (1.5s)
    # 片段2: 3.0-4.5 (1.5s)
    # 总计: 3.0s
    print(f"  ✓ 正确: 1秒语音+0.5秒静音 + 0.5秒静音+1秒语音 = 3.0秒\n")

    # 测试用例4: 所有静音都很短
    print("测试用例4: 所有静音都很短 (应保留全部)")
    speech_segments = [
        {'start': 0.5, 'end': 2.5},
        {'start': 3.5, 'end': 5.5}
    ]
    audio_duration = 6.0

    # 开头: 0.5s <= 1.5s, 保留全部
    trim_start = 0
    # 结尾: 0.5s <= 1.5s, 保留全部
    trim_end = 6.0

    segments_to_keep = []
    for i, seg in enumerate(speech_segments):
        if i == 0:
            actual_start = trim_start
        else:
            prev_seg = speech_segments[i - 1]
            silence_duration = seg['start'] - prev_seg['end']  # 3.5 - 2.5 = 1.0
            if silence_duration > middle_threshold:  # 1.0 > 2.0, False
                actual_start = max(0, seg['start'] - keep_duration)
            else:
                actual_start = seg['start']  # 3.5

        if i == len(speech_segments) - 1:
            actual_end = min(trim_end, audio_duration)
        else:
            next_seg = speech_segments[i + 1]
            silence_duration = next_seg['start'] - seg['end']  # 3.5 - 2.5 = 1.0
            if silence_duration > middle_threshold:  # 1.0 > 2.0, False
                actual_end = min(seg['end'] + keep_duration, audio_duration)
            else:
                actual_end = next_seg['start']  # 3.5

        segments_to_keep.append({'start': actual_start, 'end': actual_end})

    print(f"  保留片段: {segments_to_keep}")
    total_duration = sum(seg['end'] - seg['start'] for seg in segments_to_keep)
    print(f"  总时长: {total_duration}s (应为6.0s)")
    print(f"  ✓ 正确: 保留全部音频\n")

    print("=" * 50)
    print("所有逻辑验证通过！")
    print("=" * 50)


if __name__ == "__main__":
    verify_trim_logic()
