# 译文长度验证与批量重新翻译

## 概述

在语音克隆过程中，如果译文过长会导致生成的语音片段过长，影响最终视频质量。本系统在语音克隆前自动验证译文长度，对超长译文批量重新翻译为更简洁的版本。

## 工作流程

```
用户点击语音克隆
    ↓
读取源字幕和目标字幕
    ↓
逐句验证译文长度
    ↓
发现超长译文？
    ├─ 否 → 直接进行语音克隆
    └─ 是 ↓
        收集所有超长译文
        ↓
        批量重新翻译（LLM）
        ↓
        更新目标字幕
        ↓
        继续语音克隆
```

## 长度验证规则

### 1. 文本规范化

**中文文本**：
- 移除所有标点符号和空格
- 只统计汉字数量
- 示例：
  ```
  原文: "你好，世界！这是测试。"
  规范化: "你好世界这是测试"
  长度: 8 个字
  ```

**英文文本**：
- 移除所有标点符号
- 特殊处理缩写（"I'm", "don't" 等算作一个单词）
- 统计单词数量
- 示例：
  ```
  原文: "Hello, I'm testing this!"
  规范化: "Hello Im testing this"
  长度: 4 个词
  ```

### 2. 长度比较

- **最大比例**：1.2 倍（可配置）
- **判断标准**：译文长度 ÷ 原文长度 > 1.2
- **示例**：

| 原文（中文） | 长度 | 译文（英文） | 长度 | 比例 | 结果 |
|------------|------|-------------|------|------|------|
| "你好世界" | 4字 | "Hello world" | 2词 | 0.5 | ✅ 合格 |
| "这是一个测试" | 6字 | "This is a test" | 4词 | 0.67 | ✅ 合格 |
| "欢迎使用" | 4字 | "Welcome to use our system" | 5词 | 1.25 | ❌ 超长 |
| "早上好" | 3字 | "Good morning everyone" | 3词 | 1.0 | ✅ 合格 |

## 批量重新翻译

### 架构设计

基于 [LLM_batch_inference.py](../../LLM/LLM_batch_inference.py) 的多进程设计：

```python
# 关键特点
1. 模型只加载一次
2. 所有超长文本批量处理
3. 使用 qwen_inference 环境
4. 通过 subprocess 调用独立脚本
```

### 翻译 Prompt

```
将中文翻译成{目标语言}，语言简洁且口语化：{原文}
```

**设计原则**：
- 简洁明确，不包含复杂指令
- 强调"简洁"和"口语化"
- 避免模型输出过长翻译

### 实现流程

1. **检测超长译文**
   ```python
   too_long_items = []
   for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
       is_too_long, _, _, ratio = check_translation_length(
           source_sub["text"],
           target_sub["text"],
           target_language,
           max_ratio=1.2
       )
       if is_too_long:
           too_long_items.append({...})
   ```

2. **准备重新翻译任务**
   ```python
   retranslate_tasks = [
       {
           "task_id": f"retrans-{idx}",
           "source": "原文",
           "target_language": "英文"
       }
       for item in too_long_items
   ]
   ```

3. **生成配置文件**
   ```json
   {
       "tasks": [...],
       "model_path": "path/to/Qwen3-1.7B",
       "num_processes": 1
   }
   ```

4. **调用批量翻译脚本**
   ```bash
   python batch_retranslate.py config.json
   ```

5. **解析结果并更新字幕**
   ```python
   for result in retranslate_results:
       idx = int(result["task_id"].split('-')[1])
       target_subtitles[idx]["text"] = result["translation"]
   ```

## 配置

### 环境变量 (.env)

```bash
# Qwen Inference Python 解释器路径
QWEN_INFERENCE_PYTHON=C:\Users\7\miniconda3\envs\qwen_inference\python.exe
```

### 默认路径

如果未配置环境变量，系统使用默认路径：

- **Windows**: `C:\Users\7\miniconda3\envs\qwen_inference\python.exe`
- **Linux/Mac**: `~/miniconda3/envs/qwen_inference/bin/python`

### 模型路径

- 默认：`<项目根目录>/models/Qwen3-1.7B`
- 可在配置文件中自定义

## 性能优化

### 单进程模式

```python
"num_processes": 1  # 避免与语音克隆模型争夺显存
```

**原因**：
- 语音克隆阶段已占用大量显存
- LLM 重新翻译使用单进程，避免 OOM
- 通常超长译文数量较少（< 10条），单进程已足够快

### 超时控制

```python
timeout=600  # 10分钟超时
```

**处理策略**：
- 超时或失败：使用原译文继续
- 不会阻塞整个语音克隆流程
- 记录警告日志

## 使用示例

### 完整流程

```
1. 用户上传视频、源字幕、目标字幕
   ↓
2. 点击"开始语音克隆"
   ↓
3. 系统自动验证译文长度
   ↓
4. 如果发现 3 条超长译文：
   ⚠️  发现 3 条超长译文，准备批量重新翻译...

   [Retranslate] 使用 Python: C:\...\qwen_inference\python.exe
   [Retranslate] 脚本: batch_retranslate.py
   [Retranslate] 配置: retranslate_config.json

   [Process 1] Processing task retrans-12...
   [Process 1] Processing task retrans-34...
   [Process 1] Processing task retrans-56...

   ✅ 成功重新翻译 3 条文本
   ↓
5. 使用新译文继续语音克隆
```

