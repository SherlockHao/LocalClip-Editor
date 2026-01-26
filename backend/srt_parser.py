import re
from typing import List, Dict


class SRTParser:
    """SRT/ASS 字幕解析器"""
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

    # ==================== ASS 格式支持 ====================

    def parse_ass(self, ass_path: str) -> List[Dict]:
        """解析ASS/SSA字幕文件"""
        try:
            with open(ass_path, 'r', encoding='utf-8') as file:
                content = file.read()

            subtitles = []
            in_events = False
            format_fields = []

            for line in content.split('\n'):
                line = line.strip()

                # 检测 [Events] 部分
                if line.lower() == '[events]':
                    in_events = True
                    continue

                # 检测其他部分开始
                if line.startswith('[') and line.endswith(']'):
                    in_events = False
                    continue

                if not in_events:
                    continue

                # 解析 Format 行
                if line.lower().startswith('format:'):
                    format_str = line[7:].strip()
                    format_fields = [f.strip().lower() for f in format_str.split(',')]
                    continue

                # 解析 Dialogue 行
                if line.lower().startswith('dialogue:'):
                    dialogue_str = line[9:].strip()

                    # ASS 格式: 最后一个字段是 Text，可能包含逗号
                    # 所以我们只分割前 N-1 个字段
                    if format_fields:
                        num_fields = len(format_fields)
                        parts = dialogue_str.split(',', num_fields - 1)
                    else:
                        # 默认 ASS 格式有 10 个字段
                        parts = dialogue_str.split(',', 9)

                    if len(parts) < 3:
                        continue

                    # 获取时间字段索引
                    start_idx = format_fields.index('start') if 'start' in format_fields else 1
                    end_idx = format_fields.index('end') if 'end' in format_fields else 2
                    text_idx = format_fields.index('text') if 'text' in format_fields else -1

                    start_time_str = parts[start_idx].strip() if start_idx < len(parts) else ''
                    end_time_str = parts[end_idx].strip() if end_idx < len(parts) else ''
                    text = parts[text_idx].strip() if text_idx != -1 and text_idx < len(parts) else parts[-1].strip()

                    # 清理 ASS 特殊标签
                    text = self._clean_ass_tags(text)

                    start_time = self._ass_time_to_seconds(start_time_str)
                    end_time = self._ass_time_to_seconds(end_time_str)

                    if start_time is not None and end_time is not None:
                        subtitles.append({
                            "start_time": start_time,
                            "end_time": end_time,
                            "start_time_formatted": self._format_time(start_time),
                            "end_time_formatted": self._format_time(end_time),
                            "text": text
                        })

            # 按开始时间排序
            subtitles.sort(key=lambda x: x['start_time'])
            return subtitles

        except Exception as e:
            print(f"解析ASS文件时出错: {e}")
            return []

    def _ass_time_to_seconds(self, time_str: str) -> float:
        """将ASS时间格式转换为秒 (H:MM:SS.CC)"""
        try:
            # ASS 时间格式: H:MM:SS.CC (centiseconds)
            match = re.match(r'(\d+):(\d{2}):(\d{2})\.(\d{2})', time_str)
            if match:
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = int(match.group(3))
                centiseconds = int(match.group(4))
                return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
            return None
        except:
            return None

    def _clean_ass_tags(self, text: str) -> str:
        """清理ASS特殊标签"""
        # 移除 {\xxx} 格式的标签
        text = re.sub(r'\{[^}]*\}', '', text)
        # 将 \N 和 \n 转换为空格
        text = text.replace('\\N', ' ').replace('\\n', ' ')
        # 清理多余空格
        text = ' '.join(text.split())
        return text

    def _format_ass_time(self, seconds: float) -> str:
        """将秒数格式化为ASS时间格式 (H:MM:SS.CC)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centiseconds = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

    def save_ass(self, subtitles: List[Dict], ass_path: str,
                 title: str = "Translated Subtitle",
                 style_name: str = "Default",
                 font_name: str = "Arial",
                 font_size: int = 20,
                 primary_color: str = "&H00FFFFFF",
                 outline_color: str = "&H00000000",
                 outline: int = 2,
                 margin_v: int = 20):
        """
        保存字幕到ASS文件

        Args:
            subtitles: 字幕列表
            ass_path: 输出文件路径
            title: 脚本标题
            style_name: 样式名称
            font_name: 字体名称
            font_size: 字体大小
            primary_color: 主要颜色 (ASS格式: &HAABBGGRR)
            outline_color: 边框颜色
            outline: 边框宽度
            margin_v: 垂直边距
        """
        try:
            with open(ass_path, 'w', encoding='utf-8') as file:
                # [Script Info] 部分
                file.write("[Script Info]\n")
                file.write(f"Title: {title}\n")
                file.write("ScriptType: v4.00+\n")
                file.write("Collisions: Normal\n")
                file.write("PlayDepth: 0\n")
                file.write("PlayResX: 1920\n")
                file.write("PlayResY: 1080\n")
                file.write("\n")

                # [V4+ Styles] 部分
                file.write("[V4+ Styles]\n")
                file.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
                file.write(f"Style: {style_name},{font_name},{font_size},{primary_color},&H000000FF,{outline_color},&H80000000,0,0,0,0,100,100,0,0,1,{outline},1,2,10,10,{margin_v},1\n")
                file.write("\n")

                # [Events] 部分
                file.write("[Events]\n")
                file.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

                for sub in subtitles:
                    start_time = self._format_ass_time(sub['start_time'])
                    end_time = self._format_ass_time(sub['end_time'])
                    text = sub['text'].replace('\n', '\\N')
                    file.write(f"Dialogue: 0,{start_time},{end_time},{style_name},,0,0,0,,{text}\n")

            print(f"ASS字幕已保存: {ass_path}")

        except Exception as e:
            print(f"保存ASS文件时出错: {e}")

    def detect_subtitle_format(self, file_path: str) -> str:
        """检测字幕文件格式"""
        ext = file_path.lower()
        if ext.endswith('.ass') or ext.endswith('.ssa'):
            return 'ass'
        elif ext.endswith('.srt'):
            return 'srt'
        else:
            # 尝试通过内容检测
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read(500)
                    if '[Script Info]' in content or '[Events]' in content:
                        return 'ass'
                    elif '-->' in content:
                        return 'srt'
            except:
                pass
            return 'unknown'

    def parse_subtitle(self, file_path: str) -> List[Dict]:
        """自动检测格式并解析字幕文件"""
        format_type = self.detect_subtitle_format(file_path)
        if format_type == 'ass':
            return self.parse_ass(file_path)
        elif format_type == 'srt':
            return self.parse_srt(file_path)
        else:
            print(f"未知字幕格式: {file_path}")
            return []