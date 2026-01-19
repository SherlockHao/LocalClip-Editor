# 🌐 Browser UI Testing Guide - Phase 1-3 完整测试

## 📋 测试前准备

### 服务状态确认
✅ **后端服务**: http://localhost:8080 (运行中)
✅ **前端服务**: http://localhost:5173 (运行中)
✅ **数据库**: backend/localclip.db (已初始化，包含1条测试记录)

### 测试环境
- **浏览器**: Chrome/Edge/Firefox (推荐使用 Chrome)
- **开发者工具**: F12 打开 (用于查看网络请求和控制台)
- **测试视频**: 准备一个小视频文件 (< 50MB)

---

## 🧪 完整测试流程

### 测试 1: 访问任务看板页面

**步骤**:
1. 打开浏览器访问: http://localhost:5173
2. 观察页面是否自动重定向到 `/dashboard`

**预期结果**:
- ✅ URL 自动变为: `http://localhost:5173/dashboard`
- ✅ 页面显示 "LocalClip Editor - 任务看板"
- ✅ 显示 "上传新视频" 按钮
- ✅ 显示任务列表区域
- ✅ 看到1条测试任务: `test_video.mp4` (从 curl 测试创建的)

**如果失败**:
- 检查浏览器控制台是否有错误
- 检查 Network 标签是否有失败的请求
- 查看后端日志: `tail -50 backend/backend_upload_test.log`

---

### 测试 2: 查看现有任务

**步骤**:
1. 在任务列表中找到 `test_video.mp4` 任务卡片
2. 检查卡片显示的信息

**预期结果**:
- ✅ 显示文件名: `test_video.mp4`
- ✅ 显示创建时间 (今天的日期时间)
- ✅ 显示状态: "待处理" 或 "pending"
- ✅ 显示7种语言的进度条:
  - 🇬🇧 English
  - 🇰🇷 Korean
  - 🇯🇵 Japanese
  - 🇫🇷 French
  - 🇩🇪 German
  - 🇪🇸 Spanish
  - 🇮🇩 Indonesian
- ✅ 所有进度条显示为 0% 或灰色 (未开始)
- ✅ 有 "打开" 按钮
- ✅ 有 🗑️ 删除按钮

**如果失败**:
- 打开浏览器开发者工具 Network 标签
- 查看是否有 `GET /api/tasks/` 请求
- 检查响应状态码是否为 200
- 检查响应数据格式

---

### 测试 3: 上传新视频

**步骤**:
1. 点击 "上传新视频" 按钮
2. 选择一个视频文件 (建议使用小文件, < 10MB)
3. 等待上传完成

**预期结果**:
- ✅ 文件选择对话框打开
- ✅ 选择文件后立即开始上传
- ✅ 显示 "上传中..." 提示或进度指示
- ✅ 上传成功后页面自动跳转到编辑器页面
- ✅ URL 变为: `http://localhost:5173/tasks/{新任务ID}`
- ✅ 浏览器开发者工具 Network 显示:
  - `POST /api/tasks/` 请求成功 (200 OK)
  - Content-Type: `multipart/form-data`
  - 响应包含新任务的 JSON 数据

**后端日志验证**:
打开新的命令行窗口运行:
```bash
tail -f backend/backend_upload_test.log
```

应该看到类似日志:
```
[任务API] 收到上传请求, 文件名: your_video.mp4, 类型: video/mp4
[任务API] 生成任务ID: task_20260117_XXXXXX_XXXXXXXX
[任务API] 创建目录结构: tasks\task_20260117_XXXXXX_XXXXXXXX
[任务API] 保存视频到: tasks\task_20260117_XXXXXX_XXXXXXXX\input\...
[任务API] 视频保存成功, 大小: XXXXX bytes
[任务API] 数据库记录创建成功: task_20260117_XXXXXX_XXXXXXXX
```

**如果失败**:
1. 检查浏览器控制台错误信息
2. 检查 Network 标签中的 `/api/tasks/` 请求:
   - 状态码是否为 200?
   - 如果是 307, 检查请求 URL 是否包含尾部斜杠 `/`
   - 如果是 404, 检查后端服务是否运行
   - 如果是 500, 查看后端日志错误详情
3. 查看后端日志: `tail -50 backend/backend_upload_test.log`
4. 检查文件大小是否过大 (推荐 < 50MB)

---

### 测试 4: 验证任务创建成功

**步骤**:
1. 上传成功后,点击浏览器后退按钮
2. 或直接访问: http://localhost:5173/dashboard
3. 查看任务列表

**预期结果**:
- ✅ 任务列表顶部显示新上传的任务
- ✅ 新任务显示正确的文件名
- ✅ 新任务显示最新的创建时间
- ✅ 状态为 "待处理"
- ✅ 现在总共有 2 个任务 (包括之前的测试任务)

**数据库验证**:
```bash
cd backend
sqlite3 localclip.db "SELECT task_id, video_original_name, status, created_at FROM tasks ORDER BY created_at DESC;"
```

应该看到新任务记录。

**文件系统验证**:
```bash
dir backend\tasks\task_20260117_*\input
```

应该看到新上传的视频文件。

---

### 测试 5: 打开任务编辑器

**步骤**:
1. 在任务看板上,点击某个任务的 "打开" 按钮
2. 或直接点击任务卡片

**预期结果**:
- ✅ 页面跳转到: `http://localhost:5173/tasks/{task_id}`
- ✅ 显示原有的视频编辑器界面
- ✅ 编辑器包含所有原有功能 (视频播放、字幕编辑等)

