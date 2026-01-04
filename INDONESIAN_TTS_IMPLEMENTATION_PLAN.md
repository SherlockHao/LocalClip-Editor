# 印尼语TTS功能实现计划

## 需求分析

### 核心需求
1. 在翻译链路中添加"印尼语"(Indonesian)支持
2. 在语音克隆链路中添加印尼语TTS支持（使用VITS-TTS-ID模型）
3. 印尼语不支持真正的语音克隆，只使用3个预设音色（两男一女）
4. 说话人到印尼语音色的自动映射规则

### 语言分类
- **日语/韩语类**: ja, ko（特殊处理：假名、谚文、不含汉字）
- **英语/法语/德语/西班牙语/印尼语类**: en, fr, de, es, **id**（普通处理）

---

## 架构设计

### 1. 翻译链路改动

#### 1.1 后端改动

**文件**: `backend/main.py`

**改动点1**: 语言映射函数 (第34-52行)
```python
def get_language_name(language_code: str) -> str:
    language_map = {
        'en': '英语',
        'ko': '韩语',
        'ja': '日语',
        'fr': '法语',
        'de': '德语',
        'es': '西班牙语',
        'id': '印尼语'  # ← 新增
    }
    return language_map.get(language_code.lower(), language_code)
```

**改动点2**: 译文长度检查 (第920-928行)
```python
# 印尼语归类到英语/法语/德语/西班牙语类
if is_japanese or is_korean:
    max_ratio = 3
elif is_french or is_german or is_spanish or is_indonesian:  # ← 添加 is_indonesian
    max_ratio = 1.5
else:
    max_ratio = 1.2
```

**改动点3**: 数字替换语言映射 (第1357-1366行, 第2667-2676行)
```python
language_code_map = {
    '英语': 'en',
    '韩语': 'ko',
    '日语': 'ja',
    '法语': 'fr',
    '德语': 'de',
    '西班牙语': 'es',
    '印尼语': 'id'  # ← 新增
}
```

#### 1.2 前端改动

**文件**: `frontend/src/components/PropertiesPanel.tsx`

**改动点**: 语言选项 (第254-261行)
```tsx
<option value="">请选择目标语言</option>
<option value="en">英语</option>
<option value="ko">韩语</option>
<option value="ja">日语</option>
<option value="fr">法语</option>
<option value="de">德语</option>
<option value="es">西班牙语</option>
<option value="id">印尼语</option>  {/* ← 新增 */}
```

---

### 2. 语音克隆链路改动

#### 2.1 印尼语默认音色库配置

**文件**: `backend/main.py`

**位置**: 在 DEFAULT_VOICES 后添加 INDONESIAN_VOICES (约第262行)

```python
# 印尼语默认音色库（VITS-TTS-ID）
INDONESIAN_VOICES = [
    {
        "id": "indonesian_male_1",
        "name": "印尼男声1 (Ardi)",
        "speaker_name": "ardi",
        "gender": "male",
        "reference_text": "Halo, selamat datang di dunia sintesis suara Indonesia."
    },
    {
        "id": "indonesian_male_2",
        "name": "印尼男声2 (Wibowo)",
        "speaker_name": "wibowo",
        "gender": "male",
        "reference_text": "Teknologi text-to-speech sangat berguna untuk aksesibilitas."
    },
    {
        "id": "indonesian_female_1",
        "name": "印尼女声 (Gadis)",
        "speaker_name": "gadis",
        "gender": "female",
        "reference_text": "Suara ini dihasilkan menggunakan model VITS yang canggih."
    }
]
```

#### 2.2 API改动：获取印尼语音色库

**文件**: `backend/main.py`

**新增端点**: `GET /voice-cloning/indonesian-voices`

```python
@app.get("/voice-cloning/indonesian-voices")
async def get_indonesian_voices():
    """
    获取印尼语默认音色库
    """
    return {"voices": INDONESIAN_VOICES}
```

**位置**: 约第1650行之后

#### 2.3 说话人到印尼语音色的自动映射

**映射规则**:
```
说话人性别 → 印尼语音色映射
------------------------
女1 → gadis
女2 → gadis
女3 → gadis
...

男1 → ardi
男2 → wibowo
男3 → ardi (循环)
男4 → wibowo (循环)
...
```

**实现函数** (新增到 `backend/main.py`):

