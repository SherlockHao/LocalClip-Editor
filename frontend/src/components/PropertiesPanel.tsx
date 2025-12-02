import React from 'react';
import { Settings, Download, Users, Zap, Info, Gauge } from 'lucide-react';

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
    <div className="w-72 bg-gradient-to-b from-slate-800 to-slate-900 border-l border-slate-700 flex flex-col shadow-2xl overflow-hidden">
      {/* 头部 */}
      <div className="p-5 border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-900/80">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg">
            <Settings size={18} className="text-white" />
          </div>
          设置和导出
        </h2>
      </div>

      {/* 可滚动内容区 */}
      <div className="flex-1 overflow-y-auto p-5">
        {/* 视频信息区域 */}
        {currentVideo && (
          <div className="mb-6 p-4 bg-slate-700/30 border border-slate-600 rounded-lg">
            <div className="flex items-center gap-2 mb-3">
              <Info size={16} className="text-blue-400" />
              <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">视频信息</h3>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">分辨率</span>
                <span className="text-xs font-semibold text-blue-300 bg-blue-500/10 px-2.5 py-1 rounded">
                  {currentVideo.video_info.resolution}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">时长</span>
                <span className="text-xs font-semibold text-slate-300">
                  {currentVideo.video_info.duration_formatted}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">编码</span>
                <span className="text-xs font-semibold text-slate-300">
                  {currentVideo.video_info.codec}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-slate-400">码率</span>
                <span className="text-xs font-semibold text-slate-300">
                  {currentVideo.video_info.bitrate}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* 导出选项区域 */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-4">
            <Gauge size={16} className="text-orange-400" />
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">导出选项</h3>
          </div>
          
          <div className="space-y-4">
            {/* 硬字幕开关 */}
            <div className="flex items-center justify-between p-3 bg-slate-700/30 border border-slate-600 rounded-lg hover:border-slate-500 transition-colors">
              <label className="text-sm font-medium text-slate-300 cursor-pointer">
                硬字幕合成
              </label>
              <button
                onClick={() => onExportSettingsChange({
                  ...exportSettings,
                  hardSubtitles: !exportSettings.hardSubtitles
                })}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  exportSettings.hardSubtitles 
                    ? 'bg-gradient-to-r from-blue-600 to-blue-500' 
                    : 'bg-slate-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    exportSettings.hardSubtitles ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {/* 质量选择 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                导出质量
              </label>
              <select
                value={exportSettings.quality}
                onChange={(e) => onExportSettingsChange({
                  ...exportSettings,
                  quality: e.target.value
                })}
                className="w-full px-3 py-2.5 bg-slate-700 border border-slate-600 text-slate-100 rounded-lg text-sm font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 transition-colors appearance-none cursor-pointer"
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23cbd5e1' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'right 8px center',
                  paddingRight: '28px'
                }}
              >
                <option value="low">低质量</option>
                <option value="medium">中质量</option>
                <option value="high">高质量</option>
                <option value="original">原始质量</option>
              </select>
            </div>
          </div>
        </div>

        {/* 说话人识别区域 */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Users size={16} className="text-purple-400" />
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">AI 功能</h3>
          </div>
          
          <button
            onClick={onRunSpeakerDiarization}
            disabled={isProcessingSpeakerDiarization}
            className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
              isProcessingSpeakerDiarization 
                ? 'bg-slate-600 text-slate-400 cursor-not-allowed opacity-75' 
                : 'bg-gradient-to-r from-purple-600 to-purple-500 text-white hover:shadow-lg hover:shadow-purple-500/50'
            }`}
          >
            {isProcessingSpeakerDiarization ? (
              <>
                <div className="spinner"></div>
                <span>识别中...</span>
              </>
            ) : (
              <>
                <Users size={18} />
                <span>运行说话人识别</span>
              </>
            )}
          </button>
          
          {isProcessingSpeakerDiarization && (
            <div className="mt-2.5 p-2.5 bg-purple-500/10 border border-purple-500/30 rounded-lg">
              <p className="text-xs text-purple-300 text-center font-medium">
                正在分析音频并识别说话人...
              </p>
            </div>
          )}
        </div>
      </div>

      {/* 底部导出按钮 */}
      <div className="p-5 border-t border-slate-700 bg-gradient-to-r from-slate-900 to-slate-800">
        <button
          onClick={onExport}
          className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-emerald-600 to-emerald-500 text-white py-3 px-4 rounded-lg hover:shadow-lg hover:shadow-emerald-500/50 transition-all duration-200 font-semibold"
        >
          <Download size={18} />
          <span>导出视频</span>
        </button>
      </div>
    </div>
  );
};

export default PropertiesPanel;