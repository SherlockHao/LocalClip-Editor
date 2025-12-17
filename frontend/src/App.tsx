import React, { useState, useRef, useEffect } from 'react';
import { Upload, Video, Clock, Settings, Play, Pause, RotateCcw, Zap, Volume2, Music } from 'lucide-react';
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
  const [speakerDiarizationProgress, setSpeakerDiarizationProgress] = useState({ message: '', progress: 0 });
  const [showNotification, setShowNotification] = useState(false);
  const [notificationData, setNotificationData] = useState({
    title: '',
    message: '',
    uniqueSpeakers: undefined as number | undefined
  });
  const [speakerNameMapping, setSpeakerNameMapping] = useState<{[key: number]: string}>({});
  const [filteredSpeakerId, setFilteredSpeakerId] = useState<number | null>(null); // 筛选的说话人ID

  // 语音克隆相关状态
  const [targetLanguage, setTargetLanguage] = useState<string>('');
  const [targetSrtFilename, setTargetSrtFilename] = useState<string | null>(null);
  const [isProcessingVoiceCloning, setIsProcessingVoiceCloning] = useState(false);
  const [voiceCloningTaskId, setVoiceCloningTaskId] = useState<string | null>(null);
  const [isStitchingAudio, setIsStitchingAudio] = useState(false);
  const [stitchedAudioPath, setStitchedAudioPath] = useState<string | null>(null);
  const [useStitchedAudio, setUseStitchedAudio] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const isSeekingRef = useRef<boolean>(false);

  // 空格键播放/暂停
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // 只在没有焦点在输入框时触发
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT') {
        return;
      }

      if (e.code === 'Space') {
        e.preventDefault();
        handlePlayPause();
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [isPlaying]);

  const refreshVideos = async () => {
    try {
      const response = await fetch('/api/videos');
      if (!response.ok) {
        throw new Error(`获取视频列表失败: ${response.statusText}`);
      }
      const result = await response.json();
      setVideos(result.videos);
    } catch (error) {
      // 获取视频列表失败
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
      const video = videoRef.current;

      // 检查视频是否已经加载足够的数据
      if (video.readyState < 2) {
        return;
      }

      // 设置 seeking 标志
      isSeekingRef.current = true;

      // 设置视频时间
      video.currentTime = time;

      // 监听 seeked 事件来更新状态
      const handleSeeked = () => {
        setCurrentTime(video.currentTime);
        isSeekingRef.current = false;
        video.removeEventListener('seeked', handleSeeked);
      };
      video.addEventListener('seeked', handleSeeked, { once: true });
    }
  };

  const handleAddSpeaker = (gender: 'male' | 'female') => {
    // 获取当前最大的说话人ID
    const existingIds = Object.keys(speakerNameMapping).map(id => parseInt(id));
    const maxId = existingIds.length > 0 ? Math.max(...existingIds) : -1;
    const newId = maxId + 1;

    // 计算该性别的当前数量
    let count = 0;
    Object.values(speakerNameMapping).forEach(name => {
      if (gender === 'male' && name.startsWith('男')) count++;
      if (gender === 'female' && name.startsWith('女')) count++;
    });

    // 生成新的说话人名称
    const newName = gender === 'male' ? `男${count + 1}` : `女${count + 1}`;

    // 更新映射
    setSpeakerNameMapping({
      ...speakerNameMapping,
      [newId]: newName
    });
  };

  const handleRemoveSpeaker = (speakerId: number) => {
    // 从映射中删除该说话人
    const newMapping = { ...speakerNameMapping };
    delete newMapping[speakerId];
    setSpeakerNameMapping(newMapping);

    // 检查字幕中是否有使用该说话人，如果有则重置为undefined
    const updatedSubtitles = subtitles.map(subtitle => {
      if (subtitle.speaker_id === speakerId) {
        return {
          ...subtitle,
          speaker_id: undefined
        };
      }
      return subtitle;
    });
    setSubtitles(updatedSubtitles);
  };

  const handleExport = () => {
    // TODO: 实现视频导出功能
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
      setSpeakerDiarizationProgress({ message: '初始化中...', progress: 0 });

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
      alert('启动说话人识别失败: ' + (error as Error).message);
      setIsProcessingSpeakerDiarization(false);
      setSpeakerDiarizationProgress({ message: '', progress: 0 });
    }
  };

  const pollSpeakerDiarizationStatus = async (taskId: string) => {
    try {
      console.log('轮询状态, taskId:', taskId);
      const response = await fetch(`/api/speaker-diarization/status/${taskId}`);

      if (!response.ok) {
        throw new Error(`获取状态失败: ${response.statusText}`);
      }

      const status = await response.json();
      console.log('收到状态:', status);

      // 更新进度信息
      setSpeakerDiarizationProgress({
        message: status.message || '处理中...',
        progress: status.progress || 0
      });

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

        // 提取说话人名称映射
        if (status.speaker_name_mapping) {
          setSpeakerNameMapping(status.speaker_name_mapping);
        }

        setIsProcessingSpeakerDiarization(false);
        setSpeakerDiarizationTaskId(null);

        // 显示成功通知，包含处理时间
        const durationInfo = status.duration_str ? ` (耗时: ${status.duration_str})` : '';
        setNotificationData({
          title: '说话人识别完成',
          message: `已成功完成说话人识别并标记到字幕中，你现在可以在字幕详情中查看和编辑说话人信息。${durationInfo}`,
          uniqueSpeakers: status.unique_speakers
        });
        setShowNotification(true);
      } else if (status.status === 'failed') {
        // 显示失败通知，包含失败前的耗时
        const durationInfo = status.duration_str ? ` (失败前耗时: ${status.duration_str})` : '';
        const errorMessage = status.message || '处理过程中发生错误，请重试。';
        setNotificationData({
          title: '说话人识别失败',
          message: `${errorMessage}${durationInfo}`,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);

        setIsProcessingSpeakerDiarization(false);
        setSpeakerDiarizationTaskId(null);
      } else {
        setTimeout(() => pollSpeakerDiarizationStatus(taskId), 2000);
      }
    } catch (error) {
      alert('获取说话人识别状态失败: ' + (error as Error).message);
      setIsProcessingSpeakerDiarization(false);
      setSpeakerDiarizationTaskId(null);
    }
  };

  // 处理目标语言srt文件上传
  const handleTargetSrtUpload = async (file: File) => {
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
      setTargetSrtFilename(result.filename);
    } catch (error) {
      alert('上传目标语言字幕失败: ' + (error as Error).message);
    }
  };

  // 执行语音克隆
  const handleRunVoiceCloning = async () => {
    if (!currentVideo) {
      alert('请先上传并选择视频文件');
      return;
    }

    if (!subtitleFilename) {
      alert('请先上传原始SRT字幕文件');
      return;
    }

    if (!targetLanguage) {
      alert('请选择目标语言');
      return;
    }

    if (!targetSrtFilename) {
      alert('请上传目标语言的SRT字幕文件');
      return;
    }

    try {
      setIsProcessingVoiceCloning(true);

      const response = await fetch('/api/voice-cloning/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_filename: currentVideo.filename,
          source_subtitle_filename: subtitleFilename,
          target_language: targetLanguage,
          target_subtitle_filename: targetSrtFilename
        }),
      });

      if (!response.ok) {
        throw new Error(`请求失败: ${response.statusText}`);
      }

      const result = await response.json();
      setVoiceCloningTaskId(result.task_id);

      pollVoiceCloningStatus(result.task_id);
    } catch (error) {
      alert('启动语音克隆失败: ' + (error as Error).message);
      setIsProcessingVoiceCloning(false);
    }
  };

  // 播放克隆音频
  const handlePlayClonedAudio = (audioPath: string) => {
    // 构建完整的音频URL
    const audioUrl = `/api/cloned-audio/${voiceCloningTaskId}/${audioPath.split('/').pop()}`;
    const audio = new Audio(audioUrl);
    audio.play().catch(error => {
      console.error('播放克隆音频失败:', error);
      alert('播放克隆音频失败');
    });
  };

  // 重新生成单个片段
  const handleRegenerateSegment = async (index: number, newSpeakerId: number) => {
    if (!voiceCloningTaskId) {
      alert('语音克隆任务ID不存在');
      return;
    }

    try {
      const response = await fetch('/api/voice-cloning/regenerate-segment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: voiceCloningTaskId,
          segment_index: index,
          new_speaker_id: newSpeakerId
        })
      });

      if (!response.ok) {
        throw new Error(`重新生成失败: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // 更新该片段的克隆音频信息
        setSubtitles(prevSubtitles => {
          return prevSubtitles.map((subtitle, i) => {
            if (i === index) {
              return {
                ...subtitle,
                cloned_audio_path: result.cloned_audio_path,
                cloned_speaker_id: result.new_speaker_id
              };
            }
            return subtitle;
          });
        });

        alert('重新生成成功！');
      }
    } catch (error) {
      console.error('重新生成失败:', error);
      alert('重新生成失败: ' + (error as Error).message);
    }
  };

  // 拼接克隆音频
  const handleStitchAudio = async () => {
    if (!voiceCloningTaskId) {
      alert('语音克隆任务ID不存在');
      return;
    }

    try {
      setIsStitchingAudio(true);

      const response = await fetch('/api/voice-cloning/stitch-audio', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: voiceCloningTaskId
        })
      });

      if (!response.ok) {
        throw new Error(`拼接音频失败: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // 先清空音频路径，确保effect会被触发
        setStitchedAudioPath(null);
        setUseStitchedAudio(false);

        // 使用setTimeout确保状态更新完成后再设置新路径
        setTimeout(() => {
          // 添加时间戳参数防止浏览器缓存
          const audioPathWithCache = `${result.stitched_audio_path}?t=${Date.now()}`;
          // 保存拼接音频路径并自动切换到拼接音频
          setStitchedAudioPath(audioPathWithCache);
          setUseStitchedAudio(true);
        }, 0);

        alert(`拼接成功！已生成完整音频，共 ${result.segments_count} 个片段，总时长 ${result.total_duration.toFixed(2)}s`);
      }
    } catch (error) {
      console.error('拼接音频失败:', error);
      alert('拼接音频失败: ' + (error as Error).message);
    } finally {
      setIsStitchingAudio(false);
    }
  };

  // 轮询语音克隆状态
  const pollVoiceCloningStatus = async (taskId: string) => {
    try {
      const response = await fetch(`/api/voice-cloning/status/${taskId}`);

      if (!response.ok) {
        throw new Error(`获取状态失败: ${response.statusText}`);
      }

      const status = await response.json();

      if (status.status === 'completed') {
        setIsProcessingVoiceCloning(false);

        // 更新字幕数据，添加目标语言文本和克隆音频路径
        if (status.cloned_results && Array.isArray(status.cloned_results)) {
          setSubtitles(prevSubtitles => {
            return prevSubtitles.map((subtitle, index) => {
              const clonedResult = status.cloned_results.find((r: any) => r.index === index);
              if (clonedResult) {
                return {
                  ...subtitle,
                  target_text: clonedResult.target_text,
                  cloned_audio_path: clonedResult.cloned_audio_path,
                  cloned_speaker_id: clonedResult.speaker_id
                };
              }
              return subtitle;
            });
          });
        }

        // 显示成功通知，包含处理时间
        const durationInfo = status.duration_str ? ` (耗时: ${status.duration_str})` : '';
        setNotificationData({
          title: '语音克隆完成',
          message: `已成功完成语音克隆，可在字幕详情中播放克隆音频。${durationInfo}`,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);
      } else if (status.status === 'failed') {
        // 显示失败通知，包含失败前的耗时
        const durationInfo = status.duration_str ? ` (失败前耗时: ${status.duration_str})` : '';
        const errorMessage = status.message || '处理过程中发生错误，请重试。';
        setNotificationData({
          title: '语音克隆失败',
          message: `${errorMessage}${durationInfo}`,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);

        setIsProcessingVoiceCloning(false);
        setVoiceCloningTaskId(null);
      } else {
        setTimeout(() => pollVoiceCloningStatus(taskId), 2000);
      }
    } catch (error) {
      alert('获取语音克隆状态失败: ' + (error as Error).message);
      setIsProcessingVoiceCloning(false);
      setVoiceCloningTaskId(null);
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
        
        <div className="flex items-center gap-6">
          {/* 播放控制按钮 */}
          <div className="flex items-center space-x-3">
            <button
              onClick={handlePlayPause}
              className="flex items-center space-x-2 bg-gradient-to-r from-blue-600 to-blue-500 text-white px-4 py-2.5 rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-200 font-medium"
            >
              {isPlaying ? <Pause size={18} /> : <Play size={18} />}
              <span>{isPlaying ? '暂停' : '播放'}</span>
            </button>

            <button
              onClick={() => handleSeek(0)}
              className="flex items-center space-x-2 bg-slate-700 text-slate-100 px-4 py-2.5 rounded-lg hover:bg-slate-600 transition-all duration-200 font-medium"
            >
              <RotateCcw size={18} />
              <span>重置</span>
            </button>
          </div>

          {/* 简洁时间轴 */}
          {currentVideo && duration > 0 && (
            <div className="flex items-center gap-3 flex-1 max-w-md">
              <span className="text-xs font-mono text-slate-400 min-w-[45px]">
                {new Date(currentTime * 1000).toISOString().substr(14, 5)}
              </span>
              <div
                className="flex-1 h-2 bg-slate-700 rounded-full cursor-pointer relative group"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const x = e.clientX - rect.left;
                  const percentage = x / rect.width;
                  handleSeek(percentage * duration);
                }}
              >
                <div
                  className="absolute h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all"
                  style={{ width: `${(currentTime / duration) * 100}%` }}
                />
                <div
                  className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow-lg transition-all"
                  style={{ left: `${(currentTime / duration) * 100}%`, transform: 'translate(-50%, -50%)' }}
                />
              </div>
              <span className="text-xs font-mono text-slate-400 min-w-[45px]">
                {new Date(duration * 1000).toISOString().substr(14, 5)}
              </span>
            </div>
          )}
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
              speakerNameMapping={speakerNameMapping}
              onAddSpeaker={handleAddSpeaker}
              onRemoveSpeaker={handleRemoveSpeaker}
              onPlayClonedAudio={handlePlayClonedAudio}
              onRegenerateSegment={handleRegenerateSegment}
              voiceCloningTaskId={voiceCloningTaskId || undefined}
              filteredSpeakerId={filteredSpeakerId}
              onFilteredSpeakerChange={setFilteredSpeakerId}
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
              <div className="flex-1 flex items-center justify-center bg-black/40 overflow-hidden relative">
                {currentVideo ? (
                  <>
                    <VideoPlayer
                      videoRef={videoRef}
                      src={`/uploads/${currentVideo.filename}`}
                      key={`/uploads/${currentVideo.filename}`}
                      onTimeUpdate={handleTimeUpdate}
                      onLoadedMetadata={handleLoadedMetadata}
                      isPlaying={isPlaying}
                      currentTime={currentTime}
                      duration={duration}
                      audioSrc={stitchedAudioPath}
                      useExternalAudio={useStitchedAudio}
                      filteredSpeakerId={filteredSpeakerId}
                      subtitles={subtitles}
                    />
                    {/* 音频切换按钮 */}
                    {stitchedAudioPath && (
                      <div className="absolute top-4 right-4 flex items-center gap-2 bg-slate-900/80 backdrop-blur-sm border border-slate-700 rounded-lg px-3 py-2 shadow-lg">
                        <span className="text-xs text-slate-400 font-medium">音频源:</span>
                        <button
                          onClick={() => setUseStitchedAudio(false)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                            !useStitchedAudio
                              ? 'bg-blue-600 text-white shadow-md'
                              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-300'
                          }`}
                        >
                          <Volume2 size={14} />
                          原音频
                        </button>
                        <button
                          onClick={() => setUseStitchedAudio(true)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                            useStitchedAudio
                              ? 'bg-emerald-600 text-white shadow-md'
                              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-300'
                          }`}
                        >
                          <Music size={14} />
                          克隆音频
                        </button>
                      </div>
                    )}
                  </>
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
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl shadow-xl border border-slate-700 p-4 flex-shrink-0">
              <div className="flex items-center space-x-2 mb-3">
                <Zap size={14} className="text-yellow-400" />
                <h3 className="text-sm font-semibold text-slate-100">字幕时间轴</h3>
                <span className="ml-auto text-xs text-slate-400 bg-slate-700/50 px-2 py-0.5 rounded">
                  {subtitles.length} 条
                </span>
              </div>
              <SubtitleTimeline
                subtitles={subtitles}
                currentTime={currentTime}
                duration={duration}
                onSeek={handleSeek}
                onStitchAudio={handleStitchAudio}
                stitching={isStitchingAudio}
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
          speakerDiarizationProgress={speakerDiarizationProgress}
          currentVideo={currentVideo}
          targetLanguage={targetLanguage}
          onTargetLanguageChange={setTargetLanguage}
          targetSrtFilename={targetSrtFilename}
          onTargetSrtUpload={handleTargetSrtUpload}
          onRunVoiceCloning={handleRunVoiceCloning}
          isProcessingVoiceCloning={isProcessingVoiceCloning}
          speakerDiarizationCompleted={subtitles.some(s => s.speaker_id !== undefined)}
        />
      </div>
    </div>
  );
};

export default App;