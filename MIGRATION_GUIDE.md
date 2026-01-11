# LocalClip Editor 系统迁移指南

> **Migration Guide for LocalClip Editor**
>
> 本指南详细说明如何将 LocalClip Editor 系统迁移到新的 Windows 开发机器

---

## 📋 迁移清单概览

| 序号 | 步骤 | 验证脚本 | 优先级 | 预计时间 |
|------|------|----------|--------|----------|
| 1 | 代码文件迁移 | `1_verify_code_structure.py` | ⭐⭐⭐ | 10分钟 |
| 2 | AI模型迁移 | `2_verify_models.py` | ⭐⭐⭐ | 30分钟-2小时 |
| 3 | Conda环境安装 | `3_setup_environments.py` | ⭐⭐⭐ | 30分钟-1小时 |
| 4 | 环境验证 | `4_verify_environments.py` | ⭐⭐ | 10分钟 |
| 5 | 前端依赖安装 | 手动 | ⭐⭐ | 5-10分钟 |
| 6 | 环境变量配置 | 手动 | ⭐⭐ | 5分钟 |
| 7 | 外部服务安装 | 手动 | ⭐ | 15分钟 |

---

## 🚀 快速开始

### 前置要求

在开始迁移前，确保新机器上已安装：

1. ✅ **Miniconda 或 Anaconda**
   - 下载: https://docs.conda.io/en/latest/miniconda.html
   - 验证: `conda --version`

2. ✅ **Node.js (v18+) 和 npm**
   - 下载: https://nodejs.org/
   - 验证: `node --version` 和 `npm --version`

3. ✅ **Git**
   - 下载: https://git-scm.com/
   - 验证: `git --version`

4. ✅ **CUDA Toolkit** (如果有 NVIDIA GPU)
   - 下载: https://developer.nvidia.com/cuda-downloads
   - 建议版本: CUDA 11.8 或 12.1

### 迁移步骤时序图

```
旧机器                                新机器
  │                                     │
  ├─ 1. 打包代码和模型                 │
  │   (tar/zip 压缩)                   │
  │                                     │
  ├────────── 传输文件 ──────────────>│
  │         (网络/U盘/硬盘)             │
  │                                     ├─ 2. 解压文件
  │                                     │
  │                                     ├─ 3. 运行验证脚本
  │                                     │   ├─ verify_code_structure
  │                                     │   └─ verify_models
  │                                     │
  │                                     ├─ 4. 安装 conda 环境
  │                                     │   └─ setup_environments
  │                                     │
  │                                     ├─ 5. 验证环境
  │                                     │   └─ verify_environments
  │                                     │
  │                                     ├─ 6. 安装前端依赖
  │                                     │   └─ npm install
  │                                     │
  │                                     ├─ 7. 配置环境变量
  │                                     │
  │                                     └─ 8. 启动应用
  │                                         └─ start.bat
```

---

## 📂 第1步：代码文件迁移

### 需要迁移的目录结构

```
LocalClip-Editor/
├── backend/                    # 后端代码（必需）
│   ├── main.py                # FastAPI 主应用
│   ├── fish_simple_cloner.py  # Fish-Speech 克隆器
│   ├── indonesian_tts_cloner.py # 印尼语 TTS
│   ├── audio_optimizer.py     # 音频优化
│   ├── requirements.txt       # Python 依赖
│   └── ...
├── frontend/                   # 前端代码（必需）
│   ├── src/
│   ├── package.json
│   └── ...
├── start.bat                   # Windows 启动脚本
├── start.vbs                   # 静默启动脚本
└── migration/                  # 迁移脚本（新增）
    ├── 1_verify_code_structure.py
    ├── 2_verify_models.py
    ├── 3_setup_environments.py
    └── 4_verify_environments.py
```

### 外部依赖仓库

**必须单独迁移的仓库：**

1. **Fish-Speech 仓库**
   ```
   C:\workspace\ai_editing\fish-speech-win\
   ├── fish_speech/           # Python 包
   ├── checkpoints/
   │   └── openaudio-s1-mini/ # 模型文件（约1GB）
   └── ...
   ```

2. **VITS-TTS-ID 模型**（仅印尼语需要）
   ```
   C:\workspace\ai_editing\models\vits-tts-id\
   ├── config.json
   └── G_100000.pth          # 模型权重（约155MB）
   ```

3. **Silero VAD**（可选）
   ```
   C:\workspace\ai_editing\silero-vad\
   ```

### 验证代码结构

在新机器上运行：

```bash
cd C:\path\to\LocalClip-Editor
python migration/1_verify_code_structure.py
```

