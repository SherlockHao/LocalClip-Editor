import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle, Clock, XCircle, Loader } from 'lucide-react';

interface Task {
  task_id: string;
  status: string;
  language_status: {
    [language: string]: {
      [stage: string]: {
        status: string;
        progress: number;
        message: string;
      };
    };
  };
}

const LanguageProgressSidebar: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const [task, setTask] = useState<Task | null>(null);

  useEffect(() => {
    if (taskId) {
      loadTask();
      // 每5秒刷新一次
      const interval = setInterval(loadTask, 5000);
      return () => clearInterval(interval);
    }
  }, [taskId]);

  const loadTask = async () => {
    try {
      const response = await axios.get(`/api/tasks/${taskId}`);
      setTask(response.data);
    } catch (error) {
      console.error('Failed to load task:', error);
    }
  };

  if (!task) {
    return (
      <div className="p-4 text-center text-slate-400">
        <Loader className="animate-spin mx-auto mb-2" size={24} />
        <p className="text-sm">加载中...</p>
      </div>
    );
  }

  const languageStatus = task.language_status || {};
  const languages = [
    { code: 'English', name: '英语', flag: '🇬🇧' },
    { code: 'Korean', name: '韩语', flag: '🇰🇷' },
    { code: 'Japanese', name: '日语', flag: '🇯🇵' },
    { code: 'French', name: '法语', flag: '🇫🇷' },
    { code: 'German', name: '德语', flag: '🇩🇪' },
    { code: 'Spanish', name: '西班牙语', flag: '🇪🇸' },
    { code: 'Indonesian', name: '印尼语', flag: '🇮🇩' },
  ];

  const stages = [
    { key: 'speaker_diarization', name: '说话人识别', shortName: '说话人' },
    { key: 'translation', name: '翻译', shortName: '翻译' },
    { key: 'voice_cloning', name: '语音克隆', shortName: '克隆' },
    { key: 'export', name: '导出', shortName: '导出' },
  ];

  const getStageStatus = (language: string, stageKey: string) => {
    return languageStatus[language]?.[stageKey] || { status: 'pending', progress: 0, message: '未开始' };
  };

  const getLanguageOverallStatus = (language: string) => {
    const langData = languageStatus[language];
    if (!langData) return 'pending';

    const statuses = stages.map(s => langData[s.key]?.status || 'pending');
    if (statuses.some(s => s === 'failed')) return 'failed';
    if (statuses.every(s => s === 'completed')) return 'completed';
    if (statuses.some(s => s === 'processing')) return 'processing';
    return 'pending';
  };

  const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'processing':
        return <Loader size={16} className="text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      default:
        return <Clock size={16} className="text-gray-400" />;
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4">
      <h3 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">
        语言处理进度
      </h3>

      <div className="space-y-3">
        {languages.map(lang => {
          const overallStatus = getLanguageOverallStatus(lang.code);
          const hasProgress = !!languageStatus[lang.code];

          return (
            <div
              key={lang.code}
              className={`rounded-lg border transition-all ${
                hasProgress
                  ? 'bg-slate-700/50 border-slate-600'
                  : 'bg-slate-800/30 border-slate-700/50'
              }`}
            >
              {/* 语言标题 */}
              <div className="p-3 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="text-2xl">{lang.flag}</span>
                  <div>
                    <div className="text-sm font-medium text-slate-200">{lang.name}</div>
                    <div className="text-xs text-slate-400">{lang.code}</div>
                  </div>
                </div>
                <StatusIcon status={overallStatus} />
              </div>

              {/* 各阶段进度 */}
              {hasProgress && (
                <div className="px-3 pb-3 space-y-2">
                  {stages.map(stage => {
                    const stageStatus = getStageStatus(lang.code, stage.key);
                    const progress = stageStatus.progress || 0;

                    let progressColor = 'bg-gray-600';
                    if (stageStatus.status === 'completed') progressColor = 'bg-green-500';
                    else if (stageStatus.status === 'processing') progressColor = 'bg-blue-500';
                    else if (stageStatus.status === 'failed') progressColor = 'bg-red-500';

                    return (
                      <div key={stage.key} className="space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-slate-300 font-medium">{stage.shortName}</span>
                          <span className="text-slate-400">{progress}%</span>
                        </div>
                        <div className="w-full bg-slate-800 rounded-full h-1.5">
                          <div
                            className={`${progressColor} h-1.5 rounded-full transition-all duration-300`}
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        {stageStatus.status === 'processing' && stageStatus.message && (
                          <div className="text-xs text-slate-400 truncate" title={stageStatus.message}>
                            {stageStatus.message}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {Object.keys(languageStatus).length === 0 && (
        <div className="mt-8 text-center text-slate-400 text-sm">
          <p>尚未开始任何语言处理</p>
          <p className="text-xs text-slate-500 mt-2">请使用右侧功能面板启动处理</p>
        </div>
      )}
    </div>
  );
};

export default LanguageProgressSidebar;
