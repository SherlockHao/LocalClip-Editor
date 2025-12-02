import React, { useState, useRef, useEffect } from 'react';
import { Upload, Video, Clock, Settings, Play, Pause, RotateCcw } from 'lucide-react';
import VideoPlayer from './components/VideoPlayer';
import SubtitleTimeline from './components/SubtitleTimeline';
import Sidebar from './components/Sidebar';
import PropertiesPanel from './components/PropertiesPanel';

interface VideoFile {
  filename: string;
  original_name: string;
  size: number;
  video_info: {
    width: number;
    height: number;
    resolution: string;
    duration: number;
    duration_formatted: string;
    bitrate: string;
    codec: string;
  };
}

interface Subtitle {
  start_time: number;
  end_time: number;
  start_time_formatted: string;
  end_time_formatted: string;
  text: string;
  speaker_id?: number;  // 新增说话人ID
}

const App: React.FC = () => {
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [currentVideo, setCurrentVideo] = useState<VideoFile | null>(null);
  const [subtitles, setSubtitles] = useState<Subtitle[]>([]);
  const [subtitleFilename, setSubtitleFilename] = useState<string | null>(null); // 新增：SRT文件名
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [exportSettings, setExportSettings] = useState({
    hardSubtitles: false,
    quality: 'high'
  });
  const [isProcessingSpeakerDiarization, setIsProcessingSpeakerDiarization] = useState(false);
  const [speakerDiarizationTaskId, setSpeakerDiarizationTaskId] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  const refreshVideos = async () => {
    try {
      const response = await fetch('/api/videos');
      if (!response.ok) {
        throw new Error(`获取视频列表失败: ${response.statusText}`);
      }
      const result = await response.json();
      setVideos(result.videos);
    } catch (error) {
      console.error('获取视频列表时出错:', error);
    }
  };

  const handleVideoUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload/video', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`上传失败: ${response.statusText}`);
      }

      const result = await response.json();
      const newVideo: VideoFile = {
        filename: result.filename,
        original_name: result.original_name,
        size: result.size,
        video_info: result.video_info
      };

      // 刷新视频列表以获取最新状态，而不是添加到现有列表
      await refreshVideos();
      setCurrentVideo(newVideo);
    } catch (error) {
      console.error('上传视频时出错:', error);
      alert('上传视频失败: ' + (error as Error).message);
    }
  };

  const handleSubtitleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/upload/subtitle', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`上传失败: ${response.statusText}`);
      }

      const result = await response.json();
      setSubtitles(result.subtitles);
      setSubtitleFilename(result.filename); // 保存SRT文件名
    } catch (error) {
      console.error('上传字幕时出错:', error);
      alert('上传字幕失败: ' + (error as Error).message);
    }
  };

  const handleEditSubtitle = (index: number, newSubtitle: Subtitle) => {
    const updatedSubtitles = [...subtitles];
    updatedSubtitles[index] = newSubtitle;
    setSubtitles(updatedSubtitles);
  };

  const handleDeleteSubtitle = (index: number) => {
    const updatedSubtitles = subtitles.filter((_, i) => i !== index);
    setSubtitles(updatedSubtitles);
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const handleExport = () => {
    console.log('Exporting video with settings:', exportSettings);
    // 这里应该调用后端API导出视频
  };

  const handleRunSpeakerDiarization = async () => {
    if (!currentVideo) {
      alert('请先上传并选择视频文件');
      return;
    }
    
    if (!subtitleFilename) {
      alert('请先上传SRT字幕文件');
      return;
    }
    
    try {
      setIsProcessingSpeakerDiarization(true);
      
      // 发送请求到后端启动说话人识别
      const response = await fetch('/api/speaker-diarization/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_filename: currentVideo.filename,
          subtitle_filename: subtitleFilename
        }),
      });
      
      if (!response.ok) {
        throw new Error(`请求失败: ${response.statusText}`);
      }
      
      const result = await response.json();
      setSpeakerDiarizationTaskId(result.task_id);
      
      // 开始轮询状态
      pollSpeakerDiarizationStatus(result.task_id);
    } catch (error) {
      console.error('启动说话人识别失败:', error);
      alert('启动说话人识别失败: ' + (error as Error).message);
      setIsProcessingSpeakerDiarization(false);
    }
  };

  const pollSpeakerDiarizationStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/speaker-diarization/status/${taskId}`);
      
      if (!response.ok) {
        throw new Error(`获取状态失败: ${response.statusText}`);
      }
      
      const status = await response.json();
      
      if (status.status === 'completed') {
        // 处理完成，将说话人ID添加到字幕中
        if (status.speaker_labels) {
          const updatedSubtitles = subtitles.map((subtitle, index) => {
            const speakerId = status.speaker_labels[index];
            return {
              ...subtitle,
              speaker_id: speakerId !== null && speakerId !== undefined ? speakerId : undefined
            };
          });
          setSubtitles(updatedSubtitles);
        }
        
        setIsProcessingSpeakerDiarization(false);
        setSpeakerDiarizationTaskId(null);
        alert(`说话人识别完成！识别出 ${status.unique_speakers} 个不同说话人`);
      } else if (status.status === 'failed') {
        console.error('说话人识别失败:', status.message);
        alert('说话人识别失败: ' + status.message);
        setIsProcessingSpeakerDiarization(false);
        setSpeakerDiarizationTaskId(null);
      } else {
        // 继续轮询
        setTimeout(() => pollSpeakerDiarizationStatus(taskId), 2000);
      }
    } catch (error) {
      console.error('轮询说话人识别状态失败:', error);
      alert('获取说话人识别状态失败: ' + (error as Error).message);
      setIsProcessingSpeakerDiarization(false);
      setSpeakerDiarizationTaskId(null);
    }
  };

  

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 顶部工具栏 */}
      <header className="bg-white border-b border-gray-200 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Video className="text-blue-600" size={24} />
          <h1 className="text-xl font-bold text-gray-800">LocalClip Editor</h1>
        </div>
        <div className="flex items-center space-x-4">
          <button 
            onClick={handlePlayPause}
            className="flex items-center space-x-1 bg-blue-600 text-white px-3 py-1.5 rounded-md hover:bg-blue-700 transition-colors"
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
            <span>{isPlaying ? '暂停' : '播放'}</span>
          </button>
          <button className="flex items-center space-x-1 bg-gray-200 text-gray-800 px-3 py-1.5 rounded-md hover:bg-gray-300 transition-colors">
            <RotateCcw size={18} />
            <span>重置</span>
          </button>
        </div>
      </header>

      {/* 主内容区域 */}
      <div className="flex flex-1 overflow-hidden">
        {/* 左侧边栏 */}
        <Sidebar 
          videos={videos}
          onVideoSelect={setCurrentVideo}
          onVideoUpload={handleVideoUpload}
          onSubtitleUpload={(file) => {
            handleSubtitleUpload(file);
          }}
        />

        {/* 中央视频预览区 */}
        <main className="flex-1 flex flex-col p-4 overflow-y-auto">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col min-h-[500px]">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">
                {currentVideo ? currentVideo.original_name : '视频预览'}
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <div className="flex items-center space-x-1">
                  <Clock size={16} />
                  <span>{currentTime.toFixed(2)}s / {duration.toFixed(2)}s</span>
                </div>
                {currentVideo && (
                  <span className="bg-gray-100 px-2 py-1 rounded">
                    {currentVideo.video_info.resolution}
                  </span>
                )}
              </div>
            </div>
            <div className="flex-1 flex items-center justify-center bg-black/5 min-h-[400px]">
              {currentVideo ? (
                <VideoPlayer
                  videoRef={videoRef}
                  src={`/uploads/${currentVideo.filename}`}
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  isPlaying={isPlaying}
                  currentTime={currentTime}
                  duration={duration}
                />
              ) : (
                <div className="text-center text-gray-500">
                  <Video size={64} className="mx-auto mb-4 opacity-50" />
                  <p>请在左侧上传视频文件</p>
                </div>
              )}
            </div>
          </div>

          {/* 字幕时间轴 */}
          {subtitles.length > 0 && (
            <div className="mt-4 bg-white rounded-lg shadow-sm border border-gray-200 p-4 flex-shrink-0">
              <SubtitleTimeline
                subtitles={subtitles}
                currentTime={currentTime}
                duration={duration}
                onSeek={handleSeek}
                onEditSubtitle={handleEditSubtitle}
                onDeleteSubtitle={handleDeleteSubtitle}
              />
            </div>
          )}
        </main>

        {/* 右侧属性面板 */}
        <PropertiesPanel
          exportSettings={exportSettings}
          onExportSettingsChange={setExportSettings}
          onExport={handleExport}
          onRunSpeakerDiarization={handleRunSpeakerDiarization}
          isProcessingSpeakerDiarization={isProcessingSpeakerDiarization}
          currentVideo={currentVideo}
        />
      </div>
    </div>
  );
};

export default App;