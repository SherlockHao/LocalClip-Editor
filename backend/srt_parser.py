import re
from typing import List, Dict


class SRTParser:
    def __init__(self):
        # SRT时间格式的正则表达式
        self.time_pattern = re.compile(r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})')

    def parse_srt(self, srt_path: str) -> List[Dict]:
        """解析SRT字幕文件"""
        try:
            with open(srt_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # 按空行分割字幕块
            blocks = re.split(r'\n\s*\n', content.strip())
            
            subtitles = []
            for block in blocks:
                lines = block.strip().split('\n')
                # 至少需要2行：序号/时间戳 + 时间戳/文本（文本可以为空）
                if len(lines) < 2:
                    continue

                # 第一行是序号（可选）
                first_line = lines[0].strip()

                # 检查是否是序号
                if first_line.isdigit():
                    if len(lines) < 2:
                        continue
                    time_line = lines[1].strip()
                    text_lines = lines[2:] if len(lines) > 2 else []
                else:
                    time_line = first_line
                    text_lines = lines[1:] if len(lines) > 1 else []

                # 解析时间
                time_match = self.time_pattern.match(time_line)
                if not time_match:
                    continue

                start_time = self._time_to_seconds(time_match.group(1), time_match.group(2), time_match.group(3), time_match.group(4))
                end_time = self._time_to_seconds(time_match.group(5), time_match.group(6), time_match.group(7), time_match.group(8))

                # 合并字幕文本（允许为空）
                subtitle_text = ' '.join(text.strip() for text in text_lines if text.strip())
                
                subtitles.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_time_formatted": self._format_time(start_time),
                    "end_time_formatted": self._format_time(end_time),
                    "text": subtitle_text
                })
            
            return subtitles
        except Exception as e:
            print(f"解析SRT文件时出错: {e}")
            return []

    def _time_to_seconds(self, hours: str, minutes: str, seconds: str, milliseconds: str) -> float:
        """将时间转换为秒"""
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000

    def _format_time(self, seconds: float) -> str:
        """将秒数格式化为 HH:MM:SS,mmm 格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def create_srt_block(self, start_time: float, end_time: float, text: str) -> str:
        """创建SRT块"""
        start_formatted = self._format_time(start_time)
        end_formatted = self._format_time(end_time)
        return f"{start_formatted} --> {end_formatted}\n{text}"

    def save_srt(self, subtitles: List[Dict], srt_path: str):
        """保存字幕到SRT文件"""
        try:
            with open(srt_path, 'w', encoding='utf-8') as file:
                for i, sub in enumerate(subtitles, 1):
                    block = f"{i}\n"
                    block += f"{sub['start_time_formatted']} --> {sub['end_time_formatted']}\n"
                    block += f"{sub['text']}\n\n"
                    file.write(block)
        except Exception as e:
            print(f"保存SRT文件时出错: {e}")