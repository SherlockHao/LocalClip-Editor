# 更新日志 - 译文长度验证与批量重新翻译

## 日期：2025-12-13

## 概述

为了解决语音克隆中因译文过长导致生成语音过长的问题，新增了自动验证译文长度并批量重新翻译的功能。

## 新增功能

### ✨ 核心功能

1. **译文长度自动验证**
   - 在语音克隆前自动检查每句译文长度
   - 规范化处理中英文文本（去除标点、空格）
   - 比较译文与原文的长度比例
   - 超过 1.2 倍阈值的译文标记为"超长"

2. **批量重新翻译**
   - 收集所有超长译文
   - 使用 LLM（Qwen3-1.7B）批量重新翻译
   - 模型只加载一次，提高效率
   - 使用简洁的 prompt："将中文翻译成{目标语言}，语言简洁且口语化"
   - 自动更新字幕文件中的译文

3. **容错处理**
   - 重新翻译失败时使用原译文继续
   - 超时保护（10分钟）
   - 详细的日志输出

## 新增文件

### 1. backend/text_utils.py ✨

文本处理工具模块，提供：

- `normalize_chinese(text)` - 规范化中文文本
- `normalize_english(text)` - 规范化英文文本
- `count_chinese_length(text)` - 计算中文字数
- `count_english_length(text)` - 计算英文词数
- `count_text_length(text, language)` - 根据语言计算长度
- `check_translation_length(...)` - 检查单条译文长度
- `validate_translations(...)` - 批量验证译文长度

**关键算法**：

```python
# 中文：只保留汉字
def normalize_chinese(text):
    return re.sub(r'[^\u4e00-\u9fff]', '', text)

# 英文：保护缩写，移除标点，统计单词
def normalize_english(text):
    text = re.sub(r"(\w)'(\w)", r"\1APOSTROPHE\2", text)  # 保护 I'm, don't
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)  # 移除标点
    text = text.replace('APOSTROPHE', '')  # 恢复缩写
    return ' '.join(text.split())
```

### 2. backend/batch_retranslate.py ✨

批量重新翻译脚本，基于 `LLM/LLM_batch_inference.py` 的架构：

**特点**：
- 多进程支持（默认单进程，避免显存冲突）
- 模型只加载一次
- 实时输出翻译结果
- 支持配置文件输入

**使用方式**：

```bash
# 通过配置文件调用
python batch_retranslate.py config.json

# 配置文件格式
{
    "tasks": [
        {
            "task_id": "retrans-0",
            "source": "原文",
            "target_language": "英文"
        }
    ],
    "model_path": "path/to/Qwen3-1.7B",
    "num_processes": 1
}
```

### 3. backend/test_text_utils.py ✨

文本工具模块的测试脚本：

**测试内容**：
- 中文规范化测试
- 英文规范化测试
- 长度计算测试
- 译文长度检查测试
- 批量验证测试

**运行方式**：

```bash
cd backend
conda activate ui
python test_text_utils.py
```

### 4. docs/translation_length_validation.md ✨

详细的功能文档，包含：
- 工作流程图
- 长度验证规则详解
- 批量重新翻译架构
- 配置说明
- 性能优化建议
- 故障排查指南
- 使用示例

## 修改文件

### 1. backend/main.py

