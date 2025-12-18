import React, { useState, useRef, useEffect } from 'react';
import { Loader2, Wand2 } from 'lucide-react';

interface Subtitle {
  start_time: number;
  end_time: number;
  start_time_formatted: string;
  end_time_formatted: string;
  text: string;
  speaker_id?: number;
  target_text?: string;
  cloned_audio_path?: string;
  actual_start_time?: number;  // 重新规划后的实际开始时间
  actual_end_time?: number;    // 重新规划后的实际结束时间
}

interface SubtitleTimelineProps {
  subtitles: Subtitle[];
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  onStitchAudio?: () => void;
  stitching?: boolean;
}

const SubtitleTimeline: React.FC<SubtitleTimelineProps> = ({
  subtitles,
  currentTime,
  duration,
  onSeek,
  onStitchAudio,
  stitching = false
}) => {
  const [zoom, setZoom] = useState(1); // 缩放级别，1 = 100%
  const [scrollOffset, setScrollOffset] = useState(0); // 滚动偏移量（像素）
  const [isDragging, setIsDragging] = useState(false);
  const [isZooming, setIsZooming] = useState(false); // 缩放状态
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartOffset, setDragStartOffset] = useState(0);

  const timelineRef = useRef<HTMLDivElement>(null);
  const zoomTimeoutRef = useRef<NodeJS.Timeout | null>(null);

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

  // 处理拖拽
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      const deltaX = e.clientX - dragStartX;
      const newOffset = dragStartOffset - deltaX;

      const rect = timelineRef.current?.getBoundingClientRect();
      if (rect) {
        const maxScroll = rect.width * (zoom - 1);
        setScrollOffset(Math.max(0, Math.min(maxScroll, newOffset)));
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, dragStartX, dragStartOffset, zoom]);

  // 处理滚轮缩放
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      const target = e.target as Node;
      if (!timelineRef.current?.contains(target)) return;

      e.preventDefault();

      const rect = timelineRef.current?.getBoundingClientRect();
      if (!rect) return;

      const mouseX = e.clientX - rect.left;
      const mousePositionRatio = (mouseX + scrollOffset) / (rect.width * zoom);

      // 滚轮缩放 - 使用更平滑的缩放因子
      const zoomDelta = -e.deltaY * 0.005; // 减少灵敏度，提升丝滑度
      const newZoom = Math.max(1, Math.min(10, zoom + zoomDelta));

      // 只有缩放值真正改变时才更新
      if (Math.abs(newZoom - zoom) < 0.01) return;

      const newScrollOffset = mousePositionRatio * rect.width * newZoom - mouseX;
      const maxScroll = rect.width * (newZoom - 1);
      const clampedOffset = Math.max(0, Math.min(maxScroll, newScrollOffset));

      // 标记正在缩放
      setIsZooming(true);

      // 批量更新状态
      setZoom(newZoom);
      setScrollOffset(clampedOffset);

      // 300ms后取消缩放状态，恢复过渡动画
      if (zoomTimeoutRef.current) {
        clearTimeout(zoomTimeoutRef.current);
      }
      zoomTimeoutRef.current = setTimeout(() => {
        setIsZooming(false);
      }, 300);
    };

    const timeline = timelineRef.current;

    if (timeline) {
      timeline.addEventListener('wheel', handleWheel, { passive: false });
    }

    return () => {
      if (timeline) {
        timeline.removeEventListener('wheel', handleWheel);
      }
      if (zoomTimeoutRef.current) {
        clearTimeout(zoomTimeoutRef.current);
      }
    };
  }, [zoom, scrollOffset]);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStartX(e.clientX);
    setDragStartOffset(scrollOffset);
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (Math.abs(e.clientX - dragStartX) > 5) return; // 防止拖拽时触发点击

    // 获取时间轴容器的位置
    const timelineRect = timelineRef.current?.getBoundingClientRect();
    if (!timelineRect) return;

    const clickPosition = e.clientX - timelineRect.left + scrollOffset;
    const timelineWidth = timelineRect.width * zoom;
    const time = (clickPosition / timelineWidth) * duration;
    onSeek(time);
  };

  const hasClonedAudio = subtitles.some(s => s.cloned_audio_path);

  return (
    <div className="w-full space-y-3">
      {/* 顶部工具栏 */}
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 bg-slate-400 rounded-full"></span>
            <span className="text-slate-300 font-semibold">原始字幕</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="w-2 h-2 bg-emerald-400 rounded-full"></span>
            <span className="text-emerald-300 font-semibold">
              克隆音频 {hasClonedAudio && `(${subtitles.filter(s => s.cloned_audio_path).length}/${subtitles.length})`}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {zoom > 1 ? `缩放: ${zoom.toFixed(1)}x | 拖拽移动 • 滚轮缩放` : '拖拽移动 • 滚轮缩放'}
          </span>
          {hasClonedAudio && onStitchAudio && (
            <button
              onClick={onStitchAudio}
              disabled={stitching}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                stitching
                  ? 'bg-emerald-600/30 text-emerald-400/50 cursor-not-allowed'
                  : 'bg-emerald-600/40 text-emerald-100 hover:bg-emerald-600/60 shadow-md hover:shadow-lg'
              }`}
            >
              {stitching ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  拼接中...
                </>
              ) : (
                <>
                  <Wand2 size={14} />
                  生成完整音频
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* 统一时间轴容器 */}
      <div
        ref={timelineRef}
        className="relative bg-gradient-to-b from-slate-700 to-slate-800 rounded-lg border-2 border-slate-600 hover:border-slate-500 transition-colors shadow-lg overflow-hidden"
        style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
        onMouseDown={handleMouseDown}
      >
        {/* 可缩放内容容器 */}
        <div
          className="relative will-change-transform"
          style={{
            width: `${100 * zoom}%`,
            transform: `translateX(-${scrollOffset}px)`,
            transition: (isDragging || isZooming) ? 'none' : 'transform 0.1s ease-out'
          }}
          onClick={handleTimelineClick}
        >
          {/* 背景网格 */}
          <div className="absolute inset-0 opacity-10 pointer-events-none">
            {[...Array(Math.ceil(10 * zoom))].map((_, i) => (
              <div
                key={i}
                className="absolute h-full border-l border-slate-500"
                style={{ left: `${((i + 1) * 10) / zoom}%` }}
              />
            ))}
          </div>

          {/* 原始字幕轨道 */}
          <div className="relative h-16 border-b border-slate-600/50">
            {subtitles.map((subtitle, index) => {
              const left = (subtitle.start_time / duration) * 100;
              const width = ((subtitle.end_time - subtitle.start_time) / duration) * 100;
              const isPlaying = currentTime >= subtitle.start_time && currentTime <= subtitle.end_time;
              const colors = getColorBySpacker(subtitle.speaker_id);

              return (
                <div
                  key={`orig-${index}`}
                  className={`absolute top-2 h-12 flex flex-col items-center justify-center rounded-md overflow-hidden border-2 transition-all duration-200 cursor-pointer group ${
                    isPlaying
                      ? `bg-gradient-to-br ${colors.bg} ${colors.border} shadow-lg scale-105`
                      : `bg-slate-600/40 border-slate-500 hover:border-slate-300 hover:shadow-md hover:bg-slate-600/60`
                  }`}
                  style={{
                    left: `${left}%`,
                    width: `${Math.max(width, 2.5 / zoom)}%`,
                    minWidth: '30px'
                  }}
                  onClick={() => {
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
                    {subtitle.text.length > 10 ? `${subtitle.text.substring(0, 10)}...` : subtitle.text}
                  </span>
                </div>
              );
            })}
          </div>

          {/* 克隆音频轨道 */}
          <div className="relative h-14">
            {subtitles.map((subtitle, index) => {
              if (!subtitle.cloned_audio_path) return null;

              // 使用重新规划的时间（如果有），否则使用原始时间
              const actualStart = subtitle.actual_start_time ?? subtitle.start_time;
              const actualEnd = subtitle.actual_end_time ?? subtitle.end_time;

              const left = (actualStart / duration) * 100;
              const width = ((actualEnd - actualStart) / duration) * 100;
              const isPlaying = currentTime >= actualStart && currentTime <= actualEnd;
              const displayText = subtitle.target_text;

              return (
                <div
                  key={`cloned-${index}`}
                  className={`absolute top-1 h-12 flex flex-col items-center justify-center rounded-md overflow-hidden border-2 transition-all duration-200 cursor-pointer group ${
                    isPlaying
                      ? 'bg-emerald-600 border-emerald-400 shadow-lg scale-105'
                      : 'bg-emerald-600/40 border-emerald-500 hover:border-emerald-300 hover:shadow-md hover:bg-emerald-600/60'
                  }`}
                  style={{
                    left: `${left}%`,
                    width: `${Math.max(width, 2.5 / zoom)}%`,
                    minWidth: '30px'
                  }}
                  onClick={() => {
                    onSeek(subtitle.start_time);
                  }}
                  title={displayText || subtitle.text}
                >
                  <span className={`text-xs px-1 truncate max-w-full text-center leading-tight ${isPlaying ? 'text-white' : 'text-slate-200'}`}>
                    {displayText && displayText.length > 10 ? `${displayText.substring(0, 10)}...` : displayText || '🎵'}
                  </span>
                </div>
              );
            })}
          </div>

          {/* 播放头指示器 - 贯穿所有轨道 */}
          <div
            className="absolute top-0 bottom-0 z-30 pointer-events-none"
            style={{
              left: `${(currentTime / duration) * 100}%`
            }}
          >
            {/* 发光效果背景 */}
            <div className="absolute top-0 bottom-0 w-1 -translate-x-1/2 bg-red-500/30 blur-sm"></div>

            {/* 主线条 */}
            <div className="absolute top-0 bottom-0 w-0.5 -translate-x-1/2 bg-gradient-to-b from-red-400 via-red-500 to-red-600 shadow-lg shadow-red-500/50"></div>

            {/* 顶部装饰和时间显示 */}
            <div className="absolute -top-10 left-1/2 -translate-x-1/2 flex flex-col items-center">
              {/* 时间标签 */}
              <div className="bg-gradient-to-br from-red-600 to-red-700 backdrop-blur-sm border border-red-400/50 rounded-md px-2.5 py-1 shadow-xl shadow-red-500/30 mb-1.5">
                <span className="text-xs font-mono text-white font-bold whitespace-nowrap drop-shadow-sm">
                  {new Date(currentTime * 1000).toISOString().substr(14, 5)}
                </span>
              </div>

              {/* 装饰性三角形箭头 */}
              <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[6px] border-t-red-600 mb-0.5"></div>

              {/* 顶部圆点 */}
              <div className="relative">
                <div className="w-4 h-4 bg-gradient-to-br from-red-400 to-red-600 rounded-full shadow-lg shadow-red-500/50 border-2 border-white"></div>
                <div className="absolute inset-0 w-4 h-4 bg-red-300 rounded-full animate-ping opacity-20"></div>
              </div>
            </div>
          </div>
        </div>

        {/* 时间刻度 */}
        <div
          className="relative h-6 bg-slate-800/50 border-t border-slate-600"
          style={{
            width: `${100 * zoom}%`,
            transform: `translateX(-${scrollOffset}px)`,
            transition: (isDragging || isZooming) ? 'none' : 'transform 0.1s ease-out'
          }}
        >
          {[...Array(Math.ceil(10 * zoom) + 1)].map((_, i) => {
            const timePercent = (i * 10) / zoom;
            const timeSeconds = (timePercent / 100) * duration;
            return (
              <div
                key={i}
                className="absolute top-0 h-full flex flex-col items-center"
                style={{ left: `${timePercent}%` }}
              >
                <div className="w-px h-2 bg-slate-500"></div>
                <span className="text-[10px] text-slate-400 font-mono mt-0.5">
                  {new Date(timeSeconds * 1000).toISOString().substr(14, 5)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 提示信息 */}
      <div className="text-xs text-slate-500 text-center font-medium">
        点击字幕卡片快速定位 • 总共 {subtitles.length} 条字幕
        {hasClonedAudio && ` • ${subtitles.filter(s => s.cloned_audio_path).length} 条已克隆`}
      </div>
    </div>
  );
};

export default SubtitleTimeline;