```python
def map_speakers_to_indonesian_voices(
    speaker_references: Dict[int, Dict],
    speaker_diarization_result: Dict
) -> Dict[int, str]:
    """
    将说话人映射到印尼语音色

    Args:
        speaker_references: 说话人参考信息
        speaker_diarization_result: 说话人识别结果（包含性别信息）

    Returns:
        {speaker_id: indonesian_speaker_name}
        例如: {0: "ardi", 1: "gadis", 2: "wibowo"}
    """
    speaker_to_indonesian = {}

    # 获取性别信息
    gender_dict = speaker_diarization_result.get("gender_dict", {})

    # 分别统计男声和女声
    male_speakers = []
    female_speakers = []

    for speaker_id in sorted(speaker_references.keys()):
        gender = gender_dict.get(str(speaker_id), "unknown")
        if gender == "female":
            female_speakers.append(speaker_id)
        else:
            male_speakers.append(speaker_id)

    # 映射女声 -> gadis (所有女声使用同一音色)
    for speaker_id in female_speakers:
        speaker_to_indonesian[speaker_id] = "gadis"

    # 映射男声 -> ardi, wibowo (交替)
    indonesian_male_voices = ["ardi", "wibowo"]
    for i, speaker_id in enumerate(male_speakers):
        voice_index = i % len(indonesian_male_voices)
        speaker_to_indonesian[speaker_id] = indonesian_male_voices[voice_index]

    return speaker_to_indonesian
```

**位置**: 约第264行之后

#### 2.4 印尼语TTS批量生成脚本

**文件**: `backend/indonesian_batch_tts.py` (新建)

**功能**: 批量生成印尼语语音（基于 tts-id/batch_tts.py）

**输入配置格式**:
```json
{
  "model_dir": "c:/workspace/ai_editing/model/vits-tts-id",
  "tasks": [
    {
      "segment_index": 0,
      "speaker_name": "ardi",
      "target_text": "Selamat pagi, bagaimana kabar Anda?",
      "output_file": "exports/cloned_xxx/segment_0.wav"
    },
    {
      "segment_index": 1,
      "speaker_name": "gadis",
      "target_text": "Halo, apa kabar?",
      "output_file": "exports/cloned_xxx/segment_1.wav"
    }
  ]
}
```

**输出格式**:
```json
[
  {
    "segment_index": 0,
    "status": "success",
    "output_file": "exports/cloned_xxx/segment_0.wav",
    "inference_time": 0.045
  },
  {
    "segment_index": 1,
    "status": "success",
    "output_file": "exports/cloned_xxx/segment_1.wav",
    "inference_time": 0.042
  }
]
```

**关键代码**:
```python
def main():
    # 1. 读取配置
    config = json.load(sys.stdin) if len(sys.argv) < 2 else json.load(open(sys.argv[1]))

    model_dir = config["model_dir"]
    tasks = config["tasks"]

    # 2. 加载模型（仅一次）
    synthesizer = load_model(model_dir)

    # 3. 按说话人分组
    tasks_by_speaker = defaultdict(list)
    for task in tasks:
        speaker_name = task["speaker_name"]
        tasks_by_speaker[speaker_name].append(task)

    # 4. 逐说话人生成
    results = []
    for speaker_name, speaker_tasks in tasks_by_speaker.items():
        for task in speaker_tasks:
            # 生成语音
            wav = synthesizer.tts(text=task["target_text"], speaker_name=speaker_name)
            synthesizer.save_wav(wav, task["output_file"])

            results.append({
                "segment_index": task["segment_index"],
                "status": "success",
                "output_file": task["output_file"],
                "inference_time": inference_time
            })

    # 5. 输出结果
    print(json.dumps(results, ensure_ascii=False))
```

#### 2.5 印尼语TTS调用器

**文件**: `backend/indonesian_tts_cloner.py` (新建)

**功能**: 封装印尼语TTS调用逻辑（类似 SimpleFishCloner）

