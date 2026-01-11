#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor 代码结构验证脚本
用于验证所有必要的代码文件和目录是否已正确迁移
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

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

# 定义必需的文件和目录结构
REQUIRED_STRUCTURE = {
    # 启动脚本
    "启动脚本": [
        "start.bat",
        "start.vbs",
    ],

    # 后端核心文件
    "后端核心": [
        "backend/main.py",
        "backend/requirements.txt",
        "backend/fish_simple_cloner.py",
        "backend/fish_batch_generate.py",
        "backend/fish_multiprocess_generate.py",
        "backend/indonesian_tts_cloner.py",
        "backend/audio_optimizer.py",
        "backend/batch_translate_ollama.py",
        "backend/batch_retranslate_ollama.py",
        "backend/text_utils.py",
        "backend/srt_parser.py",
        "backend/platform_utils.py",
    ],

    # 前端核心文件
    "前端核心": [
        "frontend/package.json",
        "frontend/index.html",
        "frontend/vite.config.ts",
        "frontend/tsconfig.json",
        "frontend/tsconfig.app.json",
        "frontend/tsconfig.node.json",
        "frontend/tailwind.config.js",
        "frontend/postcss.config.js",
        "frontend/src/main.tsx",
        "frontend/src/App.tsx",
        "frontend/src/index.css",
        "frontend/src/components/SubtitleDetails.tsx",
    ],

    # 必需的目录
    "必需目录": [
        "backend",
        "frontend",
        "frontend/src",
        "frontend/src/components",
        "frontend/public",
    ],

    # 数据文件
    "数据文件": [
        "backend/digits_mapping.json",
    ],
}

# 外部依赖仓库和脚本（需要单独迁移）
EXTERNAL_DEPENDENCIES = {
    "Fish-Speech 仓库": {
        "Windows默认路径": r"C:\workspace\ai_editing\fish-speech-win",
        "关键文件": [
            "checkpoints/openaudio-s1-mini",  # 模型目录
            "fish_speech",  # Python包
        ],
        "环境变量": "FISH_SPEECH_DIR",
    },

    "VITS-TTS-ID 模型": {
        "Windows默认路径": r"C:\workspace\ai_editing\models\vits-tts-id",
        "关键文件": [
            "config.json",
            "G_100000.pth",  # 模型权重
        ],
        "环境变量": "VITS_TTS_ID_MODEL_DIR",
    },

    "Silero VAD": {
        "可能路径": [
            r"C:\workspace\ai_editing\silero-vad",
            "../silero-vad",  # 相对路径
        ],
        "说明": "可选依赖，用于 VAD 音频优化",
    },
}

def verify_file_exists(base_path: Path, relative_path: str) -> bool:
    """验证文件是否存在"""
    full_path = base_path / relative_path
    return full_path.exists()

def verify_directory_exists(base_path: Path, relative_path: str) -> bool:
    """验证目录是否存在"""
    full_path = base_path / relative_path
    return full_path.is_dir()

def get_file_size(base_path: Path, relative_path: str) -> str:
    """获取文件大小"""
    full_path = base_path / relative_path
    if not full_path.exists():
        return "N/A"

    size = full_path.stat().st_size
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"

def verify_code_structure(base_path: Path) -> Tuple[int, int, List[str]]:
    """
    验证代码结构

    Returns:
        (通过数, 总数, 缺失文件列表)
    """
    print_header("验证代码结构")

    total_checks = 0
    passed_checks = 0
    missing_files = []

    for category, items in REQUIRED_STRUCTURE.items():
        print(f"\n{Colors.BOLD}[{category}]{Colors.RESET}")

        for item in items:
            total_checks += 1

            # 检查是目录还是文件
            if category == "必需目录":
                exists = verify_directory_exists(base_path, item)
                item_type = "目录"
            else:
                exists = verify_file_exists(base_path, item)
                item_type = "文件"

            if exists:
                passed_checks += 1
                size_info = ""
                if item_type == "文件":
                    size = get_file_size(base_path, item)
                    size_info = f" ({size})"
                print_success(f"{item}{size_info}")
            else:
                print_error(f"{item} - {item_type}不存在")
                missing_files.append(item)

    return passed_checks, total_checks, missing_files

