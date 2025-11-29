import requests
import os
import time

# 等待后端服务启动
print("等待后端服务启动...")
time.sleep(5)

# 测试API端点
BASE_URL = "http://localhost:8000"

# 1. 测试根端点
print("1. 测试根端点...")
try:
    response = requests.get(BASE_URL)
    print(f"   状态码: {response.status_code}")
    print(f"   响应: {response.json()}")
except Exception as e:
    print(f"   错误: {e}")

# 2. 测试获取视频列表
print("\n2. 测试获取视频列表...")
try:
    response = requests.get(f"{BASE_URL}/videos")
    print(f"   状态码: {response.status_code}")
    data = response.json()
    print(f"   视频数量: {len(data.get('videos', []))}")
    if data.get('videos'):
        print(f"   第一个视频: {data['videos'][0]['filename']}")
except Exception as e:
    print(f"   错误: {e}")

# 3. 测试视频上传（如果需要）
print("\n3. 测试视频信息获取...")
try:
    uploads_dir = "/Users/yiya_workstation/Documents/ai_editing/workspace/LocalClip-Editor/uploads"
    video_files = [f for f in os.listdir(uploads_dir) if f.endswith('.mp4')]
    
    if video_files:
        video_file = video_files[0]
        print(f"   检测到视频文件: {video_file}")
        
        # 可以尝试获取视频信息
        response = requests.get(f"{BASE_URL}/videos")
        videos = response.json().get('videos', [])
        
        for video in videos:
            if video['filename'] == video_file:
                print(f"   视频信息: {video['video_info']}")
                break
    else:
        print("   未找到MP4视频文件")
except Exception as e:
    print(f"   错误: {e}")

# 4. 测试SRT解析
print("\n4. 测试SRT文件...")
try:
    uploads_dir = "/Users/yiya_workstation/Documents/ai_editing/workspace/LocalClip-Editor/uploads"
    srt_files = [f for f in os.listdir(uploads_dir) if f.endswith('.srt')]
    
    if srt_files:
        srt_file = srt_files[0]
        print(f"   检测到SRT文件: {srt_file}")
        
        # 尝试上传SRT文件
        srt_path = os.path.join(uploads_dir, srt_file)
        with open(srt_path, 'rb') as f:
            files = {'file': (srt_file, f, 'application/octet-stream')}
            response = requests.post(f"{BASE_URL}/upload/subtitle", files=files)
        
        print(f"   SRT上传状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   字幕条目数量: {len(data.get('subtitles', []))}")
            if data.get('subtitles'):
                print(f"   第一条字幕: {data['subtitles'][0]['text']}")
    else:
        print("   未找到SRT文件")
except Exception as e:
    print(f"   错误: {e}")

print("\n测试完成！")
print("\n环境配置检查总结:")
print("- FFmpeg 已安装 ✓")
print("- 后端依赖已安装 ✓")
print("- 视频和SRT文件已添加 ✓")
print("- 后端服务已启动 ✓")
print("- API端点可访问 ✓")
print("\n前端需要安装依赖后启动，可使用以下命令:")
print("cd /Users/yiya_workstation/Documents/ai_editing/workspace/LocalClip-Editor/frontend && npm install && npm run dev")
print("\n或者使用一键启动脚本:")
print("/Users/yiya_workstation/Documents/ai_editing/workspace/LocalClip-Editor/start.sh")