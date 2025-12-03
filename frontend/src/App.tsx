import React, { useState, useRef, useEffect } from 'react';
import { Upload, Video, Clock, Settings, Play, Pause, RotateCcw, Zap } from 'lucide-react';
import VideoPlayer from './components/VideoPlayer';
import SubtitleTimeline from './components/SubtitleTimeline';
import SubtitleDetails from './components/SubtitleDetails';
import Sidebar from './components/Sidebar';
import PropertiesPanel from './components/PropertiesPanel';
import NotificationModal from './components/NotificationModal';

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
  speaker_id?: number;
}

const App: React.FC = () => {
  const [videos, setVideos] = useState<VideoFile[]>([]);
  const [currentVideo, setCurrentVideo] = useState<VideoFile | null>(null);
  const [subtitles, setSubtitles] = useState<Subtitle[]>([]);
  const [subtitleFilename, setSubtitleFilename] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [exportSettings, setExportSettings] = useState({
    hardSubtitles: false,
    quality: 'high'
  });
  const [isProcessingSpeakerDiarization, setIsProcessingSpeakerDiarization] = useState(false);
  const [speakerDiarizationTaskId, setSpeakerDiarizationTaskId] = useState<string | null>(null);
  const [showNotification, setShowNotification] = useState(false);
  const [notificationData, setNotificationData] = useState({
    title: '',
    message: '',
    uniqueSpeakers: undefined as number | undefined
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const isSeekingRef = useRef<boolean>(false);

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
      setSubtitleFilename(result.filename);
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
    if (videoRef.current && !isSeekingRef.current) {
      console.log('[handleTimeUpdate] 视频时间:', videoRef.current.currentTime);
      setCurrentTime(videoRef.current.currentTime);
    } else if (isSeekingRef.current) {
      console.log('[handleTimeUpdate] 跳过（正在 seeking）');
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      const video = videoRef.current;
      console.log('[handleSeek] 开始 seek 到:', time);
      console.log('[handleSeek] 视频状态 - readyState:', video.readyState, 'duration:', video.duration, 'currentTime:', video.currentTime);

      // 检查视频是否已经加载足够的数据
      if (video.readyState < 2) {
        console.error('[handleSeek] 错误：视频还没有加载足够的元数据！readyState =', video.readyState);
        return;
      }

      // 设置 seeking 标志
      isSeekingRef.current = true;
      console.log('[handleSeek] 设置 isSeekingRef = true');

      // 诊断 video 元素
      console.log('[handleSeek] video 元素信息:');
      console.log('  - tagName:', video.tagName);
      console.log('  - src:', video.src);
      console.log('  - paused:', video.paused);
      console.log('  - ended:', video.ended);
      console.log('  - seeking:', video.seeking);
      console.log('  - networkState:', video.networkState);

      // 检查 currentTime 属性描述符
      const descriptor = Object.getOwnPropertyDescriptor(HTMLVideoElement.prototype, 'currentTime');
      console.log('[handleSeek] currentTime 属性描述符:', descriptor);
      console.log('  - 可写:', descriptor?.writable);
      console.log('  - 有 setter:', !!descriptor?.set);

      // 检查是否是真实的 video 元素
      console.log('[handleSeek] 元素类型检查:');
      console.log('  - instanceof HTMLVideoElement:', video instanceof HTMLVideoElement);
      console.log('  - constructor.name:', video.constructor.name);

      // 尝试多种方法设置视频时间
      console.log('[handleSeek] 正在设置 video.currentTime =', time);
      try {
        const oldTime = video.currentTime;

        // 方法1：直接赋值
        video.currentTime = time;
        console.log('[handleSeek] 方法1（直接赋值）结果:', video.currentTime);

        // 方法2：使用 setter
        if (descriptor?.set) {
          descriptor.set.call(video, time);
          console.log('[handleSeek] 方法2（调用 setter）结果:', video.currentTime);
        }

        // 方法3：使用 setAttribute
        video.setAttribute('currentTime', String(time));
        console.log('[handleSeek] 方法3（setAttribute）结果:', video.currentTime);

        const newTime = video.currentTime;
        console.log('[handleSeek] 最终设置结果: 旧值=', oldTime, ', 新值=', newTime, ', 目标=', time);

        // 如果还是失败，延迟重试
        if (newTime === oldTime) {
          console.warn('[handleSeek] 所有方法都失败，延迟重试...');
          setTimeout(() => {
            console.log('[handleSeek] 延迟重试前 currentTime =', video.currentTime);
            video.currentTime = time;
            console.log('[handleSeek] 延迟重试后 currentTime =', video.currentTime);
          }, 100);
        }
      } catch (error) {
        console.error('[handleSeek] 设置 currentTime 时出错:', error);
      }

      // 监听 seeked 事件来更新状态
      const handleSeeked = () => {
        const finalTime = video.currentTime;
        console.log('[handleSeek] seeked 事件触发，最终时间:', finalTime);

        // 更新状态到最终时间
        console.log('[handleSeek] 更新状态到:', finalTime);
        setCurrentTime(finalTime);

        // 检查是否成功
        if (Math.abs(finalTime - time) > 0.1) {
          console.warn('[handleSeek] 警告：最终时间与目标不符！目标:', time, '实际:', finalTime);
        } else {
          console.log('[handleSeek] ✓ seek 成功！');
        }

        // 清除 seeking 标志
        isSeekingRef.current = false;
        console.log('[handleSeek] 设置 isSeekingRef = false，seek 完成');

        video.removeEventListener('seeked', handleSeeked);
      };
      video.addEventListener('seeked', handleSeeked, { once: true });
    }
  };

  const handleExport = () => {
    console.log('Exporting video with settings:', exportSettings);
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

        // 显示成功通知
        setNotificationData({
          title: '说话人识别完成',
          message: '已成功完成说话人识别并标记到字幕中，你现在可以在字幕详情中查看和编辑说话人信息。',
          uniqueSpeakers: status.unique_speakers
        });
        setShowNotification(true);
      } else if (status.status === 'failed') {
        console.error('说话人识别失败:', status.message);

        // 显示失败通知
        setNotificationData({
          title: '说话人识别失败',
          message: status.message || '处理过程中发生错误，请重试。',
          uniqueSpeakers: undefined
        });
        setShowNotification(true);

        setIsProcessingSpeakerDiarization(false);
        setSpeakerDiarizationTaskId(null);
      } else {
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
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* 通知模态框 */}
      <NotificationModal
        isOpen={showNotification}
        onClose={() => setShowNotification(false)}
        title={notificationData.title}
        message={notificationData.message}
        uniqueSpeakers={notificationData.uniqueSpeakers}
      />

      {/* 顶部工具栏 */}
      <header className="bg-gradient-to-r from-slate-900 to-slate-800 border-b border-slate-700 px-6 py-4 flex items-center justify-between shadow-lg backdrop-blur-sm bg-opacity-95">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg">
            <Video className="text-white" size={24} />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-blue-300 bg-clip-text text-transparent">
            LocalClip Editor
          </h1>
        </div>
        
        <div className="flex items-center space-x-3">
          <button 
            onClick={handlePlayPause}
            className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white px-4 py-2.5 rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-200 font-medium"
          >
            {isPlaying ? <Pause size={18} /> : <Play size={18} />}
            <span>{isPlaying ? '暂停' : '播放'}</span>
          </button>
          
          <button className="flex items-center space-x-2 bg-slate-700 text-slate-100 px-4 py-2.5 rounded-lg hover:bg-slate-600 transition-all duration-200 font-medium">
            <RotateCcw size={18} />
            <span>重置</span>
          </button>
        </div>
      </header>

      {/* 主内容区域 - 新布局 */}
      <div className="flex flex-1 overflow-hidden gap-3 p-3">
        {/* 左侧边栏（素材库）- 不变 */}
        <Sidebar 
          videos={videos}
          onVideoSelect={setCurrentVideo}
          onVideoUpload={handleVideoUpload}
          onSubtitleUpload={handleSubtitleUpload}
        />

        {/* 中央区域（新布局：上方播放器+信息，下方时间轴） */}
        <div className="flex-1 flex flex-col overflow-hidden gap-3">
          {/* 上层：字幕详情 + 播放器 */}
          <div className="flex gap-3 flex-1 overflow-hidden">
            {/* 左侧：字幕详细信息列表 */}
            <SubtitleDetails
              subtitles={subtitles}
              currentTime={currentTime}
              onEditSubtitle={handleEditSubtitle}
              onDeleteSubtitle={handleDeleteSubtitle}
              onSeek={handleSeek}
            />

            {/* 右侧：播放器 + 视频信息 */}
            <div className="flex-1 flex flex-col overflow-hidden bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl shadow-xl border border-slate-700">
              {/* 视频头部信息 */}
              <div className="p-5 border-b border-slate-700 flex items-center justify-between bg-gradient-to-r from-slate-800 via-slate-800 to-slate-900 flex-shrink-0">
                <h2 className="text-lg font-semibold text-slate-100">
                  {currentVideo ? currentVideo.original_name : '视频预览'}
                </h2>
                <div className="flex items-center space-x-6 text-sm text-slate-300">
                  <div className="flex items-center space-x-2 bg-slate-700/50 px-3 py-1.5 rounded-lg">
                    <Clock size={16} className="text-blue-400" />
                    <span className="font-mono">{currentTime.toFixed(2)}s / {duration.toFixed(2)}s</span>
                  </div>
                  {currentVideo && (
                    <span className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 px-3 py-1.5 rounded-lg border border-blue-500/30 text-blue-300 font-medium">
                      {currentVideo.video_info.resolution}
                    </span>
                  )}
                </div>
              </div>

              {/* 视频播放器区域 */}
              <div className="flex-1 flex items-center justify-center bg-black/40 overflow-hidden">
                {currentVideo ? (
                  <VideoPlayer
                    videoRef={videoRef}
                    src={`/uploads/${currentVideo.filename}`}
                    key={`/uploads/${currentVideo.filename}`}
                    onTimeUpdate={handleTimeUpdate}
                    onLoadedMetadata={handleLoadedMetadata}
                    isPlaying={isPlaying}
                    currentTime={currentTime}
                    duration={duration}
                  />
                ) : (
                  <div className="text-center text-slate-400">
                    <div className="mb-4 flex justify-center">
                      <div className="p-4 bg-slate-700/30 rounded-full">
                        <Video size={64} className="opacity-60" />
                      </div>
                    </div>
                    <p className="text-lg font-medium">请在左侧上传视频文件</p>
                    <p className="text-sm text-slate-500 mt-1">支持 MP4、MOV、AVI 等常见格式</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 下层：时间轴 */}
          {subtitles.length > 0 && (
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl shadow-xl border border-slate-700 p-5 flex-shrink-0">
              <div className="flex items-center space-x-2 mb-4">
                <Zap size={18} className="text-yellow-400" />
                <h3 className="text-lg font-semibold text-slate-100">字幕时间轴</h3>
                <span className="ml-auto text-sm text-slate-400 bg-slate-700/50 px-2.5 py-1 rounded">
                  {subtitles.length} 条字幕
                </span>
              </div>
              <SubtitleTimeline
                subtitles={subtitles}
                currentTime={currentTime}
                duration={duration}
                onSeek={handleSeek}
              />
            </div>
          )}
        </div>

        {/* 右侧属性面板 - 不变 */}
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