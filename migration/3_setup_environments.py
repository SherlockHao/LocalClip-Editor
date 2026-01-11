#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor Conda 环境安装脚本
用于在新机器上创建和配置所有必需的 conda 环境
"""

import subprocess
import sys
import platform
from pathlib import Path

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

# 定义所有需要的 Conda 环境
CONDA_ENVIRONMENTS = {
    "ui": {
        "描述": "主UI后端环境（FastAPI + PyAnnote + 音频处理）",
        "python_version": "3.11",
        "必需性": "必需",
        "优先级": 1,
        "requirements_file": "backend/requirements.txt",
        "pip_packages": [
            "fastapi==0.115.0",
            "uvicorn[standard]==0.32.0",
            "python-multipart==0.0.20",
            "moviepy==1.0.3",
            "Pillow==10.1.0",
            "pydantic==2.10.1",
            "python-dotenv==1.0.0",
            "torch>=2.1.0",
            "pyannote.audio>=3.1.0",
            "huggingface_hub>=0.20.0",
            "scipy>=1.10.0",
            "scikit-learn>=1.3.0",
            "numpy>=1.21.0",
            "librosa>=0.10.0",
            "soundfile>=0.12.1",
            "speechmos>=0.0.1",
            "onnxruntime>=1.23.0",
            "transformers>=4.30.0",
            "protobuf>=5.0.0,<7.0.0",
            "requests",  # Ollama API 调用
        ],
        "conda_packages": [],
        "说明": "核心后端环境，包含所有主要功能",
    },

    "fish-speech": {
        "描述": "Fish-Speech TTS 环境（语音克隆）",
        "python_version": "3.10",
        "必需性": "必需",
        "优先级": 2,
        "pip_packages": [
            "torch>=2.1.0",
            "torchaudio",
            "numpy",
            "scipy",
            "librosa",
            "soundfile",
            "transformers>=4.30.0",
            "accelerate",
            "hydra-core",
            "omegaconf",
            "gradio",
            "loguru",
            "rich",
        ],
        "conda_packages": [],
        "说明": "用于 Fish-Speech 语音克隆，需要与 fish-speech 仓库配合",
        "额外步骤": [
            "cd C:\\workspace\\ai_editing\\fish-speech-win",
            "pip install -e .",  # 安装 fish-speech 包
        ],
    },

    "tts-id-py311": {
        "描述": "印尼语 TTS 环境（VITS-TTS-ID）",
        "python_version": "3.11",
        "必需性": "可选（仅印尼语需要）",
        "优先级": 3,
        "pip_packages": [
            "torch>=2.0.0",
            "numpy",
            "scipy",
            "librosa",
            "soundfile",
            "phonemizer",
            "Cython",
            "monotonic_align",  # VITS 特定
            "unidecode",
        ],
        "conda_packages": ["ffmpeg"],  # phonemizer 需要
        "说明": "印尼语 TTS 专用环境",
    },
}

def run_command(cmd: str, shell=True, check=True, capture_output=False):
    """执行命令"""
    print(f"{Colors.BLUE}> {cmd}{Colors.RESET}")
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            check=check,
            text=True,
            capture_output=capture_output
        )
        if capture_output:
            return result.stdout
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"命令执行失败: {e}")
        if capture_output and e.output:
            print(e.output)
        return False

def check_conda_installed() -> bool:
    """检查 conda 是否已安装"""
    try:
        result = subprocess.run(
            ["conda", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        version = result.stdout.strip()
        print_success(f"Conda 已安装: {version}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_error("Conda 未安装")
        return False

def list_existing_environments():
    """列出现有的 conda 环境"""
    try:
        result = subprocess.run(
            ["conda", "env", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        envs = []
        for line in result.stdout.split('\n'):
            if line and not line.startswith('#'):
                parts = line.split()
                if parts:
                    envs.append(parts[0])
        return envs
    except:
        return []

def create_environment(env_name: str, env_config: dict) -> bool:
    """创建单个 conda 环境"""
    print_header(f"创建环境: {env_name}")

    print_info(f"描述: {env_config['描述']}")
    print_info(f"Python 版本: {env_config['python_version']}")
    print_info(f"必需性: {env_config['必需性']}")

    # 检查环境是否已存在
    existing_envs = list_existing_environments()
    if env_name in existing_envs:
        print_warning(f"环境 '{env_name}' 已存在")
        response = input("是否删除并重新创建? (y/N): ").strip().lower()
        if response == 'y':
            print_info("删除现有环境...")
            if not run_command(f"conda env remove -n {env_name} -y"):
                return False
        else:
            print_info("跳过创建，将尝试安装/更新包")
            return install_packages(env_name, env_config)

    # 创建新环境
    print_info(f"创建新的 conda 环境...")
    python_version = env_config['python_version']

    if not run_command(f"conda create -n {env_name} python={python_version} -y"):
        return False

    print_success(f"环境 '{env_name}' 创建成功")

    # 安装包
    return install_packages(env_name, env_config)

def install_packages(env_name: str, env_config: dict) -> bool:
    """在指定环境中安装包"""
    print_info("安装包...")

    # 获取系统类型
    is_windows = platform.system() == "Windows"
    conda_prefix = "conda activate" if is_windows else "source activate"

    # 先安装 conda 包（如果有）
    if env_config.get("conda_packages"):
        print_info("安装 Conda 包...")
        conda_pkgs = " ".join(env_config["conda_packages"])
        cmd = f"conda install -n {env_name} {conda_pkgs} -y"
        if not run_command(cmd):
            print_warning("部分 Conda 包安装失败，继续...")

    # 安装 pip 包
    if env_config.get("pip_packages"):
        print_info("安装 pip 包...")

        # 使用 requirements 文件（如果存在）
        req_file = env_config.get("requirements_file")
        if req_file:
            script_dir = Path(__file__).parent.parent
            req_path = script_dir / req_file
            if req_path.exists():
                print_info(f"从 {req_file} 安装...")
                cmd = f"conda run -n {env_name} pip install -r {req_path}"
                if not run_command(cmd):
                    print_warning("从 requirements.txt 安装失败，尝试单独安装...")

        # 或者直接安装列表中的包
        for package in env_config["pip_packages"]:
            cmd = f"conda run -n {env_name} pip install {package}"
            if not run_command(cmd):
                print_warning(f"包 '{package}' 安装失败，继续...")

    # 执行额外步骤
    if env_config.get("额外步骤"):
        print_info("执行额外安装步骤...")
        for step in env_config["额外步骤"]:
            print_info(f"执行: {step}")
            # 注意：需要在激活的环境中执行
            if not run_command(step):
                print_warning(f"步骤执行失败: {step}")

    print_success(f"环境 '{env_name}' 配置完成")
    return True

def generate_activation_script():
    """生成环境激活脚本"""
    print_header("生成激活脚本")

    is_windows = platform.system() == "Windows"

    if is_windows:
        script_content = """@echo off
