# 批量视频管理系统 - 实施步骤

## 技术栈
- **前端**: React + TypeScript + React Router + Vite
- **后端**: FastAPI + 线程池任务队列
- **实时通信**: WebSocket + 轮询混合
- **数据库**: SQLite
- **文件组织**: 按任务 ID 分层目录

---

## 阶段 1: 数据库和后端基础架构 (第1-2天)

### 步骤 1.1: 创建数据库模型
**文件**: `backend/models/task.py`

```python
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, unique=True, nullable=False, index=True)
    video_filename = Column(String, nullable=False)
    video_original_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="pending")  # pending, processing, completed, failed

    # 语言处理状态 (JSON)
    language_status = Column(JSON, default={})
    # 格式: {"en": {"status": "completed", "progress": 100}, "ko": {"status": "processing", "progress": 45}}

    # 配置信息
    config = Column(JSON, default={})
    # 格式: {"target_languages": ["en", "ko"], "export_settings": {...}}

    # 错误信息
    error_message = Column(String, nullable=True)

class LanguageProcessingLog(Base):
    __tablename__ = "language_processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String, nullable=False, index=True)
    language = Column(String, nullable=False)
    stage = Column(String, nullable=False)  # speaker_diarization, translation, voice_cloning, export
    status = Column(String, nullable=False)  # started, progress, completed, failed
    progress = Column(Integer, default=0)
    message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 步骤 1.2: 初始化数据库连接
**文件**: `backend/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.task import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./localclip.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库表"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 步骤 1.3: 创建任务队列管理器
**文件**: `backend/task_queue.py`

```python
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Callable, Any
from dataclasses import dataclass
import uuid
from datetime import datetime

@dataclass
class QueuedTask:
    task_id: str
    job_id: str
    language: str
    stage: str
    future: Future
    created_at: datetime

class TaskQueue:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, QueuedTask] = {}

    def submit(
        self,
        task_id: str,
        language: str,
        stage: str,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """提交任务到队列"""
        job_id = f"{task_id}_{language}_{stage}_{uuid.uuid4().hex[:8]}"

        future = self.executor.submit(func, *args, **kwargs)

        queued_task = QueuedTask(
            task_id=task_id,
            job_id=job_id,
            language=language,
            stage=stage,
            future=future,
            created_at=datetime.utcnow()
        )

        self.tasks[job_id] = queued_task
        return job_id

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if job_id not in self.tasks:
            return {"status": "not_found"}

        task = self.tasks[job_id]
        if task.future.done():
            try:
                result = task.future.result()
                return {"status": "completed", "result": result}
            except Exception as e:
                return {"status": "failed", "error": str(e)}
        else:
            return {"status": "running"}

    def cancel(self, job_id: str) -> bool:
        """取消任务"""
        if job_id in self.tasks:
            return self.tasks[job_id].future.cancel()
        return False

    def get_task_jobs(self, task_id: str) -> list:
        """获取指定任务的所有作业"""
        return [
            {
                "job_id": job_id,
                "language": task.language,
                "stage": task.stage,
                "status": self.get_status(job_id)["status"]
            }
            for job_id, task in self.tasks.items()
            if task.task_id == task_id
        ]

# 全局任务队列实例
task_queue = TaskQueue(max_workers=4)
```

### 步骤 1.4: 文件组织工具
**文件**: `backend/file_manager.py`

```python
import os
import shutil
from pathlib import Path

class TaskFileManager:
    def __init__(self, base_dir: str = "./tasks"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def get_task_dir(self, task_id: str) -> Path:
        """获取任务根目录"""
        return self.base_dir / task_id

    def create_task_structure(self, task_id: str) -> Dict[str, Path]:
        """创建任务目录结构"""
        task_dir = self.get_task_dir(task_id)

        structure = {
            "root": task_dir,
            "input": task_dir / "input",
            "processed": task_dir / "processed",
            "outputs": task_dir / "outputs",
        }

        for path in structure.values():
            path.mkdir(parents=True, exist_ok=True)

        return structure

    def get_language_output_dir(self, task_id: str, language: str) -> Path:
        """获取语言输出目录"""
        output_dir = self.get_task_dir(task_id) / "outputs" / language
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def get_cloned_audio_dir(self, task_id: str, language: str) -> Path:
        """获取克隆音频目录"""
        audio_dir = self.get_language_output_dir(task_id, language) / "cloned_audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        return audio_dir

    def get_export_path(self, task_id: str, language: str) -> Path:
        """获取导出视频路径"""
        return self.get_language_output_dir(task_id, language) / f"export_{language}.mp4"

    def delete_task(self, task_id: str):
        """删除任务所有文件"""
        task_dir = self.get_task_dir(task_id)
        if task_dir.exists():
            shutil.rmtree(task_dir)

# 全局文件管理器实例
file_manager = TaskFileManager()
```

