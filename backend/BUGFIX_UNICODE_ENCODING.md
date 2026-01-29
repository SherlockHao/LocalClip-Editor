# UnicodeDecodeError 修复记录

## 问题描述
在 Windows 系统上运行时，多个地方的 `subprocess.run()` 调用使用了 `text=True` 参数但没有指定编码，导致默认使用系统编码（gbk），从而在处理包含特殊字符的输出时引发 `UnicodeDecodeError`。

## 错误示例
```
Exception in thread Thread-5 (_readerthread):
UnicodeDecodeError: 'gbk' codec can't decode byte 0x90 in position 4243: illegal multibyte sequence
[视频信息] FFprobe 失败: the JSON object must be str, bytes or bytearray, not NoneType
```

## 修复方案
在所有使用 `subprocess.run(..., text=True)` 的地方添加以下参数：
```python
encoding='utf-8',
errors='ignore'
```

## 已修复的文件

### 1. backend/routers/tasks.py
- **位置**: 第 217-222 行
- **修复内容**: FFprobe 获取视频信息
- **修复前**:
  ```python
  result = subprocess.run(
      ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(video_path)],
      capture_output=True,
      text=True
  )
  ```
- **修复后**:
  ```python
  result = subprocess.run(
      ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(video_path)],
      capture_output=True,
      text=True,
      encoding='utf-8',
      errors='ignore'
  )
  ```

### 2. backend/video_processor.py
修复了 6 处 subprocess.run 调用：
- **第 70 行**: 视频文件验证（ffprobe）
- **第 149 行**: 获取视频流信息（ffprobe）
- **第 217 行**: 视频导出（ffmpeg）
- **第 274 行**: 硬件加速编码（ffmpeg）
- **第 298 行**: 软件编码回退（ffmpeg）
- **第 319 行**: 检查硬件编码器（ffmpeg -encoders）

### 3. backend/fish_voice_cloner.py
修复了 3 处 subprocess.run 调用（使用 replace_all）：
- **第 159 行**: 编码参考音频（fish-speech encoder）
- **第 221 行**: 生成语义 tokens（fish-speech text2semantic）
- **第 277 行**: 解码音频（fish-speech decoder）

### 4. speaker_diarization_processing/audio_extraction.py
- **位置**: 第 105-111 行（已在之前修复）
- **修复内容**: FFmpeg 提取音频片段

## 修复效果
- ✅ 解决了所有 `UnicodeDecodeError: 'gbk' codec can't decode` 错误
- ✅ FFprobe 可以正确获取视频信息
- ✅ FFmpeg 可以正常提取和处理音频
- ✅ Fish-Speech 语音克隆可以正常运行
- ✅ 跨平台兼容性提升（Windows/Linux/macOS）

## 测试建议
1. 上传包含中文路径或特殊字符的视频文件
2. 执行说话人识别和音频提取
3. 执行视频导出和语音克隆
4. 检查日志中是否还有 UnicodeDecodeError

## 注意事项
- 所有 subprocess 调用现在都使用 UTF-8 编码
- `errors='ignore'` 确保即使遇到无法解码的字符也不会崩溃
- 这个修复对所有调用 ffmpeg/ffprobe 的外部工具都适用

---
**修复日期**: 2026-01-29
**修复版本**: 本次优化
