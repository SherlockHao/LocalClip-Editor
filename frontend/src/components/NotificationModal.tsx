import React from 'react';
import { CheckCircle, X, Users } from 'lucide-react';

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
  uniqueSpeakers?: number;
}

const NotificationModal: React.FC<NotificationModalProps> = ({
  isOpen,
  onClose,
  title,
  message,
  uniqueSpeakers
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-2xl border-2 border-green-500/50 max-w-md w-full mx-4 overflow-hidden animate-in fade-in zoom-in duration-300">
        {/* 头部 */}
        <div className="bg-gradient-to-r from-green-600/30 to-emerald-600/30 p-6 border-b border-green-500/30 relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X size={20} />
          </button>

          <div className="flex items-center space-x-3">
            <div className="p-3 bg-green-500/20 rounded-full">
              <CheckCircle size={32} className="text-green-400" />
            </div>
            <h3 className="text-xl font-bold text-slate-100">{title}</h3>
          </div>
        </div>

        {/* 内容 */}
        <div className="p-6 space-y-4">
          <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-line">
            {message}
          </p>

          {uniqueSpeakers !== undefined && (
            <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-lg p-4 border border-blue-500/30">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-blue-500/30 rounded-lg">
                  <Users size={24} className="text-blue-300" />
                </div>
                <div>
                  <div className="text-xs text-slate-400 font-medium">识别出的说话人数量</div>
                  <div className="text-2xl font-bold text-blue-300">{uniqueSpeakers} 个</div>
                </div>
              </div>
            </div>
          )}

          {/* 按钮 */}
          <button
            onClick={onClose}
            className="w-full bg-gradient-to-r from-green-600 to-emerald-600 text-white py-3 rounded-lg font-semibold hover:from-green-500 hover:to-emerald-500 transition-all duration-200 shadow-lg hover:shadow-green-500/50"
          >
            确定
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationModal;