**类定义**:
```python
class IndonesianTTSCloner:
    def __init__(self, model_dir: str, tts_id_env_python: str):
        """
        Args:
            model_dir: VITS-TTS-ID 模型路径
            tts_id_env_python: tts-id-py311 环境的 Python 路径
        """
        self.model_dir = model_dir
        self.tts_id_env_python = tts_id_env_python

    def batch_generate_audio(
        self,
        tasks: List[Dict],
        config_file: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[int, str]:
        """
        批量生成印尼语语音

        Args:
            tasks: 任务列表
            config_file: 配置文件路径
            progress_callback: 进度回调函数

        Returns:
            {segment_index: audio_file_path}
        """
        # 1. 写入配置文件
        config = {
            "model_dir": self.model_dir,
            "tasks": tasks
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        # 2. 调用批量生成脚本
        script_path = os.path.join(os.path.dirname(__file__), "indonesian_batch_tts.py")

        process = subprocess.Popen(
            [self.tts_id_env_python, script_path, config_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )

        # 3. 实时解析进度
        output_lines = []
        for line in process.stdout:
            output_lines.append(line)

            # 解析进度: [BatchGen] 进度: 5/15
            match = re.search(r'\[BatchGen\]\s+进度:\s+(\d+)/(\d+)', line)
            if match and progress_callback:
                current = int(match.group(1))
                total = int(match.group(2))
                progress_callback(current, total)

        # 4. 解析结果
        process.wait()

        # 找到 JSON 结果
        json_start = -1
        for i, line in enumerate(output_lines):
            if line.strip().startswith('['):
                json_start = i
                break

        if json_start >= 0:
            json_output = '\n'.join(output_lines[json_start:])
            results = json.loads(json_output)

            # 转换为字典
            segment_files = {}
            for result in results:
                if result["status"] == "success":
                    segment_files[result["segment_index"]] = result["output_file"]

            return segment_files
        else:
            raise Exception("Failed to parse Indonesian TTS output")
```

#### 2.6 语音克隆主流程改动

**文件**: `backend/main.py`

**改动点**: `run_voice_cloning_process()` 函数 (第653-1622行)

**新增逻辑**:

```python
async def run_voice_cloning_process(...):
    # ... 前面的步骤保持不变 ...

    # 步骤 8.5: 检测是否为印尼语
    is_indonesian = ('印尼' in target_language or
                     'indonesian' in target_language.lower() or
                     'id' in target_language.lower())

    if is_indonesian:
        # ========== 印尼语 TTS 分支 ==========
        print("\n[印尼语TTS] 检测到印尼语，使用 VITS-TTS-ID 模型...")

        # 1. 说话人到印尼语音色的映射
        speaker_to_indonesian = map_speakers_to_indonesian_voices(
            speaker_references,
            speaker_diarization_result
        )

        print(f"[印尼语TTS] 说话人音色映射:")
        for speaker_id, indo_voice in speaker_to_indonesian.items():
            speaker_name = speaker_diarization_result.get("speaker_name_mapping", {}).get(str(speaker_id), f"说话人{speaker_id}")
            print(f"  {speaker_name} -> {indo_voice}")

        # 2. 准备批量生成任务
        indonesian_tasks = []
        for idx, (source_sub, target_sub) in enumerate(zip(source_subtitles, target_subtitles)):
            speaker_id = source_sub.get("speaker_id", 0)
            indonesian_speaker = speaker_to_indonesian.get(speaker_id, "ardi")
            target_text = target_sub["text"]

            output_file = os.path.join(cloned_audio_dir, f"segment_{idx}.wav")

            indonesian_tasks.append({
                "segment_index": idx,
                "speaker_name": indonesian_speaker,
                "target_text": target_text,
                "output_file": output_file
            })

        # 3. 调用印尼语 TTS 批量生成
        from indonesian_tts_cloner import IndonesianTTSCloner

        tts_id_env_python = os.environ.get("TTS_ID_PYTHON")
        if not tts_id_env_python:
            tts_id_env_python = "C:/Users/7/miniconda3/envs/tts-id-py311/python.exe"

        model_dir = os.path.join(os.path.dirname(__file__), "..", "model", "vits-tts-id")

        cloner = IndonesianTTSCloner(model_dir, tts_id_env_python)

        # 进度回调
        def update_progress(current, total):
            progress = 20 + int((current / total) * 70)  # 20-90%
            voice_cloning_status[task_id] = {
                "status": "processing",
                "message": f"正在生成印尼语语音 ({current}/{total})...",
                "progress": progress
            }

        config_file = os.path.join(cloned_audio_dir, "indonesian_tts_config.json")

        segment_files = cloner.batch_generate_audio(
            indonesian_tasks,
            config_file,
            progress_callback=update_progress
        )

        print(f"\n[印尼语TTS] ✓ 成功生成 {len(segment_files)} 个音频片段")

        # 跳转到音频拼接步骤（步骤10）
        # ... (后续步骤与 Fish-Speech 相同) ...

    else:
        # ========== Fish-Speech 分支 ==========
        # ... (原有的 Fish-Speech 逻辑) ...
```

