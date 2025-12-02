import React from 'react';
import { Trash2, Edit2, Play, Users } from 'lucide-react';

interface Subtitle {
  start_time: number;
  end_time: number;
  start_time_formatted: string;
  end_time_formatted: string;
  text: string;
  speaker_id?: number;
}

interface SubtitleTimelineProps {
  subtitles: Subtitle[];
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  onEditSubtitle?: (index: number, newSubtitle: Subtitle) => void;
  onDeleteSubtitle?: (index: number) => void;
}

const SubtitleTimeline: React.FC<SubtitleTimelineProps> = ({
  subtitles,
  currentTime,
  duration,
  onSeek,
  onEditSubtitle,
  onDeleteSubtitle
}) => {
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

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickPosition = e.clientX - rect.left;
    const timelineWidth = rect.width;
    const time = (clickPosition / timelineWidth) * duration;
    onSeek(time);
  };

  const handleDeleteSubtitle = (index: number) => {
    if (onDeleteSubtitle) {
      onDeleteSubtitle(index);
    }
  };

  const handleEditSubtitle = (index: number) => {
    if (onEditSubtitle) {
      const currentSubtitle = subtitles[index];
      const newText = prompt('编辑字幕文本:', currentSubtitle.text);
      if (newText !== null) {
        const updatedSubtitle = {
          ...currentSubtitle,
          text: newText
        };
        onEditSubtitle(index, updatedSubtitle);
      }
    }
  };

  return (
    <div className="w-full">
      {/* 时间轴标签 */}
      <div className="flex justify-between text-xs font-mono text-slate-400 mb-2">
        <span>00:00</span>
        <span>{new Date(duration * 1000).toISOString().substr(11, 8)}</span>
      </div>

      {/* 主时间轴 */}
      <div 
        className="relative h-24 bg-gradient-to-b from-slate-700 to-slate-800 rounded-lg cursor-pointer border border-slate-600 hover:border-slate-500 transition-colors shadow-lg overflow-hidden"
        onClick={handleTimelineClick}
      >
        {/* 背景网格 */}
        <div className="absolute inset-0 opacity-10">
          {[...Array(10)].map((_, i) => (
            <div
              key={i}
              className="absolute h-full border-l border-slate-500"
              style={{ left: `${(i + 1) * 10}%` }}
            />
          ))}
        </div>

        {/* 字幕块 */}
        <div className="absolute top-0 left-0 w-full h-full">
          {subtitles.map((subtitle, index) => {
            const left = (subtitle.start_time / duration) * 100;
            const width = ((subtitle.end_time - subtitle.start_time) / duration) * 100;
            const isPlaying = currentTime >= subtitle.start_time && currentTime <= subtitle.end_time;
            const colors = getColorBySpacker(subtitle.speaker_id);
            
            return (
              <div
                key={index}
                className={`absolute top-2.5 h-16 flex flex-col items-center justify-center rounded-md overflow-hidden border-2 transition-all duration-200 cursor-pointer group
                  ${isPlaying 
                    ? 'bg-gradient-to-br from-blue-600 to-blue-500 border-blue-300 shadow-lg shadow-blue-500/50 scale-105' 
                    : `${colors.bg} border-slate-500 hover:border-blue-400 hover:shadow-md`
                  }`}
                style={{
                  left: `${left}%`,
                  width: `${Math.max(width, 2)}%`,
                  minWidth: '50px'
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek(subtitle.start_time);
                }}
              >
                {subtitle.speaker_id !== undefined && (
                  <span className={`text-xs font-bold truncate max-w-[70px] ${isPlaying ? 'text-white' : 'text-slate-300'}`}>
                    说话人 {subtitle.speaker_id}
                  </span>
                )}
                <span className={`text-xs px-1 truncate max-w-full text-center leading-tight ${isPlaying ? 'text-white' : 'text-slate-300'}`}>
                  {subtitle.text.length > 20 ? `${subtitle.text.substring(0, 20)}...` : subtitle.text}
                </span>
              </div>
            );
          })}
        </div>

        {/* 播放头指示器 */}
        <div
          className="absolute top-0 h-full w-1 bg-gradient-to-b from-red-500 to-red-600 z-20 shadow-lg"
          style={{
            left: `${(currentTime / duration) * 100}%`
          }}
        >
          <div className="absolute -top-1.5 -left-1.5 w-4 h-4 bg-red-500 border-2 border-white rounded-full shadow-lg"></div>
        </div>
      </div>

      {/* 字幕列表区域 */}
      <div className="mt-5 space-y-2 max-h-56 overflow-y-auto">
        {subtitles.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p className="text-sm">暂无字幕</p>
          </div>
        ) : (
          subtitles.map((subtitle, index) => {
            const isPlaying = currentTime >= subtitle.start_time && currentTime <= subtitle.end_time;
            const colors = getColorBySpacker(subtitle.speaker_id);
            
            return (
              <div 
                key={index}
                className={`p-3.5 rounded-lg border-2 transition-all duration-200 group
                  ${isPlaying
                    ? 'bg-blue-500/20 border-blue-400 shadow-lg shadow-blue-500/20'
                    : `${colors.bg} border-slate-600 hover:border-slate-500`
                  }`}
              >
                {/* 时间戳和操作按钮 */}
                <div className="flex justify-between items-center mb-2.5">
                  <span className={`text-xs font-mono font-semibold ${isPlaying ? 'text-blue-300' : 'text-slate-400'}`}>
                    {subtitle.start_time_formatted} → {subtitle.end_time_formatted}
                  </span>
                  <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    {subtitle.speaker_id !== undefined && (
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded ${colors.badge}`}>
                        <Users size={12} />
                        说话人 {subtitle.speaker_id}
                      </span>
                    )}
                  </div>
                </div>

                {/* 字幕文本 */}
                <p className={`text-sm leading-relaxed mb-3 ${isPlaying ? 'text-slate-100 font-medium' : 'text-slate-300'}`}>
                  {subtitle.text}
                </p>

                {/* 操作按钮 */}
                <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    className="flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold bg-blue-600/20 border border-blue-500/30 text-blue-300 px-2.5 py-1.5 rounded hover:bg-blue-600/40 hover:border-blue-400/50 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEditSubtitle(index);
                    }}
                  >
                    <Edit2 size={14} />
                    编辑
                  </button>
                  <button 
                    className="flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold bg-red-600/20 border border-red-500/30 text-red-300 px-2.5 py-1.5 rounded hover:bg-red-600/40 hover:border-red-400/50 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteSubtitle(index);
                    }}
                  >
                    <Trash2 size={14} />
                    删除
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default SubtitleTimeline;