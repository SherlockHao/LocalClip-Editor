import React from 'react';
import { Settings, Download, Users, Zap } from 'lucide-react';

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

interface ExportSettings {
  hardSubtitles: boolean;
  quality: string;
}

interface PropertiesPanelProps {
  exportSettings: ExportSettings;
  onExportSettingsChange: (settings: ExportSettings) => void;
  onExport: () => void;
  onRunSpeakerDiarization: () => void;
  isProcessingSpeakerDiarization: boolean;
  currentVideo: VideoFile | null;
}

const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  exportSettings,
  onExportSettingsChange,
  onExport,
  onRunSpeakerDiarization,
  isProcessingSpeakerDiarization,
  currentVideo
}) => {
  return (
    <div className="w-64 bg-white border-l border-gray-200 p-4">
      <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center">
        <Settings size={20} className="mr-2" />
        导出设置
      </h2>

      {currentVideo && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-700 mb-2">视频信息</h3>
          <div className="text-xs text-gray-600 space-y-1">
            <p>分辨率: {currentVideo.video_info.resolution}</p>
            <p>时长: {currentVideo.video_info.duration_formatted}</p>
            <p>编码: {currentVideo.video_info.codec}</p>
            <p>码率: {currentVideo.video_info.bitrate}</p>
          </div>
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-sm font-medium text-gray-700 mb-2">导出选项</h3>
        
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm text-gray-700">硬字幕</label>
            <div 
              className={`w-10 h-5 flex items-center rounded-full p-1 cursor-pointer ${
                exportSettings.hardSubtitles ? 'bg-blue-500' : 'bg-gray-300'
              }`}
              onClick={() => onExportSettingsChange({
                ...exportSettings,
                hardSubtitles: !exportSettings.hardSubtitles
              })}
            >
              <div 
                className={`bg-white w-3 h-3 rounded-full shadow-md transform transition-transform ${
                  exportSettings.hardSubtitles ? 'translate-x-5' : ''
                }`}
              />
            </div>
          </div>
          
          <div>
            <label className="text-sm text-gray-700 block mb-1">质量</label>
            <select
              value={exportSettings.quality}
              onChange={(e) => onExportSettingsChange({
                ...exportSettings,
                quality: e.target.value
              })}
              className="w-full p-2 border border-gray-300 rounded text-sm"
            >
              <option value="low">低质量</option>
              <option value="medium">中质量</option>
              <option value="high">高质量</option>
              <option value="original">原始质量</option>
            </select>
          </div>
        </div>
      </div>

      {/* 新增：说话人识别按钮 */}
      <div className="mb-4">
        <button
          onClick={onRunSpeakerDiarization}
          disabled={isProcessingSpeakerDiarization}
          className={`w-full flex items-center justify-center space-x-2 py-2.5 rounded-md transition-colors ${
            isProcessingSpeakerDiarization 
              ? 'bg-gray-400 cursor-not-allowed' 
              : 'bg-purple-600 hover:bg-purple-700 text-white'
          }`}
        >
          <Users size={18} />
          <span>
            {isProcessingSpeakerDiarization ? '处理中...' : '运行说话人识别'}
          </span>
        </button>
        {isProcessingSpeakerDiarization && (
          <div className="mt-2 text-xs text-center text-gray-600">
            正在分析音频并识别说话人...
          </div>
        )}
      </div>

      <button
        onClick={onExport}
        className="w-full flex items-center justify-center space-x-2 bg-green-600 text-white py-2.5 rounded-md hover:bg-green-700 transition-colors"
      >
        <Download size={18} />
        <span>导出视频</span>
      </button>
    </div>
  );
};

export default PropertiesPanel;