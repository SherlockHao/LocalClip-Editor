# 韩语和日语文本处理支持

## 更新日期
2025-12-23

## 问题描述

之前的文本长度验证逻辑只支持中文和英文，对于韩语和日语：
- **问题1**: 韩语/日语文本被当作中文处理
- **问题2**: 使用中文字符正则表达式 `[^\u4e00-\u9fff]` 会将韩语/日语字符全部删除
- **问题3**: 导致韩语/日语文本长度计算为0，无法正确验证译文长度

## 解决方案

### 1. 新增韩语规范化函数

```python
def normalize_korean(text: str) -> str:
    """规范化韩文文本，移除符号和空格"""
    # 韩文字符 Unicode 范围:
    # - 0xAC00-0xD7AF: 谚文音节 (완성형 한글)
    # - 0x1100-0x11FF: 谚文字母 (자모)
    # - 0x3130-0x318F: 谚文兼容字母
    normalized = re.sub(r'[^\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F]', '', text)
    return normalized
```

**效果**:
- 输入: `"안녕 하세요"` (带空格)
- 输出: `"안녕하세요"` (移除空格)
- 长度: 5个韩文字符

### 2. 新增日语规范化函数

```python
def normalize_japanese(text: str) -> str:
    """规范化日文文本，移除符号和空格"""
    # 日文字符 Unicode 范围:
    # - 0x3040-0x309F: 平假名 (ひらがな)
    # - 0x30A0-0x30FF: 片假名 (カタカナ)
    # - 0x4E00-0x9FFF: CJK统一汉字 (日文中使用的汉字)
    # - 0x3400-0x4DBF: CJK扩展A (罕用汉字)
    normalized = re.sub(r'[^\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\u3400-\u4DBF]', '', text)
    return normalized
```

**效果**:
- 输入: `"こんにちは 世界"` (带空格)
- 输出: `"こんにちは世界"` (移除空格)
- 长度: 7个日文字符

### 3. 更新语言检测逻辑

```python
def count_text_length(text: str, language: str) -> int:
    """根据语言类型计算文本长度"""
    language_lower = language.lower()

    # 判断语言类型
    if any(keyword in language_lower for keyword in ['英', 'english', 'en']):
        return count_english_length(text)
    elif any(keyword in language_lower for keyword in ['韩', 'korean', 'ko', '한국']):
        return count_korean_length(text)
    elif any(keyword in language_lower for keyword in ['日', 'japanese', 'ja', '日本']):
        return count_japanese_length(text)
    else:
        # 默认按中文处理
        return count_chinese_length(text)
```

## 支持的语言关键词

### 韩语
- `ko` (语言代码)
- `korean` (英文名)
- `韩文` / `韩` (中文名)
- `한국` (韩语原文)

### 日语
- `ja` (语言代码)
- `japanese` (英文名)
- `日文` / `日` (中文名)
- `日本` (日语原文)

## 测试结果

### 韩语测试
```
原文: '안녕 하세요'
规范化: '안녕하세요'
长度: 5 ✅

原文: '안녕하세요! 반갑습니다.'
规范化: '안녕하세요반갑습니다'
长度: 10 ✅
```

### 日语测试
```
原文: 'こんにちは 世界'
规范化: 'こんにちは世界'
长度: 7 ✅

原文: '私は学生です。'
规范化: '私は学生です'
长度: 6 ✅
```

### 翻译长度检查
```
中文 '你好' (2字) -> 韩语 '안녕하세요' (5字)
比例: 2.50, 超长: True ✅
```

## 影响范围

### 直接影响
- ✅ 韩语/日语文本长度现在能正确计算
- ✅ 可以正确检测韩语/日语译文是否超长
- ✅ 超长译文会触发LLM重新翻译

### 后端API
- `POST /api/voice-clone`: 语音克隆API会正确验证韩语/日语译文长度
- 超长译文会自动调用LLM重新翻译为更简洁的版本

### 前端UI
- 无需修改，前端已有韩语选项 (`<option value="ko">韩语</option>`)
- 日语可以直接添加 (`<option value="ja">日语</option>`)

## 使用示例

```python
from text_utils import count_text_length, check_translation_length

# 韩语长度计算
korean_text = "안녕 하세요"
length = count_text_length(korean_text, "ko")
# 输出: 5

# 日语长度计算
japanese_text = "こんにちは 世界"
length = count_text_length(japanese_text, "ja")
# 输出: 7

# 翻译长度检查
source = "你好"
target = "안녕하세요"
is_too_long, src_len, tgt_len, ratio = check_translation_length(
    source, target, "ko", max_ratio=1.2
)
# is_too_long: True
# src_len: 2
# tgt_len: 5
# ratio: 2.50
```

## 运行测试

```bash
cd backend
python test_korean_japanese.py
```

所有测试应该通过 ✅

## 相关文件

- `backend/text_utils.py` - 核心文本处理函数
- `backend/test_korean_japanese.py` - 韩语日语测试
- `backend/main.py` - API端点（使用这些函数）
- `backend/batch_retranslate.py` - LLM翻译（语言映射已包含韩语）

## 向前兼容性

- ✅ 不影响现有中文和英文处理逻辑
- ✅ 所有原有测试仍然通过
- ✅ 新增功能完全向后兼容
