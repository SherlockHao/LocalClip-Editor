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
  isRegeneratingVoices?: boolean;
}

const SubtitleTimeline: React.FC<SubtitleTimelineProps> = ({
  subtitles,
  currentTime,
  duration,
  onSeek,
  onStitchAudio,
  stitching = false,
  isRegeneratingVoices = false
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
    console.log('[Timeline Click] 开始处理点击事件');
    console.log('[Timeline Click] e.clientX:', e.clientX, 'dragStartX:', dragStartX, 'diff:', Math.abs(e.clientX - dragStartX));

    if (Math.abs(e.clientX - dragStartX) > 5) {
      console.log('[Timeline Click] 被拖拽检测阻止，退出');
      return; // 防止拖拽时触发点击
    }

    // 获取时间轴容器的位置
    const timelineRect = timelineRef.current?.getBoundingClientRect();
    if (!timelineRect) {
      console.log('[Timeline Click] timelineRect 为空，退出');
      return;
    }

    const clickPosition = e.clientX - timelineRect.left + scrollOffset;
    const timelineWidth = timelineRect.width * zoom;
    const time = (clickPosition / timelineWidth) * duration;

    console.log('[Timeline Click] clickPosition:', clickPosition);
    console.log('[Timeline Click] timelineWidth:', timelineWidth);
    console.log('[Timeline Click] duration:', duration);
    console.log('[Timeline Click] 计算的 time:', time);
    console.log('[Timeline Click] 调用 onSeek(', time, ')');

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
          {/* 生成完整音频按钮已移至右侧操作栏 */}
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

          {/* 播放头指示器 - 现代化设计 */}
          <div
            className="absolute top-0 bottom-0 z-30 pointer-events-none"
            style={{
              left: `${(currentTime / duration) * 100}%`
            }}
          >
            {/* 多层发光效果 */}
            <div className="absolute top-0 bottom-0 w-3 -translate-x-1/2 bg-cyan-400/20 blur-xl"></div>
            <div className="absolute top-0 bottom-0 w-2 -translate-x-1/2 bg-cyan-400/30 blur-md"></div>

            {/* 主线条 - 渐变色带 */}
            <div className="absolute top-0 bottom-0 w-1 -translate-x-1/2 bg-gradient-to-b from-cyan-300 via-cyan-400 to-blue-500 shadow-2xl shadow-cyan-400/60"></div>

            {/* 内部高光线 */}
            <div className="absolute top-0 bottom-0 w-px -translate-x-1/2 left-[-1px] bg-gradient-to-b from-white/80 via-white/40 to-transparent"></div>

            {/* 顶部装饰和时间显示 */}
            <div className="absolute -top-12 left-1/2 -translate-x-1/2 flex flex-col items-center">
              {/* 时间标签 - 玻璃态设计 */}
              <div className="relative group">
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500 to-blue-500 rounded-lg blur-md opacity-60 group-hover:opacity-80 transition-opacity"></div>
                <div className="relative bg-gradient-to-br from-slate-800/95 to-slate-900/95 backdrop-blur-xl border border-cyan-400/40 rounded-lg px-3 py-1.5 shadow-2xl">
                  <span className="text-xs font-mono text-cyan-100 font-bold whitespace-nowrap tracking-wide">
                    {new Date(currentTime * 1000).toISOString().substr(14, 5)}
                  </span>
                  {/* 内部光晕 */}
                  <div className="absolute inset-0 bg-gradient-to-t from-cyan-400/10 to-transparent rounded-lg"></div>
                </div>
              </div>

              {/* 连接线装饰 */}
              <div className="w-px h-3 bg-gradient-to-b from-cyan-400 to-transparent my-0.5"></div>

              {/* 顶部指示器 - 菱形设计 */}
              <div className="relative">
                {/* 外圈脉动光环 */}
                <div className="absolute inset-0 w-5 h-5 -translate-x-1/2 left-1/2 -translate-y-1/2 top-1/2">
                  <div className="absolute inset-0 bg-cyan-400/40 rounded-full animate-ping"></div>
                  <div className="absolute inset-0 bg-cyan-400/30 rounded-full animate-pulse"></div>
                </div>

                {/* 菱形主体 */}
                <div className="relative w-4 h-4 rotate-45 bg-gradient-to-br from-cyan-300 via-cyan-400 to-blue-500 rounded-sm shadow-lg shadow-cyan-400/50 border border-white/30">
                  {/* 内部光泽 */}
                  <div className="absolute inset-0 bg-gradient-to-br from-white/50 via-transparent to-transparent rounded-sm"></div>
                  {/* 中心高光点 */}
                  <div className="absolute top-1 left-1 w-1 h-1 bg-white/90 rounded-full"></div>
                </div>
              </div>
            </div>

            {/* 底部投影效果 */}
            <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-8 h-1 bg-gradient-to-r from-transparent via-cyan-400/30 to-transparent blur-sm"></div>
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
