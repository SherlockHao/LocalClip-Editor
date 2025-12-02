import React from 'react';
import { Upload, Video, FileText, Play, Clock } from 'lucide-react';

interface VideoFile {
  filename: string;
  original_name: string;
  size: number;
  video_info: {
    width: number;
    height: number;
    resolution: string;
    duration: number;
    duration_formatted: string;
    bitrate: string;
    codec: string;
  };
}

interface SidebarProps {
  videos: VideoFile[];
  onVideoSelect: (video: VideoFile) => void;
  onVideoUpload: (file: File) => void;
  onSubtitleUpload: (file: File) => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  videos,
  onVideoSelect,
  onVideoUpload,
  onSubtitleUpload
}) => {
  const handleVideoFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onVideoUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  const handleSubtitleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onSubtitleUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  return (
    <div className="w-72 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 flex flex-col shadow-2xl">
      {/* 上传区域 */}
      <div className="p-5 border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-900/80 backdrop-blur-sm">
        <h2 className="text-lg font-bold text-slate-100 mb-4 flex items-center">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg mr-2">
            <Video size={18} className="text-white" />
          </div>
          素材库
        </h2>
        
        <div className="space-y-2.5">
          {/* 上传视频按钮 */}
          <label className="flex items-center justify-center w-full px-4 py-3 bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-lg hover:shadow-lg hover:shadow-blue-500/50 transition-all duration-200 cursor-pointer font-medium group">
            <Upload size={18} className="mr-2 group-hover:animate-bounce" />
            <span>上传视频</span>
            <input
              type="file"
              accept="video/mp4,video/mov,video/avi,video/mkv"
              onChange={handleVideoFileSelect}
              className="hidden"
            />
          </label>
          
          {/* 上传字幕按钮 */}
          <label className="flex items-center justify-center w-full px-4 py-3 bg-gradient-to-r from-slate-700 to-slate-600 text-slate-100 rounded-lg hover:bg-slate-600 hover:shadow-lg hover:shadow-slate-600/50 transition-all duration-200 cursor-pointer font-medium group">
            <FileText size={18} className="mr-2 group-hover:animate-bounce" />
            <span>上传字幕</span>
            <input
              type="file"
              accept=".srt"
              onChange={handleSubtitleFileSelect}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* 视频列表区域 */}
      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-bold text-slate-300 mb-3 uppercase tracking-wider">
          视频文件 ({videos.length})
        </h3>
        
        {videos.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-40 text-center">
            <div className="p-4 bg-slate-700/30 rounded-lg mb-3">
              <Video size={32} className="text-slate-500 mx-auto" />
            </div>
            <p className="text-sm text-slate-400 font-medium">暂无视频文件</p>
            <p className="text-xs text-slate-500 mt-1">点击上方按钮上传视频</p>
          </div>
        ) : (
          <div className="space-y-2.5">
            {videos.map((video, index) => (
              <div
                key={index}
                onClick={() => onVideoSelect(video)}
                className="group p-3 border border-slate-600 rounded-lg cursor-pointer transition-all duration-200 hover:border-blue-500 hover:bg-slate-700/50 hover:shadow-lg hover:shadow-blue-500/10"
              >
                <div className="flex items-start gap-2.5">
                  <div className="p-2 bg-gradient-to-br from-blue-500/20 to-blue-600/20 rounded-md flex-shrink-0 group-hover:from-blue-500/40 group-hover:to-blue-600/40 transition-colors">
                    <Play size={16} className="text-blue-400" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-100 truncate group-hover:text-blue-300 transition-colors">
                      {video.original_name}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="inline-flex items-center gap-1 text-xs text-slate-400 bg-slate-700/50 px-2 py-1 rounded">
                        <Clock size={12} />
                        {video.video_info.duration_formatted}
                      </span>
                      <span className="text-xs text-slate-500 bg-slate-700/30 px-2 py-1 rounded">
                        {video.video_info.resolution}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 底部说明 */}
      <div className="p-4 border-t border-slate-700 bg-slate-900/50 text-xs text-slate-500">
        <p className="text-center">提示：支持 MP4、MOV、AVI、MKV 格式</p>
      </div>
    </div>
  );
};

export default Sidebar;