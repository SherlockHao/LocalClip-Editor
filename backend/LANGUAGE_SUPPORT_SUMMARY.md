# 多语言支持总览

## 当前支持的语言

| 语言 | 代码 | 中文名 | 长度比例 | 计算方式 | 状态 |
|-----|------|-------|---------|---------|------|
| 英语 | en | 英语 | 1.2倍 | 单词数 | ✅ 支持 |
| 韩语 | ko | 韩语 | 2.5倍 | 字符数 | ✅ 支持 |
| 日语 | ja | 日语 | 2.5倍 | 字符数 | ✅ 支持 |
| 法语 | fr | 法语 | 1.5倍 | 单词数 | ✅ 支持 |

---

## 长度比例说明

### 为什么需要不同的长度比例？

不同语言表达相同意思所需的字符/单词数量差异很大：

```
原文："今天天气真好" (6个中文字)

英语: "Nice weather today" (3词)         → 比例 0.5
法语: "Il fait très beau aujourd'hui" (5词) → 比例 0.83
韩语: "오늘 날씨가 정말 좋네요" (10字)      → 比例 1.67
日语: "きょうはほんとうにいいてんきですね" (17字) → 比例 2.83
```

### 长度比例的作用

系统使用长度比例来检测**异常超长的翻译**，超长的翻译会：
1. 导致语音过快或过慢
2. 字幕显示不完整
3. 影响观看体验

当译文超过限制时，系统会**自动重新翻译**为更简洁的版本。

---

## 快速添加新语言

### 示例：添加德语支持

#### 1. 前端添加选项

编辑 `frontend/src/components/PropertiesPanel.tsx`：

```tsx
<option value="en">英语</option>
<option value="ko">韩语</option>
<option value="ja">日语</option>
<option value="fr">法语</option>
<option value="de">德语</option>  {/* 新增 */}
```

#### 2. 后端添加语言映射

编辑 `backend/main.py` 的 `get_language_name()` 函数：

```python
language_map = {
    'en': '英语',
    'ko': '韩语',
    'ja': '日语',
    'fr': '法语',
    'de': '德语'  # 新增
}
```

#### 3. 添加长度检查逻辑

编辑 `backend/main.py` 的长度检查部分：

```python
is_german = ('德' in target_language or 'de' in target_language_lower or 'german' in target_language_lower)

if is_japanese or is_korean:
    max_ratio = 2.5
elif is_french or is_german:  # 德语和法语类似
    max_ratio = 1.5
else:
    max_ratio = 1.2
```

#### 4. 添加文本长度计算

编辑 `backend/text_utils.py` 的 `count_text_length()` 函数：

```python
elif any(keyword in language_lower for keyword in ['法', 'french', 'français', 'fr']):
    return count_english_length(text)
elif any(keyword in language_lower for keyword in ['德', 'german', 'deutsch', 'de']):
    return count_english_length(text)  # 德语和英语一样，按单词计数
```

#### 5. 创建测试

复制 `test_french_support.py` 为 `test_german_support.py`，修改测试用例。

---

## 语言分类参考

### 按单词计数（拉丁字母系）

这些语言使用空格分隔单词，计算方式相同：

| 语言 | 代码 | 建议比例 | 备注 |
|-----|------|---------|------|
| 英语 | en | 1.2倍 | 表达简洁 |
| 法语 | fr | 1.5倍 | 比英语略长 |
| 德语 | de | 1.5倍 | 复合词较长 |
| 西班牙语 | es | 1.5倍 | 与法语类似 |
| 意大利语 | it | 1.5倍 | 与法语类似 |
| 葡萄牙语 | pt | 1.5倍 | 与法语类似 |

### 按字符计数（音节文字系）

这些语言的字符本身就是完整的音节或单词：

| 语言 | 代码 | 建议比例 | 备注 |
|-----|------|---------|------|
| 日语 | ja | 2.5倍 | 假名字符多 |
| 韩语 | ko | 2.5倍 | 谚文字符多 |

### 特殊语言

| 语言 | 代码 | 建议比例 | 备注 |
|-----|------|---------|------|
| 俄语 | ru | 2.0倍 | 西里尔字母，需要单独处理 |
| 阿拉伯语 | ar | 2.0倍 | 从右到左书写，需特殊处理 |
| 泰语 | th | 2.5倍 | 无空格分隔，需特殊处理 |

---

## 代码架构

### 语言处理流程

```
1. 前端选择语言
   ↓
2. 传递语言代码 (如 'fr')
   ↓
3. get_language_name('fr') → '法语'
   ↓
4. 检查译文长度
   ↓
5. count_text_length(text, '法语') → 单词数
   ↓
6. 比较 ratio vs max_ratio
   ↓
7. 如果超长 → 调用 Ollama 重新翻译
   ↓
8. 生成语音
```

