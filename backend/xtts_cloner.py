# -*- coding: utf-8 -*-
"""
XTTS-v2 语音克隆器
基于 Coqui TTS XTTS-v2 模型，支持多语言语音克隆

通过子进程调用 xtts 环境中的脚本，类似于 fish_simple_cloner

特点：
- 无需预编码，直接使用参考音频
- 支持 GPU 加速
- 支持多语言（中、英、日、韩、法、德、西班牙语等）

作者：Claude
"""
import os
import sys
import subprocess
import json
import tempfile
import platform
from typing import Dict, List, Optional, Callable
from loguru import logger


class XTTSCloner:
    """
    XTTS-v2 语音克隆器

    特点：
    - 通过子进程调用 xtts 环境
    - 直接使用参考音频，无需预编码
    - 支持 GPU 加速
    """

    def __init__(
        self,
        xtts_python: str = None,
        use_gpu: bool = True
    ):
        """
        初始化 XTTS 克隆器

        Args:
            xtts_python: xtts 环境的 Python 可执行文件路径
            use_gpu: 是否使用 GPU
        """
        self.use_gpu = use_gpu

        # 根据平台设置默认路径
        if platform.system() == "Windows":
            self.xtts_python = xtts_python or os.environ.get(
                "XTTS_PYTHON",
                r"C:\Miniconda3\envs\xtts\python.exe"
            )
        else:
            self.xtts_python = xtts_python or os.environ.get(
                "XTTS_PYTHON",
                "/Users/yiya_workstation/miniconda3/envs/xtts/bin/python"
            )

        logger.info(f"XTTS-v2 克隆器初始化")
        logger.info(f"  Python 路径: {self.xtts_python}")
        logger.info(f"  GPU: {'启用' if use_gpu else '禁用'}")

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        speaker_references: Dict[int, Dict],
        output_dir: str,
        target_language: str = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """
        批量生成音频

        Args:
            tasks: 任务列表 [{"speaker_id": 0, "target_text": "...", "segment_index": 0}, ...]
            speaker_references: 说话人参考数据 {speaker_id: {reference_audio, reference_text, target_language, ...}}
            output_dir: 输出目录
            target_language: 目标语言（如果 tasks 中没有指定）
            progress_callback: 进度回调函数 callback(current, total)

        Returns:
            {segment_index: output_file_path, ...}
        """
        logger.info(f"\n🎵 [XTTS] 批量生成 {len(tasks)} 个语音片段...")
        print(f"\n🎵 [XTTS] 批量生成 {len(tasks)} 个语音片段...", flush=True)

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 创建临时配置文件
        generate_config = {
            "mode": "generate",
            "use_gpu": self.use_gpu,
            "output_dir": os.path.abspath(output_dir),
            "target_language": target_language,
            "tasks": []
        }

        for task in tasks:
            speaker_id = task["speaker_id"]
            segment_index = task["segment_index"]
            target_text = task["target_text"]

            # 获取说话人参考信息
            ref_info = speaker_references.get(speaker_id)
            if not ref_info:
                logger.warning(f"[XTTS] ⚠️ 说话人 {speaker_id} 没有参考数据，跳过片段 {segment_index}")
                continue

            reference_audio = ref_info.get("reference_audio")
            if not reference_audio or not os.path.exists(reference_audio):
                logger.warning(f"[XTTS] ⚠️ 说话人 {speaker_id} 的参考音频不存在: {reference_audio}")
                continue

            # 确定目标语言
            lang = target_language or ref_info.get("target_language", "en")

            generate_config["tasks"].append({
                "segment_index": segment_index,
                "speaker_id": speaker_id,
                "target_text": target_text,
                "reference_audio": os.path.abspath(reference_audio),
                "target_language": lang,
                "output_file": os.path.abspath(
                    os.path.join(output_dir, f"segment_{segment_index}.wav")
                )
            })

        if not generate_config["tasks"]:
            logger.warning("[XTTS] 没有有效的任务")
            return {}

        # 写入临时配置
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            delete=False,
            encoding='utf-8'
        ) as f:
            json.dump(generate_config, f, ensure_ascii=False, indent=2)
            config_file = f.name

        try:
            # 调用生成脚本
            script_path = os.path.join(
                os.path.dirname(__file__),
                "xtts_batch_generate.py"
            )

            cmd = [self.xtts_python, script_path, config_file]

            logger.info(f"执行生成命令: {' '.join(cmd)}")
            print(f"[XTTS] 执行: {' '.join(cmd)}", flush=True)
            print("[XTTS] 正在生成，请查看下方进度...", flush=True)

            # 使用 Popen 实时显示输出
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                bufsize=1
            )

            # 实时读取并显示输出
            output_lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    # 显示进度信息
                    if '[XTTS]' in line or 'INFO' in line:
                        print(line, flush=True)

                    # 解析进度
                    import re
                    try:
                        # 匹配 "[XTTS] 进度: 5/30" 或 "[XTTS] Progress: 5/30"
                        if '[XTTS]' in line and ('进度' in line or 'Progress' in line or '/' in line):
                            match = re.search(r'(\d+)/(\d+)', line)
                            if match:
                                current = int(match.group(1))
                                total = int(match.group(2))
                                if progress_callback:
                                    progress_callback(current, total)
                    except Exception as e:
                        pass

                    output_lines.append(line)

            # 等待进程结束
            proc.wait()

            if proc.returncode != 0:
                logger.error(f"[XTTS] 生成失败！返回码: {proc.returncode}")
                for line in output_lines[-20:]:
                    logger.error(line)
                raise RuntimeError(f"XTTS 生成失败，返回码: {proc.returncode}")

            # 解析结果 - 从后向前查找有效的 JSON 对象行
            try:
                json_line = "{}"
                for line in reversed(output_lines):
                    line = line.strip()
                    if line.startswith('{') and line.endswith('}'):
                        try:
                            json.loads(line)  # 验证是有效 JSON
                            json_line = line
                            break
                        except json.JSONDecodeError:
                            continue

                result_data = json.loads(json_line)

                # 将字符串键转换为整数键
                result_data = {int(k): v for k, v in result_data.items()}

                logger.info(f"✅ [XTTS] 生成完成！生成 {len(result_data)} 个音频文件")
                print(f"✅ [XTTS] 生成完成！生成 {len(result_data)} 个音频文件", flush=True)
                return result_data

            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.error(f"解析 XTTS 结果失败: {e}")
                logger.error(f"输出最后10行: {output_lines[-10:] if output_lines else []}")
                raise

        finally:
            # 清理临时文件
            try:
                os.remove(config_file)
            except:
                pass


# 全局单例
_global_xtts_cloner: Optional[XTTSCloner] = None


def get_xtts_cloner(use_gpu: bool = True) -> XTTSCloner:
    """
    获取全局 XTTS 克隆器实例（单例模式）

    Args:
        use_gpu: 是否使用 GPU

    Returns:
        XTTSCloner 实例
    """
    global _global_xtts_cloner

    if _global_xtts_cloner is None:
        _global_xtts_cloner = XTTSCloner(use_gpu=use_gpu)

    return _global_xtts_cloner


def reset_xtts_cloner():
    """重置全局 XTTS 克隆器"""
    global _global_xtts_cloner
    _global_xtts_cloner = None
