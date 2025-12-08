#!/usr/bin/env python3
"""
LocalClip Editor Windows 打包主脚本
完整的自动化打包流程
"""

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional
import time


class PackageBuilder:
    """Windows 打包构建器"""

    def __init__(self, project_root: Path, fish_speech_path: Optional[Path] = None):
        self.project_root = project_root
        self.package_dir = project_root / "windows_package"
        self.backend_dir = project_root / "backend"
        self.frontend_dir = project_root / "frontend"
        self.dist_dir = self.package_dir / "dist"
        self.fish_speech_path = fish_speech_path

        # 打包输出目录
        self.output_dir = self.dist_dir / "LocalClip-Editor"

        # 统计信息
        self.stats = {
            "start_time": time.time(),
            "steps_completed": 0,
            "total_steps": 7,
            "errors": []
        }

    def print_step(self, step_num: int, title: str):
        """打印步骤标题"""
        print("\n" + "=" * 60)
        print(f"[{step_num}/{self.stats['total_steps']}] {title}")
        print("=" * 60)

    def print_success(self, message: str):
        """打印成功消息"""
        print(f"✅ {message}")

    def print_error(self, message: str):
        """打印错误消息"""
        print(f"❌ {message}")
        self.stats["errors"].append(message)

    def print_warning(self, message: str):
        """打印警告消息"""
        print(f"⚠️  {message}")

    def check_prerequisites(self) -> bool:
        """检查打包前提条件"""
        self.print_step(1, "检查打包前提条件")

        # 检查 Python 版本
        if sys.version_info < (3, 10):
            self.print_error(f"Python 版本过低: {sys.version}")
            self.print_error("需要 Python 3.10+")
            return False
        self.print_success(f"Python 版本: {sys.version}")

        # 检查必要的 Python 包
        required_packages = [
            "pyinstaller",
            "fastapi",
            "uvicorn",
            "torch",
            "transformers",
            "pyannote.audio",
            "moviepy",
            "huggingface_hub"
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace("-", "_").split(".")[0])
                self.print_success(f"✓ {package}")
            except ImportError:
                missing_packages.append(package)
                self.print_error(f"✗ {package}")

        if missing_packages:
            self.print_error("缺少必要的 Python 包")
            print("\n请安装缺失的包:")
            print(f"  pip install {' '.join(missing_packages)}")
            return False

        # 检查 Node.js 和 npm
        try:
            subprocess.run(["node", "--version"], check=True, capture_output=True)
            subprocess.run(["npm", "--version"], check=True, capture_output=True)
            self.print_success("Node.js 和 npm 已安装")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.print_error("未找到 Node.js 或 npm")
            return False

        # 检查目录结构
        if not self.backend_dir.exists():
            self.print_error(f"后端目录不存在: {self.backend_dir}")
            return False

        if not self.frontend_dir.exists():
            self.print_error(f"前端目录不存在: {self.frontend_dir}")
            return False

        self.print_success("所有前提条件检查通过")
        return True

    def download_models(self) -> bool:
        """下载 AI 模型"""
        self.print_step(2, "下载 AI 模型和依赖")

        download_script = self.package_dir / "download_models.py"

        if not download_script.exists():
            self.print_error(f"未找到下载脚本: {download_script}")
            return False

        try:
            # 运行模型下载脚本
            cmd = [
                sys.executable,
                str(download_script),
                "--models-dir", str(self.dist_dir / "models"),
            ]

            if self.fish_speech_path:
                cmd.extend(["--fish-speech-path", str(self.fish_speech_path)])

            result = subprocess.run(
                cmd,
                check=True,
                capture_output=False,
                text=True
            )

            self.print_success("模型下载完成")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"模型下载失败: {e}")
            return False

    def build_frontend(self) -> bool:
        """构建前端"""
        self.print_step(3, "构建前端")

        build_script = self.package_dir / "build_frontend.py"

        if not build_script.exists():
            self.print_error(f"未找到前端构建脚本: {build_script}")
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(build_script),
                 "--frontend-dir", str(self.frontend_dir),
                 "--backend-dir", str(self.backend_dir)],
                check=True,
                capture_output=False,
                text=True
            )

            # 检查构建输出
            dist_dir = self.frontend_dir / "dist"
            if not dist_dir.exists():
                self.print_error("前端构建输出目录不存在")
                return False

            self.print_success("前端构建完成")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"前端构建失败: {e}")
            return False

    def build_backend(self) -> bool:
        """使用 PyInstaller 打包后端"""
        self.print_step(4, "打包后端 (PyInstaller)")

        spec_file = self.package_dir / "localclip_editor.spec"

        if not spec_file.exists():
            self.print_error(f"未找到 spec 文件: {spec_file}")
            return False

        try:
            # 清理旧的构建文件
            build_dir = self.package_dir / "build"
            if build_dir.exists():
                print("清理旧的构建文件...")
                shutil.rmtree(build_dir)

            old_dist = self.package_dir / "dist" / "LocalClipEditor"
            if old_dist.exists():
                print("清理旧的打包输出...")
                shutil.rmtree(old_dist)

            # 运行 PyInstaller
            print("运行 PyInstaller（这可能需要 10-30 分钟）...")
            result = subprocess.run(
                ["pyinstaller", "--clean", str(spec_file)],
                cwd=str(self.package_dir),
                check=True,
                capture_output=False,
                text=True
            )

            # 检查输出
            backend_exe = old_dist / "LocalClipEditor.exe"
            if not backend_exe.exists():
                self.print_error(f"后端打包失败，未找到 exe 文件")
                return False

            self.print_success("后端打包完成")
            return True

        except subprocess.CalledProcessError as e:
            self.print_error(f"PyInstaller 打包失败: {e}")
            return False

    def assemble_package(self) -> bool:
        """组装最终包"""
        self.print_step(5, "组装最终包")

        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 1. 复制后端
            print("📦 复制后端...")
            backend_build = self.package_dir / "dist" / "LocalClipEditor"
            if backend_build.exists():
                backend_target = self.output_dir / "backend"
                if backend_target.exists():
                    shutil.rmtree(backend_target)
                shutil.copytree(backend_build, backend_target)
                self.print_success(f"后端: {backend_target}")
            else:
                self.print_error("后端构建不存在")
                return False

            # 2. 复制前端
            print("📦 复制前端...")
            frontend_dist = self.frontend_dir / "dist"
            if frontend_dist.exists():
                frontend_target = self.output_dir / "frontend" / "dist"
                frontend_target.parent.mkdir(parents=True, exist_ok=True)
                if frontend_target.exists():
                    shutil.rmtree(frontend_target)
                shutil.copytree(frontend_dist, frontend_target)
                self.print_success(f"前端: {frontend_target}")
            else:
                self.print_warning("前端构建不存在")

            # 3. 复制模型
            print("📦 复制模型...")
            models_source = self.dist_dir / "models"
            if models_source.exists():
                models_target = self.output_dir / "models"
                if models_target.exists():
                    shutil.rmtree(models_target)
                shutil.copytree(models_source, models_target)

                # 计算模型大小
                total_size = sum(f.stat().st_size for f in models_target.rglob("*") if f.is_file())
                self.print_success(f"模型: {models_target} ({total_size / 1024 / 1024 / 1024:.2f} GB)")
            else:
                self.print_warning("模型目录不存在")

            # 4. 复制 FFmpeg
            print("📦 复制 FFmpeg...")
            ffmpeg_source = self.dist_dir.parent / "ffmpeg"
            if ffmpeg_source.exists():
                ffmpeg_target = self.output_dir / "ffmpeg"
                if ffmpeg_target.exists():
                    shutil.rmtree(ffmpeg_target)
                shutil.copytree(ffmpeg_source, ffmpeg_target)
                self.print_success(f"FFmpeg: {ffmpeg_target}")
            else:
                self.print_warning("FFmpeg 不存在")

            # 5. 创建数据目录
            print("📦 创建数据目录...")
            for dir_name in ["uploads", "exports", "audio_segments", "logs"]:
                dir_path = self.output_dir / dir_name
                dir_path.mkdir(exist_ok=True)
                # 创建 .gitkeep 文件
                (dir_path / ".gitkeep").touch()

            # 6. 复制启动脚本
            print("📦 复制启动脚本...")
            start_script_source = self.package_dir / "templates" / "start_windows.bat"
            if start_script_source.exists():
                start_script_target = self.output_dir / "启动 LocalClip Editor.bat"
                shutil.copy2(start_script_source, start_script_target)
                self.print_success(f"启动脚本: {start_script_target}")
            else:
                self.print_warning("启动脚本模板不存在")

            self.print_success("包组装完成")
            return True

        except Exception as e:
            self.print_error(f"包组装失败: {e}")
            return False

    def create_readme(self) -> bool:
        """创建使用说明文档"""
        self.print_step(6, "生成使用文档")

        readme_content = """
╔═══════════════════════════════════════════════════════════════╗
║                LocalClip Editor - Windows 版本                 ║
║                   本地视频编辑和 AI 处理工具                    ║
╚═══════════════════════════════════════════════════════════════╝

📋 版本信息
-----------
版本: 1.0.0
构建日期: {build_date}
支持系统: Windows 10/11 (64位)

📦 包含内容
-----------
✓ LocalClip Editor 后端服务 (FastAPI)
✓ React 前端界面
✓ AI 模型 (说话人识别、性别分类、语音克隆)
✓ FFmpeg 视频处理工具
✓ 完全离线运行，无需联网

🚀 快速开始
-----------
1. 双击 "启动 LocalClip Editor.bat" 启动应用
2. 等待启动完成（约 10-30 秒）
3. 浏览器会自动打开 http://localhost:8000
4. 如果没有自动打开，请手动访问该地址

💡 使用说明
-----------
• 上传视频: 支持 MP4, MOV, AVI, MKV 格式
• 上传字幕: 支持 SRT 格式
• 说话人识别: 自动识别视频中的不同说话人
• 语音克隆: 使用 Fish-Speech 进行语音合成
• 视频导出: 导出编辑后的视频文件

🔧 系统要求
-----------
• 操作系统: Windows 10/11 (64位)
• 内存: 建议 8GB 以上
• 显卡: 支持 CUDA 的 NVIDIA 显卡（可选，用于加速）
• 磁盘空间: 至少 10GB 可用空间

📂 目录结构
-----------
LocalClip-Editor/
├── 启动 LocalClip Editor.bat  # 启动程序
├── backend/                    # 后端服务
├── frontend/                   # 前端界面
├── models/                     # AI 模型
├── ffmpeg/                     # 视频处理工具
├── uploads/                    # 上传文件目录
├── exports/                    # 导出文件目录
├── audio_segments/             # 音频缓存
└── logs/                       # 日志文件

🐛 常见问题
-----------
Q: 启动时提示端口被占用？
A: 关闭其他占用 8000 端口的程序，或重启电脑

Q: 视频处理失败？
A: 检查 ffmpeg 目录是否完整，确保有 ffmpeg.exe

Q: AI 功能无法使用？
A: 检查 models 目录是否完整，确保所有模型文件存在

Q: 浏览器无法打开？
A: 手动在浏览器中访问 http://localhost:8000

📞 技术支持
-----------
• GitHub: https://github.com/your-repo/LocalClip-Editor
• 问题反馈: 请在 GitHub Issues 中提交

⚠️  注意事项
-----------
• 首次启动可能需要较长时间加载模型
• 请勿删除或移动 models 和 ffmpeg 目录
• 建议定期备份 uploads 和 exports 目录中的文件
• 本软件完全离线运行，不会上传任何数据

📄 许可证
---------
本软件遵循 Apache 2.0 许可证

感谢使用 LocalClip Editor！
""".format(build_date=time.strftime("%Y-%m-%d %H:%M:%S"))

        try:
            readme_file = self.output_dir / "使用说明.txt"
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)

            self.print_success(f"使用文档: {readme_file}")
            return True

        except Exception as e:
            self.print_error(f"创建使用文档失败: {e}")
            return False

    def create_archive(self) -> bool:
        """创建压缩包"""
        self.print_step(7, "创建压缩包")

        try:
            # 计算包大小
            total_size = sum(f.stat().st_size for f in self.output_dir.rglob("*") if f.is_file())
            print(f"📊 包总大小: {total_size / 1024 / 1024 / 1024:.2f} GB")

            # 创建 ZIP 压缩包
            archive_name = self.dist_dir / "LocalClip-Editor-Windows-v1.0.0"
            print(f"📦 创建压缩包: {archive_name}.zip")
            print("   这可能需要 5-15 分钟...")

            shutil.make_archive(
                str(archive_name),
                'zip',
                root_dir=str(self.dist_dir),
                base_dir="LocalClip-Editor"
            )

            archive_file = Path(f"{archive_name}.zip")
            archive_size = archive_file.stat().st_size

            self.print_success(f"压缩包创建完成")
            print(f"   📦 文件: {archive_file}")
            print(f"   💾 大小: {archive_size / 1024 / 1024 / 1024:.2f} GB")

            return True

        except Exception as e:
            self.print_error(f"创建压缩包失败: {e}")
            return False

    def print_summary(self):
        """打印构建摘要"""
        elapsed_time = time.time() - self.stats["start_time"]

        print("\n" + "=" * 60)
        print("📊 构建摘要")
        print("=" * 60)
        print(f"总耗时: {elapsed_time / 60:.1f} 分钟")
        print(f"完成步骤: {self.stats['steps_completed']}/{self.stats['total_steps']}")

        if self.stats["errors"]:
            print(f"\n❌ 错误 ({len(self.stats['errors'])}):")
            for error in self.stats["errors"]:
                print(f"   • {error}")
        else:
            print("\n✅ 构建成功，无错误")

        # 输出文件信息
        if self.output_dir.exists():
            total_size = sum(f.stat().st_size for f in self.output_dir.rglob("*") if f.is_file())
            print(f"\n📦 输出目录: {self.output_dir}")
            print(f"💾 总大小: {total_size / 1024 / 1024 / 1024:.2f} GB")

        print("=" * 60)

    def build(self, skip_models: bool = False, skip_frontend: bool = False) -> bool:
        """执行完整的构建流程"""
        print("\n" + "╔" + "═" * 58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "    LocalClip Editor - Windows 打包工具    ".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "═" * 58 + "╝")

        # 1. 检查前提条件
        if not self.check_prerequisites():
            return False
        self.stats["steps_completed"] += 1

        # 2. 下载模型
        if not skip_models:
            if not self.download_models():
                self.print_warning("模型下载失败，继续构建...")
        else:
            print("\n⏭️  跳过模型下载")
        self.stats["steps_completed"] += 1

        # 3. 构建前端
        if not skip_frontend:
            if not self.build_frontend():
                return False
        else:
            print("\n⏭️  跳过前端构建")
        self.stats["steps_completed"] += 1

        # 4. 打包后端
        if not self.build_backend():
            return False
        self.stats["steps_completed"] += 1

        # 5. 组装包
        if not self.assemble_package():
            return False
        self.stats["steps_completed"] += 1

        # 6. 创建文档
        if not self.create_readme():
            self.print_warning("文档创建失败，继续构建...")
        self.stats["steps_completed"] += 1

        # 7. 创建压缩包
        if not self.create_archive():
            self.print_warning("压缩包创建失败，但目录已准备好")
        self.stats["steps_completed"] += 1

        # 打印摘要
        self.print_summary()

        return len(self.stats["errors"]) == 0


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="LocalClip Editor Windows 打包工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整打包
  python build_package.py

  # 跳过模型下载（如果已下载）
  python build_package.py --skip-models

  # 跳过前端构建（如果已构建）
  python build_package.py --skip-frontend

  # 指定 Fish-Speech 路径
  python build_package.py --fish-speech-path /path/to/fish-speech
        """
    )

    parser.add_argument(
        "--fish-speech-path",
        type=Path,
        default=Path("/Users/yiya_workstation/Documents/ai_editing/fish-speech"),
        help="Fish-Speech 项目路径"
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="跳过模型下载"
    )
    parser.add_argument(
        "--skip-frontend",
        action="store_true",
        help="跳过前端构建"
    )

    args = parser.parse_args()

    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 创建构建器并执行
    builder = PackageBuilder(project_root, args.fish_speech_path)
    success = builder.build(
        skip_models=args.skip_models,
        skip_frontend=args.skip_frontend
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()