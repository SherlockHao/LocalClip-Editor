# 批量翻译功能

## 概述

本次更新将"上传目标语言字幕"功能替换为"自动翻译字幕"功能。用户选择目标语言后，系统会使用 Ollama 自动将原字幕翻译为目标语言，无需手动上传翻译好的字幕文件。

---

## 功能特点

✅ **自动翻译**：无需手动翻译字幕，选择语言后自动完成
✅ **实时进度**：显示翻译进度和当前状态
✅ **异步处理**：后台执行翻译，不阻塞界面
✅ **语言支持**：支持英语、韩语、日语、法语
✅ **智能Prompt**：日语使用特殊prompt（口语化、极简、使用假名）
✅ **并发翻译**：使用 asyncio 并发翻译，充分利用 GPU

---

## 修改文件清单

### 前端

| 文件 | 修改内容 | 状态 |
|-----|---------|------|
| `frontend/src/components/PropertiesPanel.tsx` | 替换上传按钮为翻译按钮，添加进度显示 | ✅ 完成 |
| `frontend/src/App.tsx` | 添加翻译状态、翻译函数、轮询逻辑 | ✅ 完成 |

### 后端

| 文件 | 修改内容 | 状态 |
|-----|---------|------|
| `backend/main.py` | 添加批量翻译API、状态查询API | ✅ 完成 |
| `backend/batch_translate_ollama.py` | 创建批量翻译脚本 | ✅ 完成 |
| `backend/BATCH_TRANSLATION_FEATURE.md` | 功能文档 | ✅ 完成 |

---

## 详细修改

### 1. 前端修改

#### PropertiesPanel.tsx

**修改前**：上传目标语言SRT按钮
```tsx
<label>
  <FileText size={16} className="mr-2" />
  <span>{targetSrtFilename ? '已上传 SRT' : '上传目标语言 SRT'}</span>
  <input type="file" accept=".srt" onChange={handleTargetSrtFileSelect} />
</label>
```

**修改后**：翻译字幕按钮 + 进度显示
```tsx
<button onClick={onTranslateSubtitles} disabled={...}>
  {isTranslating ? (
    <>
      <div className="spinner mr-2"></div>
      <span>翻译中...</span>
    </>
  ) : targetSrtFilename ? (
    <>
      <CheckIcon />
      <span>翻译完成</span>
    </>
  ) : (
    <>
      <FileText size={16} className="mr-2" />
      <span>翻译字幕</span>
    </>
  )}
</button>

{isTranslating && translationProgress && (
  <div className="mt-2">
    <div className="flex justify-between text-xs text-slate-400 mb-1">
      <span>{translationProgress.message}</span>
      <span>{translationProgress.progress}%</span>
    </div>
    <div className="w-full bg-slate-700 rounded-full h-1.5">
      <div className="bg-gradient-to-r from-purple-600 to-purple-400 h-1.5 rounded-full"
           style={{ width: `${translationProgress.progress}%` }}>
      </div>
    </div>
  </div>
)}
```

**新增Props**：
- `onTranslateSubtitles: () => void` - 翻译按钮点击处理
- `isTranslating: boolean` - 是否正在翻译
- `translationProgress: { message: string; progress: number } | null` - 翻译进度

---

#### App.tsx

**新增状态**：
```tsx
const [isTranslating, setIsTranslating] = useState(false);
const [translationProgress, setTranslationProgress] = useState<{message: string, progress: number} | null>(null);
```

**翻译函数**：
```tsx
const handleTranslateSubtitles = async () => {
  if (!subtitleFilename) {
    alert('请先上传原始SRT字幕文件');
    return;
  }

  if (!targetLanguage) {
    alert('请选择目标语言');
    return;
  }

  try {
    setIsTranslating(true);
    setTranslationProgress({ message: '正在准备翻译...', progress: 0 });

    const response = await fetch('/api/translate/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_subtitle_filename: subtitleFilename,
        target_language: targetLanguage,
      }),
    });

    const result = await response.json();
    pollTranslationStatus(result.task_id);
  } catch (error) {
    alert('启动翻译失败: ' + (error as Error).message);
    setIsTranslating(false);
    setTranslationProgress(null);
  }
};
```

