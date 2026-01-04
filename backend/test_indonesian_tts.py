"""
测试印尼语TTS批量生成功能
"""
import os
import sys
import io
import json
import tempfile

# 强制UTF-8输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from indonesian_tts_cloner import IndonesianTTSCloner

def test_indonesian_tts():
    """测试印尼语TTS批量生成"""

    print("=" * 70)
    print("印尼语TTS批量生成测试")
    print("=" * 70)

    # 配置
    tts_id_env_python = "C:/Users/7/miniconda3/envs/tts-id-py311/python.exe"
    model_dir = "c:/workspace/ai_editing/models/vits-tts-id"

    # 检查环境
    if not os.path.exists(tts_id_env_python):
        print(f"❌ Python环境不存在: {tts_id_env_python}")
        return False

    if not os.path.exists(model_dir):
        print(f"❌ 模型不存在: {model_dir}")
        return False

    print(f"✓ Python环境: {tts_id_env_python}")
    print(f"✓ 模型路径: {model_dir}")

    # 创建临时输出目录
    output_dir = tempfile.mkdtemp(prefix="indonesian_tts_test_")
    print(f"✓ 输出目录: {output_dir}")

    # 准备测试任务（4个印尼语句子，只测试 ardi 和 gadis）
    test_tasks = [
        {
            "segment_index": 0,
            "speaker_name": "ardi",
            "target_text": "Selamat pagi, bagaimana kabar Anda?",
            "output_file": os.path.join(output_dir, "segment_0.wav")
        },
        {
            "segment_index": 1,
            "speaker_name": "gadis",
            "target_text": "Halo, saya senang bertemu dengan Anda.",
            "output_file": os.path.join(output_dir, "segment_1.wav")
        },
        {
            "segment_index": 2,
            "speaker_name": "ardi",
            "target_text": "Teknologi ini sangat berguna.",
            "output_file": os.path.join(output_dir, "segment_2.wav")
        },
        {
            "segment_index": 3,
            "speaker_name": "gadis",
            "target_text": "Sampai jumpa di kesempatan berikutnya.",
            "output_file": os.path.join(output_dir, "segment_3.wav")
        }
    ]

    print(f"\n准备测试 {len(test_tasks)} 个任务:")
    for task in test_tasks:
        print(f"  [{task['segment_index']}] {task['speaker_name']}: {task['target_text']}")

    # 创建克隆器
    print(f"\n正在初始化印尼语TTS克隆器...")
    try:
        cloner = IndonesianTTSCloner(model_dir, tts_id_env_python)
        print("✓ 克隆器初始化成功")
    except Exception as e:
        print(f"❌ 克隆器初始化失败: {e}")
        return False

    # 进度回调
    def progress_callback(current, total):
        print(f"  进度: {current}/{total} ({current*100//total}%)")

    # 执行批量生成
    print(f"\n开始批量生成...")
    config_file = os.path.join(output_dir, "test_config.json")

    try:
        segment_files = cloner.batch_generate_audio(
            test_tasks,
            config_file,
            progress_callback=progress_callback
        )

        print(f"\n✓ 批量生成完成!")
        print(f"  成功生成: {len(segment_files)} 个音频文件")

        # 验证文件
        print(f"\n验证生成的文件:")
        all_exist = True
        for idx, filepath in segment_files.items():
            exists = os.path.exists(filepath)
            size = os.path.getsize(filepath) if exists else 0
            status = "✓" if exists and size > 0 else "❌"
            print(f"  {status} [{idx}] {filepath} ({size} bytes)")
            if not exists or size == 0:
                all_exist = False

        if all_exist:
            print(f"\n✅ 所有测试通过!")
            print(f"\n生成的音频文件保存在: {output_dir}")
            return True
        else:
            print(f"\n❌ 部分文件生成失败")
            return False

    except Exception as e:
        print(f"\n❌ 批量生成失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_indonesian_tts()
    exit(0 if success else 1)
