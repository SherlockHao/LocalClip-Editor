import React, { useState, useRef, useEffect } from 'react';
import { Upload, Video, Clock, Settings, Play, Pause, RotateCcw, Zap, Volume2, Music, ArrowLeft, PlayCircle, StopCircle, Loader2 } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import axios from 'axios';

// 批量处理状态接口
interface BatchStatus {
  state: 'idle' | 'running' | 'stopping' | 'stopped';
  is_running: boolean;
  current_task_id: string | null;
  current_language: string | null;
  current_stage: string | null;
  total_tasks: number;
  completed_tasks: number;
  total_stages: number;
  completed_stages: number;
  message: string;
  started_at: string | null;
  error: string | null;
}
import VideoPlayer from '../components/VideoPlayer';
import SubtitleTimeline from '../components/SubtitleTimeline';
import SubtitleDetails from '../components/SubtitleDetails';
import Sidebar from '../components/Sidebar';
import PropertiesPanel from '../components/PropertiesPanel';
import NotificationModal from '../components/NotificationModal';

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
  target_text?: string;
  cloned_audio_path?: string;
  cloned_speaker_id?: number;
  actual_start_time?: number;
  actual_end_time?: number;
}

const App: React.FC = () => {
  const navigate = useNavigate();
  const { taskId } = useParams<{ taskId: string }>();
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
  const speakerDiarizationProgressTimer = useRef<NodeJS.Timeout | null>(null);
  const lastRealProgress = useRef<number>(0);
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
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationProgress, setTranslationProgress] = useState<{message: string, progress: number} | null>(null);
  const translationProgressTimer = useRef<NodeJS.Timeout | null>(null);
  const lastTranslationProgress = useRef<number>(0);
  const [isProcessingVoiceCloning, setIsProcessingVoiceCloning] = useState(false);
  const [voiceCloningProgress, setVoiceCloningProgress] = useState<{message: string, progress: number} | null>(null);
  const voiceCloningProgressTimer = useRef<NodeJS.Timeout | null>(null);
  const lastVoiceCloningProgress = useRef<number>(0);
  const [voiceCloningTaskId, setVoiceCloningTaskId] = useState<string | null>(null);
  const [isStitchingAudio, setIsStitchingAudio] = useState(false);
  const [stitchedAudioPath, setStitchedAudioPath] = useState<string | null>(null);
  const [useStitchedAudio, setUseStitchedAudio] = useState(false);

  // 视频导出相关状态
  const [isExportingVideo, setIsExportingVideo] = useState(false);
  const [exportVideoCompleted, setExportVideoCompleted] = useState(false);
  const [exportVideoProgress, setExportVideoProgress] = useState<{message: string, progress: number} | null>(null);
  const [exportedVideoDir, setExportedVideoDir] = useState<string | null>(null);
  const exportVideoProgressTimer = useRef<NodeJS.Timeout | null>(null);

  // 运行任务状态 - 用于阻止同时启动多个任务
  // 这是当前 taskId 的运行任务
  const [runningTask, setRunningTask] = useState<{
    task_id?: string;
    language: string;
    stage: string;
    started_at: string;
    message?: string;
    progress?: number;
  } | null>(null);

  // 全局运行任务状态 - 可能是其他 taskId 的任务
  const [globalRunningTask, setGlobalRunningTask] = useState<{
    task_id: string;
    language: string;
    stage: string;
    started_at: string;
    message?: string;
    progress?: number;
  } | null>(null);

  // 用于防止语言切换时的竞态条件
  const currentLanguageRef = useRef<string>('');

  // 默认音色库和音色映射状态
  const [defaultVoices, setDefaultVoices] = useState<Array<{id: string, name: string, audio_url: string, reference_text: string}>>([]);
  const [speakerVoiceMapping, setSpeakerVoiceMapping] = useState<{[speakerId: string]: string}>({});
  const [initialSpeakerVoiceMapping, setInitialSpeakerVoiceMapping] = useState<{[speakerId: string]: string}>({});
  const [isRegeneratingVoices, setIsRegeneratingVoices] = useState(false);

  // 批量处理状态
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);
  const isSeekingRef = useRef<boolean>(false);
  const progressBarRef = useRef<HTMLDivElement>(null);
  const [isDraggingProgress, setIsDraggingProgress] = useState(false);

  // 空格键播放/暂停
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // 只在没有焦点在输入框时触发
      const target = e.target as HTMLElement;
      // 排除输入框、按钮等可聚焦元素，防止空格键重复触发
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.tagName === 'BUTTON') {
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

  // 进度条拖拽功能
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingProgress || !progressBarRef.current) return;

      const rect = progressBarRef.current.getBoundingClientRect();
      const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
      const percentage = x / rect.width;
      const newTime = percentage * duration;

      handleSeek(newTime);
    };

    const handleMouseUp = () => {
      setIsDraggingProgress(false);
    };

    if (isDraggingProgress) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingProgress, duration]);

  // 清理说话人识别进度定时器
  useEffect(() => {
    return () => {
      if (speakerDiarizationProgressTimer.current) {
        clearInterval(speakerDiarizationProgressTimer.current);
        speakerDiarizationProgressTimer.current = null;
      }
    };
  }, []);

  // 清理翻译进度定时器
  useEffect(() => {
    return () => {
      if (translationProgressTimer.current) {
        clearInterval(translationProgressTimer.current);
        translationProgressTimer.current = null;
      }
    };
  }, []);

  // 清理语音克隆进度定时器
  useEffect(() => {
    return () => {
      if (voiceCloningProgressTimer.current) {
        clearInterval(voiceCloningProgressTimer.current);
        voiceCloningProgressTimer.current = null;
      }
    };
  }, []);

  // 清理视频导出进度定时器
  useEffect(() => {
    return () => {
      if (exportVideoProgressTimer.current) {
        clearInterval(exportVideoProgressTimer.current);
        exportVideoProgressTimer.current = null;
      }
    };
  }, []);

  // 定期刷新全局运行任务状态
  useEffect(() => {
    if (!taskId) return;

    // 刷新全局运行任务状态的函数
    const refreshGlobalRunningTask = async () => {
      try {
        const response = await axios.get('/api/global-running-task', { timeout: 5000 });
        const data = response.data;
        if (data.has_running_task && data.running_task) {
          const rt = data.running_task;
          // 更新全局运行任务
          setGlobalRunningTask(prev => {
            if (!prev || prev.task_id !== rt.task_id || prev.language !== rt.language ||
                prev.stage !== rt.stage || prev.progress !== rt.progress || prev.message !== rt.message) {
              return {
                task_id: rt.task_id,
                language: rt.language,
                stage: rt.stage,
                started_at: rt.started_at,
                message: rt.message,
                progress: rt.progress
              };
            }
            return prev;
          });

          // 如果是当前任务，同时更新 runningTask
          if (rt.task_id === taskId) {
            setRunningTask(prev => {
              if (!prev || prev.language !== rt.language || prev.stage !== rt.stage ||
                  prev.progress !== rt.progress || prev.message !== rt.message) {
                return {
                  task_id: rt.task_id,
                  language: rt.language,
                  stage: rt.stage,
                  started_at: rt.started_at,
                  message: rt.message,
                  progress: rt.progress
                };
              }
              return prev;
            });

            // 只有当运行任务的语言与当前显示的语言匹配时，才更新个别进度状态
            // 使用 ref 确保获取最新的 targetLanguage 值
            const currentLang = currentLanguageRef.current;
            if (rt.language === currentLang) {
              // 当前显示的语言正在执行任务，更新对应的进度状态
              if (rt.stage === 'translation') {
                setIsTranslating(true);
                setTranslationProgress({ message: rt.message || '', progress: rt.progress || 0 });
              } else if (rt.stage === 'voice_cloning') {
                setIsProcessingVoiceCloning(true);
                setVoiceCloningProgress({ message: rt.message || '', progress: rt.progress || 0 });
              } else if (rt.stage === 'stitch') {
                setIsStitchingAudio(true);
              } else if (rt.stage === 'export') {
                setIsExportingVideo(true);
                setExportVideoProgress({ message: rt.message || '', progress: rt.progress || 0 });
              }
            }
            // 注意：当 rt.language !== currentLang 时，不需要做任何事
            // 因为 restoreLanguageStatus 已经清除了这些状态
            // runningTask 会显示在 "其他任务运行中" 提示框中
          } else {
            // 不是当前任务，清除 runningTask
            setRunningTask(null);
          }
        } else {
          setGlobalRunningTask(null);
          setRunningTask(null);
        }
      } catch (error) {
        // 忽略错误，保持当前状态
      }
    };

    // 立即刷新一次
    refreshGlobalRunningTask();

    // 每 2 秒刷新一次
    const interval = setInterval(refreshGlobalRunningTask, 2000);

    return () => clearInterval(interval);
  }, [taskId]);

  // 定期刷新批量处理状态
  useEffect(() => {
    const fetchBatchStatus = async () => {
      try {
        const response = await axios.get('/api/batch/status', { timeout: 5000 });
        setBatchStatus(response.data);
      } catch (error) {
        // 静默失败
      }
    };

    fetchBatchStatus();
    const interval = setInterval(fetchBatchStatus, 2000);

    return () => clearInterval(interval);
  }, []);

  // 启动单任务批量处理
  const handleStartBatchSingleTask = async () => {
    if (!taskId) return;

    // 获取当前左侧选中的语言列表
    const languages = ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id']; // TODO: 从左侧面板获取实际选择的语言

    try {
      const response = await axios.post(`/api/batch/start/${taskId}`, {
        languages: languages,
        speaker_voice_mapping: speakerVoiceMapping
      }, { timeout: 10000 });

      if (response.data.success) {
        console.log('单任务批量处理已启动:', response.data.message);
      }
    } catch (error: any) {
      if (error.response?.status === 409) {
        alert('批量处理已在运行中');
      } else {
        alert('启动批量处理失败: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  // 停止批量处理
  const handleStopBatch = async () => {
    try {
      const response = await axios.post('/api/batch/stop', {}, { timeout: 10000 });
      if (response.data.success) {
        console.log('已请求停止批量处理');
      }
    } catch (error: any) {
      alert('停止批量处理失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 获取语言的中文名称
  const getLanguageNameForBatch = (language: string): string => {
    if (language === 'default') return '';
    const languageNames: Record<string, string> = {
      'en': '英语', 'ko': '韩语', 'ja': '日语', 'fr': '法语',
      'de': '德语', 'es': '西班牙语', 'id': '印尼语'
    };
    return languageNames[language] || language;
  };

  // 获取阶段的中文名称
  const getStageNameForBatch = (stage: string): string => {
    const stageNames: Record<string, string> = {
      'speaker_diarization': '说话人识别', 'translation': '翻译',
      'voice_cloning': '语音克隆', 'stitch': '音频拼接', 'export': '视频导出'
    };
    return stageNames[stage] || stage;
  };

  // 当检测到有运行中的说话人识别任务时，自动启动轮询
  useEffect(() => {
    if (isProcessingSpeakerDiarization && speakerDiarizationTaskId && taskId) {
      console.log('[自动恢复] 开始轮询说话人识别状态...');
      // 定义轮询函数
      const startPolling = () => {
        // 延迟一小段时间再开始轮询，确保状态已经设置完毕
        setTimeout(() => {
          // pollSpeakerDiarizationStatus 会在后面定义，这里用 fetch 实现简单版本
          const poll = async () => {
            try {
              const response = await fetch(`/api/tasks/${speakerDiarizationTaskId}/speaker-diarization/status`);
              const status = await response.json();
              console.log('[自动恢复] 说话人识别状态:', status);

              // 更新进度显示
              setSpeakerDiarizationProgress({
                message: status.message || '处理中...',
                progress: status.progress || 0
              });

              if (status.status === 'completed') {
                // 完成处理
                if (status.speaker_labels) {
                  setSubtitles(prevSubtitles => prevSubtitles.map((subtitle, index) => ({
                    ...subtitle,
                    speaker_id: status.speaker_labels[index] ?? subtitle.speaker_id
                  })));
                }
                if (status.speaker_name_mapping) {
                  setSpeakerNameMapping(status.speaker_name_mapping);
                }
                setIsProcessingSpeakerDiarization(false);
                setSpeakerDiarizationTaskId(null);
                setSpeakerDiarizationProgress({ message: '', progress: 0 });
                setRunningTask(null);

                const durationInfo = status.duration_str ? ` (耗时: ${status.duration_str})` : '';
                setNotificationData({
                  title: '说话人识别完成',
                  message: `已成功完成说话人识别并标记到字幕中。${durationInfo}`,
                  uniqueSpeakers: status.unique_speakers
                });
                setShowNotification(true);
              } else if (status.status === 'failed') {
                setIsProcessingSpeakerDiarization(false);
                setSpeakerDiarizationTaskId(null);
                setSpeakerDiarizationProgress({ message: '', progress: 0 });
                setRunningTask(null);

                setNotificationData({
                  title: '说话人识别失败',
                  message: status.message || '处理过程中发生错误',
                  uniqueSpeakers: undefined
                });
                setShowNotification(true);
              } else {
                // 继续轮询
                setTimeout(poll, 2000);
              }
            } catch (error) {
              console.error('[自动恢复] 轮询失败:', error);
              // 发生错误时继续轮询
              setTimeout(poll, 2000);
            }
          };
          poll();
        }, 500);
      };
      startPolling();
    }
  }, [isProcessingSpeakerDiarization, speakerDiarizationTaskId]);

  // 当检测到有运行中的翻译任务时，自动启动轮询
  useEffect(() => {
    if (isTranslating && taskId && targetLanguage) {
      console.log('[自动恢复] 开始轮询翻译状态...');
      const poll = async () => {
        try {
          const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/translate/status`);
          const status = await response.json();
          console.log('[自动恢复] 翻译状态:', status);

          setTranslationProgress({
            message: status.message || '翻译中...',
            progress: status.progress || 0
          });

          if (status.status === 'completed') {
            setTranslationProgress({ message: '翻译完成', progress: 100 });
            setTargetSrtFilename(status.target_srt_filename || 'translated.srt');
            setIsTranslating(false);
            setRunningTask(null);
            setTimeout(() => setTranslationProgress(null), 2000);
          } else if (status.status === 'failed') {
            setIsTranslating(false);
            setTranslationProgress(null);
            setRunningTask(null);
            alert('翻译失败: ' + (status.message || '未知错误'));
          } else {
            setTimeout(poll, 1000);
          }
        } catch (error) {
          console.error('[自动恢复] 翻译轮询失败:', error);
          setTimeout(poll, 2000);
        }
      };
      setTimeout(poll, 500);
    }
  }, [isTranslating, taskId, targetLanguage]);

  // 当检测到有运行中的语音克隆任务时，自动启动轮询
  useEffect(() => {
    if (isProcessingVoiceCloning && voiceCloningTaskId && targetLanguage) {
      console.log('[自动恢复] 开始轮询语音克隆状态...');
      const poll = async () => {
        try {
          const response = await fetch(`/api/tasks/${voiceCloningTaskId}/languages/${targetLanguage}/voice-cloning/status`);
          const status = await response.json();
          console.log('[自动恢复] 语音克隆状态:', status);

          setVoiceCloningProgress({
            message: status.message || '语音克隆中...',
            progress: status.progress || 0
          });

          if (status.status === 'completed') {
            setVoiceCloningProgress({ message: '语音克隆完成', progress: 100 });
            setIsProcessingVoiceCloning(false);
            setRunningTask(null);
            if (status.cloned_results && Array.isArray(status.cloned_results)) {
              setSubtitles(prevSubtitles => prevSubtitles.map((subtitle, index) => {
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
              }));
            }
            setTimeout(() => setVoiceCloningProgress(null), 2000);
          } else if (status.status === 'failed') {
            setIsProcessingVoiceCloning(false);
            setVoiceCloningProgress(null);
            setVoiceCloningTaskId(null);
            setRunningTask(null);
            alert('语音克隆失败: ' + (status.message || '未知错误'));
          } else {
            setTimeout(poll, 1000);
          }
        } catch (error) {
          console.error('[自动恢复] 语音克隆轮询失败:', error);
          setTimeout(poll, 2000);
        }
      };
      setTimeout(poll, 500);
    }
  }, [isProcessingVoiceCloning, voiceCloningTaskId, targetLanguage]);

  // 当检测到有运行中的视频导出任务时，自动启动轮询
  useEffect(() => {
    if (isExportingVideo && taskId && targetLanguage) {
      console.log('[自动恢复] 开始轮询视频导出状态...');
      const poll = async () => {
        try {
          const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/export-video/status`);
          const status = await response.json();
          console.log('[自动恢复] 视频导出状态:', status);

          setExportVideoProgress({
            message: status.message || '导出中...',
            progress: status.progress || 0
          });

          if (status.status === 'completed' || status.file_exists) {
            setIsExportingVideo(false);
            setExportVideoCompleted(true);
            setExportedVideoDir(status.output_dir || null);
            setExportVideoProgress(null);
            setRunningTask(null);
          } else if (status.status === 'failed') {
            setIsExportingVideo(false);
            setExportVideoProgress(null);
            setRunningTask(null);
            alert('视频导出失败: ' + (status.message || '未知错误'));
          } else {
            setTimeout(poll, 1000);
          }
        } catch (error) {
          console.error('[自动恢复] 视频导出轮询失败:', error);
          setTimeout(poll, 2000);
        }
      };
      setTimeout(poll, 500);
    }
  }, [isExportingVideo, taskId, targetLanguage]);

  const handleProgressBarMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    setIsDraggingProgress(true);

    // 立即跳转到点击位置
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    handleSeek(percentage * duration);
  };

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

  // 加载任务数据（视频、字幕和各阶段状态）
  useEffect(() => {
    const loadTaskData = async () => {
      if (!taskId) return;

      // 重置所有运行状态（进入新任务时清除旧状态）
      console.log('[任务加载] 重置运行状态...');
      setRunningTask(null);
      setGlobalRunningTask(null);
      setIsProcessingSpeakerDiarization(false);
      setSpeakerDiarizationTaskId(null);
      setSpeakerDiarizationProgress({ message: '', progress: 0 });
      setIsTranslating(false);
      setTranslationProgress(null);
      setIsProcessingVoiceCloning(false);
      setVoiceCloningProgress(null);
      setVoiceCloningTaskId(null);
      setIsStitchingAudio(false);
      setIsExportingVideo(false);
      setExportVideoProgress(null);
      // 重置语言相关状态
      setTargetLanguage('');
      setTargetSrtFilename(null);
      setStitchedAudioPath(null);
      setUseStitchedAudio(false);
      setExportVideoCompleted(false);
      setExportedVideoDir(null);

      try {
        console.log('[任务加载] 加载任务数据:', taskId);

        // 首先检查全局是否有正在运行的任务
        try {
          const globalRunningResponse = await axios.get('/api/global-running-task', { timeout: 5000 });
          const globalRunningData = globalRunningResponse.data;
          console.log('[任务加载] 全局运行任务状态:', globalRunningData);

          if (globalRunningData.has_running_task && globalRunningData.running_task) {
            const rt = globalRunningData.running_task;
            setGlobalRunningTask({
              task_id: rt.task_id,
              language: rt.language,
              stage: rt.stage,
              started_at: rt.started_at,
              message: rt.message,
              progress: rt.progress
            });

            // 如果运行的是当前任务
            if (rt.task_id === taskId) {
              setRunningTask({
                task_id: rt.task_id,
                language: rt.language,
                stage: rt.stage,
                started_at: rt.started_at,
                message: rt.message,
                progress: rt.progress
              });
              console.log(`[任务加载] 发现当前任务正在运行: ${rt.language}/${rt.stage}`);

              // 如果是说话人识别正在运行，自动恢复到说话人识别状态
              if (rt.stage === 'speaker_diarization') {
                console.log('[任务加载] 说话人识别正在运行，恢复轮询...');
                setIsProcessingSpeakerDiarization(true);
                setSpeakerDiarizationTaskId(taskId);
              }

              // 如果是其他语言任务正在运行，设置目标语言并恢复状态
              if (rt.language !== 'default' && rt.stage !== 'speaker_diarization') {
                setTargetLanguage(rt.language);

                // 根据阶段设置对应的处理状态
                if (rt.stage === 'translation') {
                  setIsTranslating(true);
                } else if (rt.stage === 'voice_cloning') {
                  setIsProcessingVoiceCloning(true);
                  setVoiceCloningTaskId(taskId);
                } else if (rt.stage === 'stitch') {
                  setIsStitchingAudio(true);
                } else if (rt.stage === 'export') {
                  setIsExportingVideo(true);
                }
              }
            } else {
              console.log(`[任务加载] 其他任务正在运行: ${rt.task_id} - ${rt.language}/${rt.stage}`);
              // 其他任务在运行，当前任务的 runningTask 为 null
              setRunningTask(null);
            }
          } else {
            setGlobalRunningTask(null);
            setRunningTask(null);
          }
        } catch (err) {
          console.log('[任务加载] 获取全局运行任务状态失败:', err);
          setGlobalRunningTask(null);
          setRunningTask(null);
        }

        // 获取任务信息
        const taskResponse = await axios.get(`/api/tasks/${taskId}`, { timeout: 10000 });
        const task = taskResponse.data;

        console.log('[任务加载] 任务数据:', task);
        console.log('[任务加载] language_status:', task.language_status);

        // 加载视频
        if (task.video_filename) {
          const videoPath = `/uploads/${taskId}/input/${task.video_filename}`;
          console.log('[任务加载] 加载视频:', videoPath);

          // 获取视频信息
          const videoInfoResponse = await axios.get(`/api/tasks/${taskId}/video-info`, { timeout: 15000 });
          const videoInfo = videoInfoResponse.data;

          const videoFile: VideoFile = {
            filename: task.video_filename,
            original_name: task.video_original_name,
            size: videoInfo.size || 0,
            video_info: videoInfo
          };

          setCurrentVideo(videoFile);
          setVideos([videoFile]);
        }

        // 加载字幕（如果存在）
        if (task.config?.source_subtitle_filename) {
          console.log('[任务加载] 加载字幕:', task.config.source_subtitle_filename);
          const subtitleResponse = await axios.get(`/api/tasks/${taskId}/subtitle`, { timeout: 10000 });
          setSubtitles(subtitleResponse.data.subtitles || []);
          setSubtitleFilename(task.config.source_subtitle_filename);
        }

        // ========== 恢复说话人识别状态 ==========
        const languageStatus = task.language_status || {};
        const defaultStatus = languageStatus['default'] || {};
        const speakerDiarizationStatus = defaultStatus['speaker_diarization'] || {};

        if (speakerDiarizationStatus.status === 'completed') {
          console.log('[任务加载] 说话人识别已完成，恢复状态...');
          try {
            // 获取说话人识别结果
            const speakerStatusResponse = await axios.get(`/api/tasks/${taskId}/speaker-diarization/status`, { timeout: 10000 });
            const speakerResult = speakerStatusResponse.data;
            console.log('[任务加载] 说话人识别结果:', speakerResult);

            // 如果有说话人标签，更新字幕
            if (speakerResult.speaker_labels && speakerResult.speaker_labels.length > 0) {
              const subtitleResponse = await axios.get(`/api/tasks/${taskId}/subtitle`, { timeout: 10000 });
              const loadedSubtitles = subtitleResponse.data.subtitles || [];
              const updatedSubtitles = loadedSubtitles.map((subtitle: Subtitle, index: number) => {
                const speakerId = index < speakerResult.speaker_labels.length
                  ? speakerResult.speaker_labels[index]
                  : undefined;
                return {
                  ...subtitle,
                  speaker_id: speakerId !== null && speakerId !== undefined ? speakerId : undefined
                };
              });
              setSubtitles(updatedSubtitles);
            }

            // 恢复说话人名称映射
            if (speakerResult.speaker_name_mapping) {
              // 将字符串键转换为数字键
              const numericMapping: {[key: number]: string} = {};
              Object.entries(speakerResult.speaker_name_mapping).forEach(([key, value]) => {
                numericMapping[parseInt(key)] = value as string;
              });
              setSpeakerNameMapping(numericMapping);
              console.log('[任务加载] 恢复说话人名称映射:', numericMapping);
            }
          } catch (err) {
            console.error('[任务加载] 恢复说话人识别状态失败:', err);
          }
        }

        // ========== 恢复各语言的处理状态 ==========
        // 遍历所有语言状态（排除 'default'）
        const languages = Object.keys(languageStatus).filter(lang => lang !== 'default');
        console.log('[任务加载] 发现的语言:', languages);

        for (const language of languages) {
          const langStatus = languageStatus[language] || {};

          // 检查翻译状态
          const translationStatus = langStatus['translation'] || {};
          if (translationStatus.status === 'completed') {
            console.log(`[任务加载] ${language} 翻译已完成`);
            // 如果当前选中的目标语言匹配，设置状态
            // 注意：这里需要用户选择目标语言后才能完整恢复
          }

          // 检查语音克隆状态
          const voiceCloningStatus = langStatus['voice_cloning'] || {};
          if (voiceCloningStatus.status === 'completed') {
            console.log(`[任务加载] ${language} 语音克隆已完成`);
          }

          // 检查拼接状态
          const stitchStatus = langStatus['stitch'] || {};
          if (stitchStatus.status === 'completed') {
            console.log(`[任务加载] ${language} 音频拼接已完成`);
          }
        }

      } catch (error) {
        console.error('[任务加载] 加载任务失败:', error);
      }
    };

    loadTaskData();
  }, [taskId]);

  // 加载默认音色库
  useEffect(() => {
    const loadDefaultVoices = async () => {
      try {
        console.log('[加载默认音色] 开始加载...');
        const response = await fetch('/api/voice-cloning/default-voices');
        console.log('[加载默认音色] 响应状态:', response.status, response.ok);
        if (response.ok) {
          const result = await response.json();
          console.log('[加载默认音色] 返回数据:', result);
          setDefaultVoices(result.voices || []);
          console.log('[加载默认音色] 设置音色数量:', result.voices?.length);
        } else {
          console.error('[加载默认音色] 响应失败:', response.status, response.statusText);
        }
      } catch (error) {
        console.error('加载默认音色库失败:', error);
      }
    };
    loadDefaultVoices();
  }, []);

  // 当目标语言改变时，检查并恢复该语言的翻译、语音克隆和拼接状态
  useEffect(() => {
    // 更新 ref 用于防止竞态条件
    currentLanguageRef.current = targetLanguage;

    const restoreLanguageStatus = async () => {
      if (!taskId || !targetLanguage) return;

      // 保存当前语言，用于检查竞态条件
      const requestedLanguage = targetLanguage;
      console.log(`[语言状态恢复] 开始恢复 ${requestedLanguage} 的状态...`);

      // 重要：当切换语言时，始终先清除所有语言相关的运行状态
      // 这些状态只在当前语言正在执行任务时才应该为 true
      // 如果有运行中的任务且不是当前语言，这些应该为 false，进度由 runningTask 显示
      setIsTranslating(false);
      setTranslationProgress(null);
      setIsProcessingVoiceCloning(false);
      setVoiceCloningProgress(null);
      setIsStitchingAudio(false);
      setIsExportingVideo(false);
      setExportVideoProgress(null);

      // 检查是否有正在运行的任务属于当前切换到的语言
      // 如果有，恢复对应的状态
      try {
        const globalRunningResponse = await axios.get('/api/global-running-task', { timeout: 3000 });
        const globalRunningData = globalRunningResponse.data;

        if (globalRunningData.has_running_task && globalRunningData.running_task) {
          const rt = globalRunningData.running_task;

          // 只有当正在运行的任务是当前任务且是当前语言时，才恢复运行状态
          if (rt.task_id === taskId && rt.language === requestedLanguage) {
            console.log(`[语言状态恢复] 恢复 ${requestedLanguage} 的运行状态: ${rt.stage}`);
            if (rt.stage === 'translation') {
              setIsTranslating(true);
              setTranslationProgress({ message: rt.message || '', progress: rt.progress || 0 });
            } else if (rt.stage === 'voice_cloning') {
              setIsProcessingVoiceCloning(true);
              setVoiceCloningProgress({ message: rt.message || '', progress: rt.progress || 0 });
              setVoiceCloningTaskId(taskId);
            } else if (rt.stage === 'stitch') {
              setIsStitchingAudio(true);
            } else if (rt.stage === 'export') {
              setIsExportingVideo(true);
              setExportVideoProgress({ message: rt.message || '', progress: rt.progress || 0 });
            }
          }
        }
      } catch (err) {
        console.log('[语言状态恢复] 获取全局运行任务状态失败:', err);
      }

      // 重置语言相关的完成状态（会在下面恢复）
      setTargetSrtFilename(null);
      setStitchedAudioPath(null);
      setUseStitchedAudio(false);
      setExportVideoCompleted(false);
      setExportedVideoDir(null);

      // 清除字幕中的克隆信息（会在下面恢复）
      setSubtitles(prevSubtitles => prevSubtitles.map(subtitle => ({
        ...subtitle,
        cloned_audio_path: undefined,
        cloned_speaker_id: undefined,
        actual_start_time: undefined,
        actual_end_time: undefined
      })));

      try {
        // 1. 检查翻译状态
        const translationResponse = await axios.get(
          `/api/tasks/${taskId}/languages/${targetLanguage}/translate/status`,
          { timeout: 8000 }
        );
        const translationStatus = translationResponse.data;
        console.log(`[语言状态恢复] ${targetLanguage} 翻译状态:`, translationStatus);

        if (translationStatus.status === 'completed') {
          console.log(`[语言状态恢复] ${targetLanguage} 翻译已完成`);
          // 设置翻译文件名
          if (translationStatus.target_srt_filename) {
            setTargetSrtFilename(translationStatus.target_srt_filename);
          }
          // 不需要设置 isTranslating 或 translationProgress，因为已完成
        }

        // 2. 检查语音克隆状态
        const voiceCloningResponse = await axios.get(
          `/api/tasks/${taskId}/languages/${targetLanguage}/voice-cloning/status`,
          { timeout: 8000 }
        );
        const voiceCloningStatus = voiceCloningResponse.data;
        console.log(`[语言状态恢复] ${targetLanguage} 语音克隆状态:`, voiceCloningStatus);

        if (voiceCloningStatus.status === 'completed') {
          console.log(`[语言状态恢复] ${targetLanguage} 语音克隆已完成`);
          // 如果有克隆结果，可以加载字幕的克隆音频路径
          if (voiceCloningStatus.cloned_results && voiceCloningStatus.cloned_results.length > 0) {
            console.log(`[语言状态恢复] cloned_results:`, voiceCloningStatus.cloned_results);
            // 更新字幕的克隆音频信息
            setSubtitles(prevSubtitles => {
              return prevSubtitles.map((subtitle, index) => {
                // cloned_results 按 index 排序，找到对应的结果
                const clonedResult = voiceCloningStatus.cloned_results.find(
                  (r: any) => r.index === index
                );
                if (clonedResult && clonedResult.cloned_audio_path) {
                  return {
                    ...subtitle,
                    cloned_audio_path: clonedResult.cloned_audio_path,
                    cloned_speaker_id: clonedResult.speaker_id,
                    target_text: clonedResult.target_text || subtitle.target_text
                  };
                }
                return subtitle;
              });
            });
          }
        }

        // 3. 检查拼接音频状态 - 使用专门的状态 API
        try {
          const stitchStatusResponse = await axios.get(
            `/api/tasks/${taskId}/languages/${targetLanguage}/stitch-audio/status`,
            { timeout: 8000 }
          );
          const stitchStatus = stitchStatusResponse.data;
          console.log(`[语言状态恢复] ${targetLanguage} 拼接状态:`, stitchStatus);

          if (stitchStatus.status === 'completed' || stitchStatus.file_exists) {
            console.log(`[语言状态恢复] ${targetLanguage} 拼接音频已完成`);
            // 添加时间戳防止缓存
            const audioPathWithCache = `${stitchStatus.stitched_audio_path}?t=${Date.now()}`;
            setStitchedAudioPath(audioPathWithCache);
            setUseStitchedAudio(true);

            // 从 cloned_results 恢复字幕的 actual_start_time 和 actual_end_time
            if (stitchStatus.cloned_results && stitchStatus.cloned_results.length > 0) {
              console.log(`[语言状态恢复] 从拼接结果恢复字幕时间轴信息，共 ${stitchStatus.cloned_results.length} 条记录`);
              console.log(`[语言状态恢复] 第一条 cloned_result:`, stitchStatus.cloned_results[0]);
              setSubtitles(prevSubtitles => {
                console.log(`[语言状态恢复] 当前字幕数量: ${prevSubtitles.length}`);
                const updatedSubtitles = prevSubtitles.map((subtitle, index) => {
                  const clonedResult = stitchStatus.cloned_results.find(
                    (r: any) => r.index === index
                  );
                  if (clonedResult) {
                    const updated = {
                      ...subtitle,
                      cloned_audio_path: clonedResult.cloned_audio_path || subtitle.cloned_audio_path,
                      cloned_speaker_id: clonedResult.speaker_id ?? subtitle.cloned_speaker_id,
                      target_text: clonedResult.target_text || subtitle.target_text,
                      actual_start_time: clonedResult.actual_start_time,
                      actual_end_time: clonedResult.actual_end_time
                    };
                    if (index === 0) {
                      console.log(`[语言状态恢复] 更新第一条字幕:`, {
                        before: { start: subtitle.start_time, end: subtitle.end_time, actual_start: subtitle.actual_start_time, actual_end: subtitle.actual_end_time },
                        after: { start: updated.start_time, end: updated.end_time, actual_start: updated.actual_start_time, actual_end: updated.actual_end_time }
                      });
                    }
                    return updated;
                  }
                  return subtitle;
                });
                return updatedSubtitles;
              });
            } else {
              console.log(`[语言状态恢复] 没有找到 cloned_results 数据`);
            }
          } else {
            setStitchedAudioPath(null);
            setUseStitchedAudio(false);
          }
        } catch (err) {
          // API 调用失败
          console.log(`[语言状态恢复] ${targetLanguage} 获取拼接状态失败`);
          setStitchedAudioPath(null);
          setUseStitchedAudio(false);
        }

        // 4. 检查视频导出状态
        try {
          const exportStatusResponse = await axios.get(
            `/api/tasks/${taskId}/languages/${targetLanguage}/export-video/status`,
            { timeout: 8000 }
          );
          const exportStatus = exportStatusResponse.data;
          console.log(`[语言状态恢复] ${targetLanguage} 导出状态:`, exportStatus);

          if (exportStatus.status === 'completed' || exportStatus.file_exists) {
            console.log(`[语言状态恢复] ${targetLanguage} 视频导出已完成`);
            setExportVideoCompleted(true);
            setExportedVideoDir(exportStatus.output_dir || null);
          } else {
            setExportVideoCompleted(false);
            setExportedVideoDir(null);
          }
        } catch (err) {
          console.log(`[语言状态恢复] ${targetLanguage} 获取导出状态失败`);
          setExportVideoCompleted(false);
          setExportedVideoDir(null);
        }

      } catch (error) {
        console.error(`[语言状态恢复] 恢复 ${targetLanguage} 状态失败:`, error);
      }
    };

    restoreLanguageStatus();
  }, [taskId, targetLanguage]);

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

  // 使用时间戳来防止重复触发
  const lastPlayPauseTime = useRef<number>(0);

  const handlePlayPause = () => {
    const now = Date.now();
    const timeSinceLastCall = now - lastPlayPauseTime.current;

    // 防止 200ms 内重复触发
    if (timeSinceLastCall < 200) {
      return;
    }

    lastPlayPauseTime.current = now;

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
      // 清理之前的定时器
      if (speakerDiarizationProgressTimer.current) {
        clearInterval(speakerDiarizationProgressTimer.current);
        speakerDiarizationProgressTimer.current = null;
      }
      lastRealProgress.current = 0;

      setIsProcessingSpeakerDiarization(true);
      setSpeakerDiarizationProgress({ message: '初始化中...', progress: 0 });

      const response = await fetch(`/api/tasks/${taskId}/speaker-diarization`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
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
      const response = await fetch(`/api/tasks/${taskId}/speaker-diarization/status`);

      if (!response.ok) {
        throw new Error(`获取状态失败: ${response.statusText}`);
      }

      const status = await response.json();
      console.log('收到状态:', status);

      const realProgress = status.progress || 0;

      // 如果真实进度大于上次的真实进度，更新并停止模拟
      if (realProgress > lastRealProgress.current) {
        lastRealProgress.current = realProgress;

        // 清除之前的模拟定时器
        if (speakerDiarizationProgressTimer.current) {
          clearInterval(speakerDiarizationProgressTimer.current);
          speakerDiarizationProgressTimer.current = null;
        }

        // 立即更新到真实进度
        setSpeakerDiarizationProgress({
          message: status.message || '处理中...',
          progress: realProgress
        });

        // 如果还没有完成，启动新的模拟进度增长
        if (status.status === 'processing') {
          speakerDiarizationProgressTimer.current = setInterval(() => {
            setSpeakerDiarizationProgress(prev => {
              // 每2秒增加1%，但不超过真实进度的下一个阶段
              const nextProgress = Math.min(prev.progress + 1, 99);
              return {
                ...prev,
                progress: nextProgress
              };
            });
          }, 2000);
        }
      } else {
        // 真实进度没有变化，只更新消息
        setSpeakerDiarizationProgress(prev => ({
          message: status.message || prev.message,
          progress: prev.progress
        }));
      }

      if (status.status === 'completed') {
        // 清除模拟定时器
        if (speakerDiarizationProgressTimer.current) {
          clearInterval(speakerDiarizationProgressTimer.current);
          speakerDiarizationProgressTimer.current = null;
        }
        lastRealProgress.current = 0;
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
        setSpeakerDiarizationProgress({ message: '', progress: 0 }); // 重置进度
        setRunningTask(null); // 清除运行任务状态

        // 显示成功通知，包含处理时间
        const durationInfo = status.duration_str ? ` (耗时: ${status.duration_str})` : '';
        setNotificationData({
          title: '说话人识别完成',
          message: `已成功完成说话人识别并标记到字幕中，你现在可以在字幕详情中查看和编辑说话人信息。${durationInfo}`,
          uniqueSpeakers: status.unique_speakers
        });
        setShowNotification(true);
      } else if (status.status === 'failed') {
        // 清除模拟定时器
        if (speakerDiarizationProgressTimer.current) {
          clearInterval(speakerDiarizationProgressTimer.current);
          speakerDiarizationProgressTimer.current = null;
        }
        lastRealProgress.current = 0;

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
        setSpeakerDiarizationProgress({ message: '', progress: 0 }); // 重置进度
        setRunningTask(null); // 清除运行任务状态
      } else {
        setTimeout(() => pollSpeakerDiarizationStatus(taskId), 2000);
      }
    } catch (error) {
      // 清除模拟定时器
      if (speakerDiarizationProgressTimer.current) {
        clearInterval(speakerDiarizationProgressTimer.current);
        speakerDiarizationProgressTimer.current = null;
      }
      lastRealProgress.current = 0;

      alert('获取说话人识别状态失败: ' + (error as Error).message);
      setIsProcessingSpeakerDiarization(false);
      setSpeakerDiarizationTaskId(null);
    }
  };

  // 处理目标语言srt文件上传（已废弃，保留以防需要）
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

  // 翻译字幕
  const handleTranslateSubtitles = async () => {
    if (!taskId) {
      alert('任务ID不存在');
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

    try {
      // 清理之前的定时器
      if (translationProgressTimer.current) {
        clearInterval(translationProgressTimer.current);
        translationProgressTimer.current = null;
      }
      lastTranslationProgress.current = 0;

      console.log('[启动翻译] 开始调用API, taskId:', taskId, 'language:', targetLanguage);
      setIsTranslating(true);
      setTranslationProgress({ message: '正在准备翻译...', progress: 0 });

      // 使用新的任务系统API (路由在 /api/tasks 下)
      const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/translate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      console.log('[启动翻译] 收到HTTP响应, status:', response.status);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`翻译失败: ${errorText || response.statusText}`);
      }

      const result = await response.json();

      console.log('[启动翻译] 解析JSON完成, 收到响应:', result);

      // 开始轮询翻译状态
      console.log('[启动翻译] 开始轮询, taskId:', taskId, 'language:', targetLanguage);
      pollTranslationStatus(taskId, targetLanguage);
    } catch (error) {
      alert('启动翻译失败: ' + (error as Error).message);
      setIsTranslating(false);
      setTranslationProgress(null);
    }
  };

  // 轮询翻译状态
  const pollTranslationStatus = async (pollTaskId: string, language: string) => {
    console.log('[翻译轮询] 开始轮询, taskId:', pollTaskId, 'language:', language);
    try {
      // 使用新的任务系统API (路由在 /api/tasks 下)
      const response = await fetch(`/api/tasks/${pollTaskId}/languages/${language}/translate/status`);

      if (!response.ok) {
        console.error('[翻译轮询] HTTP错误:', response.status, response.statusText);
        throw new Error(`获取翻译状态失败: ${response.statusText}`);
      }

      const result = await response.json();

      const realProgress = result.progress || 0;

      console.log('[翻译轮询]', {
        status: result.status,
        progress: realProgress,
        message: result.message
      });

      if (result.status === 'processing') {
        // 直接使用真实进度，不再使用模拟增长
        setTranslationProgress({
          message: result.message || '翻译中...',
          progress: realProgress
        });
        console.log('[翻译轮询] 设置进度:', realProgress);

        setTimeout(() => pollTranslationStatus(pollTaskId, language), 1000);
      } else if (result.status === 'completed') {
        // 清除模拟定时器
        if (translationProgressTimer.current) {
          clearInterval(translationProgressTimer.current);
          translationProgressTimer.current = null;
        }
        lastTranslationProgress.current = 0;

        setTranslationProgress({ message: '翻译完成', progress: 100 });
        setTargetSrtFilename(result.target_srt_filename || 'translated.srt');
        setIsTranslating(false);
        setRunningTask(null); // 清除运行任务状态

        // 显示完成通知，包含耗时信息
        const totalItems = result.total_items || 0;
        const elapsedTime = result.elapsed_time || 0;

        let notificationMessage = '字幕翻译已完成';
        if (totalItems > 0 && elapsedTime > 0) {
          const avgTime = (elapsedTime / totalItems).toFixed(2);
          notificationMessage = `已成功翻译 ${totalItems} 条字幕\n总耗时: ${elapsedTime}秒\n平均耗时: ${avgTime}秒/条`;
        }

        setNotificationData({
          title: '翻译完成',
          message: notificationMessage,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);

        setTimeout(() => setTranslationProgress(null), 2000);
      } else if (result.status === 'failed') {
        // 清除模拟定时器
        if (translationProgressTimer.current) {
          clearInterval(translationProgressTimer.current);
          translationProgressTimer.current = null;
        }
        lastTranslationProgress.current = 0;

        throw new Error(result.message || '翻译失败');
      } else if (result.status === 'pending') {
        // 任务还未开始，继续轮询
        setTimeout(() => pollTranslationStatus(pollTaskId, language), 1000);
      }
    } catch (error) {
      console.error('[翻译轮询] 捕获到错误:', error);
      // 清除模拟定时器
      if (translationProgressTimer.current) {
        clearInterval(translationProgressTimer.current);
        translationProgressTimer.current = null;
      }
      lastTranslationProgress.current = 0;

      alert('翻译失败: ' + (error as Error).message);
      setIsTranslating(false);
      setTranslationProgress(null);
      setRunningTask(null); // 清除运行任务状态
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

      // 重置拼接音频状态（因为语音克隆会生成新的音频片段，旧的拼接音频将不再有效）
      setStitchedAudioPath(null);
      setUseStitchedAudio(false);

      // 清除旧的进度定时器并重置进度
      if (voiceCloningProgressTimer.current) {
        clearInterval(voiceCloningProgressTimer.current);
        voiceCloningProgressTimer.current = null;
      }
      lastVoiceCloningProgress.current = 0;
      setVoiceCloningProgress({ message: '正在启动语音克隆...', progress: 0 });

      // 使用任务系统的语音克隆 API
      const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/voice-cloning`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          speaker_voice_mapping: speakerVoiceMapping
        }),
      });

      if (!response.ok) {
        throw new Error(`请求失败: ${response.statusText}`);
      }

      const result = await response.json();
      // 任务系统使用原 taskId，不再生成新的 voiceCloningTaskId
      setVoiceCloningTaskId(taskId || null);

      // 轮询时需要传递 language
      pollVoiceCloningStatus(taskId || '', targetLanguage);
    } catch (error) {
      alert('启动语音克隆失败: ' + (error as Error).message);
      setIsProcessingVoiceCloning(false);
    }
  };

  // 播放克隆音频
  const handlePlayClonedAudio = (audioPath: string) => {
    // 构建完整的音频URL，添加额外的随机参数确保不使用缓存
    const separator = audioPath.includes('?') ? '&' : '?';
    // 新的任务系统路径已经包含 /api 前缀
    const audioUrl = audioPath.startsWith('/api')
      ? `${audioPath}${separator}_=${Date.now()}`
      : `/api/${audioPath}${separator}_=${Date.now()}`;
    const audio = new Audio();
    // 设置不使用缓存
    audio.preload = 'none';
    audio.src = audioUrl;
    audio.load(); // 强制重新加载
    audio.play().catch(error => {
      console.error('播放克隆音频失败:', error);
      alert('播放克隆音频失败');
    });
  };

  // 重新生成单个片段
  const handleRegenerateSegment = async (index: number, newSpeakerId: number, newTargetText?: string) => {
    if (!taskId || !targetLanguage) {
      alert('任务ID或目标语言不存在');
      return;
    }

    try {
      const requestBody: any = {
        segment_index: index,
        new_speaker_id: newSpeakerId
      };

      if (newTargetText) {
        requestBody.new_target_text = newTargetText;
      }

      // 使用新的任务系统 API
      const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/regenerate-segment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
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
              const updates: any = {
                ...subtitle,
                cloned_audio_path: result.cloned_audio_path,
                cloned_speaker_id: result.new_speaker_id
              };
              // 如果有新的译文，也更新
              if (newTargetText) {
                updates.target_text = newTargetText;
              }
              return updates;
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

  // 批量重新生成音色变化的说话人
  const handleRegenerateVoices = async () => {
    if (!voiceCloningTaskId) {
      alert('语音克隆任务ID不存在');
      return;
    }

    try {
      setIsRegeneratingVoices(true);

      const response = await fetch('/api/voice-cloning/regenerate-voices', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          task_id: voiceCloningTaskId,
          speaker_voice_mapping: speakerVoiceMapping
        })
      });

      if (!response.ok) {
        throw new Error(`重新生成失败: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // 更新初始映射
        setInitialSpeakerVoiceMapping({...speakerVoiceMapping});

        // 获取最新的字幕数据
        const statusResponse = await fetch(`/api/voice-cloning/status/${voiceCloningTaskId}`);
        if (statusResponse.ok) {
          const status = await statusResponse.json();

          console.log('[重新生成] 获取到的 cloned_results 数量:', status.cloned_results?.length);
          console.log('[重新生成] 前3个 cloned_results:', status.cloned_results?.slice(0, 3));

          // 更新字幕数据，添加克隆音频路径
          if (status.cloned_results && Array.isArray(status.cloned_results)) {
            const newSubtitles = subtitles.map((subtitle, index) => {
              const clonedResult = status.cloned_results.find((r: any) => r.index === index);
              if (clonedResult) {
                if (index <= 2) {
                  console.log(`[重新生成] 更新片段 ${index}:`, {
                    old: subtitle.cloned_audio_path,
                    new: clonedResult.cloned_audio_path
                  });
                }
                return {
                  ...subtitle,
                  cloned_audio_path: clonedResult.cloned_audio_path,
                  cloned_speaker_id: clonedResult.speaker_id
                };
              }
              return subtitle;
            });

            const updatedCount = newSubtitles.filter((s, i) => s.cloned_audio_path !== subtitles[i].cloned_audio_path).length;
            console.log(`[重新生成] 总共更新了 ${updatedCount} 个片段`);

            setSubtitles(newSubtitles);

            // 验证更新是否生效
            setTimeout(() => {
              console.log('[重新生成] 验证: 片段0的音频路径:', newSubtitles[0]?.cloned_audio_path);
            }, 100);
          }
        }

        // 显示成功通知
        setNotificationData({
          title: '重新生成完成',
          message: `已成功重新生成 ${result.regenerated_count} 个片段，可在字幕详情中播放克隆音频。 (耗时: ${result.duration})`,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);
      }
    } catch (error) {
      console.error('重新生成失败:', error);
      alert('重新生成失败: ' + (error as Error).message);
    } finally {
      setIsRegeneratingVoices(false);
    }
  };

  // 检查音色映射是否有变化
  const hasVoiceMappingChanged = () => {
    const currentKeys = Object.keys(speakerVoiceMapping);
    const initialKeys = Object.keys(initialSpeakerVoiceMapping);

    if (currentKeys.length !== initialKeys.length) return true;

    for (const key of currentKeys) {
      if (speakerVoiceMapping[key] !== initialSpeakerVoiceMapping[key]) {
        return true;
      }
    }

    return false;
  };

  // 拼接克隆音频
  const handleStitchAudio = async () => {
    if (!taskId || !targetLanguage) {
      alert('任务ID或目标语言不存在');
      return;
    }

    try {
      setIsStitchingAudio(true);

      // 使用新的任务系统 API
      const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/stitch-audio`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
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

        // 从返回结果中更新字幕数据（包含 actual_start_time 和 actual_end_time）
        if (result.cloned_results && Array.isArray(result.cloned_results)) {
          setSubtitles(prevSubtitles => {
            return prevSubtitles.map((subtitle, index) => {
              const clonedResult = result.cloned_results.find((r: any) => r.index === index);
              if (clonedResult) {
                return {
                  ...subtitle,
                  target_text: clonedResult.target_text,
                  cloned_audio_path: clonedResult.cloned_audio_path,
                  cloned_speaker_id: clonedResult.speaker_id,
                  actual_start_time: clonedResult.actual_start_time,
                  actual_end_time: clonedResult.actual_end_time
                };
              }
              return subtitle;
            });
          });
        }

        alert(`拼接成功！已生成完整音频，共 ${result.segments_count} 个片段，总时长 ${result.total_duration.toFixed(2)}s${result.replanned_segments > 0 ? `，其中 ${result.replanned_segments} 个片段使用了智能时间轴规划` : ''}`);
        setRunningTask(null); // 清除运行任务状态
      }
    } catch (error) {
      console.error('拼接音频失败:', error);
      alert('拼接音频失败: ' + (error as Error).message);
      setRunningTask(null); // 清除运行任务状态
    } finally {
      setIsStitchingAudio(false);
    }
  };

  // 导出视频
  const handleExportVideo = async () => {
    if (!taskId || !targetLanguage) {
      alert('任务ID或目标语言不存在');
      return;
    }

    if (!stitchedAudioPath) {
      alert('请先完成音频拼接');
      return;
    }

    try {
      setIsExportingVideo(true);
      setExportVideoCompleted(false);
      setExportVideoProgress({ message: '开始导出视频...', progress: 0 });

      const response = await fetch(`/api/tasks/${taskId}/languages/${targetLanguage}/export-video`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({})
      });

      if (!response.ok) {
        throw new Error(`导出视频失败: ${response.statusText}`);
      }

      const result = await response.json();
      console.log('[导出视频] API 响应:', result);

      // 开始轮询导出状态
      pollExportVideoStatus(taskId, targetLanguage);

    } catch (error) {
      console.error('导出视频失败:', error);
      alert('导出视频失败: ' + (error as Error).message);
      setIsExportingVideo(false);
      setExportVideoProgress(null);
    }
  };

  // 轮询导出视频状态
  const pollExportVideoStatus = async (pollTaskId: string, language: string) => {
    try {
      const response = await fetch(`/api/tasks/${pollTaskId}/languages/${language}/export-video/status`);

      if (!response.ok) {
        throw new Error('获取导出状态失败');
      }

      const status = await response.json();
      console.log('[导出视频] 状态:', status);

      setExportVideoProgress({
        message: status.message || '正在导出...',
        progress: status.progress || 0
      });

      if (status.status === 'completed' || status.file_exists) {
        // 导出完成
        setIsExportingVideo(false);
        setExportVideoCompleted(true);
        setExportedVideoDir(status.output_dir || null);
        setExportVideoProgress(null);
        setRunningTask(null); // 清除运行任务状态

        // 清除轮询定时器
        if (exportVideoProgressTimer.current) {
          clearInterval(exportVideoProgressTimer.current);
          exportVideoProgressTimer.current = null;
        }

        alert(`视频导出成功！\n文件名: ${status.output_filename}`);
      } else if (status.status === 'failed') {
        // 导出失败
        setIsExportingVideo(false);
        setExportVideoProgress(null);
        setRunningTask(null); // 清除运行任务状态

        if (exportVideoProgressTimer.current) {
          clearInterval(exportVideoProgressTimer.current);
          exportVideoProgressTimer.current = null;
        }

        alert(`视频导出失败: ${status.message || '未知错误'}`);
      } else {
        // 继续轮询
        if (!exportVideoProgressTimer.current) {
          exportVideoProgressTimer.current = setInterval(() => {
            pollExportVideoStatus(pollTaskId, language);
          }, 1000);
        }
      }
    } catch (error) {
      console.error('[导出视频] 轮询失败:', error);
      // 出错时也继续轮询，避免中断
      if (!exportVideoProgressTimer.current) {
        exportVideoProgressTimer.current = setInterval(() => {
          pollExportVideoStatus(pollTaskId, language);
        }, 2000);
      }
    }
  };

  // 打开导出文件夹
  const handleOpenExportFolder = () => {
    if (exportedVideoDir) {
      // 使用 window.open 打开本地文件夹
      // 注意：这在浏览器中通常不起作用，需要后端支持
      // 我们将使用一个专门的 API 来打开文件夹
      fetch(`/api/open-folder`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: exportedVideoDir })
      }).catch(err => {
        console.error('打开文件夹失败:', err);
        // 如果 API 不存在，显示路径给用户
        alert(`导出文件夹路径:\n${exportedVideoDir}`);
      });
    }
  };

  // 轮询语音克隆状态
  const pollVoiceCloningStatus = async (pollTaskId: string, language: string) => {
    try {
      // 使用任务系统的状态查询 API
      const response = await fetch(`/api/tasks/${pollTaskId}/languages/${language}/voice-cloning/status`);

      if (!response.ok) {
        throw new Error(`获取状态失败: ${response.statusText}`);
      }

      const status = await response.json();
      const realProgress = status.progress || 0;

      console.log('[语音克隆轮询]', {
        status: status.status,
        progress: realProgress,
        message: status.message
      });

      if (status.status === 'processing') {
        // 直接使用真实进度，不再使用模拟增长
        setVoiceCloningProgress({
          message: status.message || '语音克隆中...',
          progress: realProgress
        });
        console.log('[语音克隆轮询] 设置进度:', realProgress);

        setTimeout(() => pollVoiceCloningStatus(pollTaskId, language), 1000);
      } else if (status.status === 'completed') {
        // 清除定时器并重置
        if (voiceCloningProgressTimer.current) {
          clearInterval(voiceCloningProgressTimer.current);
          voiceCloningProgressTimer.current = null;
        }
        lastVoiceCloningProgress.current = 0;

        setVoiceCloningProgress({ message: '语音克隆完成', progress: 100 });
        setIsProcessingVoiceCloning(false);
        setRunningTask(null); // 清除运行任务状态

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

        // 保存初始音色映射，用于后续检测变化
        // 使用后端返回的初始映射（印尼语会自动设置为对应音色）
        if (status.initial_speaker_voice_mapping) {
          setSpeakerVoiceMapping(status.initial_speaker_voice_mapping);
          setInitialSpeakerVoiceMapping(status.initial_speaker_voice_mapping);
        } else {
          setInitialSpeakerVoiceMapping({...speakerVoiceMapping});
        }

        // 显示成功通知，包含处理时间
        const elapsedTime = status.elapsed_time || 0;
        const totalItems = status.total_items || 0;
        let durationInfo = '';
        if (elapsedTime > 0) {
          const avgTime = totalItems > 0 ? (elapsedTime / totalItems).toFixed(2) : '0';
          durationInfo = `\n总耗时: ${elapsedTime.toFixed(1)}秒`;
          if (totalItems > 0) {
            durationInfo += `\n平均耗时: ${avgTime}秒/条`;
          }
        }
        setNotificationData({
          title: '语音克隆完成',
          message: `已成功完成 ${totalItems} 条语音克隆，可在字幕详情中播放克隆音频。${durationInfo}`,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);

        // 2秒后清除进度条
        setTimeout(() => setVoiceCloningProgress(null), 2000);
      } else if (status.status === 'failed') {
        // 清除定时器并重置
        if (voiceCloningProgressTimer.current) {
          clearInterval(voiceCloningProgressTimer.current);
          voiceCloningProgressTimer.current = null;
        }
        lastVoiceCloningProgress.current = 0;

        // 显示失败通知
        const errorMessage = status.message || '处理过程中发生错误，请重试。';
        setNotificationData({
          title: '语音克隆失败',
          message: errorMessage,
          uniqueSpeakers: undefined
        });
        setShowNotification(true);

        setIsProcessingVoiceCloning(false);
        setVoiceCloningProgress(null);
        setVoiceCloningTaskId(null);
        setRunningTask(null); // 清除运行任务状态
      } else {
        setTimeout(() => pollVoiceCloningStatus(pollTaskId, language), 1000);
      }
    } catch (error) {
      // 清除定时器并重置
      if (voiceCloningProgressTimer.current) {
        clearInterval(voiceCloningProgressTimer.current);
        voiceCloningProgressTimer.current = null;
      }
      lastVoiceCloningProgress.current = 0;

      alert('获取语音克隆状态失败: ' + (error as Error).message);
      setIsProcessingVoiceCloning(false);
      setVoiceCloningProgress(null);
      setVoiceCloningTaskId(null);
      setRunningTask(null); // 清除运行任务状态
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
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors flex items-center space-x-2 text-slate-200"
            title="返回任务看板"
          >
            <ArrowLeft size={20} />
            <span className="text-sm font-medium">返回看板</span>
          </button>
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
              disabled={!currentVideo || isProcessingSpeakerDiarization || isProcessingVoiceCloning}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg transition-all duration-200 font-medium ${
                !currentVideo || isProcessingSpeakerDiarization || isProcessingVoiceCloning
                  ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:shadow-lg hover:shadow-blue-500/50'
              }`}
              title={!currentVideo ? '请先上传视频' : isProcessingSpeakerDiarization || isProcessingVoiceCloning ? '处理中，请稍候' : ''}
            >
              {isPlaying ? <Pause size={18} /> : <Play size={18} />}
              <span>{isPlaying ? '暂停' : '播放'}</span>
            </button>

            <button
              onClick={() => handleSeek(0)}
              disabled={!currentVideo || isProcessingSpeakerDiarization || isProcessingVoiceCloning}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg transition-all duration-200 font-medium ${
                !currentVideo || isProcessingSpeakerDiarization || isProcessingVoiceCloning
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  : 'bg-slate-700 text-slate-100 hover:bg-slate-600'
              }`}
              title={!currentVideo ? '请先上传视频' : isProcessingSpeakerDiarization || isProcessingVoiceCloning ? '处理中，请稍候' : ''}
            >
              <RotateCcw size={18} />
              <span>重置</span>
            </button>
          </div>

          {/* 批量处理按钮 */}
          <div className="flex items-center space-x-2">
            {batchStatus?.is_running ? (
              <>
                {/* 运行中状态显示 */}
                <div className="flex items-center space-x-2 bg-blue-900/50 text-blue-200 px-3 py-2 rounded-lg border border-blue-700">
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-sm">
                    {batchStatus.current_language && batchStatus.current_stage
                      ? `${getLanguageNameForBatch(batchStatus.current_language)} - ${getStageNameForBatch(batchStatus.current_stage)}`
                      : '批量处理中...'}
                  </span>
                  {batchStatus.total_stages > 0 && (
                    <span className="text-xs text-blue-300">
                      ({batchStatus.completed_stages}/{batchStatus.total_stages})
                    </span>
                  )}
                </div>
                {/* 停止按钮 */}
                <button
                  onClick={handleStopBatch}
                  disabled={batchStatus.state === 'stopping'}
                  className="flex items-center space-x-2 bg-red-600 hover:bg-red-500 disabled:bg-red-800 disabled:cursor-not-allowed text-white px-4 py-2.5 rounded-lg transition-all duration-200 font-medium"
                  title="停止批量处理"
                >
                  <StopCircle size={18} />
                  <span>{batchStatus.state === 'stopping' ? '停止中...' : '停止'}</span>
                </button>
              </>
            ) : (
              /* 开始批量处理按钮 */
              <button
                onClick={handleStartBatchSingleTask}
                disabled={!currentVideo || isProcessingSpeakerDiarization || isProcessingVoiceCloning || isTranslating || isStitchingAudio || isExportingVideo || !!globalRunningTask || !!runningTask}
                className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg transition-all duration-200 font-medium ${
                  !currentVideo || isProcessingSpeakerDiarization || isProcessingVoiceCloning || isTranslating || isStitchingAudio || isExportingVideo || !!globalRunningTask || !!runningTask
                    ? 'bg-slate-600 text-slate-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-green-600 to-green-500 text-white hover:shadow-lg hover:shadow-green-500/50'
                }`}
                title={!currentVideo ? '请先上传视频' : (isProcessingSpeakerDiarization || isProcessingVoiceCloning || isTranslating || isStitchingAudio || isExportingVideo || globalRunningTask || runningTask) ? '有任务正在运行，请稍候' : '批量处理当前任务（说话人识别→翻译→语音克隆→拼接→导出）'}
              >
                <PlayCircle size={18} />
                <span>批量处理</span>
              </button>
            )}
          </div>

          {/* 简洁时间轴 */}
          {currentVideo && duration > 0 && (
            <div className="flex items-center gap-3 flex-1 max-w-md">
              <span className="text-xs font-mono text-blue-300 min-w-[45px] font-semibold">
                {new Date(currentTime * 1000).toISOString().substr(14, 5)}
              </span>
              <div
                ref={progressBarRef}
                className="flex-1 h-3 bg-slate-700/50 rounded-full cursor-pointer relative group shadow-inner hover:shadow-lg transition-all duration-200"
                onMouseDown={handleProgressBarMouseDown}
                style={{ cursor: isDraggingProgress ? 'grabbing' : 'pointer' }}
              >
                {/* 进度条背景光晕 */}
                <div
                  className="absolute h-full bg-gradient-to-r from-blue-600/20 to-blue-400/20 rounded-full transition-all duration-200"
                  style={{ width: `${(currentTime / duration) * 100}%` }}
                />
                {/* 进度条主体 */}
                <div
                  className="absolute h-full bg-gradient-to-r from-blue-500 via-blue-400 to-blue-500 rounded-full transition-all duration-200 shadow-md"
                  style={{ width: `${(currentTime / duration) * 100}%` }}
                />
                {/* 进度条光泽效果 */}
                <div
                  className="absolute top-0 h-1/2 bg-gradient-to-b from-white/30 to-transparent rounded-full transition-all duration-200"
                  style={{ width: `${(currentTime / duration) * 100}%` }}
                />
                {/* 播放头 */}
                <div
                  className="absolute top-1/2 w-4 h-4 bg-white rounded-full shadow-lg transition-all duration-200 group-hover:scale-125 border-2 border-blue-400"
                  style={{ left: `${(currentTime / duration) * 100}%`, transform: 'translate(-50%, -50%)' }}
                >
                  <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 opacity-50"></div>
                </div>
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
        {/* 左侧边栏（处理进度） */}
        <Sidebar
          speakerDiarizationCompleted={subtitles.some(s => s.speaker_id !== undefined)}
          selectedLanguage={targetLanguage}
          onLanguageSelect={setTargetLanguage}
        />

        {/* 中央区域（新布局：上方播放器+信息，下方时间轴） - 始终显示占位 */}
        <div className="flex-1 flex flex-col overflow-hidden gap-3">
          {/* 上层：字幕详情 + 播放器 */}
          <div className="flex gap-3 flex-1 overflow-hidden">
            {/* 左侧：字幕详细信息列表 (增加宽度比例) - 始终显示 */}
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
                defaultVoices={defaultVoices}
                speakerVoiceMapping={speakerVoiceMapping}
                onSpeakerVoiceMappingChange={setSpeakerVoiceMapping}
                onRegenerateVoices={handleRegenerateVoices}
                hasVoiceMappingChanged={hasVoiceMappingChanged()}
                isRegeneratingVoices={isRegeneratingVoices}
                isProcessingVoiceCloning={isProcessingVoiceCloning}
                isStitchingAudio={isStitchingAudio}
                targetLanguage={targetLanguage}
                hasRunningTask={isProcessingSpeakerDiarization || isProcessingVoiceCloning || isTranslating || isStitchingAudio || isExportingVideo || !!globalRunningTask || !!runningTask}
              />

            {/* 右侧：播放器 + 视频信息 (缩小宽度比例) */}
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
                      src={taskId ? `/uploads/${taskId}/input/${currentVideo.filename}` : `/uploads/${currentVideo.filename}`}
                      key={taskId ? `/uploads/${taskId}/input/${currentVideo.filename}` : `/uploads/${currentVideo.filename}`}
                      onTimeUpdate={handleTimeUpdate}
                      onLoadedMetadata={handleLoadedMetadata}
                      onEnded={() => {
                        setIsPlaying(false);
                        setCurrentTime(0);
                        if (videoRef.current) {
                          videoRef.current.currentTime = 0;
                        }
                      }}
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
                          disabled={isPlaying}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                            isPlaying
                              ? 'opacity-50 cursor-not-allowed'
                              : !useStitchedAudio
                              ? 'bg-blue-600 text-white shadow-md'
                              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-300'
                          }`}
                          title={isPlaying ? '播放时无法切换音频源' : '使用原始音频'}
                        >
                          <Volume2 size={14} />
                          原音频
                        </button>
                        <button
                          onClick={() => setUseStitchedAudio(true)}
                          disabled={isPlaying}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
                            isPlaying
                              ? 'opacity-50 cursor-not-allowed'
                              : useStitchedAudio
                              ? 'bg-emerald-600 text-white shadow-md'
                              : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-slate-300'
                          }`}
                          title={isPlaying ? '播放时无法切换音频源' : '使用克隆音频'}
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

          {/* 下层：时间轴 - 始终显示占位 */}
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl shadow-xl border border-slate-700 p-4 flex-shrink-0">
            <div className="flex items-center space-x-2 mb-3">
              <Zap size={14} className="text-yellow-400" />
              <h3 className="text-sm font-semibold text-slate-100">字幕时间轴</h3>
              {subtitles.length > 0 && (
                <span className="ml-auto text-xs text-slate-400 bg-slate-700/50 px-2 py-0.5 rounded">
                  {subtitles.length} 条
                </span>
              )}
            </div>
            {subtitles.length > 0 ? (
              <SubtitleTimeline
                subtitles={subtitles}
                currentTime={currentTime}
                duration={duration}
                onSeek={handleSeek}
                onStitchAudio={handleStitchAudio}
                stitching={isStitchingAudio}
                isRegeneratingVoices={isRegeneratingVoices}
              />
            ) : (
              <div className="flex items-center justify-center h-32 text-slate-500 text-sm">
                <div className="text-center">
                  <p>上传字幕文件后，时间轴将显示在这里</p>
                </div>
              </div>
            )}
          </div>
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
          onTranslateSubtitles={handleTranslateSubtitles}
          isTranslating={isTranslating}
          translationProgress={translationProgress}
          onRunVoiceCloning={handleRunVoiceCloning}
          isProcessingVoiceCloning={isProcessingVoiceCloning}
          voiceCloningProgress={voiceCloningProgress}
          speakerDiarizationCompleted={subtitles.some(s => s.speaker_id !== undefined)}
          voiceCloningCompleted={subtitles.some(s => s.cloned_audio_path !== undefined)}
          stitchedAudioReady={!!stitchedAudioPath}
          onStitchAudio={handleStitchAudio}
          isStitchingAudio={isStitchingAudio}
          onExportVideo={handleExportVideo}
          isExportingVideo={isExportingVideo}
          exportVideoCompleted={exportVideoCompleted}
          exportVideoProgress={exportVideoProgress}
          exportedVideoDir={exportedVideoDir}
          onOpenExportFolder={handleOpenExportFolder}
          runningTask={runningTask}
          globalRunningTask={globalRunningTask}
        />
      </div>
    </div>
  );
};

export default App;