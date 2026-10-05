import React from 'react';
import { 
  Clock, User, ShieldCheck, Briefcase, 
  AlertCircle, CheckCircle2, MessageSquare, ChevronRight,
  UserPlus, FileText, Zap, Edit3, Radio, TrendingUp
} from 'lucide-react';

const NotificationDropdown = ({ userRole, notifications, onMarkAllRead }) => {
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

  const displayNotifications = showAll ? [
    ...notifications,
    { id: 10, title: 'Old Alert', desc: 'This is an archived notification from yesterday.', time: '1d ago', type: 'system', icon: 'Clock', bgColor: 'bg-slate-50', textColor: 'text-slate-400', read: true },
    { id: 11, title: 'Previous Update', desc: 'Your profile was verified by the system.', time: '2d ago', type: 'system', icon: 'ShieldCheck', bgColor: 'bg-slate-50', textColor: 'text-slate-400', read: true }
  ] : notifications;

  return (
    <div className="absolute right-0 sm:right-0 -right-4 sm:translate-x-0 top-[calc(100%+16px)] w-[calc(100vw-2rem)] sm:w-[380px] max-w-[380px] bg-white border border-gray-100 rounded-[32px] shadow-2xl py-6 z-[60] animate-in fade-in slide-in-from-top-4 duration-300">
      <div className="px-6 sm:px-8 pb-6 border-b border-gray-50 flex justify-between items-center">
        <div>
          <h4 className="text-base font-black text-slate-900">
            {userRole === 'CANDIDATE' ? 'Your Updates' : userRole === 'HR' ? 'Recruitment Alerts' : 'System Console'}
          </h4>
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest mt-0.5">
            {notifications.filter(n => !n.read).length} Unread {notifications.filter(n => !n.read).length === 1 ? 'Alert' : 'Alerts'}
          </p>
        </div>
        <button 
          onClick={onMarkAllRead}
          className="text-[10px] font-black text-[#D60041] uppercase tracking-widest hover:underline decoration-2 underline-offset-4 transition-all"
        >
          Mark all read
        </button>
      </div>

      <div className="max-h-[420px] overflow-y-auto px-4 py-2 custom-scrollbar">
        {displayNotifications.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center text-center px-8">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mb-4 border border-slate-100">
              <CheckCircle2 className="text-slate-200" size={32} />
            </div>
            <h5 className="text-sm font-black text-slate-900 mb-1">All Caught Up!</h5>
            <p className="text-xs text-slate-400 font-medium">No new notifications at the moment.</p>
          </div>
        ) : (
          displayNotifications.map((notif) => (
            <div key={notif.id} className={`p-4 rounded-2xl hover:bg-slate-50 transition-all cursor-pointer group border border-transparent hover:border-gray-100 mt-2 relative overflow-hidden ${notif.read ? 'opacity-60' : ''}`}>
              {!notif.read && (
                <div className="absolute top-4 right-4 w-2 h-2 bg-[#D60041] rounded-full" />
              )}
              <div className="flex gap-4">
                <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border border-gray-100 group-hover:border-pink-100 transition-colors ${notif.bgColor} ${notif.textColor}`}>
                  {renderIcon(notif.icon)}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex justify-between items-start mb-1.5">
                    <h5 className="text-sm font-black text-slate-900 truncate pr-4">{notif.title}</h5>
                  </div>
                  <p className="text-xs text-slate-500 font-medium leading-relaxed line-clamp-2 mb-2">{notif.desc}</p>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-300 uppercase tracking-widest">
                      <Clock size={10} />
                      {notif.time}
                    </div>
                    {notif.tag && (
                      <span className={`text-[8px] font-black px-1.5 py-0.5 rounded uppercase tracking-tighter ${notif.tagColor}`}>
                        {notif.tag}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {!showAll && (
        <div className="px-8 pt-4 border-t border-gray-50 mt-2">
          <button 
            onClick={() => setShowAll(true)}
            className="w-full py-4 bg-slate-50 hover:bg-slate-900 hover:text-white rounded-2xl text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-2 group"
          >
            View Complete History <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>
      )}
    </div>
  );
};

export default NotificationDropdown;
