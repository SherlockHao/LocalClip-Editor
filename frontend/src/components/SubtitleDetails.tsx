import React, { useEffect, useRef, useState } from 'react';
import { Trash2, Edit2, Users, FileText, Save, X, Plus, Minus, Play, RotateCw, Loader2, ChevronDown, Volume2 } from 'lucide-react';

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

interface DefaultVoice {
  id: string;
  name: string;
  audio_url: string;
  reference_text: string;
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
  onRegenerateSegment?: (index: number, newSpeakerId: number, newTargetText?: string) => void;
  voiceCloningTaskId?: string;
  filteredSpeakerId?: number | null;
  onFilteredSpeakerChange?: (speakerId: number | null) => void;
  defaultVoices?: DefaultVoice[];
  speakerVoiceMapping?: {[speakerId: string]: string};
  onSpeakerVoiceMappingChange?: (mapping: {[speakerId: string]: string}) => void;
  onRegenerateVoices?: () => void;
  hasVoiceMappingChanged?: boolean;
  isRegeneratingVoices?: boolean;
  isProcessingVoiceCloning?: boolean;
  isStitchingAudio?: boolean;
  targetLanguage?: string;
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
  voiceCloningTaskId,
  filteredSpeakerId = null,
  onFilteredSpeakerChange,
  defaultVoices = [],
  speakerVoiceMapping = {},
  onSpeakerVoiceMappingChange,
  onRegenerateVoices,
  hasVoiceMappingChanged = false,
  isRegeneratingVoices = false,
  isProcessingVoiceCloning = false,
  isStitchingAudio = false,
  targetLanguage = ''
}) => {
  const activeSubtitleRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const voiceButtonRefs = useRef<{[speakerId: number]: HTMLButtonElement | null}>({});
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingText, setEditingText] = useState<string>('');
  const [editingTargetText, setEditingTargetText] = useState<string>('');
  const [editingSourceText, setEditingSourceText] = useState<string>('');
  const [selectedClonedSpeaker, setSelectedClonedSpeaker] = useState<{[index: number]: number}>({});
  const [regeneratingIndex, setRegeneratingIndex] = useState<number | null>(null);
  const [openVoiceMenuSpeakerId, setOpenVoiceMenuSpeakerId] = useState<number | null>(null);
  const [voiceMenuPosition, setVoiceMenuPosition] = useState<{top: number, left: number} | null>(null);

  // 保存初始状态用于检测变化
  const [initialSubtitleState, setInitialSubtitleState] = useState<{[index: number]: {text: string, target_text: string, speaker_id?: number}}>({});

  // 调试：检查接收到的 defaultVoices
  useEffect(() => {
    console.log('[SubtitleDetails] 接收到的 defaultVoices:', defaultVoices);
  }, [defaultVoices]);

  // 保存字幕的初始状态
  useEffect(() => {
    const newInitialState: {[index: number]: {text: string, target_text: string, speaker_id?: number}} = {};
    subtitles.forEach((subtitle, index) => {
      if (!initialSubtitleState[index]) {
        newInitialState[index] = {
          text: subtitle.text,
          target_text: subtitle.target_text || '',
          speaker_id: subtitle.speaker_id
        };
      }
    });
    if (Object.keys(newInitialState).length > 0) {
      setInitialSubtitleState(prev => ({ ...prev, ...newInitialState }));
    }
  }, [subtitles]);

  const uniqueSpeakers = getUniqueSpeakers(subtitles);

  // 根据筛选条件过滤字幕，保留原始索引
  const filteredSubtitlesWithIndex = filteredSpeakerId !== null
    ? subtitles
        .map((sub, idx) => ({ subtitle: sub, originalIndex: idx }))
        .filter(item => item.subtitle.speaker_id === filteredSpeakerId)
    : subtitles.map((sub, idx) => ({ subtitle: sub, originalIndex: idx }));

  // 切换说话人筛选
  const toggleSpeakerFilter = (speakerId: number) => {
    if (onFilteredSpeakerChange) {
      onFilteredSpeakerChange(filteredSpeakerId === speakerId ? null : speakerId);
    }
  };

  // 音色选择处理
  const handleVoiceSelect = (speakerId: number, voiceId: string) => {
    if (onSpeakerVoiceMappingChange) {
      const newMapping = { ...speakerVoiceMapping, [speakerId.toString()]: voiceId };
      onSpeakerVoiceMappingChange(newMapping);
    }
  };

  // 播放默认音色预览
  const handlePlayDefaultVoice = (audioUrl: string) => {
    const audio = new Audio(audioUrl);
    audio.play().catch(err => console.error('播放失败:', err));
  };

  // 获取当前说话人选择的音色
  const getSelectedVoice = (speakerId: number): string => {
    return speakerVoiceMapping[speakerId.toString()] || 'default';
  };

  // 获取音色显示名称
  const getVoiceName = (voiceId: string): string => {
    if (voiceId === 'default') return '原音色';
    const voice = defaultVoices.find(v => v.id === voiceId);
    return voice ? voice.name : '未知';
  };

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

  const handleStartEdit = (index: number, field: 'text' | 'target_text') => {
    setEditingIndex(index);
    if (field === 'text') {
      setEditingSourceText(subtitles[index].text);
      setEditingTargetText(''); // 不编辑target
    } else {
      setEditingTargetText(subtitles[index].target_text || '');
      setEditingSourceText(''); // 不编辑source
    }
  };

  const handleSaveEdit = (index: number) => {
    if (onEditSubtitle) {
      const updates: Partial<Subtitle> = {};
      if (editingSourceText) {
        updates.text = editingSourceText;
      }
      if (editingTargetText) {
        updates.target_text = editingTargetText;
      }
      onEditSubtitle(index, { ...subtitles[index], ...updates });
    }
    setEditingIndex(null);
    setEditingSourceText('');
    setEditingTargetText('');
  };

  const handleCancelEdit = () => {
    setEditingIndex(null);
    setEditingSourceText('');
    setEditingTargetText('');
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
    if (!onRegenerateSegment || !voiceCloningTaskId || !targetLanguage) return;

    const subtitle = subtitles[index];
    const initialState = initialSubtitleState[index];

    if (!initialState) {
      console.warn('[重新生成] 没有找到初始状态，使用当前说话人');
      const newSpeakerId = subtitle.speaker_id;
      if (newSpeakerId !== undefined) {
        setRegeneratingIndex(index);
        try {
          await onRegenerateSegment(index, newSpeakerId);
        } finally {
          setRegeneratingIndex(null);
        }
      }
      return;
    }

    const sourceTextChanged = subtitle.text !== initialState.text;
    const targetTextChanged = subtitle.target_text !== initialState.target_text;
    const speakerChanged = subtitle.speaker_id !== initialState.speaker_id;

    console.log('[重新生成] 变化检测:', {
      sourceTextChanged,
      targetTextChanged,
      speakerChanged,
      currentText: subtitle.text,
      initialText: initialState.text,
      currentTarget: subtitle.target_text,
      initialTarget: initialState.target_text
    });

    setRegeneratingIndex(index);

    try {
      let targetTextToUse = subtitle.target_text;

      // (a) 原文变化 - 优先级最高
      if (sourceTextChanged) {
        console.log('[重新生成] 原文发生变化，调用LLM翻译');
        console.log('[重新生成] 原文:', subtitle.text);
        console.log('[重新生成] 目标语言:', targetLanguage);

        // 无论译文是否修改，都重新翻译原文
        try {
          console.log('[重新生成] 开始调用翻译API...');
          const response = await fetch('/api/translate-text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              text: subtitle.text,
              target_language: targetLanguage
            })
          });

          if (response.ok) {
            const data = await response.json();
            targetTextToUse = data.translation;
            console.log('[重新生成] 翻译成功:', targetTextToUse);

            // 更新字幕以显示新译文
            if (onEditSubtitle) {
              onEditSubtitle(index, { ...subtitle, target_text: targetTextToUse });
            }
          } else {
            const errorText = await response.text();
            console.error('[重新生成] 翻译失败:', errorText);
            // 翻译失败时使用原文
            targetTextToUse = subtitle.text;
            alert('翻译失败，将使用原文生成语音');
          }
        } catch (error) {
          console.error('[重新生成] 翻译请求异常:', error);
          // 翻译异常时使用原文
          targetTextToUse = subtitle.text;
          alert('翻译超时或失败，将使用原文生成语音');
        }
      }
      // (b) 目标文本变化
      else if (targetTextChanged) {
        console.log('[重新生成] 译文发生变化，使用新译文');
        targetTextToUse = subtitle.target_text;
      }
      // (c) 说话人变化
      else if (speakerChanged) {
        console.log('[重新生成] 说话人发生变化');
        targetTextToUse = subtitle.target_text;
      }
      // (d) 没有变化
      else {
        console.log('[重新生成] 没有检测到变化');
        targetTextToUse = subtitle.target_text;
      }

      // 使用当前说话人重新生成
      const speakerId = subtitle.speaker_id;
      if (speakerId !== undefined) {
        console.log('[重新生成] 开始生成音频，说话人:', speakerId, '译文:', targetTextToUse);
        await onRegenerateSegment(index, speakerId, targetTextToUse);

        // 更新初始状态
        setInitialSubtitleState(prev => ({
          ...prev,
          [index]: {
            text: subtitle.text,
            target_text: targetTextToUse || '',
            speaker_id: speakerId
          }
        }));
      }
    } catch (error) {
      console.error('[重新生成] 失败:', error);
      alert('重新生成失败: ' + (error as Error).message);
    } finally {
      setRegeneratingIndex(null);
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
    <div className="w-[45%] flex-shrink-0 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 rounded-xl shadow-xl flex flex-col overflow-hidden">
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
                const isFiltered = filteredSpeakerId === speaker.id;
                const isDimmed = filteredSpeakerId !== null && !isFiltered;
                const selectedVoice = getSelectedVoice(speaker.id);
                return (
                  <div key={speaker.id} className="flex-shrink-0 flex items-center space-x-1">
                    <button
                      onClick={() => toggleSpeakerFilter(speaker.id)}
                      className={`px-3 py-1.5 rounded-lg border-2 text-xs font-semibold transition-all cursor-pointer ${
                        isFiltered
                          ? `${colors.badge} ${colors.border} ring-2 ring-blue-400 shadow-lg`
                          : isDimmed
                          ? 'bg-slate-700/30 border-slate-600/30 text-slate-500 opacity-40'
                          : `${colors.badge} ${colors.border} hover:ring-2 hover:ring-blue-400/50`
                      }`}
                    >
                      {speaker.name}
                    </button>
                    <button
                      ref={(el) => { voiceButtonRefs.current[speaker.id] = el; }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (openVoiceMenuSpeakerId === speaker.id) {
                          setOpenVoiceMenuSpeakerId(null);
                          setVoiceMenuPosition(null);
                        } else {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setVoiceMenuPosition({
                            top: rect.bottom + 4,
                            left: rect.left
                          });
                          setOpenVoiceMenuSpeakerId(speaker.id);
                        }
                      }}
                      className="w-5 h-5 rounded bg-slate-700/50 hover:bg-slate-600 flex items-center justify-center text-slate-400 hover:text-slate-200 transition-all"
                      title="选择音色"
                    >
                      <ChevronDown size={12} />
                    </button>
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
                const isFiltered = filteredSpeakerId === speaker.id;
                const isDimmed = filteredSpeakerId !== null && !isFiltered;
                const selectedVoice = getSelectedVoice(speaker.id);
                return (
                  <div key={speaker.id} className="flex-shrink-0 flex items-center space-x-1">
                    <button
                      onClick={() => toggleSpeakerFilter(speaker.id)}
                      className={`px-3 py-1.5 rounded-lg border-2 text-xs font-semibold transition-all cursor-pointer ${
                        isFiltered
                          ? `${colors.badge} ${colors.border} ring-2 ring-pink-400 shadow-lg`
                          : isDimmed
                          ? 'bg-slate-700/30 border-slate-600/30 text-slate-500 opacity-40'
                          : `${colors.badge} ${colors.border} hover:ring-2 hover:ring-pink-400/50`
                      }`}
                    >
                      {speaker.name}
                    </button>
                    <button
                      ref={(el) => { voiceButtonRefs.current[speaker.id] = el; }}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (openVoiceMenuSpeakerId === speaker.id) {
                          setOpenVoiceMenuSpeakerId(null);
                          setVoiceMenuPosition(null);
                        } else {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setVoiceMenuPosition({
                            top: rect.bottom + 4,
                            left: rect.left
                          });
                          setOpenVoiceMenuSpeakerId(speaker.id);
                        }
                      }}
                      className="w-5 h-5 rounded bg-slate-700/50 hover:bg-slate-600 flex items-center justify-center text-slate-400 hover:text-slate-200 transition-all"
                      title="选择音色"
                    >
                      <ChevronDown size={12} />
                    </button>
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

          {/* 重新生成按钮 */}
          {voiceCloningTaskId && (
            <div className="mt-3 pt-3 border-t border-slate-700">
              <button
                onClick={onRegenerateVoices}
                disabled={!hasVoiceMappingChanged || isRegeneratingVoices || isProcessingVoiceCloning || isStitchingAudio}
                className={`w-full flex items-center justify-center space-x-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                  hasVoiceMappingChanged && !isRegeneratingVoices && !isProcessingVoiceCloning && !isStitchingAudio
                    ? 'bg-gradient-to-r from-purple-600 to-purple-500 hover:from-purple-500 hover:to-purple-400 text-white shadow-lg hover:shadow-purple-500/50'
                    : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
                }`}
                title={!hasVoiceMappingChanged ? '音色未变化' : isRegeneratingVoices ? '正在重新生成...' : '重新生成变化的音色'}
              >
                {isRegeneratingVoices ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    <span>重新生成中...</span>
                  </>
                ) : (
                  <>
                    <RotateCw size={14} />
                    <span>重新生成音色</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* 字幕列表 */}
      <div ref={containerRef} className="flex-1 overflow-y-auto p-4 space-y-2.5">
        {filteredSubtitlesWithIndex.map(({ subtitle, originalIndex }) => {
          const index = originalIndex; // 使用原始索引
          const isPlaying = currentTime >= subtitle.start_time && currentTime <= subtitle.end_time;
          const colors = getColorBySpacker(subtitle.speaker_id);

          // 获取当前音色名称
          const currentVoiceName = subtitle.speaker_id !== undefined
            ? getVoiceName(getSelectedVoice(subtitle.speaker_id))
            : '';

          return (
            <div
              key={index}
              ref={isPlaying ? activeSubtitleRef : null}
              className={`relative p-3 rounded-lg border-2 transition-all duration-200 group ${
                isPlaying ? 'bg-blue-500/25 border-blue-400 shadow-lg shadow-blue-500/30 scale-105' : `${colors.bg} border-slate-600 hover:border-slate-500 hover:shadow-md`
              }`}
            >
              {/* 右上角删除按钮 */}
              <button
                onClick={(e) => { e.stopPropagation(); handleDeleteSubtitle(index); }}
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-xs bg-red-600/30 border border-red-500/40 text-red-300 px-1.5 py-1 rounded hover:bg-red-600/50"
                title="删除"
              >
                <Trash2 size={11} />
              </button>

              {/* 索引和时间 */}
              <div className="flex items-center justify-between mb-2 pr-8">
                <span className={`text-xs font-mono font-bold ${isPlaying ? 'text-blue-300' : 'text-slate-400'}`}>#{index + 1}</span>
                <span className={`text-xs font-mono font-semibold ${isPlaying ? 'text-blue-300' : 'text-slate-500'}`}>
                  {subtitle.start_time_formatted} - {subtitle.end_time_formatted}
                </span>
              </div>

              {/* 字幕文本 - 可点击编辑 */}
              {editingIndex === index && editingSourceText ? (
                <div className="mb-2" onClick={(e) => e.stopPropagation()}>
                  <label className="text-xs text-slate-400 mb-1 block">编辑原文:</label>
                  <textarea
                    value={editingSourceText}
                    onChange={(e) => setEditingSourceText(e.target.value)}
                    className="w-full text-xs leading-relaxed bg-slate-700/50 text-slate-100 border border-blue-500/50 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
                    rows={2}
                    autoFocus
                  />
                </div>
              ) : (
                <p
                  className={`text-xs leading-relaxed mb-1 cursor-text hover:bg-slate-700/30 rounded px-1 py-0.5 -mx-1 ${isPlaying ? 'text-slate-100 font-semibold' : 'text-slate-300'}`}
                  onClick={(e) => { e.stopPropagation(); handleStartEdit(index, 'text'); }}
                  title="点击编辑原文"
                >
                  {subtitle.text}
                </p>
              )}

              {editingIndex === index && editingTargetText !== '' ? (
                <div className="mb-2" onClick={(e) => e.stopPropagation()}>
                  <label className="text-xs text-cyan-400 mb-1 block">编辑译文:</label>
                  <textarea
                    value={editingTargetText}
                    onChange={(e) => setEditingTargetText(e.target.value)}
                    className="w-full text-xs leading-relaxed bg-slate-700/50 text-cyan-100 border border-cyan-500/50 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 resize-none"
                    rows={2}
                    autoFocus
                  />
                </div>
              ) : subtitle.target_text && (
                <p
                  className="text-xs leading-relaxed mb-2 text-cyan-300 italic border-l-2 border-cyan-500/50 pl-2 bg-cyan-900/10 py-1 cursor-text hover:bg-cyan-900/20"
                  onClick={(e) => { e.stopPropagation(); handleStartEdit(index, 'target_text'); }}
                  title="点击编辑译文"
                >
                  {subtitle.target_text}
                </p>
              )}

              {/* 保存/取消编辑按钮 */}
              {editingIndex === index && (
                <div className="flex gap-1.5 mb-2" onClick={(e) => e.stopPropagation()}>
                  <button onClick={() => handleSaveEdit(index)} className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-green-600/30 border border-green-500/40 text-green-300 px-2 py-1.5 rounded hover:bg-green-600/50 transition-colors">
                    <Save size={12} />保存
                  </button>
                  <button onClick={handleCancelEdit} className="flex-1 flex items-center justify-center gap-1 text-xs font-semibold bg-gray-600/30 border border-gray-500/40 text-gray-300 px-2 py-1.5 rounded hover:bg-gray-600/50 transition-colors">
                    <X size={12} />取消
                  </button>
                </div>
              )}

              {/* 操作区域 - 新布局 */}
              {sortedSpeakers.length > 0 && subtitle.cloned_audio_path && (
                <div className="flex gap-1.5 items-center" onClick={(e) => e.stopPropagation()}>
                  {/* 说话人下拉菜单 */}
                  <select
                    value={subtitle.speaker_id ?? ''}
                    onChange={(e) => handleSpeakerChange(index, e.target.value ? Number(e.target.value) : undefined)}
                    className={`text-xs font-semibold px-2 py-1 rounded border-2 ${subtitle.speaker_id !== undefined ? `${colors.badge} border-transparent` : 'bg-slate-700/50 text-slate-400 border-slate-600'} hover:border-blue-400/50 focus:outline-none cursor-pointer`}
                  >
                    <option value="">选择说话人</option>
                    {sortedSpeakers.map(speakerId => (
                      <option key={speakerId} value={speakerId}>{speakerNameMapping[speakerId] || `说话人${speakerId}`}</option>
                    ))}
                  </select>

                  {/* 当前音色显示（不可编辑） */}
                  <div className="text-xs bg-slate-700/50 text-slate-300 px-2 py-1 rounded border border-slate-600">
                    {currentVoiceName}
                  </div>

                  {/* 播放按钮 */}
                  <button
                    onClick={(e) => { e.stopPropagation(); handlePlayClonedAudio(subtitle.cloned_audio_path!); }}
                    disabled={regeneratingIndex === index || isRegeneratingVoices}
                    className={`flex items-center justify-center text-xs px-2 py-1 rounded transition-colors ${
                      regeneratingIndex === index || isRegeneratingVoices
                        ? 'bg-emerald-600/20 border border-emerald-500/20 text-emerald-400/50 cursor-not-allowed'
                        : 'bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-600/50'
                    }`}
                    title={isRegeneratingVoices ? "正在重新生成音色..." : "播放克隆音频"}
                  >
                    {regeneratingIndex === index ? <Loader2 size={11} className="animate-spin" /> : <Play size={11} />}
                  </button>

                  {/* 重新生成按钮 */}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleRegenerateSegment(index); }}
                    disabled={regeneratingIndex === index || isRegeneratingVoices}
                    className={`flex items-center justify-center text-xs px-2 py-1 rounded transition-colors ${
                      regeneratingIndex === index || isRegeneratingVoices
                        ? 'bg-orange-600/20 border border-orange-500/20 text-orange-400/50 cursor-not-allowed'
                        : 'bg-orange-600/30 border border-orange-500/40 text-orange-300 hover:bg-orange-600/50'
                    }`}
                    title={isRegeneratingVoices ? "正在重新生成音色..." : "重新生成"}
                  >
                    {regeneratingIndex === index ? <Loader2 size={11} className="animate-spin" /> : <RotateCw size={11} />}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Fixed 定位的下拉菜单 - 渲染在最上层 */}
      {openVoiceMenuSpeakerId !== null && voiceMenuPosition && (
        <>
          {/* 遮罩层 - 点击关闭菜单 */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => {
              setOpenVoiceMenuSpeakerId(null);
              setVoiceMenuPosition(null);
            }}
          />

          {/* 下拉菜单 */}
          <div
            className="fixed z-50 bg-slate-800 border border-slate-700 rounded-lg shadow-xl min-w-[140px]"
            style={{
              top: `${voiceMenuPosition.top}px`,
              left: `${voiceMenuPosition.left}px`
            }}
          >
            {(() => {
              const selectedVoice = speakerVoiceMapping[openVoiceMenuSpeakerId.toString()] || 'default';
              console.log('[下拉菜单] defaultVoices:', defaultVoices);
              console.log('[下拉菜单] defaultVoices 数量:', defaultVoices.length);
              return (
                <>
                  <button
                    onClick={() => {
                      handleVoiceSelect(openVoiceMenuSpeakerId, 'default');
                      setOpenVoiceMenuSpeakerId(null);
                      setVoiceMenuPosition(null);
                    }}
                    className={`w-full px-3 py-2 text-xs text-left hover:bg-slate-700 transition-colors ${
                      selectedVoice === 'default' ? 'bg-slate-700 text-blue-400' : 'text-slate-300'
                    }`}
                  >
                    原音色
                  </button>
                  {defaultVoices.map(voice => (
                    <div
                      key={voice.id}
                      className={`w-full px-3 py-2 text-xs hover:bg-slate-700 transition-colors flex items-center justify-between ${
                        selectedVoice === voice.id ? 'bg-slate-700 text-blue-400' : 'text-slate-300'
                      }`}
                    >
                      <span
                        onClick={() => {
                          handleVoiceSelect(openVoiceMenuSpeakerId, voice.id);
                          setOpenVoiceMenuSpeakerId(null);
                          setVoiceMenuPosition(null);
                        }}
                        className="flex-1 cursor-pointer"
                      >
                        {voice.name}
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePlayDefaultVoice(voice.audio_url);
                        }}
                        className="ml-2 w-4 h-4 flex items-center justify-center hover:text-blue-400 flex-shrink-0"
                        title="试听"
                      >
                        <Volume2 size={12} />
                      </button>
                    </div>
                  ))}
                </>
              );
            })()}
          </div>
        </>
      )}
    </div>
  );
};

export default SubtitleDetails;