---

## 阶段 2: 后端 API 实现 (第3-4天)

### 步骤 2.1: 任务 CRUD API
**文件**: `backend/routers/tasks.py`

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import shutil

from database import get_db
from models.task import Task as TaskModel
from file_manager import file_manager
from task_queue import task_queue

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# Pydantic 模型
class TaskCreate(BaseModel):
    target_languages: List[str] = []

class TaskResponse(BaseModel):
    id: int
    task_id: str
    video_filename: str
    video_original_name: str
    status: str
    language_status: dict
    config: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LanguageProcessRequest(BaseModel):
    stage: str  # speaker_diarization, translation, voice_cloning, export

@router.post("/", response_model=TaskResponse)
async def create_task(
    video: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """创建新任务并上传视频"""
    # 生成任务ID
    task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    # 创建目录结构
    structure = file_manager.create_task_structure(task_id)

    # 保存视频文件
    video_filename = f"{task_id}_{video.filename}"
    video_path = structure["input"] / video_filename

    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # 创建数据库记录
    db_task = TaskModel(
        task_id=task_id,
        video_filename=video_filename,
        video_original_name=video.filename,
        status="pending",
        language_status={},
        config={"target_languages": []}
    )

    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    return db_task

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """获取任务列表"""
    tasks = db.query(TaskModel).order_by(TaskModel.created_at.desc()).offset(skip).limit(limit).all()
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取单个任务详情"""
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 删除文件
    file_manager.delete_task(task_id)

    # 删除数据库记录
    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}

@router.post("/{task_id}/languages/{language}/process")
async def process_language(
    task_id: str,
    language: str,
    request: LanguageProcessRequest,
    db: Session = Depends(get_db)
):
    """启动语言处理任务"""
    task = db.query(TaskModel).filter(TaskModel.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 根据不同阶段提交任务到队列
    # (这里需要集成现有的处理函数)

    return {"message": f"Started {request.stage} for {language}"}
```

### 步骤 2.2: WebSocket 进度推送
**文件**: `backend/routers/websocket.py`

```python
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

    def disconnect(self, task_id: str, websocket: WebSocket):
        if task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]

    async def broadcast_to_task(self, task_id: str, message: dict):
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
            # 保持连接
            await websocket.receive_text()
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
```

### 步骤 2.3: 在 main.py 注册路由
**修改**: `backend/main.py`

```python
# 在文件开头添加导入
from routers import tasks, websocket
from database import init_db

# 在 app 创建后添加
@app.on_event("startup")
async def startup_event():
    init_db()

app.include_router(tasks.router)
app.include_router(websocket.router)
```

---

## 阶段 3: 前端路由和页面结构 (第5-6天)

### 步骤 3.1: 安装依赖
```bash
cd frontend
npm install react-router-dom@6
npm install axios
```

### 步骤 3.2: 创建路由配置
**文件**: `frontend/src/App.tsx`

```typescript
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import TaskDashboard from './pages/TaskDashboard';
import TaskEditor from './pages/TaskEditor';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<TaskDashboard />} />
        <Route path="/tasks/:taskId" element={<TaskEditor />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
```

### 步骤 3.3: 创建任务看板页面
**文件**: `frontend/src/pages/TaskDashboard.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Upload, Play, Trash2, Plus } from 'lucide-react';

interface Task {
  id: number;
  task_id: string;
  video_filename: string;
  video_original_name: string;
  status: string;
  language_status: Record<string, { status: string; progress: number }>;
  config: { target_languages: string[] };
  created_at: string;
}

const TaskDashboard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [uploading, setUploading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchTasks();
  }, []);

  const fetchTasks = async () => {
    try {
      const response = await axios.get('/api/tasks');
      setTasks(response.data);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    const formData = new FormData();
    formData.append('video', file);

    try {
      const response = await axios.post('/api/tasks', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setTasks([response.data, ...tasks]);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (taskId: string) => {
    if (!confirm('确定删除此任务？')) return;

    try {
      await axios.delete(`/api/tasks/${taskId}`);
      setTasks(tasks.filter(t => t.task_id !== taskId));
    } catch (error) {
      console.error('Delete failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <div className="max-w-7xl mx-auto">
        {/* 头部 */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-white">任务看板</h1>

          <label className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-purple-500 text-white px-6 py-3 rounded-lg cursor-pointer hover:shadow-lg transition-all">
            <Plus size={20} />
            <span>上传新视频</span>
            <input
              type="file"
              accept="video/*"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleUpload(e.target.files[0])}
              disabled={uploading}
            />
          </label>
        </div>

        {/* 任务网格 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {tasks.map(task => (
            <TaskCard
              key={task.task_id}
              task={task}
              onOpen={() => navigate(`/tasks/${task.task_id}`)}
              onDelete={() => handleDelete(task.task_id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

interface TaskCardProps {
  task: Task;
  onOpen: () => void;
  onDelete: () => void;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onOpen, onDelete }) => {
  const languages = ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id'];
  const languageNames: Record<string, string> = {
    en: '英语', ko: '韩语', ja: '日语', fr: '法语',
    de: '德语', es: '西语', id: '印尼语'
  };

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 hover:border-purple-500 transition-all">
      {/* 视频信息 */}
      <div className="mb-4">
        <h3 className="text-white font-semibold truncate mb-2">
          {task.video_original_name}
        </h3>
        <p className="text-sm text-slate-400">
          {new Date(task.created_at).toLocaleString('zh-CN')}
        </p>
      </div>

      {/* 语言进度 */}
      <div className="space-y-2 mb-4">
        {languages.map(lang => {
          const langStatus = task.language_status[lang];
          const status = langStatus?.status || 'idle';
          const progress = langStatus?.progress || 0;

          return (
            <div key={lang} className="flex items-center gap-2">
              <span className="text-xs text-slate-400 w-12">{languageNames[lang]}</span>
              <div className="flex-1 bg-slate-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    status === 'completed' ? 'bg-green-500' :
                    status === 'processing' ? 'bg-blue-500' :
                    status === 'failed' ? 'bg-red-500' : 'bg-slate-600'
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-slate-400 w-8">{progress}%</span>
            </div>
          );
        })}
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button
          onClick={onOpen}
          className="flex-1 flex items-center justify-center gap-2 bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-500 transition-all"
        >
          <Play size={16} />
          <span>打开</span>
        </button>
        <button
          onClick={onDelete}
          className="px-3 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 transition-all"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
};

export default TaskDashboard;
```

### 步骤 3.4: 创建任务编辑器页面（集成现有UI）
**文件**: `frontend/src/pages/TaskEditor.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import axios from 'axios';

// 导入现有组件
import VideoPlayer from '../components/VideoPlayer';
import SubtitlePanel from '../components/SubtitlePanel';
import PropertiesPanel from '../components/PropertiesPanel';

const TaskEditor: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<any>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    if (!taskId) return;

    // 获取任务信息
    fetchTask();

    // 建立 WebSocket 连接
    const ws = new WebSocket(`ws://localhost:8080/ws/tasks/${taskId}`);

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleProgressUpdate(data);
    };

    return () => ws.close();
  }, [taskId]);

  const fetchTask = async () => {
    try {
      const response = await axios.get(`/api/tasks/${taskId}`);
      setTask(response.data);
    } catch (error) {
      console.error('Failed to fetch task:', error);
    }
  };

  const handleProgressUpdate = (data: any) => {
    // 更新进度状态
    console.log('Progress update:', data);
    // TODO: 更新本地状态
  };

  if (!task) {
    return <div className="flex items-center justify-center h-screen bg-slate-900 text-white">加载中...</div>;
  }

  return (
    <div className="h-screen bg-slate-900 flex flex-col">
      {/* 顶部导航 */}
      <div className="bg-slate-800 border-b border-slate-700 px-6 py-4 flex items-center gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 text-slate-300 hover:text-white transition-colors"
        >
          <ArrowLeft size={20} />
          <span>返回看板</span>
        </button>

        <div className="flex-1">
          <h2 className="text-white font-semibold">{task.video_original_name}</h2>
          <p className="text-sm text-slate-400">任务 ID: {task.task_id}</p>
        </div>

        {wsConnected && (
          <div className="flex items-center gap-2 text-green-400 text-sm">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            <span>实时连接</span>
          </div>
        )}
      </div>

      {/* 主编辑器（复用现有布局） */}
      <div className="flex-1 flex overflow-hidden">
        {/* TODO: 集成现有的 VideoPlayer, SubtitlePanel, PropertiesPanel */}
        {/* 需要将它们改造为接收 taskId 作为参数 */}
      </div>
    </div>
  );
};

export default TaskEditor;
```

---

## 阶段 4: 集成现有功能 (第7-9天)

### 步骤 4.1: 重构现有 API 以支持任务 ID
需要修改的核心函数:
- `/upload` → 改为从 tasks 目录读取
- `/speaker-diarization` → 接收 task_id 参数
- `/translate-subtitles` → 接收 task_id 参数
- `/voice-cloning` → 接收 task_id 参数
- `/export` → 接收 task_id 和 language 参数

### 步骤 4.2: 进度推送集成
在现有的处理函数中添加 WebSocket 推送:

```python
# 在 speaker diarization 处理中
from routers.websocket import update_progress

async def process_speaker_diarization(task_id: str, ...):
    await update_progress(task_id, "base", "speaker_diarization", 10, "正在加载模型...")
    # ... 处理逻辑
    await update_progress(task_id, "base", "speaker_diarization", 50, "识别中...")
    # ... 处理逻辑
    await update_progress(task_id, "base", "speaker_diarization", 100, "完成")
```

### 步骤 4.3: 轮询备用方案
**文件**: `frontend/src/hooks/useTaskProgress.ts`

```typescript
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

export const useTaskProgress = (taskId: string) => {
  const [progress, setProgress] = useState<any>({});
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // 尝试 WebSocket 连接
    connectWebSocket();

    // 启动轮询作为备份
    startPolling();

    return () => {
      wsRef.current?.close();
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [taskId]);

  const connectWebSocket = () => {
    const ws = new WebSocket(`ws://localhost:8080/ws/tasks/${taskId}`);

    ws.onopen = () => {
      setIsConnected(true);
      // WebSocket 连接成功，停止轮询
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      updateProgress(data);
    };

    ws.onclose = () => {
      setIsConnected(false);
      // WebSocket 断开，恢复轮询
      startPolling();
    };

    wsRef.current = ws;
  };

  const startPolling = () => {
    if (pollingRef.current) return; // 已经在轮询

    pollingRef.current = setInterval(async () => {
      try {
        const response = await axios.get(`/api/tasks/${taskId}`);
        setProgress(response.data.language_status);
      } catch (error) {
        console.error('Polling failed:', error);
      }
    }, 2000); // 每2秒轮询一次
  };

  const updateProgress = (data: any) => {
    setProgress((prev: any) => ({
      ...prev,
      [data.language]: {
        ...prev[data.language],
        [data.stage]: {
          progress: data.progress,
          message: data.message
        }
      }
    }));
  };

  return { progress, isConnected };
};
```

---

## 阶段 5: 测试和优化 (第10-11天)

### 步骤 5.1: 功能测试清单
- [ ] 上传视频创建任务
- [ ] 任务列表显示正确
- [ ] 点击任务打开编辑器
- [ ] 说话人识别进度实时更新
- [ ] 多语言翻译独立处理
- [ ] 语音克隆进度独立显示
- [ ] 导出视频到正确目录
- [ ] WebSocket 断线自动切换轮询
- [ ] 删除任务清理文件
- [ ] 多任务并发处理

### 步骤 5.2: 性能优化
- 数据库索引优化 (task_id, created_at)
- 文件缓存策略
- WebSocket 连接池管理
- 任务队列优先级调度

---

## 阶段 6: 部署准备 (第12天)

### 步骤 6.1: 环境变量配置
**文件**: `backend/.env.example`

```env
DATABASE_URL=sqlite:///./localclip.db
TASK_QUEUE_WORKERS=4
UPLOAD_DIR=./tasks
MAX_VIDEO_SIZE_MB=500
```

### 步骤 6.2: 启动脚本更新
**修改**: `start.bat`

添加数据库初始化:
```batch
echo [X/Y] Initializing database...
python -c "from database import init_db; init_db()"
```

---

## 总结

### 关键技术点
1. **SQLite + SQLAlchemy**: 轻量级持久化
2. **ThreadPoolExecutor**: 简单任务队列，无需 Celery
3. **WebSocket + 轮询**: 自动降级保证可靠性
4. **目录组织**: tasks/{task_id}/{input|processed|outputs/{lang}}
5. **React Router**: 无需后端多页支持

### 预期工作量
- **后端**: 约 1500 行代码（数据库模型、API、队列管理）
- **前端**: 约 800 行代码（Dashboard、Editor、Hooks）
- **总时间**: 9-12 天（单人开发）

### 下一步
建议按阶段顺序实施，每完成一个阶段进行集成测试，确保各模块独立可用。
