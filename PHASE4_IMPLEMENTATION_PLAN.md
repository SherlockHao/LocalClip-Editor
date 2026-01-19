# Phase 4 实施计划

## 📋 概述

Phase 4 的目标是将现有的视频处理流程（上传、说话人识别、翻译、语音克隆）完整集成到 Phase 1-3 建立的任务系统中。

## 🎯 核心目标

1. **统一文件管理**: 所有文件使用任务目录结构
2. **任务状态追踪**: 每个处理步骤更新任务状态
3. **实时进度推送**: WebSocket 推送处理进度
4. **编辑器集成**: 编辑器从 URL 读取 task_id 并加载任务数据

## 📊 当前系统分析

### 现有 API 端点

| API 端点 | 功能 | 当前文件路径 | 状态追踪 |
|---------|------|------------|---------|
| `POST /upload/video` | 上传视频 | `uploads/{uuid}.mp4` | 无 |
| `POST /speaker-diarization/process` | 说话人识别 | `uploads/` | `speaker_processing_status` 字典 |
| `POST /translate/batch` | 批量翻译 | `uploads/` | `translation_status` 字典 |
| `POST /voice-cloning/process` | 语音克隆 | `uploads/`, `cloned-audio/` | `voice_cloning_status` 字典 |
| `POST /export` | 导出视频 | `exports/` | 无 |

### 现有问题

1. **文件分散**: 文件存储在全局 `uploads/` 目录，难以管理
2. **状态分散**: 每个处理步骤使用独立的状态字典
3. **无持久化**: 状态只在内存中，服务重启后丢失
4. **无任务关联**: 处理步骤之间缺乏关联
5. **无进度推送**: 前端需要轮询获取状态

## 🔄 改造方案

### 方案 1: 渐进式改造（推荐）

**优点**:
- 风险低，可以逐步测试
- 保留原有 API 作为后备
- 可以分阶段部署

**步骤**:
1. 保留原有 API 端点不变
2. 创建新的任务导向 API (`/api/tasks/{task_id}/...`)
3. 前端逐步迁移到新 API
4. 验证稳定后移除旧 API

### 方案 2: 直接改造（快速）

**优点**:
- 代码更简洁
- 避免维护两套 API

**缺点**:
- 需要同时修改前后端
- 一次性改动较大

### 最终选择: 方案 1（渐进式改造）

考虑到系统复杂性和稳定性，采用渐进式改造。

## 🏗️ 架构设计

### 新的文件目录结构

```
tasks/
└── {task_id}/
    ├── input/
    │   └── video.mp4                    # 原始视频
    ├── processed/
    │   ├── audio.wav                    # 提取的音频
    │   ├── source_subtitle.srt          # 原始字幕
    │   ├── speaker_segments/            # 说话人音频片段
    │   │   ├── segment_0001.wav
    │   │   └── ...
    │   └── speaker_data.json            # 说话人聚类数据
    └── outputs/
        ├── English/
        │   ├── translated.srt
        │   ├── cloned_audio/
        │   │   ├── segment_0001.wav
        │   │   └── ...
        │   ├── stitched_audio.wav
        │   └── final_video.mp4
        ├── Korean/
        └── ...
```

### 数据库结构（已有）

**Task 表**:
```python
{
    "task_id": "task_20260117_...",
    "status": "pending|processing|completed|failed",
    "language_status": {
        "English": {
            "speaker_diarization": {"status": "completed", "progress": 100},
            "translation": {"status": "processing", "progress": 45},
            "voice_cloning": {"status": "pending", "progress": 0},
            "export": {"status": "pending", "progress": 0}
        },
        "Korean": {...}
    },
    "config": {
        "target_languages": ["English", "Korean"],
        "video_filename": "video.mp4",
        "source_subtitle_filename": "source_subtitle.srt"
    }
}
```

### WebSocket 消息格式

```json
{
    "type": "progress_update",
    "task_id": "task_20260117_...",
    "language": "English",
    "stage": "translation",
    "progress": 45,
    "message": "正在翻译第 45/100 条字幕..."
}
```

## 📝 实施步骤

### Step 1: 创建进度更新辅助函数

创建 `backend/progress_manager.py`:

