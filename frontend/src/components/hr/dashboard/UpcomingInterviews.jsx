import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Calendar, Clock, Video, User, ChevronRight, 
  Plus, CheckCircle2, AlertCircle, ArrowUpRight, Sparkles 
} from 'lucide-react';
import { useGetAllInterviewsQuery } from '../../../redux/api/apiSlice';

const UpcomingInterviews = ({ onScheduleClick }) => {
  const navigate = useNavigate();
  const { data: interviews = [], isLoading } = useGetAllInterviewsQuery();

  // Filter and sort for upcoming interviews
  const upcomingInterviews = [...interviews]
    .filter(item => {
      const status = (item.status || '').toUpperCase();
      return status !== 'CANCELLED' && status !== 'REJECTED';
    })
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
    .slice(0, 4);

  const formatInterviewTime = (startStr) => {
    if (!startStr) return { dateStr: 'TBD', timeStr: 'TBD', isToday: false };
    const dateObj = new Date(startStr);
    const today = new Date();
    const isToday = 
      dateObj.getDate() === today.getDate() &&
      dateObj.getMonth() === today.getMonth() &&
      dateObj.getFullYear() === today.getFullYear();

    const dateStr = isToday
      ? 'Today'
      : dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric', weekday: 'short' });

    const timeStr = dateObj.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });

    return { dateStr, timeStr, isToday };
  };

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-6 shadow-xs flex flex-col justify-between">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-pink-50 text-[#D60041] flex items-center justify-center font-bold">
              <Calendar size={18} />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
                Upcoming Interviews
                {upcomingInterviews.length > 0 && (
                  <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-pink-50 text-[#D60041] border border-pink-100">
                    {upcomingInterviews.length}
                  </span>
                )}
              </h3>
              <p className="text-[11px] text-slate-500 font-medium">Candidate evaluation schedule</p>
            </div>
          </div>

          <button
            onClick={() => navigate('/hr/scheduling')}
            className="text-[11px] font-bold text-[#D60041] hover:text-[#b50037] flex items-center gap-1 transition-colors"
          >
            <span>Calendar</span>
            <ChevronRight size={14} />
          </button>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="space-y-3 py-2 animate-pulse">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-16 bg-slate-50 rounded-2xl"></div>
            ))}
          </div>
        ) : upcomingInterviews.length === 0 ? (
          <div className="py-8 px-4 text-center flex flex-col items-center justify-center">
            <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 mb-3 shadow-inner">
              <Clock size={22} />
            </div>
            <h4 className="text-sm font-bold text-slate-800">No Interviews Today</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-[240px]">
              No upcoming interview sessions found in the queue.
            </p>
            <button
              onClick={() => onScheduleClick ? onScheduleClick() : navigate('/hr/scheduling')}
              className="mt-4 px-3.5 py-1.5 bg-slate-900 hover:bg-[#D60041] text-white text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 shadow-sm active:scale-95"
            >
              <Plus size={14} />
              <span>Schedule Session</span>
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {upcomingInterviews.map((item) => {
              const { dateStr, timeStr, isToday } = formatInterviewTime(item.start_time);
              return (
                <div
                  key={item.id}
                  className="p-3 sm:p-3.5 rounded-2xl border border-slate-100 hover:border-pink-200/80 bg-slate-50/50 hover:bg-white hover:shadow-md transition-all duration-200 group flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {/* Time Badge */}
                    <div className={`w-14 shrink-0 text-center py-1.5 px-1 rounded-xl flex flex-col justify-center ${
                      isToday 
                        ? 'bg-gradient-to-br from-rose-500 to-[#D60041] text-white shadow-xs' 
                        : 'bg-white border border-slate-200/90 text-slate-700'
                    }`}>
                      <span className={`text-[9px] font-black uppercase tracking-wider ${isToday ? 'text-rose-100' : 'text-slate-400'}`}>
                        {dateStr}
                      </span>
                      <span className="text-[11px] font-black leading-tight">
                        {timeStr.split(' ')[0]}
                      </span>
                      <span className={`text-[8px] font-bold ${isToday ? 'text-rose-100' : 'text-slate-400'}`}>
                        {timeStr.split(' ')[1] || ''}
                      </span>
                    </div>

                    {/* Candidate & Role Info */}
                    <div className="min-w-0">
                      <h4 className="text-xs sm:text-sm font-bold text-slate-900 group-hover:text-[#D60041] transition-colors truncate">
                        {item.candidate_name || item.title || 'Applicant'}
                      </h4>
                      <p className="text-[11px] text-slate-500 truncate mt-0.5">
                        {item.job_title || 'Position Interview'}
                      </p>
                      {item.interviewer_name && (
                        <p className="text-[10px] text-slate-400 font-medium truncate flex items-center gap-1 mt-0.5">
                          <User size={10} />
                          <span>Panel: {item.interviewer_name}</span>
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    {item.meeting_link ? (
                      <a
                        href={item.meeting_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-2.5 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200/80 rounded-xl text-[11px] font-black flex items-center gap-1 transition-colors"
                        title="Join Virtual Room"
                      >
                        <Video size={13} />
                        <span className="hidden sm:inline">Join</span>
                      </a>
                    ) : (
                      <button
                        onClick={() => navigate('/hr/scheduling')}
                        className="p-1.5 text-slate-400 hover:text-[#D60041] hover:bg-pink-50 rounded-lg transition-colors"
                        title="View Interview in Calendar"
                      >
                        <ArrowUpRight size={15} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer link */}
      <div className="pt-4 mt-3 border-t border-slate-100 flex items-center justify-between text-xs">
        <span className="text-slate-400 font-medium text-[11px]">Syncs with Google Calendar</span>
        <button
          onClick={() => navigate('/hr/scheduling')}
          className="font-bold text-[#D60041] hover:underline flex items-center gap-1 text-[11px]"
        >
          <span>Open Calendar</span>
          <ChevronRight size={13} />
        </button>
      </div>
    </div>
  );
};

export default UpcomingInterviews;
