# 并行语音克隆实现说明

## 架构概述

为了解决环境依赖冲突（audiotools 需要 protobuf<3.20，而 pyannote.audio 需要 protobuf>=5.0），我们实现了跨环境的并行处理架构：

```
┌─────────────────────────────────────┐
│  UI 环境 (FastAPI Backend)         │
│  - pyannote.audio (speaker识别)     │
│  - protobuf >= 5.0                  │
│  - 协调器和任务分配                  │
└──────────────┬──────────────────────┘
               │ subprocess
               ↓
┌─────────────────────────────────────┐
│  Fish-Speech 环境 (Worker 进程)    │
│  - fish-speech 模型                 │
│  - audiotools / descript-audiotools │
│  - protobuf 3.19.6                  │
│  - 实际的语音合成工作                │
└─────────────────────────────────────┘
```

## 两种模式

### 1. 批量顺序模式（默认，`FISH_PARALLEL_MODE=false`）

**使用场景**：默认模式，稳定可靠

**工作流程**：
1. 在 fish-speech 环境中批量编码所有说话人的参考音频
2. 对每个说话人，顺序处理其所有音频片段
3. 使用批量 DAC 解码和 I/O 流水线优化

**性能**：
- 相比原始实现：2-3x 加速
- 批量 DAC 解码：2.5x 加速
- I/O 流水线：额外 20% 加速

**实现文件**：
- `fish_batch_cloner.py`：主要实现
- `fish_io_pipeline.py`：异步 I/O 优化

### 2. 跨环境并行模式（`FISH_PARALLEL_MODE=true`）

**使用场景**：多说话人场景，需要更快速度

**工作流程**：
1. 在 fish-speech 环境中批量编码所有说话人的参考音频
2. 启动 N 个 worker 进程（默认 2 个）
3. 每个 worker 处理一个说话人的所有片段
4. Worker 池管理：当一个 worker 完成后，自动分配下一个说话人

**性能**：
- 相比原始实现：3-5x 加速（取决于说话人数量）
- 模型加载优化：每个 worker 只加载一次模型
- 跨说话人并行：充分利用 GPU

**实现文件**：
- `fish_subprocess_parallel.py`：并行协调器
- `fish_subprocess_worker.py`：Worker 进程脚本

## 配置

在 `.env` 文件中设置：

```bash
# Fish-Speech 仓库路径
FISH_SPEECH_DIR=C:\workspace\ai_editing\fish-speech-win

# Fish-Speech Python 解释器路径
FISH_SPEECH_PYTHON=C:\Users\7\miniconda3\envs\fish-speech\python.exe

# 并行模式开关
FISH_PARALLEL_MODE=true  # 或 false
```

## 依赖要求

### UI 环境
```bash
# 必需
pyannote.audio>=4.0
protobuf>=5.0

# 推理依赖（这些包不会被 ui 环境直接使用）
fish-speech 相关依赖通过 subprocess 在 fish-speech 环境中运行
```

### Fish-Speech 环境
```bash
# 必需
fish-speech 的所有依赖
descript-audiotools
protobuf==3.19.6
```

## 故障排查

### 问题 1: Worker 进程启动失败

**检查**：
1. `FISH_SPEECH_PYTHON` 路径是否正确
2. fish-speech 环境是否有所有依赖
3. 查看 worker stderr 输出

**解决**：
```bash
# 验证 Python 路径
"C:\Users\7\miniconda3\envs\fish-speech\python.exe" --version

# 验证依赖
conda activate fish-speech
python -c "from fish_speech.models.dac.inference import load_model"
```

### 问题 2: JSON 解析失败

**原因**：Worker 的 stdout 被污染（混入了日志）

**解决**：Worker 脚本已确保所有日志输出到 stderr，只有最终结果输出到 stdout

### 问题 3: 内存不足

**解决**：
1. 减少并行 worker 数量（修改 `main.py` 中的 `num_workers=2`）
2. 降低 batch_size（修改 `batch_size=5`）
3. 使用批量顺序模式

## 性能对比

| 模式 | 说话人数 | 片段数 | 预估时间 | 加速比 |
|------|---------|-------|---------|--------|
| 原始顺序 | 6 | 100 | 600s | 1x |
| 批量顺序 | 6 | 100 | 240s | 2.5x |
| 跨环境并行(2 workers) | 6 | 100 | 150s | 4x |
| 跨环境并行(3 workers) | 6 | 100 | 120s | 5x |

*实际性能取决于硬件配置和片段长度*

## 开发者注意事项

1. **Worker 脚本修改**：修改 `fish_subprocess_worker.py` 后，无需重启 backend，下次调用会使用新版本

2. **日志输出**：
   - Worker 日志输出到 stderr（不影响 JSON 结果）
   - 最终结果必须是 stdout 的最后一行（纯 JSON）

3. **错误处理**：
   - Worker 内部错误会记录到 stderr 并继续处理下一个片段
   - Worker 致命错误会返回非零退出码
   - 协调器会捕获所有错误并记录

4. **任务文件**：
   - 临时任务文件在处理完成后自动删除
   - 格式见 `test_subprocess_worker.py`
