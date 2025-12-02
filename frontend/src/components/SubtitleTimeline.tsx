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
  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickPosition = e.clientX - rect.left;
    const timelineWidth = rect.width; // 使用实际宽度而不是固定值
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
        className="relative h-20 bg-gray-200 rounded cursor-pointer border border-gray-300"
        onClick={handleTimelineClick}
        style={{ width: '100%', maxWidth: '100%' }}
      >
        {/* 时间轴 */}
        <div className="absolute top-0 left-0 w-full h-full">
          {/* 字幕块 */}
          {subtitles.map((subtitle, index) => {
            const left = (subtitle.start_time / duration) * 100;
            const width = ((subtitle.end_time - subtitle.start_time) / duration) * 100;
            
            return (
              <div
                key={index}
                className={`absolute top-3 h-12 flex flex-col items-center justify-center border border-gray-600 rounded-md overflow-hidden ${
                  currentTime >= subtitle.start_time && currentTime <= subtitle.end_time
                    ? 'bg-blue-600 text-white'  // 使用更深的蓝色
                    : subtitle.speaker_id !== undefined ? 
                      // 根据说话人ID设置不同颜色，使用更不透明的颜色
                      subtitle.speaker_id % 6 === 0 ? 'bg-blue-400 text-gray-900' :
                      subtitle.speaker_id % 6 === 1 ? 'bg-green-400 text-gray-900' :
                      subtitle.speaker_id % 6 === 2 ? 'bg-yellow-400 text-gray-900' :
                      subtitle.speaker_id % 6 === 3 ? 'bg-purple-400 text-gray-900' :
                      subtitle.speaker_id % 6 === 4 ? 'bg-pink-400 text-gray-900' :
                      'bg-indigo-400 text-gray-900' :  // speaker_id % 6 === 5
                      'bg-blue-400 text-gray-900'  // 使用更深更不透明的蓝色
                }`}
                style={{
                  left: `${left}%`,
                  width: `${width}%`,
                  minWidth: '60px'
                }}
              >
                {subtitle.speaker_id !== undefined && (
                  <span className="text-xs font-bold truncate max-w-[80px]">说话人 {subtitle.speaker_id}</span>
                )}
                <span className="text-xs px-1 truncate max-w-full">
                  {subtitle.text.length > 25 ? `${subtitle.text.substring(0, 25)}...` : subtitle.text}
                </span>
              </div>
            );
          })}
        </div>

        {/* 播放头 */}
        <div
          className="absolute top-0 h-full w-0.5 bg-red-600 z-10"
          style={{
            left: `${(currentTime / duration) * 100}%`
          }}
        >
          <div className="absolute -top-1 -ml-1.5 w-3 h-3 bg-red-600 rounded-full"></div>
        </div>
      </div>

      {/* 字幕编辑区域 */}
      <div className="mt-4 space-y-2 max-h-40 overflow-y-auto">
        {subtitles.map((subtitle, index) => (
          <div 
            key={index}
            className={`p-2 rounded border ${
              currentTime >= subtitle.start_time && currentTime <= subtitle.end_time
                ? 'bg-blue-100 border-blue-500'  // 使用更深的边框颜色
                : subtitle.speaker_id !== undefined ?
                  // 根据说话人ID设置背景色
                  subtitle.speaker_id % 6 === 0 ? 'bg-blue-50 border-blue-200' :
                  subtitle.speaker_id % 6 === 1 ? 'bg-green-50 border-green-200' :
                  subtitle.speaker_id % 6 === 2 ? 'bg-yellow-50 border-yellow-200' :
                  subtitle.speaker_id % 6 === 3 ? 'bg-purple-50 border-purple-200' :
                  subtitle.speaker_id % 6 === 4 ? 'bg-pink-50 border-pink-200' :
                  'bg-indigo-50 border-indigo-200' :  // speaker_id % 6 === 5
                  'bg-gray-50 border-gray-200'
            }`}
          >
            <div className="flex justify-between">
              <span className="text-xs font-mono text-gray-600">
                {subtitle.start_time_formatted} → {subtitle.end_time_formatted}
                {subtitle.speaker_id !== undefined && (
                  <span className={`ml-2 px-1.5 py-0.5 rounded text-xs ${
                    subtitle.speaker_id % 6 === 0 ? 'bg-blue-200 text-blue-800' :
                    subtitle.speaker_id % 6 === 1 ? 'bg-green-200 text-green-800' :
                    subtitle.speaker_id % 6 === 2 ? 'bg-yellow-200 text-yellow-800' :
                    subtitle.speaker_id % 6 === 3 ? 'bg-purple-200 text-purple-800' :
                    subtitle.speaker_id % 6 === 4 ? 'bg-pink-200 text-pink-800' :
                    'bg-indigo-200 text-indigo-800'
                  }`}>
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