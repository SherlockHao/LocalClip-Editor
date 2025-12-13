# Bug修复：保存重新翻译后的字幕到文件

## 问题描述

批量重新翻译功能已经生效，LLM 成功生成了更简洁的译文，但是：

**现象**：
- 重新翻译的文本用于语音克隆（生成的语音确实更短了）
- 但前端左侧字幕块中显示的仍然是旧的（超长的）译文

**原因**：
- 代码只更新了内存中的 `target_subtitles` 列表
- 没有将更新后的字幕保存回原始的 SRT 文件
- 前端读取的是原始文件，所以看到的是旧内容

## 解决方案

### 修改位置

**文件**: `backend/main.py`
**行号**: 891-894

### 修改内容

**修改前**:
```python
# 更新目标字幕
for result_item in retranslate_results:
    task_id_str = result_item["task_id"]
    idx = int(task_id_str.split('-')[1])
    new_translation = result_item["translation"]

    target_subtitles[idx]["text"] = new_translation  # ✅ 更新内存

print(f"✅ 成功重新翻译 {len(retranslate_results)} 条文本")

# ❌ 缺少：没有保存到文件！
```

**修改后**:
```python
# 更新目标字幕
for result_item in retranslate_results:
    task_id_str = result_item["task_id"]
    idx = int(task_id_str.split('-')[1])
    new_translation = result_item["translation"]

    old_translation = target_subtitles[idx]["text"]
    target_subtitles[idx]["text"] = new_translation

    # 打印对比
    print(f"  [更新 {idx}] '{old_translation}' -> '{new_translation}'")

print(f"✅ 成功重新翻译 {len(retranslate_results)} 条文本")

# ✅ 保存更新后的字幕到文件
print(f"[Retranslate] 保存更新后的字幕到: {target_subtitle_path}")
srt_parser.save_srt(target_subtitles, target_subtitle_path)
print(f"✅ 字幕文件已更新")
```

### 关键改进

1. **保存到文件**：调用 `srt_parser.save_srt()` 将更新后的字幕保存
2. **打印对比**：显示旧译文 vs 新译文，方便查看效果
3. **确认日志**：明确打印保存路径和成功信息

## 预期行为

现在重新翻译后，您会看到如下日志：

```
⚠️  发现 1 条超长译文，准备批量重新翻译...
[Retranslate] 使用 Python: C:\Users\7\miniconda3\envs\qwen_inference\python.exe
[Retranslate] 启动批量重新翻译进程...

[Process 1] Processing task retrans-0...
[retrans-0] 原文: 你好啊
[retrans-0] 译文: Hello

✅ 成功重新翻译 1 条文本

  [更新 0] 'Hello there my friend' -> 'Hello'

[Retranslate] 保存更新后的字幕到: uploads/srt_en_qwen.srt
✅ 字幕文件已更新

[继续语音克隆...]
```

## 影响范围

### 文件更新

| 文件 | 时机 |
|------|------|
| 目标字幕文件 (如 `srt_en_qwen.srt`) | 重新翻译成功后立即更新 |
| 内存中的 `target_subtitles` | 同时更新 |

### 数据流

```
1. 读取目标字幕文件
   ↓
2. 检测超长译文
   ↓
3. 批量重新翻译
   ↓
4. 更新内存中的字幕 (target_subtitles)
   ↓
5. ✅ 保存到文件 (新增)
   ↓
6. 使用更新后的字幕生成语音
   ↓
7. 前端读取文件 → 显示新译文 ✅
```

## 测试验证

### 测试步骤

1. **上传视频和字幕**
2. **触发语音克隆**
3. **观察日志**：查看是否有重新翻译
4. **检查字幕文件**：
   ```bash
   # 查看目标字幕文件
   cat uploads/srt_en_qwen.srt
   ```
5. **查看前端**：左侧字幕块应显示新的简洁译文

### 验收标准

✅ 重新翻译成功后，日志显示：
```
  [更新 X] '旧译文' -> '新译文'
✅ 字幕文件已更新
```

✅ 字幕文件内容已更新（可直接打开查看）

✅ 前端左侧字幕块显示新译文

✅ 生成的语音使用新译文（更短）

## 相关代码

### SRTParser.save_srt()

**文件**: `backend/srt_parser.py:78-88`

