import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Play, Trash2, Plus, Video, Clock, Loader2, FileText, Upload, PlayCircle, StopCircle, CheckCircle, XCircle, Activity, TrendingUp } from 'lucide-react';

interface StageStatus {
  status: string;
  progress: number;
  message?: string;
}

interface LanguageStageStatus {
  speaker_diarization?: StageStatus;
  translation?: StageStatus;
  voice_cloning?: StageStatus;
  stitch?: StageStatus;
  export?: StageStatus;
}

interface Task {
  id: number;
  task_id: string;
  video_filename: string;
  video_original_name: string;
  status: string;
  language_status: Record<string, LanguageStageStatus>;
  config: { target_languages: string[] };
  created_at: string;
}

// 运行任务信息接口
interface RunningTaskInfo {
  task_id: string;
  language: string;
  stage: string;
  started_at: string;
  message?: string;
  progress?: number;
}

// 队列中的任务信息
interface QueuedTaskInfo {
  task_id: string;
  languages: string[];
  added_at: string;
}

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
  queued_tasks: QueuedTaskInfo[];
  queued_count: number;
}

const TaskDashboard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [subtitleFile, setSubtitleFile] = useState<File | null>(null);
  const [runningTasks, setRunningTasks] = useState<Record<string, RunningTaskInfo>>({});
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const navigate = useNavigate();

  // 用于追踪是否曾经成功加载过任务
  const hasLoadedRef = useRef(false);
  // 用于追踪重试次数
  const retryCountRef = useRef(0);

  useEffect(() => {
    fetchTasks();
    fetchRunningTasks();
    fetchBatchStatus();

    // 每3秒刷新一次运行任务状态、任务列表和批量处理状态
    const runningTasksInterval = setInterval(fetchRunningTasks, 3000);
    const tasksInterval = setInterval(() => {
      // 静默刷新任务列表，不设置 loading 状态
      fetchTasksSilent();
    }, 3000);
    const batchStatusInterval = setInterval(fetchBatchStatus, 2000);

    return () => {
      clearInterval(runningTasksInterval);
      clearInterval(tasksInterval);
      clearInterval(batchStatusInterval);
    };
  }, []);

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/tasks/', { timeout: 10000 });
      setTasks(response.data || []);
      hasLoadedRef.current = true;
      retryCountRef.current = 0;
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      // 如果首次加载失败，尝试重试
      if (!hasLoadedRef.current && retryCountRef.current < 3) {
        retryCountRef.current++;
        console.log(`Retrying fetchTasks (attempt ${retryCountRef.current})...`);
        setTimeout(fetchTasks, 1000);
        return; // 不设置 loading 为 false，继续重试
      }
    } finally {
      setLoading(false);
    }
  };

  // 静默刷新任务列表（不显示loading状态）
  const fetchTasksSilent = async () => {
    try {
      const response = await axios.get('/api/tasks/', { timeout: 10000 });
      // 无论返回什么都更新任务列表（包括空数组）
      if (response.data !== undefined) {
        setTasks(response.data || []);
        hasLoadedRef.current = true;
      }
    } catch (error) {
      // 静默失败，不做任何处理
      console.log('Silent fetch tasks failed:', error);
    }
  };

  const fetchRunningTasks = async () => {
    try {
      const response = await axios.get('/api/running-tasks', { timeout: 5000 });
      setRunningTasks(response.data.running_tasks || {});
    } catch (error) {
      console.log('Failed to fetch running tasks (API may not be available yet):', error);
    }
  };

  // 获取批量处理状态
  const fetchBatchStatus = async () => {
    try {
      const response = await axios.get('/api/batch/status', { timeout: 5000 });
      setBatchStatus(response.data);
    } catch (error) {
      // 静默失败
      console.log('Failed to fetch batch status:', error);
    }
  };

  // 启动批量处理所有任务
  const handleStartBatchAll = async () => {
    if (tasks.length === 0) {
      alert('没有任务可以处理');
      return;
    }

    try {
      const response = await axios.post('/api/batch/start', {
        task_ids: tasks.map(t => t.task_id),
        languages: ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id']
      }, { timeout: 10000 });

      if (response.data.success) {
        console.log('批量处理已启动:', response.data.message);
        fetchBatchStatus();
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
        fetchBatchStatus();
      }
    } catch (error: any) {
      alert('停止批量处理失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 添加任务到批量处理队列
  const handleAddToQueue = async (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // 防止触发打开任务

    try {
      const response = await axios.post(`/api/batch/queue/${taskId}`, {
        languages: ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id']
      }, { timeout: 8000 });

      if (response.data.success) {
        console.log(`任务 ${taskId} 已添加到队列`);
        fetchBatchStatus();
      }
    } catch (error: any) {
      if (error.response?.status === 409) {
        alert(error.response?.data?.detail || '无法添加任务到队列');
      } else {
        alert('添加到队列失败: ' + (error.response?.data?.detail || error.message));
      }
    }
  };

  // 从队列中移除任务
  const handleRemoveFromQueue = async (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation();

    try {
      const response = await axios.delete(`/api/batch/queue/${taskId}`, { timeout: 8000 });
      if (response.data.success) {
        console.log(`任务 ${taskId} 已从队列移除`);
        fetchBatchStatus();
      }
    } catch (error: any) {
      alert('移除失败: ' + (error.response?.data?.detail || error.message));
    }
  };

  // 检查任务是否在队列中
  const isTaskInQueue = (taskId: string): boolean => {
    return batchStatus?.queued_tasks?.some(t => t.task_id === taskId) || false;
  };

  // 检查任务是否正在处理
  const isTaskProcessing = (taskId: string): boolean => {
    return batchStatus?.current_task_id === taskId;
  };

  // 获取阶段的中文名称
  const getStageName = (stage: string): string => {
    const stageNames: Record<string, string> = {
      'speaker_diarization': '说话人识别',
      'translation': '翻译',
      'voice_cloning': '语音克隆',
      'stitch': '音频拼接',
      'export': '视频导出'
    };
    return stageNames[stage] || stage;
  };

  // 获取语言的中文名称
  const getLanguageName = (language: string): string => {
    if (language === 'default') return '';
    const languageNames: Record<string, string> = {
      'en': '英语',
      'ko': '韩语',
      'ja': '日语',
      'fr': '法语',
      'de': '德语',
      'es': '西班牙语',
      'id': '印尼语'
    };
    return languageNames[language] || language;
  };

  const handleUploadSubmit = async () => {
    if (!videoFile) {
      alert('请选择视频文件');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('video', videoFile);
    if (subtitleFile) {
      formData.append('subtitle', subtitleFile);
    }

    try {
      const response = await axios.post('/api/tasks/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000  // 5分钟超时，视频上传可能较慢
      });

      // 新任务添加到列表最后面
      setTasks([...tasks, response.data]);
      setShowUploadModal(false);
      setVideoFile(null);
      setSubtitleFile(null);
      // 留在看板页面，不跳转到编辑器
    } catch (error) {
      console.error('Upload failed:', error);
      alert('上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (taskId: string, event: React.MouseEvent) => {
    event.stopPropagation(); // 防止触发打开任务

    if (!confirm('确定删除此任务？所有相关文件将被删除。')) return;

    try {
      await axios.delete(`/api/tasks/${taskId}`, { timeout: 30000 });
      setTasks(tasks.filter(t => t.task_id !== taskId));
    } catch (error) {
      console.error('Delete failed:', error);
      alert('删除失败，请重试');
    }
  };

  // 判断是否可以启动批量处理
  const canStartBatch = tasks.length > 0 && !batchStatus?.is_running;
  const isBatchRunning = batchStatus?.is_running || false;
  const isBatchStopping = batchStatus?.state === 'stopping';

  // 计算任务统计（基于所有语言的所有环节状态）
  const taskStats = React.useMemo(() => {
    const total = tasks.length;
    const languages = ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id'];
    const languageStages = ['translation', 'voice_cloning', 'stitch', 'export'];

    // 辅助函数：检查任务是否所有语言的所有环节都完成
    const isTaskFullyCompleted = (task: Task): boolean => {
      const langStatus = task.language_status || {};

      // 1. 检查说话人识别是否完成（在 'default' 或第一个语言下）
      const defaultLangData = langStatus['default'] || langStatus[languages[0]];
      if (!defaultLangData?.speaker_diarization || defaultLangData.speaker_diarization.status !== 'completed') {
        return false;
      }

      // 2. 检查所有语言的所有阶段是否完成
      return languages.every(lang => {
        const langData = langStatus[lang];
        if (!langData) return false;
        return languageStages.every(stage => {
          const stageData = langData[stage as keyof LanguageStageStatus];
          return stageData?.status === 'completed';
        });
      });
    };

    // 辅助函数：检查任务是否有任何环节失败
    const isTaskFailed = (task: Task): boolean => {
      const langStatus = task.language_status || {};

      // 1. 检查说话人识别是否失败
      const defaultLangData = langStatus['default'] || langStatus[languages[0]];
      if (defaultLangData?.speaker_diarization?.status === 'failed') {
        return true;
      }

      // 2. 检查所有语言的所有阶段是否有失败
      return languages.some(lang => {
        const langData = langStatus[lang];
        if (!langData) return false;
        return languageStages.some(stage => {
          const stageData = langData[stage as keyof LanguageStageStatus];
          return stageData?.status === 'failed';
        });
      });
    };

    // 1. "失败" = 有任何一个环节失败的任务
    const failed = tasks.filter(isTaskFailed).length;

    // 2. "已完成" = 所有7种语言的所有环节都完成 && 没有任何失败环节的任务
    const completed = tasks.filter(t => isTaskFullyCompleted(t) && !isTaskFailed(t)).length;

    // 3. "正在运行" = 当前正在处理的任务（batchStatus.current_task_id存在且不在queued_tasks中）
    const actuallyProcessing = batchStatus?.current_task_id &&
      !batchStatus?.queued_tasks?.some(qt => qt.task_id === batchStatus.current_task_id) ? 1 : 0;

    // 4. "待处理（队列中）" = 在批量处理队列中等待的任务数
    const pending = batchStatus?.queued_count || 0;

    // 5. "进行中" = 正在处理的任务 + 队列中等待的任务
    const processing = actuallyProcessing + pending;

    // 6. "完成率" = 已完成任务数 / 总任务数
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;

    // 检查是否有任务真正在运行（用于控制loading动画）
    const hasRunningTasks = actuallyProcessing > 0 || isBatchRunning;

    return { total, processing, completed, failed, pending, actuallyProcessing, hasRunningTasks, completionRate };
  }, [tasks, runningTasks, isBatchRunning, batchStatus]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Ascendia 品牌头部 */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-blue-600 rounded-2xl blur-xl opacity-50 animate-pulse"></div>
                <div className="relative p-4 bg-gradient-to-br from-purple-600 via-blue-600 to-cyan-600 rounded-2xl shadow-2xl">
                  <Video size={36} className="text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 via-blue-400 to-cyan-400">
                  Ascendia
                </h1>
                <p className="text-slate-400 text-sm mt-1 font-medium">AI 驱动的智能视频编辑平台</p>
              </div>
            </div>

          <div className="flex items-center gap-3">
            {/* 批量处理按钮 */}
            {!isBatchRunning ? (
              <button
                onClick={handleStartBatchAll}
                disabled={!canStartBatch || loading}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  canStartBatch && !loading
                    ? 'bg-gradient-to-r from-green-600 to-emerald-600 text-white hover:shadow-xl hover:shadow-green-500/40 hover:-translate-y-0.5 border border-green-500/30'
                    : 'bg-slate-700/50 text-slate-400 cursor-not-allowed border border-slate-600'
                }`}
                title={loading ? '正在加载任务列表' : !canStartBatch ? '没有可处理的任务' : '批量处理所有任务'}
              >
                <PlayCircle size={20} />
                <span>批量处理</span>
              </button>
            ) : (
              <button
                onClick={handleStopBatch}
                disabled={isBatchStopping || loading}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${
                  isBatchStopping || loading
                    ? 'bg-slate-700/50 text-slate-400 cursor-not-allowed border border-slate-600'
                    : 'bg-gradient-to-r from-red-600 to-rose-600 text-white hover:shadow-xl hover:shadow-red-500/40 hover:-translate-y-0.5 border border-red-500/30'
                }`}
              >
                {isBatchStopping ? (
                  <>
                    <Loader2 size={20} className="animate-spin" />
                    <span>正在停止...</span>
                  </>
                ) : (
                  <>
                    <StopCircle size={20} />
                    <span>停止处理</span>
                  </>
                )}
              </button>
            )}

            <button
              onClick={() => setShowUploadModal(true)}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold transition-all ${
                uploading || loading
                  ? 'bg-slate-700/50 text-slate-400 cursor-not-allowed border border-slate-600'
                  : 'bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-600 text-white hover:shadow-xl hover:shadow-purple-500/40 hover:-translate-y-0.5 border border-purple-500/30'
              }`}
              disabled={uploading || loading}
              title={uploading ? '上传中' : loading ? '加载中' : '创建新任务'}
            >
              <Plus size={20} />
              <span>创建新任务</span>
            </button>
          </div>
        </div>
        </div>

        {/* 任务统计看板 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
          {/* 总任务数 */}
          <div className="bg-gradient-to-br from-slate-800/80 to-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 hover:border-slate-600 transition-all hover:shadow-lg hover:shadow-slate-500/10">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-gradient-to-br from-slate-700 to-slate-600 rounded-lg">
                <Video size={20} className="text-slate-300" />
              </div>
              <TrendingUp size={16} className="text-slate-400" />
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold text-white">{taskStats.total}</p>
              <p className="text-xs text-slate-400 mt-1">总任务数</p>
            </div>
          </div>

          {/* 进行中 */}
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 backdrop-blur-sm border border-blue-500/30 rounded-xl p-6 hover:border-blue-400/50 transition-all hover:shadow-lg hover:shadow-blue-500/20">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-gradient-to-br from-blue-600 to-blue-500 rounded-lg">
                <Activity size={20} className="text-white" />
              </div>
              {/* 只有真正有任务在运行时才显示loading动画 */}
              {taskStats.hasRunningTasks && (
                <Loader2 size={16} className="text-blue-400 animate-spin" />
              )}
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold text-blue-400">{taskStats.processing}</p>
              <p className="text-xs text-blue-300 mt-1">进行中 {taskStats.pending > 0 && `(${taskStats.actuallyProcessing}运行 + ${taskStats.pending}排队)`}</p>
            </div>
          </div>

          {/* 已完成 */}
          <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 backdrop-blur-sm border border-green-500/30 rounded-xl p-6 hover:border-green-400/50 transition-all hover:shadow-lg hover:shadow-green-500/20">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-gradient-to-br from-green-600 to-green-500 rounded-lg">
                <CheckCircle size={20} className="text-white" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold text-green-400">{taskStats.completed}</p>
              <p className="text-xs text-green-300 mt-1">已完成</p>
            </div>
            {taskStats.total > 0 && (
              <div className="mt-3 pt-3 border-t border-green-500/20">
                <p className="text-xs text-green-400">
                  完成率: {taskStats.completionRate}%
                </p>
              </div>
            )}
          </div>

          {/* 失败 */}
          <div className="bg-gradient-to-br from-red-500/10 to-red-600/5 backdrop-blur-sm border border-red-500/30 rounded-xl p-6 hover:border-red-400/50 transition-all hover:shadow-lg hover:shadow-red-500/20">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-gradient-to-br from-red-600 to-red-500 rounded-lg">
                <XCircle size={20} className="text-white" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold text-red-400">{taskStats.failed}</p>
              <p className="text-xs text-red-300 mt-1">失败</p>
            </div>
          </div>

          {/* 待处理 */}
          <div className="bg-gradient-to-br from-yellow-500/10 to-yellow-600/5 backdrop-blur-sm border border-yellow-500/30 rounded-xl p-6 hover:border-yellow-400/50 transition-all hover:shadow-lg hover:shadow-yellow-500/20">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-gradient-to-br from-yellow-600 to-yellow-500 rounded-lg">
                <Clock size={20} className="text-white" />
              </div>
            </div>
            <div className="mt-4">
              <p className="text-3xl font-bold text-yellow-400">{taskStats.pending}</p>
              <p className="text-xs text-yellow-300 mt-1">待处理</p>
            </div>
          </div>
        </div>

        {/* 批量处理状态提示 */}
        {isBatchRunning && batchStatus && (
          <div className={`mb-6 p-4 rounded-lg ${
            isBatchStopping
              ? 'bg-yellow-500/10 border border-yellow-500/30'
              : 'bg-blue-500/10 border border-blue-500/30'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Loader2 size={20} className={`animate-spin ${isBatchStopping ? 'text-yellow-400' : 'text-blue-400'}`} />
                <div>
                  <h3 className={`text-sm font-bold ${isBatchStopping ? 'text-yellow-300' : 'text-blue-300'}`}>
                    {isBatchStopping ? '正在停止...' : '批量处理中'}
                  </h3>
                  <p className={`text-xs mt-1 ${isBatchStopping ? 'text-yellow-200' : 'text-blue-200'}`}>
                    {batchStatus.message}
                    {batchStatus.current_language && batchStatus.current_language !== 'default' && (
                      <span> ({getLanguageName(batchStatus.current_language)})</span>
                    )}
                  </p>
                  {isBatchStopping && (
                    <p className="text-xs text-yellow-300 mt-1">
                      当前阶段完成后将停止批量处理
                    </p>
                  )}
                </div>
              </div>
              <div className="text-right">
                <p className={`text-sm ${isBatchStopping ? 'text-yellow-300' : 'text-blue-300'}`}>
                  任务: {batchStatus.current_task_id ? batchStatus.completed_tasks + 1 : batchStatus.completed_tasks}/{batchStatus.total_tasks}
                  {batchStatus.queued_count > 0 && (
                    <span className="text-green-400 ml-2">(+{batchStatus.queued_count} 队列中)</span>
                  )}
                </p>
                <p className={`text-xs ${isBatchStopping ? 'text-yellow-200' : 'text-blue-200'}`}>
                  阶段: {batchStatus.completed_stages}/{batchStatus.total_stages}
                </p>
              </div>
            </div>
            {batchStatus.total_stages > 0 && (
              <div className="mt-3">
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${
                      isBatchStopping
                        ? 'bg-gradient-to-r from-yellow-500 to-yellow-400'
                        : 'bg-gradient-to-r from-blue-500 to-blue-400'
                    }`}
                    style={{ width: `${(batchStatus.completed_stages / batchStatus.total_stages) * 100}%` }}
                  />
                </div>
              </div>
            )}
            {/* 队列中的任务列表 */}
            {batchStatus.queued_count > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-600">
                <p className="text-xs text-green-400 mb-2">等待队列中的任务:</p>
                <div className="flex flex-wrap gap-2">
                  {batchStatus.queued_tasks.map((queuedTask) => (
                    <span
                      key={queuedTask.task_id}
                      className="inline-flex items-center gap-1 text-xs px-2 py-1 bg-green-500/20 text-green-300 rounded"
                    >
                      {queuedTask.task_id.slice(-8)}
                      <button
                        onClick={(e) => handleRemoveFromQueue(queuedTask.task_id, e)}
                        className="hover:text-red-400 ml-1"
                        title="从队列移除"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 任务网格 */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 size={48} className="animate-spin text-blue-400" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-96 text-slate-400">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-gradient-to-r from-purple-600/20 to-blue-600/20 rounded-full blur-2xl"></div>
              <div className="relative p-6 bg-gradient-to-br from-slate-800 to-slate-700 rounded-full border border-slate-600">
                <Video size={64} className="text-slate-400" />
              </div>
            </div>
            <h3 className="text-2xl font-bold text-slate-300 mb-2">还没有任务</h3>
            <p className="text-slate-400 text-center max-w-md">
              开始您的 AI 视频编辑之旅<br/>
              点击右上角"创建新任务"按钮上传视频
            </p>
            <div className="mt-8 flex items-center gap-2 text-xs text-slate-500">
              <div className="w-2 h-2 rounded-full bg-gradient-to-r from-purple-500 to-blue-500 animate-pulse"></div>
              <span>支持多语言翻译 • 智能语音克隆 • 自动视频导出</span>
            </div>
          </div>
        ) : (
          <div className="max-h-[calc(100vh-280px)] overflow-y-auto pr-2">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" style={{ paddingBottom: '600px' }}>
              {tasks.map(task => (
                <TaskCard
                  key={task.task_id}
                  task={task}
                  onOpen={() => navigate(`/tasks/${task.task_id}`)}
                  onDelete={(e) => handleDelete(task.task_id, e)}
                  onAddToQueue={(e) => handleAddToQueue(task.task_id, e)}
                  onRemoveFromQueue={(e) => handleRemoveFromQueue(task.task_id, e)}
                  runningTask={runningTasks[task.task_id] || null}
                  getStageName={getStageName}
                  getLanguageName={getLanguageName}
                  isInQueue={isTaskInQueue(task.task_id)}
                  isProcessing={isTaskProcessing(task.task_id)}
                  loading={loading}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 上传模态框 */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn" onClick={() => !uploading && setShowUploadModal(false)}>
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl p-8 max-w-md w-full mx-4 border border-slate-700 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg">
                <Plus size={24} className="text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white">创建新任务</h2>
            </div>

            {/* 视频文件上传 */}
            <div className="mb-6">
              <label className="block text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <Video size={16} className="text-purple-400" />
                视频文件 <span className="text-red-400">*</span>
              </label>
              <label className={`group flex items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                videoFile
                  ? 'border-purple-500 bg-purple-500/10'
                  : 'border-slate-600 bg-slate-700/30 hover:border-purple-500 hover:bg-purple-500/5'
              }`}>
                <div className="text-center">
                  {videoFile ? (
                    <>
                      <div className="p-3 bg-gradient-to-br from-purple-600 to-blue-600 rounded-xl inline-block mb-3">
                        <Video className="text-white" size={32} />
                      </div>
                      <p className="text-sm text-white font-semibold">{videoFile.name}</p>
                      <p className="text-xs text-purple-300 mt-1">{(videoFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </>
                  ) : (
                    <>
                      <Upload className="mx-auto mb-3 text-slate-400 group-hover:text-purple-400 transition-colors" size={36} />
                      <p className="text-sm text-slate-300 font-medium group-hover:text-white transition-colors">点击选择视频文件</p>
                      <p className="text-xs text-slate-500 mt-2">支持 MP4, MOV, AVI, MKV</p>
                    </>
                  )}
                </div>
                <input
                  type="file"
                  accept="video/mp4,video/mov,video/avi,video/mkv"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && setVideoFile(e.target.files[0])}
                  disabled={uploading}
                />
              </label>
            </div>

            {/* 字幕文件上传 (可选) */}
            <div className="mb-8">
              <label className="block text-sm font-semibold text-slate-300 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-blue-400" />
                字幕文件 <span className="text-slate-500 font-normal">(可选)</span>
              </label>
              <label className={`group flex items-center justify-center w-full px-4 py-6 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                subtitleFile
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-slate-600 bg-slate-700/30 hover:border-blue-500 hover:bg-blue-500/5'
              }`}>
                <div className="text-center">
                  {subtitleFile ? (
                    <>
                      <div className="p-2.5 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-lg inline-block mb-2">
                        <FileText className="text-white" size={24} />
                      </div>
                      <p className="text-sm text-white font-semibold">{subtitleFile.name}</p>
                      <p className="text-xs text-blue-300 mt-1">{(subtitleFile.size / 1024).toFixed(2)} KB</p>
                    </>
                  ) : (
                    <>
                      <FileText className="mx-auto mb-2 text-slate-400 group-hover:text-blue-400 transition-colors" size={32} />
                      <p className="text-sm text-slate-300 font-medium group-hover:text-white transition-colors">点击选择字幕文件</p>
                      <p className="text-xs text-slate-500 mt-1">支持 SRT 格式</p>
                    </>
                  )}
                </div>
                <input
                  type="file"
                  accept=".srt"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && setSubtitleFile(e.target.files[0])}
                  disabled={uploading}
                />
              </label>
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setVideoFile(null);
                  setSubtitleFile(null);
                }}
                className="flex-1 px-5 py-3 bg-slate-700/50 text-slate-300 rounded-xl hover:bg-slate-600/50 transition-all font-semibold border border-slate-600"
                disabled={uploading}
              >
                取消
              </button>
              <button
                onClick={handleUploadSubmit}
                className="flex-1 px-5 py-3 bg-gradient-to-r from-purple-600 via-blue-600 to-cyan-600 text-white rounded-xl hover:shadow-xl hover:shadow-purple-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed font-semibold"
                disabled={uploading || !videoFile}
              >
                {uploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 size={18} className="animate-spin" />
                    上传中...
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-2">
                    <Upload size={18} />
                    创建任务
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

interface TaskCardProps {
  task: Task;
  onOpen: () => void;
  onDelete: (e: React.MouseEvent) => void;
  onAddToQueue: (e: React.MouseEvent) => void;
  onRemoveFromQueue: (e: React.MouseEvent) => void;
  runningTask: RunningTaskInfo | null;
  getStageName: (stage: string) => string;
  getLanguageName: (language: string) => string;
  isInQueue: boolean;
  isProcessing: boolean;
  loading: boolean;
}

const TaskCard: React.FC<TaskCardProps> = ({
  task, onOpen, onDelete, onAddToQueue, onRemoveFromQueue,
  runningTask, getStageName, getLanguageName,
  isInQueue, isProcessing, loading
}) => {
  const languages = ['en', 'ko', 'ja', 'fr', 'de', 'es', 'id'];
  const languageNames: Record<string, string> = {
    en: '英语', ko: '韩语', ja: '日语', fr: '法语',
    de: '德语', es: '西语', id: '印尼语'
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 计算某个语言的综合进度和状态
  const getLanguageOverallStatus = (lang: string): { status: string; progress: number } => {
    const langStatus = task.language_status[lang];
    if (!langStatus) return { status: 'idle', progress: 0 };

    const stages = ['translation', 'voice_cloning', 'stitch'] as const;
    let completedStages = 0;
    let processingProgress = 0;
    let hasProcessing = false;
    let hasFailed = false;

    stages.forEach(stage => {
      const stageData = langStatus[stage];
      if (stageData?.status === 'completed') {
        completedStages++;
      } else if (stageData?.status === 'processing') {
        hasProcessing = true;
        processingProgress = stageData.progress || 0;
      } else if (stageData?.status === 'failed') {
        hasFailed = true;
      }
    });

    if (hasFailed) return { status: 'failed', progress: Math.round((completedStages / stages.length) * 100) };
    if (completedStages === stages.length) return { status: 'completed', progress: 100 };
    if (hasProcessing) {
      const baseProgress = (completedStages / stages.length) * 100;
      const currentStageProgress = (processingProgress / stages.length);
      return { status: 'processing', progress: Math.round(baseProgress + currentStageProgress) };
    }
    if (completedStages > 0) return { status: 'partial', progress: Math.round((completedStages / stages.length) * 100) };
    return { status: 'idle', progress: 0 };
  };

  // 检查说话人识别状态
  const speakerDiarizationStatus = task.language_status['default']?.speaker_diarization;
  const isSpeakerDiarizationCompleted = speakerDiarizationStatus?.status === 'completed';

  return (
    <div
      onClick={onOpen}
      className="group relative bg-gradient-to-br from-slate-800/90 to-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 hover:border-purple-500/50 transition-all cursor-pointer hover:shadow-2xl hover:shadow-purple-500/30 hover:-translate-y-1"
    >
      {/* 背景渐变光晕 */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-500/0 via-blue-500/0 to-cyan-500/0 group-hover:from-purple-500/5 group-hover:via-blue-500/5 group-hover:to-cyan-500/5 rounded-xl transition-all duration-500"></div>

      <div className="relative z-10">
      {/* 视频信息 */}
      <div className="mb-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="p-2.5 bg-gradient-to-br from-purple-600/20 to-blue-600/20 rounded-lg border border-purple-500/30">
            <Video size={20} className="text-purple-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-bold truncate text-lg group-hover:text-purple-300 transition-colors">
              {task.video_original_name}
            </h3>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
              <Clock size={12} />
              <span>{formatDate(task.created_at)}</span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`text-xs px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 ${
            task.status === 'completed' ? 'bg-gradient-to-r from-green-500/20 to-green-600/20 text-green-400 border border-green-500/30' :
            task.status === 'processing' ? 'bg-gradient-to-r from-blue-500/20 to-blue-600/20 text-blue-400 border border-blue-500/30' :
            task.status === 'failed' ? 'bg-gradient-to-r from-red-500/20 to-red-600/20 text-red-400 border border-red-500/30' :
            'bg-gradient-to-r from-slate-500/20 to-slate-600/20 text-slate-400 border border-slate-500/30'
          }`}>
            {task.status === 'completed' ? <><CheckCircle size={12} />已完成</> :
             task.status === 'processing' ? <><Activity size={12} />处理中</> :
             task.status === 'failed' ? <><XCircle size={12} />失败</> : '待处理'}
          </span>
          {isSpeakerDiarizationCompleted && (
            <span className="text-xs px-3 py-1.5 rounded-lg font-semibold bg-gradient-to-r from-purple-500/20 to-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center gap-1">
              <CheckCircle size={12} />
              说话人识别
            </span>
          )}
        </div>

        {/* 运行任务指示 */}
        {runningTask && (
          <div className="mt-3 p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
            <div className="flex items-center gap-2">
              <Loader2 size={14} className="text-blue-400 animate-spin" />
              <span className="text-xs text-blue-300 font-medium">
                正在执行: {getStageName(runningTask.stage)}
                {runningTask.language !== 'default' && ` (${getLanguageName(runningTask.language)})`}
              </span>
            </div>
            {runningTask.progress !== undefined && runningTask.progress > 0 && (
              <div className="mt-2">
                <div className="w-full bg-slate-700 rounded-full h-1">
                  <div
                    className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                    style={{ width: `${runningTask.progress}%` }}
                  />
                </div>
                <p className="text-xs text-blue-300 text-right mt-1">{runningTask.progress}%</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 语言进度 */}
      <div className="space-y-2 mb-4">
        {languages.map(lang => {
          const { status, progress } = getLanguageOverallStatus(lang);

          return (
            <div key={lang} className="flex items-center gap-2">
              <span className="text-xs text-slate-400 w-12">{languageNames[lang]}</span>
              <div className="flex-1 bg-slate-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    status === 'completed' ? 'bg-green-500' :
                    status === 'processing' ? 'bg-blue-500' :
                    status === 'failed' ? 'bg-red-500' :
                    status === 'partial' ? 'bg-yellow-500' : 'bg-slate-600'
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-slate-400 w-10 text-right">{progress}%</span>
            </div>
          );
        })}
      </div>

      {/* 队列状态指示 */}
      {isInQueue && (
        <div className="mb-3 p-2 rounded-lg bg-green-500/10 border border-green-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock size={14} className="text-green-400" />
              <span className="text-xs text-green-300 font-medium">在队列中等待处理</span>
            </div>
            <button
              onClick={onRemoveFromQueue}
              disabled={loading}
              className={`text-xs transition-colors ${
                loading
                  ? 'text-slate-400 cursor-not-allowed'
                  : 'text-green-400 hover:text-red-400'
              }`}
              title={loading ? '正在加载任务列表' : '从队列移除'}
            >
              移除
            </button>
          </div>
        </div>
      )}

      {isProcessing && (
        <div className="mb-3 p-2 rounded-lg bg-blue-500/10 border border-blue-500/30">
          <div className="flex items-center gap-2">
            <Loader2 size={14} className="text-blue-400 animate-spin" />
            <span className="text-xs text-blue-300 font-medium">正在批量处理中...</span>
          </div>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button
          onClick={onOpen}
          disabled={loading}
          className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg font-semibold transition-all ${
            loading
              ? 'bg-slate-600/50 text-slate-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-500 hover:to-blue-500 hover:shadow-lg hover:shadow-purple-500/30'
          }`}
        >
          <Play size={16} />
          <span>打开任务</span>
        </button>

        {/* 添加到队列按钮（任务不在队列/处理中时显示）*/}
        {!isInQueue && !isProcessing && (
          <button
            onClick={onAddToQueue}
            disabled={loading}
            className={`px-3 py-2.5 rounded-lg transition-all border ${
              loading
                ? 'bg-slate-600/50 text-slate-400 border-slate-600 cursor-not-allowed'
                : 'bg-green-600/10 text-green-400 border-green-500/30 hover:bg-green-600/20 hover:border-green-400/50'
            }`}
            title={loading ? '正在加载任务列表' : '添加到批量处理队列'}
          >
            <Plus size={16} />
          </button>
        )}

        <button
          onClick={onDelete}
          disabled={loading}
          className={`px-3 py-2.5 rounded-lg transition-all border ${
            loading
              ? 'bg-slate-600/50 text-slate-400 border-slate-600 cursor-not-allowed'
              : 'bg-red-600/10 text-red-400 border-red-500/30 hover:bg-red-600/20 hover:border-red-400/50'
          }`}
          title="删除任务"
        >
          <Trash2 size={16} />
        </button>
      </div>
      </div>
    </div>
  );
};

export default TaskDashboard;
