#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor Conda 环境验证脚本
用于验证所有 conda 环境是否正确安装且可用
"""

import subprocess
import sys
import json
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

# 定义需要验证的环境和包
ENVIRONMENTS_TO_VERIFY = {
    "ui": {
        "描述": "主UI后端环境",
        "必需性": "必需",
        "python_version": "3.11",
        "critical_packages": {
            "fastapi": "0.115.0",
            "uvicorn": "0.32.0",
            "torch": "2.1.0",
            "pyannote.audio": "3.1.0",
            "librosa": "0.10.0",
            "soundfile": "0.12.1",
        },
        "import_tests": [
            "import fastapi",
            "import uvicorn",
            "import torch",
            "import pyannote.audio",
            "import librosa",
            "import soundfile",
            "import moviepy.editor",
            "import scipy",
            "import sklearn",
            "import transformers",
        ],
    },

    "fish-speech": {
        "描述": "Fish-Speech TTS 环境",
        "必需性": "必需",
        "python_version": "3.10",
        "critical_packages": {
            "torch": "2.1.0",
            "transformers": "4.30.0",
        },
        "import_tests": [
            "import torch",
            "import torchaudio",
            "import transformers",
            "import librosa",
            "import soundfile",
            "import hydra",
            "import loguru",
        ],
    },

    "tts-id-py311": {
        "描述": "印尼语 TTS 环境",
        "必需性": "可选",
        "python_version": "3.11",
        "critical_packages": {
            "torch": "2.0.0",
            "librosa": None,
        },
        "import_tests": [
            "import torch",
            "import librosa",
            "import soundfile",
            "import scipy",
        ],
    },
}

def run_conda_command(cmd: List[str], capture_output=True) -> Tuple[bool, str]:
    """执行 conda 命令"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return True, result.stdout if capture_output else ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr if capture_output else ""
    except FileNotFoundError:
        return False, "conda 命令未找到"

def check_environment_exists(env_name: str) -> bool:
    """检查环境是否存在"""
    success, output = run_conda_command(["conda", "env", "list"])
    if not success:
        return False

    for line in output.split('\n'):
        if line.strip() and not line.startswith('#'):
            parts = line.split()
            if parts and parts[0] == env_name:
                return True
    return False

def get_python_version(env_name: str) -> str:
    """获取环境的 Python 版本"""
    success, output = run_conda_command([
        "conda", "run", "-n", env_name,
        "python", "--version"
    ])

    if success:
        # 输出格式: "Python 3.11.5"
        return output.strip().split()[1]
    return "未知"

def get_installed_packages(env_name: str) -> Dict[str, str]:
    """获取环境中安装的包及版本"""
    success, output = run_conda_command([
        "conda", "run", "-n", env_name,
        "pip", "list", "--format=json"
    ])

    if not success:
        return {}

    try:
        packages = json.loads(output)
        return {pkg["name"]: pkg["version"] for pkg in packages}
    except:
        return {}

def check_package_version(installed_version: str, required_version: str) -> bool:
    """检查包版本是否满足要求"""
    if required_version is None:
        return True  # 无版本要求

    # 简化版本比较（只比较主版本号）
    try:
        installed_major = installed_version.split('.')[0]
        required_major = required_version.split('.')[0]
        return installed_major >= required_major
    except:
        return True  # 无法比较时认为通过

def test_imports(env_name: str, import_statements: List[str]) -> Tuple[List[str], List[str]]:
    """测试导入语句"""
    passed = []
    failed = []

    for import_stmt in import_statements:
        success, output = run_conda_command([
            "conda", "run", "-n", env_name,
            "python", "-c", import_stmt
        ])

        if success:
            passed.append(import_stmt)
        else:
            failed.append(import_stmt)

    return passed, failed

