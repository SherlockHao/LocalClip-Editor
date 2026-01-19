#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API 端点测试脚本
使用 requests 库测试后端 API 功能
"""

import requests
import time
import json
from pathlib import Path

BASE_URL = "http://localhost:8080"

print("=" * 60)
print("API 端点测试")
print("=" * 60)
print()
print("确保后端服务已启动 (python -m uvicorn main:app --port 8080)")
print("按 Enter 继续...")
input()

# 测试 1: 获取任务列表
print("[测试 1/3] GET /api/tasks - 获取任务列表")
try:
    response = requests.get(f"{BASE_URL}/api/tasks")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        tasks = response.json()
        print(f"✓ 成功获取任务列表，共 {len(tasks)} 个任务")
        if tasks:
            print(f"  示例: {tasks[0]['task_id']}")
    else:
        print(f"✗ 请求失败: {response.text}")
except Exception as e:
    print(f"✗ 连接失败: {e}")
    print("请确保后端服务已启动")
    exit(1)

print()

# 测试 2: 创建任务（需要视频文件）
print("[测试 2/3] POST /api/tasks - 创建任务")
print("注意: 此测试需要上传视频文件，跳过...")
print("可以使用 Postman 或 curl 测试:")
print('  curl -X POST "http://localhost:8080/api/tasks" -F "video=@test.mp4"')
print()

# 测试 3: 健康检查
print("[测试 3/3] 测试 WebSocket 连接（需要手动测试）")
print("WebSocket 端点: ws://localhost:8080/ws/tasks/{task_id}")
print("可以使用前端应用或 WebSocket 客户端测试")
print()

print("=" * 60)
print("API 端点基础测试完成")
print("=" * 60)
print()
print("后续测试步骤:")
print("1. 启动前端服务测试 UI 交互")
print("2. 测试文件上传和任务创建")
print("3. 测试 WebSocket 实时进度推送")
