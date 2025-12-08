#!/usr/bin/env python3
"""
从本地 HuggingFace 缓存复制模型到打包目录
用于 Windows 打包，避免重复下载
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict


class LocalModelCopier:
    """本地模型复制工具"""

    def __init__(self, target_dir: str = "models"):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)

        # HuggingFace 缓存目录
        self.hf_cache = Path.home() / ".cache" / "huggingface"
        self.hf_hub = self.hf_cache / "hub"

        # 需要复制的模型
        self.models = [
            {
                "name": "pyannote-wespeaker",
                "hub_name": "models--pyannote--wespeaker-voxceleb-resnet34-LM",
                "target_subdir": "pyannote"
            },
            {
                "name": "gender-detection",
                "hub_name": "models--prithivMLmods--Common-Voice-Geneder-Detection",
                "target_subdir": "wav2vec2"
            },
            {
                "name": "pyannote-segmentation",
                "hub_name": "models--pyannote--segmentation",
                "target_subdir": "pyannote"
            }
        ]

    def find_model(self, hub_name: str) -> Path:
        """查找模型在本地缓存中的位置"""
        model_path = self.hf_hub / hub_name

        if not model_path.exists():
            raise FileNotFoundError(
                f"模型未找到: {hub_name}\n"
                f"请先下载模型或检查路径: {model_path}"
            )

        return model_path

    def copy_model(self, model_info: Dict) -> bool:
        """复制单个模型"""
        print(f"\n📦 复制模型: {model_info['name']}")
        print(f"   来源: {model_info['hub_name']}")

        try:
            # 查找源模型
            source_path = self.find_model(model_info['hub_name'])
            print(f"   找到模型: {source_path}")

            # 目标路径
            target_path = self.target_dir / model_info['target_subdir'] / model_info['hub_name']

            # 复制模型
            if target_path.exists():
                print(f"   清理旧模型...")
                shutil.rmtree(target_path)

            target_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"   复制中...")

            shutil.copytree(source_path, target_path, symlinks=True)

            # 计算大小
            total_size = sum(f.stat().st_size for f in target_path.rglob("*") if f.is_file())
            print(f"   ✅ 完成: {total_size / 1024 / 1024:.2f} MB")
            print(f"   目标: {target_path}")

            return True

        except Exception as e:
            print(f"   ❌ 复制失败: {str(e)}")
            return False

    def copy_all_models(self) -> bool:
        """复制所有模型"""
        print("=" * 60)
        print("📦 LocalClip Editor - 本地模型复制工具")
        print("=" * 60)
        print(f"源目录: {self.hf_hub}")
        print(f"目标目录: {self.target_dir.absolute()}")
        print("=" * 60)

        success_count = 0
        total_count = len(self.models)

        for idx, model_info in enumerate(self.models, 1):
            print(f"\n[{idx}/{total_count}] 处理: {model_info['name']}")
            if self.copy_model(model_info):
                success_count += 1

        # 总结
        print("\n" + "=" * 60)
        print("📊 复制完成")
        print("=" * 60)
        print(f"成功: {success_count}/{total_count}")

        if success_count < total_count:
            print(f"失败: {total_count - success_count}")
            return False

        # 计算总大小
        total_size = sum(f.stat().st_size for f in self.target_dir.rglob("*") if f.is_file())
        print(f"总大小: {total_size / 1024 / 1024 / 1024:.2f} GB")
        print(f"目标: {self.target_dir.absolute()}")
        print("=" * 60)

        return True

    def verify_models(self) -> bool:
        """验证模型是否存在"""
        print("\n🔍 验证本地模型...")

        all_exist = True
        for model_info in self.models:
            model_path = self.hf_hub / model_info['hub_name']
            exists = model_path.exists()

            status = "✅" if exists else "❌"
            print(f"   {status} {model_info['name']}: {model_path}")

            if not exists:
                all_exist = False

        return all_exist


def copy_fish_speech_models(
    fish_speech_path: str,
    target_dir: str = "models/fish_speech"
):
    """
    复制 Fish-Speech 模型到打包目录

    Args:
        fish_speech_path: Fish-Speech 项目路径
        target_dir: 目标目录
    """
    print("\n" + "=" * 60)
    print("📦 复制 Fish-Speech 模型...")
    print("=" * 60)

    source = Path(fish_speech_path)
    target = Path(target_dir)

    if not source.exists():
        print(f"❌ Fish-Speech 路径不存在: {source}")
        return False

    # 需要复制的目录和文件
    items_to_copy = [
        "checkpoints/openaudio-s1-mini",
        "fish_speech",
        "tools",
        "pyproject.toml",
        "batch_inference.py",
    ]

    target.mkdir(parents=True, exist_ok=True)

    for item in items_to_copy:
        source_path = source / item
        target_path = target / item

        if not source_path.exists():
            print(f"⚠️  跳过不存在的项: {item}")
            continue

        print(f"📋 复制: {item}")

        if source_path.is_dir():
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.copytree(source_path, target_path, dirs_exist_ok=True)
        else:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

    # 计算总大小
    total_size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    print(f"\n✅ Fish-Speech 模型复制完成！")
    print(f"   总大小: {total_size / 1024 / 1024 / 1024:.2f} GB")
    print(f"   保存路径: {target.absolute()}")

    return True


def download_ffmpeg_windows(target_dir: str = "ffmpeg"):
    """
    下载 Windows 版本的 FFmpeg（支持 NVIDIA GPU）

    Args:
        target_dir: 目标目录
    """
    print("\n" + "=" * 60)
    print("📥 下载 FFmpeg for Windows (NVIDIA GPU 支持)...")
    print("=" * 60)

    import urllib.request
    import zipfile

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    # FFmpeg 下载链接（GPU 版本）
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = target / "ffmpeg.zip"

    print(f"📡 下载地址: {ffmpeg_url}")
    print(f"💾 保存路径: {target.absolute()}")
    print("⏳ 下载中... (大约 100-150 MB，可能需要几分钟)")
    print("   此版本支持 NVIDIA GPU 硬件加速")

    try:
        # 下载
        urllib.request.urlretrieve(ffmpeg_url, zip_path)

        # 解压
        print("📦 解压中...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target)

        # 移动文件到根目录
        extracted_dir = list(target.glob("ffmpeg-*"))[0]
        bin_dir = extracted_dir / "bin"

        for exe in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
            src = bin_dir / exe
            dst = target / exe
            if src.exists():
                shutil.move(str(src), str(dst))

        # 清理
        shutil.rmtree(extracted_dir)
        zip_path.unlink()

        print("✅ FFmpeg 下载完成！")
        print(f"   ffmpeg.exe: {(target / 'ffmpeg.exe').exists()}")
        print(f"   支持编码器: h264_nvenc (NVIDIA GPU)")
        print(f"   支持编码器: hevc_nvenc (NVIDIA GPU)")

        return True

    except Exception as e:
        print(f"❌ FFmpeg 下载失败: {str(e)}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="LocalClip Editor 本地模型复制工具（Windows 打包专用）"
    )
    parser.add_argument(
        "--models-dir",
        default="models",
        help="模型目标目录"
    )
    parser.add_argument(
        "--fish-speech-path",
        default="/Users/yiya_workstation/Documents/ai_editing/fish-speech",
        help="Fish-Speech 项目路径"
    )
    parser.add_argument(
        "--skip-huggingface",
        action="store_true",
        help="跳过 HuggingFace 模型复制"
    )
    parser.add_argument(
        "--skip-fish-speech",
        action="store_true",
        help="跳过 Fish-Speech 模型复制"
    )
    parser.add_argument(
        "--skip-ffmpeg",
        action="store_true",
        help="跳过 FFmpeg 下载"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="仅验证模型，不复制"
    )

    args = parser.parse_args()

    # 创建复制器
    copier = LocalModelCopier(target_dir=args.models_dir)

    if args.verify_only:
        # 仅验证
        copier.verify_models()
        return

    success = True

    # 复制 HuggingFace 模型
    if not args.skip_huggingface:
        success = copier.copy_all_models() and success
    else:
        print("\n⏭️  跳过 HuggingFace 模型复制")

    # 复制 Fish-Speech 模型
    if not args.skip_fish_speech:
        success = copy_fish_speech_models(
            args.fish_speech_path,
            os.path.join(args.models_dir, "fish_speech")
        ) and success
    else:
        print("\n⏭️  跳过 Fish-Speech 模型复制")

    # 下载 FFmpeg
    if not args.skip_ffmpeg:
        success = download_ffmpeg_windows("ffmpeg") and success
    else:
        print("\n⏭️  跳过 FFmpeg 下载")

    # 最终总结
    print("\n" + "=" * 60)
    if success:
        print("🎉 所有模型复制完成！可以开始打包了")
    else:
        print("⚠️  部分任务失败，请检查错误信息")
    print("=" * 60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
