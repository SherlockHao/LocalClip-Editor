# 调试：重新翻译的文本显示问题

## 问题描述

**现象**：
- ✅ 重新翻译功能生效（LLM 生成了更短的译文）
- ✅ 字幕文件已更新（文件中是新译文）
- ✅ 生成的克隆音频对应新译文（音频更短）
- ✅ 前端左侧字幕块中的**音频**已更新
- ❌ 前端左侧字幕块中的**文本**仍然显示旧译文

## 数据流分析

### 后端流程

```
1. 读取目标字幕 (target_subtitles)
   ↓
2. 检测超长译文
   ↓
3. 批量重新翻译
   ↓
4. 更新 target_subtitles[idx]["text"] = new_translation  ← 内存更新
   ↓
5. 保存到字幕文件 srt_parser.save_srt()  ← 文件更新
   ↓
6. 使用更新后的 target_subtitles 准备任务
   ↓
7. 构建 cloned_results：
   for idx, target_sub in enumerate(target_subtitles):
       target_text = target_sub["text"]  ← 应该是新译文
       cloned_results.append({
           "index": idx,
           "target_text": target_text  ← 传给前端
       })
   ↓
8. 返回给前端: {"cloned_results": cloned_results}
```

### 前端流程

```javascript
// App.tsx:513-528
if (status.cloned_results && Array.isArray(status.cloned_results)) {
  setSubtitles(prevSubtitles => {
    return prevSubtitles.map((subtitle, index) => {
      const clonedResult = status.cloned_results.find((r: any) => r.index === index);
      if (clonedResult) {
        return {
          ...subtitle,
          target_text: clonedResult.target_text,  ← 更新前端字幕
          cloned_audio_path: clonedResult.cloned_audio_path,
          cloned_speaker_id: clonedResult.speaker_id
        };
      }
      return subtitle;
    });
  });
}
```

## 可能的原因

### 假设 1：后端 cloned_results 中的 target_text 是旧的

**检查点**：
- `target_subtitles` 在重新翻译后是否真的更新了？
- 构建 `cloned_results` 时是否使用了更新后的 `target_subtitles`？

**已添加的调试日志**：

1. **重新翻译结果**：
   ```python
   print(f"\n[Retranslate] 解析到 {len(retranslate_results)} 条重新翻译结果:")
   print(json.dumps(retranslate_results, ensure_ascii=False, indent=2))
   ```

2. **更新详情**：
   ```python
   for result_item in retranslate_results:
       idx = int(result_item["task_id"].split('-')[1])
       new_translation = result_item["translation"]
       old_translation = target_subtitles[idx]["text"]

       print(f"  [更新 {idx}]")
       print(f"    旧: '{old_translation}'")
       print(f"    新: '{new_translation}'")
   ```

3. **保存验证**：
   ```python
   print(f"\n[Retranslate] 验证保存结果...")
   saved_subtitles = srt_parser.parse_srt(target_subtitle_path)
   for result_item in retranslate_results:
       idx = int(result_item["task_id"].split('-')[1])
       saved_text = saved_subtitles[idx]["text"]
       expected_text = result_item["translation"]
       match = "✅" if saved_text == expected_text else "❌"
       print(f"  {match} [{idx}] 文件中: '{saved_text}'")
   ```

4. **准备任务时的 target_subtitles**：
   ```python
   print(f"\n[DEBUG] 准备任务列表，target_subtitles 中前3条文本:")
   for i in range(min(3, len(target_subtitles))):
       print(f"  [{i}] {target_subtitles[i]['text']}")
   ```

5. **cloned_results 中的 target_text**：
   ```python
   print(f"\n[DEBUG] cloned_results 示例 (前3个):")
   for i, result in enumerate(cloned_results[:3]):
       print(f"  [{i}] index={result['index']}, speaker_id={result['speaker_id']}")
       print(f"      target_text='{result['target_text']}'")
       print(f"      cloned_audio_path={result.get('cloned_audio_path', 'None')}")
   ```

### 假设 2：前端缓存问题

**可能性**：
- 前端在某个地方缓存了旧的字幕文本
- 更新 `target_text` 时被覆盖或忽略

**检查点**：
- 浏览器控制台的 Network 标签，查看 `/voice-cloning/status/{task_id}` 返回的数据
- React DevTools 查看 `subtitles` state 的值

### 假设 3：字幕文件路径问题

**可能性**：
- 前端读取的字幕文件和后端更新的不是同一个文件
- 有多个副本存在

**检查点**：
- 确认前端和后端使用的字幕文件路径一致

## 调试步骤

### 步骤 1：重启后端，查看调试日志

重启后端后，触发语音克隆，查看日志输出：

