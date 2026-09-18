import React from 'react';
import { Calendar, Clock, Video, User, ExternalLink } from 'lucide-react';
import { useSelector } from 'react-redux';
import { useGetCandidateInterviewsQuery } from '../../../redux/api/apiSlice';

const UpcomingInterviews = () => {
  const { user: email } = useSelector((state) => state.auth);
  const { data: interviews = [], isLoading } = useGetCandidateInterviewsQuery(email, {
    skip: !email,
    pollingInterval: 10000,
  });

  const activeInterviews = interviews
    .filter((i) => i.status !== 'CANCELED' && i.status !== 'COMPLETED')
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

  return (
    <div className="bg-white border border-slate-100 rounded-[40px] p-8 sm:p-10 shadow-xl shadow-slate-200/40">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-pink-50 rounded-2xl flex items-center justify-center text-[#D10043] border border-pink-100 shadow-sm">
            <Calendar size={22} />
          </div>
          <div>
            <h3 className="text-xl font-black text-slate-900 tracking-tight">Interview Schedule</h3>
            <p className="text-xs text-slate-400 font-semibold mt-0.5">Upcoming evaluation sessions</p>
          </div>
        </div>
        {activeInterviews.length > 0 && (
          <span className="text-xs font-black text-[#D10043] bg-pink-50 border border-pink-200 px-3 py-1 rounded-full uppercase tracking-wider">
            {activeInterviews.length} Scheduled
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="bg-slate-50/50 rounded-[32px] p-8 border border-slate-100 text-center animate-pulse">
          <div className="h-4 bg-slate-200 rounded w-1/3 mx-auto mb-3" />
          <div className="h-8 bg-slate-100 rounded w-1/2 mx-auto" />
        </div>
      ) : activeInterviews.length === 0 ? (
        <div className="bg-slate-50/50 rounded-[32px] p-8 border border-slate-100 text-center space-y-2">
          <Calendar size={28} className="mx-auto text-slate-300" />
          <p className="text-sm text-slate-600 font-bold">No upcoming interviews scheduled yet.</p>
          <p className="text-xs text-slate-400">Our HR panel is reviewing your applications. You will see your meeting schedule here once scheduled.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {activeInterviews.map((iv) => {
            const startDate = new Date(iv.start_time);
            const endDate = new Date(iv.end_time);

            return (
              <div
                key={iv.id}
                className="bg-slate-50/70 hover:bg-pink-50/30 rounded-[32px] p-6 border border-slate-100 hover:border-[#D10043]/20 relative group overflow-hidden transition-all shadow-sm"
              >
                <div className="absolute top-0 right-0 w-2 h-full bg-[#D10043] opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="flex items-center justify-between mb-3">
                  <span className="bg-orange-100 text-orange-700 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                    {iv.status || 'Upcoming'}
                  </span>
                  <span className="bg-blue-100 text-blue-700 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1">
                    <Video size={10} /> Google Meet
                  </span>
                </div>

                <h4 className="font-black text-lg text-slate-900 mb-1 leading-tight tracking-tight">
                  {iv.title}
                </h4>

                {iv.job_title && (
                  <p className="text-xs text-slate-500 font-medium mb-2">
                    Position: <strong className="text-slate-800">{iv.job_title}</strong>
                  </p>
                )}

                {iv.interviewer_name && (
                  <p className="text-xs text-[#D10043] font-bold flex items-center gap-1.5 mb-4">
                    <User size={13} /> Panelist: {iv.interviewer_name}
                  </p>
                )}

                <div className="flex flex-wrap items-center text-xs text-slate-700 font-bold mb-5 bg-white p-3 rounded-2xl border border-slate-100 shadow-sm gap-2">
                  <Clock className="w-4 h-4 text-[#D10043] shrink-0" />
                  <span>
                    {startDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                  <span className="text-slate-300">•</span>
                  <span>
                    {startDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })} – {endDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}
                  </span>
                </div>

                {iv.meeting_link ? (
                  <a
                    href={iv.meeting_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-3.5 bg-[#D10043] hover:bg-slate-900 text-white rounded-2xl text-[11px] font-black uppercase tracking-[0.15em] transition-all shadow-md hover:shadow-lg active:scale-[0.98] flex items-center justify-center gap-2 group/btn block text-center"
                  >
                    <Video size={15} className="group-hover/btn:animate-pulse" /> Join Meeting Session
                  </a>
                ) : (
                  <div className="py-3 px-4 bg-white border border-slate-100 text-slate-400 rounded-2xl text-xs font-semibold text-center">
                    Meeting link will be provided prior to session
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default UpcomingInterviews;
