import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Play, Trash2, Plus, Video, Clock, Loader2, FileText, Upload } from 'lucide-react';

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

const TaskDashboard: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [subtitleFile, setSubtitleFile] = useState<File | null>(null);
  const [runningTasks, setRunningTasks] = useState<Record<string, RunningTaskInfo>>({});
  const navigate = useNavigate();

  // 用于追踪是否曾经成功加载过任务
  const hasLoadedRef = useRef(false);
  // 用于追踪重试次数
  const retryCountRef = useRef(0);

  useEffect(() => {
    fetchTasks();
    fetchRunningTasks();

    // 每3秒刷新一次运行任务状态和任务列表（更频繁以确保及时更新）
    const runningTasksInterval = setInterval(fetchRunningTasks, 3000);
    const tasksInterval = setInterval(() => {
      // 静默刷新任务列表，不设置 loading 状态
      fetchTasksSilent();
    }, 3000);

    return () => {
      clearInterval(runningTasksInterval);
      clearInterval(tasksInterval);
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
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setTasks([response.data, ...tasks]);
      setShowUploadModal(false);
      setVideoFile(null);
      setSubtitleFile(null);

      // 自动跳转到新创建的任务编辑器
      navigate(`/tasks/${response.data.task_id}`);
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
      await axios.delete(`/api/tasks/${taskId}`);
      setTasks(tasks.filter(t => t.task_id !== taskId));
    } catch (error) {
      console.error('Delete failed:', error);
      alert('删除失败，请重试');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <div className="max-w-7xl mx-auto">
        {/* 头部 */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center gap-3">
              <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg">
                <Video size={28} />
              </div>
              任务看板
            </h1>
            <p className="text-slate-400 mt-2">管理您的视频编辑任务</p>
          </div>

          <button
            onClick={() => setShowUploadModal(true)}
            className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-purple-500 text-white px-6 py-3 rounded-lg hover:shadow-lg hover:shadow-purple-500/50 transition-all"
            disabled={uploading}
          >
            <Plus size={20} />
            <span>创建新任务</span>
          </button>
        </div>

        {/* 任务网格 */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <Loader2 size={48} className="animate-spin text-blue-400" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-slate-400">
            <Video size={64} className="mb-4 opacity-50" />
            <p className="text-lg">暂无任务</p>
            <p className="text-sm mt-2">点击"上传新视频"创建第一个任务</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tasks.map(task => (
              <TaskCard
                key={task.task_id}
                task={task}
                onOpen={() => navigate(`/tasks/${task.task_id}`)}
                onDelete={(e) => handleDelete(task.task_id, e)}
                runningTask={runningTasks[task.task_id] || null}
                getStageName={getStageName}
                getLanguageName={getLanguageName}
              />
            ))}
          </div>
        )}
      </div>

      {/* 上传模态框 */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => !uploading && setShowUploadModal(false)}>
          <div className="bg-slate-800 rounded-lg p-8 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-2xl font-bold text-white mb-6">创建新任务</h2>

            {/* 视频文件上传 */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                视频文件 <span className="text-red-400">*</span>
              </label>
              <label className="flex items-center justify-center w-full px-4 py-8 border-2 border-dashed border-slate-600 rounded-lg cursor-pointer hover:border-purple-500 transition-all bg-slate-700/30">
                <div className="text-center">
                  {videoFile ? (
                    <>
                      <Video className="mx-auto mb-2 text-purple-400" size={32} />
                      <p className="text-sm text-white font-medium">{videoFile.name}</p>
                      <p className="text-xs text-slate-400 mt-1">{(videoFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </>
                  ) : (
                    <>
                      <Upload className="mx-auto mb-2 text-slate-400" size={32} />
                      <p className="text-sm text-slate-300">点击选择视频文件</p>
                      <p className="text-xs text-slate-500 mt-1">支持 MP4, MOV, AVI, MKV</p>
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
            <div className="mb-6">
              <label className="block text-sm font-medium text-slate-300 mb-2">
                字幕文件 <span className="text-slate-500">(可选)</span>
              </label>
              <label className="flex items-center justify-center w-full px-4 py-6 border-2 border-dashed border-slate-600 rounded-lg cursor-pointer hover:border-blue-500 transition-all bg-slate-700/30">
                <div className="text-center">
                  {subtitleFile ? (
                    <>
                      <FileText className="mx-auto mb-2 text-blue-400" size={28} />
                      <p className="text-sm text-white font-medium">{subtitleFile.name}</p>
                      <p className="text-xs text-slate-400 mt-1">{(subtitleFile.size / 1024).toFixed(2)} KB</p>
                    </>
                  ) : (
                    <>
                      <FileText className="mx-auto mb-2 text-slate-400" size={28} />
                      <p className="text-sm text-slate-300">点击选择字幕文件</p>
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
                className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition-all"
                disabled={uploading}
              >
                取消
              </button>
              <button
                onClick={handleUploadSubmit}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-purple-600 to-purple-500 text-white rounded-lg hover:shadow-lg hover:shadow-purple-500/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={uploading || !videoFile}
              >
                {uploading ? (
                  <span className="flex items-center justify-center gap-2">
                    <Loader2 size={16} className="animate-spin" />
                    上传中...
                  </span>
                ) : (
                  '创建任务'
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
  runningTask: RunningTaskInfo | null;
  getStageName: (stage: string) => string;
  getLanguageName: (language: string) => string;
}

const TaskCard: React.FC<TaskCardProps> = ({ task, onOpen, onDelete, runningTask, getStageName, getLanguageName }) => {
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
      className="bg-slate-800 border border-slate-700 rounded-lg p-6 hover:border-purple-500 transition-all cursor-pointer hover:shadow-xl hover:shadow-purple-500/20"
    >
      {/* 视频信息 */}
      <div className="mb-4">
        <h3 className="text-white font-semibold truncate mb-2 flex items-center gap-2">
          <Video size={18} className="text-blue-400 flex-shrink-0" />
          <span className="truncate">{task.video_original_name}</span>
        </h3>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Clock size={14} />
          <span>{formatDate(task.created_at)}</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className={`text-xs px-2 py-1 rounded ${
            task.status === 'completed' ? 'bg-green-500/20 text-green-400' :
            task.status === 'processing' ? 'bg-blue-500/20 text-blue-400' :
            task.status === 'failed' ? 'bg-red-500/20 text-red-400' :
            'bg-slate-500/20 text-slate-400'
          }`}>
            {task.status === 'completed' ? '已完成' :
             task.status === 'processing' ? '处理中' :
             task.status === 'failed' ? '失败' : '待处理'}
          </span>
          {isSpeakerDiarizationCompleted && (
            <span className="text-xs px-2 py-1 rounded bg-purple-500/20 text-purple-400">
              说话人识别 ✓
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

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <button
          onClick={onOpen}
          className="flex-1 flex items-center justify-center gap-2 bg-purple-600 text-white py-2 rounded-lg hover:bg-purple-500 transition-all"
        >
          <Play size={16} />
          <span>打开</span>
        </button>
        <button
          onClick={onDelete}
          className="px-3 py-2 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 transition-all"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </div>
  );
};

export default TaskDashboard;