```python
from database import SessionLocal
from models.task import Task
from routers.websocket import manager
import json

async def update_task_progress(
    task_id: str,
    language: str,
    stage: str,
    progress: int,
    message: str,
    status: str = "processing"
):
    """更新任务进度并推送 WebSocket"""
    db = SessionLocal()
    try:
        # 更新数据库
        task = db.query(Task).filter(Task.task_id == task_id).first()
        if task:
            language_status = task.language_status or {}
            if language not in language_status:
                language_status[language] = {}

            language_status[language][stage] = {
                "status": status,
                "progress": progress,
                "message": message
            }

            task.language_status = language_status
            db.commit()

        # 推送 WebSocket
        await manager.broadcast_to_task(task_id, {
            "type": "progress_update",
            "task_id": task_id,
            "language": language,
            "stage": stage,
            "progress": progress,
            "message": message,
            "status": status
        })
    finally:
        db.close()
```

### Step 2: 修改视频上传 API

**选项 A**: 废弃旧端点 `POST /upload/video`，改用 `POST /api/tasks/` ✅

**原因**: Phase 3 已经实现了新的上传 API，前端已经使用

**需要做的**:
- 前端已经迁移到新 API
- 旧的 `/upload/video` 可以标记为 deprecated

### Step 3: 创建任务关联的处理 API

创建新的路由文件 `backend/routers/processing.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.task import Task
from progress_manager import update_task_progress

router = APIRouter(prefix="/api/tasks", tags=["processing"])

@router.post("/{task_id}/languages/{language}/speaker-diarization")
async def process_speaker_diarization(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """启动说话人识别（任务关联版本）"""
    # 1. 验证任务存在
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 2. 获取任务文件路径
    video_path = f"tasks/{task_id}/input/{task.video_filename}"
    subtitle_path = f"tasks/{task_id}/processed/source_subtitle.srt"

    # 3. 启动后台处理
    # ... 调用现有的处理函数，但使用任务目录

    return {"message": "说话人识别已启动"}
```

### Step 4: 重构现有处理函数

将现有的处理函数改造为支持任务系统：

```python
async def run_speaker_diarization_with_task(
    task_id: str,
    language: str,
    video_path: str,
    subtitle_path: str
):
    """支持任务系统的说话人识别"""
    try:
        # 更新进度: 开始
        await update_task_progress(
            task_id, language, "speaker_diarization",
            0, "开始音频提取...", "processing"
        )

        # 步骤 1: 音频提取
        # ... 现有代码
        await update_task_progress(
            task_id, language, "speaker_diarization",
            25, "音频提取完成，开始特征提取...", "processing"
        )

        # 步骤 2: 特征提取
        # ... 现有代码
        await update_task_progress(
            task_id, language, "speaker_diarization",
            50, "特征提取完成，开始说话人聚类...", "processing"
        )

        # 步骤 3: 聚类
        # ... 现有代码
        await update_task_progress(
            task_id, language, "speaker_diarization",
            100, "说话人识别完成", "completed"
        )

    except Exception as e:
        await update_task_progress(
            task_id, language, "speaker_diarization",
            0, f"错误: {str(e)}", "failed"
        )
```

### Step 5: 改造编辑器

修改 `frontend/src/pages/TaskEditorOld.tsx`:

```typescript
import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import axios from 'axios';

function TaskEditor() {
    const { taskId } = useParams();  // 从 URL 获取 task_id
    const [task, setTask] = useState(null);

    useEffect(() => {
        // 加载任务数据
        axios.get(`/api/tasks/${taskId}`)
            .then(res => {
                setTask(res.data);
                // 设置视频 URL
                const videoUrl = `/uploads/${res.data.video_filename}`;
                // ... 加载视频
            });
    }, [taskId]);

    // 启动处理时使用任务 API
    const handleSpeakerDiarization = async (language) => {
        await axios.post(
            `/api/tasks/${taskId}/languages/${language}/speaker-diarization`
        );
    };

    // ... 其他处理函数类似
}
```

### Step 6: 实现导出功能

