import React from 'react';
import { Calendar, Clock, Video } from 'lucide-react';
import { useSelector } from 'react-redux';
import { useGetCandidateInterviewsQuery } from '../../../redux/api/apiSlice';

const UpcomingInterviews = () => {
  const { user: email } = useSelector((state) => state.auth);
  const { data: interviews = [] } = useGetCandidateInterviewsQuery(email, {
    skip: !email,
    pollingInterval: 10000,
  });

  const activeInterviews = interviews.filter(i => i.status !== 'CANCELED' && i.status !== 'COMPLETED');
  const nextInterview = activeInterviews.length > 0 ? activeInterviews[activeInterviews.length - 1] : null;

  return (
    <div className="bg-white border border-slate-100 rounded-[40px] p-10 shadow-xl shadow-slate-200/40">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-pink-50 rounded-2xl flex items-center justify-center text-[#D10043] border border-pink-100">
          <Calendar size={22} />
        </div>
        <h3 className="text-xl font-black text-slate-900 tracking-tight">Interviews</h3>
      </div>

      {!nextInterview ? (
        <div className="bg-slate-50/50 rounded-[32px] p-8 border border-slate-100 text-center">
          <p className="text-sm text-slate-500 font-medium">No upcoming interviews scheduled.</p>
        </div>
      ) : (
        <div className="bg-slate-50/50 rounded-[32px] p-6 border border-slate-100 relative group overflow-hidden">
          <div className="absolute top-0 right-0 w-2 h-full bg-[#D10043] opacity-0 group-hover:opacity-100 transition-opacity" />

          <div className="flex items-center justify-between mb-4">
            <span className="bg-orange-100 text-orange-600 text-[8px] font-black px-2 py-0.5 rounded-md uppercase tracking-widest">Upcoming</span>
            <span className="bg-blue-100 text-blue-600 text-[8px] font-black px-2 py-0.5 rounded-md uppercase tracking-widest">Google Meet</span>
          </div>

          <h4 className="font-black text-lg text-slate-900 mb-1 leading-none tracking-tight">{nextInterview.title}</h4>
          <p className="text-xs text-slate-400 font-bold uppercase tracking-widest mb-6">HR Department</p>

          <div className="flex items-center text-xs text-slate-700 font-black uppercase tracking-widest mb-6 bg-white w-fit px-4 py-2.5 rounded-xl border border-slate-100 shadow-sm">
            <Clock className="w-4 h-4 mr-3 text-[#D10043]" />
            {new Date(nextInterview.start_time).toLocaleString()}
          </div>

          {nextInterview.meeting_link ? (
            <a href={nextInterview.meeting_link} target="_blank" rel="noopener noreferrer" className="w-full py-4 bg-[#D10043] hover:bg-slate-900 text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all shadow-lg active:scale-[0.95] flex items-center justify-center gap-2 group/btn block text-center">
              <Video size={14} className="group-hover/btn:animate-pulse" /> Join Meeting
            </a>
          ) : (
            <button className="w-full py-4 bg-slate-900 hover:bg-[#D10043] text-white rounded-2xl text-[10px] font-black uppercase tracking-[0.2em] transition-all shadow-lg active:scale-[0.95]">
              Prepare for Session
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default UpcomingInterviews;
