"""
印尼语TTS调用器
封装印尼语TTS批量生成逻辑（类似 SimpleFishCloner）
"""
import os
import subprocess
import json
import re
from typing import List, Dict, Optional, Callable


class IndonesianTTSCloner:
    """印尼语TTS批量克隆器"""

    def __init__(self, model_dir: str, tts_id_env_python: str):
        """
        初始化印尼语TTS克隆器

        Args:
            model_dir: VITS-TTS-ID 模型路径
            tts_id_env_python: tts-id-py311 环境的 Python 路径
        """
        self.model_dir = model_dir
        self.tts_id_env_python = tts_id_env_python

        # 验证模型路径
        if not os.path.exists(model_dir):
            raise FileNotFoundError(f"Indonesian TTS model directory not found: {model_dir}")

        # 验证Python环境
        if not os.path.exists(tts_id_env_python):
            raise FileNotFoundError(f"TTS-ID Python environment not found: {tts_id_env_python}")

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        config_file: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """
        批量生成印尼语语音

        Args:
            tasks: 任务列表，每个任务格式:
                {
                    "segment_index": 0,
                    "speaker_name": "ardi",
                    "target_text": "Selamat pagi",
                    "output_file": "exports/cloned_xxx/segment_0.wav"
                }
            config_file: 配置文件路径
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            {segment_index: audio_file_path}
        """
        print(f"\n[IndonesianTTS] 开始批量生成 {len(tasks)} 个音频片段...")

        # 1. 写入配置文件
        config = {
            "model_dir": self.model_dir,
            "tasks": tasks
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"[IndonesianTTS] 配置文件已写入: {config_file}")

        # 2. 调用批量生成脚本
        script_path = os.path.join(os.path.dirname(__file__), "indonesian_batch_tts.py")

        print(f"[IndonesianTTS] 执行脚本: {script_path}")
        print(f"[IndonesianTTS] Python环境: {self.tts_id_env_python}")

        process = subprocess.Popen(
            [self.tts_id_env_python, script_path, config_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 3. 实时解析进度和日志
        # 使用 communicate() 同时读取 stdout 和 stderr，避免死锁
        import threading

        stderr_lines = []
        total_tasks = len(tasks)

        def read_stderr():
            """在单独的线程中读取 stderr"""
            for line in process.stderr:
                line = line.strip()
                if line:
                    stderr_lines.append(line)
                    print(f"[IndonesianTTS] {line}")

                    # 解析进度: [BatchGen] 进度: 5/15
                    match = re.search(r'\[BatchGen\]\s+进度:\s+(\d+)/(\d+)', line)
                    if match and progress_callback:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        progress_callback(current, total)

        # 在后台线程中读取 stderr
        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        # 主线程读取 stdout（JSON 结果）
        stdout = process.stdout.read()

        # 等待进程完成和 stderr 线程结束
        process.wait()
        stderr_thread.join(timeout=5)  # 最多等待5秒
        returncode = process.returncode

        if returncode != 0:
            error_msg = "\n".join(stderr_lines[-10:])  # 最后10行错误信息
            raise RuntimeError(f"Indonesian TTS batch generation failed (exit code {returncode}):\n{error_msg}")

        # 4. 解析结果 (stdout 是 JSON)
        try:
            results = json.loads(stdout)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Failed to parse output JSON: {e}")
            print(f"[ERROR] stdout content:\n{stdout[:500]}")
            raise RuntimeError(f"Failed to parse Indonesian TTS output: {e}")

        # 5. 转换为字典格式
        segment_files = {}
        success_count = 0
        error_count = 0

        for result in results:
            segment_index = result["segment_index"]
            status = result["status"]

            if status == "success":
                segment_files[segment_index] = result["output_file"]
                success_count += 1
            else:
                error_count += 1
                error_msg = result.get("error_message", "Unknown error")
                print(f"[ERROR] Segment {segment_index} failed: {error_msg}")

        print(f"\n[IndonesianTTS] 批量生成完成:")
        print(f"  成功: {success_count} 个")
        print(f"  失败: {error_count} 个")

        return segment_files

    def get_available_speakers(self) -> List[str]:
        """
        获取可用的印尼语音色列表

        Returns:
            音色名称列表 ["ardi", "wibowo", "gadis"]
        """
        return ["ardi", "wibowo", "gadis"]
