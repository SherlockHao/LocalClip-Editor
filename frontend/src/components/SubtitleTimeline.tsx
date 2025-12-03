import React, { useState, useRef, useEffect } from 'react';

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
  const [zoom, setZoom] = useState(1); // 缩放级别，1 = 100%
  const [scrollOffset, setScrollOffset] = useState(0); // 滚动偏移量（像素）
  const timelineRef = useRef<HTMLDivElement>(null);
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

  // 处理缩放
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      // 检查是否在时间轴上
      if (!timelineRef.current?.contains(e.target as Node)) return;

      // Ctrl/Cmd + 滚轮 = 缩放
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();

        const rect = timelineRef.current.getBoundingClientRect();
        const mouseX = e.clientX - rect.left; // 鼠标在时间轴上的位置
        const mousePositionRatio = (mouseX + scrollOffset) / (rect.width * zoom); // 鼠标位置对应的时间比例

        // 计算新的缩放级别
        const zoomDelta = -e.deltaY * 0.01;
        const newZoom = Math.max(1, Math.min(10, zoom + zoomDelta)); // 限制在1x到10x之间

        // 调整滚动偏移，使鼠标位置保持不变
        const newScrollOffset = mousePositionRatio * rect.width * newZoom - mouseX;
        const maxScroll = rect.width * (newZoom - 1);

        setZoom(newZoom);
        setScrollOffset(Math.max(0, Math.min(maxScroll, newScrollOffset)));
      } else {
        // 普通滚轮 = 水平滚动（当放大时）
        if (zoom > 1) {
          e.preventDefault();

          const rect = timelineRef.current.getBoundingClientRect();
          const maxScroll = rect.width * (zoom - 1);
          const newOffset = scrollOffset + e.deltaY;

          setScrollOffset(Math.max(0, Math.min(maxScroll, newOffset)));
        }
      }
    };

    const timeline = timelineRef.current;
    if (timeline) {
      timeline.addEventListener('wheel', handleWheel, { passive: false });
    }

    return () => {
      if (timeline) {
        timeline.removeEventListener('wheel', handleWheel);
      }
    };
  }, [zoom, scrollOffset]);

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickPosition = e.clientX - rect.left + scrollOffset;
    const timelineWidth = rect.width * zoom;
    const time = (clickPosition / timelineWidth) * duration;
    console.log('=== [SubtitleTimeline] 点击进度条，计算时间:', time, '秒 ===');
    onSeek(time);
  };

  return (
    <div className="w-full">
      {/* 时间轴标签和缩放提示 */}
      <div className="flex justify-between items-center text-xs font-mono text-slate-400 mb-3">
        <span className="font-semibold">00:00</span>
        <span className="text-xs text-slate-500">
          {zoom > 1 ? `缩放: ${zoom.toFixed(1)}x | 滚轮滚动，Ctrl+滚轮缩放` : 'Ctrl+滚轮缩放时间轴'}
        </span>
        <span className="font-semibold">{new Date(duration * 1000).toISOString().substr(11, 8)}</span>
      </div>

      {/* 主时间轴 */}
      <div
        ref={timelineRef}
        className="relative h-28 bg-gradient-to-b from-slate-700 to-slate-800 rounded-lg cursor-pointer border-2 border-slate-600 hover:border-slate-500 transition-colors shadow-lg overflow-hidden"
        onClick={handleTimelineClick}
      >
        {/* 可缩放的内容容器 */}
        <div
          className="absolute top-0 left-0 h-full"
          style={{
            width: `${100 * zoom}%`,
            transform: `translateX(-${scrollOffset}px)`,
            transition: 'transform 0.1s ease-out'
          }}
        >
          {/* 背景网格 */}
          <div className="absolute inset-0 opacity-10">
            {[...Array(Math.ceil(10 * zoom))].map((_, i) => (
              <div
                key={i}
                className="absolute h-full border-l border-slate-500"
                style={{ left: `${((i + 1) * 10) / zoom}%` }}
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
                    width: `${Math.max(width, 2.5 / zoom)}%`,
                    minWidth: '45px'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    console.log('=== [SubtitleTimeline] 点击字幕块，跳转到:', subtitle.start_time, '秒 ===');
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
      </div>

      {/* 提示信息 */}
      <div className="mt-3 text-xs text-slate-500 text-center font-medium">
        点击时间轴或字幕卡片快速定位 • 总共 {subtitles.length} 条字幕
      </div>
    </div>
  );
};

export default SubtitleTimeline;