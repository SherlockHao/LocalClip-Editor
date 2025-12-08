#!/usr/bin/env python3
"""
前端构建脚本
用于构建 React 前端为静态文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_node_npm():
    """检查 Node.js 和 npm 是否已安装"""
    print("🔍 检查 Node.js 和 npm...")

    try:
        # 检查 node
        node_version = subprocess.check_output(["node", "--version"], stderr=subprocess.STDOUT, text=True).strip()
        print(f"   ✅ Node.js: {node_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ❌ 未找到 Node.js！")
        print("   请安装 Node.js: https://nodejs.org/")
        return False

    try:
        # 检查 npm
        npm_version = subprocess.check_output(["npm", "--version"], stderr=subprocess.STDOUT, text=True).strip()
        print(f"   ✅ npm: v{npm_version}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ❌ 未找到 npm！")
        return False

    return True


def install_dependencies(frontend_dir: Path):
    """安装前端依赖"""
    print("\n📦 安装前端依赖...")

    if not (frontend_dir / "package.json").exists():
        print(f"   ❌ 未找到 package.json: {frontend_dir}")
        return False

    try:
        # 切换到前端目录
        original_dir = os.getcwd()
        os.chdir(frontend_dir)

        # 运行 npm install
        print("   ⏳ 运行 npm install...")
        subprocess.run(
            ["npm", "install"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("   ✅ 依赖安装完成！")
        return True

    except subprocess.CalledProcessError as e:
        print(f"   ❌ 依赖安装失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False
    finally:
        os.chdir(original_dir)


def build_frontend(frontend_dir: Path):
    """构建前端"""
    print("\n🔨 构建前端...")

    try:
        # 切换到前端目录
        original_dir = os.getcwd()
        os.chdir(frontend_dir)

        # 运行 npm run build
        print("   ⏳ 运行 npm run build...")
        result = subprocess.run(
            ["npm", "run", "build"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print("   ✅ 前端构建完成！")

        # 检查构建输出
        dist_dir = frontend_dir / "dist"
        if not dist_dir.exists():
            print(f"   ❌ 未找到构建输出目录: {dist_dir}")
            return False

        # 统计文件
        files = list(dist_dir.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        total_size = sum(f.stat().st_size for f in files if f.is_file())

        print(f"   📊 构建统计:")
        print(f"      文件数: {file_count}")
        print(f"      总大小: {total_size / 1024 / 1024:.2f} MB")
        print(f"      输出目录: {dist_dir.absolute()}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"   ❌ 前端构建失败: {e}")
        print(f"   错误输出: {e.stderr}")
        return False
    finally:
        os.chdir(original_dir)


def modify_backend_for_static_frontend(backend_dir: Path):
    """
    修改后端代码以支持静态前端文件服务
    在 main.py 中添加静态文件挂载
    """
    print("\n🔧 修改后端以支持静态文件服务...")

    main_py = backend_dir / "main.py"
    if not main_py.exists():
        print(f"   ❌ 未找到 main.py: {main_py}")
        return False

    # 读取文件内容
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已经添加过静态文件支持
    if "StaticFiles" in content and "mount" in content:
        print("   ℹ️  静态文件支持已存在，跳过修改")
        return True

    # 在导入部分添加 StaticFiles
    if "from fastapi import FastAPI" in content:
        content = content.replace(
            "from fastapi import FastAPI",
            "from fastapi import FastAPI\nfrom fastapi.staticfiles import StaticFiles\nfrom fastapi.responses import FileResponse"
        )

    # 在 app 创建后添加静态文件挂载
    # 查找 app = FastAPI() 的位置
    if 'app = FastAPI(' in content:
        # 找到 app 定义后的位置，添加静态文件配置
        insert_code = '''
# 静态文件服务（打包环境）
from package_utils import PathConfig
path_config = PathConfig()

# 挂载前端静态文件
if path_config.frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(path_config.frontend_dist / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        """提供前端入口页面"""
        index_file = path_config.frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "LocalClip Editor API"}
'''

        # 找到合适的插入位置（在 CORS 中间件之后）
        if "app.add_middleware(CORSMiddleware" in content:
            # 在 CORS 配置后插入
            cors_end = content.find(")", content.find("app.add_middleware(CORSMiddleware"))
            cors_end = content.find("\n", cors_end) + 1
            content = content[:cors_end] + insert_code + content[cors_end:]
        else:
            # 否则在 app 创建后立即插入
            app_line = content.find("app = FastAPI(")
            app_line_end = content.find("\n", app_line) + 1
            content = content[:app_line_end] + insert_code + content[app_line_end:]

    # 写回文件
    with open(main_py, 'w', encoding='utf-8') as f:
        f.write(content)

    print("   ✅ 后端修改完成！")
    return True


def clean_build(frontend_dir: Path):
    """清理前端构建输出"""
    print("\n🧹 清理旧的构建文件...")

    dist_dir = frontend_dir / "dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
        print("   ✅ 清理完成！")
    else:
        print("   ℹ️  无需清理")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="LocalClip Editor 前端构建工具")
    parser.add_argument("--frontend-dir", default="../frontend", help="前端目录路径")
    parser.add_argument("--backend-dir", default="../backend", help="后端目录路径")
    parser.add_argument("--skip-install", action="store_true", help="跳过依赖安装")
    parser.add_argument("--skip-modify-backend", action="store_true", help="跳过后端修改")
    parser.add_argument("--clean", action="store_true", help="清理旧的构建文件")

    args = parser.parse_args()

    # 解析路径
    script_dir = Path(__file__).parent
    frontend_dir = (script_dir / args.frontend_dir).resolve()
    backend_dir = (script_dir / args.backend_dir).resolve()

    print("=" * 60)
    print("🎨 LocalClip Editor 前端构建工具")
    print("=" * 60)
    print(f"前端目录: {frontend_dir}")
    print(f"后端目录: {backend_dir}")
    print("=" * 60)

    # 检查目录是否存在
    if not frontend_dir.exists():
        print(f"❌ 前端目录不存在: {frontend_dir}")
        sys.exit(1)

    if not backend_dir.exists():
        print(f"❌ 后端目录不存在: {backend_dir}")
        sys.exit(1)

    # 检查 Node.js 和 npm
    if not check_node_npm():
        sys.exit(1)

    # 清理旧文件
    if args.clean:
        clean_build(frontend_dir)

    # 安装依赖
    if not args.skip_install:
        if not install_dependencies(frontend_dir):
            sys.exit(1)

    # 构建前端
    if not build_frontend(frontend_dir):
        sys.exit(1)

    # 修改后端
    if not args.skip_modify_backend:
        if not modify_backend_for_static_frontend(backend_dir):
            print("   ⚠️  后端修改失败，但前端构建成功")

    print("\n" + "=" * 60)
    print("✅ 前端构建完成！")
    print("=" * 60)
    print(f"📦 构建输出: {frontend_dir / 'dist'}")
    print("🚀 可以开始打包后端了")


if __name__ == "__main__":
    main()