# 日语支持完整说明

## 概述

本系统已完整支持日语翻译和语音克隆功能，与英语、韩语平行实现。

---

## 一、前端支持

### 1. 语言选择（PropertiesPanel.tsx）

位置：[PropertiesPanel.tsx:254-258](../frontend/src/components/PropertiesPanel.tsx#L254-L258)

```tsx
<select value={targetLanguage} onChange={(e) => onTargetLanguageChange(e.target.value)}>
  <option value="">请选择目标语言</option>
  <option value="en">英语</option>
  <option value="ko">韩语</option>
  <option value="ja">日语</option>  ✅ 已支持
</select>
```

### 2. 单条翻译调用（SubtitleDetails.tsx）

位置：[SubtitleDetails.tsx:351-358](../frontend/src/components/SubtitleDetails.tsx#L351-L358)

当用户修改原文后重新生成语音时，会自动调用翻译 API：

```tsx
const response = await fetch('/api/translate-text', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: subtitle.text,
    target_language: targetLanguage  // "ja"
  })
});
```

---

## 二、后端支持

### 1. 语言代码映射（main.py）

位置：[main.py:32-48](main.py#L32-L48)

新增 `get_language_name()` 函数，将前端传递的语言代码转换为 LLM prompt 使用的中文名称：

```python
def get_language_name(language_code: str) -> str:
    """
    将语言代码转换为中文名称（用于LLM prompt）

    Args:
        language_code: 语言代码 (en, ko, ja 等)

    Returns:
        str: 语言的中文名称
    """
    language_map = {
        'en': '英语',
        'ko': '韩语',
        'ja': '日语'  ✅ 日语映射
    }
    return language_map.get(language_code.lower(), language_code)
```

**映射示例**：
- `"ja"` → `"日语"`
- `"JA"` → `"日语"`
- `"Japanese"` → `"Japanese"` (未映射，返回原值)

### 2. 批量重新翻译（main.py）

位置：[main.py:938-947](main.py#L938-L947)

在语音克隆过程中，如果检测到超长译文，会批量调用 Ollama 重新翻译：

```python
# 将语言代码转换为中文名称（用于LLM prompt）
target_language_name = get_language_name(target_language)  # "ja" -> "日语"

retranslate_tasks = []
for item in too_long_items:
    retranslate_tasks.append({
        "task_id": f"retrans-{item['index']}",
        "source": item["source"],
        "target_language": target_language_name  ✅ 传递 "日语"
    })
```

### 3. 单条翻译 API（main.py）

位置：[main.py:1624-1648](main.py#L1624-L1648)

处理前端单条翻译请求：

```python
@app.post("/translate-text")
async def translate_text(request: TranslateTextRequest):
    """使用LLM翻译文本"""
    # 将语言代码转换为中文名称（用于LLM prompt）
    target_language_name = get_language_name(request.target_language)  ✅ "ja" -> "日语"
    print(f"[翻译API] 语言代码: {request.target_language} -> {target_language_name}")

    # 创建临时配置文件（使用 Ollama）
    config_data = {
        "tasks": [{
            "task_id": "translate-1",
            "source": request.text,
            "target_language": target_language_name  ✅ 传递 "日语"
        }],
        "model": "qwen3:4b"
    }
```

**重要改进**：
- ✅ 已从旧的 HuggingFace 方案迁移到 Ollama
- ✅ 使用 `ui` conda 环境
- ✅ 调用 `batch_retranslate_ollama.py`

---

## 三、翻译引擎支持（batch_retranslate_ollama.py）

### Ollama 翻译 Prompt（日语特殊处理）

位置：[batch_retranslate_ollama.py:152-157](batch_retranslate_ollama.py#L152-L157)

**日语特殊 Prompt**：

```python
# 针对日语添加特殊要求：使用假名
if '日' in target_language or 'ja' in target_language.lower():
    prompt = f'请将以下中文翻译成{target_language}（口语化、极简、使用假名），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
else:
    prompt = f'请将以下中文翻译成{target_language}（口语化、极简），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
```

**日语翻译示例**：
- `target_language = "日语"`
- 生成的 prompt: `"请将以下中文翻译成日语（口语化、极简、使用假名），以 JSON 格式输出，Key 为 "tr"：\n\n你好"`
- 模型输出: `{"tr": "こんにちは"}`（优先使用假名而非汉字）

**其他语言翻译示例**：
- `target_language = "英语"`
- 生成的 prompt: `"请将以下中文翻译成英语（口语化、极简），以 JSON 格式输出，Key 为 "tr"：\n\n你好"`
- 模型输出: `{"tr": "Hello"}`

**为什么日语需要"使用假名"？**

1. **语音合成友好**：假名（平假名/片假名）的发音更加确定，TTS 系统更容易准确发音
2. **口语化要求**：日常对话中，假名的使用频率高于汉字，更符合"口语化"要求
3. **减少歧义**：同一个汉字在日语中可能有多种读音（音读/训读），使用假名避免发音歧义

**对比示例**：

| 中文 | 使用汉字 | 使用假名（推荐） | 说明 |
|-----|---------|----------------|------|
| 今天 | 今日 | きょう | "今日"可读作"きょう"或"こんにち"，假名更明确 |
| 吃饭 | 食事 | ごはん | 口语中更常用"ごはん" |
| 漂亮 | 綺麗 | きれい | 假名更口语化 |

---

## 四、文本处理支持（text_utils.py）

### 1. 日语文本规范化

位置：[text_utils.py:73-89](text_utils.py#L73-L89)

```python
def normalize_japanese(text: str) -> str:
    """
    规范化日文文本，移除符号和空格

    日文字符 Unicode 范围:
    - 0x3040-0x309F: 平假名 (ひらがな)
    - 0x30A0-0x30FF: 片假名 (カタカナ)
    - 0x4E00-0x9FFF: CJK统一汉字 (日文中使用的汉字)
    - 0x3400-0x4DBF: CJK扩展A (罕用汉字)
    """
    normalized = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF]', '', text)
    return normalized
```

**测试案例**：
| 输入 | 输出 | 说明 |
|-----|------|------|
| `"こんにちは！"` | `"こんにちは"` | 移除标点 |
| `"カタカナ"` | `"カタカナ"` | 片假名保留 |
| `"日本語"` | `"日本語"` | 汉字保留 |
| `"Hello こんにちは 123"` | `"こんにちは"` | 只保留日文 |

### 2. 日语长度计算

位置：[text_utils.py:136-147](text_utils.py#L136-L147)

```python
def count_japanese_length(text: str) -> int:
    """计算日文文本的长度（统计字符数）"""
    normalized = normalize_japanese(text)
    return len(normalized)
```

**示例**：
- `"こんにちは"` → 5 个字符
- `"今日は良い天気ですね"` → 10 个字符

### 3. 多语言长度检测

位置：[text_utils.py:150-172](text_utils.py#L150-L172)

```python
def count_text_length(text: str, language: str) -> int:
    """根据语言类型计算文本长度"""
    language_lower = language.lower()

    if any(keyword in language_lower for keyword in ['英', 'english', 'en']):
        return count_english_length(text)
    elif any(keyword in language_lower for keyword in ['韩', 'korean', 'ko', '한국']):
        return count_korean_length(text)
    elif any(keyword in language_lower for keyword in ['日', 'japanese', 'ja', '日本']):  ✅ 日语检测
        return count_japanese_length(text)
    else:
        return count_chinese_length(text)
```

**支持的日语关键词**：
- `"日"`, `"日语"`, `"日文"`
- `"ja"`, `"JA"`
- `"japanese"`, `"Japanese"`, `"JAPANESE"`
- `"日本"`, `"日本語"`

### 4. 译文长度验证

位置：[text_utils.py:175-208](text_utils.py#L175-L208)

在语音克隆时，系统会自动检查日语译文长度是否超过中文原文的 1.2 倍：

```python
is_too_long, source_len, target_len, ratio = check_translation_length(
    source_text="你好世界",
    target_text="こんにちは世界",
    target_language="日语",
    max_ratio=1.2
)
# source_len=4, target_len=7, ratio=1.75
# is_too_long=True (超过1.2倍，会触发重新翻译)
```

---

## 五、完整工作流程

### 场景1：语音克隆流程

```
1. 用户在前端选择目标语言: "ja"
   ↓
2. 上传日语字幕 SRT 文件
   ↓
3. 点击"开始克隆"
   ↓
4. 后端接收 target_language="ja"
   ↓
5. 使用 text_utils.count_text_length() 验证每句日语译文长度
   ↓
6. 如果检测到超长译文:
   - 调用 get_language_name("ja") → "日语"
   - 生成重新翻译任务配置
   - 调用 batch_retranslate_ollama.py
   - Prompt: "请将以下中文翻译成日语（口语化、极简）..."
   ↓
7. 获得优化后的日语译文
   ↓
8. 使用日语译文进行语音克隆
```

### 场景2：单条重新生成流程

```
1. 用户在字幕详情中修改某条原文
   ↓
2. 点击"重新生成"按钮
   ↓
3. 前端检测到原文变化，调用 /api/translate-text
   - 参数: { text: "修改后的原文", target_language: "ja" }
   ↓
4. 后端 translate_text API:
   - 调用 get_language_name("ja") → "日语"
   - 创建临时配置，调用 batch_retranslate_ollama.py
   - Prompt: "请将以下中文翻译成日语..."
   ↓
5. 返回新的日语译文给前端
   ↓
6. 前端使用新译文调用语音生成 API
```

---

## 六、测试验证

### 快速测试

```bash
cd backend
set PYTHONIOENCODING=utf-8
python -c "from text_utils import count_japanese_length; print('Test Japanese:', count_japanese_length('こんにちは'))"
# 输出: Test Japanese: 5
```

### 语言代码映射测试

```bash
python -c "from main import get_language_name; print(get_language_name('ja'))"
# 输出: 日语
```

### 完整测试套件

```bash
python test_japanese_support.py
```

---

## 七、与英语、韩语的对比

| 特性 | 英语 (en) | 韩语 (ko) | 日语 (ja) |
|-----|----------|----------|----------|
| **前端选项** | ✅ | ✅ | ✅ |
| **语言代码映射** | en → 英语 | ko → 韩语 | ja → 日语 |
| **文本规范化** | 移除符号，保留字母 | 移除符号，保留谚文 | 移除符号，保留平假名/片假名/汉字 |
| **长度计算** | 单词数 | 字符数 | 字符数 |
| **LLM Prompt** | "翻译成英语" | "翻译成韩语" | "翻译成日语" |
| **Ollama 模型** | qwen3:4b | qwen3:4b | qwen3:4b |
| **Unicode 范围** | a-z, A-Z | 0xAC00-0xD7AF | 0x3040-0x30FF |

---

## 八、关键文件清单

| 文件 | 修改内容 | 状态 |
|-----|---------|------|
| `frontend/src/components/PropertiesPanel.tsx` | 已有日语选项 | ✅ 无需修改 |
| `frontend/src/components/SubtitleDetails.tsx` | 单条翻译调用 | ✅ 无需修改 |
| `backend/main.py` | 新增 `get_language_name()` 函数 | ✅ 已修改 |
| `backend/main.py` | 批量重新翻译应用映射 | ✅ 已修改 |
| `backend/main.py` | `/translate-text` API 迁移到 Ollama | ✅ 已修改 |
| `backend/text_utils.py` | 日语处理函数 | ✅ 已有支持 |
| `backend/batch_retranslate_ollama.py` | Ollama 翻译引擎 | ✅ 已有支持 |

---

## 九、总结

✅ **日语支持已完整实现**，与英语、韩语功能完全平行：

1. **前端** - 用户可以选择"日语"作为目标语言
2. **语言映射** - 自动将 `"ja"` 转换为 `"日语"` 用于 LLM prompt
3. **文本处理** - 正确处理平假名、片假名、日文汉字
4. **长度验证** - 按字符数统计日语长度
5. **批量翻译** - 超长译文自动重新翻译
6. **单条翻译** - 修改原文后自动调用翻译 API
7. **Ollama 集成** - 使用 qwen3:4b 模型进行日语翻译

**无需额外配置或修改，日语功能即可使用！**
