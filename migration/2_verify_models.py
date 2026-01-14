#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor 模型验证脚本
用于验证所有必要的AI模型是否已正确迁移
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.RESET}\n")

def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

# 定义所有需要的模型及其路径
MODELS_CONFIG = {
    "Fish-Speech TTS 模型": {
        "描述": "Fish-Speech 语音克隆模型（英语、中文等多语言）",
        "默认路径": r"d:/ai_editing\fish-speech-win\checkpoints\openaudio-s1-mini",
        "环境变量": "FISH_SPEECH_DIR",
        "必需文件": {
            "firefly-gan-vq-fsq-8x1024-21hz-generator.pth": {
                "类型": "模型权重",
                "最小大小_MB": 100,
                "预期大小_MB": 166,
            },
            "model.pth": {
                "类型": "主模型",
                "最小大小_MB": 500,
                "预期大小_MB": 875,
            },
            "config.json": {
                "类型": "配置文件",
                "最小大小_MB": 0.001,
            },
        },
        "优先级": "高",
        "必需性": "必需（英语、中文TTS）",
    },

    "VITS-TTS-ID 印尼语模型": {
        "描述": "印尼语 TTS 模型（VITS 架构）",
        "默认路径": r"d:/ai_editing\models\vits-tts-id",
        "环境变量": "VITS_TTS_ID_MODEL_DIR",
        "必需文件": {
            "G_100000.pth": {
                "类型": "生成器权重",
                "最小大小_MB": 100,
                "预期大小_MB": 155,
            },
            "config.json": {
                "类型": "配置文件",
                "最小大小_MB": 0.001,
            },
        },
        "优先级": "中",
        "必需性": "可选（仅印尼语TTS需要）",
    },

    "PyAnnote Speaker Diarization": {
        "描述": "说话人分离模型（自动从 HuggingFace 下载）",
        "缓存路径": "~/.cache/torch/pyannote",
        "HuggingFace模型": [
            "pyannote/speaker-diarization-3.1",
            "pyannote/segmentation-3.0",
            "speechbrain/spkrec-ecapa-voxceleb",
        ],
        "优先级": "高",
        "必需性": "必需（说话人识别）",
        "说明": "首次运行时会自动下载，需要 HuggingFace Token",
    },

    "Silero VAD 模型": {
        "描述": "语音活动检测模型（可选，用于音频优化）",
        "可能路径": [
            r"d:/ai_editing\silero-vad",
            "../../silero-vad",
        ],
        "优先级": "低",
        "必需性": "可选（音频优化功能）",
        "说明": "用于 VAD 去除静音，不影响核心功能",
    },
}

def check_file_exists(file_path: Path, expected_size_mb: float = None, min_size_mb: float = None) -> Tuple[bool, str, int]:
    """
    检查文件是否存在且大小合理

    Returns:
        (是否通过, 状态信息, 文件大小)
    """
    if not file_path.exists():
        return False, "文件不存在", 0

    if not file_path.is_file():
        return False, "不是文件", 0

    size = file_path.stat().st_size
    size_mb = size / (1024 * 1024)

    # 检查最小大小
    if min_size_mb and size_mb < min_size_mb:
        return False, f"文件过小 ({format_size(size)}, 最小 {min_size_mb:.1f} MB)", size

    # 检查预期大小（允许±20%）
    if expected_size_mb:
        if size_mb < expected_size_mb * 0.8:
            return False, f"文件可能不完整 ({format_size(size)}, 预期 ~{expected_size_mb:.1f} MB)", size
        elif size_mb > expected_size_mb * 1.2:
            return True, f"文件偏大 ({format_size(size)}, 预期 ~{expected_size_mb:.1f} MB)", size

    return True, f"大小正常 ({format_size(size)})", size

def verify_model(model_name: str, model_config: Dict) -> Tuple[bool, List[str]]:
    """
    验证单个模型

    Returns:
        (是否通过, 问题列表)
    """
    print(f"\n{Colors.BOLD}[{model_name}]{Colors.RESET}")
    print(f"  {model_config['描述']}")
    print(f"  必需性: {model_config['必需性']}")
    print(f"  优先级: {model_config['优先级']}")

    issues = []
    all_passed = True

    # 检查路径
    default_path = model_config.get("默认路径")
    cache_path = model_config.get("缓存路径")
    possible_paths = model_config.get("可能路径", [])

    if default_path:
        model_path = Path(default_path).expanduser()
        print(f"\n  检查路径: {model_path}")

        if not model_path.exists():
            all_passed = False
            print_error(f"  模型目录不存在")
            issues.append(f"{model_name}: 目录不存在 ({model_path})")

            # 提示环境变量
            env_var = model_config.get("环境变量")
            if env_var:
                print_info(f"  可以设置环境变量 {env_var} 指定模型路径")
        else:
            print_success(f"  模型目录存在")

            # 检查必需文件
            if "必需文件" in model_config:
                print(f"\n  {Colors.BOLD}检查必需文件:{Colors.RESET}")

                for file_name, file_info in model_config["必需文件"].items():
                    file_path = model_path / file_name
                    min_size = file_info.get("最小大小_MB")
                    expected_size = file_info.get("预期大小_MB")

                    passed, status, size = check_file_exists(file_path, expected_size, min_size)

                    if passed:
                        print_success(f"  {file_name} - {status}")
                    else:
                        all_passed = False
                        print_error(f"  {file_name} - {status}")
                        issues.append(f"{model_name}: {file_name} {status}")

    elif cache_path:
        cache_dir = Path(cache_path).expanduser()
        print(f"\n  缓存路径: {cache_dir}")

        if cache_dir.exists():
            # 计算缓存大小
            total_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
            print_success(f"  缓存目录存在 (总大小: {format_size(total_size)})")

            # 列出 HuggingFace 模型
            if "HuggingFace模型" in model_config:
                print(f"\n  {Colors.BOLD}需要的 HuggingFace 模型:{Colors.RESET}")
                for hf_model in model_config["HuggingFace模型"]:
                    print_info(f"  - {hf_model}")
                print_warning(f"  首次运行时会自动下载，需要 HuggingFace Token")
        else:
            print_warning(f"  缓存目录不存在（首次运行时会创建）")
            issues.append(f"{model_name}: 缓存未初始化（不影响首次运行）")

    elif possible_paths:
        found_any = False
        for path_str in possible_paths:
            path = Path(path_str).expanduser()
            if path.exists():
                print_success(f"  找到: {path}")
                found_any = True
                break

        if not found_any:
            print_warning(f"  未找到模型（{model_config.get('说明', '')}）")
            if model_config.get("优先级") == "高":
                all_passed = False
                issues.append(f"{model_name}: 未找到")

    # 特殊说明
    if "说明" in model_config:
        print(f"\n  {Colors.YELLOW}说明: {model_config['说明']}{Colors.RESET}")

    return all_passed, issues

