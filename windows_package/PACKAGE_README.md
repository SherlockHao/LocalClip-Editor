# LocalClip Editor - Windows 打包指南

> 完整的 Windows 独立可执行程序打包方案

## 📋 目录

- [概述](#概述)
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细步骤](#详细步骤)
- [目录结构](#目录结构)
- [常见问题](#常见问题)
- [高级配置](#高级配置)

---

## 概述

本打包方案将 LocalClip Editor 打包成完全独立的 Windows 可执行程序，包含：

- ✅ **完整的 Python 运行环境** - 无需安装 Python
- ✅ **所有 AI 模型** - 完全离线运行（约 5-8GB）
- ✅ **FFmpeg 视频处理工具** - 内置 Windows 版本
- ✅ **React 前端界面** - 构建为静态文件
- ✅ **一键启动** - 双击即可运行

**预计打包体积**: 6-8 GB
**预计打包时间**: 30-60 分钟

---

## 系统要求

### 打包环境要求（开发机）

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11, macOS, 或 Linux |
| Python | 3.10+ |
| Node.js | 16.0+ |
| npm | 8.0+ |
| 磁盘空间 | 至少 20GB 可用空间 |
| 内存 | 建议 16GB+ |
| 网络 | 首次需要联网下载模型 |

### 运行环境要求（最终用户）

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10/11 (64位) |
| 内存 | 建议 8GB+ |
| 显卡 | 可选：NVIDIA GPU（CUDA 支持） |
| 磁盘空间 | 至少 10GB 可用空间 |
| 网络 | 无需联网，完全离线运行 |

---

## 快速开始

### 一键打包

```bash
# 1. 进入打包目录
cd windows_package

# 2. 安装 PyInstaller（如果未安装）
pip install pyinstaller

# 3. 执行完整打包
python build_package.py
```

### 打包完成后

打包完成后，你会得到：

```
windows_package/dist/
├── LocalClip-Editor/                      # 可分发的目录
│   ├── 启动 LocalClip Editor.bat          # 启动程序
│   ├── backend/                           # 后端可执行文件
│   ├── frontend/                          # 前端静态文件
│   ├── models/                            # AI 模型（5-8GB）
│   ├── ffmpeg/                            # FFmpeg 工具
│   └── 使用说明.txt                       # 用户文档
│
└── LocalClip-Editor-Windows-v1.0.0.zip   # 压缩包（便于分发）
```

**分发方式**:
- 直接分发整个 `LocalClip-Editor` 目录
- 或分发 `.zip` 压缩包（用户解压后使用）

---

## 详细步骤

### 步骤 1: 环境准备

#### 1.1 安装 Python 依赖

```bash
# 进入项目根目录
cd /path/to/LocalClip-Editor

# 安装后端依赖
pip install -r backend/requirements.txt

# 安装打包工具
pip install pyinstaller
```

#### 1.2 安装 Node.js 依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
```

#### 1.3 验证环境

```bash
# 检查 Python
python --version  # 应显示 3.10+

# 检查 Node.js
node --version    # 应显示 16.0+

# 检查 npm
npm --version     # 应显示 8.0+

# 检查 PyInstaller
pyinstaller --version
```

---

### 步骤 2: 下载 AI 模型

#### 2.1 自动下载（推荐）

```bash
cd windows_package
python download_models.py
```

这会下载：
- ✅ pyannote.audio 说话人识别模型（~500MB）
- ✅ Wav2Vec2 性别识别模型（~400MB）
- ✅ Fish-Speech 语音克隆模型（~3.4GB）
- ✅ FFmpeg Windows 版本（~100MB）

#### 2.2 手动下载

如果自动下载失败，可以手动下载：

**HuggingFace 模型**:
```bash
# 使用 huggingface-cli
huggingface-cli download pyannote/wespeaker-voxceleb-resnet34-LM
huggingface-cli download prithivMLmods/Common-Voice-Geneder-Detection
```

**Fish-Speech 模型**:
- 确保 Fish-Speech 项目已正确安装
- 模型位于: `fish-speech/checkpoints/openaudio-s1-mini`

**FFmpeg**:
- 下载地址: https://github.com/BtbN/FFmpeg-Builds/releases
- 解压到 `windows_package/ffmpeg/` 目录

#### 2.3 验证模型

```bash
cd windows_package
python download_models.py --verify-only
```

---

### 步骤 3: 构建前端

```bash
cd windows_package
python build_frontend.py
```

这会：
1. 安装前端依赖（`npm install`）
2. 构建前端（`npm run build`）
3. 修改后端以支持静态文件服务
4. 输出构建结果到 `frontend/dist`

---

### 步骤 4: 打包后端

```bash
cd windows_package
pyinstaller --clean localclip_editor.spec
```

**预计时间**: 10-30 分钟

**输出位置**: `windows_package/dist/LocalClipEditor/`

**包含内容**:
- `LocalClipEditor.exe` - 主程序
- `_internal/` - 所有依赖库

---

### 步骤 5: 组装完整包

打包脚本会自动组装，或手动执行：

```bash
cd windows_package
python build_package.py --skip-models --skip-frontend
```

这会：
1. 复制后端可执行文件
2. 复制前端静态文件
3. 复制 AI 模型
4. 复制 FFmpeg
5. 创建数据目录
6. 生成启动脚本
7. 创建用户文档

---

### 步骤 6: 创建压缩包

```bash
# 自动创建 ZIP 压缩包
cd windows_package/dist
python -m zipfile -c LocalClip-Editor-Windows.zip LocalClip-Editor/
```

---

## 目录结构

### 打包工具目录

```
windows_package/
├── config.yaml                    # 打包配置
├── build_package.py               # 主打包脚本
├── download_models.py             # 模型下载脚本
├── build_frontend.py              # 前端构建脚本
├── localclip_editor.spec          # PyInstaller 配置
├── templates/
│   └── start_windows.bat          # Windows 启动脚本模板
├── dist/                          # 打包输出目录
│   ├── models/                    # 下载的模型
│   ├── LocalClip-Editor/          # 最终包
│   └── *.zip                      # 压缩包
└── build/                         # 临时构建文件
```

### 最终包目录结构

```
LocalClip-Editor/
├── 启动 LocalClip Editor.bat      # 🚀 启动程序（用户双击此文件）
├── 使用说明.txt                    # 📖 用户文档
│
├── backend/                        # 后端服务
│   ├── LocalClipEditor.exe         # 主程序
│   └── _internal/                  # 依赖库
│       ├── torch/
│       ├── transformers/
│       ├── pyannote/
│       └── ...
│
├── frontend/                       # 前端界面
│   └── dist/
│       ├── index.html
│       ├── assets/
│       └── ...
│
├── models/                         # AI 模型（5-8GB）
│   ├── fish_speech/
│   │   ├── checkpoints/
│   │   │   └── openaudio-s1-mini/  # 3.4GB
│   │   ├── fish_speech/
│   │   └── tools/
│   ├── pyannote/                   # 说话人识别模型
│   ├── wav2vec2/                   # 性别识别模型
│   └── dnsmos/                     # 音频质量评分
│
├── ffmpeg/                         # 视频处理工具
│   ├── ffmpeg.exe
│   ├── ffprobe.exe
│   └── ffplay.exe
│
├── uploads/                        # 用户上传文件目录
├── exports/                        # 导出文件目录
├── audio_segments/                 # 音频片段缓存
└── logs/                           # 日志文件
```

---

## 常见问题

### Q1: 打包时出现 "Module not found" 错误

**解决方案**:

1. 检查是否安装了所有依赖:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. 在 `localclip_editor.spec` 中添加缺失的模块到 `hiddenimports`:
   ```python
   hiddenimports = [
       # ... 其他导入
       "missing_module_name",
   ]
   ```

3. 重新打包:
   ```bash
   pyinstaller --clean localclip_editor.spec
   ```

---

### Q2: PyInstaller 打包很慢

**原因**: PyInstaller 需要分析和收集所有依赖，PyTorch 等大型库会很慢。

**优化方案**:

1. 使用 `--exclude-module` 排除不需要的模块:
   ```bash
   pyinstaller --exclude-module matplotlib --exclude-module pandas ...
   ```

2. 禁用 UPX 压缩（已在 spec 中禁用）

3. 使用更快的磁盘（SSD）

**预计时间**:
- 首次打包: 20-40 分钟
- 增量打包: 5-10 分钟

---

### Q3: 打包后的 exe 被杀毒软件拦截

**原因**: PyInstaller 打包的程序可能被误报为病毒。

**解决方案**:

1. 禁用 UPX 压缩（已在 spec 中设置 `upx=False`）

2. 代码签名:
   ```bash
   signtool sign /f certificate.pfx /p password LocalClipEditor.exe
   ```

3. 提交到杀毒软件厂商进行白名单申请

---

### Q4: 模型下载失败

**解决方案**:

1. 检查网络连接

2. 使用代理或镜像:
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   python download_models.py
   ```

3. 手动下载并放置到对应目录

---

### Q5: 打包后体积过大

**当前体积**: 6-8 GB

**优化方案**:

1. **分离模型包** (推荐):
   - 主程序包: ~2GB
   - 模型扩展包: ~5GB
   - 用户可选择性下载模型

2. **移除不需要的模型**:
   - 只保留核心功能所需模型
   - 可减少到 3-4GB

3. **使用模型量化**:
   - 使用量化后的模型（精度略降）
   - 可减少 30-50% 体积

---

### Q6: Windows 上启动失败

**可能原因**:

1. 端口被占用
   - 解决: 关闭占用 8000 端口的程序

2. FFmpeg 缺失
   - 解决: 确保 `ffmpeg/` 目录完整

3. 模型文件损坏
   - 解决: 重新下载模型

**调试步骤**:

1. 在命令行中手动运行:
   ```cmd
   cd backend
   LocalClipEditor.exe --host 0.0.0.0 --port 8000
   ```

2. 查看错误信息

3. 检查 `logs/` 目录中的日志文件

---

## 高级配置

### 自定义打包配置

编辑 `config.yaml`:

```yaml
package:
  name: "LocalClip-Editor"
  version: "1.0.0"
  icon: "path/to/icon.ico"  # 自定义图标

pyinstaller:
  console: false  # 不显示控制台窗口
  onedir: true    # 单目录模式

models:
  huggingface_models:
    - model_id: "your-custom-model"
      cache_dir: "models/custom"
```

---

### 只打包特定组件

```bash
# 只下载模型
python download_models.py

# 只构建前端
python build_frontend.py

# 只打包后端
pyinstaller localclip_editor.spec

# 跳过已完成的步骤
python build_package.py --skip-models --skip-frontend
```

---

### 创建安装程序

使用 Inno Setup 创建 Windows 安装程序:

1. 安装 Inno Setup: https://jrsoftware.org/isinfo.php

2. 创建 `installer.iss` 脚本:
   ```iss
   [Setup]
   AppName=LocalClip Editor
   AppVersion=1.0.0
   DefaultDirName={pf}\LocalClip-Editor
   DefaultGroupName=LocalClip Editor
   OutputDir=.
   OutputBaseFilename=LocalClip-Editor-Setup

   [Files]
   Source: "dist\LocalClip-Editor\*"; DestDir: "{app}"; Flags: recursesubdirs

   [Icons]
   Name: "{group}\LocalClip Editor"; Filename: "{app}\启动 LocalClip Editor.bat"
   Name: "{commondesktop}\LocalClip Editor"; Filename: "{app}\启动 LocalClip Editor.bat"
   ```

3. 编译:
   ```bash
   iscc installer.iss
   ```

---

## 打包检查清单

在分发前，请确保：

- [ ] 所有模型文件已下载并完整
- [ ] FFmpeg 可执行文件存在
- [ ] 前端已成功构建
- [ ] 后端已成功打包
- [ ] 启动脚本可以正常运行
- [ ] 在 Windows 上测试启动和基本功能
- [ ] 用户文档已创建
- [ ] 文件大小合理（6-8GB）
- [ ] 压缩包已创建

---

## 支持与反馈

如有问题，请：

1. 查看本文档的常见问题部分
2. 查看项目的 GitHub Issues
3. 提交新的 Issue 并附上详细的错误信息

---

## 许可证

本项目遵循 Apache 2.0 许可证。

---

**最后更新**: 2024-12-09