REM LocalClip Editor 环境激活脚本

echo 可用环境:
echo   1. ui            - 主UI后端环境
echo   2. fish-speech   - Fish-Speech TTS 环境
echo   3. tts-id-py311  - 印尼语 TTS 环境

echo.
echo 激活环境示例:
echo   conda activate ui
echo   conda activate fish-speech
echo   conda activate tts-id-py311

echo.
echo 当前环境列表:
conda env list
"""
        script_file = "activate_env.bat"
    else:
        script_content = """#!/bin/bash
# LocalClip Editor 环境激活脚本

echo "可用环境:"
echo "  1. ui            - 主UI后端环境"
echo "  2. fish-speech   - Fish-Speech TTS 环境"
echo "  3. tts-id-py311  - 印尼语 TTS 环境"

echo ""
echo "激活环境示例:"
echo "  conda activate ui"
echo "  conda activate fish-speech"
echo "  conda activate tts-id-py311"

echo ""
echo "当前环境列表:"
conda env list
"""
        script_file = "activate_env.sh"

    script_dir = Path(__file__).parent.parent
    script_path = script_dir / script_file

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    if not is_windows:
        script_path.chmod(0o755)

    print_success(f"激活脚本已生成: {script_path}")

def main():
    """主函数"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║          LocalClip Editor 环境安装脚本                            ║")
    print("║                 Environment Setup Script                           ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    # 检查 conda
    if not check_conda_installed():
        print_error("请先安装 Miniconda 或 Anaconda")
        print_info("下载地址:")
        print_info("  Miniconda: https://docs.conda.io/en/latest/miniconda.html")
        print_info("  Anaconda: https://www.anaconda.com/download")
        return 1

    # 显示将要创建的环境
    print_header("环境规划")
    print(f"{Colors.BOLD}将创建以下环境:{Colors.RESET}\n")

    for env_name, env_config in sorted(CONDA_ENVIRONMENTS.items(), key=lambda x: x[1]['优先级']):
        priority = env_config['优先级']
        necessity = env_config['必需性']
        desc = env_config['描述']

        print(f"{priority}. {Colors.BOLD}{env_name}{Colors.RESET}")
        print(f"   {desc}")
        print(f"   必需性: {necessity}")
        print()

    # 确认
    response = input(f"\n{Colors.YELLOW}是否继续? (Y/n): {Colors.RESET}").strip().lower()
    if response == 'n':
        print_info("用户取消")
        return 0

    # 创建所有环境
    failed_envs = []

    for env_name, env_config in sorted(CONDA_ENVIRONMENTS.items(), key=lambda x: x[1]['优先级']):
        if not create_environment(env_name, env_config):
            failed_envs.append(env_name)

            # 如果是必需环境失败，询问是否继续
            if env_config['必需性'] == "必需":
                response = input(f"\n{Colors.YELLOW}必需环境创建失败，是否继续? (y/N): {Colors.RESET}").strip().lower()
                if response != 'y':
                    print_error("安装中止")
                    return 1

    # 生成激活脚本
    generate_activation_script()

    # 摘要
    print_header("安装摘要")

    total = len(CONDA_ENVIRONMENTS)
    success = total - len(failed_envs)

    print(f"总计环境: {total}")
    print(f"成功: {success}")
    print(f"失败: {len(failed_envs)}")

    if failed_envs:
        print(f"\n{Colors.BOLD}失败的环境:{Colors.RESET}")
        for env in failed_envs:
            print(f"  - {env}")

        return 1
    else:
        print_success("\n所有环境安装成功！")

        print(f"\n{Colors.BOLD}下一步:{Colors.RESET}")
        print("  1. 运行验证脚本: python migration/4_verify_environments.py")
        print("  2. 配置环境变量（参考 MIGRATION_GUIDE.md）")
        print("  3. 运行 start.bat 启动应用")

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