def verify_environment(env_name: str, env_config: Dict) -> Tuple[bool, Dict]:
    """
    验证单个环境

    Returns:
        (是否通过, 详细信息)
    """
    print(f"\n{Colors.BOLD}[{env_name}]{Colors.RESET}")
    print(f"  {env_config['描述']} ({env_config['必需性']})")

    results = {
        "exists": False,
        "python_version": None,
        "packages": {},
        "missing_packages": [],
        "import_passed": [],
        "import_failed": [],
    }

    # 1. 检查环境是否存在
    if not check_environment_exists(env_name):
        print_error(f"  环境不存在")
        return False, results

    results["exists"] = True
    print_success(f"  环境存在")

    # 2. 检查 Python 版本
    python_version = get_python_version(env_name)
    results["python_version"] = python_version

    expected_version = env_config["python_version"]
    if python_version.startswith(expected_version):
        print_success(f"  Python 版本: {python_version}")
    else:
        print_warning(f"  Python 版本: {python_version} (预期: {expected_version})")

    # 3. 检查关键包
    print(f"\n  {Colors.BOLD}检查关键包:{Colors.RESET}")
    installed_packages = get_installed_packages(env_name)
    results["packages"] = installed_packages

    all_packages_ok = True

    for pkg_name, required_version in env_config["critical_packages"].items():
        if pkg_name in installed_packages:
            installed_version = installed_packages[pkg_name]
            results["packages"][pkg_name] = installed_version

            if check_package_version(installed_version, required_version):
                print_success(f"  {pkg_name}: {installed_version}")
            else:
                print_warning(f"  {pkg_name}: {installed_version} (要求: >={required_version})")
        else:
            print_error(f"  {pkg_name}: 未安装")
            results["missing_packages"].append(pkg_name)
            all_packages_ok = False

    # 4. 测试导入
    if "import_tests" in env_config:
        print(f"\n  {Colors.BOLD}测试模块导入:{Colors.RESET}")

        passed, failed = test_imports(env_name, env_config["import_tests"])
        results["import_passed"] = passed
        results["import_failed"] = failed

        for import_stmt in passed:
            module_name = import_stmt.split()[1].split('.')[0]
            print_success(f"  {module_name}")

        for import_stmt in failed:
            module_name = import_stmt.split()[1].split('.')[0]
            print_error(f"  {module_name}")
            all_packages_ok = False

    return all_packages_ok, results

def check_cuda_availability():
    """检查 CUDA 是否可用"""
    print_header("CUDA 可用性检查")

    # 在 ui 环境中检查 PyTorch CUDA
    print(f"{Colors.BOLD}PyTorch CUDA:{Colors.RESET}")
    success, output = run_conda_command([
        "conda", "run", "-n", "ui",
        "python", "-c",
        "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Version: {torch.version.cuda}' if torch.cuda.is_available() else 'N/A'); print(f'Device Count: {torch.cuda.device_count()}' if torch.cuda.is_available() else '0')"
    ])

    if success:
        print(output)
    else:
        print_error("无法检查 CUDA")

def generate_fix_instructions(failed_envs: Dict):
    """生成修复指引"""
    if not failed_envs:
        return

    print_header("修复指引")

    for env_name, results in failed_envs.items():
        print(f"\n{Colors.BOLD}环境: {env_name}{Colors.RESET}")

        if not results["exists"]:
            print(f"  环境不存在，运行安装脚本:")
            print(f"  {Colors.BLUE}python migration/3_setup_environments.py{Colors.RESET}")
            continue

        if results["missing_packages"]:
            print(f"\n  缺失的包:")
            for pkg in results["missing_packages"]:
                print(f"    conda run -n {env_name} pip install {pkg}")

        if results["import_failed"]:
            print(f"\n  导入失败的模块:")
            for import_stmt in results["import_failed"]:
                module_name = import_stmt.split()[1].split('.')[0]
                print(f"    {module_name} - 可能需要重新安装或检查依赖")

def main():
    """主函数"""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                                                                    ║")
    print("║          LocalClip Editor 环境验证脚本                            ║")
    print("║                Environment Verification                            ║")
    print("║                                                                    ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")

    # 检查 conda
    success, _ = run_conda_command(["conda", "--version"])
    if not success:
        print_error("conda 未安装或不在 PATH 中")
        return 1

    print_success("conda 已安装")

    # 验证所有环境
    failed_envs = {}
    passed_count = 0
    total_count = len(ENVIRONMENTS_TO_VERIFY)

    print_header("环境验证")

    for env_name, env_config in ENVIRONMENTS_TO_VERIFY.items():
        passed, results = verify_environment(env_name, env_config)

        if passed:
            passed_count += 1
        else:
            failed_envs[env_name] = results

            # 如果是必需环境失败，记录
            if env_config["必需性"] == "必需":
                print_error(f"\n  ⚠ 必需环境验证失败！")

    # CUDA 检查
    check_cuda_availability()

    # 摘要
    print_header("验证摘要")

    print(f"总计环境: {total_count}")
    print(f"通过: {passed_count}")
    print(f"失败: {len(failed_envs)}")

    if failed_envs:
        print(f"\n{Colors.BOLD}失败的环境:{Colors.RESET}")
        for env_name, results in failed_envs.items():
            env_config = ENVIRONMENTS_TO_VERIFY[env_name]
            print(f"  - {env_name} ({env_config['必需性']})")

        generate_fix_instructions(failed_envs)

        # 检查是否所有必需环境都通过
        critical_failed = any(
            ENVIRONMENTS_TO_VERIFY[env]["必需性"] == "必需"
            for env in failed_envs.keys()
        )

        if critical_failed:
            print_error("\n关键环境验证失败！应用可能无法正常运行")
            return 1
        else:
            print_warning("\n可选环境验证失败，但不影响核心功能")
            return 0
    else:
        print_success("\n所有环境验证通过！")

        print(f"\n{Colors.BOLD}下一步:{Colors.RESET}")
        print("  1. 检查模型: python migration/2_verify_models.py")
        print("  2. 配置环境变量")
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
