# LocalClip Editor 迁移检查清单

> **Migration Checklist - 用于 Claude Code 检查**
>
> 在新机器上依次执行以下步骤，并使用 Claude Code 验证每个步骤的结果

---

## 📋 迁移前准备

### ✅ 检查项 0：前置软件安装

在新机器上确认以下软件已安装：

```bash
# 检查 Conda
conda --version
# 预期输出: conda 23.x.x 或更高

# 检查 Node.js
node --version
# 预期输出: v18.x.x 或更高

npm --version
# 预期输出: 9.x.x 或更高

# 检查 Git
git --version
# 预期输出: git version 2.x.x

# 检查 CUDA（如有 NVIDIA GPU）
nvidia-smi
# 应显示 GPU 信息和 CUDA 版本
```

**Claude Code 提示：**
```
请帮我检查这台机器是否已安装所有前置软件？
[粘贴上述命令的输出]
```

---

## 📂 步骤 1：代码文件迁移验证

### 执行验证

```bash
cd C:\path\to\LocalClip-Editor
python migration/1_verify_code_structure.py
```

### 预期结果

```
✓ 代码结构验证通过
  通过: 35/35 (100%)
✓ 外部依赖找到 2/3 (Fish-Speech, VITS-TTS-ID)
  ⚠ Silero VAD 未找到（可选）
```

### Claude Code 检查点

```
我运行了代码结构验证脚本，输出如下：
[粘贴脚本输出]

请帮我分析：
1. 是否所有必需文件都已迁移？
2. 缺失的文件是否重要？
3. 外部依赖路径是否正确？
```

### ✅ 通过标准

- [ ] 代码结构完整度 >= 90%
- [ ] 所有必需目录存在
- [ ] Fish-Speech 仓库路径正确
- [ ] 后端核心文件完整
- [ ] 前端核心文件完整

### ❌ 如果失败

**Claude Code 询问：**
```
验证脚本显示缺少以下文件：
[列出缺失文件]

这些文件应该从哪里获取？如何修复？
```

---

## 🤖 步骤 2：AI 模型验证

### 执行验证

```bash
python migration/2_verify_models.py
```

### 预期结果

```
[Fish-Speech TTS 模型]
  ✓ 模型目录存在
  ✓ model.pth - 大小正常 (875.51 MB)
  ✓ firefly-gan-vq-fsq-8x1024-21hz-generator.pth - 大小正常 (166.24 MB)

[VITS-TTS-ID 印尼语模型]
  ✓ 模型目录存在
  ✓ G_100000.pth - 大小正常 (155.32 MB)

[PyAnnote Speaker Diarization]
  ⚠ 缓存目录不存在（首次运行时会创建）

总体评估: 优秀！
```

### Claude Code 检查点

```
模型验证结果：
[粘贴脚本输出]

请确认：
1. Fish-Speech 模型是否完整？
2. 印尼语模型是否需要（如果不需要可跳过）？
3. PyAnnote 警告是否正常？
4. 是否需要下载任何模型？
```

### ✅ 通过标准

- [ ] Fish-Speech 模型文件完整且大小正确
- [ ] 模型文件路径可访问
- [ ] 印尼语模型（如需要）已就位

### ❌ 如果失败

**Claude Code 询问：**
```
模型验证失败，缺少：
[列出缺失模型]

请告诉我：
1. 如何下载这些模型？
2. 应该放在哪个目录？
3. 是否可以跳过某些模型？
```

---

## 🐍 步骤 3：Conda 环境安装

### 执行安装

```bash
python migration/3_setup_environments.py
```

### 预期过程

```
========== 环境规划 ==========

1. ui - 主UI后端环境
2. fish-speech - Fish-Speech TTS 环境
3. tts-id-py311 - 印尼语 TTS 环境（可选）

是否继续? (Y/n): Y

[创建 ui 环境...]
  ✓ 环境创建成功
  ✓ 安装 pip 包...
  ✓ 环境配置完成

[创建 fish-speech 环境...]
  ✓ 环境创建成功
  ✓ 安装 Fish-Speech 包...
  ✓ 环境配置完成

所有环境安装成功！
```

### Claude Code 检查点

```
Conda 环境安装完成，输出：
[粘贴脚本输出]

请确认：
1. 所有环境是否创建成功？
2. 包安装是否有错误或警告？
3. 是否需要手动修复任何问题？
```

### ✅ 通过标准

- [ ] `ui` 环境创建成功
- [ ] `fish-speech` 环境创建成功
- [ ] 所有关键包安装无错误
- [ ] 生成了 `activate_env.bat`

