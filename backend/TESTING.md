# 测试指南

## 测试文件清单

### 1. GPU 和模型选择测试

**文件**: `test_model_selection.py`
**启动**: `test_model_select.bat`
**环境**: qwen_inference

**测试内容**:
- GPU 显存检测
- 模型存在性检查
- 自动模型选择逻辑
- 详细的测试报告

**运行方式**:
```bash
# Windows
test_model_select.bat

# 或手动
conda activate qwen_inference
python test_model_selection.py
```

**预期输出**:
```
🔍 开始测试模型选择功能...

============================================================
测试GPU显存检测
============================================================
[GPU检测] GPU显存信息:
  总显存: 12.00 GB
  已分配: 0.00 GB
  已保留: 0.00 GB
  可用: 12.00 GB

✅ GPU检测成功，可用显存: 12.00 GB

============================================================
测试模型选择
============================================================

模型目录: d:/ai_editing\models

可用模型:
  ✓ Qwen3-4B-FP8
  ✗ Qwen3-4B
  ✓ Qwen3-1.7B

------------------------------------------------------------
[模型选择] 可用显存: 12.00 GB
[模型选择] ✓ 选择 Qwen3-4B-FP8 (需要 6.0 GB, 可用 12.00 GB)
------------------------------------------------------------

✅ 选择的模型路径: d:/ai_editing\models\Qwen3-4B-FP8
   模型名称: Qwen3-4B-FP8

============================================================
测试总结
============================================================
✅ GPU可用显存: 12.00 GB
✅ 已选择模型: Qwen3-4B-FP8

💡 建议: 使用 Qwen3-4B-FP8 可以获得最佳翻译质量

============================================================
✅ 测试完成
============================================================
```

---

### 2. 翻译功能测试

**文件**: `test_translation_simple.py`
**启动**: `test_translation.bat`
**环境**: qwen_inference

**测试内容**:
- 模型加载
- 实际翻译任务
- JSON 格式输出
- 结果验证

**运行方式**:
```bash
# Windows
test_translation.bat

# 或手动
conda activate qwen_inference
python test_translation_simple.py
```

**预期输出**:
```
================================================================
简单翻译测试
================================================================
✅ 已导入 batch_retranslate 模块

[测试任务]
原文: 你好
目标语言: 韩文

配置文件: C:\Users\...\tmp_xxx.json

================================================================
开始翻译...
================================================================

[GPU检测] GPU显存信息:
  总显存: 12.00 GB
  可用: 12.00 GB

[模型选择] ✓ 选择 Qwen3-4B-FP8

[PID 12345] Loading model from d:/ai_editing\models\Qwen3-4B-FP8...
[PID 12345] Model loaded on device: cuda:0

[批量翻译] 开始批量翻译
  任务数量: 1
  进程数量: 1

[Worker 1] 开始处理任务 simple-test-1: 你好...
[Worker 1] 完成任务 simple-test-1，耗时 2.35秒

[1/1] simple-test-1: 你好 -> 안녕

================================================================
翻译结果
================================================================

任务ID: simple-test-1
原文: 你好
译文: 안녕
状态: ✅ 成功

✅ 翻译测试完成
```

---

### 3. 端到端流程测试

**文件**: `test_batch_translation_e2e.py`
**环境**: qwen_inference

**测试内容**:
- 配置文件创建
- 模块导入验证
- GPU 检测
- 模型选择
- 配置格式验证

**运行方式**:
```bash
conda activate qwen_inference
python test_batch_translation_e2e.py
```

