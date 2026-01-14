#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LocalClip Editor Frontend Installation Verification Script
Verifies that all frontend dependencies are properly installed
"""

import subprocess
import json
from pathlib import Path
import os

def print_header(text):
    """Print section header"""
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)

def check_node_npm():
    """Check if Node.js and npm are installed"""
    print_header("Checking Node.js and npm Installation")

    try:
        # Try to get Node.js version
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        node_version = result.stdout.strip()
        print(f"[OK] Node.js: {node_version}")
    except:
        print("[ERROR] Node.js not found or not in PATH")
        return False

    try:
        # Try to get npm version
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        npm_version = result.stdout.strip()
        print(f"[OK] npm: {npm_version}")
    except:
        print("[ERROR] npm not found or not in PATH")
        return False

    return True

def check_frontend_structure():
    """Check frontend directory structure"""
    print_header("Checking Frontend Directory Structure")

    frontend_dir = Path("d:/ai_editing/workspace/LocalClip-Editor/frontend")

    if not frontend_dir.exists():
        print(f"[ERROR] Frontend directory not found: {frontend_dir}")
        return False

    print(f"[OK] Frontend directory exists: {frontend_dir}")

    # Check key files
    key_files = [
        "package.json",
        "package-lock.json",
        "vite.config.ts",
        "tsconfig.json",
        "index.html",
    ]

    all_exist = True
    for file in key_files:
        file_path = frontend_dir / file
        if file_path.exists():
            print(f"[OK] {file}")
        else:
            print(f"[ERROR] {file} not found")
            all_exist = False

    return all_exist

def check_node_modules():
    """Check if node_modules is installed"""
    print_header("Checking node_modules Installation")

    frontend_dir = Path("d:/ai_editing/workspace/LocalClip-Editor/frontend")
    node_modules = frontend_dir / "node_modules"

    if not node_modules.exists():
        print("[ERROR] node_modules directory not found")
        print("Run: cd frontend && npm install")
        return False

    print(f"[OK] node_modules directory exists")

    # Count packages
    try:
        package_dirs = [d for d in node_modules.iterdir() if d.is_dir() and not d.name.startswith('.')]
        package_count = len(package_dirs)
        print(f"[INFO] Found {package_count} top-level packages")

        # Get total size
        total_size = sum(f.stat().st_size for f in node_modules.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"[INFO] Total size: {size_mb:.1f} MB")
    except Exception as e:
        print(f"[WARNING] Could not analyze node_modules: {e}")

    return True

def check_package_json_dependencies():
    """Verify all package.json dependencies are installed"""
    print_header("Verifying Package Dependencies")

    frontend_dir = Path("d:/ai_editing/workspace/LocalClip-Editor/frontend")
    package_json = frontend_dir / "package.json"
    node_modules = frontend_dir / "node_modules"

    if not package_json.exists():
        print("[ERROR] package.json not found")
        return False

    # Read package.json
    with open(package_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    dependencies = data.get('dependencies', {})
    dev_dependencies = data.get('devDependencies', {})

    print(f"\n[Production Dependencies] ({len(dependencies)} packages)")
    missing_deps = []
    for package in dependencies.keys():
        package_dir = node_modules / package
        if package_dir.exists():
            print(f"  [OK] {package}")
        else:
            print(f"  [ERROR] {package} - NOT INSTALLED")
            missing_deps.append(package)

    print(f"\n[Development Dependencies] ({len(dev_dependencies)} packages)")
    missing_dev_deps = []
    for package in dev_dependencies.keys():
        package_dir = node_modules / package
        if package_dir.exists():
            print(f"  [OK] {package}")
        else:
            print(f"  [ERROR] {package} - NOT INSTALLED")
            missing_dev_deps.append(package)

    if missing_deps or missing_dev_deps:
        print(f"\n[ERROR] Missing packages: {len(missing_deps) + len(missing_dev_deps)}")
        return False

    print(f"\n[SUCCESS] All dependencies installed!")
    return True

def check_critical_packages():
    """Check critical packages for LocalClip Editor"""
    print_header("Checking Critical Packages")

    frontend_dir = Path("d:/ai_editing/workspace/LocalClip-Editor/frontend")
    node_modules = frontend_dir / "node_modules"

    critical_packages = {
        "react": "UI framework",
        "react-dom": "React DOM renderer",
        "vite": "Build tool and dev server",
        "axios": "HTTP client for API calls",
        "tailwindcss": "CSS framework",
        "lucide-react": "Icon library",
        "typescript": "TypeScript compiler",
    }

    all_ok = True
    for package, description in critical_packages.items():
        package_dir = node_modules / package
        if package_dir.exists():
            # Try to get version
            package_json = package_dir / "package.json"
            if package_json.exists():
                try:
                    with open(package_json, 'r', encoding='utf-8') as f:
                        pkg_data = json.load(f)
                        version = pkg_data.get('version', 'unknown')
                        print(f"[OK] {package:20s} {version:15s} - {description}")
                except:
                    print(f"[OK] {package:20s} {'installed':15s} - {description}")
            else:
                print(f"[OK] {package:20s} {'installed':15s} - {description}")
        else:
            print(f"[ERROR] {package:20s} {'NOT INSTALLED':15s} - {description}")
            all_ok = False

    return all_ok

def generate_summary():
    """Generate verification summary"""
    print_header("VERIFICATION SUMMARY")

    frontend_dir = Path("d:/ai_editing/workspace/LocalClip-Editor/frontend")
    package_json = frontend_dir / "package.json"
    node_modules = frontend_dir / "node_modules"

    # Read package.json
    if package_json.exists():
        with open(package_json, 'r', encoding='utf-8') as f:
            data = json.load(f)

        total_deps = len(data.get('dependencies', {}))
        total_dev_deps = len(data.get('devDependencies', {}))

        print(f"\nPackage Information:")
        print(f"  Name: {data.get('name', 'unknown')}")
        print(f"  Version: {data.get('version', 'unknown')}")
        print(f"  Production Dependencies: {total_deps}")
        print(f"  Development Dependencies: {total_dev_deps}")
        print(f"  Total: {total_deps + total_dev_deps}")

    if node_modules.exists():
        package_dirs = [d for d in node_modules.iterdir() if d.is_dir() and not d.name.startswith('.')]
        print(f"\nInstalled Packages:")
        print(f"  Top-level packages: {len(package_dirs)}")

        # Count all package.json files for total packages including nested
        try:
            all_packages = list(node_modules.rglob('package.json'))
            print(f"  Total packages (including nested): {len(all_packages)}")
        except:
            pass

    print("\nNext Steps:")
    print("  1. Test frontend dev server: cd frontend && npm run dev")
    print("  2. Configure environment variables (Phase 6)")
    print("  3. Run full application: start.bat")

def main():
    """Main verification function"""
    print("\n" + "=" * 70)
    print("LocalClip Editor - Frontend Installation Verification")
    print("=" * 70)

    checks = [
        ("Node.js and npm", check_node_npm),
        ("Frontend structure", check_frontend_structure),
        ("node_modules", check_node_modules),
        ("Package dependencies", check_package_json_dependencies),
        ("Critical packages", check_critical_packages),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] {name} check failed with exception: {e}")
            results.append((name, False))

    # Summary
    generate_summary()

    print_header("FINAL RESULT")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nChecks Passed: {passed}/{total}")

    for name, result in results:
        status = "[OK]" if result else "[FAILED]"
        print(f"  {status} {name}")

    if passed == total:
        print("\n[SUCCESS] Frontend installation verified successfully!")
        print("Frontend is ready for development and production.")
        return 0
    else:
        print("\n[ERROR] Some checks failed!")
        print("Please run: cd frontend && npm install")
        return 1

if __name__ == "__main__":
    import sys
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
