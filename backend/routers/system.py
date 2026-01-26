# -*- coding: utf-8 -*-
"""
系统管理路由 - 系统状态查询、关闭系统等
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import sys
import time
import platform
import psutil

router = APIRouter(prefix="/api/system", tags=["system"])

# 记录系统启动时间
_start_time = time.time()


class SystemStatus(BaseModel):
    """系统状态响应"""
    status: str  # running, stopping
    uptime_seconds: float
    uptime_formatted: str
    platform: str
    python_version: str
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float


class ShutdownRequest(BaseModel):
    """关闭请求"""
    confirm: bool = False


def format_uptime(seconds: float) -> str:
    """格式化运行时间"""
    if seconds < 60:
        return f"{int(seconds)} 秒"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes} 分 {secs} 秒"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours} 小时 {minutes} 分"


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    获取系统状态

    返回：
    - 运行状态
    - 运行时间
    - 系统信息
    - CPU/内存使用率
    """
    uptime = time.time() - _start_time

    # 获取内存信息
    memory = psutil.virtual_memory()

    return SystemStatus(
        status="running",
        uptime_seconds=uptime,
        uptime_formatted=format_uptime(uptime),
        platform=platform.system(),
        python_version=platform.python_version(),
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=memory.percent,
        memory_used_gb=round(memory.used / (1024 ** 3), 2),
        memory_total_gb=round(memory.total / (1024 ** 3), 2)
    )


@router.post("/shutdown")
async def shutdown_system(request: ShutdownRequest):
    """
    关闭系统

    需要在请求体中设置 confirm: true 才会执行关闭

    关闭流程：
    1. 返回确认消息
    2. 延迟 1 秒后终止进程
    """
    if not request.confirm:
        raise HTTPException(
            status_code=400,
            detail="请设置 confirm: true 以确认关闭系统"
        )

    print("\n" + "=" * 50, flush=True)
    print("[系统] 收到关闭请求，系统即将关闭...", flush=True)
    print("=" * 50 + "\n", flush=True)

    # 使用后台线程延迟关闭，让响应先返回
    import threading

    def delayed_shutdown():
        import subprocess
        time.sleep(1)
        print("[系统] 正在关闭...", flush=True)

        # 方法1：通过端口关闭前端进程
        try:
            result = subprocess.run(
                'netstat -ano | findstr ":5173.*LISTENING"',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1].strip()
                        if pid.isdigit():
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                            print(f"[系统] 已终止前端进程 PID: {pid}", flush=True)
        except Exception as e:
            print(f"[系统] 关闭前端时出错: {e}", flush=True)

        # 方法2：通过窗口标题关闭 CMD 窗口（使用 taskkill 的 /FI 过滤器）
        try:
            # 尝试多种窗口标题匹配
            window_titles = [
                "Ascendia-Frontend", "Ascendia-Backend",
                "LocalClip-Frontend", "LocalClip-Backend"
            ]
            for title in window_titles:
                subprocess.run(f'taskkill /FI "WINDOWTITLE eq {title}*" /F', shell=True, capture_output=True)
            print("[系统] 已关闭服务窗口", flush=True)
        except:
            pass

        # 方法3：通过查找父进程为 cmd.exe 且命令行包含 localclip 的进程
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == 'cmd.exe':
                        cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                        if 'localclip' in cmdline or 'ascendia' in cmdline:
                            proc.kill()
                except:
                    pass
        except:
            pass

        # 方法4：关闭后端子进程
        try:
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except:
                    pass
            psutil.wait_procs(children, timeout=2)
        except:
            pass

        # 终止自身
        os._exit(0)

    shutdown_thread = threading.Thread(target=delayed_shutdown)
    shutdown_thread.start()

    return {
        "message": "系统正在关闭...",
        "status": "shutting_down"
    }


@router.get("/health")
async def health_check():
    """
    健康检查接口（用于前端检测服务是否在线）
    """
    return {"status": "ok", "timestamp": time.time()}