**轮询翻译状态**：
```tsx
const pollTranslationStatus = async (taskId: string) => {
  const response = await fetch(`/api/translate/status/${taskId}`);
  const result = await response.json();

  if (result.status === 'processing') {
    setTranslationProgress({
      message: result.message || '翻译中...',
      progress: result.progress || 0
    });
    setTimeout(() => pollTranslationStatus(taskId), 1000);
  } else if (result.status === 'completed') {
    setTranslationProgress({ message: '翻译完成', progress: 100 });
    setTargetSrtFilename(result.target_srt_filename);
    setIsTranslating(false);
    setTimeout(() => setTranslationProgress(null), 2000);
  } else if (result.status === 'failed') {
    throw new Error(result.message || '翻译失败');
  }
};
```

---

### 2. 后端修改

#### main.py - 全局状态

```python
# 全局变量用于存储翻译处理状态
translation_status = {}
```

#### main.py - 请求模型

```python
class BatchTranslateRequest(BaseModel):
    source_subtitle_filename: str
    target_language: str
```

#### main.py - API接口

**1. 启动批量翻译**：`POST /api/translate/batch`

```python
@app.post("/api/translate/batch")
async def batch_translate_subtitles(request: BatchTranslateRequest, background_tasks: BackgroundTasks):
    """批量翻译字幕文件"""
    task_id = str(uuid.uuid4())

    translation_status[task_id] = {
        "status": "processing",
        "message": "正在准备翻译...",
        "progress": 0,
        "source_subtitle_filename": request.source_subtitle_filename,
        "target_language": request.target_language
    }

    background_tasks.add_task(
        run_batch_translation,
        task_id,
        request.source_subtitle_filename,
        request.target_language
    )

    return {"task_id": task_id, "message": "翻译任务已启动"}
```

**2. 查询翻译状态**：`GET /api/translate/status/{task_id}`

```python
@app.get("/api/translate/status/{task_id}")
async def get_translation_status(task_id: str):
    """获取翻译状态"""
    if task_id not in translation_status:
        raise HTTPException(status_code=404, detail="翻译任务不存在")

    return translation_status[task_id]
```

**3. 后台翻译任务**：`run_batch_translation()`

主要步骤：
1. 读取原文SRT文件
2. 解析所有字幕条目
3. 创建翻译任务列表
4. 调用 `batch_translate_ollama.py` 脚本
5. 实时更新进度
6. 解析翻译结果
7. 生成新的SRT文件
8. 保存文件并更新状态

```python
async def run_batch_translation(task_id: str, source_subtitle_filename: str, target_language: str):
    # 1. 读取原文字幕
    source_srt_path = UPLOADS_DIR / source_subtitle_filename

    # 2. 解析SRT（正则表达式）
    subtitle_pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n((?:.*\n?)+?)(?=\n\d+\n|\n*$)'
    matches = re.findall(subtitle_pattern, source_content)

    # 3. 创建翻译任务
    translate_tasks = [{
        "task_id": f"tr-{sub['index']}",
        "source": sub["text"],
        "target_language": target_language_name
    } for sub in subtitles]

    # 4. 调用翻译脚本
    process = subprocess.Popen([ui_env_python, batch_translate_script, config_file], ...)

    # 5. 实时读取输出并更新进度
    for line in process.stdout:
        if line.startswith('[') and '/' in line:
            # 解析: [5/30] ✓ tr-4: ...
            current, total = parse_progress(line)
            progress = 10 + int((current / total) * 80)
            translation_status[task_id]["progress"] = progress

    # 6. 解析JSON结果
    results = json.loads(json_text)

    # 7. 生成SRT文件
    target_srt_filename = f"translated_{target_language}_{source_filename}.srt"
    srt_content = generate_srt(translated_subtitles)

    # 8. 保存并更新状态
    with open(target_srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    translation_status[task_id]["status"] = "completed"
    translation_status[task_id]["target_srt_filename"] = target_srt_filename
```

---

