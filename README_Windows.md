# LocalClip Editor - Windows 使用指南

## 📋 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.10+
- **Node.js**: 18+
- **Conda**: Miniconda3 或 Anaconda
- **GPU**: NVIDIA GPU (可选，推荐用于加速)

## 🚀 快速开始

### 1. 环境准备

#### 1.1 安装 Conda 环境

确保已安装以下 conda 环境：

```bash
# 查看已有环境
conda env list

# 应该看到以下环境：
# - ui (主环境，用于 LocalClip Editor)
# - fish-speech (Fish-Speech 专用环境)
```

如果没有 `ui` 环境，创建它：

```bash
conda create -n ui python=3.10 -y
conda activate ui
```

#### 1.2 安装依赖

```bash
# 激活 ui 环境
conda activate ui

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install
```

### 2. 模型配置

#### 2.1 确认模型位置

模型应该位于项目根目录的上两级 `models` 文件夹中：

```
C:\workspace\ai_editing\
├── models\
│   ├── models--prithivMLmods--Common-Voice-Geneder-Detection\
│   ├── models--pyannote--segmentation\
│   ├── models--pyannote--speaker-diarization-3.1\
│   └── models--pyannote--wespeaker-voxceleb-resnet34-LM\
└── workspace\
    └── LocalClip-Editor\
```

#### 2.2 环境变量配置（可选）

复制 `.env.example` 为 `.env` 并根据需要修改：

```bash
copy .env.example .env
```

### 3. Fish-Speech 配置

#### 3.1 确认 Fish-Speech 路径

Fish-Speech 应该位于：

```
C:\workspace\ai_editing\fish-speech-win\
```

#### 3.2 确认 Fish-Speech Checkpoint

确保存在：

```
C:\workspace\ai_editing\fish-speech-win\checkpoints\openaudio-s1-mini\
├── codec.pth
├── model.ckpt
└── ...
```

### 4. 启动服务

#### 方法 1: 使用启动脚本（推荐）

双击运行 `start.bat` 文件，或在命令行中执行：

```bash
start.bat
```

这将：
1. 自动检查并停止占用端口的进程
2. 启动后端服务 (FastAPI)
3. 启动前端服务 (React + Vite)

#### 方法 2: 手动启动

**启动后端：**

```bash
cd backend
conda activate ui
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**启动前端（新窗口）：**

```bash
cd frontend
npm run dev
```

### 5. 访问服务

- **前端界面**: http://localhost:5173
- **后端 API 文档**: http://localhost:8000/docs
- **后端 Swagger UI**: http://localhost:8000/redoc

## 🔧 常见问题

### Q1: 端口被占用

**错误**: `Address already in use: 8000` 或 `5173`

**解决方案**:

```bash
# 查找占用端口的进程
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# 终止进程 (PID 从上一步获取)
taskkill /F /PID <PID>
```

### Q2: Fish-Speech 找不到

**错误**: `FileNotFoundError: 找不到 fish-speech 目录`

**解决方案**:

1. 在 `.env` 文件中设置 `FISH_SPEECH_DIR`:

   ```bash
   FISH_SPEECH_DIR=C:\workspace\ai_editing\fish-speech-win
   ```

2. 或设置环境变量:

   ```bash
   set FISH_SPEECH_DIR=C:\workspace\ai_editing\fish-speech-win
   ```

### Q3: GPU 不可用

**错误**: 系统使用 CPU 而非 GPU

**解决方案**:

1. 确认 CUDA 安装:

   ```bash
   nvidia-smi
   ```

2. 确认 PyTorch 支持 CUDA:

   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

3. 如果返回 `False`，重新安装 PyTorch:

   ```bash
   conda activate ui
   pip uninstall torch torchaudio -y
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```

### Q4: 模型找不到

**错误**: `FileNotFoundError: 未找到本地模型文件`

**解决方案**:

确保模型在正确的位置，或在 `.env` 中设置 `MODELS_DIR`:

```bash
MODELS_DIR=C:\workspace\ai_editing\models
```

### Q5: 性别识别模型加载失败

**错误**: `Error loading gender classifier model`

**解决方案**:

1. 确认模型路径:

   ```
   C:\workspace\ai_editing\models\models--prithivMLmods--Common-Voice-Geneder-Detection\
   ```

2. 如果模型不存在，会自动从 HuggingFace 下载（需要网络连接）

### Q6: torchcodec 警告

**警告**: `torchcodec is not installed correctly`

**解决方案**:

这是正常的，系统会自动使用 `torchaudio` 作为替代音频后端，不影响功能。

## 📊 性能优化建议

### 1. GPU 加速

- **NVIDIA GPU**: 自动使用 CUDA
- **确保 CUDA 驱动最新**: https://www.nvidia.com/Download/index.aspx

### 2. Fish-Speech 并行模式

在 `.env` 中启用并行模式以提升语音克隆速度：

```bash
FISH_PARALLEL_MODE=true
```

### 3. 内存优化

如果遇到内存不足：

```bash
# 在 .env 中添加
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
CUDA_MODULE_LOADING=LAZY
```

## 🆘 获取帮助

如果遇到其他问题：

1. 查看后端日志（在后端窗口）
2. 查看前端日志（在前端窗口或浏览器控制台）
3. 检查 `.env` 配置是否正确

## 📝 注意事项

1. **首次运行较慢**: 模型加载需要时间，请耐心等待
2. **GPU 内存**: 建议至少 6GB 显存
3. **磁盘空间**: 模型文件较大，确保有足够空间
4. **网络**: 首次运行需要下载依赖，确保网络畅通