**预期输出：**
```
✓ 所有文件检查通过
✓ 外部依赖找到: 2/3
  ⚠ Silero VAD 未找到（可选）
```

---

## 🤖 第2步：AI模型迁移

### 模型清单和大小

| 模型 | 大小 | 必需性 | 存放位置 |
|------|------|--------|----------|
| Fish-Speech TTS | ~1.0 GB | ✅ 必需 | `fish-speech-win/checkpoints/openaudio-s1-mini/` |
| PyAnnote Diarization | ~750 MB | ✅ 必需 | 自动下载到 `~/.cache/torch/pyannote/` |
| VITS-TTS-ID | ~155 MB | ⭕ 可选 | `models/vits-tts-id/` |
| Silero VAD | ~5 MB | ⭕ 可选 | `silero-vad/` |
| **总计** | **~2 GB** | - | - |

### 迁移方法

#### 方法1：直接复制（推荐，如果有快速存储）

```bash
# 旧机器
robocopy C:\workspace\ai_editing\fish-speech-win Z:\backup\fish-speech-win /MIR
robocopy C:\workspace\ai_editing\models Z:\backup\models /MIR

# 新机器
robocopy Z:\backup\fish-speech-win C:\workspace\ai_editing\fish-speech-win /MIR
robocopy Z:\backup\models C:\workspace\ai_editing\models /MIR
```

#### 方法2：从 HuggingFace 重新下载

```bash
# Fish-Speech 模型
cd C:\workspace\ai_editing
git clone https://huggingface.co/fishaudio/fish-speech-1.5 fish-speech-win

# VITS-TTS-ID 模型
git lfs clone https://huggingface.co/bookbot/vits-tts-id models/vits-tts-id
```

### PyAnnote 模型配置

**重要：PyAnnote 需要 HuggingFace Token**

1. 访问 https://huggingface.co/settings/tokens
2. 创建新 Token（Read 权限）
3. 接受模型许可：
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
4. 设置环境变量：
   ```bash
   set HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxx
   ```

### 验证模型

```bash
python migration/2_verify_models.py
```

**预期输出：**
```
[Fish-Speech TTS 模型]
  ✓ 模型目录存在
  ✓ firefly-gan-vq-fsq-8x1024-21hz-generator.pth - 大小正常 (166.xx MB)
  ✓ model.pth - 大小正常 (875.xx MB)

[PyAnnote Speaker Diarization]
  ⚠ 缓存目录不存在（首次运行时会创建）

总体评估: 优秀！
```

---

## 🐍 第3步：Conda 环境安装

### 环境列表

| 环境名 | Python | 用途 | 必需性 | 安装时间 |
|--------|--------|------|--------|----------|
| `ui` | 3.11 | 主UI后端 | ✅ 必需 | 15-20分钟 |
| `fish-speech` | 3.10 | Fish-Speech TTS | ✅ 必需 | 10-15分钟 |
| `tts-id-py311` | 3.11 | 印尼语 TTS | ⭕ 可选 | 5-10分钟 |

### 自动安装

```bash
cd C:\path\to\LocalClip-Editor
python migration/3_setup_environments.py
```

该脚本会：
1. ✅ 检查 conda 是否已安装
2. ✅ 创建所有必需的环境
3. ✅ 安装所有 Python 包
4. ✅ 配置 Fish-Speech 包
5. ✅ 生成激活脚本 `activate_env.bat`

### 手动安装（备选）

如果自动安装失败，可以手动执行：

#### 环境1：ui（主后端）

```bash
# 创建环境
conda create -n ui python=3.11 -y
conda activate ui

# 安装依赖
cd backend
pip install -r requirements.txt

# 验证安装
python -c "import fastapi; import torch; import pyannote.audio; print('OK')"
```

#### 环境2：fish-speech

```bash
# 创建环境
conda create -n fish-speech python=3.10 -y
conda activate fish-speech

# 安装 PyTorch
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# 安装 Fish-Speech
cd C:\workspace\ai_editing\fish-speech-win
pip install -e .

# 验证安装
python -c "import fish_speech; print('OK')"
```

#### 环境3：tts-id-py311（可选）

```bash
# 创建环境
conda create -n tts-id-py311 python=3.11 -y
conda activate tts-id-py311

# 安装依赖
conda install ffmpeg -y
pip install torch librosa soundfile phonemizer
```

### 验证环境

```bash
python migration/4_verify_environments.py
```