**预期输出**:
```
======================================================================
端到端测试：批量翻译完整流程
======================================================================

[步骤1] 创建测试配置文件...
✅ 配置文件已创建
   任务数量: 3
   目标语言: 韩文

[步骤2] 验证 batch_retranslate.py...
✅ batch_retranslate.py 导入成功

[步骤3] 检测 GPU 显存...
✅ GPU 检测成功，可用显存: 12.00 GB

[步骤4] 自动选择模型...
✅ 已选择模型: Qwen3-4B-FP8
   ✓ config.json
   ✓ tokenizer_config.json
✅ 模型文件验证通过

[步骤5] 模拟批量翻译流程...
提示: 完整翻译需要加载模型，这里仅测试配置和选择逻辑

[步骤6] 验证配置文件格式...
✅ 配置文件格式正确

======================================================================
测试总结
======================================================================
✅ 配置文件创建
✅ 模块导入
✅ GPU检测
✅ 模型选择
✅ 模型文件验证
✅ 配置格式验证

💡 下一步:
  1. 运行 test_model_select.bat 测试模型选择
  2. 在应用中触发翻译任务，验证完整流程
  3. 检查日志确认使用了正确的模型

======================================================================
✅ 端到端测试完成
======================================================================
```

---

### 4. JSON 提取测试

**文件**: `test_json_extraction_standalone.py`
**环境**: 无需特殊环境（不依赖 transformers）

**测试内容**:
- JSON 格式提取
- 多种输出格式支持
- 思考过程移除
- 韩语/日语支持
- 错误处理

**运行方式**:
```bash
python test_json_extraction_standalone.py
```

**预期输出**:
```
=== 测试JSON提取功能 ===

✅ 测试1: 标准JSON格式
✅ 测试2: 无空格JSON
✅ 测试3: 带空格JSON
✅ 测试4: 韩语翻译
✅ 测试5: 日语翻译
...

============================================================
测试结果: 13 通过, 0 失败
============================================================

🎉 所有测试通过！
```

---

### 5. 韩语/日语文本处理测试

**文件**: `test_korean_japanese.py`
**环境**: 无需特殊环境

**测试内容**:
- 韩语文本规范化
- 日语文本规范化
- 文本长度计算
- 多语言支持

**运行方式**:
```bash
python test_korean_japanese.py
```

---

## 完整测试流程

### 测试顺序（推荐）

1. **基础功能测试**（不需要加载模型）
   ```bash
   python test_json_extraction_standalone.py
   python test_korean_japanese.py
   python test_batch_translation_e2e.py
   ```

2. **模型选择测试**
   ```bash
   test_model_select.bat
   ```

3. **翻译功能测试**
   ```bash
   test_translation.bat
   ```

4. **应用集成测试**
   - 启动应用
   - 上传视频和字幕
   - 触发语音克隆
   - 检查日志中的模型选择信息

---

## 故障排查

### 问题1: 找不到 transformers 模块

**症状**:
```
ModuleNotFoundError: No module named 'transformers'
```

**解决方案**:
```bash
# 确保在正确的环境中
conda activate qwen_inference

# 如果仍然缺少，安装 transformers
conda install transformers
```

---

### 问题2: 找不到模型文件

**症状**:
```
[模型选择] ✗ Qwen3-4B-FP8 不存在
[模型选择] ✗ Qwen3-1.7B 不存在
```

**解决方案**:
检查模型目录：
```bash
dir d:/ai_editing\models
```

应该看到：
- `Qwen3-4B-FP8/`
- `Qwen3-1.7B/`

如果缺失，需要重新下载模型。

---

### 问题3: GPU 显存不足

**症状**:
```
[GPU检测] 可用显存: 3.50 GB
[模型选择] ✗ Qwen3-4B-FP8 显存不足 (需要 6.0 GB)
[模型选择] ⚠ 显存不足，使用回退模型: Qwen3-1.7B
```

**解决方案**:
1. 关闭其他占用 GPU 的程序
2. 重启应用释放显存
3. 如果是 Fish-Speech 占用，考虑使用 CPU 模式

---

### 问题4: UnicodeDecodeError

**症状**:
```
UnicodeDecodeError: 'gbk' codec can't encode character
```

**解决方案**:
所有测试脚本都已添加 UTF-8 强制输出：
```python
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
```

如果仍然出现，检查：
1. Windows 控制台编码设置
2. 使用批处理文件（已包含 `chcp 65001`）