def verify_external_dependencies() -> Tuple[int, int]:
    """
    验证外部依赖

    Returns:
        (找到数, 总数)
    """
    print_header("验证外部依赖")

    total_deps = len(EXTERNAL_DEPENDENCIES)
    found_deps = 0

    for dep_name, dep_info in EXTERNAL_DEPENDENCIES.items():
        print(f"\n{Colors.BOLD}[{dep_name}]{Colors.RESET}")

        # 检查默认路径
        default_path = dep_info.get("Windows默认路径")
        if default_path:
            dep_path = Path(default_path)
            if dep_path.exists():
                found_deps += 1
                print_success(f"找到: {default_path}")

                # 检查关键文件
                if "关键文件" in dep_info:
                    for key_file in dep_info["关键文件"]:
                        key_file_path = dep_path / key_file
                        if key_file_path.exists():
                            size = ""
                            if key_file_path.is_file():
                                size_bytes = key_file_path.stat().st_size
                                if size_bytes > 1024 * 1024 * 1024:
                                    size = f" ({size_bytes / (1024**3):.2f} GB)"
                                elif size_bytes > 1024 * 1024:
                                    size = f" ({size_bytes / (1024**2):.2f} MB)"
                            print_success(f"  - {key_file}{size}")
                        else:
                            print_error(f"  - {key_file} 不存在")
            else:
                print_error(f"未找到: {default_path}")
                if "环境变量" in dep_info:
                    print_info(f"  可以设置环境变量: {dep_info['环境变量']}")

        # 检查可能路径
        if "可能路径" in dep_info:
            found_any = False
            for possible_path in dep_info["可能路径"]:
                if Path(possible_path).exists():
                    found_deps += 1
                    found_any = True
                    print_success(f"找到: {possible_path}")
                    break

            if not found_any:
                print_warning(f"{dep_info.get('说明', '未找到')}")

    return found_deps, total_deps

def check_python_imports(base_path: Path):
    """检查关键 Python 文件是否可以导入（语法检查）"""
    print_header("Python 语法检查")

    key_python_files = [
        "backend/main.py",
        "backend/fish_simple_cloner.py",
        "backend/indonesian_tts_cloner.py",
        "backend/audio_optimizer.py",
    ]

    import py_compile

    passed = 0
    total = len(key_python_files)

    for py_file in key_python_files:
        full_path = base_path / py_file
        if not full_path.exists():
            print_error(f"{py_file} - 文件不存在")
            continue

        try:
            py_compile.compile(str(full_path), doraise=True)
            print_success(f"{py_file} - 语法正确")
            passed += 1
        except py_compile.PyCompileError as e:
            print_error(f"{py_file} - 语法错误: {e}")

    return passed, total

def generate_summary_report(
    code_passed: int,
    code_total: int,
    missing_files: List[str],
    deps_found: int,
    deps_total: int,
    syntax_passed: int,
    syntax_total: int
):
    """生成摘要报告"""
    print_header("验证摘要报告")

    # 代码结构
    code_percent = (code_passed / code_total * 100) if code_total > 0 else 0
    print(f"\n{Colors.BOLD}代码结构:{Colors.RESET}")
    print(f"  通过: {code_passed}/{code_total} ({code_percent:.1f}%)")

    if missing_files:
        print(f"\n{Colors.BOLD}缺失文件:{Colors.RESET}")
        for f in missing_files[:10]:  # 最多显示10个
            print(f"  - {f}")
        if len(missing_files) > 10:
            print(f"  ... 还有 {len(missing_files) - 10} 个文件")

    # 外部依赖
    deps_percent = (deps_found / deps_total * 100) if deps_total > 0 else 0
    print(f"\n{Colors.BOLD}外部依赖:{Colors.RESET}")
    print(f"  找到: {deps_found}/{deps_total} ({deps_percent:.1f}%)")

    # Python 语法
    syntax_percent = (syntax_passed / syntax_total * 100) if syntax_total > 0 else 0
    print(f"\n{Colors.BOLD}Python 语法:{Colors.RESET}")
    print(f"  通过: {syntax_passed}/{syntax_total} ({syntax_percent:.1f}%)")

    # 总体评估
    print(f"\n{Colors.BOLD}总体评估:{Colors.RESET}")
    overall_score = (code_percent + deps_percent + syntax_percent) / 3

    if overall_score >= 90:
        print_success(f"优秀！完整度 {overall_score:.1f}% - 可以开始使用")
    elif overall_score >= 70:
        print_warning(f"良好！完整度 {overall_score:.1f}% - 可能需要安装部分依赖")
    elif overall_score >= 50:
        print_warning(f"中等！完整度 {overall_score:.1f}% - 需要补充缺失文件")
    else:
        print_error(f"不完整！完整度 {overall_score:.1f}% - 需要大量补充")

    return overall_score >= 70

def main():
    """主函数"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║          LocalClip Editor 代码结构验证脚本                          ║")
    print("║                     Migration Verification                         ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    # 获取 LocalClip-Editor 根目录
    script_dir = Path(__file__).parent
    base_path = script_dir.parent

    print_info(f"项目根目录: {base_path}")

    if not base_path.exists():
        print_error(f"项目目录不存在: {base_path}")
        return False

    # 1. 验证代码结构
    code_passed, code_total, missing_files = verify_code_structure(base_path)

    # 2. 验证外部依赖
    deps_found, deps_total = verify_external_dependencies()

    # 3. Python 语法检查
    syntax_passed, syntax_total = check_python_imports(base_path)

    # 4. 生成摘要报告
    success = generate_summary_report(
        code_passed, code_total, missing_files,
        deps_found, deps_total,
        syntax_passed, syntax_total
    )

    # 返回状态码
    return 0 if success else 1

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
