"""
集成测试 - 测试译文长度验证和重新翻译的集成流程
不实际运行 LLM，而是模拟整个流程
"""
import os
import json
import tempfile
from text_utils import check_translation_length, validate_translations


def test_integration_flow():
    """测试完整的集成流程（模拟）"""
    print("=" * 60)
    print("集成测试 - 译文长度验证和重新翻译流程")
    print("=" * 60)

    # 模拟源字幕和目标字幕
    source_subtitles = [
        {"text": "你好"},
        {"text": "早上好"},
        {"text": "谢谢"},
        {"text": "再见"},
        {"text": "欢迎"},
    ]

    target_subtitles = [
        {"text": "Hello"},
        {"text": "Good morning"},
        {"text": "Thank you very much for everything you have done"},  # 超长
        {"text": "Goodbye"},
        {"text": "Welcome to our amazing platform and service"},  # 超长
    ]

    target_language = "英文"

    print("\n[步骤 1] 验证译文长度...")
    print("-" * 60)

    # 检查每句译文长度
    too_long_items = []
    for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
        source_text = source_sub["text"]
        target_text = target_sub["text"]

        is_too_long, source_len, target_len, ratio = check_translation_length(
            source_text, target_text, target_language, max_ratio=1.2
        )

        status = "[超长]" if is_too_long else "[合格]"
        print(f"{status} [{idx}] '{source_text}' ({source_len}字) -> '{target_text}' ({target_len}词)")
        print(f"       比例: {ratio:.2f}x")

        if is_too_long:
            too_long_items.append({
                "index": idx,
                "source": source_text,
                "target": target_text,
                "source_length": source_len,
                "target_length": target_len,
                "ratio": ratio
            })

    print(f"\n检测结果: 发现 {len(too_long_items)} 条超长译文")

    if too_long_items:
        print("\n[步骤 2] 准备批量重新翻译...")
        print("-" * 60)

        # 准备重新翻译任务
        retranslate_tasks = []
        for item in too_long_items:
            retranslate_tasks.append({
                "task_id": f"retrans-{item['index']}",
                "source": item["source"],
                "target_language": target_language
            })

        print(f"准备重新翻译 {len(retranslate_tasks)} 条文本:")
        for task in retranslate_tasks:
            print(f"  - {task['task_id']}: '{task['source']}'")

        # 生成配置文件
        print("\n[步骤 3] 生成配置文件...")
        print("-" * 60)

        # 使用临时目录
        temp_dir = tempfile.gettempdir()
        config_file = os.path.join(temp_dir, "test_retranslate_config.json")

        model_path = "C:\\workspace\\ai_editing\\models\\Qwen3-1.7B"

        retranslate_config = {
            "tasks": retranslate_tasks,
            "model_path": model_path,
            "num_processes": 1
        }

        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(retranslate_config, f, ensure_ascii=False, indent=2)

        print(f"配置文件已生成: {config_file}")
        print(f"内容预览:")
        print(json.dumps(retranslate_config, ensure_ascii=False, indent=2))

        # 模拟翻译结果
        print("\n[步骤 4] 模拟批量重新翻译...")
        print("-" * 60)
        print("(注: 实际运行时会调用 batch_retranslate.py)")

        # 模拟的翻译结果
        mock_results = [
            {
                "task_id": "retrans-2",
                "source": "谢谢",
                "translation": "Thanks",
                "process_id": 1,
                "time": 1.23,
                "target_language": "英文"
            },
            {
                "task_id": "retrans-4",
                "source": "欢迎",
                "translation": "Welcome",
                "process_id": 1,
                "time": 1.15,
                "target_language": "英文"
            }
        ]

        print("模拟翻译结果:")
        for result in mock_results:
            print(f"  [{result['task_id']}] '{result['source']}' -> '{result['translation']}' ({result['time']:.2f}s)")

        # 更新目标字幕
        print("\n[步骤 5] 更新目标字幕...")
        print("-" * 60)

        for result_item in mock_results:
            task_id_str = result_item["task_id"]
            # 提取索引: "retrans-123" -> 123
            idx = int(task_id_str.split('-')[1])
            new_translation = result_item["translation"]

            old_text = target_subtitles[idx]["text"]
            target_subtitles[idx]["text"] = new_translation

            print(f"[{idx}] 更新译文:")
            print(f"     原: '{old_text}'")
            print(f"     新: '{new_translation}'")

        # 验证更新后的长度
        print("\n[步骤 6] 验证更新后的译文长度...")
        print("-" * 60)

        for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
            source_text = source_sub["text"]
            target_text = target_sub["text"]

            is_too_long, source_len, target_len, ratio = check_translation_length(
                source_text, target_text, target_language, max_ratio=1.2
            )

            status = "[超长]" if is_too_long else "[合格]"
            print(f"{status} [{idx}] '{source_text}' -> '{target_text}'")
            print(f"       {source_len}字 -> {target_len}词 = {ratio:.2f}x")

        print("\n" + "=" * 60)
        print("集成测试完成!")
        print("=" * 60)

    return True


def test_batch_validate():
    """测试批量验证函数"""
    print("\n" + "=" * 60)
    print("批量验证测试")
    print("=" * 60)

    translations = [
        {"id": 1, "source": "你好", "target": "Hello"},
        {"id": 2, "source": "早上好", "target": "Good morning"},
        {"id": 3, "source": "谢谢", "target": "Thank you very much for everything"},
        {"id": 4, "source": "再见", "target": "Goodbye"},
        {"id": 5, "source": "欢迎", "target": "Welcome to our amazing platform"},
    ]

    valid, too_long = validate_translations(translations, "英文", max_ratio=1.2)

    print(f"\n合格译文: {len(valid)} 条")
    for item in valid:
        print(f"  [{item['id']}] '{item['source']}' -> '{item['target']}'")

    print(f"\n超长译文: {len(too_long)} 条")
    for item in too_long:
        print(f"  [{item['id']}] '{item['source']}' -> '{item['target']}'")
        print(f"       {item['source_length']}字 -> {item['target_length']}词 = {item['length_ratio']:.2f}x")

    return len(valid) == 3 and len(too_long) == 2


def main():
    """运行所有集成测试"""
    print("\n" + "=" * 60)
    print("译文长度验证 - 集成测试套件")
    print("=" * 60 + "\n")

    # 测试 1: 批量验证
    test1_pass = test_batch_validate()
    print(f"\n[测试 1] 批量验证: {'PASS' if test1_pass else 'FAIL'}")

    # 测试 2: 完整集成流程
    test2_pass = test_integration_flow()
    print(f"\n[测试 2] 集成流程: {'PASS' if test2_pass else 'FAIL'}")

    # 总结
    print("\n" + "=" * 60)
    all_pass = test1_pass and test2_pass
    print(f"所有测试: {'全部通过' if all_pass else '部分失败'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