**预期输出：**
```
[ui]
  ✓ 环境存在
  ✓ Python 版本: 3.11.x
  ✓ fastapi: 0.115.0
  ✓ torch: 2.1.0
  ...

[fish-speech]
  ✓ 环境存在
  ✓ Python 版本: 3.10.x
  ...

CUDA 可用性检查:
  CUDA Available: True
  CUDA Version: 11.8
  Device Count: 1

所有环境验证通过！
```

---

## 🎨 第4步：前端依赖安装

### 安装 Node.js 依赖

```bash
cd frontend
npm install
```

**预期时间：** 5-10分钟（取决于网络速度）

### 验证前端

```bash
# 开发模式测试
npm run dev

# 应该看到
# VITE v5.4.8  ready in xxx ms
# ➜  Local:   http://localhost:5173/
```

按 `Ctrl+C` 停止测试。

---

## ⚙️ 第5步：环境变量配置

### Windows 环境变量设置

打开 **系统属性 > 环境变量**，或在 PowerShell 中设置：

```powershell
# 必需环境变量
[System.Environment]::SetEnvironmentVariable("FISH_SPEECH_DIR", "C:\workspace\ai_editing\fish-speech-win", "User")
[System.Environment]::SetEnvironmentVariable("FISH_SPEECH_PYTHON", "C:\Users\YourUsername\miniconda3\envs\fish-speech\python.exe", "User")
[System.Environment]::SetEnvironmentVariable("HUGGINGFACE_TOKEN", "hf_your_token_here", "User")

# 可选环境变量（印尼语）
[System.Environment]::SetEnvironmentVariable("TTS_ID_PYTHON", "C:\Users\YourUsername\miniconda3\envs\tts-id-py311\python.exe", "User")
[System.Environment]::SetEnvironmentVariable("VITS_TTS_ID_MODEL_DIR", "C:\workspace\ai_editing\models\vits-tts-id", "User")

# 可选：启用多进程模式（>=16GB GPU）
[System.Environment]::SetEnvironmentVariable("FISH_MULTIPROCESS_MODE", "true", "User")
```

### 或创建 `.env` 文件

在 `backend/` 目录下创建 `.env` 文件：

```ini
# Fish-Speech 配置
FISH_SPEECH_DIR=C:\workspace\ai_editing\fish-speech-win
FISH_SPEECH_PYTHON=C:\Users\YourUsername\miniconda3\envs\fish-speech\python.exe

# HuggingFace Token
HUGGINGFACE_TOKEN=hf_your_token_here

# 印尼语 TTS（可选）
TTS_ID_PYTHON=C:\Users\YourUsername\miniconda3\envs\tts-id-py311\python.exe
VITS_TTS_ID_MODEL_DIR=C:\workspace\ai_editing\models\vits-tts-id

# 多进程模式（可选）
FISH_MULTIPROCESS_MODE=true
```

### 验证环境变量

```bash
# PowerShell
$env:FISH_SPEECH_DIR
$env:HUGGINGFACE_TOKEN

# CMD
echo %FISH_SPEECH_DIR%
echo %HUGGINGFACE_TOKEN%
```

---

## 🔧 第6步：外部服务安装（可选）

### Ollama（用于翻译）

LocalClip Editor 使用 Ollama 进行 AI 翻译。

#### 安装 Ollama

1. 下载：https://ollama.com/download
2. 安装后运行：`ollama serve`
3. 下载模型：
   ```bash
   ollama pull qwen2.5:7b
   ```

#### 验证 Ollama

```bash
curl http://localhost:11434/api/tags
```

应该返回已安装的模型列表。

### FFmpeg（已包含在 conda 环境中）

如果需要单独安装：
1. 下载：https://ffmpeg.org/download.html
2. 添加到 PATH
3. 验证：`ffmpeg -version`

---

## 🎯 第7步：启动应用

### 首次启动

```bash
cd C:\path\to\LocalClip-Editor
start.bat
```

或双击 `start.vbs`（静默启动，无控制台窗口）

### 启动流程

```
[1/6] 检查并清理占用的端口...
[2/6] 启动后端服务 (FastAPI)...
[3/6] 等待后端服务启动...
      Backend service is ready!
[4/6] 检查前端依赖...
      Frontend dependencies already installed
[5/6] 启动前端服务 (React + Vite)...
[6/7] 等待前端服务就绪...
      Frontend service is ready!
[7/7] 打开浏览器...

✅ LocalClip Editor Started!
   Frontend URL: http://localhost:5173
   Backend API:  http://localhost:8000/docs
```

### 验证应用运行

1. 浏览器自动打开 http://localhost:5173
2. 应该看到 LocalClip Editor 界面
3. 测试功能：
   - 上传视频
   - 字幕识别
   - 说话人分离
   - 语音克隆

