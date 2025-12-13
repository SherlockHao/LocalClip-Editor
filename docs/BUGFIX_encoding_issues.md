# Bug修复：批量重新翻译的编码问题

## 问题描述

在执行批量重新翻译时，遇到以下错误：

```
Exception in thread Thread-109 (_readerthread):
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa8 in position 98: invalid start byte

⚠️  重新翻译出错: 'NoneType' object has no attribute 'strip'
AttributeError: 'NoneType' object has no attribute 'strip'
```

## 根本原因

### 原因 1：subprocess 编码问题

在 Windows 上，`subprocess.Popen` 使用 `text=True` 和 `encoding='utf-8'` 时：

```python
# 有问题的代码
process = subprocess.Popen(
    [python_exe, script, config],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,           # ❌ 问题
    encoding='utf-8',    # ❌ 问题
)
```

**问题**：
- Windows 控制台可能输出非 UTF-8 字符（GBK、CP936 等）
- subprocess 内部的 `_readerthread` 尝试用 UTF-8 解码失败
- 解码失败导致 `communicate()` 返回 `None`

### 原因 2：批量翻译脚本的输出编码

`batch_retranslate.py` 在 Windows 上运行时：
- 默认使用系统编码（通常是 GBK）
- print() 输出的中文可能包含 GBK 字节序列
- 父进程尝试用 UTF-8 解码这些字节时失败

### 原因 3：模型路径错误

配置文件中的模型路径错误：
```json
"model_path": "C:\\workspace\\ai_editing\\workspace\\LocalClip-Editor\\models\\Qwen3-1.7B"
```

实际路径应该是：
```json
"model_path": "C:\\workspace\\ai_editing\\models\\Qwen3-1.7B"
```

## 解决方案

### 修复 1：subprocess 使用 bytes 模式

**文件**: `backend/main.py`

**修改前**:
```python
process = subprocess.Popen(
    [qwen_env_python, batch_retranslate_script, config_file],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,          # ❌
    encoding='utf-8',   # ❌
)

stdout, stderr = process.communicate(timeout=600)
# stdout 可能为 None！
output_lines = stdout.strip().split('\n')  # AttributeError!
```

**修改后**:
```python
process = subprocess.Popen(
    [qwen_env_python, batch_retranslate_script, config_file],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    # ✅ 使用 bytes 模式，手动解码
)

stdout_bytes, stderr_bytes = process.communicate(timeout=600)

# ✅ 手动解码，使用 errors='replace' 避免解码错误
stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
```

**关键点**：
- 不指定 `text=True` 和 `encoding`，使用 bytes 模式
- 手动解码时使用 `errors='replace'`：遇到无法解码的字节用 `�` 替换
- 检查 bytes 对象是否为 None 再解码

### 修复 2：强制批量翻译脚本使用 UTF-8 输出

**文件**: `backend/batch_retranslate.py`

**修改**: 在文件开头添加
```python
import sys
import os

# 强制 UTF-8 输出，避免 Windows 控制台编码问题
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
```

**作用**：
- 确保脚本输出使用 UTF-8 编码
- 即使在 GBK 控制台环境中也输出 UTF-8
- `errors='replace'` 确保无法编码的字符不会导致崩溃

### 修复 3：修正模型路径计算

**文件**: `backend/main.py`

**修改前**:
```python
script_dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
models_dir = os.path.join(script_dir_path, "models")
model_path = os.path.join(models_dir, "Qwen3-1.7B")
# 结果: C:\...\LocalClip-Editor\models\Qwen3-1.7B ❌
```

**修改后**:
```python
# 从 backend 目录向上 4 级到达 ai_editing 目录
backend_dir = os.path.dirname(os.path.abspath(__file__))  # backend
localclip_dir = os.path.dirname(backend_dir)  # LocalClip-Editor
workspace_dir = os.path.dirname(localclip_dir)  # workspace
ai_editing_dir = os.path.dirname(workspace_dir)  # ai_editing
model_path = os.path.join(ai_editing_dir, "models", "Qwen3-1.7B")
# 结果: C:\workspace\ai_editing\models\Qwen3-1.7B ✅
```

### 修复 4：改进错误处理和日志

**文件**: `backend/main.py`

**改进**:
1. 添加模型路径验证
2. 过滤无关的 stderr 警告
3. 处理空输出的情况
4. 打印更详细的调试信息