**注意**:
⚠️ 当前编辑器尚未完全集成任务系统 (这是 Phase 4 的工作)
- 编辑器可能无法自动加载任务视频
- 这是正常的,因为我们在 Phase 3 只完成了路由集成,不是功能集成

---

### 测试 6: 删除任务

**步骤**:
1. 返回任务看板: http://localhost:5173/dashboard
2. 找到测试任务 `test_video.mp4`
3. 点击任务卡片上的 🗑️ 删除按钮
4. 如果有确认对话框,点击确认

**预期结果**:
- ✅ 任务从列表中立即消失
- ✅ 任务总数减少 1
- ✅ 浏览器 Network 显示 `DELETE /api/tasks/{task_id}` 请求成功

**后端验证**:
```bash
# 检查数据库记录是否删除
cd backend
sqlite3 localclip.db "SELECT task_id FROM tasks WHERE task_id = 'task_20260117_145025_083c8e1f';"
```

应该返回空 (记录已删除)。

```bash
# 检查文件目录是否删除
dir backend\tasks\task_20260117_145025_083c8e1f
```

应该提示目录不存在。

**后端日志**:
```
[任务] 删除任务: task_20260117_145025_083c8e1f
```

---

## 🔍 故障排查

### 问题 1: 页面显示空白

**检查**:
1. 浏览器控制台是否有 JavaScript 错误?
2. Network 标签是否有失败的请求?
3. 前端服务是否运行? `curl http://localhost:5173`

**解决**:
```bash
# 重启前端服务
cd frontend
npm run dev
```

---

### 问题 2: 任务列表为空

**检查**:
1. Network 标签查看 `/api/tasks/` 请求
2. 响应状态码是否为 200?
3. 响应数据是否为空数组 `[]`?

**如果是空数组**:
这是正常的!首次使用时没有任务,需要上传视频创建任务。

**如果请求失败**:
```bash
# 检查后端服务
curl http://localhost:8080/api/tasks/

# 重启后端服务
cd backend
python main.py
```

---

### 问题 3: 上传失败

**检查清单**:
1. ✅ 文件大小是否 < 50MB?
2. ✅ 文件格式是否为视频? (mp4, avi, mov, etc.)
3. ✅ Network 请求 URL 是否为 `/api/tasks/` (注意尾部斜杠)?
4. ✅ 响应状态码是什么?

**状态码 307 Temporary Redirect**:
- 问题: 请求 URL 缺少尾部斜杠
- 解决: 确认 TaskDashboard.tsx 中使用 `/api/tasks/` (带斜杠)

**状态码 404 Not Found**:
- 问题: 后端服务未运行或路由未注册
- 解决: 检查 `main.py` 是否包含 `app.include_router(tasks.router)`

**状态码 500 Internal Server Error**:
- 问题: 后端处理失败
- 解决: 查看后端日志详细错误:
```bash
tail -50 backend/backend_upload_test.log
# 或使用日志查看工具
view_logs.bat
```

---

### 问题 4: 删除失败

**检查**:
1. Network 查看 `DELETE /api/tasks/{task_id}` 请求
2. 状态码是否为 200?
3. 是否有错误响应?

**常见原因**:
- 任务 ID 不存在
- 后端文件删除权限问题

**解决**:
查看后端日志了解具体错误。

---

## 📊 测试完成检查清单

完成以下所有测试即可验证 Phase 1-3 成功:

- [ ] ✅ 能访问任务看板 (http://localhost:5173/dashboard)
- [ ] ✅ 能看到任务列表 (包括测试任务)
- [ ] ✅ 能上传新视频创建任务
- [ ] ✅ 上传后自动跳转到编辑器页面
- [ ] ✅ 返回看板能看到新任务
- [ ] ✅ 新任务显示正确信息 (文件名、时间、状态)
- [ ] ✅ 7种语言进度条显示正确
- [ ] ✅ 点击 "打开" 能跳转到编辑器
- [ ] ✅ 能删除任务
- [ ] ✅ 删除后任务从列表和数据库消失

**预计测试时间**: 10-15 分钟

---

## 🎯 测试视频建议

为了快速测试,建议使用以下类型的视频:

1. **小视频文件** (< 10MB)
   - 上传速度快
   - 减少等待时间

2. **常见格式**
   - MP4 (推荐)
   - AVI
   - MOV

3. **获取测试视频**
   - 使用手机录制短视频
   - 下载免费样本视频
   - 使用现有项目中的测试视频

---

## 📝 测试记录模板

建议在测试时记录结果:

```
测试时间: 2026-01-17
测试人员: [你的名字]

测试 1 - 访问任务看板: ✅/❌
测试 2 - 查看现有任务: ✅/❌
测试 3 - 上传新视频: ✅/❌
  - 文件名: __________
  - 文件大小: __________
  - 任务 ID: __________
测试 4 - 验证任务创建: ✅/❌
测试 5 - 打开编辑器: ✅/❌
测试 6 - 删除任务: ✅/❌

遇到的问题:
1. __________
2. __________

整体评价: ✅ 通过 / ❌ 失败
```

---

## 🚀 测试成功后的下一步

如果所有测试通过,恭喜! Phase 1-3 已经完成。

**Phase 4 预览**:
- 集成现有处理 API 到任务系统
- 实现实时进度更新
- 重构编辑器使用任务目录
- 完善语言处理流程

---

**需要帮助?**

- 查看后端日志: `view_logs.bat` 或 `tail -f backend/backend_upload_test.log`
- 查看前端日志: 浏览器开发者工具 Console 标签
- 查看 API 文档: http://localhost:8080/docs
- 阅读完整实施文档: `BATCH_SYSTEM_IMPLEMENTATION.md`

**祝测试顺利!** 🎉
