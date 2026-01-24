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

interface LanguageProgressSidebarProps {
  speakerDiarizationCompleted: boolean;
  selectedLanguage: string;
  onLanguageSelect: (languageCode: string) => void;
}

// 语言代码映射（API使用的代码 -> 显示名称）
const LANGUAGE_MAP: { [key: string]: { name: string; flag: string; apiCode: string } } = {
  'en': { name: '英语', flag: '🇬🇧', apiCode: 'en' },
  'ko': { name: '韩语', flag: '🇰🇷', apiCode: 'ko' },
  'ja': { name: '日语', flag: '🇯🇵', apiCode: 'ja' },
  'fr': { name: '法语', flag: '🇫🇷', apiCode: 'fr' },
  'de': { name: '德语', flag: '🇩🇪', apiCode: 'de' },
  'es': { name: '西班牙语', flag: '🇪🇸', apiCode: 'es' },
  'id': { name: '印尼语', flag: '🇮🇩', apiCode: 'id' },
};

// 所有支持的语言列表
const ALL_LANGUAGES = Object.entries(LANGUAGE_MAP).map(([code, info]) => ({
  code,
  name: info.name,
  flag: info.flag,
}));

const LanguageProgressSidebar: React.FC<LanguageProgressSidebarProps> = ({
  speakerDiarizationCompleted,
  selectedLanguage,
  onLanguageSelect,
}) => {
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
      const response = await axios.get(`/api/tasks/${taskId}`, { timeout: 8000 });
      setTask(response.data);
    } catch (error) {
      console.error('Failed to load task:', error);
      // 如果首次加载失败，设置一个默认的空任务对象以避免一直显示加载状态
      if (!task) {
        setTask({
          task_id: taskId || '',
          status: 'pending',
          language_status: {}
        });
      }
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

  // 定义各阶段（不包括 speaker_diarization，因为它是全局的）
  const stages = [
    { key: 'translation', name: '翻译', shortName: '翻译' },
    { key: 'voice_cloning', name: '语音克隆', shortName: '克隆' },
    { key: 'stitch', name: '音频拼接', shortName: '拼接' },
    { key: 'export', name: '视频导出', shortName: '导出' },
  ];

  const getStageStatus = (language: string, stageKey: string) => {
    return languageStatus[language]?.[stageKey] || { status: 'pending', progress: 0, message: '未开始' };
  };

  // 检查语言是否所有步骤都完成（翻译、语音克隆、拼接、导出）
  const isLanguageFullyCompleted = (language: string) => {
    const langData = languageStatus[language];
    if (!langData) return false;

    const translationCompleted = langData['translation']?.status === 'completed';
    const voiceCloningCompleted = langData['voice_cloning']?.status === 'completed';
    const stitchCompleted = langData['stitch']?.status === 'completed';
    const exportCompleted = langData['export']?.status === 'completed';

    return translationCompleted && voiceCloningCompleted && stitchCompleted && exportCompleted;
  };

  const getLanguageOverallStatus = (language: string) => {
    const langData = languageStatus[language];
    if (!langData) return 'pending';

    // 检查是否全部完成
    if (isLanguageFullyCompleted(language)) return 'completed';

    const statuses = stages.map(s => langData[s.key]?.status || 'pending');
    if (statuses.some(s => s === 'failed')) return 'failed';
    if (statuses.some(s => s === 'processing')) return 'processing';
    if (statuses.some(s => s === 'completed')) return 'partial'; // 部分完成
    return 'pending';
  };

  const StatusIcon: React.FC<{ status: string; isFullyCompleted?: boolean }> = ({ status, isFullyCompleted }) => {
    if (isFullyCompleted) {
      return <CheckCircle size={16} className="text-green-500" />;
    }
    switch (status) {
      case 'completed':
        return <CheckCircle size={16} className="text-green-500" />;
      case 'processing':
        return <Loader size={16} className="text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      case 'partial':
        return <Clock size={16} className="text-yellow-500" />;
      default:
        return <Clock size={16} className="text-gray-400" />;
    }
  };

  const handleLanguageClick = (languageCode: string) => {
    if (!speakerDiarizationCompleted) return;
    onLanguageSelect(languageCode);
  };

  return (
    <div className="flex-1 overflow-y-auto p-4">
      {/* 说话人识别状态 */}
      <div className="mb-4 p-3 rounded-lg border bg-slate-700/50 border-slate-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-xl">🎙️</span>
            <div>
              <div className="text-sm font-medium text-slate-200">说话人识别</div>
              <div className="text-xs text-slate-400">
                {speakerDiarizationCompleted ? '已完成' : '未执行'}
              </div>
            </div>
          </div>
          {speakerDiarizationCompleted ? (
            <CheckCircle size={16} className="text-green-500" />
          ) : (
            <Clock size={16} className="text-gray-400" />
          )}
        </div>
      </div>

      <h3 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">
        语言处理进度
      </h3>

      {!speakerDiarizationCompleted && (
        <div className="mb-3 p-2 rounded bg-yellow-900/30 border border-yellow-700/50 text-xs text-yellow-400">
          请先完成说话人识别后再选择语言
        </div>
      )}

      <div className="space-y-3">
        {ALL_LANGUAGES.map(lang => {
          const overallStatus = getLanguageOverallStatus(lang.code);
          const hasProgress = !!languageStatus[lang.code];
          const isSelected = selectedLanguage === lang.code;
          const isFullyCompleted = isLanguageFullyCompleted(lang.code);
          const isDisabled = !speakerDiarizationCompleted;

          return (
            <div
              key={lang.code}
              onClick={() => handleLanguageClick(lang.code)}
              className={`rounded-lg border transition-all ${
                isDisabled
                  ? 'bg-slate-800/20 border-slate-700/30 opacity-50 cursor-not-allowed'
                  : isSelected
                  ? 'bg-blue-900/40 border-blue-500 ring-1 ring-blue-500 cursor-pointer'
                  : hasProgress
                  ? 'bg-slate-700/50 border-slate-600 hover:border-slate-500 cursor-pointer'
                  : 'bg-slate-800/50 border-slate-700 hover:border-slate-600 cursor-pointer'
              }`}
            >
              {/* 语言标题 */}
              <div className="p-3 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className={`text-2xl ${isDisabled ? 'grayscale' : ''}`}>{lang.flag}</span>
                  <div>
                    <div className={`text-sm font-medium ${isDisabled ? 'text-slate-500' : 'text-slate-200'}`}>
                      {lang.name}
                    </div>
                    <div className={`text-xs ${isDisabled ? 'text-slate-600' : 'text-slate-400'}`}>
                      {lang.code}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {isFullyCompleted && (
                    <span className="text-xs bg-green-600/30 text-green-400 px-2 py-0.5 rounded">
                      已完成
                    </span>
                  )}
                  <StatusIcon status={overallStatus} isFullyCompleted={isFullyCompleted} />
                </div>
              </div>

              {/* 各阶段进度 - 仅在有进度时显示 */}
              {hasProgress && !isDisabled && (
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

      {Object.keys(languageStatus).filter(k => k !== 'default').length === 0 && speakerDiarizationCompleted && (
        <div className="mt-8 text-center text-slate-400 text-sm">
          <p>尚未开始任何语言处理</p>
          <p className="text-xs text-slate-500 mt-2">点击上方语言卡片或使用右侧面板</p>
        </div>
      )}
    </div>
  );
};

export default LanguageProgressSidebar;
