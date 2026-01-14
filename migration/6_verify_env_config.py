#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor Environment Variable Configuration Verification
Verifies that all required environment variables are properly configured
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def print_header(text):
    """Print section header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def check_env_file():
    """Check if .env file exists"""
    print_header("Checking .env File")

    project_root = Path("d:/ai_editing/workspace/LocalClip-Editor")
    env_file = project_root / ".env"

    if not env_file.exists():
        print(f"[ERROR] .env file not found: {env_file}")
        print("\nPlease create .env file with required configuration.")
        return False, None

    print(f"[OK] .env file found: {env_file}")

    # Get file size
    size = env_file.stat().st_size
    print(f"[INFO] File size: {size} bytes")

    # Load the .env file
    load_dotenv(env_file)
    print(f"[OK] .env file loaded successfully")

    return True, env_file

def check_required_vars():
    """Check required environment variables"""
    print_header("Checking Required Environment Variables")

    required_vars = {
        "FISH_SPEECH_DIR": {
            "description": "Fish-Speech repository directory",
            "example": "d:/ai_editing/fish-speech-win",
            "critical": True,
        },
        "FISH_SPEECH_PYTHON": {
            "description": "Fish-Speech Python interpreter",
            "example": "C:\\Miniconda3\\envs\\fish-speech\\python.exe",
            "critical": True,
        },
        "HUGGINGFACE_TOKEN": {
            "description": "HuggingFace access token for PyAnnote",
            "example": "hf_xxxxxxxxxxxxxxxxxxxx",
            "critical": True,
        },
    }

    results = {}
    all_ok = True

    for var_name, var_info in required_vars.items():
        value = os.getenv(var_name)

        print(f"\n[{var_name}]")
        print(f"  Description: {var_info['description']}")

        if value is None:
            print(f"  [ERROR] NOT SET")
            print(f"  Example: {var_info['example']}")
            results[var_name] = {"set": False, "valid": False, "value": None}
            all_ok = False
        elif value == "hf_your_token_here" or value.strip() == "":
            print(f"  [WARNING] Set but using placeholder value")
            print(f"  Current: {value}")
            print(f"  Please replace with actual value")
            results[var_name] = {"set": True, "valid": False, "value": value}
            if var_info["critical"]:
                all_ok = False
        else:
            print(f"  [OK] Set: {value}")
            results[var_name] = {"set": True, "valid": True, "value": value}

    return all_ok, results

def check_optional_vars():
    """Check optional environment variables"""
    print_header("Checking Optional Environment Variables")

    optional_vars = {
        "TTS_ID_PYTHON": {
            "description": "Indonesian TTS Python interpreter",
            "example": "C:\\Miniconda3\\envs\\tts-id-py311\\python.exe",
        },
        "VITS_TTS_ID_MODEL_DIR": {
            "description": "VITS Indonesian TTS model directory",
            "example": "d:/ai_editing/models/vits-tts-id",
        },
        "FISH_MULTIPROCESS_MODE": {
            "description": "Enable multiprocess mode (requires >=16GB VRAM)",
            "example": "false",
        },
    }

    results = {}

    for var_name, var_info in optional_vars.items():
        value = os.getenv(var_name)

        print(f"\n[{var_name}]")
        print(f"  Description: {var_info['description']}")

        if value is None:
            print(f"  [INFO] Not set (optional)")
            results[var_name] = {"set": False, "value": None}
        else:
            print(f"  [OK] Set: {value}")
            results[var_name] = {"set": True, "value": value}

    return results

def validate_paths():
    """Validate that configured paths exist"""
    print_header("Validating Configured Paths")

    path_vars = [
        ("FISH_SPEECH_DIR", "directory"),
        ("FISH_SPEECH_PYTHON", "file"),
        ("TTS_ID_PYTHON", "file"),
        ("VITS_TTS_ID_MODEL_DIR", "directory"),
    ]

    all_valid = True

    for var_name, path_type in path_vars:
        value = os.getenv(var_name)

        if value is None:
            continue

        print(f"\n[{var_name}]")
        print(f"  Path: {value}")

        path = Path(value)

        if path_type == "directory":
            if path.exists() and path.is_dir():
                print(f"  [OK] Directory exists")
            else:
                print(f"  [ERROR] Directory not found!")
                all_valid = False
        elif path_type == "file":
            if path.exists() and path.is_file():
                print(f"  [OK] File exists")
            else:
                print(f"  [WARNING] File not found (may cause errors)")
                # Don't fail for optional paths
                if var_name in ["FISH_SPEECH_PYTHON"]:
                    all_valid = False

    return all_valid

def check_huggingface_token():
    """Special validation for HuggingFace token"""
    print_header("HuggingFace Token Validation")

    token = os.getenv("HUGGINGFACE_TOKEN")

    if token is None:
        print("[ERROR] HUGGINGFACE_TOKEN not set")
        print("\nPyAnnote speaker diarization will fail without this token!")
        print("\nHow to get token:")
        print("  1. Visit https://huggingface.co/settings/tokens")
        print("  2. Create new token with READ permission")
        print("  3. Accept model licenses:")
        print("     - https://huggingface.co/pyannote/speaker-diarization-3.1")
        print("     - https://huggingface.co/pyannote/segmentation-3.0")
        print("  4. Set HUGGINGFACE_TOKEN in .env file")
        return False

    if token == "hf_your_token_here":
        print("[ERROR] HUGGINGFACE_TOKEN is still placeholder")
        print(f"Current value: {token}")
        print("\nPlease replace with your actual HuggingFace token!")
        print("See instructions above.")
        return False

    if not token.startswith("hf_"):
        print(f"[WARNING] Token format looks unusual: {token[:10]}...")
        print("HuggingFace tokens usually start with 'hf_'")
        print("Proceeding anyway, but verify this is correct.")
        return True

    # Token looks valid
    print(f"[OK] Token set: {token[:10]}...{token[-4:]}")
    print(f"[INFO] Token length: {len(token)} characters")
    print("\nNote: Token validity will be tested when PyAnnote models are used.")
    print("Make sure you have accepted the model licenses!")

    return True

def generate_summary(env_file_ok, required_ok, paths_ok, token_ok):
    """Generate verification summary"""
    print_header("VERIFICATION SUMMARY")

    checks = [
        (".env file exists", env_file_ok),
        ("Required variables set", required_ok),
        ("Paths valid", paths_ok),
        ("HuggingFace token valid", token_ok),
    ]

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    print(f"\nChecks Passed: {passed}/{total}\n")

    for check_name, result in checks:
        status = "[OK]" if result else "[FAILED]"
        print(f"  {status} {check_name}")

    if passed == total:
        print("\n[SUCCESS] Environment configuration is complete!")
        print("\nNext steps:")
        print("  1. Get HuggingFace token if not done yet")
        print("  2. Test application: cd LocalClip-Editor && start.bat")
        return True
    else:
        print("\n[ERROR] Environment configuration incomplete!")
        print("\nPlease fix the issues above before running the application.")
        return False

def main():
    """Main verification function"""
    print("\n" + "=" * 70)
    print("LocalClip Editor - Environment Configuration Verification")
    print("=" * 70)

    # Check .env file
    env_file_ok, env_file = check_env_file()

    if not env_file_ok:
        return 1

    # Check required variables
    required_ok, required_results = check_required_vars()

    # Check optional variables
    optional_results = check_optional_vars()

    # Validate paths
    paths_ok = validate_paths()

    # Special check for HuggingFace token
    token_ok = check_huggingface_token()

    # Generate summary
    success = generate_summary(env_file_ok, required_ok, paths_ok, token_ok)

    # Print configuration summary
    print_header("CONFIGURATION SUMMARY")

    print("\nRequired Variables:")
    for var, result in required_results.items():
        if result["set"] and result["valid"]:
            value_display = result["value"]
            if var == "HUGGINGFACE_TOKEN" and value_display:
                value_display = f"{value_display[:10]}...{value_display[-4:]}"
            print(f"  [OK] {var:25s} = {value_display}")
        else:
            print(f"  [ERROR] {var:25s} = NOT SET OR INVALID")

    print("\nOptional Variables:")
    for var, result in optional_results.items():
        if result["set"]:
            print(f"  [OK] {var:25s} = {result['value']}")
        else:
            print(f"  [ ]  {var:25s} = (not set)")

    if success:
        return 0
    else:
        return 1

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
