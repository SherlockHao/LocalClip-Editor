import React from 'react';
import { Video } from 'lucide-react';
import LanguageProgressSidebar from './LanguageProgressSidebar';

interface SidebarProps {
  speakerDiarizationCompleted: boolean;
  selectedLanguage: string;
  onLanguageSelect: (languageCode: string) => void;
  isSpeakerEditingMode?: boolean;
  onSpeakerEditingSelect?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  speakerDiarizationCompleted,
  selectedLanguage,
  onLanguageSelect,
  isSpeakerEditingMode = false,
  onSpeakerEditingSelect,
}) => {
  return (
    <div className="w-72 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 flex flex-col shadow-2xl">
      {/* 标题区域 */}
      <div className="p-5 border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-900/80 backdrop-blur-sm">
        <h2 className="text-lg font-bold text-slate-100 flex items-center">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg mr-2">
            <Video size={18} className="text-white" />
          </div>
          处理进度
        </h2>
      </div>

      {/* 语言进度显示区域 */}
      <LanguageProgressSidebar
        speakerDiarizationCompleted={speakerDiarizationCompleted}
        selectedLanguage={selectedLanguage}
        onLanguageSelect={onLanguageSelect}
        isSpeakerEditingMode={isSpeakerEditingMode}
        onSpeakerEditingSelect={onSpeakerEditingSelect}
      />

      {/* 底部说明 */}
      <div className="p-4 border-t border-slate-700 bg-slate-900/50 text-xs text-slate-500">
        <p className="text-center">点击说话人识别或语言卡片切换视图</p>
      </div>
    </div>
  );
};

export default Sidebar;
