# LocalClip Editor 迁移工具包

> Migration Toolkit for LocalClip Editor

这个目录包含了将 LocalClip Editor 迁移到新机器所需的所有验证和安装脚本。

---

## 📦 脚本清单

### 1️⃣ `1_verify_code_structure.py` - 代码结构验证

**用途：** 验证所有必需的代码文件和目录是否已正确迁移

**运行：**
```bash
python 1_verify_code_structure.py
```

**检查内容：**
- ✅ 启动脚本（`start.bat`, `start.vbs`）
- ✅ 后端核心文件（`main.py`, `fish_simple_cloner.py` 等）
- ✅ 前端核心文件（`package.json`, `src/` 等）
- ✅ 必需目录结构
- ✅ 数据文件（`digits_mapping.json`）
- ✅ 外部依赖仓库（Fish-Speech, VITS-TTS-ID）

**输出示例：**
```
========== 验证代码结构 ==========

[启动脚本]
✓ start.bat (2.5 KB)
✓ start.vbs (1.2 KB)

[后端核心]
✓ backend/main.py (156.3 KB)
✓ backend/fish_simple_cloner.py (12.5 KB)
...

总体评估: 优秀！完整度 95.0% - 可以开始使用
```

---

### 2️⃣ `2_verify_models.py` - AI 模型验证

**用途：** 验证所有 AI 模型是否已正确下载和配置

**运行：**
```bash
python 2_verify_models.py
```

**检查内容：**
- ✅ Fish-Speech TTS 模型（~1 GB）
- ✅ VITS-TTS-ID 印尼语模型（~155 MB）
- ✅ PyAnnote 说话人分离模型（自动下载）
- ✅ Silero VAD 模型（可选）

**输出示例：**
```
========== 模型大小估算 ==========
必需模型:
  - Fish-Speech TTS: ~1.0 GB
自动下载模型 (PyAnnote):
  - speaker-diarization-3.1: ~500 MB
  ...

[Fish-Speech TTS 模型]
  ✓ 模型目录存在
  ✓ firefly-gan-vq-fsq-8x1024-21hz-generator.pth - 大小正常 (166.24 MB)
  ✓ model.pth - 大小正常 (875.51 MB)

所有模型检查通过！
```

**包含下载指引：** 如果模型缺失，脚本会输出详细的下载链接和放置位置

---

### 3️⃣ `3_setup_environments.py` - Conda 环境安装

**用途：** 自动创建和配置所有必需的 conda 环境

**运行：**
```bash
python 3_setup_environments.py
```

**会创建的环境：**

1. **ui** (Python 3.11)
   - FastAPI 后端
   - PyAnnote 说话人分离
   - 音频处理库

2. **fish-speech** (Python 3.10)
   - Fish-Speech 语音克隆
   - PyTorch + CUDA

3. **tts-id-py311** (Python 3.11) *可选*
   - 印尼语 TTS

**输出示例：**
```
========== 环境规划 ==========

1. ui
   主UI后端环境（FastAPI + PyAnnote + 音频处理）
   必需性: 必需

2. fish-speech
   Fish-Speech TTS 环境（语音克隆）
   必需性: 必需

是否继续? (Y/n): Y

========== 创建环境: ui ==========
[✓] 环境创建成功
[✓] 安装 pip 包...
[✓] 环境配置完成

所有环境安装成功！
```

**特性：**
- 🔄 自动检测已存在的环境
- 📦 从 `requirements.txt` 安装依赖
- 🎯 优先级排序安装
- 💾 生成激活脚本 `activate_env.bat`

---

### 4️⃣ `4_verify_environments.py` - 环境验证

**用途：** 验证所有 conda 环境是否正确安装且可用

**运行：**
```bash
python 4_verify_environments.py
```

**检查内容：**
- ✅ 环境是否存在
- ✅ Python 版本是否正确
- ✅ 关键包是否已安装
- ✅ 包版本是否满足要求
- ✅ 模块能否正常导入
- ✅ CUDA 是否可用（GPU）

**输出示例：**
```
========== 环境验证 ==========

[ui]
  主UI后端环境 (必需)
  ✓ 环境存在
  ✓ Python 版本: 3.11.5

  检查关键包:
  ✓ fastapi: 0.115.0
  ✓ torch: 2.1.0+cu118
  ✓ pyannote.audio: 3.1.1

  测试模块导入:
  ✓ fastapi
  ✓ torch
  ✓ pyannote.audio
  ...

CUDA 可用性检查:
PyTorch CUDA:
  CUDA Available: True
  CUDA Version: 11.8
  Device Count: 1

所有环境验证通过！
```