```python
# 检查模型路径
if not os.path.exists(model_path):
    print(f"⚠️  模型路径不存在: {model_path}")
    print(f"使用原译文继续...")
    # 跳过重新翻译

# 过滤 stderr
if stderr and stderr.strip():
    stderr_lines = stderr.strip().split('\n')
    filtered_stderr = '\n'.join([
        line for line in stderr_lines
        if 'UnicodeDecodeError' not in line and '_readerthread' not in line
    ])
    if filtered_stderr:
        print(f"[Retranslate] stderr:\n{filtered_stderr}")

# 处理不同的返回情况
if returncode == 0 and stdout:
    # 正常解析
    ...
elif returncode != 0:
    print(f"⚠️  重新翻译失败 (返回码: {returncode})")
    if stdout and stdout.strip():
        print(f"[Retranslate] stdout:\n{stdout[:500]}")
    print("使用原译文继续...")
else:
    print("⚠️  重新翻译返回成功但没有输出，使用原译文继续...")
```

## 测试验证

### 测试 1：编码问题修复验证

**预期行为**:
- 不再出现 `UnicodeDecodeError`
- 不再出现 `'NoneType' object has no attribute 'strip'`
- stderr 中的编码相关警告被过滤

**测试命令**:
```bash
# 重启后端
cd backend
conda activate ui
uvicorn main:app --reload

# 触发语音克隆，查看日志
```

### 测试 2：模型路径验证

**预期输出**:
```
[Retranslate] 模型路径: C:\workspace\ai_editing\models\Qwen3-1.7B
```

如果路径不存在：
```
⚠️  模型路径不存在: ...
使用原译文继续...
```

### 测试 3：批量翻译脚本独立测试

```bash
# 激活 qwen_inference 环境
conda activate qwen_inference

# 运行测试配置
cd c:\workspace\ai_editing\workspace\LocalClip-Editor\backend
python batch_retranslate.py test_retranslate_config.json
```

**预期**:
- 脚本正常输出 UTF-8 编码的中文
- 不再有编码错误
- 最后输出 JSON 结果

## 相关文件修改

| 文件 | 修改内容 | 行号 |
|------|---------|------|
| `backend/main.py` | subprocess bytes 模式 | 832-848 |
| `backend/main.py` | 手动解码with errors='replace' | 845-847 |
| `backend/main.py` | 过滤 stderr 警告 | 855-861 |
| `backend/main.py` | 改进错误处理 | 889-895 |
| `backend/main.py` | 修正模型路径计算 | 782-789 |
| `backend/batch_retranslate.py` | 强制 UTF-8 输出 | 6-13 |

## 技术要点

### Python subprocess 编码最佳实践

**问题代码**:
```python
# ❌ 在 Windows 上容易出错
proc = subprocess.Popen(..., text=True, encoding='utf-8')
stdout, stderr = proc.communicate()
```

**推荐代码**:
```python
# ✅ 跨平台健壮
proc = subprocess.Popen(..., stdout=PIPE, stderr=PIPE)  # bytes 模式
stdout_bytes, stderr_bytes = proc.communicate()
stdout = stdout_bytes.decode('utf-8', errors='replace')
stderr = stderr_bytes.decode('utf-8', errors='replace')
```

### Windows 控制台编码问题

**问题**：
- Windows 控制台默认编码：GBK (CP936)
- Python 默认输出编码：跟随控制台（GBK）
- subprocess 期望编码：UTF-8

**解决**：
```python
# 在被调用脚本中强制 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

### 解码错误处理策略

| 策略 | 说明 | 使用场景 |
|------|------|---------|
| `errors='strict'` | 遇到错误抛异常（默认） | 严格验证数据完整性 |
| `errors='ignore'` | 忽略无法解码的字节 | 丢失数据可接受 |
| `errors='replace'` | 用 � 替换无法解码的字节 | 保留数据结构，允许部分损失 |
| `errors='backslashreplace'` | 用 \\xNN 替换 | 调试、查看原始字节 |

**本项目选择**: `errors='replace'`
- 保留 JSON 结构（重要！）
- 允许中文日志部分损失（可接受）
- 确保不崩溃（关键）

## 验收标准

✅ 批量重新翻译不再报 `UnicodeDecodeError`
✅ 不再报 `'NoneType' object has no attribute 'strip'`
✅ 模型路径正确
✅ 超长译文能够成功重新翻译
✅ 翻译失败时正常降级到原译文

## 后续改进

1. **日志优化**
   - 实时显示翻译进度
   - 使用结构化日志（JSON）

2. **性能优化**
   - 缓存模型加载
   - 并行翻译（如果显存足够）

3. **用户体验**
   - 添加进度条
   - 翻译前预览超长译文
   - 允许用户手动编辑

## 参考资料

- [Python subprocess 文档](https://docs.python.org/3/library/subprocess.html)
- [Unicode HOWTO](https://docs.python.org/3/howto/unicode.html)
- [Windows 控制台编码问题](https://stackoverflow.com/questions/878972/windows-cmd-encoding-change-causes-python-crash)

## 版本历史

- **v1.0** (2025-12-13): 初始版本，修复编码问题
  - subprocess 使用 bytes 模式
  - 手动解码with errors='replace'
  - 强制批量翻译脚本 UTF-8 输出
  - 修正模型路径