---

## 🐛 故障排除

### 问题1：端口被占用

**错误：** `Address already in use: 8000` 或 `5173`

**解决：**
```bash
# 查找占用进程
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# 终止进程
taskkill /F /PID <进程ID>

# 或重启 start.bat
```

### 问题2：CUDA 不可用

**错误：** `CUDA not available`

**解决：**
1. 检查 NVIDIA 驱动：`nvidia-smi`
2. 重新安装 PyTorch with CUDA：
   ```bash
   conda activate ui
   pip uninstall torch torchaudio
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

### 问题3：PyAnnote 模型下载失败

**错误：** `401 Unauthorized` 或 `403 Forbidden`

**解决：**
1. 确认已设置 `HUGGINGFACE_TOKEN`
2. 确认已接受模型许可
3. 测试 Token：
   ```bash
   curl -H "Authorization: Bearer hf_xxx" https://huggingface.co/api/whoami
   ```

### 问题4：Ollama 连接失败

**错误：** `Connection refused: localhost:11434`

**解决：**
1. 启动 Ollama：`ollama serve`
2. 或系统会自动启动（如果配置了自动启动）
3. 验证：`curl http://localhost:11434/api/tags`

### 问题5：前端 npm 安装失败

**错误：** `ERR! network` 或超时

**解决：**
```bash
# 使用国内镜像
npm config set registry https://registry.npmmirror.com

# 清理缓存重试
npm cache clean --force
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📊 迁移验证清单

使用以下清单确认迁移完成：

- [ ] ✅ 代码结构验证通过 (`1_verify_code_structure.py`)
- [ ] ✅ AI 模型全部就位 (`2_verify_models.py`)
- [ ] ✅ Conda 环境安装成功 (`3_setup_environments.py`)
- [ ] ✅ 环境验证通过 (`4_verify_environments.py`)
- [ ] ✅ 前端依赖安装完成 (`npm install`)
- [ ] ✅ 环境变量已配置
- [ ] ✅ Ollama 已安装并运行
- [ ] ✅ 应用成功启动 (`start.bat`)
- [ ] ✅ 能够上传视频并识别字幕
- [ ] ✅ 说话人分离功能正常
- [ ] ✅ 语音克隆功能正常
- [ ] ✅ 翻译功能正常（如需要）

---

## 📝 系统要求总结

### 最低配置

- **操作系统：** Windows 10/11 (64-bit)
- **CPU：** 4核心
- **内存：** 16 GB RAM
- **存储：** 20 GB 可用空间
- **GPU：** 可选（NVIDIA GTX 1060+ 推荐）

### 推荐配置

- **操作系统：** Windows 11 (64-bit)
- **CPU：** 8核心+
- **内存：** 32 GB RAM
- **存储：** 50 GB SSD
- **GPU：** NVIDIA RTX 3060+ (12GB+ VRAM)

### 软件依赖

- Miniconda/Anaconda
- Node.js 18+
- Git
- CUDA Toolkit 11.8+ (如有 NVIDIA GPU)
- Ollama (可选，用于翻译)

---

## 🎓 使用 Claude Code 检查

在新机器上，使用 Claude Code 验证迁移：

```
> 请帮我验证 LocalClip Editor 迁移是否完整

然后依次运行：
1. python migration/1_verify_code_structure.py
2. python migration/2_verify_models.py
3. python migration/3_setup_environments.py
4. python migration/4_verify_environments.py

如有问题，询问：
> 为什么 XXX 验证失败？应该如何修复？
```

---

## 📞 获取帮助

如遇到问题，请检查：

1. **日志文件**
   - 后端日志：控制台输出或 `backend/logs/`
   - 前端日志：浏览器开发者工具控制台

2. **系统信息**
   ```bash
   python migration/platform_utils.py
   ```

3. **验证脚本输出**
   - 详细的错误信息和修复建议

---

## 🔄 更新和维护

### 更新代码

```bash
cd LocalClip-Editor
git pull origin main
```

### 更新依赖

```bash
# 后端
conda activate ui
cd backend
pip install -r requirements.txt --upgrade

# 前端
cd frontend
npm update
```

### 更新模型

```bash
# Fish-Speech
cd C:\workspace\ai_editing\fish-speech-win
git pull

# PyAnnote（自动更新）
# 删除缓存强制重新下载
rm -rf ~/.cache/torch/pyannote
```

---

**迁移完成后，您的新机器已经准备就绪！**

🎉 **祝使用愉快！**