**修复指引：** 如果验证失败，脚本会输出详细的修复命令

---

## 🚀 快速开始指南

### 完整迁移流程

在新机器上按顺序执行：

```bash
# 1. 进入项目目录
cd C:\path\to\LocalClip-Editor

# 2. 验证代码结构
python migration/1_verify_code_structure.py

# 3. 验证AI模型
python migration/2_verify_models.py

# 4. 安装conda环境
python migration/3_setup_environments.py

# 5. 验证环境
python migration/4_verify_environments.py

# 6. 安装前端依赖
cd frontend
npm install

# 7. 启动应用
cd ..
start.bat
```

### 只验证不安装

如果只想检查迁移状态而不进行安装：

```bash
# 快速检查所有内容
python migration/1_verify_code_structure.py
python migration/2_verify_models.py
python migration/4_verify_environments.py
```

---

## 📋 脚本参数和选项

### 所有脚本通用参数

```bash
# 显示帮助
python <script>.py --help

# 详细输出模式
python <script>.py --verbose

# 静默模式（只显示错误）
python <script>.py --quiet
```

### 特定脚本选项

#### `3_setup_environments.py`

```bash
# 只创建必需环境
python 3_setup_environments.py --required-only

# 跳过某个环境
python 3_setup_environments.py --skip tts-id-py311

# 强制重新创建所有环境
python 3_setup_environments.py --force
```

---

## 🎨 输出颜色说明

脚本使用颜色编码来表示不同的状态：

- 🟢 **绿色 ✓** - 成功/通过
- 🔴 **红色 ✗** - 失败/错误
- 🟡 **黄色 ⚠** - 警告/可选
- 🔵 **蓝色 ℹ** - 信息/提示

---

## 🐛 常见问题

### Q1: 脚本报错 "conda 命令未找到"

**A:** 确保 Conda 已安装并添加到 PATH。在 Anaconda Prompt 中运行脚本。

### Q2: 某个环境安装失败怎么办？

**A:** 查看详细错误信息，通常是网络问题或依赖冲突。可以：
1. 手动创建环境并安装包
2. 使用国内镜像源
3. 跳过该环境（如果是可选的）

### Q3: 模型验证失败但我确定已下载？

**A:** 检查路径配置：
1. 查看脚本输出的预期路径
2. 设置对应的环境变量
3. 或将模型移动到默认路径

### Q4: 环境验证通过但应用无法启动？

**A:** 可能的原因：
1. 环境变量未配置
2. 端口被占用（8000, 5173）
3. Ollama 未启动（翻译功能需要）

---

## 📚 相关文档

- **[../MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md)** - 完整迁移指南
- **[../README.md](../README.md)** - 项目说明
- **[../backend/requirements.txt](../backend/requirements.txt)** - Python 依赖列表
- **[../frontend/package.json](../frontend/package.json)** - Node.js 依赖列表

---

## 🔧 自定义和扩展

### 添加新的验证项

编辑对应的脚本，在 `REQUIRED_STRUCTURE` 或类似字典中添加新项：

```python
# 1_verify_code_structure.py
REQUIRED_STRUCTURE = {
    "自定义分类": [
        "path/to/your/file.py",
        "path/to/your/directory/",
    ],
}
```

### 添加新的 Conda 环境

编辑 `3_setup_environments.py`，在 `CONDA_ENVIRONMENTS` 中添加：

```python
CONDA_ENVIRONMENTS = {
    "your-env-name": {
        "描述": "环境描述",
        "python_version": "3.11",
        "必需性": "可选",
        "优先级": 4,
        "pip_packages": [
            "package1",
            "package2",
        ],
    },
}
```

---

## 📞 获取帮助

如果遇到问题：

1. **查看详细日志**
   - 脚本会输出详细的错误信息和修复建议

2. **使用 Claude Code 询问**
   ```
   > 我运行 1_verify_code_structure.py 遇到错误：[粘贴错误信息]
   > 应该如何解决？
   ```

3. **检查迁移指南**
   - [MIGRATION_GUIDE.md](../MIGRATION_GUIDE.md) 包含故障排除章节

---

**Happy Migrating! 🚀**

*这些脚本让系统迁移变得简单且可靠*