### 关键函数

#### 1. `get_language_name(language_code: str) -> str`
- **位置**：`backend/main.py`
- **功能**：语言代码 → 中文名称
- **示例**：`'fr'` → `'法语'`

#### 2. `count_text_length(text: str, language: str) -> int`
- **位置**：`backend/text_utils.py`
- **功能**：根据语言类型计算文本长度
- **示例**：
  - 英语/法语：`"Hello world"` → `2` (单词数)
  - 日语：`"こんにちは"` → `5` (字符数)

#### 3. `check_translation_length(...)`
- **位置**：`backend/text_utils.py`
- **功能**：检查译文是否超长
- **返回**：`(is_too_long, source_len, target_len, ratio)`

---

## 日语特殊处理

日语除了长度检查外，还有**汉字检测**功能：

```python
# 日语特殊规则：如果译文中包含汉字，需要重新翻译（要求使用假名）
if not needs_retranslation and is_japanese:
    if contains_chinese_characters(target_text):
        needs_retranslation = True
        print(f"[日语检查] 第 {idx} 条译文包含汉字，需要重新翻译: '{target_text}'")
```

**原因**：语音克隆要求使用假名（平假名/片假名），避免汉字混淆。

---

## 重新翻译 Prompt

### 通用语言

```python
prompt = f'请将以下中文翻译成{target_language_name}（极简、字数极少），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
```

### 日语特殊 Prompt

```python
prompt = f'请将以下中文翻译成{target_language_name}（极简、字数极少、使用假名），以 JSON 格式输出，Key 为 "tr"：\n\n{sentence}'
```

**关键**：日语加上了 "使用假名" 的要求。

---

## 测试清单

添加新语言支持后，需要测试以下功能：

- [ ] 前端可以选择新语言
- [ ] 语言代码映射正确
- [ ] 长度计算方式正确
- [ ] 长度比例限制合理
- [ ] 重新翻译正常工作
- [ ] JSON 提取成功
- [ ] 语音生成正常

---

## 常见问题

### Q1: 如何确定合理的长度比例？

**A**: 收集真实翻译样本，计算平均比例：

```python
samples = [
    ("你好", "Bonjour"),          # 2:1 = 0.5
    ("谢谢", "Merci"),            # 2:1 = 0.5
    ("今天天气真好", "Il fait très beau aujourd'hui"),  # 6:5 = 0.83
]

ratios = [target_words / source_chars for source, target in samples]
max_ratio = max(ratios) * 1.2  # 留 20% 余量
```

### Q2: 为什么法语用单词数而不是字符数？

**A**:
- 法语使用拉丁字母，单词之间有空格
- 字符数会包含大量空格和标点，不准确
- 单词数更接近"信息量"的概念
- 与英语保持一致的计算方式

### Q3: 如果超长怎么办？

**A**: 系统会自动：
1. 检测到超长译文
2. 调用 Ollama qwen3:4b 模型
3. 用 prompt 要求"极简、字数极少"
4. 重新翻译为更短的版本
5. 使用新译文生成语音

### Q4: 可以完全禁用长度检查吗？

**A**: 可以，修改 `main.py`：

```python
# 设置一个很大的比例，实际上禁用检查
max_ratio = 10.0  # 或者更大
```

但**不推荐**，因为超长译文会导致语音质量下降。

---

## 未来扩展

### 计划支持的语言

1. **德语** (de) - 1.5倍，单词数
2. **西班牙语** (es) - 1.5倍，单词数
3. **意大利语** (it) - 1.5倍，单词数
4. **葡萄牙语** (pt) - 1.5倍，单词数
5. **俄语** (ru) - 2.0倍，需要特殊处理

### 可能的优化

1. **自适应长度比例**：根据历史数据动态调整
2. **多语言混合**：支持中英混合等场景
3. **方言支持**：粤语、闽南语等
4. **语音质量评分**：集成 NISQA 等评分系统

---

## 相关文档

- [日语和韩语长度比例优化](JAPANESE_KOREAN_LENGTH_RATIO.md)
- [法语支持添加](FRENCH_SUPPORT.md)
- [日语假名 Prompt](JAPANESE_KANA_PROMPT.md)
- [翻译关键词 Bug 修复](FIX_TRANSLATION_KEYWORD_BUG.md)

---

## 总结

✅ **当前支持 4 种语言**：英语、韩语、日语、法语

✅ **完整的多语言架构**：
- 前端语言选择
- 后端语言映射
- 智能长度检查
- 自动重新翻译
- 完善的测试

✅ **易于扩展**：按照本文档的步骤，15 分钟内可添加新语言支持