```python
@router.post("/{task_id}/languages/{language}/export")
async def export_video(
    task_id: str,
    language: str,
    db: Session = Depends(get_db)
):
    """导出指定语言的最终视频"""
    task = db.query(Task).filter(Task.task_id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 输出路径
    output_dir = f"tasks/{task_id}/outputs/{language}"
    output_video = f"{output_dir}/final_video.mp4"

    # 合并视频和音频
    # ... 使用 ffmpeg

    await update_task_progress(
        task_id, language, "export",
        100, "导出完成", "completed"
    )

    return {
        "video_url": f"/exports/{task_id}/{language}/final_video.mp4",
        "message": "导出成功"
    }
```

## ⚠️ 风险和注意事项

### 1. 文件路径迁移

**风险**: 现有代码大量使用 `UPLOADS_DIR` 全局路径

**解决**:
- 创建路径辅助函数 `get_task_paths(task_id)`
- 逐步替换硬编码路径

### 2. 状态字典依赖

**风险**: 现有代码依赖内存中的状态字典

**解决**:
- 保留状态字典作为缓存
- 同时更新数据库
- 添加数据库 → 状态字典的同步机制

### 3. 异步处理复杂性

**风险**: WebSocket 推送在异步任务中可能失败

**解决**:
- 使用 try-catch 包裹 WebSocket 推送
- 推送失败不影响主流程
- 前端保留轮询作为后备

### 4. 前端兼容性

**风险**: 大量现有前端代码需要修改

**解决**:
- 采用渐进式改造
- 保留旧 API 作为后备
- 分功能模块逐步迁移

## 📅 实施时间线

### Phase 4.1: 基础设施（1-2 小时）
- [x] 创建 `progress_manager.py`
- [x] 创建 `routers/processing.py`
- [x] 添加路径辅助函数

### Phase 4.2: 说话人识别集成（1-2 小时）
- [ ] 重构 `run_speaker_diarization_process`
- [ ] 添加进度推送
- [ ] 测试完整流程

### Phase 4.3: 翻译集成（1 小时）
- [ ] 重构 `run_batch_translation`
- [ ] 添加进度推送
- [ ] 测试翻译流程

### Phase 4.4: 语音克隆集成（1-2 小时）
- [ ] 重构 `run_voice_cloning_process`
- [ ] 添加进度推送
- [ ] 测试克隆流程

### Phase 4.5: 编辑器改造（2-3 小时）
- [ ] 修改 TaskEditorOld.tsx 读取 task_id
- [ ] 更新所有 API 调用
- [ ] 测试完整工作流

### Phase 4.6: 导出功能（1 小时）
- [ ] 实现按语言导出
- [ ] 添加下载链接
- [ ] 测试导出功能

### Phase 4.7: 完整测试（1-2 小时）
- [ ] 端到端测试
- [ ] 性能测试
- [ ] 错误处理测试

**总计**: 约 8-14 小时

## ✅ 验收标准

### 功能完整性
- [ ] 可以创建任务并上传视频
- [ ] 可以启动说话人识别
- [ ] 可以翻译到多种语言
- [ ] 可以进行语音克隆
- [ ] 可以导出最终视频
- [ ] 所有文件存储在任务目录

### 进度追踪
- [ ] 每个处理步骤更新数据库
- [ ] WebSocket 实时推送进度
- [ ] 前端显示实时进度
- [ ] 进度条准确反映处理状态

### 稳定性
- [ ] 错误处理完善
- [ ] 服务重启后可恢复
- [ ] 文件管理正确
- [ ] 无内存泄漏

### 用户体验
- [ ] 编辑器自动加载任务数据
- [ ] 进度实时更新无延迟
- [ ] 导出文件易于下载
- [ ] 错误提示清晰

## 📚 参考文档

- [BATCH_SYSTEM_IMPLEMENTATION.md](./BATCH_SYSTEM_IMPLEMENTATION.md) - Phase 1-3 实施指南
- [PHASE1-3_COMPLETE_REPORT.md](./PHASE1-3_COMPLETE_REPORT.md) - Phase 1-3 完成报告
- FastAPI 文档: https://fastapi.tiangolo.com/
- SQLAlchemy 文档: https://docs.sqlalchemy.org/

---

**准备开始实施!** 🚀
