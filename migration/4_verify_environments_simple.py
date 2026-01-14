#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor Conda Environment Verification Script (Simplified for Windows GBK)
"""

import subprocess
import sys
import json
from pathlib import Path

# Define environments to verify
ENVIRONMENTS = {
    "ui": {
        "description": "Main UI Backend Environment",
        "required": True,
        "python_version": "3.11",
        "critical_packages": [
            "fastapi",
            "uvicorn",
            "torch",
            "pyannote-audio",
            "librosa",
            "soundfile",
        ],
        "import_tests": [
            "import fastapi",
            "import uvicorn",
            "import torch",
            "import pyannote.audio",
            "import librosa",
            "import soundfile",
            "import moviepy.editor",
        ],
    },
    "fish-speech": {
        "description": "Fish-Speech TTS Environment",
        "required": True,
        "python_version": "3.10",
        "critical_packages": [
            "torch",
            "transformers",
        ],
        "import_tests": [
            "import torch",
            "import torchaudio",
            "import transformers",
            "import fish_speech",
        ],
    },
    "tts-id-py311": {
        "description": "Indonesian TTS Environment",
        "required": False,
        "python_version": "3.11",
        "critical_packages": [
            "torch",
            "librosa",
        ],
        "import_tests": [
            "import torch",
            "import librosa",
            "import soundfile",
        ],
    },
}

def run_command(cmd):
    """Execute command and return success status and output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except FileNotFoundError:
        return False, "Command not found"

def check_conda():
    """Check if conda is available"""
    print("=" * 70)
    print("Checking conda installation...")
    print("=" * 70)

    success, output = run_command(["conda", "--version"])
    if success:
        print(f"[OK] conda found: {output.strip()}")
        return True
    else:
        print("[ERROR] conda not found in PATH")
        return False

def check_env_exists(env_name):
    """Check if conda environment exists"""
    success, output = run_command(["conda", "env", "list"])
    if not success:
        return False

    for line in output.split('\n'):
        if line.strip() and not line.startswith('#'):
            parts = line.split()
            if parts and parts[0] == env_name:
                return True
    return False

def get_python_version(env_name):
    """Get Python version in environment"""
    success, output = run_command([
        "conda", "run", "-n", env_name,
        "python", "--version"
    ])
    if success:
        return output.strip()
    return "Unknown"

def get_installed_packages(env_name):
    """Get installed packages in environment"""
    success, output = run_command([
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

def test_import(env_name, import_stmt):
    """Test if import statement works"""
    success, _ = run_command([
        "conda", "run", "-n", env_name,
        "python", "-c", import_stmt
    ])
    return success

def verify_environment(env_name, config):
    """Verify single environment"""
    print(f"\n{'=' * 70}")
    print(f"Environment: {env_name}")
    print(f"Description: {config['description']}")
    print(f"Required: {'Yes' if config['required'] else 'No (Optional)'}")
    print('=' * 70)

    all_passed = True

    # Check existence
    print(f"\n[1/4] Checking if environment exists...")
    if not check_env_exists(env_name):
        print(f"[ERROR] Environment '{env_name}' does not exist!")
        return False
    print(f"[OK] Environment exists")

    # Check Python version
    print(f"\n[2/4] Checking Python version...")
    python_version = get_python_version(env_name)
    print(f"[INFO] {python_version}")
    if config['python_version'] in python_version:
        print(f"[OK] Python version matches (expected: {config['python_version']})")
    else:
        print(f"[WARNING] Python version mismatch (expected: {config['python_version']})")

    # Check packages
    print(f"\n[3/4] Checking critical packages...")
    packages = get_installed_packages(env_name)

    missing_packages = []
    for pkg_name in config['critical_packages']:
        if pkg_name in packages:
            print(f"[OK] {pkg_name}: {packages[pkg_name]}")
        else:
            print(f"[ERROR] {pkg_name}: NOT INSTALLED")
            missing_packages.append(pkg_name)
            all_passed = False

    # Test imports
    print(f"\n[4/4] Testing module imports...")
    failed_imports = []
    for import_stmt in config['import_tests']:
        module_name = import_stmt.split()[1].split('.')[0]
        if test_import(env_name, import_stmt):
            print(f"[OK] {module_name}")
        else:
            print(f"[ERROR] {module_name} - Import failed")
            failed_imports.append(module_name)
            all_passed = False

    return all_passed

def check_cuda():
    """Check CUDA availability"""
    print(f"\n{'=' * 70}")
    print("CUDA Availability Check")
    print('=' * 70)

    print("\n[PyTorch CUDA Check - ui environment]")
    success, output = run_command([
        "conda", "run", "-n", "ui",
        "python", "-c",
        "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); "
        "print(f'CUDA Version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}'); "
        "print(f'Device Count: {torch.cuda.device_count()}'); "
        "print(f'Device Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
    ])

    if success:
        print(output)
    else:
        print("[ERROR] Failed to check CUDA")
        print(output)

def main():
    """Main function"""
    print("\n" + "=" * 70)
    print("LocalClip Editor - Environment Verification Script")
    print("=" * 70 + "\n")

    # Check conda
    if not check_conda():
        return 1

    # Verify all environments
    results = {}
    for env_name, config in ENVIRONMENTS.items():
        passed = verify_environment(env_name, config)
        results[env_name] = {
            "passed": passed,
            "required": config["required"]
        }

    # Check CUDA
    check_cuda()

    # Summary
    print(f"\n{'=' * 70}")
    print("VERIFICATION SUMMARY")
    print('=' * 70)

    total = len(results)
    passed = sum(1 for r in results.values() if r["passed"])
    failed = total - passed

    print(f"\nTotal Environments: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed Environments:")
        for env_name, result in results.items():
            if not result["passed"]:
                req_status = "REQUIRED" if result["required"] else "Optional"
                print(f"  - {env_name} ({req_status})")

        # Check if any required environment failed
        critical_failed = any(
            not result["passed"] and result["required"]
            for result in results.values()
        )

        if critical_failed:
            print("\n[ERROR] Critical environment verification failed!")
            print("The application may not work properly.")
            return 1
        else:
            print("\n[WARNING] Optional environment verification failed.")
            print("Core functionality should still work.")
            return 0
    else:
        print("\n[SUCCESS] All environments verified successfully!")
        print("\nNext steps:")
        print("  1. Install frontend dependencies: cd frontend && npm install")
        print("  2. Configure environment variables")
        print("  3. Run start.bat to launch the application")
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] User cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