**位置**：[main.py:723-860](../backend/main.py#L723-L860)

**修改内容**：在 `run_voice_cloning_process` 函数中，读取目标字幕后新增验证和重新翻译逻辑：

```python
# 1. 读取源字幕和目标字幕
target_subtitles = srt_parser.parse_srt(target_subtitle_path)
source_subtitles = srt_parser.parse_srt(source_subtitle_path)

# 2. 验证译文长度
too_long_items = []
for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
    is_too_long, source_len, target_len, ratio = check_translation_length(
        source_sub["text"], target_sub["text"], target_language, max_ratio=1.2
    )
    if is_too_long:
        too_long_items.append({...})

# 3. 批量重新翻译
if too_long_items:
    # 生成配置文件
    # 调用 batch_retranslate.py
    # 解析结果
    # 更新 target_subtitles
```

**进度更新**：
- 验证长度：76%
- 批量重新翻译：77%
- 批量生成语音：80%

### 2. .env

**位置**：[.env:44-50](../.env#L44-L50)

**新增配置**：

```bash
# ========================================
# LLM 翻译配置
# ========================================

# Qwen Inference Python 解释器路径（用于批量重新翻译）
QWEN_INFERENCE_PYTHON=C:\Users\7\miniconda3\envs\qwen_inference\python.exe
```

## 工作流程

### 集成到语音克隆流程

```
用户点击"开始语音克隆"
    ↓
[现有流程] 音频提取、说话人识别、MOS评分
    ↓
[现有流程] 批量编码参考音频
    ↓
[现有流程] 读取目标字幕
    ↓
[新增] 读取源字幕
    ↓
[新增] 逐句验证译文长度
    ↓
[新增] 如果有超长译文：
    ├─ 生成重新翻译配置
    ├─ 调用 batch_retranslate.py
    ├─ 解析翻译结果
    └─ 更新目标字幕
    ↓
[现有流程] 批量生成克隆语音
    ↓
[现有流程] 合成最终视频
```

## 使用示例

### 场景 1：所有译文合格

```
[Voice Clone] 正在验证译文长度...
✅ 所有译文长度合格，共 50 条
[Voice Clone] 正在批量生成克隆语音...
```

### 场景 2：发现超长译文

```
[Voice Clone] 正在验证译文长度...
⚠️  发现 3 条超长译文，准备批量重新翻译...

超长译文详情:
  [12] "早上好" (3字) -> "Good morning everyone, have a nice day" (7词) = 2.33x
  [34] "谢谢" (2字) -> "Thank you very much for your help" (7词) = 3.5x
  [56] "欢迎" (2字) -> "Welcome to use our amazing platform" (6词) = 3.0x

[Retranslate] 使用 Python: C:\...\qwen_inference\python.exe
[Retranslate] 配置: retranslate_config.json

[Process 1] Processing task retrans-12...
[retrans-12] 原文: 早上好
[retrans-12] 译文: Good morning

[Process 1] Processing task retrans-34...
[retrans-34] 原文: 谢谢
[retrans-34] 译文: Thanks

[Process 1] Processing task retrans-56...
[retrans-56] 原文: 欢迎
[retrans-56] 译文: Welcome

✅ 成功重新翻译 3 条文本

新译文验证:
  [12] "Good morning" (2词) = 0.67x ✅
  [34] "Thanks" (1词) = 0.5x ✅
  [56] "Welcome" (1词) = 0.5x ✅

[Voice Clone] 正在批量生成克隆语音...
```

## 性能影响

### 验证阶段

- **时间消耗**：约 0.5-1 秒（50条字幕）
- **CPU 消耗**：低
- **内存消耗**：极低

### 重新翻译阶段（如果触发）

假设 50 条字幕中有 5 条超长：

- **模型加载**：约 5-10 秒
- **单条翻译**：约 1-2 秒
- **总耗时**：约 15-20 秒
- **显存消耗**：约 4-6 GB（Qwen3-1.7B）

### 整体影响

- **无超长译文**：几乎无影响（+1秒）
- **有超长译文**：增加 15-30 秒（取决于数量）
- **优势**：避免后续重新生成语音，总体节省时间

## 技术亮点

### 1. 智能文本规范化

- **中文**：精确识别汉字（Unicode 0x4E00-0x9FFF）
- **英文**：正确处理缩写（I'm, don't, can't 等）
- **兼容性**：支持混合文本（数字、符号自动过滤）

### 2. 基于 LLM_batch_inference 架构

- **复用成熟方案**：基于已验证的批量推理架构
- **模型共享**：一次加载，批量处理
- **多进程支持**：可扩展到多进程（如果显存充足）

### 3. 无缝集成

- **零中断**：翻译失败时自动降级使用原译文
- **进度透明**：实时更新处理进度
- **日志详细**：方便调试和监控

## 配置选项

### 可调参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_ratio` | 1.2 | 最大长度比例 |
| `num_processes` | 1 | 重新翻译进程数 |
| `timeout` | 600 | 重新翻译超时（秒） |
| `model_path` | `models/Qwen3-1.7B` | LLM 模型路径 |

### 调整示例

**更严格的验证**：
```python
is_too_long, _, _, _ = check_translation_length(
    source, target, language, max_ratio=1.1  # 1.1倍
)
```

**使用多进程重新翻译**（如果显存充足）：
```python
retranslate_config = {
    "tasks": retranslate_tasks,
    "model_path": model_path,
    "num_processes": 2  # 使用2个进程
}
```

## 依赖要求

### Python 环境

1. **ui 环境**（后端主环境）
   - 已有依赖即可
   - 无新增依赖

2. **qwen_inference 环境**（LLM 推理）
   - transformers
   - torch
   - 已在 `LLM_batch_inference.py` 中使用

### 模型要求

- **Qwen3-1.7B** 或兼容的 LLM 模型
- 路径：`<项目根>/models/Qwen3-1.7B`

## 测试方法

### 1. 单元测试

```bash
cd backend
conda activate ui
python test_text_utils.py
```

**预期输出**：
```
============================================================
文本工具模块测试
============================================================

============================================================
测试中文规范化
============================================================
✅ '你好，世界！' -> '你好世界' (期望: '你好世界')
✅ '这是一个测试。' -> '这是一个测试' (期望: '这是一个测试')
...

所有测试完成！
```

### 2. 集成测试

1. 准备测试数据：
   - 视频文件
   - 源字幕（中文）
   - 目标字幕（英文，故意添加一些超长译文）

2. 启动后端：
   ```bash
   cd backend
   conda activate ui
   uvicorn main:app --reload
   ```

3. 触发语音克隆流程

4. 观察日志输出，验证：
   - 是否正确识别超长译文
   - 是否成功调用批量重新翻译
   - 是否正确更新字幕

### 3. 批量翻译脚本测试

```bash
cd backend

# 创建测试配置
cat > test_retranslate_config.json << EOF
{
    "tasks": [
        {
            "task_id": "test-1",
            "source": "早上好",
            "target_language": "英文"
        },
        {
            "task_id": "test-2",
            "source": "谢谢你的帮助",
            "target_language": "英文"
        }
    ],
    "model_path": "../../models/Qwen3-1.7B",
    "num_processes": 1
}
EOF

# 运行测试
conda activate qwen_inference
python batch_retranslate.py test_retranslate_config.json
```

## 已知限制

### 1. 语言支持

- 目前主要优化了中文→英文的场景
- 其他语言对（如日语、韩语）需要调整规范化算法

### 2. 长度比例阈值

- 固定 1.2 倍可能不适合所有语言对
- 某些语言天然表达较长（如德语）

### 3. LLM 翻译质量

- 依赖 Qwen3-1.7B 模型质量
- 简洁 prompt 可能牺牲部分翻译准确性
- 建议人工检查重要场景的翻译

## 未来优化方向

### 1. 自适应阈值

根据语言对自动调整长度比例：

```python
thresholds = {
    "中文->英文": 1.2,
    "中文->日文": 1.5,
    "中文->德文": 1.8
}
```

### 2. 翻译质量评估

- 引入翻译质量评分（如 BLEU、COMET）
- 平衡长度和质量

### 3. 缓存机制

- 缓存常见短语的翻译
- 避免重复翻译

### 4. 用户交互

- 翻译前预览超长译文
- 允许用户手动编辑
- 批量接受/拒绝重新翻译

## 相关文档

- [详细功能文档](./translation_length_validation.md)
- [多进程语音克隆](./multiprocess_voice_cloning.md)
- [NISQA MOS 评分](./nisqa_integration.md)

## 维护者

- 初始实现：2025-12-13
- 基于需求：避免语音克隆中译文过长导致语音过长

## 反馈

如有问题或建议，请联系项目维护者或提交 Issue。
