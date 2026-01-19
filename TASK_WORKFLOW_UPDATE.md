# 任务工作流更新说明

**日期**: 2026-01-17
**版本**: Task-Driven Workflow Update

---

## 📋 更新概述

完成了从"编辑器上传素材"到"任务看板上传素材"的工作流转换，使整个应用完全基于任务驱动。

---

## ✅ 完成的改造

### 1. 任务看板增强 (TaskDashboard.tsx)

**新增功能**:
- ✅ 创建新任务时可同时上传视频和字幕
- ✅ 视频文件为必填项
- ✅ 字幕文件为可选项
- ✅ 模态框式上传界面，用户体验友好

**实现细节**:
```typescript
// 状态管理
const [showUploadModal, setShowUploadModal] = useState(false);
const [videoFile, setVideoFile] = useState<File | null>(null);
const [subtitleFile, setSubtitleFile] = useState<File | null>(null);

// 上传处理
const handleUploadSubmit = async () => {
  const formData = new FormData();
  formData.append('video', videoFile);
  if (subtitleFile) {
    formData.append('subtitle', subtitleFile);
  }

  const response = await axios.post('/api/tasks/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });

  // 自动跳转到新创建的任务编辑器
  navigate(`/tasks/${response.data.task_id}`);
};
```

**UI 变化**:
- 原来: 简单的文件选择按钮
- 现在: "创建新任务" 按钮 → 打开模态框 → 视频（必填）+ 字幕（可选）

---

### 2. 后端 API 增强 (backend/routers/tasks.py)

#### 2.1 任务创建 API 更新

**原接口**:
```python
POST /api/tasks/
参数: video (必填)
```

**新接口**:
```python
POST /api/tasks/
参数:
  - video (必填, UploadFile)
  - subtitle (可选, UploadFile)

功能:
  - 创建任务目录结构
  - 保存视频到 {task_id}/input/
  - 保存字幕到 {task_id}/processed/source_subtitle.srt (如果提供)
  - 更新任务配置中的字幕信息
```

#### 2.2 新增视频信息 API

```python
GET /api/tasks/{task_id}/video-info

返回:
{
  "size": 12345678,
  "duration": 120.5,
  "width": 1920,
  "height": 1080,
  "resolution": "1920x1080",
  "bitrate": "5000000",
  "codec": "h264"
}

说明: 使用 ffprobe 获取视频详细信息
```

#### 2.3 新增字幕获取 API

```python
GET /api/tasks/{task_id}/subtitle

返回:
{
  "subtitles": [
    {
      "start_time": 0.0,
      "end_time": 2.5,
      "start_time_formatted": "00:00:00,000",
      "end_time_formatted": "00:00:02,500",
      "text": "字幕内容"
    }
  ],
  "filename": "source_subtitle.srt"
}

说明: 解析 SRT 文件返回字幕数据
```

---

### 3. 编辑器改造 (TaskEditorOld.tsx)

#### 3.1 移除素材库上传功能

**变更**:
- ✅ 移除了 Sidebar 组件的 `onVideoUpload` 和 `onSubtitleUpload` props
- ✅ 移除了相关的上传处理函数
- ✅ Sidebar 现在只显示处理进度，不再提供上传功能

**Sidebar 组件简化**:
```typescript
// 原来
<Sidebar
  videos={videos}
  onVideoSelect={setCurrentVideo}
  onVideoUpload={handleVideoUpload}
  onSubtitleUpload={handleSubtitleUpload}
/>

// 现在
<Sidebar />
```

#### 3.2 从任务数据加载视频和字幕

**新增功能**:
```typescript
// 1. 使用 useParams 获取任务 ID
const { taskId } = useParams<{ taskId: string }>();

// 2. 加载任务数据
useEffect(() => {
  const loadTaskData = async () => {
    // 获取任务信息
    const taskResponse = await axios.get(`/api/tasks/${taskId}`);

    // 加载视频
    const videoInfoResponse = await axios.get(`/api/tasks/${taskId}/video-info`);
    const videoFile: VideoFile = {
      filename: task.video_filename,
      original_name: task.video_original_name,
      size: videoInfo.size,
      video_info: videoInfo
    };
    setCurrentVideo(videoFile);

    // 加载字幕（如果存在）
    if (task.config?.source_subtitle_filename) {
      const subtitleResponse = await axios.get(`/api/tasks/${taskId}/subtitle`);
      setSubtitles(subtitleResponse.data.subtitles);
    }
  };

  loadTaskData();
}, [taskId]);

// 3. 更新视频路径
<VideoPlayer
  src={`/uploads/${taskId}/input/${currentVideo.filename}`}
  ...
/>
```

---

### 4. Sidebar 组件重构 (frontend/src/components/Sidebar.tsx)

**变更**:
- ✅ 移除所有上传相关的代码
- ✅ 移除 props: `videos`, `onVideoSelect`, `onVideoUpload`, `onSubtitleUpload`
- ✅ 标题从"素材库"改为"处理进度"
- ✅ 专注于显示语言处理进度