---

### 问题5: NameError: model_path not defined

**症状**:
```
NameError: name 'model_path' is not defined
```

**解决方案**:
已在最新代码中修复。确保使用最新版本的 `main.py`。

---

## 日志解读

### 正常日志示例

```
[GPU检测] GPU显存信息:
  总显存: 12.00 GB
  已分配: 0.00 GB
  已保留: 0.00 GB
  可用: 12.00 GB

[模型选择] 可用显存: 12.00 GB
[模型选择] ✓ 选择 Qwen3-4B-FP8 (需要 6.0 GB, 可用 12.00 GB)

[PID 12345] Loading model from d:/ai_editing\models\Qwen3-4B-FP8...
[PID 12345] Tokenizer loaded, loading model...
[PID 12345] Model loaded on device: cuda:0

[批量翻译] 开始批量翻译
  任务数量: 10
  进程数量: 1

[Worker 1] 开始处理任务 task-1: 你好...
[Worker 1] 完成任务 task-1，耗时 2.35秒

[1/10] task-1: 你好 -> 안녕
[2/10] task-2: 不好 -> 안 좋아
...

[批量翻译] 全部完成！共处理 10 个任务
```

### 关键日志标记

| 日志前缀 | 含义 | 示例 |
|---------|------|------|
| `[GPU检测]` | GPU 显存检测信息 | 显存大小、占用情况 |
| `[模型选择]` | 模型选择决策 | 选择了哪个模型 |
| `[PID xxx]` | 工作进程日志 | 模型加载进度 |
| `[Worker x]` | 工作线程日志 | 任务处理状态 |
| `[批量翻译]` | 批处理流程 | 总体进度 |
| `[x/y]` | 实时翻译结果 | 每句翻译的结果 |

---

## 性能基准

### 预期性能指标

| 指标 | RTX 5090 | RTX 5070 | 其他 (<8GB) |
|-----|---------|---------|-------------|
| 选择模型 | Qwen3-4B-FP8 | Qwen3-4B-FP8 | Qwen3-1.7B |
| 单句翻译时间 | 1-3秒 | 2-4秒 | 1-2秒 |
| 首次加载时间 | 15-30秒 | 20-40秒 | 10-20秒 |
| 显存占用 | ~6GB | ~6GB | ~4GB |
| 批量吞吐 | 20-30句/分钟 | 15-20句/分钟 | 30-40句/分钟 |

---

## 自动化测试

### 运行所有测试

创建 `run_all_tests.bat`:
```batch
@echo off
echo 运行所有测试...

echo.
echo ========================================
echo 测试1: JSON 提取
echo ========================================
python test_json_extraction_standalone.py
if errorlevel 1 goto :error

echo.
echo ========================================
echo 测试2: 韩语/日语处理
echo ========================================
python test_korean_japanese.py
if errorlevel 1 goto :error

echo.
echo ========================================
echo 测试3: 端到端流程
echo ========================================
python test_batch_translation_e2e.py
if errorlevel 1 goto :error

echo.
echo ========================================
echo 测试4: 模型选择
echo ========================================
call test_model_select.bat

echo.
echo ========================================
echo 所有测试通过！
echo ========================================
goto :end

:error
echo.
echo ========================================
echo 测试失败！
echo ========================================
pause
exit /b 1

:end
pause
```

---

## 持续集成建议

对于生产环境，建议：

1. **每次部署前运行完整测试套件**
2. **监控日志中的模型选择决策**
3. **定期验证翻译质量**
4. **记录性能指标**
5. **保留测试日志用于问题排查**

---

## 相关文档

- [MODEL_SELECTION.md](MODEL_SELECTION.md) - 模型选择详细说明
- [TRANSLATION_JSON_FORMAT.md](TRANSLATION_JSON_FORMAT.md) - JSON 格式说明
- [KOREAN_JAPANESE_SUPPORT.md](KOREAN_JAPANESE_SUPPORT.md) - 多语言支持
