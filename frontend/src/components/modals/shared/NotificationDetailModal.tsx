import React, { useState, useEffect } from 'react';
import { 
  X, Clock, Calendar, Copy, Check, Briefcase, 
  ShieldCheck, AlertCircle, CheckCircle2, MessageSquare, 
  UserPlus, FileText, Zap, Edit3, Radio, TrendingUp, Lock, Tag, User
} from 'lucide-react';
import { NotificationItem } from '../../../types';

export interface NotificationDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  notification: NotificationItem | null;
  userRole?: string;
}

const NotificationDetailModal: React.FC<NotificationDetailModalProps> = ({
  isOpen,
  onClose,
  notification,
  userRole
}) => {
  const [copied, setCopied] = useState(false);

  // Close on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Reset copied status when notification changes
  useEffect(() => {
    setCopied(false);
  }, [notification]);

  if (!isOpen || !notification) return null;

  const handleCopyMessage = async () => {
    const textToCopy = notification.desc || notification.message || '';
    if (!textToCopy) return;

    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy notification text:', err);
    }
  };

  const renderIcon = (iconName?: string) => {
    const props = { size: 20 };
    switch (iconName) {
      case 'UserPlus': return <UserPlus {...props} />;
      case 'Briefcase': return <Briefcase {...props} />;
      case 'FileText': return <FileText {...props} />;
      case 'ShieldCheck': return <ShieldCheck {...props} />;
      case 'Zap': return <Zap {...props} />;
      case 'Edit3': return <Edit3 {...props} />;
      case 'Radio': return <Radio {...props} />;
      case 'MessageSquare': return <MessageSquare {...props} />;
      case 'TrendingUp': return <TrendingUp {...props} />;
      case 'Clock': return <Clock {...props} />;
      default: return <AlertCircle {...props} />;
    }
  };

  const roleLabel = userRole === 'CANDIDATE' 
    ? 'Candidate Notification' 
    : userRole === 'HR' 
      ? 'Recruitment Alert' 
      : 'System Console Alert';

  const fullText = notification.desc || notification.message || 'No description provided for this notification.';

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="notification-modal-title"
    >
      <div 
        className="bg-white w-full max-w-lg rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200 border border-slate-100 flex flex-col relative max-h-[90vh]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Accent Gradient Bar */}
        <div className="h-1.5 w-full bg-gradient-to-r from-[#D60041] via-rose-500 to-amber-500 shrink-0" />

        {/* Modal Header */}
        <div className="px-5 sm:px-6 pt-5 pb-4 border-b border-gray-100 flex items-start justify-between gap-4 shrink-0 bg-white">
          <div className="flex items-start gap-3.5 min-w-0">
            {/* Notification Category Icon */}
            <div className={`w-11 h-11 sm:w-12 sm:h-12 rounded-2xl flex items-center justify-center shrink-0 border border-black/5 shadow-2xs mt-0.5 ${notification.bgColor || 'bg-slate-50'} ${notification.textColor || 'text-slate-700'}`}>
              {renderIcon(notification.icon)}
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="text-[10px] sm:text-[11px] font-black uppercase tracking-wider text-slate-400">
                  {roleLabel}
                </span>

                {notification.tag && (
                  <span className={`text-[9px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider ${notification.tagColor || 'bg-slate-100 text-slate-700'}`}>
                    {notification.tag}
                  </span>
                )}

                {!notification.read && (
                  <span className="inline-flex items-center gap-1 text-[9px] font-bold text-[#D60041] bg-rose-50 border border-rose-200/80 px-2 py-0.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#D60041] animate-pulse" /> Unread
                  </span>
                )}
              </div>

              <h3 
                id="notification-modal-title"
                className="text-base sm:text-lg font-black text-slate-900 tracking-tight leading-snug break-words"
              >
                {notification.title || 'Notification Details'}
              </h3>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close modal"
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer shrink-0 -mr-1"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body: Scrollable Details */}
        <div className="px-5 sm:px-6 py-4 overflow-y-auto custom-scrollbar space-y-4">
          {/* Metadata badges row */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] sm:text-xs text-slate-500 bg-slate-50/80 p-3 rounded-xl border border-slate-100">
            <div className="flex items-center gap-1.5 font-semibold text-slate-700">
              <Calendar size={13} className="text-[#D60041] shrink-0" />
              <span>{notification.fullDateTime || notification.displayDateTime || notification.timeStr || notification.time}</span>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {notification.relativeTime && (
                <span className="text-[10px] font-bold text-slate-500 bg-white border border-slate-200/80 px-2 py-0.5 rounded-full shadow-2xs">
                  {notification.relativeTime}
                </span>
              )}
              {notification.sender_role && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 bg-indigo-50 border border-indigo-200/80 px-2 py-0.5 rounded-full">
                  <User size={10} /> Sender: {notification.sender_role}
                </span>
              )}
            </div>
          </div>

          {/* Full Message Box */}
          <div>
            <label className="block text-[10px] sm:text-[11px] font-black uppercase tracking-wider text-slate-400 mb-1.5">
              Detailed Message
            </label>
            <div className="bg-slate-50/50 border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-2xs">
              <p className="text-xs sm:text-sm font-medium text-slate-800 leading-relaxed whitespace-pre-wrap break-words select-text">
                {fullText}
              </p>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 sm:px-6 py-3.5 bg-slate-50 border-t border-gray-100 flex items-center justify-between gap-3 shrink-0">
          <button
            type="button"
            onClick={handleCopyMessage}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100/80 border border-slate-200/80 px-3.5 py-2 rounded-xl transition-all cursor-pointer shadow-2xs active:scale-95"
          >
            {copied ? (
              <>
                <Check size={14} className="text-emerald-600" />
                <span className="text-emerald-600">Copied to Clipboard!</span>
              </>
            ) : (
              <>
                <Copy size={14} className="text-slate-500" />
                <span>Copy Message</span>
              </>
            )}
          </button>

          <button
            type="button"
            onClick={onClose}
            className="px-5 py-2 bg-[#D60041] hover:bg-[#B50037] text-white text-xs font-black uppercase tracking-wider rounded-xl transition-all shadow-md shadow-pink-200 hover:shadow-lg active:scale-95 cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationDetailModal;