**简化后的结构**:
```typescript
interface SidebarProps {}

const Sidebar: React.FC<SidebarProps> = () => {
  return (
    <div className="w-72 ...">
      {/* 标题 */}
      <div className="p-5 ...">
        <h2>处理进度</h2>
      </div>

      {/* 语言进度显示 */}
      <LanguageProgressSidebar />

      {/* 底部说明 */}
      <div className="p-4 ...">
        <p>实时显示各语言处理进度</p>
      </div>
    </div>
  );
};
```

---

## 🔄 工作流变化

### 原工作流
```
1. 用户进入编辑器
2. 在编辑器侧边栏上传视频
3. 在编辑器侧边栏上传字幕
4. 开始编辑和处理
```

### 新工作流
```
1. 用户在任务看板点击"创建新任务"
2. 在模态框中上传视频（必填）和字幕（可选）
3. 系统创建任务，自动跳转到编辑器
4. 编辑器自动加载任务的视频和字幕
5. 用户直接开始编辑和处理
```

---

## 📂 文件目录结构

### 任务目录结构
```
uploads/
└── {task_id}/
    ├── input/              # 输入文件
    │   └── {task_id}_video.mp4
    ├── processed/          # 处理文件
    │   └── source_subtitle.srt  # 原始字幕
    └── outputs/            # 输出文件
        └── {language}/
            ├── translated.srt
            ├── cloned_audio/
            └── final_video.mp4
```

### 数据库结构
```json
{
  "task_id": "task_20260117_123456_abc123",
  "video_filename": "task_20260117_123456_abc123_video.mp4",
  "video_original_name": "video.mp4",
  "status": "pending",
  "config": {
    "source_subtitle_filename": "source_subtitle.srt",
    "target_languages": ["English", "Korean", "Japanese"]
  },
  "language_status": {
    "English": {
      "speaker_diarization": {
        "status": "completed",
        "progress": 100
      },
      "translation": {
        "status": "processing",
        "progress": 45
      }
    }
  }
}
```

---

## 🎯 优势

### 1. 更清晰的任务边界
- ✅ 每个任务都有独立的目录
- ✅ 文件不会混淆
- ✅ 易于管理和清理

### 2. 更好的用户体验
- ✅ 创建任务时就准备好所有素材
- ✅ 进入编辑器即可直接开始工作
- ✅ 不需要在编辑器中管理文件

### 3. 更强的数据完整性
- ✅ 视频和字幕与任务绑定
- ✅ 所有处理结果都在任务目录下
- ✅ 易于备份和恢复

### 4. 更简洁的编辑器
- ✅ 编辑器专注于编辑功能
- ✅ 侧边栏专注于进度显示
- ✅ 职责分离更清晰

---

## 🧪 测试要点

### 功能测试

1. **任务创建**
   - [ ] 只上传视频（不上传字幕）
   - [ ] 同时上传视频和字幕
   - [ ] 检查任务目录结构
   - [ ] 检查数据库记录

2. **编辑器加载**
   - [ ] 从任务看板进入编辑器
   - [ ] 视频正确加载和播放
   - [ ] 字幕正确加载和显示
   - [ ] 视频信息正确显示

3. **侧边栏**
   - [ ] 不再显示上传按钮
   - [ ] 正确显示语言进度
   - [ ] 实时更新进度状态

### 路径测试

1. **视频路径**
   ```
   原路径: /uploads/video.mp4
   新路径: /uploads/task_xxx/input/task_xxx_video.mp4
   ```

2. **字幕路径**
   ```
   原路径: /uploads/subtitle.srt
   新路径: /uploads/task_xxx/processed/source_subtitle.srt
   ```

### 错误处理

1. **任务不存在**
   - [ ] 访问不存在的任务 ID
   - [ ] 显示友好的错误信息

2. **文件不存在**
   - [ ] 任务存在但视频文件被删除
   - [ ] 任务存在但字幕文件不存在
   - [ ] 正确处理这些情况

---

## 📝 API 变更总结

| 端点 | 方法 | 变更类型 | 说明 |
|------|------|---------|------|
| `/api/tasks/` | POST | 修改 | 新增可选 `subtitle` 参数 |
| `/api/tasks/{task_id}/video-info` | GET | 新增 | 获取视频详细信息 |
| `/api/tasks/{task_id}/subtitle` | GET | 新增 | 获取字幕数据 |
| `/api/tasks/{task_id}/subtitle` | POST | 保留 | 单独上传字幕（已存在） |

---

## 🚀 下一步

现在整个系统已经完全基于任务驱动，可以继续进行：

1. **Phase 4 剩余工作**
   - 提取翻译逻辑到 processing.py
   - 提取语音克隆逻辑到 processing.py
   - 实现导出功能
   - 端到端测试

2. **优化建议**
   - 添加上传进度显示
   - 支持视频预览（创建任务时）
   - 支持批量创建任务
   - 添加任务模板功能

---

## 📚 相关文档

- [Phase 4 架构更新](./PHASE4_ARCHITECTURE_UPDATE.md)
- [Phase 4 UI 更新](./PHASE4_UI_UPDATES.md)
- [Phase 4 完成总结](./PHASE4_COMPLETION_SUMMARY.md)

---

**更新时间**: 2026-01-17
**状态**: ✅ 工作流改造完成，待测试