**位置**: 约第1050行之后（在"步骤8"和"步骤9"之间插入）

---

### 3. 前端改动

#### 3.1 印尼语检测和UI调整

**文件**: `frontend/src/App.tsx`

**改动点1**: 检测印尼语状态

```typescript
// 在状态定义部分添加
const [isIndonesian, setIsIndonesian] = useState<boolean>(false);

// 在 handleTargetLanguageChange 中更新
const handleTargetLanguageChange = (language: string) => {
  setTargetLanguage(language);
  setIsIndonesian(language === 'id');
};
```

**改动点2**: 说话人音色选择（条件渲染）

```typescript
// 如果是印尼语，不显示音色选择下拉菜单
{!isIndonesian && (
  <VoiceSelector
    speakers={speakers}
    speakerVoiceMapping={speakerVoiceMapping}
    onVoiceMappingChange={handleVoiceMappingChange}
    defaultVoices={defaultVoices}
  />
)}

// 如果是印尼语，显示自动映射提示
{isIndonesian && (
  <div className="indonesian-voice-notice">
    <p>印尼语将自动分配音色：</p>
    <ul>
      <li>女声 → 印尼女声 (Gadis)</li>
      <li>男声 → 印尼男声1/男声2 (Ardi/Wibowo)</li>
    </ul>
  </div>
)}
```

---

## TODO清单

### Phase 1: 翻译链路改动 ✅

- [ ] 1.1 后端语言映射添加印尼语
  - [ ] `backend/main.py`: `get_language_name()` 添加 `'id': '印尼语'`
  - [ ] `backend/main.py`: 译文长度检查添加 `is_indonesian` 判断
  - [ ] `backend/main.py`: 数字替换语言映射添加印尼语

- [ ] 1.2 前端语言选项添加印尼语
  - [ ] `frontend/src/components/PropertiesPanel.tsx`: 添加 `<option value="id">印尼语</option>`

- [ ] 1.3 测试翻译功能
  - [ ] 创建测试脚本：测试中文→印尼语翻译
  - [ ] 验证译文长度检查逻辑（1.5倍限制）
  - [ ] 验证数字替换功能

### Phase 2: 印尼语音色库和映射 ✅

- [ ] 2.1 添加印尼语音色库配置
  - [ ] `backend/main.py`: 定义 `INDONESIAN_VOICES`
  - [ ] `backend/main.py`: 新增 API `/voice-cloning/indonesian-voices`

- [ ] 2.2 实现说话人到印尼语音色的映射
  - [ ] `backend/main.py`: 实现 `map_speakers_to_indonesian_voices()`

- [ ] 2.3 测试映射逻辑
  - [ ] 创建测试脚本：测试不同性别组合的映射结果
  - [ ] 验证女声全部映射到 gadis
  - [ ] 验证男声交替映射到 ardi/wibowo

### Phase 3: 印尼语TTS批量生成 ✅

- [ ] 3.1 创建批量生成脚本
  - [ ] 新建 `backend/indonesian_batch_tts.py`
  - [ ] 实现模型加载（仅一次）
  - [ ] 实现按说话人分组生成
  - [ ] 实现进度输出和JSON结果输出

- [ ] 3.2 创建TTS调用器
  - [ ] 新建 `backend/indonesian_tts_cloner.py`
  - [ ] 实现 `IndonesianTTSCloner` 类
  - [ ] 实现 `batch_generate_audio()` 方法
  - [ ] 实现进度解析和回调

- [ ] 3.3 测试批量生成
  - [ ] 创建测试脚本：生成5-10个音频片段
  - [ ] 验证模型只加载一次
  - [ ] 验证不同说话人的音频质量
  - [ ] 验证进度输出格式

### Phase 4: 语音克隆主流程集成 ✅

- [ ] 4.1 集成印尼语分支
  - [ ] `backend/main.py`: 在 `run_voice_cloning_process()` 中添加印尼语检测
  - [ ] 实现说话人音色映射调用
  - [ ] 实现批量生成任务准备
  - [ ] 实现 `IndonesianTTSCloner` 调用
  - [ ] 复用音频拼接步骤

- [ ] 4.2 环境变量配置
  - [ ] 添加 `TTS_ID_PYTHON` 环境变量支持
  - [ ] 添加 `VITS_TTS_ID_MODEL_DIR` 环境变量支持

### Phase 5: 前端UI调整 ✅

- [ ] 5.1 印尼语状态检测
  - [ ] `frontend/src/App.tsx`: 添加 `isIndonesian` 状态
  - [ ] 在语言选择时更新状态

