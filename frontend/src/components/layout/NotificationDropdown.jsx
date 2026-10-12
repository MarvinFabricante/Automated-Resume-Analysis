import React from 'react';
import { 
  Clock, Calendar, ShieldCheck, Briefcase, 
  AlertCircle, CheckCircle2, MessageSquare, ChevronRight,
  UserPlus, FileText, Zap, Edit3, Radio, TrendingUp, Lock, Check, X
} from 'lucide-react';

const NotificationDropdown = ({ userRole, notifications = [], onMarkAllRead, onClose }) => {
  const [showAll, setShowAll] = React.useState(false);

  const renderIcon = (iconName) => {
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
    <div className="fixed sm:absolute inset-x-2.5 sm:inset-x-auto sm:right-0 top-16 sm:top-[calc(100%+12px)] w-auto sm:w-[400px] max-w-none sm:max-w-[400px] bg-white border border-gray-200/90 rounded-2xl sm:rounded-3xl shadow-2xl py-4 sm:py-5 z-[70] animate-in fade-in slide-in-from-top-3 duration-200 max-h-[85vh] sm:max-h-[580px] flex flex-col">
      
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
      <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-2 custom-scrollbar space-y-2">
        {displayNotifications.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center text-center px-6">
            <div className="w-14 h-14 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mb-3 border border-emerald-100 shadow-2xs">
              <CheckCircle2 size={28} />
            </div>
            <h5 className="text-sm font-black text-slate-900 mb-1">All Caught Up!</h5>
            <p className="text-xs text-slate-400 font-medium">No alerts or notifications at the moment.</p>
          </div>
        ) : (
          displayNotifications.map((notif) => (
            <div 
              key={notif.id} 
              className={`p-3 sm:p-3.5 rounded-xl sm:rounded-2xl transition-all border relative overflow-hidden group ${
                !notif.read 
                  ? 'bg-rose-50/30 border-rose-100/90 hover:bg-rose-50/50 hover:border-rose-200 shadow-2xs' 
                  : 'bg-white border-gray-100 hover:bg-slate-50/80 hover:border-gray-200 opacity-80 hover:opacity-100'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Notification Category Icon */}
                <div className={`w-9 h-9 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center shrink-0 border border-black/5 mt-0.5 shadow-2xs ${notif.bgColor} ${notif.textColor}`}>
                  {renderIcon(notif.icon)}
                </div>

                <div className="min-w-0 flex-1">
                  {/* Title & Tag header */}
                  <div className="flex items-start justify-between gap-1.5 mb-1">
                    <h5 className={`text-xs sm:text-sm truncate ${!notif.read ? 'font-black text-slate-950' : 'font-bold text-slate-700'}`}>
                      {notif.title}
                    </h5>
                    
                    <div className="flex items-center gap-1.5 shrink-0">
                      {notif.tag && (
                        <span className={`text-[9px] font-black px-1.5 py-0.5 rounded uppercase tracking-wider ${notif.tagColor}`}>
                          {notif.tag}
                        </span>
                      )}
                      {!notif.read && (
                        <span className="w-2 h-2 rounded-full bg-[#D60041] shrink-0 animate-pulse" title="Unread" />
                      )}
                    </div>
                  </div>

                  {/* Message body */}
                  <p className="text-xs text-slate-600 font-medium leading-relaxed line-clamp-2 mb-2">
                    {notif.desc}
                  </p>

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
          ))
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
  );
};

export default NotificationDropdown;
