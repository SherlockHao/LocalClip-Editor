#!/usr/bin/env python3
"""
SRT 字幕解析功能测试脚本
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from srt_parser import SRTParser, SubtitleEntry

def test_srt_parsing():
    """测试 SRT 字幕解析功能"""
    print("=== 测试 SRT 字幕解析功能 ===")
    
    # 测试数据 - 用户提供的示例
    test_srt_content = """1
00:00:03,900 --> 00:00:04,733
你好啊

2
00:00:04,733 --> 00:00:06,200
我是你大哥
"""
    
    print("1. 测试基本解析功能...")
    try:
        entries = SRTParser.parse_file(test_srt_content)
        print(f"✓ 成功解析 {len(entries)} 条字幕")
        
        # 验证第一条字幕
        entry1 = entries[0]
        entry1_dict = entry1.to_dict()
        print(f"   字幕1: '{entry1.text}'")
        print(f"   开始时间: {entry1.start_time}s ({entry1_dict['start_formatted']})")
        print(f"   结束时间: {entry1.end_time}s ({entry1_dict['end_formatted']})")
        print(f"   持续时间: {entry1.duration}s")
        
        # 验证第二条字幕
        entry2 = entries[1]
        entry2_dict = entry2.to_dict()
        print(f"   字幕2: '{entry2.text}'")
        print(f"   开始时间: {entry2.start_time}s ({entry2_dict['start_formatted']})")
        print(f"   结束时间: {entry2.end_time}s ({entry2_dict['end_formatted']})")
        print(f"   持续时间: {entry2.duration}s")
        
        # 验证时间计算准确性
        expected_start1 = 3.9  # 00:00:03,900
        expected_end1 = 4.733  # 00:00:04,733
        expected_start2 = 4.733  # 00:00:04,733
        expected_end2 = 6.2  # 00:00:06,200
        
        assert abs(entry1.start_time - expected_start1) < 0.001, f"字幕1开始时间错误: {entry1.start_time} != {expected_start1}"
        assert abs(entry1.end_time - expected_end1) < 0.001, f"字幕1结束时间错误: {entry1.end_time} != {expected_end1}"
        assert abs(entry2.start_time - expected_start2) < 0.001, f"字幕2开始时间错误: {entry2.start_time} != {expected_start2}"
        assert abs(entry2.end_time - expected_end2) < 0.001, f"字幕2结束时间错误: {entry2.end_time} != {expected_end2}"
        
        print("✓ 时间解析准确无误")
        
    except Exception as e:
        print(f"✗ 解析失败: {e}")
        return False
    
    print("\n2. 测试时间轴位置计算...")
    try:
        # 假设视频总时长为 10 秒
        video_duration = 10.0
        timeline_data = SRTParser.calculate_timeline_positions(entries, video_duration)
        
        print(f"✓ 成功计算 {len(timeline_data)} 条字幕的时间轴位置")
        
        for i, data in enumerate(timeline_data):
            print(f"   字幕{i+1}: 左边距 {data['left_percent']:.2f}%, 宽度 {data['width_percent']:.2f}%")
            
            # 验证位置计算
            expected_left = (data['start_time'] / video_duration) * 100
            expected_width = ((data['end_time'] - data['start_time']) / video_duration) * 100
            
            assert abs(data['left_percent'] - expected_left) < 0.01, f"左边距计算错误"
            assert abs(data['width_percent'] - expected_width) < 0.01, f"宽度计算错误"
        
        print("✓ 时间轴位置计算准确无误")
        
    except Exception as e:
        print(f"✗ 时间轴计算失败: {e}")
        return False
    
    print("\n3. 测试字幕查找功能...")
    try:
        # 测试在不同时间点的字幕查找
        test_cases = [
            (3.5, None),  # 在第一条字幕之前
            (4.0, entries[0]),  # 在第一条字幕期间
            (5.0, entries[1]),  # 在第二条字幕期间
            (7.0, None),  # 在所有字幕之后
        ]
        
        for time_point, expected in test_cases:
            result = SRTParser.get_subtitle_at_time(entries, time_point)
            if expected is None:
                assert result is None, f"时间点 {time_point}s 应该没有字幕"
                print(f"   ✓ 时间点 {time_point}s: 无字幕 (预期)")
            else:
                assert result == expected, f"时间点 {time_point}s 字幕匹配错误"
                print(f"   ✓ 时间点 {time_point}s: '{result.text}'")
        
        print("✓ 字幕查找功能正常")
        
    except Exception as e:
        print(f"✗ 字幕查找失败: {e}")
        return False
    
    print("\n=== SRT 字幕解析功能测试通过 ===")
    return True

def test_edge_cases():
    """测试边界情况"""
    print("\n=== 测试边界情况 ===")
    
    # 测试空内容
    try:
        entries = SRTParser.parse_file("")
        assert len(entries) == 0
        print("✓ 空内容处理正常")
    except Exception as e:
        print(f"✗ 空内容处理失败: {e}")
        return False
    
    # 测试单个字幕
    single_subtitle = "1\n00:00:01,000 --> 00:00:02,000\n测试字幕"
    try:
        entries = SRTParser.parse_file(single_subtitle)
        assert len(entries) == 1
        assert entries[0].text == "测试字幕"
        print("✓ 单个字幕处理正常")
    except Exception as e:
        print(f"✗ 单个字幕处理失败: {e}")
        return False
    
    print("=== 边界情况测试通过 ===")
    return True

if __name__ == "__main__":
    success = test_srt_parsing() and test_edge_cases()
    
    if success:
        print("\n🎉 所有测试通过！SRT 字幕解析功能工作正常。")
        sys.exit(0)
    else:
        print("\n❌ 测试失败！")
        sys.exit(1)