```
⚠️  发现 1 条超长译文，准备批量重新翻译...

[Retranslate] 解析到 1 条重新翻译结果:
[
  {
    "task_id": "retrans-0",
    "source": "你好啊",
    "translation": "Hello",
    "process_id": 1,
    "time": 1.23,
    "target_language": "en"
  }
]

  [更新 0]
    旧: 'Hello there my friend'
    新: 'Hello'

✅ 成功重新翻译 1 条文本

[Retranslate] 保存更新后的字幕到: uploads/srt_en_qwen.srt
✅ 字幕文件已更新

[Retranslate] 验证保存结果...
  ✅ [0] 文件中: 'Hello'

[DEBUG] 准备任务列表，target_subtitles 中前3条文本:
  [0] Hello  ← 应该是新译文
  [1] ...
  [2] ...

[DEBUG] cloned_results 示例 (前3个):
  [0] index=0, speaker_id=...
      target_text='Hello'  ← 应该是新译文
      cloned_audio_path=/cloned-audio/...
```

**关键检查点**：
1. `target_subtitles[0]['text']` 是否是 `'Hello'`？
2. `cloned_results[0]['target_text']` 是否是 `'Hello'`？

### 步骤 2：检查前端接收的数据

打开浏览器开发者工具：
1. **Network 标签** → 找到 `/voice-cloning/status/{task_id}` 请求
2. **查看 Response** → `cloned_results[0].target_text` 的值
3. **如果是新译文** → 问题在前端
4. **如果是旧译文** → 问题在后端

### 步骤 3：检查前端 state

使用 React DevTools：
1. 查找 `App` 组件
2. 查看 `subtitles` state
3. 找到 index=0 的字幕
4. 查看 `target_text` 的值

## 预期结果

### 正常情况

**后端日志**：
```
[更新 0]
  旧: 'Hello there my friend'
  新: 'Hello'

[DEBUG] target_subtitles 中前3条文本:
  [0] Hello  ✅

[DEBUG] cloned_results 示例:
  [0] target_text='Hello'  ✅
```

**前端显示**：
- 字幕块中显示 `Hello` ✅

### 异常情况 A：后端 target_subtitles 未更新

**后端日志**：
```
[更新 0]
  旧: 'Hello there my friend'
  新: 'Hello'

[DEBUG] target_subtitles 中前3条文本:
  [0] Hello there my friend  ❌ 还是旧的！
```

**原因**：内存更新失败
**解决**：检查 `target_subtitles[idx]["text"] = new_translation` 是否执行

### 异常情况 B：后端 cloned_results 使用了错误的数据源

**后端日志**：
```
[DEBUG] target_subtitles 中前3条文本:
  [0] Hello  ✅

[DEBUG] cloned_results 示例:
  [0] target_text='Hello there my friend'  ❌ 没有用 target_subtitles！
```

**原因**：`cloned_results` 构建时使用了其他数据源
**解决**：检查第 946 行 `target_text = target_sub["text"]` 是否正确

### 异常情况 C：前端未更新

**后端日志**：全部正确 ✅

**浏览器 Network**：`cloned_results[0].target_text = 'Hello'` ✅

**前端显示**：还是 `Hello there my friend` ❌

**原因**：前端更新逻辑有问题
**解决**：检查 `App.tsx:514-527` 的 `setSubtitles` 逻辑

## 后续计划

根据调试日志的输出，确定问题所在：

1. **如果 target_subtitles 未更新** → 修复内存更新逻辑
2. **如果 cloned_results 构建错误** → 修复数据源
3. **如果前端未更新** → 检查前端 React 代码

## 相关文件

| 文件 | 关键位置 |
|------|---------|
| `backend/main.py` | 行 877-909: 重新翻译和保存 |
| `backend/main.py` | 行 941-946: 准备任务，读取 target_text |
| `backend/main.py` | 行 987-1000: 构建 cloned_results |
| `frontend/src/App.tsx` | 行 513-528: 更新前端 subtitles |

## 测试命令

```bash
# 1. 重启后端
cd c:\workspace\ai_editing\workspace\LocalClip-Editor\backend
# Ctrl+C 停止当前进程
conda activate ui
uvicorn main:app --reload

# 2. 触发语音克隆
# 在前端上传视频和字幕，点击"开始语音克隆"

# 3. 查看后端日志
# 寻找以下关键输出：
# - [Retranslate] 解析到 X 条重新翻译结果
# - [更新 X] 旧: '...' 新: '...'
# - [DEBUG] target_subtitles 中前3条文本
# - [DEBUG] cloned_results 示例

# 4. 查看前端
# 打开浏览器开发者工具 → Network → 查看 /voice-cloning/status 响应
```

## 版本历史

- **v1.0** (2025-12-13): 添加详细调试日志
  - 打印重新翻译结果
  - 打印更新前后对比
  - 验证文件保存
  - 打印 target_subtitles 和 cloned_results
