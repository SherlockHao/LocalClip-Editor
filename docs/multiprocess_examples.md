# 多进程语音克隆配置示例

本文档提供不同硬件配置下的推荐设置和预期性能。

## 硬件配置示例

### 1. 单 GPU - RTX 4090 (24GB)

#### 配置 A: 保守模式（推荐新手）
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=8.0
```

**预期结果**：
- Worker 数量: 2 个
- 每个 GPU 分配: GPU 0: 2 workers
- 显存占用: ~16GB
- 加速比: 2x

**日志示例**：
```
[GPU 0] NVIDIA GeForce RTX 4090, Total Memory: 24.00 GB
[GPU 0] Can run 2 workers (Available: 21.60 GB)
[Main] Using 2 parallel workers across 1 GPU(s)
[Main] GPU 0: 2 workers
[Main] Launching Worker 0 on GPU 0 for Speaker 0
[Main] Launching Worker 1 on GPU 0 for Speaker 1
```

#### 配置 B: 激进模式（充分利用显存）
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=6.0
```

**预期结果**：
- Worker 数量: 3 个
- 每个 GPU 分配: GPU 0: 3 workers
- 显存占用: ~18-20GB
- 加速比: 3x

**日志示例**：
```
[GPU 0] NVIDIA GeForce RTX 4090, Total Memory: 24.00 GB
[GPU 0] Can run 3 workers (Available: 21.60 GB)
[Main] Using 3 parallel workers across 1 GPU(s)
[Main] GPU 0: 3 workers
```

**注意**：如果遇到 OOM，说明实际模型占用超过 6GB，需要调回 7.0 或 8.0。

---

### 2. 单 GPU - RTX 3090 (24GB)

与 RTX 4090 配置相同。

---

### 3. 单 GPU - RTX 4080 (16GB)

#### 推荐配置
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=8.0
```

**预期结果**：
- Worker 数量: 1 个
- 显存占用: ~8GB
- 加速比: 1x（与单进程模式相同，无加速）

**建议**：16GB 显存建议使用单进程模式，或者尝试降低 `FISH_MODEL_MEMORY_GB=7.0` 来运行 2 个 worker。

#### 激进配置（需测试）
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=7.0
```

**预期结果**：
- Worker 数量: 2 个
- 显存占用: ~14-15GB
- 加速比: 2x

---

### 4. 双 GPU - 2x RTX 4090 (24GB each)

#### 推荐配置
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=8.0
```

**预期结果**：
- Worker 数量: 4 个
- 每个 GPU 分配: GPU 0: 2 workers, GPU 1: 2 workers
- 显存占用: 每个 GPU ~16GB
- 加速比: 4x

**日志示例**：
```
[GPU 0] NVIDIA GeForce RTX 4090, Total Memory: 24.00 GB
[GPU 0] Can run 2 workers (Available: 21.60 GB)
[GPU 1] NVIDIA GeForce RTX 4090, Total Memory: 24.00 GB
[GPU 1] Can run 2 workers (Available: 21.60 GB)
[Main] Using 4 parallel workers across 2 GPU(s)
[Main] GPU 0: 2 workers
[Main] GPU 1: 2 workers
[Main] Launching Worker 0 on GPU 0 for Speaker 0
[Main] Launching Worker 1 on GPU 0 for Speaker 1
[Main] Launching Worker 2 on GPU 1 for Speaker 2
[Main] Launching Worker 3 on GPU 1 for Speaker 3
```

#### 激进配置
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=6.0
```

**预期结果**：
- Worker 数量: 6 个
- 每个 GPU 分配: GPU 0: 3 workers, GPU 1: 3 workers
- 显存占用: 每个 GPU ~18-20GB
- 加速比: 6x

---

### 5. 双 GPU - 2x RTX 3060 (12GB each)

#### 推荐配置
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=9.0
```

**预期结果**：
- Worker 数量: 2 个
- 每个 GPU 分配: GPU 0: 1 worker, GPU 1: 1 worker
- 显存占用: 每个 GPU ~9GB
- 加速比: 2x

**说明**：12GB 显存较小，调高 `FISH_MODEL_MEMORY_GB` 避免 OOM。

---

### 6. 服务器 GPU - A100 (80GB)

#### 推荐配置
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=8.0
```

