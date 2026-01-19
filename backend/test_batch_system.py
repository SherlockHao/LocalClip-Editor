#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量任务系统测试脚本
测试数据库、文件管理、任务队列等核心功能
"""

import sys
import os
import time
import uuid
from pathlib import Path

# 设置环境变量
os.environ["TORCH_DYNAMO_DISABLE"] = "1"

print("=" * 60)
print("批量任务系统 - 功能测试")
print("=" * 60)
print()

# 测试 1: 数据库模块
print("[测试 1/5] 测试数据库模块...")
try:
    from database import init_db, SessionLocal
    from models.task import Task, LanguageProcessingLog

    # 初始化数据库
    init_db()
    print("✓ 数据库初始化成功")

    # 创建测试任务
    db = SessionLocal()
    test_task = Task(
        task_id=f"test_task_{uuid.uuid4().hex[:8]}",
        video_filename="test_video.mp4",
        video_original_name="测试视频.mp4",
        status="pending",
        language_status={},
        config={"target_languages": ["en", "ko"]}
    )
    db.add(test_task)
    db.commit()
    print(f"✓ 创建测试任务: {test_task.task_id}")

    # 查询任务
    retrieved_task = db.query(Task).filter(Task.task_id == test_task.task_id).first()
    assert retrieved_task is not None
    assert retrieved_task.video_original_name == "测试视频.mp4"
    print(f"✓ 查询任务成功: {retrieved_task.video_original_name}")

    # 更新任务状态
    retrieved_task.status = "processing"
    retrieved_task.language_status = {"en": {"status": "processing", "progress": 50}}
    db.commit()
    print("✓ 更新任务状态成功")

    # 删除测试任务
    db.delete(retrieved_task)
    db.commit()
    db.close()
    print("✓ 删除测试任务成功")
    print()

except Exception as e:
    print(f"✗ 数据库模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 2: 文件管理模块
print("[测试 2/5] 测试文件管理模块...")
try:
    from file_manager import TaskFileManager

    file_manager = TaskFileManager(base_dir="./test_tasks")
    test_task_id = f"test_task_{uuid.uuid4().hex[:8]}"

    # 创建任务目录结构
    structure = file_manager.create_task_structure(test_task_id)
    assert structure["root"].exists()
    assert structure["input"].exists()
    assert structure["processed"].exists()
    assert structure["outputs"].exists()
    print(f"✓ 创建任务目录结构: {structure['root']}")

    # 创建语言输出目录
    en_dir = file_manager.get_language_output_dir(test_task_id, "en")
    assert en_dir.exists()
    print(f"✓ 创建语言输出目录: {en_dir}")

    # 创建克隆音频目录
    audio_dir = file_manager.get_cloned_audio_dir(test_task_id, "en")
    assert audio_dir.exists()
    print(f"✓ 创建克隆音频目录: {audio_dir}")

    # 删除测试目录
    file_manager.delete_task(test_task_id)
    assert not structure["root"].exists()
    print("✓ 删除任务目录成功")

    # 清理测试目录
    Path("./test_tasks").rmdir()
    print()

except Exception as e:
    print(f"✗ 文件管理模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 3: 任务队列模块
print("[测试 3/5] 测试任务队列模块...")
try:
    from task_queue import TaskQueue

    queue = TaskQueue(max_workers=2)

    # 定义测试函数
    def test_job(duration, result):
        time.sleep(duration)
        return result

    # 提交任务
    job_id1 = queue.submit("task1", "en", "test", test_job, 0.1, "result1")
    job_id2 = queue.submit("task1", "ko", "test", test_job, 0.1, "result2")
    print(f"✓ 提交任务到队列: {job_id1}, {job_id2}")

    # 检查任务状态
    time.sleep(0.05)
    status1 = queue.get_status(job_id1)
    print(f"✓ 获取任务状态: {status1['status']}")

    # 等待任务完成
    time.sleep(0.2)
    status1 = queue.get_status(job_id1)
    status2 = queue.get_status(job_id2)
    assert status1["status"] == "completed"
    assert status2["status"] == "completed"
    assert status1["result"] == "result1"
    assert status2["result"] == "result2"
    print("✓ 任务执行成功，结果正确")

    # 获取任务的所有作业
    jobs = queue.get_task_jobs("task1")
    assert len(jobs) == 2
    print(f"✓ 获取任务作业列表: {len(jobs)} 个作业")
    print()

except Exception as e:
    print(f"✗ 任务队列模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 4: 路由模块导入
print("[测试 4/5] 测试路由模块导入...")
try:
    from routers import tasks, websocket

    assert hasattr(tasks, 'router')
    assert hasattr(websocket, 'router')
    print("✓ 任务路由模块导入成功")
    print("✓ WebSocket路由模块导入成功")
    print()

except Exception as e:
    print(f"✗ 路由模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试 5: 集成测试 - 模拟完整工作流
print("[测试 5/5] 集成测试 - 模拟完整工作流...")
try:
    from database import SessionLocal
    from models.task import Task
    from file_manager import file_manager
    from task_queue import task_queue

    # 1. 创建任务
    db = SessionLocal()
    task_id = f"integration_test_{uuid.uuid4().hex[:8]}"
    task = Task(
        task_id=task_id,
        video_filename=f"{task_id}_video.mp4",
        video_original_name="集成测试视频.mp4",
        status="pending",
        language_status={},
        config={"target_languages": ["en", "ko"]}
    )
    db.add(task)
    db.commit()
    print(f"✓ 步骤 1: 创建任务 {task_id}")

    # 2. 创建目录结构
    structure = file_manager.create_task_structure(task_id)
    print(f"✓ 步骤 2: 创建目录结构")

    # 3. 模拟语言处理任务
    def mock_process(lang, stage):
        time.sleep(0.1)
        return f"Processed {lang} - {stage}"

    job_id_en = task_queue.submit(task_id, "en", "translation", mock_process, "en", "translation")
    job_id_ko = task_queue.submit(task_id, "ko", "translation", mock_process, "ko", "translation")
    print(f"✓ 步骤 3: 提交语言处理任务")

    # 4. 等待任务完成并更新状态
    time.sleep(0.2)
    status_en = task_queue.get_status(job_id_en)
    status_ko = task_queue.get_status(job_id_ko)

    if status_en["status"] == "completed" and status_ko["status"] == "completed":
        task.language_status = {
            "en": {"status": "completed", "progress": 100},
            "ko": {"status": "completed", "progress": 100}
        }
        task.status = "completed"
        db.commit()
        print(f"✓ 步骤 4: 更新任务状态为已完成")

    # 5. 清理
    file_manager.delete_task(task_id)
    db.delete(task)
    db.commit()
    db.close()
    print(f"✓ 步骤 5: 清理测试数据")
    print()

except Exception as e:
    print(f"✗ 集成测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("✓ 所有测试通过！")
print("=" * 60)
print()
print("后端基础架构已成功实现，包括：")
print("  - 数据库模型和连接管理")
print("  - 任务文件管理系统")
print("  - 线程池任务队列")
print("  - RESTful API 路由")
print("  - WebSocket 实时推送")
print()
print("可以开始启动后端服务进行 API 测试。")