### ❌ 如果失败

**Claude Code 询问：**
```
环境安装失败，错误信息：
[粘贴错误]

应该如何修复？是否需要手动创建环境？
```

---

## ✅ 步骤 4：环境验证

### 执行验证

```bash
python migration/4_verify_environments.py
```

### 预期结果

```
[ui]
  ✓ 环境存在
  ✓ Python 版本: 3.11.5
  ✓ fastapi: 0.115.0
  ✓ torch: 2.1.0+cu118
  ✓ pyannote.audio: 3.1.1

  测试模块导入:
  ✓ fastapi
  ✓ torch
  ✓ pyannote.audio
  ...

[fish-speech]
  ✓ 环境存在
  ✓ Python 版本: 3.10.13
  ✓ torch: 2.1.0+cu118
  ...

CUDA 可用性检查:
  CUDA Available: True
  CUDA Version: 11.8
  Device Count: 1

所有环境验证通过！
```

### Claude Code 检查点

```
环境验证结果：
[粘贴完整输出]

请分析：
1. 所有环境是否正常？
2. CUDA 是否可用？（如有 GPU）
3. 包版本是否兼容？
4. 导入测试是否都通过？
```

### ✅ 通过标准

- [ ] 所有必需环境验证通过
- [ ] Python 版本正确
- [ ] 关键包全部安装且可导入
- [ ] CUDA 可用（如有 GPU）

### ❌ 如果失败

**Claude Code 询问：**
```
环境验证失败：
[粘贴失败详情]

问题：
1. 哪些包需要重新安装？
2. 版本冲突如何解决？
3. 导入失败的原因是什么？
```

---

## 🎨 步骤 5：前端依赖安装

### 执行安装

```bash
cd frontend
npm install
```

### 预期输出

```
npm WARN deprecated ...

added 1234 packages, and audited 1235 packages in 2m

123 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
```

### Claude Code 检查点

```
npm install 完成：
[粘贴输出]

请确认：
1. 是否有严重的警告或错误？
2. 依赖包数量是否合理（~1200个）？
3. 是否有安全漏洞需要修复？
```

### ✅ 通过标准

- [ ] npm install 成功完成
- [ ] 无严重错误（WARN 可忽略）
- [ ] `node_modules/` 目录已创建

### 测试前端

```bash
npm run dev
```

应该看到：
```
VITE v5.4.8  ready in 1234 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

按 `Ctrl+C` 停止。

---

## ⚙️ 步骤 6：环境变量配置

### 必需的环境变量

在 PowerShell 中设置：

```powershell
# Fish-Speech
[System.Environment]::SetEnvironmentVariable("FISH_SPEECH_DIR", "d:/ai_editing\fish-speech-win", "User")
[System.Environment]::SetEnvironmentVariable("FISH_SPEECH_PYTHON", "C:\Users\YOUR_USERNAME\miniconda3\envs\fish-speech\python.exe", "User")

# HuggingFace Token（从 https://huggingface.co/settings/tokens 获取）
[System.Environment]::SetEnvironmentVariable("HUGGINGFACE_TOKEN", "hf_YOUR_TOKEN", "User")
```

### 验证环境变量

```powershell
$env:FISH_SPEECH_DIR
$env:FISH_SPEECH_PYTHON
$env:HUGGINGFACE_TOKEN
```

### Claude Code 检查点

```
我设置了以下环境变量：
FISH_SPEECH_DIR=d:/ai_editing\fish-speech-win
FISH_SPEECH_PYTHON=C:\Users\xxx\miniconda3\envs\fish-speech\python.exe
HUGGINGFACE_TOKEN=hf_xxxxx

请确认：
1. 路径是否正确？
2. Python 路径格式是否正确？
3. 是否需要重启终端使环境变量生效？
```

### ✅ 通过标准

- [ ] 所有必需环境变量已设置
- [ ] 路径指向正确位置
- [ ] Python.exe 文件存在

---

## 🎯 步骤 7：启动应用测试

### 首次启动

```bash
cd C:\path\to\LocalClip-Editor
start.bat
```

### 预期流程

```
[1/6] 检查并清理占用的端口...
[2/6] 启动后端服务 (FastAPI)...
[3/6] 等待后端服务启动...
      Backend service is ready!
[4/6] 检查前端依赖...
[5/6] 启动前端服务 (React + Vite)...
[6/7] 等待前端服务就绪...
      Frontend service is ready!
[7/7] 打开浏览器...

