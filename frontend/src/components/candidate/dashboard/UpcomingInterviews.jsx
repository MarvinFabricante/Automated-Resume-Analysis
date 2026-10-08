import React from 'react';
import { Calendar, Clock, Mail, User, Video, CheckCircle2, ChevronRight, ShieldCheck } from 'lucide-react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { useGetCandidateInterviewsQuery } from '../../../redux/api/apiSlice';

const UpcomingInterviews = () => {
  const navigate = useNavigate();
  const { user: email } = useSelector((state) => state.auth);
  const { data: interviews = [], isLoading } = useGetCandidateInterviewsQuery(email, {
    skip: !email,
    pollingInterval: 10000,
  });

  const activeInterviews = interviews
    .filter((i) => i.status !== 'CANCELED' && i.status !== 'COMPLETED')
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

  return (
    <div className="bg-white border border-slate-200/80 rounded-[32px] p-6 sm:p-8 shadow-sm space-y-6">
      
      {/* HEADER */}
      <div className="flex items-center justify-between pb-5 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[#D10043]/10 text-[#D10043] rounded-xl flex items-center justify-center shrink-0">
            <Calendar size={20} />
          </div>
          <div>
            <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">Interview Schedule</h3>
            <p className="text-xs text-slate-400 font-medium">Upcoming evaluation sessions</p>
          </div>
        </div>

        {activeInterviews.length > 0 && (
          <span className="text-[10px] font-black text-[#D10043] bg-pink-50 border border-pink-200/60 px-3 py-1 rounded-full uppercase tracking-wider">
            {activeInterviews.length} Scheduled
          </span>
        )}
      </div>

      {/* SKELETON / EMPTY / SESSIONS */}
      {isLoading ? (
        <div className="bg-slate-50/60 rounded-2xl p-6 border border-slate-100 text-center animate-pulse space-y-3">
          <div className="h-4 bg-slate-200 rounded w-1/3 mx-auto" />
          <div className="h-8 bg-slate-100 rounded w-1/2 mx-auto" />
        </div>
      ) : activeInterviews.length === 0 ? (
        <div className="bg-slate-50/60 rounded-3xl p-7 border border-slate-100 text-center space-y-3">
          <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center mx-auto text-slate-300 shadow-xs border border-slate-100">
            <Calendar size={22} />
          </div>
          <h4 className="text-sm font-bold text-slate-800">No Pending Interviews</h4>
          <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto">
            Our HR panel reviews applications actively. Once your application advances to the interview stage, schedule details will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {activeInterviews.map((iv) => {
            const startDate = new Date(iv.start_time);
            const endDate = new Date(iv.end_time);

            return (
              <div
                key={iv.id}
                className="bg-slate-50/70 hover:bg-white rounded-2xl p-5 border border-slate-200/70 hover:border-[#D10043]/30 hover:shadow-md transition-all duration-200 space-y-4 group"
              >
                {/* Status Badges */}
                <div className="flex items-center justify-between gap-2">
                  <span className="bg-amber-100/80 text-amber-800 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                    {iv.status || 'Scheduled'}
                  </span>
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200/60 text-[9px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1">
                    <Mail size={10} /> Confirmed via Email
                  </span>
                </div>

                {/* Title & Role */}
                <div>
                  <h4 className="font-black text-base text-slate-900 group-hover:text-[#D10043] transition-colors leading-tight">
                    {iv.title}
                  </h4>
                  {iv.job_title && (
                    <p className="text-xs text-slate-500 font-semibold mt-0.5">
                      Target Role: <strong className="text-slate-800">{iv.job_title}</strong>
                    </p>
                  )}
                  {iv.interviewer_name && (
                    <p className="text-xs text-slate-600 font-medium flex items-center gap-1 mt-1.5">
                      <User size={13} className="text-[#D10043]" />
                      Panelist: <span className="font-bold text-slate-800">{iv.interviewer_name}</span>
                    </p>
                  )}
                </div>

                {/* Date & Time Pill */}
                <div className="bg-white p-3 rounded-xl border border-slate-200/80 flex items-center gap-2.5 text-xs font-bold text-slate-800 shadow-2xs">
                  <Clock size={15} className="text-[#D10043] shrink-0" />
                  <div className="min-w-0">
                    <div>
                      {startDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                    </div>
                    <div className="text-[11px] text-slate-400 font-semibold">
                      {startDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })} – {endDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}
                    </div>
                  </div>
                </div>

                {/* Email Confirmation Notice */}
                <div className="p-3 bg-emerald-50/60 border border-emerald-100 rounded-xl text-[11px] text-emerald-800 flex items-center gap-2 font-medium">
                  <Video size={14} className="text-emerald-600 shrink-0" />
                  <span>Google Meet / Meeting coordinates delivered to your registered email</span>
                </div>

              </div>
            );
          })}
        </div>
      )}

      {/* Helpful Guidance Footer */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400 font-medium">
        <span>Need to reschedule?</span>
        <button
          type="button"
          onClick={() => navigate('/candidate/messages')}
          className="text-[#D10043] hover:underline font-bold"
        >
          Message HR Coordinator
        </button>
      </div>

    </div>
  );
};

export default UpcomingInterviews;
