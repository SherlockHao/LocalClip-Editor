import React from 'react';
import { Upload, Video, FileText } from 'lucide-react';

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
      e.target.value = ''; // 重置输入，允许选择相同文件
    }
  };

  const handleSubtitleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      onSubtitleUpload(e.target.files[0]);
      e.target.value = ''; // 重置输入，允许选择相同文件
    }
  };

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800 mb-3">素材库</h2>
        
        <div className="space-y-2">
          <label className="flex items-center justify-center w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors cursor-pointer">
            <Upload size={16} className="mr-2" />
            <span>上传视频</span>
            <input
              type="file"
              accept="video/mp4,video/mov,video/avi,video/mkv"
              onChange={handleVideoFileSelect}
              className="hidden"
            />
          </label>
          
          <label className="flex items-center justify-center w-full px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors cursor-pointer">
            <FileText size={16} className="mr-2" />
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

      <div className="flex-1 overflow-y-auto p-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">视频文件</h3>
        {videos.length === 0 ? (
          <p className="text-sm text-gray-500">暂无视频文件</p>
        ) : (
          <div className="space-y-2">
            {videos.map((video, index) => (
              <div
                key={index}
                className="p-2 border border-gray-200 rounded cursor-pointer hover:bg-gray-50"
                onClick={() => onVideoSelect(video)}
              >
                <div className="flex items-start">
                  <Video size={16} className="text-blue-600 mr-2 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {video.original_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {video.video_info.resolution} • {video.video_info.duration_formatted}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Sidebar;