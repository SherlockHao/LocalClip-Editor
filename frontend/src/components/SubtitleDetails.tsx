import React, { useEffect, useRef, useState } from 'react';
import { Trash2, Edit2, Users, FileText, Save, X } from 'lucide-react';

interface Subtitle {
  start_time: number;
  end_time: number;
  start_time_formatted: string;
  end_time_formatted: string;
  text: string;
  speaker_id?: number;
}

interface SubtitleDetailsProps {
  subtitles: Subtitle[];
  currentTime: number;
  onEditSubtitle?: (index: number, newSubtitle: Subtitle) => void;
  onDeleteSubtitle?: (index: number) => void;
  onSeek?: (time: number) => void;
  speakerNameMapping?: {[key: number]: string};
}

// 获取所有唯一的说话人ID
const getUniqueSpeakers = (subtitles: Subtitle[]): number[] => {
  const speakerIds = subtitles
    .map(sub => sub.speaker_id)
    .filter((id): id is number => id !== undefined);
  return Array.from(new Set(speakerIds)).sort((a, b) => a - b);
};

const SubtitleDetails: React.FC<SubtitleDetailsProps> = ({
  subtitles,
  currentTime,
  onEditSubtitle,
  onDeleteSubtitle,
  onSeek,
  speakerNameMapping = {}
}) => {
  const activeSubtitleRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingText, setEditingText] = useState<string>('');

  const uniqueSpeakers = getUniqueSpeakers(subtitles);

  const speakerColors = [
    { bg: 'bg-blue-500/30', border: 'border-blue-400/50', text: 'text-blue-300', badge: 'bg-blue-500/50 text-blue-200' },
    { bg: 'bg-green-500/30', border: 'border-green-400/50', text: 'text-green-300', badge: 'bg-green-500/50 text-green-200' },
    { bg: 'bg-yellow-500/30', border: 'border-yellow-400/50', text: 'text-yellow-300', badge: 'bg-yellow-500/50 text-yellow-200' },
    { bg: 'bg-purple-500/30', border: 'border-purple-400/50', text: 'text-purple-300', badge: 'bg-purple-500/50 text-purple-200' },
    { bg: 'bg-pink-500/30', border: 'border-pink-400/50', text: 'text-pink-300', badge: 'bg-pink-500/50 text-pink-200' },
    { bg: 'bg-indigo-500/30', border: 'border-indigo-400/50', text: 'text-indigo-300', badge: 'bg-indigo-500/50 text-indigo-200' }
  ];

  const getColorBySpacker = (speakerId: number | undefined) => {
    if (speakerId === undefined) return speakerColors[0];
    return speakerColors[speakerId % speakerColors.length];
  };

  // 自动滚动到当前播放的字幕
  useEffect(() => {
    if (activeSubtitleRef.current && containerRef.current) {
      const container = containerRef.current;
      const activeElement = activeSubtitleRef.current;

      // 计算元素相对于容器的位置
      const containerRect = container.getBoundingClientRect();
      const elementRect = activeElement.getBoundingClientRect();

      // 检查元素是否在可视区域内
      const isVisible =
        elementRect.top >= containerRect.top &&
        elementRect.bottom <= containerRect.bottom;

      // 如果不在可视区域，滚动到元素位置
      if (!isVisible) {
        activeElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
          inline: 'nearest'
        });
      }
    }
  }, [currentTime, subtitles]);

  const handleDeleteSubtitle = (index: number) => {
    if (onDeleteSubtitle) {
      onDeleteSubtitle(index);
    }
  };

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setEditingText(subtitles[index].text);
  };

  const handleSaveEdit = (index: number) => {
    if (onEditSubtitle) {
      const currentSubtitle = subtitles[index];
      const updatedSubtitle = {
        ...currentSubtitle,
        text: editingText
      };
      onEditSubtitle(index, updatedSubtitle);
    }
    setEditingIndex(null);
    setEditingText('');
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditingText('');
  };

  const handleSpeakerChange = (index: number, speakerId: number | undefined) => {
    if (onEditSubtitle) {
      const currentSubtitle = subtitles[index];
      const updatedSubtitle = {
        ...currentSubtitle,
        speaker_id: speakerId
      };
      onEditSubtitle(index, updatedSubtitle);
    }
  };

  const handleSubtitleClick = (index: number) => {
    if (onSeek) {
      onSeek(subtitles[index].start_time);
    }
  };

  if (subtitles.length === 0) {
    return (
      <div className="w-64 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 rounded-xl shadow-xl flex flex-col justify-center items-center text-center p-4">
        <div className="p-4 bg-slate-700/30 rounded-lg mb-3">
          <FileText size={40} className="text-slate-500 mx-auto mb-2" />
        </div>
        <p className="text-sm text-slate-400 font-medium">暂无字幕</p>
        <p className="text-xs text-slate-500 mt-1">上传字幕文件后显示详情</p>
      </div>
    );
  }

  return (
    <div className="w-72 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 rounded-xl shadow-xl flex flex-col overflow-hidden">
      {/* 头部 */}
      <div className="p-4 border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-900/80 flex-shrink-0">
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center">
          <FileText size={16} className="mr-2 text-cyan-400" />
          字幕详情
          <span className="ml-auto text-xs font-semibold text-slate-400 bg-slate-700/50 px-2 py-1 rounded">
            {subtitles.length}
          </span>
        </h3>
      </div>

      {/* 字幕列表 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-2.5">
        {subtitles.map((subtitle, index) => {
          const isPlaying = currentTime >= subtitle.start_time && currentTime <= subtitle.end_time;
          const colors = getColorBySpacker(subtitle.speaker_id);

          return (
            <div
              key={index}
              ref={isPlaying ? activeSubtitleRef : null}
              onClick={() => handleSubtitleClick(index)}
              className={`p-3 rounded-lg border-2 transition-all duration-200 group cursor-pointer
                ${isPlaying
                  ? 'bg-blue-500/25 border-blue-400 shadow-lg shadow-blue-500/30 scale-105'
                  : `${colors.bg} border-slate-600 hover:border-slate-500 hover:shadow-md`
                }`}
            >
              {/* 索引和时间 */}
              <div className="flex items-center justify-between mb-2">
                <span className={`text-xs font-mono font-bold ${isPlaying ? 'text-blue-300' : 'text-slate-400'}`}>
                  #{index + 1}
                </span>
                <span className={`text-xs font-mono font-semibold ${isPlaying ? 'text-blue-300' : 'text-slate-500'}`}>
                  {subtitle.start_time_formatted} - {subtitle.end_time_formatted}
                </span>
              </div>

              {/* 说话人选择 */}
              {uniqueSpeakers.length > 0 && (
                <div className="mb-2" onClick={(e) => e.stopPropagation()}>
                  <select
                    value={subtitle.speaker_id ?? ''}
                    onChange={(e) => handleSpeakerChange(index, e.target.value ? Number(e.target.value) : undefined)}
                    className={`text-xs font-semibold px-2 py-1 rounded border-2 transition-colors ${
                      subtitle.speaker_id !== undefined
                        ? `${colors.badge} border-transparent`
                        : 'bg-slate-700/50 text-slate-400 border-slate-600'
                    } hover:border-blue-400/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 cursor-pointer`}
                  >
                    <option value="">选择说话人</option>
                    {uniqueSpeakers.map(speakerId => (
                      <option key={speakerId} value={speakerId}>
                        {speakerNameMapping[speakerId] || `说话人${speakerId}`}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* 字幕文本 */}
              {editingIndex === index ? (
                // 编辑模式
                <div className="mb-3" onClick={(e) => e.stopPropagation()}>
                  <textarea
                    value={editingText}
                    onChange={(e) => setEditingText(e.target.value)}
                    className="w-full text-xs leading-relaxed bg-slate-700/50 text-slate-100 border border-blue-500/50 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                    rows={3}
                    autoFocus
                  />
                </div>
              ) : (
                // 显示模式
                <p className={`text-xs leading-relaxed mb-3 ${isPlaying ? 'text-slate-100 font-semibold' : 'text-slate-300'}`}>
                  {subtitle.text}
                </p>
              )}

              {/* 操作按钮 */}
              {editingIndex === index ? (
                // 编辑模式的按钮
                <div className="flex gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <button
                    className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-green-600/30 border border-green-500/40 text-green-300 px-2 py-1.5 rounded hover:bg-green-600/50 hover:border-green-400/60 transition-colors"
                    onClick={() => handleSaveEdit(index)}
                  >
                    <Save size={12} />
                    保存
                  </button>
                  <button
                    className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-gray-600/30 border border-gray-500/40 text-gray-300 px-2 py-1.5 rounded hover:bg-gray-600/50 hover:border-gray-400/60 transition-colors"
                    onClick={handleCancelEdit}
                  >
                    <X size={12} />
                    取消
                  </button>
                </div>
              ) : (
                // 普通模式的按钮
                <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-blue-600/30 border border-blue-500/40 text-blue-300 px-2 py-1.5 rounded hover:bg-blue-600/50 hover:border-blue-400/60 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStartEdit(index);
                    }}
                  >
                    <Edit2 size={12} />
                    编辑
                  </button>
                  <button
                    className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-red-600/30 border border-red-500/40 text-red-300 px-2 py-1.5 rounded hover:bg-red-600/50 hover:border-red-400/60 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSubtitle(index);
                    }}
                  >
                    <Trash2 size={12} />
                    删除
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default SubtitleDetails;