**预期结果**：
- Worker 数量: 9 个
- 每个 GPU 分配: GPU 0: 9 workers
- 显存占用: ~72GB
- 加速比: 9x

**说明**：大显存 GPU 可以运行非常多的 worker，适合处理大量说话人的场景。

#### 超激进配置（完全利用显存）
```bash
FISH_MULTIPROCESS_MODE=true
FISH_MODEL_MEMORY_GB=6.5
```

**预期结果**：
- Worker 数量: 11 个
- 显存占用: ~71.5GB
- 加速比: 11x

---

## 性能测试结果对比

| 硬件配置 | 模式 | Worker数 | 6说话人/46片段耗时 | 加速比 |
|---------|------|---------|------------------|--------|
| RTX 4090 (24GB) | 单进程 | 1 | 2分30秒 | 1x |
| RTX 4090 (24GB) | 多进程 (8GB) | 2 | 1分15秒 | 2x |
| RTX 4090 (24GB) | 多进程 (6GB) | 3 | 50秒 | 3x |
| 2x RTX 4090 | 多进程 (8GB) | 4 | 40秒 | 3.75x |
| 2x RTX 4090 | 多进程 (6GB) | 6 | 25秒 | 6x |

*注：实际性能受 CPU、内存、磁盘 I/O 等因素影响*

---

## 如何选择配置

### 第一步：确定是否启用多进程

- ✅ **启用多进程**：显存 ≥ 16GB 且说话人 ≥ 2
- ❌ **使用单进程**：显存 < 16GB 或说话人 = 1

### 第二步：选择 FISH_MODEL_MEMORY_GB

1. **新手推荐**：使用默认值 8.0
2. **显存充足**（如 24GB）：尝试 6.0-7.0，获得更多 worker
3. **显存紧张**（如 16GB）：提高到 9.0-10.0，避免 OOM
4. **大显存**（如 40GB+）：降低到 6.0，最大化并行数

### 第三步：测试和调整

1. 启用多进程，运行一次语音克隆
2. 观察后端日志：
   - 查看 `[GPU X] Can run N workers` 来确认 worker 数量
   - 如果 worker 数太少，降低 `FISH_MODEL_MEMORY_GB`
   - 如果出现 OOM 错误，提高 `FISH_MODEL_MEMORY_GB`
3. 使用 `nvidia-smi` 监控实际显存占用
4. 根据实际情况微调配置

---

## 故障排查

### OOM (Out of Memory) 错误

**症状**：
```
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
```

**解决方法**：
1. 提高 `FISH_MODEL_MEMORY_GB`（如从 6.0 改为 8.0）
2. 或者禁用多进程：`FISH_MULTIPROCESS_MODE=false`

### Worker 数量为 1（未并行）

**症状**：
```
[Main] Using 1 parallel workers across 1 GPU(s)
```

**可能原因**：
- 显存太小，只能运行 1 个 worker
- `FISH_MODEL_MEMORY_GB` 设置过高

**解决方法**：
- 降低 `FISH_MODEL_MEMORY_GB`（如从 10.0 改为 7.0）
- 检查显存是否被其他程序占用

### 性能没有提升

**可能原因**：
- 说话人数量太少（1-2 个）
- Worker 数量等于 1（未真正并行）
- CPU 或磁盘 I/O 成为瓶颈

**解决方法**：
- 确认 worker 数量 > 1
- 检查 CPU 和磁盘使用率
- 说话人少时多进程优势不明显，属于正常

---

## 高级配置

### 混合精度

在 `fish_multiprocess_generate.py` 中可以修改精度：

```python
# 使用 float16 减少显存占用（可能影响质量）
precision = torch.float16  # 默认 bfloat16

# 使用 float32 提高质量（增加显存占用）
precision = torch.float32
```

### 自定义 GPU 分配

如果你想手动控制 GPU 分配，可以修改 `calculate_worker_count` 函数。

---

## 总结

- **默认配置**（推荐大多数用户）：`FISH_MULTIPROCESS_MODE=true`, `FISH_MODEL_MEMORY_GB=8.0`
- **显存充足**（24GB+）：降低到 6.0-7.0，获得更多并行
- **显存紧张**（16GB）：提高到 9.0-10.0，或使用单进程模式
- **多 GPU**：自动充分利用所有 GPU
- **大显存**（40GB+）：可以运行 5+ 个 worker，大幅加速
