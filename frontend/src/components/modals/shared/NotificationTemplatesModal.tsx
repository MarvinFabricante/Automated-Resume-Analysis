import React from 'react';
import { X, MessageSquare } from 'lucide-react';
import NotificationTemplatesEditor from '../../notifications/NotificationTemplatesEditor';

interface NotificationTemplatesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const NotificationTemplatesModal: React.FC<NotificationTemplatesModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-gray-900/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-5xl max-h-[92vh] rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col">
        <div className="px-5 sm:px-8 py-4 border-b border-gray-100 flex items-center justify-between bg-white sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-rose-50 text-[#D60041] flex items-center justify-center">
              <MessageSquare size={18} />
            </div>
            <div>
              <h2 className="text-base font-black text-gray-900 tracking-tight">
                Email & SMS Message Templates
              </h2>
              <p className="text-[11px] text-gray-500 font-medium">
                Customize default candidate Email & SMS templates with dynamic schedule details
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400 hover:text-gray-700"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-5 sm:p-8 overflow-y-auto flex-1">
          <NotificationTemplatesEditor compact />
        </div>
      </div>
    </div>
  );
};

export default NotificationTemplatesModal;
