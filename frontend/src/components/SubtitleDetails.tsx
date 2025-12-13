import React, { useEffect, useRef, useState } from 'react';
import { Trash2, Edit2, Users, FileText, Save, X, Plus, Minus, Play, RotateCw, Loader2 } from 'lucide-react';

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
}

interface SubtitleDetailsProps {
  subtitles: Subtitle[];
  currentTime: number;
  onEditSubtitle?: (index: number, newSubtitle: Subtitle) => void;
  onDeleteSubtitle?: (index: number) => void;
  onSeek?: (time: number) => void;
  speakerNameMapping?: {[key: number]: string};
  onAddSpeaker?: (gender: 'male' | 'female') => void;
  onRemoveSpeaker?: (speakerId: number) => void;
  onPlayClonedAudio?: (audioPath: string) => void;
  onRegenerateSegment?: (index: number, newSpeakerId: number) => void;
  voiceCloningTaskId?: string;
}

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
  speakerNameMapping = {},
  onAddSpeaker,
  onRemoveSpeaker,
  onPlayClonedAudio,
  onRegenerateSegment,
  voiceCloningTaskId
}) => {
  const activeSubtitleRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingText, setEditingText] = useState<string>('');
  const [selectedClonedSpeaker, setSelectedClonedSpeaker] = useState<{[index: number]: number}>({});
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);

  const uniqueSpeakers = getUniqueSpeakers(subtitles);

  // 获取所有说话人ID（包括手动添加但未分配的）
  const allSpeakerIds = Object.keys(speakerNameMapping).map(id => parseInt(id));

  // 按照男1、男2...女1、女2的顺序排序说话人
  const sortedSpeakers = [...allSpeakerIds].sort((a, b) => {
    const nameA = speakerNameMapping[a] || `说话人${a}`;
    const nameB = speakerNameMapping[b] || `说话人${b}`;

    const isMaleA = nameA.startsWith('男');
    const isMaleB = nameB.startsWith('男');

    // 男声在前，女声在后
    if (isMaleA && !isMaleB) return -1;
    if (!isMaleA && isMaleB) return 1;

    // 同性别按数字排序
    const numA = parseInt(nameA.match(/\d+/)?.[0] || '0');
    const numB = parseInt(nameB.match(/\d+/)?.[0] || '0');
    return numA - numB;
  });

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

  // 获取男女说话人列表
  const maleSpeakers: Array<{id: number, name: string}> = [];
  const femaleSpeakers: Array<{id: number, name: string}> = [];

  Object.entries(speakerNameMapping).forEach(([id, name]) => {
    const speakerId = parseInt(id);
    if (name.startsWith('男')) {
      maleSpeakers.push({ id: speakerId, name });
    } else if (name.startsWith('女')) {
      femaleSpeakers.push({ id: speakerId, name });
    }
  });

  // 排序
  const sortByNumber = (a: {name: string}, b: {name: string}) => {
    const numA = parseInt(a.name.match(/\d+/)?.[0] || '0');
    const numB = parseInt(b.name.match(/\d+/)?.[0] || '0');
    return numA - numB;
  };
  maleSpeakers.sort(sortByNumber);
  femaleSpeakers.sort(sortByNumber);

  useEffect(() => {
    if (activeSubtitleRef.current && containerRef.current) {
      const container = containerRef.current;
      const activeElement = activeSubtitleRef.current;
      const containerRect = container.getBoundingClientRect();
      const elementRect = activeElement.getBoundingClientRect();
      const isVisible = elementRect.top >= containerRect.top && elementRect.bottom <= containerRect.bottom;
      if (!isVisible) {
        activeElement.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'nearest' });
      }
    }
  }, [currentTime, subtitles]);

  const handleDeleteSubtitle = (index: number) => {
    if (onDeleteSubtitle) onDeleteSubtitle(index);
  };

  const handleStartEdit = (index: number) => {
    setEditingIndex(index);
    setEditingText(subtitles[index].text);
  };

  const handleSaveEdit = (index: number) => {
    if (onEditSubtitle) {
      onEditSubtitle(index, { ...subtitles[index], text: editingText });
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
      // 更新说话人，并自动链接克隆音色
      const updatedSubtitle = {
        ...subtitles[index],
        speaker_id: speakerId,
        cloned_speaker_id: speakerId  // 自动链接克隆音色
      };
      onEditSubtitle(index, updatedSubtitle);

      // 同时更新本地选择状态
      if (speakerId !== undefined) {
        setSelectedClonedSpeaker(prev => ({ ...prev, [index]: speakerId }));
      }
    }
  };

  const handleSubtitleClick = (index: number) => {
    if (onSeek) onSeek(subtitles[index].start_time);
  };

  const handleRemoveSpeaker = (gender: 'male' | 'female') => {
    const speakers = gender === 'male' ? maleSpeakers : femaleSpeakers;
    if (speakers.length > 0 && onRemoveSpeaker) {
      onRemoveSpeaker(speakers[speakers.length - 1].id);
    }
  };

  const handleClonedSpeakerChange = (index: number, newSpeakerId: number) => {
    setSelectedClonedSpeaker(prev => ({ ...prev, [index]: newSpeakerId }));
  };

  const handlePlayClonedAudio = (audioPath: string) => {
    if (onPlayClonedAudio) {
      onPlayClonedAudio(audioPath);
    }
  };

  const handleRegenerateSegment = async (index: number) => {
    // 使用当前选择的克隆音色，如果没有选择则使用字幕中保存的克隆音色
    const newSpeakerId = selectedClonedSpeaker[index] ?? subtitles[index].cloned_speaker_id;
    if (newSpeakerId !== undefined && onRegenerateSegment) {
      setRegeneratingIndex(index);
      try {
        await onRegenerateSegment(index, newSpeakerId);
      } finally {
        setRegeneratingIndex(null);
      }
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

      {/* 说话人列表区域 - 两行布局 */}
      {Object.keys(speakerNameMapping).length > 0 && (
        <div className="px-4 py-3 border-b border-slate-700 bg-slate-800/50 flex-shrink-0">
          <div className="flex items-center space-x-2 mb-2">
            <Users size={14} className="text-purple-400" />
            <span className="text-xs font-semibold text-slate-300">说话人</span>
          </div>
          <div className="space-y-2">
            {/* 男声行 */}
            <div className="flex items-center space-x-2 overflow-x-auto pb-1">
              <span className="flex-shrink-0 text-xs font-semibold text-blue-400">男:</span>
              {maleSpeakers.map(speaker => {
                const colors = getColorBySpacker(speaker.id);
                return (
                  <div key={speaker.id} className={`flex-shrink-0 px-3 py-1.5 rounded-lg border-2 ${colors.badge} ${colors.border} text-xs font-semibold`}>
                    {speaker.name}
                  </div>
                );
              })}
              <button onClick={() => onAddSpeaker?.('male')} className="flex-shrink-0 w-7 h-7 rounded-lg border-2 border-dashed border-blue-600/50 bg-blue-700/20 hover:bg-blue-700/40 text-blue-400 flex items-center justify-center" title="添加男声">
                <Plus size={14} />
              </button>
              {maleSpeakers.length > 0 && (
                <button onClick={() => handleRemoveSpeaker('male')} className="flex-shrink-0 w-7 h-7 rounded-lg border-2 border-dashed border-red-600/50 bg-red-700/20 hover:bg-red-700/40 text-red-400 flex items-center justify-center" title="删除最后一个男声">
                  <Minus size={14} />
                </button>
              )}
            </div>
            {/* 女声行 */}
            <div className="flex items-center space-x-2 overflow-x-auto pb-1">
              <span className="flex-shrink-0 text-xs font-semibold text-pink-400">女:</span>
              {femaleSpeakers.map(speaker => {
                const colors = getColorBySpacker(speaker.id);
                return (
                  <div key={speaker.id} className={`flex-shrink-0 px-3 py-1.5 rounded-lg border-2 ${colors.badge} ${colors.border} text-xs font-semibold`}>
                    {speaker.name}
                  </div>
                );
              })}
              <button onClick={() => onAddSpeaker?.('female')} className="flex-shrink-0 w-7 h-7 rounded-lg border-2 border-dashed border-pink-600/50 bg-pink-700/20 hover:bg-pink-700/40 text-pink-400 flex items-center justify-center" title="添加女声">
                <Plus size={14} />
              </button>
              {femaleSpeakers.length > 0 && (
                <button onClick={() => handleRemoveSpeaker('female')} className="flex-shrink-0 w-7 h-7 rounded-lg border-2 border-dashed border-red-600/50 bg-red-700/20 hover:bg-red-700/40 text-red-400 flex items-center justify-center" title="删除最后一个女声">
                  <Minus size={14} />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

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
              className={`p-3 rounded-lg border-2 transition-all duration-200 group cursor-pointer ${
                isPlaying ? 'bg-blue-500/25 border-blue-400 shadow-lg shadow-blue-500/30 scale-105' : `${colors.bg} border-slate-600 hover:border-slate-500 hover:shadow-md`
              }`}
            >
              {/* 索引和时间 */}
              <div className="flex items-center justify-between mb-2">
                <span className={`text-xs font-mono font-bold ${isPlaying ? 'text-blue-300' : 'text-slate-400'}`}>#{index + 1}</span>
                <span className={`text-xs font-mono font-semibold ${isPlaying ? 'text-blue-300' : 'text-slate-500'}`}>
                  {subtitle.start_time_formatted} - {subtitle.end_time_formatted}
                </span>
              </div>

              {/* 字幕文本 */}
              {editingIndex === index ? (
                <div className="mb-2" onClick={(e) => e.stopPropagation()}>
                  <textarea value={editingText} onChange={(e) => setEditingText(e.target.value)} className="w-full text-xs leading-relaxed bg-slate-700/50 text-slate-100 border border-blue-500/50 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none" rows={3} autoFocus />
                </div>
              ) : (
                <>
                  <p className={`text-xs leading-relaxed mb-1 ${isPlaying ? 'text-slate-100 font-semibold' : 'text-slate-300'}`}>{subtitle.text}</p>
                  {subtitle.target_text && (
                    <p className="text-xs leading-relaxed mb-2 text-cyan-300 italic border-l-2 border-cyan-500/50 pl-2 bg-cyan-900/10 py-1">
                      {subtitle.target_text}
                    </p>
                  )}
                </>
              )}

              {/* 操作区域 */}
              {editingIndex === index ? (
                <div className="flex gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <button onClick={() => handleSaveEdit(index)} className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-green-600/30 border border-green-500/40 text-green-300 px-2 py-1.5 rounded hover:bg-green-600/50 transition-colors">
                    <Save size={12} />保存
                  </button>
                  <button onClick={handleCancelEdit} className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-gray-600/30 border border-gray-500/40 text-gray-300 px-2 py-1.5 rounded hover:bg-gray-600/50 transition-colors">
                    <X size={12} />取消
                  </button>
                </div>
              ) : sortedSpeakers.length > 0 ? (
                <div className="space-y-1.5" onClick={(e) => e.stopPropagation()}>
                  {/* 原始说话人选择 */}
                  <div className="flex gap-1.5 items-center">
                    <select value={subtitle.speaker_id ?? ''} onChange={(e) => handleSpeakerChange(index, e.target.value ? Number(e.target.value) : undefined)} className={`flex-1 text-xs font-semibold px-2 py-1 rounded border-2 ${subtitle.speaker_id !== undefined ? `${colors.badge} border-transparent` : 'bg-slate-700/50 text-slate-400 border-slate-600'} hover:border-blue-400/50 focus:outline-none cursor-pointer`}>
                      <option value="">选择说话人</option>
                      {sortedSpeakers.map(speakerId => (
                        <option key={speakerId} value={speakerId}>{speakerNameMapping[speakerId] || `说话人${speakerId}`}</option>
                      ))}
                    </select>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onClick={(e) => { e.stopPropagation(); handleStartEdit(index); }} className="flex items-center justify-center text-xs bg-blue-600/30 border border-blue-500/40 text-blue-300 px-2 py-1 rounded hover:bg-blue-600/50 transition-colors" title="编辑">
                        <Edit2 size={11} />
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); handleDeleteSubtitle(index); }} className="flex items-center justify-center text-xs bg-red-600/30 border border-red-500/40 text-red-300 px-2 py-1 rounded hover:bg-red-600/50 transition-colors" title="删除">
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>

                  {/* 克隆音色选择和播放 */}
                  {subtitle.cloned_audio_path && (
                    <div className="flex gap-1.5 items-center">
                      <select
                        value={selectedClonedSpeaker[index] ?? subtitle.cloned_speaker_id ?? ''}
                        onChange={(e) => handleClonedSpeakerChange(index, Number(e.target.value))}
                        className="flex-1 text-xs font-semibold px-2 py-1 rounded border-2 bg-emerald-500/20 border-emerald-500/40 text-emerald-300 hover:border-emerald-400/60 focus:outline-none cursor-pointer"
                      >
                        <option value="">克隆音色</option>
                        {sortedSpeakers.map(speakerId => (
                          <option key={speakerId} value={speakerId}>{speakerNameMapping[speakerId] || `说话人${speakerId}`}</option>
                        ))}
                      </select>
                      <button
                        onClick={(e) => { e.stopPropagation(); handlePlayClonedAudio(subtitle.cloned_audio_path!); }}
                        disabled={regeneratingIndex === index}
                        className={`flex items-center justify-center text-xs px-2 py-1 rounded transition-colors ${
                          regeneratingIndex === index
                            ? 'bg-emerald-600/20 border border-emerald-500/20 text-emerald-400/50 cursor-not-allowed'
                            : 'bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/50'
                        }`}
                        title="播放克隆音频"
                      >
                        {regeneratingIndex === index ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRegenerateSegment(index); }}
                        disabled={regeneratingIndex === index}
                        className={`flex items-center justify-center text-xs px-2 py-1 rounded transition-colors ${
                          regeneratingIndex === index
                            ? 'bg-orange-600/20 border border-orange-500/20 text-orange-400/50 cursor-not-allowed'
                            : 'bg-orange-600/30 border border-orange-500/40 text-orange-300 hover:bg-orange-600/50'
                        }`}
                        title="重新生成"
                      >
                        {regeneratingIndex === index ? <Loader2 size={11} className="animate-spin" /> : <RotateCw size={11} />}
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                  <button onClick={(e) => { e.stopPropagation(); handleStartEdit(index); }} className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-blue-600/30 border border-blue-500/40 text-blue-300 px-2 py-1.5 rounded hover:bg-blue-600/50 transition-colors">
                    <Edit2 size={12} />编辑
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); handleDeleteSubtitle(index); }} className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-red-600/30 border border-red-500/40 text-red-300 px-2 py-1.5 rounded hover:bg-red-600/50 transition-colors">
                    <Trash2 size={12} />删除
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
