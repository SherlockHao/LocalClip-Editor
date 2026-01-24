# -*- coding: utf-8 -*-
"""
Test accumulative concatenation logic
"""


def test_accumulative_logic():
    """
    Test accumulative concatenation logic without actual audio processing
    """
    print("=== Test Accumulative Audio Concatenation Logic ===\n")

    # Simulate scenario: 5 audio segments with different durations after trimming
    segments = [
        {"name": "segment_1.wav", "mos": 4.2, "original_duration": 3.0, "trimmed_duration": 0.8},
        {"name": "segment_2.wav", "mos": 4.0, "original_duration": 2.5, "trimmed_duration": 0.6},
        {"name": "segment_3.wav", "mos": 3.8, "original_duration": 2.8, "trimmed_duration": 0.4},
        {"name": "segment_4.wav", "mos": 3.5, "original_duration": 1.5, "trimmed_duration": 0.3},
        {"name": "segment_5.wav", "mos": 3.2, "original_duration": 1.8, "trimmed_duration": 0.5},
    ]

    min_duration = 2.0
    min_final_duration = 1.5

    # Sort by MOS score (already sorted in this example)
    sorted_segments = sorted(segments, key=lambda x: x["mos"], reverse=True)

    print(f"Target cumulative duration: >= {min_final_duration}s\n")
    print("Phase 1: Process segments with original duration >= 2.0s")

    accumulated_audios = []
    accumulated_duration = 0.0

    for seg in sorted_segments:
        if seg["original_duration"] >= min_duration:
            print(f"\nTrying segment {len(accumulated_audios)+1}: {seg['name']}")
            print(f"  Original: {seg['original_duration']}s, MOS: {seg['mos']}")
            print(f"  After trimming: {seg['trimmed_duration']}s")

            if seg["trimmed_duration"] > 0:
                accumulated_audios.append(seg["name"])
                accumulated_duration += seg["trimmed_duration"]
                print(f"  [Accumulated] {seg['trimmed_duration']}s, Total: {accumulated_duration:.2f}s")

                if accumulated_duration >= min_final_duration:
                    print(f"\n[SUCCESS] Reached target duration {accumulated_duration:.2f}s >= {min_final_duration}s")
                    print(f"[RESULT] Will concatenate {len(accumulated_audios)} segments:")
                    for i, name in enumerate(accumulated_audios, 1):
                        print(f"  {i}. {name}")
                    return True

    print(f"\nPhase 2: Process segments with original duration < 2.0s")
    print(f"Current cumulative: {accumulated_duration:.2f}s")

    for seg in sorted_segments:
        if seg["original_duration"] < min_duration:
            print(f"\nTrying segment {len(accumulated_audios)+1}: {seg['name']}")
            print(f"  Original: {seg['original_duration']}s, MOS: {seg['mos']}")
            print(f"  After trimming: {seg['trimmed_duration']}s")

            if seg["trimmed_duration"] > 0:
                accumulated_audios.append(seg["name"])
                accumulated_duration += seg["trimmed_duration"]
                print(f"  [Accumulated] {seg['trimmed_duration']}s, Total: {accumulated_duration:.2f}s")

                if accumulated_duration >= min_final_duration:
                    print(f"\n[SUCCESS] Reached target duration {accumulated_duration:.2f}s >= {min_final_duration}s")
                    print(f"[RESULT] Will concatenate {len(accumulated_audios)} segments:")
                    for i, name in enumerate(accumulated_audios, 1):
                        print(f"  {i}. {name}")
                    return True

    # If still not enough
    if accumulated_audios:
        print(f"\n[WARNING] All segments cumulative duration {accumulated_duration:.2f}s < {min_final_duration}s")
        print(f"[FALLBACK] Use accumulated {len(accumulated_audios)} segments:")
        for i, name in enumerate(accumulated_audios, 1):
            print(f"  {i}. {name}")
        return True
    else:
        print("\n[ERROR] No usable segments")
        return False


def test_expected_behavior():
    """
    Test expected behavior with the example data
    """
    print("\n\n" + "=" * 60)
    print("Expected Behavior Analysis")
    print("=" * 60 + "\n")

    segments = [
        {"name": "segment_1.wav", "mos": 4.2, "trimmed": 0.8},
        {"name": "segment_2.wav", "mos": 4.0, "trimmed": 0.6},
        {"name": "segment_3.wav", "mos": 3.8, "trimmed": 0.4},
        {"name": "segment_4.wav", "mos": 3.5, "trimmed": 0.3},
        {"name": "segment_5.wav", "mos": 3.2, "trimmed": 0.5},
    ]

    print("Accumulation process:")
    cumulative = 0.0
    selected = []

    for i, seg in enumerate(segments, 1):
        cumulative += seg["trimmed"]
        selected.append(seg["name"])
        print(f"  Step {i}: Add {seg['name']} ({seg['trimmed']}s) -> Total: {cumulative:.2f}s")

        if cumulative >= 1.5:
            print(f"\n[STOP] Reached 1.5s at step {i}")
            print(f"Selected segments: {selected}")
            print(f"Total duration: {cumulative:.2f}s")
            break

    print("\nExpected: Should select segments 1, 2, 3 (0.8 + 0.6 + 0.4 = 1.8s)")


if __name__ == "__main__":
    success = test_accumulative_logic()

    if success:
        test_expected_behavior()
        print("\n" + "=" * 60)
        print("[PASS] Accumulative logic test completed successfully")
        print("=" * 60)
    else:
        print("\n[FAIL] Accumulative logic test failed")
