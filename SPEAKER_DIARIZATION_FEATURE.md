# 说话人识别功能

## 功能描述

LocalClip Editor 现在支持说话人识别和聚类功能。该功能可以根据SRT字幕的时间段，从视频中提取对应的音频片段，并使用深度学习模型识别和区分不同的说话人。

## 工作流程

1. 按SRT文件的时间段从视频中提取音频片段（转换为WAV格式）
2. 使用 `pyannote.audio` 的 `wespeaker-voxceleb-resnet34-LM` 模型提取每个音频片段的说话人嵌入向量
3. 使用AgglomerativeClustering算法对嵌入向量进行聚类，识别不同的说话人
4. 将识别结果与原始字幕关联，并在UI中显示

## 文件结构

```
workspace/LocalClip-Editor/
├── speaker_diarization_processing/     # 新增：说话人识别处理脚本
│   ├── __init__.py
│   ├── audio_extraction.py             # 音频提取功能
│   ├── embedding_extraction.py         # 嵌入提取功能
│   ├── speaker_clustering.py           # 说话人聚类功能
│   └── main_processor.py               # 主处理脚本
├── backend/
│   ├── main.py                         # 已修改：添加说话人识别API端点
│   └── requirements.txt                # 已修改：添加新依赖
└── frontend/
    └── src/
        ├── components/
        │   └── SubtitleTimeline.tsx    # 已修改：显示说话人ID
        ├── types/
        │   └── index.ts                # 已修改：添加speaker_id字段
        └── components/
            └── PropertiesPanel.tsx     # 已修改：添加说话人识别按钮
```

## 新增API端点

- `POST /speaker-diarization/process` - 启动说话人识别处理流程
- `GET /speaker-diarization/status/{task_id}` - 获取说话人识别处理状态

## 新增依赖

- `torch` - PyTorch深度学习框架
- `pyannote.audio` - 说话人识别模型
- `huggingface_hub` - 模型下载
- `scipy` - 科学计算
- `scikit-learn` - 机器学习聚类算法

## 使用方法

1. 上传视频文件
2. 上传对应的SRT字幕文件
3. 点击右侧属性面板中的"运行说话人识别"按钮
4. 等待处理完成（状态显示在按钮下方）
5. 处理完成后，字幕时间轴上会显示每个片段对应的说话人ID

## 缓存管理

- 视频和字幕文件：`uploads/` 目录
- 音频片段缓存：`audio_segments/` 目录（分离存储）

## 注意事项

- 首次运行可能需要下载模型文件，需要网络连接
- 处理时间取决于视频长度和字幕段落数量
- 推荐在配置较高的设备上运行以获得更好的性能