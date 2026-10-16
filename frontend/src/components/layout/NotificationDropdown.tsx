import React, { useState } from 'react';
import { 
  Clock, ShieldCheck, Briefcase, 
  AlertCircle, CheckCircle2, MessageSquare, ChevronRight,
  UserPlus, FileText, Zap, Edit3, Radio, TrendingUp, Lock, X,
  Maximize2, ChevronDown, ChevronUp
} from 'lucide-react';
import { NotificationItem } from '../../types';
import NotificationDetailModal from '../modals/shared/NotificationDetailModal';

export interface NotificationDropdownProps {
  userRole?: string;
  notifications?: NotificationItem[];
  onMarkAllRead?: () => void;
  onClose?: () => void;
}

const NotificationDropdown: React.FC<NotificationDropdownProps> = ({ 
  userRole, 
  notifications = [], 
  onMarkAllRead, 
  onClose 
}) => {
  const [showAll, setShowAll] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Record<string | number, boolean>>({});
  const [selectedNotification, setSelectedNotification] = useState<NotificationItem | null>(null);

  const toggleExpand = (id: string | number) => {
    setExpandedIds(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const isLongMessage = (desc?: string) => {
    if (!desc) return false;
    return desc.length > 70 || desc.includes('\n');
  };

  const renderIcon = (iconName?: string) => {
    const props = { size: 16 };
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

  const unreadCount = notifications.filter(n => !n.read).length;
  const displayNotifications = showAll ? notifications : notifications.slice(0, 10);

  return (
    <>
      <div className="fixed sm:absolute inset-x-2.5 sm:inset-x-auto sm:right-0 top-16 sm:top-[calc(100%+12px)] w-auto sm:w-[420px] max-w-none sm:max-w-[420px] bg-white border border-gray-200/90 rounded-2xl sm:rounded-3xl shadow-2xl py-4 sm:py-5 z-[70] animate-in fade-in slide-in-from-top-3 duration-200 max-h-[85vh] sm:max-h-[580px] flex flex-col">
        
        {/* ─── Header ─── */}
        <div className="px-4 sm:px-6 pb-3 sm:pb-3.5 border-b border-gray-100 flex justify-between items-center shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm sm:text-base font-black text-slate-900 tracking-tight">
                {userRole === 'CANDIDATE' ? 'Your Updates' : userRole === 'HR' ? 'Recruitment Alerts' : 'System Console'}
              </h4>
              <span className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-amber-700 bg-amber-50 border border-amber-200/80 px-2 py-0.5 rounded-full shadow-2xs">
                <Lock size={10} className="text-amber-600" /> Read-Only
              </span>
            </div>
            <p className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">
              {unreadCount > 0 ? (
                <span className="text-[#D60041]">{unreadCount} Unread {unreadCount === 1 ? 'Alert' : 'Alerts'}</span>
              ) : (
                <span>All Alerts Read ({notifications.length})</span>
              )}
            </p>
          </div>

          <div className="flex items-center gap-1.5">
            {unreadCount > 0 && (
              <button 
                type="button"
                onClick={onMarkAllRead}
                className="text-[11px] font-bold text-[#D60041] hover:text-[#B50037] active:scale-95 px-2.5 py-1 rounded-lg hover:bg-rose-50 transition-all cursor-pointer whitespace-nowrap"
              >
                Mark all read
              </button>
            )}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close notifications"
                className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              >
                <X size={16} />
              </button>
            )}
          </div>
        </div>

        {/* ─── Scrollable Notification List ─── */}
        <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-2 custom-scrollbar space-y-2.5">
          {displayNotifications.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-center px-6">
              <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mb-3 border border-emerald-100 shadow-2xs">
                <CheckCircle2 size={28} />
              </div>
              <h5 className="text-sm font-black text-slate-900 mb-1">All Caught Up!</h5>
              <p className="text-xs text-slate-400 font-medium">No alerts or notifications at the moment.</p>
            </div>
          ) : (
            displayNotifications.map((notif) => {
              const isLong = isLongMessage(notif.desc);
              const isExpanded = !!expandedIds[notif.id];

              return (
                <div 
                  key={notif.id} 
                  onClick={() => setSelectedNotification(notif)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setSelectedNotification(notif);
                    }
                  }}
                  className={`p-3 sm:p-3.5 rounded-xl sm:rounded-2xl transition-all border relative overflow-hidden group cursor-pointer focus:outline-hidden focus:ring-2 focus:ring-[#D60041]/30 ${
                    !notif.read 
                      ? 'bg-rose-50/30 border-rose-100/90 hover:bg-rose-50/60 hover:border-rose-200 shadow-2xs' 
                      : 'bg-white border-gray-100 hover:bg-slate-50 hover:border-gray-200 opacity-90 hover:opacity-100'
                  } ${isExpanded ? 'ring-1 ring-[#D60041]/20 bg-rose-50/20' : ''}`}
                >
                  <div className="flex items-start gap-3">
                    {/* Notification Category Icon */}
                    <div className={`w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 border border-black/5 mt-0.5 shadow-2xs ${notif.bgColor} ${notif.textColor}`}>
                      {renderIcon(notif.icon)}
                    </div>

                    <div className="min-w-0 flex-1">
                      {/* Title & Tag header */}
                      <div className="flex items-start justify-between gap-1.5 mb-1">
                        <h5 className={`text-xs sm:text-sm ${isExpanded ? 'break-words' : 'truncate'} ${!notif.read ? 'font-black text-slate-950' : 'font-bold text-slate-700'}`}>
                          {notif.title}
                        </h5>
                        
                        <div className="flex items-center gap-1 shrink-0 ml-1">
                          {notif.tag && (
                            <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-wider ${notif.tagColor}`}>
                              {notif.tag}
                            </span>
                          )}

                          {/* Enlarge in Modal Button */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedNotification(notif);
                            }}
                            title="Enlarge notification details"
                            aria-label="Enlarge notification details"
                            className="p-1 rounded-md text-slate-400 hover:text-[#D60041] hover:bg-rose-50 transition-colors cursor-pointer"
                          >
                            <Maximize2 size={12} />
                          </button>

                          {!notif.read && (
                            <span className="w-2 h-2 rounded-full bg-[#D60041] shrink-0 animate-pulse ml-0.5" title="Unread" />
                          )}
                        </div>
                      </div>

                      {/* Message body */}
                      <p className={`text-xs text-slate-600 font-medium leading-relaxed mb-1.5 ${
                        isExpanded 
                          ? 'whitespace-pre-wrap break-words text-slate-800' 
                          : 'line-clamp-2'
                      }`}>
                        {notif.desc}
                      </p>

                      {/* Interactive Expand / Enlarge Controls for Long Messages */}
                      {isLong && (
                        <div className="flex items-center justify-between gap-2 mb-2 pt-1 border-t border-slate-100/70">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleExpand(notif.id);
                            }}
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-[#D60041] hover:text-[#B50037] hover:underline cursor-pointer transition-colors"
                          >
                            {isExpanded ? (
                              <>
                                <ChevronUp size={12} />
                                <span>Show less</span>
                              </>
                            ) : (
                              <>
                                <ChevronDown size={12} />
                                <span>Show more</span>
                              </>
                            )}
                          </button>

                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedNotification(notif);
                            }}
                            className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-600 hover:text-[#D60041] bg-slate-100/80 hover:bg-rose-50 border border-slate-200/80 px-2 py-0.5 rounded-md transition-all cursor-pointer shadow-2xs"
                          >
                            <Maximize2 size={10} />
                            <span>Enlarge</span>
                          </button>
                        </div>
                      )}

                      {/* Accurate Date & Time Footer */}
                      <div className="flex items-center justify-between gap-2 pt-1.5 border-t border-slate-100 text-[10px] sm:text-[11px]">
                        <div 
                          className="flex items-center gap-1.5 text-slate-600 font-semibold truncate hover:text-[#D60041] transition-colors"
                          title={`Created: ${notif.fullDateTime || notif.displayDateTime || notif.time}`}
                        >
                          <Clock size={11} className="text-[#D60041] shrink-0" />
                          <span className="truncate">{notif.displayDateTime || notif.time}</span>
                        </div>

                        <span className="text-[9px] sm:text-[10px] font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full shrink-0">
                          {notif.relativeTime || notif.time}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ─── Footer: Expand / Collapse All ─── */}
        {notifications.length > 10 && (
          <div className="px-4 sm:px-6 pt-2.5 pb-1 border-t border-gray-100 shrink-0">
            <button 
              type="button"
              onClick={() => setShowAll(!showAll)}
              className="w-full py-2 bg-slate-50 hover:bg-[#D60041] hover:text-white rounded-xl text-[10px] font-black text-slate-600 uppercase tracking-widest transition-all flex items-center justify-center gap-2 group cursor-pointer shadow-2xs"
            >
              <span>{showAll ? 'Show Fewer' : `View All (${notifications.length})`}</span>
              <ChevronRight size={12} className={`transition-transform ${showAll ? '-rotate-90' : 'rotate-90 sm:rotate-0 sm:group-hover:translate-x-1'}`} />
            </button>
          </div>
        )}

      </div>

      {/* ─── Detailed Enlarged Notification Modal ─── */}
      <NotificationDetailModal
        isOpen={!!selectedNotification}
        onClose={() => setSelectedNotification(null)}
        notification={selectedNotification}
        userRole={userRole}
      />
    </>
  );
};

export default NotificationDropdown;

