"""
临时文件泄漏检测脚本

此脚本用于检测后端服务是否正确清理临时文件。

使用方法：
1. 运行此脚本: python test_temp_file_leak.py --before
2. 执行一些任务操作
3. 运行此脚本: python test_temp_file_leak.py --after
"""

import os
import sys
import json
import tempfile
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set


SNAPSHOT_FILE = "temp_file_snapshot.json"


def get_temp_files() -> Dict[str, Dict]:
    """获取所有临时文件及其信息"""
    temp_dir = Path(tempfile.gettempdir())
    files = {}

    # 搜索可能的临时文件模式
    patterns = [
        "*.json",
        "*.wav",
        "*.mp3",
        "*.mp4",
        "tmp*",
        "speaker_*",
        "segment_*",
        "cloned_*",
        "fish_*",
        "cosy_*",
        "nisqa_*",
    ]

    for pattern in patterns:
        for f in temp_dir.glob(pattern):
            try:
                stat = f.stat()
                files[str(f)] = {
                    'size': stat.st_size,
                    'mtime': stat.st_mtime,
                    'mtime_str': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            except:
                pass

    return files


def save_snapshot():
    """保存当前快照"""
    files = get_temp_files()
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'temp_dir': tempfile.gettempdir(),
        'file_count': len(files),
        'files': files,
    }

    with open(SNAPSHOT_FILE, 'w', encoding='utf-8') as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"快照已保存: {SNAPSHOT_FILE}")
    print(f"临时目录: {tempfile.gettempdir()}")
    print(f"文件数量: {len(files)}")


def compare_snapshot():
    """比较当前状态与快照"""
    if not os.path.exists(SNAPSHOT_FILE):
        print(f"[错误] 未找到快照文件: {SNAPSHOT_FILE}")
        print("请先运行: python test_temp_file_leak.py --before")
        return

    with open(SNAPSHOT_FILE, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)

    before_files = set(snapshot['files'].keys())
    current_files_dict = get_temp_files()
    current_files = set(current_files_dict.keys())

    # 计算差异
    new_files = current_files - before_files
    deleted_files = before_files - current_files

    print("=" * 60)
    print("临时文件泄漏分析报告")
    print("=" * 60)
    print()
    print(f"快照时间: {snapshot['timestamp']}")
    print(f"当前时间: {datetime.now().isoformat()}")
    print()
    print(f"快照文件数: {len(before_files)}")
    print(f"当前文件数: {len(current_files)}")
    print(f"新增文件数: {len(new_files)}")
    print(f"删除文件数: {len(deleted_files)}")
    print()

    # 分析新增文件
    if new_files:
        print("-" * 60)
        print("新增的临时文件:")
        print("-" * 60)

        # 分类统计
        json_files = []
        audio_files = []
        other_files = []

        for f in sorted(new_files):
            info = current_files_dict.get(f, {})
            size_kb = info.get('size', 0) / 1024
            fname = os.path.basename(f)

            if fname.endswith('.json'):
                json_files.append((f, size_kb))
            elif fname.endswith(('.wav', '.mp3', '.mp4')):
                audio_files.append((f, size_kb))
            else:
                other_files.append((f, size_kb))

        if json_files:
            print(f"\nJSON 配置文件 ({len(json_files)} 个):")
            total_size = 0
            for f, size in json_files[:10]:
                print(f"  [{size:.1f} KB] {os.path.basename(f)}")
                total_size += size
            if len(json_files) > 10:
                print(f"  ... 还有 {len(json_files) - 10} 个")
            print(f"  总大小: {total_size:.1f} KB")

        if audio_files:
            print(f"\n音频/视频文件 ({len(audio_files)} 个):")
            total_size = 0
            for f, size in audio_files[:10]:
                print(f"  [{size:.1f} KB] {os.path.basename(f)}")
                total_size += size
            if len(audio_files) > 10:
                print(f"  ... 还有 {len(audio_files) - 10} 个")
            print(f"  总大小: {total_size / 1024:.2f} MB")

        if other_files:
            print(f"\n其他文件 ({len(other_files)} 个):")
            for f, size in other_files[:10]:
                print(f"  [{size:.1f} KB] {os.path.basename(f)}")
            if len(other_files) > 10:
                print(f"  ... 还有 {len(other_files) - 10} 个")

    print()
    print("=" * 60)

    # 判断是否有泄漏
    # 检查是否有项目相关的临时文件未清理
    project_keywords = ['speaker', 'segment', 'cloned', 'fish', 'cosy', 'nisqa', 'translate', 'retranslate']
    project_files = [f for f in new_files if any(kw in os.path.basename(f).lower() for kw in project_keywords)]

    if project_files:
        print(f"[警告] 发现 {len(project_files)} 个可能泄漏的项目相关临时文件!")
        print()
        for f in project_files[:20]:
            print(f"  - {os.path.basename(f)}")
        if len(project_files) > 20:
            print(f"  ... 还有 {len(project_files) - 20} 个")
        print()
        print("建议检查以下代码中 delete=False 的临时文件是否有清理:")
        print("  - main.py")
        print("  - translation_service.py")
        print("  - cosyvoice_cloner.py")
        print("  - fish_simple_cloner.py")
        print("  - xtts_cloner.py")
    else:
        print("[OK] 未发现项目相关临时文件泄漏")

    print("=" * 60)


def clean_old_temp_files(days: int = 1):
    """清理旧的临时文件"""
    temp_dir = Path(tempfile.gettempdir())
    cutoff = datetime.now() - timedelta(days=days)

    project_keywords = ['speaker', 'segment', 'cloned', 'fish', 'cosy', 'nisqa', 'translate', 'retranslate']
    cleaned_count = 0
    cleaned_size = 0

    for pattern in ["*.json", "*.wav"]:
        for f in temp_dir.glob(pattern):
            fname = os.path.basename(f).lower()
            if any(kw in fname for kw in project_keywords):
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime < cutoff:
                        size = f.stat().st_size
                        f.unlink()
                        cleaned_count += 1
                        cleaned_size += size
                        print(f"删除: {fname}")
                except Exception as e:
                    print(f"删除失败 {fname}: {e}")

    print()
    print(f"已清理 {cleaned_count} 个文件，释放 {cleaned_size / 1024 / 1024:.2f} MB")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="临时文件泄漏检测")
    parser.add_argument('--before', action='store_true', help="保存执行任务前的快照")
    parser.add_argument('--after', action='store_true', help="比较执行任务后的变化")
    parser.add_argument('--clean', type=int, metavar='DAYS', help="清理超过指定天数的旧临时文件")
    parser.add_argument('--list', action='store_true', help="列出当前所有临时文件")

    args = parser.parse_args()

    if args.before:
        save_snapshot()
    elif args.after:
        compare_snapshot()
    elif args.clean:
        clean_old_temp_files(args.clean)
    elif args.list:
        files = get_temp_files()
        print(f"临时目录: {tempfile.gettempdir()}")
        print(f"文件数量: {len(files)}")
        print()
        for f, info in sorted(files.items()):
            print(f"  [{info['size']/1024:.1f} KB] {os.path.basename(f)}")
    else:
        parser.print_help()
