import React, { useState } from 'react';
import {
  Calendar,
  Clock,
  Mail,
  User,
  Video,
  CheckCircle2,
  Copy,
  Check,
  ExternalLink,
  MessageSquare
} from 'lucide-react';
import { useSelector } from 'react-redux';
import { useNavigate } from '@/utils/navigation';
import { useGetCandidateInterviewsQuery } from '../../../redux/api/apiSlice';
import { RootState } from '../../../redux/store';

const UpcomingInterviews: React.FC = () => {
  const navigate = useNavigate();
  const { user: email } = useSelector((state: RootState) => state.auth);
  const [copiedId, setCopiedId] = useState<string | number | null>(null);

  const { data: interviews = [], isLoading } = useGetCandidateInterviewsQuery(email || '', {
    skip: !email,
    pollingInterval: 10000,
  });

  const activeInterviews = (interviews || [])
    .filter((i: any) => i.status !== 'CANCELED' && i.status !== 'COMPLETED')
    .sort((a: any, b: any) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());

  const handleCopyDetails = (iv: any) => {
    const text = `Interview: ${iv.title}\nRole: ${iv.job_title || 'Mariwasa Position'}\nDate: ${new Date(iv.start_time).toLocaleString()}\nInterviewer: ${iv.interviewer_name || 'HR Panel'}`;
    navigator.clipboard.writeText(text);
    setCopiedId(iv.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-7 shadow-xs space-y-5">
      
      {/* HEADER */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-50 text-purple-700 rounded-xl flex items-center justify-center shrink-0 border border-purple-100/80">
            <Calendar size={18} />
          </div>
          <div>
            <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
              Interview Schedule
            </h3>
            <p className="text-xs text-slate-400 font-medium">Upcoming evaluation sessions</p>
          </div>
        </div>

        {activeInterviews.length > 0 && (
          <span className="text-[10px] font-black text-purple-700 bg-purple-50 border border-purple-200/60 px-2.5 py-0.5 rounded-full uppercase tracking-wider">
            {activeInterviews.length} Scheduled
          </span>
        )}
      </div>

      {/* SKELETON / EMPTY / SESSIONS */}
      {isLoading ? (
        <div className="bg-slate-50/60 rounded-2xl p-5 border border-slate-100 text-center animate-pulse space-y-2">
          <div className="h-4 bg-slate-200 rounded w-1/3 mx-auto" />
          <div className="h-8 bg-slate-100 rounded w-1/2 mx-auto" />
        </div>
      ) : activeInterviews.length === 0 ? (
        <div className="bg-slate-50/50 rounded-2xl p-5 border border-slate-200/60 text-center space-y-3">
          <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center mx-auto text-slate-300 shadow-2xs border border-slate-100">
            <Calendar size={20} />
          </div>
          <div>
            <h4 className="text-xs sm:text-sm font-black text-slate-800">No Pending Interviews</h4>
            <p className="text-xs text-slate-400 leading-relaxed max-w-xs mx-auto mt-0.5">
              Once your application advances past screening, recruitment evaluation coordinates will appear here.
            </p>
          </div>

          {/* Quick Interview Readiness Checklist */}
          <div className="pt-2 border-t border-slate-200/60 text-left space-y-1.5 text-[11px] text-slate-500">
            <span className="font-bold text-slate-700 block text-[10px] uppercase tracking-wider">
              Recruitment Quick Tips
            </span>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 size={12} className="text-emerald-500 shrink-0" />
              <span>Keep your resume and contact info up to date</span>
            </div>
            <div className="flex items-center gap-1.5">
              <CheckCircle2 size={12} className="text-emerald-500 shrink-0" />
              <span>Check registered email for calendar invites</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3.5">
          {activeInterviews.map((iv: any) => {
            const startDate = new Date(iv.start_time);
            const endDate = new Date(iv.end_time);
            const isCopied = copiedId === iv.id;

            return (
              <div
                key={iv.id}
                className="bg-slate-50/60 hover:bg-white rounded-2xl p-4 sm:p-5 border border-slate-200/70 hover:border-purple-200 hover:shadow-md transition-all duration-200 space-y-3.5 group"
              >
                {/* Status Badges */}
                <div className="flex items-center justify-between gap-2">
                  <span className="bg-purple-100/90 text-purple-900 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                    {iv.status || 'Scheduled'}
                  </span>
                  <span className="bg-emerald-50 text-emerald-700 border border-emerald-200/60 text-[9px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1">
                    <Mail size={10} /> Email Confirmed
                  </span>
                </div>

                {/* Title & Role */}
                <div>
                  <h4 className="font-black text-sm sm:text-base text-slate-900 group-hover:text-purple-700 transition-colors leading-snug">
                    {iv.title}
                  </h4>
                  {iv.job_title && (
                    <p className="text-xs text-slate-500 font-semibold mt-0.5">
                      Target Role: <strong className="text-slate-800">{iv.job_title}</strong>
                    </p>
                  )}
                  {iv.interviewer_name && (
                    <p className="text-xs text-slate-600 font-medium flex items-center gap-1 mt-1">
                      <User size={12} className="text-purple-600" />
                      <span>Panelist: <strong className="text-slate-800">{iv.interviewer_name}</strong></span>
                    </p>
                  )}
                </div>

                {/* Date & Time Pill */}
                <div className="bg-white p-3 rounded-xl border border-slate-200/80 flex items-center justify-between gap-2 text-xs font-bold text-slate-800 shadow-2xs">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Clock size={15} className="text-purple-600 shrink-0" />
                    <div className="min-w-0">
                      <div className="truncate">
                        {startDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                      </div>
                      <div className="text-[11px] text-slate-400 font-semibold truncate">
                        {startDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })} – {endDate.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}
                      </div>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleCopyDetails(iv)}
                    title="Copy interview schedule details"
                    className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors shrink-0 cursor-pointer"
                  >
                    {isCopied ? <Check size={14} className="text-emerald-600" /> : <Copy size={14} />}
                  </button>
                </div>

                {/* Coordinates Notice */}
                <div className="p-2.5 bg-purple-50/50 border border-purple-100 rounded-xl text-[11px] text-purple-900 flex items-center gap-2 font-medium">
                  <Video size={13} className="text-purple-600 shrink-0" />
                  <span className="truncate">Video meet coordinates sent to registered email</span>
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
          className="text-[#D10043] hover:underline font-bold cursor-pointer"
        >
          Message HR Coordinator
        </button>
      </div>

    </div>
  );
};

export default UpcomingInterviews;