#### batch_translate_ollama.py

新建的翻译脚本，基于 `batch_retranslate_ollama.py`：

```python
async def translate_single(client, sentence, target_language, task_id, model="qwen3:4b"):
    """单个翻译任务"""
    # 日语特殊prompt
    if '日' in target_language or 'ja' in target_language.lower():
        prompt = f'请将以下中文翻译成{target_language}（口语化、极简、使用假名），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
    else:
        prompt = f'请将以下中文翻译成{target_language}（口语化、极简），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'

    response = await client.chat.completions.create(model=model, messages=[...])
    result = response.choices[0].message.content.strip()
    translation = extract_translation_from_json(result, sentence)

    return {"task_id": task_id, "source": sentence, "translation": translation, ...}


async def batch_translate(tasks, model="qwen3:4b"):
    """批量翻译任务"""
    # 1. 确保 Ollama 运行
    if not check_ollama_running():
        start_ollama_server()

    # 2. 创建异步客户端
    client = AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    # 3. 创建所有翻译任务
    translate_tasks = [translate_single(...) for task in tasks]

    # 4. 并发执行，逐个返回结果
    results = []
    for i, coro in enumerate(asyncio.as_completed(translate_tasks), 1):
        result = await coro
        results.append(result)
        print(f"[{i}/{total}] ✓ {result['task_id']}: {source} -> {translation}")

    return results
```

---

## 使用流程

### 用户操作流程

1. **上传视频和原文字幕**
   - 上传中文视频
   - 上传中文SRT字幕

2. **运行说话人识别**
   - 点击"运行说话人识别"
   - 等待识别完成

3. **选择目标语言**
   - 在下拉框选择：英语/韩语/日语/法语

4. **点击"翻译字幕"按钮**
   - 系统自动开始翻译
   - 显示实时进度（例如："正在翻译... (15/30)"）
   - 进度条显示百分比

5. **翻译完成**
   - 按钮显示"翻译完成" ✓
   - 显示"已翻译为XX语"
   - 自动启用"运行语音克隆"按钮

6. **运行语音克隆**
   - 点击"运行语音克隆"
   - 使用翻译后的字幕生成语音

---

### 系统处理流程

```
[前端] 点击翻译按钮
   ↓
[前端] POST /api/translate/batch
   {
     source_subtitle_filename: "xxx.srt",
     target_language: "ja"
   }
   ↓
[后端] 生成task_id，初始化状态
   ↓
[后端] 后台任务：run_batch_translation()
   ├─ 读取原文SRT
   ├─ 解析字幕条目
   ├─ 创建翻译任务列表
   ├─ 调用 batch_translate_ollama.py
   ├─ 实时更新进度
   ├─ 解析翻译结果
   ├─ 生成翻译后SRT
   └─ 保存文件，更新状态为completed
   ↓
[前端] 轮询 GET /api/translate/status/{task_id}
   {
     status: "processing",
     message: "正在翻译... (15/30)",
     progress: 60
   }
   ↓
[前端] 继续轮询...
   {
     status: "completed",
     progress: 100,
     target_srt_filename: "translated_ja_xxx.srt"
   }
   ↓
[前端] 显示翻译完成，启用语音克隆按钮
```

---

## 文件命名规则

翻译后的SRT文件命名格式：
```
translated_{target_language}_{original_filename}.srt
```

示例：
- 原文件：`source_subtitle.srt`
- 目标语言：日语 (`ja`)
- 翻译后：`translated_ja_source_subtitle.srt`

---

## 翻译Prompt对比

### 日语特殊Prompt
```
请将以下中文翻译成日语（口语化、极简、使用假名），以 JSON 格式输出，Key 为 "tr"：

今天天气真好
```

期望输出：
```json
{"tr": "きょうはほんとうにいいてんきですね"}
```

### 其他语言通用Prompt
```
请将以下中文翻译成英语（口语化、极简），以 JSON 格式输出，Key 为 "tr"：

今天天气真好
```

期望输出：
```json
{"tr": "Nice weather today"}
```

---

## 进度显示说明

