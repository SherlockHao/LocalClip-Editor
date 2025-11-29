#!/bin/bash

# LocalClip Editor 一键启动脚本
# 用于同时启动后端和前端服务

echo "🔄 检查并清理已占用的端口..."

# 清理8000端口（后端）
BACKEND_PIDS=$(lsof -ti:8000)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "🚫 终止占用8000端口的进程: $BACKEND_PIDS"
    kill -9 $BACKEND_PIDS 2>/dev/null
    sleep 2
fi

# 清理5173端口（前端）
FRONTEND_PIDS=$(lsof -ti:5173)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "🚫 终止占用5173端口的进程: $FRONTEND_PIDS"
    kill -9 $FRONTEND_PIDS 2>/dev/null
    sleep 2
fi

echo "🚀 启动 LocalClip Editor..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 启动后端服务
echo "🔌 启动后端服务 (FastAPI)..."
cd "$SCRIPT_DIR/backend"

# 激活conda环境并启动后端
eval "$(~/miniconda3/bin/conda shell.bash hook)" && conda activate ui && uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 5

# 启动前端服务
echo "🎨 启动前端服务 (React)..."
cd "$SCRIPT_DIR/frontend"

# 安装/更新前端依赖
echo "📦 安装/更新前端依赖..."
npm install

npm run dev &
FRONTEND_PID=$!

echo "✅ LocalClip Editor 已启动！"
echo "🌐 前端访问地址: http://localhost:5173"
echo "🔧 后端API文档: http://localhost:8000/docs"
echo "📊 后端PID: $BACKEND_PID"
echo "📊 前端PID: $FRONTEND_PID"

# 定义清理函数
cleanup() {
    echo "🛑 正在停止 LocalClip Editor..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit 0
}

# 捕获退出信号
trap cleanup INT TERM

# 等待所有进程结束
wait $BACKEND_PID $FRONTEND_PID