def generate_download_instructions(issues: List[str]):
    """生成下载指引"""
    print_header("模型下载指引")

    print(f"{Colors.BOLD}1. Fish-Speech 模型{Colors.RESET}")
    print("   下载地址: https://huggingface.co/fishaudio/fish-speech-1.5")
    print("   或使用: git clone https://huggingface.co/fishaudio/fish-speech-1.5")
    print(f"   放置位置: {Colors.BLUE}C:\\workspace\\ai_editing\\fish-speech-win\\checkpoints\\openaudio-s1-mini{Colors.RESET}")

    print(f"\n{Colors.BOLD}2. VITS-TTS-ID 印尼语模型{Colors.RESET}")
    print("   下载地址: https://huggingface.co/bookbot/vits-tts-id")
    print("   或使用: git lfs clone https://huggingface.co/bookbot/vits-tts-id")
    print(f"   放置位置: {Colors.BLUE}C:\\workspace\\ai_editing\\models\\vits-tts-id{Colors.RESET}")

    print(f"\n{Colors.BOLD}3. PyAnnote 模型（自动下载）{Colors.RESET}")
    print("   需要 HuggingFace Token:")
    print("   1. 访问 https://huggingface.co/settings/tokens")
    print("   2. 创建 Access Token (read 权限)")
    print("   3. 设置环境变量:")
    print(f"      {Colors.BLUE}set HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxx{Colors.RESET}")
    print("   4. 接受模型许可:")
    print("      - https://huggingface.co/pyannote/speaker-diarization-3.1")
    print("      - https://huggingface.co/pyannote/segmentation-3.0")

    print(f"\n{Colors.BOLD}4. Silero VAD（可选）{Colors.RESET}")
    print("   下载地址: https://github.com/snakers4/silero-vad")
    print("   或使用: git clone https://github.com/snakers4/silero-vad.git")
    print(f"   放置位置: {Colors.BLUE}C:\\workspace\\ai_editing\\silero-vad{Colors.RESET}")

def verify_models_size_summary():
    """显示模型总大小估算"""
    print_header("模型大小估算")

    total_size_gb = 0

    print(f"{Colors.BOLD}必需模型:{Colors.RESET}")
    print(f"  - Fish-Speech TTS: ~1.0 GB")
    total_size_gb += 1.0

    print(f"\n{Colors.BOLD}可选模型:{Colors.RESET}")
    print(f"  - VITS-TTS-ID (印尼语): ~155 MB")
    print(f"  - Silero VAD: ~5 MB")

    print(f"\n{Colors.BOLD}自动下载模型 (PyAnnote):{Colors.RESET}")
    print(f"  - speaker-diarization-3.1: ~500 MB")
    print(f"  - segmentation-3.0: ~200 MB")
    print(f"  - spkrec-ecapa-voxceleb: ~50 MB")
    total_size_gb += 0.75

    print(f"\n{Colors.BOLD}总计:{Colors.RESET}")
    print(f"  必需: ~{total_size_gb:.2f} GB")
    print(f"  可选: ~0.16 GB")
    print(f"  总计: ~{total_size_gb + 0.16:.2f} GB")

def main():
    """主函数"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║            LocalClip Editor 模型验证脚本                           ║")
    print("║                     Model Verification                             ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    # 显示模型大小估算
    verify_models_size_summary()

    # 验证所有模型
    all_issues = []
    critical_missing = False

    for model_name, model_config in MODELS_CONFIG.items():
        passed, issues = verify_model(model_name, model_config)
        all_issues.extend(issues)

        if not passed and model_config.get("优先级") == "高":
            critical_missing = True

    # 生成摘要
    print_header("验证摘要")

    if not all_issues:
        print_success("所有模型检查通过！")
        return 0
    else:
        print(f"\n{Colors.BOLD}发现 {len(all_issues)} 个问题:{Colors.RESET}")
        for issue in all_issues:
            print(f"  - {issue}")

        if critical_missing:
            print_error("\n关键模型缺失！请下载必需的模型")
            generate_download_instructions(all_issues)
            return 1
        else:
            print_warning("\n可选模型缺失，不影响核心功能")
            return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}用户中断{Colors.RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