✅ LocalClip Editor Started!
```

浏览器应自动打开 http://localhost:5173

### Claude Code 检查点

```
应用启动日志：
[粘贴启动输出]

浏览器显示：
[描述看到的界面或错误]

问题：
1. 应用是否成功启动？
2. 前后端服务是否都在运行？
3. 界面是否正常显示？
```

### ✅ 通过标准

- [ ] 后端启动无错误（端口 8000）
- [ ] 前端启动无错误（端口 5173）
- [ ] 浏览器自动打开
- [ ] 界面正常显示

---

## 🧪 步骤 8：功能测试

### 测试 1：视频上传

1. 准备一个测试视频（MP4格式）
2. 在界面上传视频
3. 观察是否成功识别

**Claude Code 检查：**
```
上传视频后的响应：
[粘贴日志或错误]

是否正常？如有错误应如何修复？
```

### 测试 2：字幕识别

1. 点击"识别字幕"
2. 等待处理完成

**预期：** 显示识别的字幕文本

### 测试 3：说话人分离

1. 点击"说话人分离"
2. 观察识别的说话人数量

**预期：** 显示不同说话人的音色

### 测试 4：语音克隆

1. 选择目标语言
2. 点击"开始语音克隆"
3. 等待生成完成

**Claude Code 检查：**
```
语音克隆日志：
[粘贴后端日志]

问题：
1. 是否检测到GPU并启用多进程？
2. 生成速度是否正常？
3. 音频质量如何？
```

### ✅ 功能测试通过标准

- [ ] 视频上传成功
- [ ] 字幕识别成功
- [ ] 说话人分离成功
- [ ] 语音克隆成功
- [ ] 音频播放正常

---

## 📊 最终验证清单

### 系统状态确认

```bash
# 检查服务状态
netstat -ano | findstr :8000  # 后端
netstat -ano | findstr :5173  # 前端

# 检查环境
conda env list  # 应显示 ui, fish-speech, tts-id-py311

# 检查GPU
nvidia-smi  # 如有GPU
```

### 完整性检查清单

- [ ] ✅ 代码结构完整
- [ ] ✅ AI 模型就位
- [ ] ✅ Conda 环境正确
- [ ] ✅ 前端依赖安装
- [ ] ✅ 环境变量配置
- [ ] ✅ 应用成功启动
- [ ] ✅ 基本功能测试通过
- [ ] ✅ GPU 正常工作（如有）

### Claude Code 最终确认

```
迁移完成！请帮我确认系统状态：

1. 代码验证结果：[通过/失败]
2. 模型验证结果：[通过/失败]
3. 环境验证结果：[通过/失败]
4. 功能测试结果：[列出测试项]

是否有任何遗漏或需要优化的地方？
```

---

## 🚨 常见问题快速参考

### 问题：端口被占用

```bash
netstat -ano | findstr :8000
taskkill /F /PID <进程ID>
```

### 问题：CUDA 不可用

```bash
conda activate ui
pip uninstall torch torchaudio
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 问题：PyAnnote 401 错误

```bash
# 检查 Token
curl -H "Authorization: Bearer $env:HUGGINGFACE_TOKEN" https://huggingface.co/api/whoami

# 重新设置 Token
[System.Environment]::SetEnvironmentVariable("HUGGINGFACE_TOKEN", "hf_NEW_TOKEN", "User")
```

### 问题：Ollama 连接失败

```bash
# 启动 Ollama
ollama serve

# 验证
curl http://localhost:11434/api/tags
```

---

## 📈 性能优化建议

迁移完成后，可以进行以下优化：

1. **多进程模式**（>=16GB GPU）
   ```bash
   [System.Environment]::SetEnvironmentVariable("FISH_MULTIPROCESS_MODE", "true", "User")
   ```

2. **PyTorch 优化**
   ```python
   # 在 backend/main.py 添加
   torch.backends.cudnn.benchmark = True
   ```

3. **Node.js 生产构建**
   ```bash
   cd frontend
   npm run build
   ```

---

## 🎉 迁移成功！

**如果所有检查项都通过，恭喜！您已成功完成 LocalClip Editor 的迁移！**

### 下一步

1. 📚 阅读 [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) 了解更多细节
2. 🔧 根据需要调整配置
3. 📝 记录任何特殊配置或遇到的问题
4. 🚀 开始使用 LocalClip Editor！

---

**使用 Claude Code 随时获取帮助：**

```
我在迁移过程中遇到了 XXX 问题：
[描述问题和相关日志]

请帮我分析原因并提供解决方案。
```