| 进度范围 | 阶段 | 说明 |
|---------|------|------|
| 0-5% | 初始化 | 正在准备翻译... |
| 5-10% | 读取文件 | 正在读取原文字幕... |
| 10-90% | 翻译中 | 正在翻译... (15/30) |
| 90-100% | 保存 | 正在保存翻译结果... |
| 100% | 完成 | 翻译完成 |

进度计算公式：
```typescript
progress = 10 + (current / total) * 80
```

例如：翻译 30 条字幕，完成 15 条
```
progress = 10 + (15 / 30) * 80 = 50%
```

---

## 错误处理

### 前端错误处理

1. **启动翻译失败**
   ```tsx
   catch (error) {
     alert('启动翻译失败: ' + (error as Error).message);
     setIsTranslating(false);
     setTranslationProgress(null);
   }
   ```

2. **轮询状态失败**
   ```tsx
   if (result.status === 'failed') {
     throw new Error(result.message || '翻译失败');
   }
   ```

### 后端错误处理

1. **文件不存在**
   ```python
   if not os.path.exists(source_srt_path):
       raise FileNotFoundError(f"原文字幕文件不存在: {source_srt_path}")
   ```

2. **SRT解析失败**
   ```python
   if not matches:
       raise ValueError("无法解析SRT文件")
   ```

3. **翻译脚本失败**
   ```python
   if return_code != 0:
       raise Exception(f"翻译脚本失败: {stderr_output}")
   ```

所有错误都会更新状态为：
```python
translation_status[task_id]["status"] = "failed"
translation_status[task_id]["message"] = f"翻译失败: {str(e)}"
```

---

## 性能优化

### 1. 异步并发翻译
使用 `asyncio.as_completed()` 并发执行所有翻译任务：
```python
for i, coro in enumerate(asyncio.as_completed(translate_tasks), 1):
    result = await coro
    # 实时输出进度
```

**优点**：
- 充分利用 GPU 性能
- 多个请求同时处理
- 逐个返回结果，实时反馈

### 2. 后台任务处理
使用 FastAPI 的 `BackgroundTasks`：
```python
background_tasks.add_task(run_batch_translation, task_id, ...)
```

**优点**：
- 不阻塞API响应
- 立即返回task_id
- 用户可以继续操作

### 3. 进度轮询优化
前端每秒轮询一次：
```tsx
setTimeout(() => pollTranslationStatus(taskId), 1000);
```

**优点**：
- 实时更新进度
- 不会过度请求服务器
- 用户体验流畅

---

## 与语音克隆的集成

翻译完成后，翻译的SRT文件会自动设置为 `targetSrtFilename`，后续语音克隆流程保持不变：

```tsx
// 翻译完成
setTargetSrtFilename(result.target_srt_filename);

// 语音克隆按钮启用条件
const isVoiceCloningEnabled =
  speakerDiarizationCompleted &&
  targetLanguage !== '' &&
  targetSrtFilename !== null;  // ← 翻译完成后自动满足
```

---

## 测试清单

- [ ] 选择英语，翻译字幕
- [ ] 选择韩语，翻译字幕
- [ ] 选择日语，翻译字幕（检查是否使用假名）
- [ ] 选择法语，翻译字幕
- [ ] 检查进度显示是否正常
- [ ] 翻译完成后是否启用语音克隆按钮
- [ ] 使用翻译后的字幕运行语音克隆
- [ ] 检查生成的SRT文件格式是否正确
- [ ] 测试错误处理（文件不存在、网络错误等）

---

## 总结

✅ **功能完整**：
- 前端UI：翻译按钮 + 进度显示
- 后端API：批量翻译 + 状态查询
- 翻译脚本：异步并发 + JSON提取

✅ **用户体验**：
- 无需手动翻译字幕
- 实时进度反馈
- 自动保存结果

✅ **技术优势**：
- 异步并发，性能优秀
- 后台任务，不阻塞界面
- 支持多语言，易于扩展

✅ **与现有功能集成**：
- 翻译结果自动用于语音克隆
- 保持原有工作流程
- 无缝替换上传SRT步骤