- [ ] 5.2 条件渲染音色选择
  - [ ] 印尼语时隐藏音色选择下拉菜单
  - [ ] 显示自动映射说明

### Phase 6: 端到端测试 ✅

- [ ] 6.1 完整流程测试
  - [ ] 上传视频
  - [ ] 识别说话人（多男多女场景）
  - [ ] 翻译到印尼语
  - [ ] 执行语音克隆
  - [ ] 验证最终音频

- [ ] 6.2 边界条件测试
  - [ ] 只有男声场景
  - [ ] 只有女声场景
  - [ ] 超过2个男声场景（测试循环映射）

- [ ] 6.3 性能测试
  - [ ] 测试100+条字幕的批量生成性能
  - [ ] 对比Fish-Speech和印尼语TTS的速度

---

## 文件清单

### 新建文件
1. `backend/indonesian_batch_tts.py` - 印尼语批量TTS脚本
2. `backend/indonesian_tts_cloner.py` - 印尼语TTS调用器
3. `backend/test_indonesian_tts.py` - 印尼语TTS测试脚本
4. `backend/test_indonesian_mapping.py` - 说话人映射测试脚本

### 修改文件
1. `backend/main.py`
   - 添加印尼语语言映射
   - 添加 `INDONESIAN_VOICES` 配置
   - 添加 `/voice-cloning/indonesian-voices` API
   - 添加 `map_speakers_to_indonesian_voices()` 函数
   - 修改 `run_voice_cloning_process()` 函数（添加印尼语分支）

2. `frontend/src/components/PropertiesPanel.tsx`
   - 添加印尼语选项

3. `frontend/src/App.tsx`
   - 添加 `isIndonesian` 状态
   - 条件渲染音色选择

---

## 技术要点

### 1. 模型路径配置
```python
# 默认模型路径
DEFAULT_MODEL_DIR = "c:/workspace/ai_editing/model/vits-tts-id"

# 环境变量支持
model_dir = os.environ.get("VITS_TTS_ID_MODEL_DIR", DEFAULT_MODEL_DIR)
```

### 2. Python环境路径
```python
# 默认tts-id环境路径
DEFAULT_TTS_ID_PYTHON = "C:/Users/7/miniconda3/envs/tts-id-py311/python.exe"

# 环境变量支持
tts_id_python = os.environ.get("TTS_ID_PYTHON", DEFAULT_TTS_ID_PYTHON)
```

### 3. 进度计算
```
总进度范围: 0-100%
- 0-5%: 提取音频
- 5-10%: 识别说话人
- 10-15%: MOS评分
- 15-20%: 准备任务
- 20-90%: 批量生成语音 (70%区间)
- 90-95%: 拼接音频
- 95-100%: 完成
```

### 4. 错误处理
- 模型加载失败 → 返回详细错误信息
- 生成失败 → 记录失败的片段索引，继续其他片段
- 环境路径不存在 → 使用默认路径并警告

---

## 预期效果

### 翻译示例
```
原文（中文）: "你好，欢迎来到这里。"
译文（印尼语）: "Halo, selamat datang di sini."
```

### 音色映射示例
```
场景1: 2男1女
- 男1 → ardi
- 男2 → wibowo
- 女1 → gadis

场景2: 3男2女
- 男1 → ardi
- 男2 → wibowo
- 男3 → ardi (循环)
- 女1 → gadis
- 女2 → gadis

场景3: 1男1女
- 男1 → ardi
- 女1 → gadis
```

### 性能预期
```
参考 tts-id/batch_tts.py 的性能:
- 15条文本
- 总推理耗时: 1.33秒
- 平均推理速度: 0.089秒/个
- GPU: RTX 5070

预期 100 条字幕:
- 总推理耗时: ~6秒
- 加上模型加载: ~13秒
- 总体速度优于 Fish-Speech
```

---

## 开发顺序建议

1. **Phase 1 (30分钟)**: 翻译链路 - 最简单，风险最低
2. **Phase 2 (30分钟)**: 音色库和映射 - 独立功能，易于测试
3. **Phase 3 (1小时)**: TTS批量生成 - 核心模块，需仔细测试
4. **Phase 4 (1小时)**: 主流程集成 - 复杂度最高
5. **Phase 5 (30分钟)**: 前端UI - 简单改动
6. **Phase 6 (1小时)**: 端到端测试 - 全面验证

**总估时**: 4.5小时
