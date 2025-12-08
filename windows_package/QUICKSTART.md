# 🚀 快速开始 - LocalClip Editor Windows 打包

> 5 分钟快速上手打包

## ⚡ 超快速打包（一键完成）

```bash
# 1. 进入打包目录
cd windows_package

# 2. 安装 PyInstaller
pip install pyinstaller

# 3. 一键打包（包含所有步骤）
python build_package.py
```

**等待 30-60 分钟**，完成后在 `windows_package/dist/` 目录找到：
- `LocalClip-Editor/` - 可分发的完整目录
- `LocalClip-Editor-Windows-v1.0.0.zip` - 压缩包

---

## 📦 打包步骤详解

### 步骤 1: 准备环境（5 分钟）

```bash
# 安装 Python 依赖
pip install -r backend/requirements.txt
pip install pyinstaller

# 安装 Node.js 依赖
cd frontend && npm install && cd ..
```

### 步骤 2: 下载模型（10-20 分钟）

```bash
cd windows_package
python download_models.py
```

### 步骤 3: 构建前端（3-5 分钟）

```bash
python build_frontend.py
```

### 步骤 4: 打包后端（10-30 分钟）

```bash
pyinstaller --clean localclip_editor.spec
```

### 步骤 5: 组装包（5-10 分钟）

```bash
python build_package.py --skip-models --skip-frontend
```

---

## 🎯 分步打包（可控制每一步）

如果想分步执行或跳过某些步骤：

```bash
# 只下载模型
python download_models.py

# 只构建前端
python build_frontend.py

# 只打包后端
pyinstaller --clean localclip_editor.spec

# 跳过已完成的步骤
python build_package.py --skip-models --skip-frontend
```

---

## 🎁 打包输出

打包完成后的目录结构：

```
windows_package/dist/
├── LocalClip-Editor/                    # ← 这是最终的可分发目录
│   ├── 启动 LocalClip Editor.bat        # 用户双击启动
│   ├── backend/                         # 后端服务
│   ├── frontend/                        # 前端界面
│   ├── models/                          # AI 模型 (5-8GB)
│   ├── ffmpeg/                          # FFmpeg
│   └── 使用说明.txt
│
└── LocalClip-Editor-Windows-v1.0.0.zip # ← 压缩包（便于分发）
```

---

## 🚚 分发给用户

### 方式 1: 分发目录

将整个 `LocalClip-Editor/` 目录复制给用户：

```bash
# 可以使用 USB 驱动器、网络共享等方式
cp -r windows_package/dist/LocalClip-Editor /path/to/usb/
```

### 方式 2: 分发压缩包（推荐）

发送 `.zip` 文件给用户：

```bash
# 上传到云盘、邮件发送等
# 用户解压后即可使用
```

**用户使用步骤**:
1. 解压 `LocalClip-Editor-Windows-v1.0.0.zip`
2. 双击 `启动 LocalClip Editor.bat`
3. 浏览器自动打开 http://localhost:8000

---

## ⚙️ 自定义配置

### 修改配置文件

编辑 `config.yaml` 自定义打包选项：

```yaml
package:
  name: "LocalClip-Editor"
  version: "1.0.0"
  icon: "assets/icon.ico"  # 自定义图标

pyinstaller:
  console: false  # 隐藏控制台窗口
```

### 自定义 Fish-Speech 路径

```bash
python build_package.py --fish-speech-path /path/to/fish-speech
```

---

## 🐛 常见问题速查

### 问题 1: PyInstaller 未安装

```bash
pip install pyinstaller
```

### 问题 2: 模型下载失败

```bash
# 使用镜像
export HF_ENDPOINT=https://hf-mirror.com
python download_models.py
```

### 问题 3: 前端构建失败

```bash
# 确保 Node.js 已安装
node --version

# 重新安装依赖
cd frontend
rm -rf node_modules
npm install
```

### 问题 4: 打包后体积过大

当前体积约 6-8GB，主要是 AI 模型。可以：
- 移除不需要的模型
- 使用模型量化
- 分离模型包

---

## 📋 打包检查清单

打包完成后，请确认：

- [ ] ✅ `LocalClipEditor.exe` 存在于 `backend/` 目录
- [ ] ✅ `frontend/dist/` 包含 `index.html` 等文件
- [ ] ✅ `models/` 目录包含所有模型（约 5-8GB）
- [ ] ✅ `ffmpeg/ffmpeg.exe` 存在
- [ ] ✅ `启动 LocalClip Editor.bat` 可以正常运行
- [ ] ✅ 在 Windows 上测试启动成功

---

## 📞 需要帮助？

- 📖 详细文档: [PACKAGE_README.md](PACKAGE_README.md)
- 🐛 问题反馈: GitHub Issues
- 💬 讨论: GitHub Discussions

---

**预计总时间**: 30-60 分钟
**预计体积**: 6-8 GB
**支持系统**: Windows 10/11 (64位)

开始打包吧！ 🎉
