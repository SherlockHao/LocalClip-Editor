import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { useTaskProgress } from '../hooks/useTaskProgress';

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

const TaskProgressBar: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const { progress, isConnected } = useTaskProgress(taskId || '');
  const [task, setTask] = useState<Task | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    if (taskId) {
      loadTask();
    }
  }, [taskId]);

  useEffect(() => {
    if (Object.keys(progress).length > 0) {
      loadTask();
    }
  }, [progress]);

  const loadTask = async () => {
    try {
      const response = await axios.get(`/api/tasks/${taskId}`);
      setTask(response.data);
    } catch (error) {
      console.error('Failed to load task:', error);
    }
  };

  if (!task) return null;

  const languageStatus = task.language_status || {};
  const languages = Object.keys(languageStatus);
  const hasProgress = languages.length > 0;

  if (!hasProgress) return null;

  const getOverallProgress = () => {
    const stages = ['speaker_diarization', 'translation', 'voice_cloning', 'export'];
    let totalProgress = 0;
    let count = 0;

    languages.forEach(lang => {
      stages.forEach(stage => {
        const stageData = languageStatus[lang]?.[stage];
        if (stageData) {
          totalProgress += stageData.progress || 0;
          count++;
        }
      });
    });

    return count > 0 ? Math.round(totalProgress / count) : 0;
  };

  const getActiveProcesses = () => {
    const active: string[] = [];
    languages.forEach(lang => {
      Object.entries(languageStatus[lang] || {}).forEach(([stage, data]) => {
        if (data.status === 'processing') {
          const stageNames: { [key: string]: string } = {
            'speaker_diarization': '说话人识别',
            'translation': '翻译',
            'voice_cloning': '语音克隆',
            'export': '导出'
          };
          active.push(`${lang} - ${stageNames[stage] || stage}: ${data.progress}%`);
        }
      });
    });
    return active;
  };

  const overallProgress = getOverallProgress();
  const activeProcesses = getActiveProcesses();

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-white shadow-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4 flex-1">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm font-medium text-gray-700 hover:text-gray-900 flex items-center"
            >
              <span className="mr-2">{isExpanded ? '▼' : '▶'}</span>
              任务进度
            </button>

            {/* 总体进度条 */}
            <div className="flex-1 max-w-md">
              <div className="flex items-center space-x-2">
                <div className="flex-1 bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${overallProgress}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-700 min-w-[3rem]">
                  {overallProgress}%
                </span>
              </div>
            </div>

            {/* WebSocket 连接状态 */}
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
              <span className="text-xs text-gray-500">
                {isConnected ? '实时' : '轮询'}
              </span>
            </div>
          </div>
        </div>

        {/* 展开的详细进度 */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            {activeProcesses.length > 0 ? (
              <div className="space-y-1">
                <div className="text-xs font-medium text-gray-600 mb-2">正在处理:</div>
                {activeProcesses.map((process, index) => (
                  <div key={index} className="text-sm text-gray-700 flex items-center">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-2 animate-pulse" />
                    {process}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">暂无活动任务</div>
            )}

            {/* 所有语言的详细状态 */}
            <div className="mt-3 grid grid-cols-2 gap-4">
              {languages.map(lang => {
                const langData = languageStatus[lang] || {};
                const stages = [
                  { key: 'speaker_diarization', name: '说话人' },
                  { key: 'translation', name: '翻译' },
                  { key: 'voice_cloning', name: '克隆' },
                  { key: 'export', name: '导出' }
                ];

                return (
                  <div key={lang} className="text-xs">
                    <div className="font-medium text-gray-700 mb-1">{lang}</div>
                    <div className="flex space-x-2">
                      {stages.map(stage => {
                        const stageData = langData[stage.key];
                        const status = stageData?.status || 'pending';
                        const progress = stageData?.progress || 0;

                        let color = 'bg-gray-300';
                        if (status === 'completed') color = 'bg-green-500';
                        else if (status === 'processing') color = 'bg-blue-500';
                        else if (status === 'failed') color = 'bg-red-500';

                        return (
                          <div key={stage.key} className="flex-1" title={`${stage.name}: ${progress}%`}>
                            <div className="text-xs text-gray-600 mb-1">{stage.name}</div>
                            <div className="bg-gray-200 rounded-full h-1">
                              <div
                                className={`${color} h-1 rounded-full transition-all`}
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskProgressBar;
