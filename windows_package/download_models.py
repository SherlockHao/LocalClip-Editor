#!/usr/bin/env python3
"""
模型下载和管理脚本
用于下载所有需要的 HuggingFace 模型到本地目录
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import shutil

try:
    from huggingface_hub import snapshot_download
    from transformers import AutoModel, AutoTokenizer, Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor
    import torch
except ImportError:
    print("❌ 请先安装依赖：pip install transformers huggingface_hub torch")
    sys.exit(1)


class ModelDownloader:
    """AI 模型下载管理器"""

    def __init__(self, target_dir: str = "models"):
        self.target_dir = Path(target_dir)
        self.target_dir.mkdir(parents=True, exist_ok=True)

        # 定义需要下载的模型
        self.models = [
            {
                "name": "pyannote-wespeaker",
                "model_id": "pyannote/wespeaker-voxceleb-resnet34-LM",
                "type": "pyannote",
                "cache_dir": self.target_dir / "pyannote",
                "size_estimate": "500 MB"
            },
            {
                "name": "gender-detection",
                "model_id": "prithivMLmods/Common-Voice-Geneder-Detection",
                "type": "wav2vec2",
                "cache_dir": self.target_dir / "wav2vec2",
                "size_estimate": "400 MB"
            }
        ]

    def download_all(self):
        """下载所有模型"""
        print("=" * 60)
        print("🚀 LocalClip Editor - AI 模型下载工具")
        print("=" * 60)
        print(f"\n📁 模型保存目录: {self.target_dir.absolute()}\n")

        total_models = len(self.models)

        for idx, model_info in enumerate(self.models, 1):
            print(f"\n[{idx}/{total_models}] 正在下载: {model_info['name']}")
            print(f"   模型ID: {model_info['model_id']}")
            print(f"   预计大小: {model_info['size_estimate']}")
            print(f"   保存路径: {model_info['cache_dir']}")

            try:
                self._download_model(model_info)
                print(f"   ✅ 下载成功！")
            except Exception as e:
                print(f"   ❌ 下载失败: {str(e)}")
                return False

        print("\n" + "=" * 60)
        print("✅ 所有模型下载完成！")
        print("=" * 60)
        return True

    def _download_model(self, model_info: Dict):
        """下载单个模型"""
        cache_dir = model_info["cache_dir"]
        cache_dir.mkdir(parents=True, exist_ok=True)

        model_type = model_info["type"]
        model_id = model_info["model_id"]

        if model_type == "pyannote":
            # 下载 pyannote.audio 模型
            snapshot_download(
                repo_id=model_id,
                cache_dir=str(cache_dir),
                resume_download=True,
            )

        elif model_type == "wav2vec2":
            # 下载 Wav2Vec2 模型和特征提取器
            Wav2Vec2ForSequenceClassification.from_pretrained(
                model_id,
                cache_dir=str(cache_dir)
            )
            Wav2Vec2FeatureExtractor.from_pretrained(
                model_id,
                cache_dir=str(cache_dir)
            )

    def verify_models(self) -> bool:
        """验证所有模型是否已下载"""
        print("\n🔍 验证模型完整性...\n")

        all_valid = True
        for model_info in self.models:
            cache_dir = model_info["cache_dir"]
            exists = cache_dir.exists() and any(cache_dir.iterdir())

            status = "✅" if exists else "❌"
            print(f"   {status} {model_info['name']}: {cache_dir}")

            if not exists:
                all_valid = False

        return all_valid

    def get_models_info(self) -> Dict:
        """获取模型信息统计"""
        info = {
            "total_models": len(self.models),
            "downloaded": 0,
            "total_size": 0,
            "models": []
        }

        for model_info in self.models:
            cache_dir = model_info["cache_dir"]
            exists = cache_dir.exists()

            size = 0
            if exists:
                size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
                info["downloaded"] += 1
                info["total_size"] += size

            info["models"].append({
                "name": model_info["name"],
                "id": model_info["model_id"],
                "downloaded": exists,
                "size_bytes": size,
                "size_mb": f"{size / 1024 / 1024:.2f} MB"
            })

        return info


def copy_fish_speech_models(fish_speech_path: str, target_dir: str = "models/fish_speech"):
    """
    复制 Fish-Speech 模型文件到打包目录

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


def download_ffmpeg(target_dir: str = "ffmpeg"):
    """
    下载 Windows 版本的 FFmpeg

    Args:
        target_dir: 目标目录
    """
    print("\n" + "=" * 60)
    print("📥 下载 FFmpeg for Windows...")
    print("=" * 60)

    import urllib.request
    import zipfile

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)

    # FFmpeg 下载链接
    ffmpeg_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = target / "ffmpeg.zip"

    print(f"📡 下载地址: {ffmpeg_url}")
    print(f"💾 保存路径: {target.absolute()}")
    print("⏳ 下载中... (大约 100-150 MB，可能需要几分钟)")

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
        print(f"   ffprobe.exe: {(target / 'ffprobe.exe').exists()}")
        print(f"   ffplay.exe: {(target / 'ffplay.exe').exists()}")

        return True

    except Exception as e:
        print(f"❌ FFmpeg 下载失败: {str(e)}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="LocalClip Editor 模型下载工具")
    parser.add_argument("--models-dir", default="models", help="模型保存目录")
    parser.add_argument("--fish-speech-path",
                       default="/Users/yiya_workstation/Documents/ai_editing/fish-speech",
                       help="Fish-Speech 项目路径")
    parser.add_argument("--skip-huggingface", action="store_true",
                       help="跳过 HuggingFace 模型下载")
    parser.add_argument("--skip-fish-speech", action="store_true",
                       help="跳过 Fish-Speech 模型复制")
    parser.add_argument("--skip-ffmpeg", action="store_true",
                       help="跳过 FFmpeg 下载")
    parser.add_argument("--verify-only", action="store_true",
                       help="仅验证模型，不下载")

    args = parser.parse_args()

    # 创建下载器
    downloader = ModelDownloader(target_dir=args.models_dir)

    if args.verify_only:
        # 仅验证
        downloader.verify_models()
        info = downloader.get_models_info()
        print(f"\n📊 统计信息:")
        print(f"   已下载: {info['downloaded']}/{info['total_models']}")
        print(f"   总大小: {info['total_size'] / 1024 / 1024 / 1024:.2f} GB")
        return

    success = True

    # 下载 HuggingFace 模型
    if not args.skip_huggingface:
        success = downloader.download_all() and success

    # 复制 Fish-Speech 模型
    if not args.skip_fish_speech:
        success = copy_fish_speech_models(
            args.fish_speech_path,
            os.path.join(args.models_dir, "fish_speech")
        ) and success

    # 下载 FFmpeg
    if not args.skip_ffmpeg:
        success = download_ffmpeg("ffmpeg") and success

    # 最终验证
    print("\n" + "=" * 60)
    print("📊 最终验证")
    print("=" * 60)

    downloader.verify_models()

    # 打印统计信息
    info = downloader.get_models_info()
    print(f"\n✅ 完成！")
    print(f"   HuggingFace 模型: {info['downloaded']}/{info['total_models']}")
    print(f"   模型总大小: {info['total_size'] / 1024 / 1024 / 1024:.2f} GB")

    if success:
        print("\n🎉 所有资源准备就绪，可以开始打包了！")
        sys.exit(0)
    else:
        print("\n⚠️  部分资源下载失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
