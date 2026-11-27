import React from 'react';
import { useNavigate } from '@/utils/navigation';
import { 
  Calendar, Clock, Video, User, ChevronRight, 
  Plus, ArrowUpRight
} from 'lucide-react';
import { useGetAllInterviewsQuery } from '../../../redux/api/apiSlice';
import { Interview } from '../../../types';
import {
  filterAndSortUpcomingInterviews,
} from '../../../utils/interviewUtils';
import { getJoinButtonLabel } from '../../../utils/meetingPlatform';

interface UpcomingInterviewsProps {
  onScheduleClick?: () => void;
}

const UpcomingInterviews: React.FC<UpcomingInterviewsProps> = ({ onScheduleClick }) => {
  const navigate = useNavigate();
  const { data: interviews = [], isLoading } = useGetAllInterviewsQuery(undefined, {
    pollingInterval: 5000,
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    refetchOnReconnect: true,
  });

  // Filter and sort for truly upcoming active interviews
  const upcomingInterviews = filterAndSortUpcomingInterviews(interviews as Interview[]).slice(0, 4);

  const formatInterviewTime = (startStr?: string) => {
    if (!startStr) return { dateStr: 'TBD', timeStr: 'TBD', isToday: false };
    const dateObj = new Date(startStr);
    const today = new Date();
    const isToday = 
      dateObj.getDate() === today.getDate() &&
      dateObj.getMonth() === today.getMonth() &&
      dateObj.getFullYear() === today.getFullYear();

    const dateStr = isToday
      ? 'Today'
      : dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

    const timeStr = dateObj.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });

    return { dateStr, timeStr, isToday };
  };

  return (
    <div
      data-testid="upcoming-interviews-card"
      className="bg-white border border-slate-200/80 rounded-2xl p-4 sm:p-6 lg:p-8 shadow-xs flex flex-col justify-between"
    >
      {/* Header */}
      <div>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center pb-4 mb-4 sm:pb-5 sm:mb-5 border-b border-slate-100 gap-3 sm:gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#D60041] border border-rose-100 flex items-center justify-center font-bold shrink-0">
              <Calendar size={18} />
            </div>
            <div>
              <h3 className="text-base sm:text-lg md:text-xl font-semibold text-slate-900 tracking-tight flex items-center gap-2 flex-wrap">
                <span>Upcoming Interviews</span>
                {upcomingInterviews.length > 0 && (
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-rose-50 text-[#D60041] border border-rose-100/90">
                    {upcomingInterviews.length} Scheduled
                  </span>
                )}
              </h3>
              <p className="text-xs sm:text-xs text-slate-500 font-medium mt-0.5">
                Candidate evaluation schedule and upcoming panel sessions
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 self-end sm:self-auto">
            <button
              type="button"
              onClick={() => onScheduleClick ? onScheduleClick() : navigate('/hr/scheduling')}
              className="px-3.5 py-2 bg-rose-50 hover:bg-rose-100 text-[#D60041] border border-rose-200/90 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 shadow-2xs active:scale-95 cursor-pointer"
            >
              <Plus size={14} />
              <span>Schedule Session</span>
            </button>
            <button
              type="button"
              onClick={() => navigate('/hr/scheduling')}
              className="text-xs font-bold text-[#D60041] hover:text-[#b50037] flex items-center gap-1 transition-colors cursor-pointer"
            >
              <span>Calendar</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 py-2 animate-pulse">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-20 bg-slate-50 rounded-2xl"></div>
            ))}
          </div>
        ) : upcomingInterviews.length === 0 ? (
          <div className="py-10 px-4 text-center flex flex-col items-center justify-center bg-slate-50/50 rounded-2xl border border-slate-100">
            <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 flex items-center justify-center text-slate-500 mb-3 shadow-inner">
              <Clock size={22} />
            </div>
            <h4 className="text-sm font-bold text-slate-800">No upcoming interviews</h4>
            <p className="text-xs text-slate-500 mt-1 max-w-xs">
              No upcoming interview sessions found in the queue.
            </p>
            <button
              type="button"
              onClick={() => onScheduleClick ? onScheduleClick() : navigate('/hr/scheduling')}
              className="mt-4 px-4 py-2 bg-slate-900 hover:bg-[#D60041] text-white text-xs font-bold rounded-xl transition-all flex items-center gap-1.5 shadow-sm active:scale-95 cursor-pointer"
            >
              <Plus size={14} />
              <span>Schedule Session</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 sm:gap-4">
            {upcomingInterviews.map((item) => {
              const { dateStr, timeStr, isToday } = formatInterviewTime(item.start_time);
              return (
                <div
                  key={item.id}
                  data-testid="upcoming-interview-item"
                  onClick={() => navigate('/hr/scheduling')}
                  className="p-4 sm:p-4.5 rounded-2xl border border-slate-200/90 hover:border-rose-200/90 bg-white hover:shadow-md transition-all duration-200 group flex items-center justify-between gap-3.5 cursor-pointer"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    {/* Time Badge */}
                    <div className={`w-15 shrink-0 text-center py-2 px-1.5 rounded-xl flex flex-col justify-center ${
                      isToday 
                        ? 'bg-gradient-to-br from-rose-500 to-[#D60041] text-white shadow-xs' 
                        : 'bg-slate-50 border border-slate-200/90 text-slate-700'
                    }`}>
                      <span className={`text-[10.5px] font-semibold uppercase tracking-wider ${isToday ? 'text-rose-100' : 'text-slate-500'}`}>
                        {dateStr}
                      </span>
                      <span className="text-xs sm:text-sm font-bold leading-tight mt-0.5">
                        {timeStr.split(' ')[0]}
                      </span>
                      <span className={`text-[10.5px] font-bold ${isToday ? 'text-rose-100' : 'text-slate-500'}`}>
                        {timeStr.split(' ')[1] || ''}
                      </span>
                    </div>

                    {/* Candidate & Role Info */}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-sm sm:text-base font-semibold text-slate-900 group-hover:text-[#D60041] transition-colors truncate">
                          {item.candidate_name || item.title || 'Applicant'}
                        </h4>
                        {isToday && (
                          <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md bg-rose-50 text-[#D60041] border border-rose-200/80">
                            Today
                          </span>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-slate-600 truncate mt-0.5">
                        {item.job_title || 'Position Interview'}
                      </p>
                      {item.interviewer_name && (
                        <p className="text-xs text-slate-500 font-medium truncate flex items-center gap-1 mt-1">
                          <User size={11} className="text-slate-400 shrink-0" />
                          <span className="truncate">Panel: {item.interviewer_name}</span>
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
                        onClick={(e) => e.stopPropagation()}
                        className="px-3 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200/80 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs"
                        title={getJoinButtonLabel(item.meeting_link, item.platform)}
                      >
                        <Video size={14} />
                        <span>{getJoinButtonLabel(item.meeting_link, item.platform, { compact: true })}</span>
                      </a>
                    ) : (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate('/hr/scheduling');
                        }}
                        className="p-2 text-slate-500 hover:text-[#D60041] bg-slate-50 hover:bg-rose-50 border border-slate-200/80 hover:border-rose-200 rounded-xl transition-colors cursor-pointer"
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
      <div className="pt-4 mt-5 border-t border-slate-100 flex items-center justify-between text-xs">
        <span className="text-slate-500 font-medium text-xs">Syncs with Google Calendar</span>
        <button
          onClick={() => navigate('/hr/scheduling')}
          className="font-bold text-[#D60041] hover:underline flex items-center gap-1 text-xs cursor-pointer"
        >
          <span>Open Calendar</span>
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
};

export default UpcomingInterviews;
