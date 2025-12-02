import React from 'react';

interface Subtitle {
  start_time: number;
  end_time: number;
  start_time_formatted: string;
  end_time_formatted: string;
  text: string;
  speaker_id?: number;  // 新增说话人ID
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
  const timelineWidth = 1000; // 固定像素宽度，可以根据容器大小调整

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickPosition = e.clientX - rect.left;
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
      // 提供一个默认的编辑功能，实际应用中可能需要弹出编辑对话框
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
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>00:00</span>
        <span>{new Date(duration * 1000).toISOString().substr(11, 8)}</span>
      </div>
      <div 
        className="relative h-20 bg-gray-100 rounded cursor-pointer border border-gray-300"
        onClick={handleTimelineClick}
      >
        {/* 时间轴 */}
        <div className="absolute top-0 left-0 w-full h-full flex">
          {/* 字幕块 */}
          {subtitles.map((subtitle, index) => {
            const left = (subtitle.start_time / duration) * 100;
            const width = ((subtitle.end_time - subtitle.start_time) / duration) * 100;
            
            return (
              <div
                key={index}
                className={`absolute top-3 h-12 flex flex-col items-center justify-center border border-gray-400 rounded ${
                  currentTime >= subtitle.start_time && currentTime <= subtitle.end_time
                    ? 'bg-blue-500 text-white'
                    : subtitle.speaker_id !== undefined ? 
                      `bg-slate-${100 + subtitle.speaker_id * 100} text-gray-800` : // 根据说话人ID设置不同颜色
                      'bg-blue-200 text-gray-800'
                }`}
                style={{
                  left: `${left}%`,
                  width: `${width}%`,
                  minWidth: '60px'
                }}
              >
                {subtitle.speaker_id !== undefined && (
                  <span className="text-xs font-bold">说话人 {subtitle.speaker_id}</span>
                )}
                <span className="text-xs px-1 truncate">{subtitle.text}</span>
              </div>
            );
          })}
        </div>

        {/* 播放头 */}
        <div
          className="absolute top-0 h-full w-0.5 bg-red-500 z-10"
          style={{
            left: `${(currentTime / duration) * 100}%`
          }}
        >
          <div className="absolute -top-1 -ml-1.5 w-3 h-3 bg-red-500 rounded-full"></div>
        </div>
      </div>

      {/* 字幕编辑区域 */}
      <div className="mt-4 space-y-2 max-h-40 overflow-y-auto">
        {subtitles.map((subtitle, index) => (
          <div 
            key={index}
            className={`p-2 rounded border ${
              currentTime >= subtitle.start_time && currentTime <= subtitle.end_time
                ? 'bg-blue-100 border-blue-300'
                : 'bg-white border-gray-200'
            }`}
          >
            <div className="flex justify-between">
              <span className="text-xs font-mono text-gray-500">
                {subtitle.start_time_formatted} → {subtitle.end_time_formatted}
                {subtitle.speaker_id !== undefined && (
                  <span className="ml-2 bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded text-xs">
                    说话人 {subtitle.speaker_id}
                  </span>
                )}
              </span>
              <div className="flex space-x-2">
                <button 
                  className="text-xs bg-blue-500 hover:bg-blue-600 text-white px-2 py-1 rounded"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEditSubtitle(index);
                  }}
                >
                  编辑
                </button>
                <button 
                  className="text-xs bg-red-500 hover:bg-red-600 text-white px-2 py-1 rounded"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDeleteSubtitle(index);
                  }}
                >
                  删除
                </button>
              </div>
            </div>
            <p className="mt-1">{subtitle.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SubtitleTimeline;