```python
def save_srt(self, subtitles: List[Dict], srt_path: str):
    """保存字幕到SRT文件"""
    try:
        with open(srt_path, 'w', encoding='utf-8') as file:
            for i, sub in enumerate(subtitles, 1):
                block = f"{i}\n"
                block += f"{sub['start_time_formatted']} --> {sub['end_time_formatted']}\n"
                block += f"{sub['text']}\n\n"
                file.write(block)
    except Exception as e:
        print(f"保存SRT文件时出错: {e}")
```

**特点**：
- UTF-8 编码写入
- 标准 SRT 格式
- 自动处理序号、时间戳、文本

## 边界情况处理

### 情况 1：重新翻译失败

```python
if returncode != 0:
    print(f"⚠️  重新翻译失败")
    # 不保存，使用原译文
```

**行为**：不修改文件，前端显示原译文 ✅

### 情况 2：部分译文重新翻译

```python
# 只更新成功翻译的部分
for result_item in retranslate_results:
    idx = int(result_item["task_id"].split('-')[1])
    target_subtitles[idx]["text"] = result_item["translation"]

# 保存整个字幕文件（包含未修改的部分）
srt_parser.save_srt(target_subtitles, target_subtitle_path)
```

**行为**：混合新旧译文，只更新超长的部分 ✅

### 情况 3：无超长译文

```python
if too_long_items:
    # 执行重新翻译
else:
    # 跳过，不修改文件
```

**行为**：不触发保存，文件保持原样 ✅

## 性能影响

**文件写入开销**：
- 单次写入，覆盖整个文件
- 通常 < 1ms（50 条字幕）
- 相比翻译时间（15-30s）可忽略

**磁盘 I/O**：
- 写入时机：重新翻译成功后
- 文件大小：通常 < 10KB
- 影响：极小

## 日志示例

### 成功场景

```
⚠️  发现 2 条超长译文，准备批量重新翻译...

[Retranslate] 使用 Python: C:\...\qwen_inference\python.exe
[Retranslate] 脚本: batch_retranslate.py
[Retranslate] 配置: retranslate_config.json
[Retranslate] 模型路径: C:\workspace\ai_editing\models\Qwen3-1.7B
[Retranslate] 启动批量重新翻译进程...

[Process 1] Processing task retrans-0...
[retrans-0] 原文: 早上好
[retrans-0] 译文: Good morning

[Process 1] Processing task retrans-5...
[retrans-5] 原文: 谢谢
[retrans-5] 译文: Thanks

✅ 成功重新翻译 2 条文本

  [更新 0] 'Good morning everyone, have a nice day' -> 'Good morning'
  [更新 5] 'Thank you very much for your help' -> 'Thanks'

[Retranslate] 保存更新后的字幕到: uploads/srt_en_qwen.srt
✅ 字幕文件已更新

[Voice Clone] 正在批量生成克隆语音...
```

### 失败场景（文件不修改）

```
⚠️  发现 1 条超长译文，准备批量重新翻译...
[Retranslate] 启动批量重新翻译进程...
⚠️  重新翻译失败 (返回码: 1)
使用原译文继续...

[Voice Clone] 正在批量生成克隆语音...
```

## 用户体验改进

### 之前

1. 重新翻译生效（语音变短了）
2. 但前端显示的还是旧译文
3. 用户困惑：为什么显示的和实际不一致？

### 现在

1. 重新翻译生效（语音变短了）
2. 前端显示新的简洁译文
3. 字幕文件已更新，可直接查看
4. 数据一致性 ✅

## 后续优化建议

### 1. 备份原始字幕

```python
# 保存前先备份
backup_path = target_subtitle_path + ".backup"
import shutil
shutil.copy(target_subtitle_path, backup_path)

# 然后保存
srt_parser.save_srt(target_subtitles, target_subtitle_path)
```

### 2. 版本控制

```python
# 保存带时间戳的版本
import datetime
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
versioned_path = f"{target_subtitle_path}.{timestamp}"
srt_parser.save_srt(target_subtitles, versioned_path)
```

### 3. 通知前端刷新

```python
# 通过 WebSocket 或状态标志通知前端
voice_cloning_status[task_id]["subtitles_updated"] = True
```

## 版本历史

- **v1.0** (2025-12-13): 初始修复
  - 添加字幕文件保存逻辑
  - 添加更新日志输出
  - 确保前后端数据一致性

## 相关文档

- [译文长度验证功能](./translation_length_validation.md)
- [批量重新翻译](./CHANGELOG_translation_validation.md)
- [编码问题修复](./BUGFIX_encoding_issues.md)
