# 字幕数量不匹配问题 - 调试信息说明

## 问题描述
翻译完成后，语音克隆报错：
```
字幕文件行数不匹配: 原文 563 条 vs 译文 561 条
```

## 添加的调试日志位置

### 1. 说话人识别阶段 (processing.py)

#### 音频提取后 (第479行)
```python
print(f"[DEBUG-切分] audio_paths 长度: {len(audio_paths)}")
```
**作用**: 查看音频提取后有多少个音频文件（可能因切分而 > 原始字幕数）

#### 聚类后 (第534行)
```python
print(f"[DEBUG-聚类] speaker_labels 长度: {len(speaker_labels)}")
```
**作用**: 查看说话人标签数组的长度（应该等于 audio_paths 长度）

#### 解析字幕后 (第591-592行)
```python
print(f"[DEBUG-字幕] 原始字幕 subtitles 长度: {len(subtitles)}")
print(f"[DEBUG-字幕] audio_paths 长度: {len(audio_paths)}")
```
**作用**: 对比原始字幕和音频文件数量

#### zip 操作警告 (第594-598行)
```python
if len(audio_paths) != len(subtitles):
    print(f"[DEBUG-警告] ⚠️  audio_paths 和 subtitles 长度不一致!")
    print(f"  zip() 将截断到较短的长度: {min(len(audio_paths), len(subtitles))}")
```
**作用**: 检测 zip 是否会截断数据（zip 以较短的为准）

#### 构建 audio_segments 后 (第607行)
```python
print(f"[DEBUG-构建] audio_segments 长度: {len(audio_segments)}")
```
**作用**: 查看实际构建的 segments 数量

#### 保存前检查 (第629-637行)
```python
print(f"[DEBUG-保存] 准备保存 speaker_data.json:")
print(f"  - segments 长度: {len(audio_segments)}")
print(f"  - speaker_labels 长度: {len(speaker_labels)}")
print(f"  - 原始字幕 subtitles 长度: {len(subtitles)}")
if len(audio_segments) != len(speaker_labels):
    print(f"[DEBUG-警告] ❌ 数据长度不一致!")
```
**作用**: 保存到 speaker_data.json 之前的最终一致性检查

### 2. 语音克隆阶段 (voice_cloning_service.py)

#### 读取数据后 (第186-189行)
```python
print(f"[DEBUG-克隆] speaker_labels 长度: {len(speaker_labels)}")
print(f"[DEBUG-克隆] target_subtitles 长度: {len(target_subtitles)}")
print(f"[DEBUG-克隆] source_subtitles 长度: {len(source_subtitles)}")
print(f"[DEBUG-克隆] segments 长度: {len(segments)}")
```
**作用**: 查看语音克隆时读取到的所有数据长度

## 如何使用这些调试信息

### 运行测试后，检查日志中的关键数据：

1. **音频切分是否导致数量增加？**
   ```
   [DEBUG-切分] audio_paths 长度: ???
   [DEBUG-字幕] 原始字幕 subtitles 长度: 563
   ```
   如果 audio_paths > 563，说明切分逻辑导致了音频文件增加

2. **zip 是否截断了数据？**
   ```
   [DEBUG-警告] ⚠️  audio_paths 和 subtitles 长度不一致!
   ```
   如果出现此警告，说明 zip 会截断数据

3. **最终保存的数据是否一致？**
   ```
   [DEBUG-保存] segments 长度: ???
   [DEBUG-保存] speaker_labels 长度: ???
   ```
   两者应该相等

4. **翻译是否导致字幕减少？**
   ```
   [DEBUG-克隆] speaker_labels 长度: 563 (或其他)
   [DEBUG-克隆] target_subtitles 长度: 561
   [DEBUG-克隆] source_subtitles 长度: 563
   ```
   对比三者的数量

## 问题分析流程图

```
原始SRT (563条)
  ↓
extract_audio_segments() [DEBUG-切分]
  ↓
audio_paths (可能 > 563) [DEBUG-字幕]
  ↓
cluster_embeddings() [DEBUG-聚类]
  ↓
speaker_labels (长度 = audio_paths) [DEBUG-保存]
  ↓
zip(audio_paths, subtitles) [DEBUG-警告: 可能截断!]
  ↓
audio_segments (长度 = min(audio_paths, subtitles))
  ↓
保存到 speaker_data.json
  ↓
翻译服务 (生成 561 条译文)
  ↓
语音克隆读取 [DEBUG-克隆]
  ↓
比较: speaker_labels vs target_subtitles
  ↓
❌ 不匹配报错
```

## 预期结果

### 情况 A: 切分导致问题
```
[DEBUG-切分] audio_paths 长度: 565
[DEBUG-字幕] 原始字幕 subtitles 长度: 563
[DEBUG-警告] ⚠️  audio_paths 和 subtitles 长度不一致!
[DEBUG-构建] audio_segments 长度: 563  # zip 截断到 563
[DEBUG-保存] speaker_labels 长度: 565  # 但 speaker_labels 还是 565!
[DEBUG-保存] ❌ 数据长度不一致!
```

### 情况 B: 翻译导致问题
```
[DEBUG-切分] audio_paths 长度: 563
[DEBUG-聚类] speaker_labels 长度: 563
[DEBUG-保存] ✓ 数据长度一致: 563
[DEBUG-克隆] speaker_labels 长度: 563
[DEBUG-克隆] target_subtitles 长度: 561  # 翻译少了 2 条
```

## 下一步行动

根据调试日志的输出，我们可以确定：
1. 是否是切分逻辑导致的问题
2. 是否是 zip 截断导致的问题
3. 是否是翻译服务导致的问题
4. 需要在哪个环节进行修复

---
**创建时间**: 2026-01-29
**目的**: 诊断字幕数量不匹配问题
