# 多进程语音克隆架构说明

## 核心设计理念

**一次加载，批量处理**：每个 worker 加载模型一次，然后处理分配给它的所有说话人。

## 架构流程

### 1. 初始化阶段

```
[Main] 检测 GPU 信息
  ↓
[Main] 计算可用 worker 数量
  ↓
[Main] 均匀分配说话人给 workers
  ↓
[Main] 启动所有 worker 进程（并行）
```

### 2. Worker 执行阶段

每个 worker 独立执行：

```
[Worker N] 启动
  ↓
[Worker N] 加载 Text2Semantic 模型 (一次)
  ↓
[Worker N] 加载 DAC 模型 (一次)
  ↓
[Worker N] 开始处理分配的说话人
  ├─ Speaker A
  │   ├─ 加载 Speaker A 的 npy
  │   ├─ 生成 Speaker A 的所有文本
  │   └─ 清理 Speaker A 的 npy
  ├─ Speaker B
  │   ├─ 加载 Speaker B 的 npy
  │   ├─ 生成 Speaker B 的所有文本
  │   └─ 清理 Speaker B 的 npy
  └─ ...
  ↓
[Worker N] 清理模型
  ↓
[Worker N] 返回结果
```

### 3. 结果收集阶段

```
[Main] 等待所有 worker 完成
  ↓
[Main] 收集所有结果
  ↓
[Main] 输出 JSON 结果
```

## 分配策略

### 轮询分配（Round-robin）

说话人按顺序轮流分配给 workers：

**示例 1：6 个说话人，2 个 workers**
```
Worker 0: [Speaker 0, Speaker 2, Speaker 4]
Worker 1: [Speaker 1, Speaker 3, Speaker 5]
```

**示例 2：6 个说话人，3 个 workers**
```
Worker 0: [Speaker 0, Speaker 3]
Worker 1: [Speaker 1, Speaker 4]
Worker 2: [Speaker 2, Speaker 5]
```

**示例 3：6 个说话人，1 个 worker**
```
Worker 0: [Speaker 0, Speaker 1, Speaker 2, Speaker 3, Speaker 4, Speaker 5]
```

### 负载均衡

轮询分配确保：
- 每个 worker 处理的说话人数量基本相同
- 避免某些 worker 空闲而其他忙碌
- 即使说话人文本数量不同，整体仍然较均衡

## GPU 分配示例

### 单 GPU，24GB 显存，FISH_MODEL_MEMORY_GB=5.3

```
[GPU 0] Can run 4 workers (Available: 21.60 GB)
[Main] Using 4 parallel workers across 1 GPU(s)
[Main] GPU 0: 4 workers

说话人分配：
  Worker 0: [Speaker 0, Speaker 4] → GPU 0
  Worker 1: [Speaker 1, Speaker 5] → GPU 0
  Worker 2: [Speaker 2]           → GPU 0
  Worker 3: [Speaker 3]           → GPU 0
```

**执行流程**：
- 4 个 worker 同时启动
- 每个 worker 加载模型到 GPU 0 的不同内存区域
- 并行处理各自的说话人
- 预计加速：4x（理想情况）

### 双 GPU，2x 24GB，FISH_MODEL_MEMORY_GB=8.0

```
[GPU 0] Can run 2 workers (Available: 21.60 GB)
[GPU 1] Can run 2 workers (Available: 21.60 GB)
[Main] Using 4 parallel workers across 2 GPU(s)
[Main] GPU 0: 2 workers
[Main] GPU 1: 2 workers

说话人分配：
  Worker 0: [Speaker 0, Speaker 4] → GPU 0
  Worker 1: [Speaker 1, Speaker 5] → GPU 0
  Worker 2: [Speaker 2]           → GPU 1
  Worker 3: [Speaker 3]           → GPU 1
```

**执行流程**：
- Worker 0, 1 使用 GPU 0
- Worker 2, 3 使用 GPU 1
- 总共 4x 加速

## 与旧架构的对比

### 旧架构（分批处理）

```
批次 1: 启动 2 个 worker
  Worker 0 → 加载模型 → 处理 Speaker 0 → 卸载模型
  Worker 1 → 加载模型 → 处理 Speaker 1 → 卸载模型
批次 2: 启动 2 个 worker
  Worker 2 → 加载模型 → 处理 Speaker 2 → 卸载模型  ❌ 重复加载！
  Worker 3 → 加载模型 → 处理 Speaker 3 → 卸载模型  ❌ 重复加载！
批次 3: 启动 2 个 worker
  Worker 4 → 加载模型 → 处理 Speaker 4 → 卸载模型  ❌ 重复加载！
  Worker 5 → 加载模型 → 处理 Speaker 5 → 卸载模型  ❌ 重复加载！
```