### 日志输出

```
[Voice Clone] 正在验证译文长度...
⚠️  发现 3 条超长译文，准备批量重新翻译...

超长译文列表:
  [12] 原文: "早上好" (3字)
       译文: "Good morning everyone, have a nice day" (7词)
       比例: 2.33x ❌

  [34] 原文: "谢谢" (2字)
       译文: "Thank you very much for your help" (7词)
       比例: 3.5x ❌

[Retranslate] 批量重新翻译中...
[Process 1] Task retrans-12 completed in 1.23s
  原文: 早上好
  译文: Good morning

[Process 1] Task retrans-34 completed in 1.15s
  原文: 谢谢
  译文: Thanks

✅ 成功重新翻译 2 条文本

新译文长度验证:
  [12] "Good morning" (2词) → 比例: 0.67x ✅
  [34] "Thanks" (1词) → 比例: 0.5x ✅
```

## 技术细节

### 文本规范化算法

**中文**：
```python
def normalize_chinese(text: str) -> str:
    # 只保留汉字 (Unicode: 0x4E00-0x9FFF)
    return re.sub(r'[^\u4e00-\u9fff]', '', text)
```

**英文**：
```python
def normalize_english(text: str) -> str:
    # 1. 保护缩写中的撇号
    text = re.sub(r"(\w)'(\w)", r"\1APOSTROPHE\2", text)

    # 2. 移除所有标点
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)

    # 3. 恢复撇号（作为单词一部分）
    text = text.replace('APOSTROPHE', '')

    # 4. 标准化空格
    return ' '.join(text.split())
```

### 批量翻译脚本接口

**输入** (`retranslate_config.json`):
```json
{
    "tasks": [
        {
            "task_id": "retrans-0",
            "source": "原文（中文）",
            "target_language": "英文"
        }
    ],
    "model_path": "path/to/Qwen3-1.7B",
    "num_processes": 1
}
```

**输出** (stdout 的最后一个 JSON 块):
```json
[
    {
        "task_id": "retrans-0",
        "source": "原文（中文）",
        "translation": "Translation",
        "process_id": 1,
        "time": 1.23,
        "pid": 12345,
        "target_language": "英文"
    }
]
```

## 故障排查

### 问题 1: 重新翻译失败

**症状**：
```
⚠️  重新翻译失败: [Errno 2] No such file or directory: '...'
使用原译文继续...
```

**解决**：
1. 检查 `QWEN_INFERENCE_PYTHON` 环境变量是否正确
2. 确认 qwen_inference conda 环境存在
3. 验证 Qwen3-1.7B 模型已下载

### 问题 2: 重新翻译超时

**症状**：
```
⚠️  重新翻译超时，使用原译文继续...
```

**原因**：
- 模型加载慢
- 任务数量过多（>20条）
- 显存不足导致推理慢

**解决**：
- 检查显存是否充足
- 确认模型路径正确
- 适当增加超时时间（修改 `timeout=600`）

### 问题 3: 未找到重新翻译结果

**症状**：
```
⚠️  未找到重新翻译结果，使用原译文
```

**原因**：
- 脚本输出格式错误
- JSON 解析失败

**解决**：
- 查看完整的 stderr 输出
- 检查 `batch_retranslate.py` 脚本是否正常
- 手动运行脚本测试：
  ```bash
  python batch_retranslate.py retranslate_config.json
  ```

## 最佳实践

### 1. 长度比例调整

根据实际情况调整最大比例：

```python
# 更严格（1.15倍）
is_too_long, _, _, _ = check_translation_length(
    source, target, language, max_ratio=1.15
)

# 更宽松（1.5倍）
is_too_long, _, _, _ = check_translation_length(
    source, target, language, max_ratio=1.5
)
```

### 2. 批量处理阈值

如果超长译文数量很多（>50条），考虑：
- 提高 `num_processes` 到 2-3（如果显存充足）
- 分批处理，避免一次性翻译过多

### 3. 翻译质量检查

重新翻译后，可选择性地：
- 人工检查关键句子
- 再次验证长度
- 比较原译文和新译文的质量

## 相关文件

| 文件 | 用途 |
|------|------|
| [text_utils.py](../backend/text_utils.py) | 文本规范化、长度计算 |
| [batch_retranslate.py](../backend/batch_retranslate.py) | 批量重新翻译脚本 |
| [main.py:725-860](../backend/main.py#L725-L860) | 验证与重新翻译集成 |
| [.env:49](../.env#L49) | QWEN_INFERENCE_PYTHON 配置 |

## 参考

- [LLM 批量推理示例](../../LLM/LLM_batch_inference.py)
- [NISQA 批量评分](./nisqa_integration.md)
- [多进程语音克隆](./multiprocess_voice_cloning.md)

## 版本历史

- **v1.0** (2025-12-13): 初始版本
  - 自动验证译文长度
  - 批量重新翻译超长文本
  - 基于 LLM_batch_inference.py 的多进程架构
