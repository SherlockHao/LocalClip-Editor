# Bug修复：语言代码映射

## 问题描述

批量重新翻译时，Prompt 使用的是语言代码（如 `"en"`）而不是语言名称（如 `"英文"`）：

```
请将以下中文翻译成en，要求简洁且口语化...  ❌ 不自然
```

这会导致：
- Prompt 不自然，模型可能理解错误
- 翻译质量下降或输出格式异常

## 解决方案

添加语言代码到中文名称的映射表。

### 修改位置

**文件**: `backend/batch_retranslate.py`
**行号**: 70-99

### 实现

```python
# 语言代码到中文名称的映射
language_map = {
    "en": "英文",
    "english": "英文",
    "ja": "日文",
    "japanese": "日文",
    "ko": "韩文",
    "korean": "韩文",
    "fr": "法文",
    "french": "法文",
    "de": "德文",
    "german": "德文",
    "es": "西班牙文",
    "spanish": "西班牙文",
    "ru": "俄文",
    "russian": "俄文",
    "zh": "中文",
    "chinese": "中文",
}

# 转换语言代码为中文名称
target_language_lower = target_language.lower()
language_name = language_map.get(target_language_lower, target_language)

# 使用中文名称构建 prompt
prompt = f"请将以下中文翻译成{language_name}，要求简洁且口语化，直接输出翻译结果，不要解释：\n\n{source_text}"
```

### 效果对比

**修改前**：
```
Target language: en
Prompt: 请将以下中文翻译成en，要求简洁且口语化...  ❌
```

**修改后**：
```
Target language: en -> 英文
Prompt: 请将以下中文翻译成英文，要求简洁且口语化...  ✅
```

## 支持的语言

| 语言代码 | 中文名称 | 示例 |
|---------|---------|------|
| `en`, `english` | 英文 | Hello |
| `ja`, `japanese` | 日文 | こんにちは |
| `ko`, `korean` | 韩文 | 안녕하세요 |
| `fr`, `french` | 法文 | Bonjour |
| `de`, `german` | 德文 | Guten Tag |
| `es`, `spanish` | 西班牙文 | Hola |
| `ru`, `russian` | 俄文 | Привет |
| `zh`, `chinese` | 中文 | 你好 |

**扩展性**：如果映射表中找不到，会使用原始值（fallback）

## 日志输出

现在会打印语言映射：

```
[Task retrans-0] Target language: en -> 英文
[Task retrans-0] Prompt: 请将以下中文翻译成英文，要求简洁且口语化，直接输出翻译结果，不要解释：

你好啊
```

## 相关修改

- 添加了 `language_map` 字典
- 添加了调试日志显示映射结果
- 改进了函数文档字符串

## 测试

重启后端后，触发语音克隆时应该看到：

```
[Task retrans-0] Target language: en -> 英文  ✅
[Task retrans-0] Prompt: 请将以下中文翻译成英文...  ✅
```

而不是：

```
Prompt: 请将以下中文翻译成en...  ❌
```

## 版本历史

- **v1.0** (2025-12-13): 初始版本
  - 添加语言代码映射表
  - 支持8种常见语言
  - 添加调试日志