**问题**：
- 模型被重复加载 6 次（浪费时间）
- 只有 2x 并行度（同时运行 2 个 worker）

### 新架构（一次加载）

```
同时启动 2 个 worker:
  Worker 0 → 加载模型 → 处理 [Speaker 0, 2, 4] → 卸载模型  ✅ 加载一次！
  Worker 1 → 加载模型 → 处理 [Speaker 1, 3, 5] → 卸载模型  ✅ 加载一次！
```

**优势**：
- 模型只加载 2 次（每个 worker 一次）
- 始终保持 2x 并行度
- 更快的总体速度

## 性能分析

### 时间构成

单个说话人的处理时间：
```
加载模型时间: ~30-60 秒（首次）
加载 npy:     ~1 秒
生成 N 个文本: ~N * 10 秒（14 tokens/sec）
```

### 场景：6 个说话人，每人 8 个文本

**单进程模式**：
```
加载模型: 45秒
处理 6 个说话人: 6 * (1秒 + 8*10秒) = 486秒
总计: 531秒 ≈ 9分钟
```

**旧的多进程（2 worker，分批）**：
```
批次1: 45秒加载 + 81秒处理 = 126秒
批次2: 45秒加载 + 81秒处理 = 126秒  ❌ 重复加载
批次3: 45秒加载 + 81秒处理 = 126秒  ❌ 重复加载
总计: 378秒 ≈ 6.3分钟
加速比: 1.4x（效率差）
```

**新的多进程（2 worker，一次加载）**：
```
Worker 0: 45秒加载 + 243秒处理(3个说话人) = 288秒
Worker 1: 45秒加载 + 243秒处理(3个说话人) = 288秒
总计: 288秒 ≈ 4.8分钟（并行执行）
加速比: 1.84x
```

**新的多进程（4 worker，充分利用显存）**：
```
Worker 0-3: 45秒加载 + 121.5秒处理(1.5个说话人) ≈ 166.5秒
总计: 166.5秒 ≈ 2.8分钟（并行执行）
加速比: 3.2x
```

## 日志示例

### 启动阶段

```
[Main] Total tasks: 46
[GPU 0] NVIDIA GeForce RTX 4090, Total Memory: 24.00 GB
[GPU 0] Can run 4 workers (Available: 21.60 GB)
[Main] Using 4 parallel workers across 1 GPU(s)
[Main] GPU 0: 4 workers
[Main] Speakers: 6

[Main] Speaker assignment:
  Worker 0: 2 speakers (IDs: [0, 4]), 16 texts
  Worker 1: 2 speakers (IDs: [1, 5]), 15 texts
  Worker 2: 1 speakers (IDs: [2]), 8 texts
  Worker 3: 1 speakers (IDs: [3]), 7 texts

[Main] Launching 4 workers...
[Main] Launching Worker 0 on GPU 0
[Main] Launching Worker 1 on GPU 0
[Main] Launching Worker 2 on GPU 0
[Main] Launching Worker 3 on GPU 0
```

### Worker 执行阶段

```
[Worker 0] Starting on cuda:0
[Worker 0] Assigned 2 speakers, 16 texts total
[Worker 0] Loading Text2Semantic model...
[Worker 0] Loading DAC model...
[Worker 0] Models loaded! Starting generation...

[Worker 0] Processing Speaker 0 (1/2)
[Worker 0] This speaker has 8 texts
[Worker 0] Speaker 0 progress: 1/8
[Worker 0] Speaker 0 progress: 5/8
[Worker 0] ✅ Completed Speaker 0: 8 segments

[Worker 0] Processing Speaker 4 (2/2)
[Worker 0] This speaker has 8 texts
[Worker 0] Speaker 4 progress: 1/8
[Worker 0] Speaker 4 progress: 5/8
[Worker 0] ✅ Completed Speaker 4: 8 segments

[Worker 0] ✅ All done! Processed 16/16 segments
```

### 完成阶段

```
[Main] Waiting for all workers to complete...
[Main] Collecting results...
[Main] All done! Generated 46/46 segments
```

## 总结

新架构的核心优势：

1. **消除重复加载**：模型只加载一次（每个 worker）
2. **最大化并行**：所有 worker 同时运行
3. **负载均衡**：轮询分配确保均衡
4. **显存高效**：根据显存大小动态决定 worker 数量
5. **简单可靠**：逻辑清晰，易于调试

这种设计在 worker 数量 = 1 时也能高效工作，不会有任何重复加载或无效操作。
