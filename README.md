# LocalClip Editor

一个基于 Mac Mini M4 的本地视频编辑应用，支持视频剪辑、SRT字幕编辑和导出功能。

## 技术栈

- **后端**: Python FastAPI + FFmpeg
- **前端**: React + Vite + TypeScript + Tailwind CSS + Shadcn/UI
- **视频处理**: FFmpeg (支持 h264_videotoolbox 硬件加速)

## 功能特性

- 🎬 多格式视频支持 (MP4, MOV, AVI, MKV)
- 📝 SRT 字幕解析和可视化时间轴
- ⚡ 自适应视频预览 (保持原始宽高比)
- 🎨 HeyGen 风格的现代化 UI
- 🚀 Mac M4 芯片硬件加速导出
- 💾 硬字幕烧录导出

## 系统要求

- macOS (推荐 Mac Mini M4 或 Apple Silicon 芯片)
- Python 3.8+
- Node.js 16+
- FFmpeg

## 安装指南

### 1. 安装 FFmpeg

```bash
# 使用 Homebrew 安装 FFmpeg
brew install ffmpeg

# 验证安装
ffmpeg -version
```

### 2. 克隆项目

```bash
git clone <repository-url>
cd LocalClip-Editor
```

### 3. 后端设置

```bash
# 进入后端目录
cd backend

# 创建虚拟环境 (推荐)
python3 -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装 Python 依赖
pip install -r requirements.txt
```

### 4. 前端设置

```bash
# 进入前端目录
cd ../frontend

# 安装 Node.js 依赖
npm install
```

## 启动应用

### 方法一：使用一键启动脚本 (推荐)

```bash
# 在项目根目录执行
chmod +x start.sh
./start.sh
```

该脚本会自动：
- 清理之前占用8000和5173端口的进程
- 启动后端服务 (端口 8000)
- 启动前端服务 (端口 5173)

### 方法二：手动启动

```bash
# 终端1：启动后端服务
cd backend
source venv/bin/activate  # 如果使用了虚拟环境
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 终端2：启动前端服务
cd frontend
npm run dev
```

## 访问应用

打开浏览器访问: http://localhost:5173

API 文档: http://localhost:8000/docs

## 项目结构

```
LocalClip-Editor/
├── backend/           # Python FastAPI 后端
│   ├── main.py       # 主服务器文件
│   ├── video_processor.py  # 视频处理工具
│   └── srt_parser.py # SRT 字幕解析器
├── frontend/         # React 前端
│   ├── src/
│   │   ├── components/
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── SubtitleTimeline.tsx
│   │   │   └── ...
│   │   └── App.tsx
│   └── package.json
├── uploads/          # 上传文件存储
├── exports/          # 导出文件存储
├── README.md
└── start.sh         # 一键启动脚本（带端口清理功能）
```

## 使用说明

1. **上传视频**: 点击左侧素材库的"上传视频"按钮
2. **添加字幕**: 上传 SRT 字幕文件或在时间轴手动添加
3. **编辑预览**: 在中央预览窗口查看效果，使用底部时间轴精确定位
4. **导出视频**: 在右侧属性面板设置导出参数，点击"导出"

## 性能优化

- 自动检测并使用 `h264_videotoolbox` 硬件编码器
- 智能内存管理，避免大文件处理时的内存溢出
- 响应式设计，适配不同屏幕尺寸

## 故障排除

### FFmpeg 相关问题

```bash
# 如果 FFmpeg 未找到路径
which ffmpeg
# 确保 /opt/homebrew/bin/ffmpeg 在 PATH 中

# 重新安装 FFmpeg
brew reinstall ffmpeg
```

### 端口占用问题

一键启动脚本会自动清理之前占用的端口。如果需要手动清理：

```bash
# 查看端口占用
lsof -i :8000  # 后端端口
lsof -i :5173  # 前端端口

# 杀死占用进程
kill -9 <PID>
```

## 开发说明

### 后端 API 接口

- `POST /upload/video` - 上传视频文件
- `POST /upload/subtitle` - 上传字幕文件
- `GET /videos` - 获取视频列表
- `POST /export` - 导出视频

### 前端组件架构

- `App.tsx` - 主布局组件
- `VideoPlayer.tsx` - 视频播放器
- `SubtitleTimeline.tsx` - 字幕时间轴
- `Sidebar.tsx` - 左侧素材库
- `PropertiesPanel.tsx` - 右侧属性面板

## 许可证

MIT License