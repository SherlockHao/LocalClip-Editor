from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        if task_id not in self.active_connections:
            self.active_connections[task_id] = set()
        self.active_connections[task_id].add(websocket)
        print(f"[WebSocket] 客户端连接: {task_id}, 当前连接数: {len(self.active_connections[task_id])}")

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
            print(f"[WebSocket] 客户端断开: {task_id}")

    async def broadcast_to_task(self, task_id: str, message: dict):
        """向指定任务的所有订阅客户端广播消息"""
        if task_id in self.active_connections:
            disconnected = set()
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_json(message)
                except:
                    disconnected.add(connection)

            # 清理断开的连接
            for conn in disconnected:
                self.active_connections[task_id].discard(conn)

manager = ConnectionManager()

@router.websocket("/ws/tasks/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await manager.connect(task_id, websocket)
    try:
        while True:
            # 保持连接，接收客户端心跳（如果有）
            data = await websocket.receive_text()
            # 可以处理客户端发送的心跳或命令
    except WebSocketDisconnect:
        manager.disconnect(task_id, websocket)

# 进度更新辅助函数
async def update_progress(task_id: str, language: str, stage: str, progress: int, message: str):
    """发送进度更新到所有订阅的客户端"""
    await manager.broadcast_to_task(task_id, {
        "type": "progress",
        "language": language,
        "stage": stage,
        "progress": progress,
        "message": message
    })
    print(f"[WebSocket] 进度更新 - {task_id}/{language}/{stage}: {progress}% - {message}")
