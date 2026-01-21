import React from 'react';
import { Settings, Download, Users, Zap, Info, FileText, Mic, Music, FolderOpen } from 'lucide-react';

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
  speakerDiarizationProgress: { message: string; progress: number };
  currentVideo: VideoFile | null;
  targetLanguage: string;
  onTargetLanguageChange: (language: string) => void;
  targetSrtFilename: string | null;
  onTranslateSubtitles: () => void;
  isTranslating: boolean;
  translationProgress: { message: string; progress: number } | null;
  onRunVoiceCloning: () => void;
  isProcessingVoiceCloning: boolean;
  voiceCloningProgress: { message: string; progress: number } | null;
  speakerDiarizationCompleted: boolean;
  voiceCloningCompleted?: boolean;
  stitchedAudioReady?: boolean;
  onStitchAudio?: () => void;
  isStitchingAudio?: boolean;
  // 新增：导出视频相关
  onExportVideo?: () => void;
  isExportingVideo?: boolean;
  exportVideoCompleted?: boolean;
  exportVideoProgress?: { message: string; progress: number } | null;
  exportedVideoDir?: string | null;
  onOpenExportFolder?: () => void;
}

const PropertiesPanel: React.FC<PropertiesPanelProps> = ({
  exportSettings,
  onExportSettingsChange,
  onExport,
  onRunSpeakerDiarization,
  isProcessingSpeakerDiarization,
  speakerDiarizationProgress,
  currentVideo,
  targetLanguage,
  onTargetLanguageChange,
  targetSrtFilename,
  onTranslateSubtitles,
  isTranslating,
  translationProgress,
  onRunVoiceCloning,
  isProcessingVoiceCloning,
  voiceCloningProgress,
  speakerDiarizationCompleted,
  voiceCloningCompleted = false,
  stitchedAudioReady = false,
  onStitchAudio,
  isStitchingAudio = false,
  // 新增：导出视频相关
  onExportVideo,
  isExportingVideo = false,
  exportVideoCompleted = false,
  exportVideoProgress = null,
  exportedVideoDir = null,
  onOpenExportFolder
}) => {

  // 判断语音克隆按钮是否可用
  const isVoiceCloningEnabled = speakerDiarizationCompleted &&
                                 targetLanguage !== '' &&
                                 targetSrtFilename !== null;

  // 判断导出视频按钮是否可用（拼接音频完成后才能导出）
  const isExportVideoEnabled = stitchedAudioReady && targetLanguage !== '';

  return (
    <div className="w-72 bg-gradient-to-b from-slate-800 to-slate-900 border-l border-slate-700 flex flex-col shadow-2xl overflow-hidden">
      {/* 头部 */}
      <div className="p-5 border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-900/80">
        <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg">
            <Settings size={18} className="text-white" />
          </div>
          操作栏
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
                : speakerDiarizationCompleted
                ? 'bg-gradient-to-r from-green-600 to-green-500 text-white hover:shadow-lg hover:shadow-green-500/50'
                : 'bg-gradient-to-r from-purple-600 to-purple-500 text-white hover:shadow-lg hover:shadow-purple-500/50'
            }`}
          >
            {isProcessingSpeakerDiarization ? (
              <>
                <div className="spinner"></div>
                <span>识别中...</span>
              </>
            ) : speakerDiarizationCompleted ? (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>说话人识别已完成</span>
              </>
            ) : (
              <>
                <Users size={18} />
                <span>运行说话人识别</span>
              </>
            )}
          </button>

          {isProcessingSpeakerDiarization && (
            <div className="mt-2.5 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
              <p className="text-xs text-purple-300 font-medium mb-2 transition-opacity duration-300">
                {speakerDiarizationProgress.message || '正在处理...'}
              </p>
              <div className="w-full bg-slate-700/50 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-purple-500 to-blue-500 h-full transition-all duration-1000 ease-out"
                  style={{ width: `${speakerDiarizationProgress.progress}%` }}
                />
              </div>
              <p className="text-xs text-purple-400 text-right mt-1 font-mono transition-all duration-500">
                {speakerDiarizationProgress.progress}%
              </p>
            </div>
          )}

          {speakerDiarizationCompleted && !isProcessingSpeakerDiarization && (
            <p className="text-xs text-green-400 mt-1.5 flex items-center gap-1">
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              点击可重新运行说话人识别
            </p>
          )}
        </div>

        {/* 语音克隆区域 */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Mic size={16} className="text-blue-400" />
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">语音克隆</h3>
          </div>

          <div className="space-y-3">
            {/* 克隆语言选择 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                克隆语言
              </label>
              <select
                value={targetLanguage}
                onChange={(e) => onTargetLanguageChange(e.target.value)}
                disabled={!speakerDiarizationCompleted}
                className={`w-full px-3 py-2.5 border rounded-lg text-sm font-medium transition-colors appearance-none ${
                  speakerDiarizationCompleted
                    ? 'bg-slate-700 border-slate-600 text-slate-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/50 cursor-pointer'
                    : 'bg-slate-800 border-slate-700 text-slate-500 cursor-not-allowed opacity-60'
                }`}
                style={{
                  backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23cbd5e1' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
                  backgroundRepeat: 'no-repeat',
                  backgroundPosition: 'right 8px center',
                  paddingRight: '28px'
                }}
              >
                <option value="">请选择目标语言</option>
                <option value="en">英语</option>
                <option value="ko">韩语</option>
                <option value="ja">日语</option>
                <option value="fr">法语</option>
                <option value="de">德语</option>
                <option value="es">西班牙语</option>
                <option value="id">印尼语</option>
              </select>
              {!speakerDiarizationCompleted && (
                <p className="text-xs text-slate-500 mt-1.5">
                  请先完成说话人识别
                </p>
              )}
            </div>

            {/* 翻译字幕按钮 */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                目标语言字幕
              </label>
              <button
                onClick={onTranslateSubtitles}
                disabled={!speakerDiarizationCompleted || !targetLanguage || isTranslating}
                className={`flex items-center justify-center w-full px-4 py-2.5 rounded-lg font-medium transition-all duration-200 ${
                  speakerDiarizationCompleted && targetLanguage && !isTranslating
                    ? 'bg-gradient-to-r from-purple-600 to-purple-500 text-white hover:shadow-lg hover:shadow-purple-500/50'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed opacity-60'
                }`}
              >
                {isTranslating ? (
                  <>
                    <div className="spinner mr-2"></div>
                    <span>翻译中...</span>
                  </>
                ) : targetSrtFilename ? (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    <span>翻译完成</span>
                  </>
                ) : (
                  <>
                    <FileText size={16} className="mr-2" />
                    <span>翻译字幕</span>
                  </>
                )}
              </button>
              {targetSrtFilename && !isTranslating && (
                <p className="text-xs text-green-400 mt-1.5 flex items-center gap-1">
                  <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  已翻译为{targetLanguage === 'en' ? '英语' : targetLanguage === 'ko' ? '韩语' : targetLanguage === 'ja' ? '日语' : '法语'}
                </p>
              )}
              {isTranslating && translationProgress && (
                <div className="mt-2">
                  <div className="flex justify-between text-xs text-slate-400 mb-1">
                    <span>{translationProgress.message}</span>
                    <span>{translationProgress.progress}%</span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-1.5">
                    <div
                      className="bg-gradient-to-r from-purple-600 to-purple-400 h-1.5 rounded-full transition-all duration-300"
                      style={{ width: `${translationProgress.progress}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>

            {/* 语音克隆按钮 */}
            <button
              onClick={onRunVoiceCloning}
              disabled={!isVoiceCloningEnabled || isProcessingVoiceCloning}
              className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
                isProcessingVoiceCloning
                  ? 'bg-slate-600 text-slate-400 cursor-not-allowed opacity-75'
                  : voiceCloningCompleted
                  ? 'bg-gradient-to-r from-green-600 to-green-500 text-white hover:shadow-lg hover:shadow-green-500/50'
                  : isVoiceCloningEnabled
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white hover:shadow-lg hover:shadow-blue-500/50'
                  : 'bg-slate-600 text-slate-400 cursor-not-allowed opacity-75'
              }`}
            >
              {isProcessingVoiceCloning ? (
                <>
                  <div className="spinner"></div>
                  <span>克隆中...</span>
                </>
              ) : voiceCloningCompleted ? (
                <>
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>语音克隆已完成</span>
                </>
              ) : (
                <>
                  <Mic size={18} />
                  <span>语音克隆</span>
                </>
              )}
            </button>

            {voiceCloningProgress && (
              <div className="mt-2.5 p-2.5 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <p className="text-xs text-blue-300 text-center font-medium mb-2">
                  {voiceCloningProgress.message}
                </p>
                <div className="w-full bg-slate-700 rounded-full h-1.5">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-400 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${voiceCloningProgress.progress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-blue-300 text-center mt-1">
                  {voiceCloningProgress.progress}%
                </p>
              </div>
            )}

            {voiceCloningCompleted && !isProcessingVoiceCloning && !voiceCloningProgress && (
              <p className="text-xs text-green-400 mt-1.5 flex items-center gap-1">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                {stitchedAudioReady ? '语音克隆和音频拼接已完成' : '点击可重新运行语音克隆'}
              </p>
            )}

            {!isVoiceCloningEnabled && !isProcessingVoiceCloning && !voiceCloningCompleted && (
              <div className="p-2.5 bg-slate-700/30 border border-slate-600 rounded-lg">
                <p className="text-xs text-slate-400 text-center">
                  完成以下步骤后可启用：
                </p>
                <ul className="text-xs text-slate-400 mt-1.5 space-y-1">
                  <li className={speakerDiarizationCompleted ? 'text-green-400' : ''}>
                    {speakerDiarizationCompleted ? '✓' : '○'} 完成说话人识别
                  </li>
                  <li className={targetLanguage ? 'text-green-400' : ''}>
                    {targetLanguage ? '✓' : '○'} 选择克隆语言
                  </li>
                  <li className={targetSrtFilename ? 'text-green-400' : ''}>
                    {targetSrtFilename ? '✓' : '○'} 翻译任务
                  </li>
                </ul>
              </div>
            )}

            {/* 拼接音频按钮 - 语音克隆完成后显示 */}
            {voiceCloningCompleted && onStitchAudio && (
              <div className="mt-3 pt-3 border-t border-slate-600">
                <button
                  onClick={onStitchAudio}
                  disabled={isStitchingAudio}
                  className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
                    isStitchingAudio
                      ? 'bg-slate-600 text-slate-400 cursor-not-allowed opacity-75'
                      : stitchedAudioReady
                      ? 'bg-gradient-to-r from-green-600 to-green-500 text-white hover:shadow-lg hover:shadow-green-500/50'
                      : 'bg-gradient-to-r from-amber-600 to-amber-500 text-white hover:shadow-lg hover:shadow-amber-500/50'
                  }`}
                >
                  {isStitchingAudio ? (
                    <>
                      <div className="spinner"></div>
                      <span>拼接中...</span>
                    </>
                  ) : stitchedAudioReady ? (
                    <>
                      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span>音频拼接已完成</span>
                    </>
                  ) : (
                    <>
                      <Music size={18} />
                      <span>拼接音频</span>
                    </>
                  )}
                </button>
                {stitchedAudioReady && !isStitchingAudio && (
                  <p className="text-xs text-green-400 mt-1.5 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    可点击播放预览拼接后的音频
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 底部导出按钮 */}
      <div className="p-5 border-t border-slate-700 bg-gradient-to-r from-slate-900 to-slate-800">
        {/* 导出视频按钮 */}
        <div className="flex gap-2">
          <button
            onClick={onExportVideo}
            disabled={!isExportVideoEnabled || isExportingVideo}
            className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-semibold transition-all duration-200 ${
              isExportingVideo
                ? 'bg-slate-600 text-slate-400 cursor-not-allowed opacity-75'
                : exportVideoCompleted
                ? 'bg-gradient-to-r from-green-600 to-green-500 text-white hover:shadow-lg hover:shadow-green-500/50'
                : isExportVideoEnabled
                ? 'bg-gradient-to-r from-emerald-600 to-emerald-500 text-white hover:shadow-lg hover:shadow-emerald-500/50'
                : 'bg-slate-600 text-slate-400 cursor-not-allowed opacity-75'
            }`}
          >
            {isExportingVideo ? (
              <>
                <div className="spinner"></div>
                <span>导出中...</span>
              </>
            ) : exportVideoCompleted ? (
              <>
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>导出成功</span>
              </>
            ) : (
              <>
                <Download size={18} />
                <span>导出视频</span>
              </>
            )}
          </button>

          {/* 打开文件夹按钮 - 导出完成后显示 */}
          {exportVideoCompleted && onOpenExportFolder && (
            <button
              onClick={onOpenExportFolder}
              className="flex items-center justify-center p-3 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 transition-all duration-200"
              title="打开输出文件夹"
            >
              <FolderOpen size={18} />
            </button>
          )}
        </div>

        {/* 导出进度 */}
        {isExportingVideo && exportVideoProgress && (
          <div className="mt-3 p-2.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <p className="text-xs text-emerald-300 text-center font-medium mb-2">
              {exportVideoProgress.message}
            </p>
            <div className="w-full bg-slate-700 rounded-full h-1.5">
              <div
                className="bg-gradient-to-r from-emerald-500 to-emerald-400 h-1.5 rounded-full transition-all duration-300"
                style={{ width: `${exportVideoProgress.progress}%` }}
              ></div>
            </div>
            <p className="text-xs text-emerald-300 text-center mt-1">
              {exportVideoProgress.progress}%
            </p>
          </div>
        )}

        {/* 未启用时的提示 */}
        {!isExportVideoEnabled && !isExportingVideo && !exportVideoCompleted && (
          <p className="text-xs text-slate-500 mt-2 text-center">
            完成音频拼接后可导出视频
          </p>
        )}
      </div>
    </div>
  );
};

export default PropertiesPanel;
