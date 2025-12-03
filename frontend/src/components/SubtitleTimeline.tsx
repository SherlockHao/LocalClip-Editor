import React from 'react';

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
}

const SubtitleTimeline: React.FC<SubtitleTimelineProps> = ({
  subtitles,
  currentTime,
  duration,
  onSeek
}) => {
  const speakerColors = [
    { bg: 'from-blue-600 to-blue-500', border: 'border-blue-400' },
    { bg: 'from-green-600 to-green-500', border: 'border-green-400' },
    { bg: 'from-yellow-600 to-yellow-500', border: 'border-yellow-400' },
    { bg: 'from-purple-600 to-purple-500', border: 'border-purple-400' },
    { bg: 'from-pink-600 to-pink-500', border: 'border-pink-400' },
    { bg: 'from-indigo-600 to-indigo-500', border: 'border-indigo-400' }
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

  return (
    <div className="w-full">
      {/* 时间轴标签 */}
      <div className="flex justify-between text-xs font-mono text-slate-400 mb-3">
        <span className="font-semibold">00:00</span>
        <span className="font-semibold">{new Date(duration * 1000).toISOString().substr(11, 8)}</span>
      </div>

      {/* 主时间轴 */}
      <div 
        className="relative h-28 bg-gradient-to-b from-slate-700 to-slate-800 rounded-lg cursor-pointer border-2 border-slate-600 hover:border-slate-500 transition-colors shadow-lg overflow-hidden"
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
                className={`absolute top-3 h-20 flex flex-col items-center justify-center rounded-md overflow-hidden border-2 transition-all duration-200 cursor-pointer group
                  ${isPlaying 
                    ? `bg-gradient-to-br ${colors.bg} ${colors.border} shadow-lg scale-110` 
                    : `bg-slate-600/40 border-slate-500 hover:border-slate-300 hover:shadow-md hover:bg-slate-600/60`
                  }`}
                style={{
                  left: `${left}%`,
                  width: `${Math.max(width, 2.5)}%`,
                  minWidth: '45px'
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek(subtitle.start_time);
                }}
                title={subtitle.text}
              >
                {subtitle.speaker_id !== undefined && (
                  <span className={`text-xs font-bold truncate max-w-[70px] ${isPlaying ? 'text-white' : 'text-slate-300'}`}>
                    说话人{subtitle.speaker_id}
                  </span>
                )}
                <span className={`text-xs px-1 truncate max-w-full text-center leading-tight ${isPlaying ? 'text-white' : 'text-slate-300'}`}>
                  {subtitle.text.length > 15 ? `${subtitle.text.substring(0, 15)}...` : subtitle.text}
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
          <div className="absolute -top-2 -left-2 w-5 h-5 bg-red-500 border-2 border-white rounded-full shadow-lg"></div>
        </div>
      </div>

      {/* 提示信息 */}
      <div className="mt-3 text-xs text-slate-500 text-center font-medium">
        点击时间轴或字幕卡片快速定位 • 总共 {subtitles.length} 条字幕
      </div>
    </div>
  );
};

export default SubtitleTimeline;