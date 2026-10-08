import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Calendar, Search, ArrowRight, FileText } from 'lucide-react';

const WelcomeHeader = ({ applicationCount = 0, interviewCount = 0 }) => {
  const navigate = useNavigate();
  const fullname = localStorage.getItem('fullname') || 'Candidate';

  // Dynamic greeting based on current hour
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Formatted date
  const todayFormatted = new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }).format(new Date());

  return (
    <div className="relative overflow-hidden bg-white border border-slate-200/80 rounded-[32px] p-6 sm:p-8 md:p-10 shadow-sm mb-8 sm:mb-10">
      {/* Ambient background accents */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-[#D10043]/5 via-rose-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/3 w-64 h-32 bg-slate-50/80 rounded-full blur-2xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6 sm:gap-8">
        
        {/* Left Column: Greeting & Summary */}
        <div className="space-y-3 max-w-2xl">
          
          {/* Top badges */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] bg-[#D10043]/10 text-[#D10043] border border-[#D10043]/15">
              <Sparkles size={12} className="animate-pulse" />
              Candidate Hub
            </span>

            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-slate-500 bg-slate-50 border border-slate-200/60">
              <Calendar size={13} className="text-slate-400" />
              {todayFormatted}
            </span>
          </div>

          {/* Heading */}
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-tight">
            {getGreeting()},{' '}
            <span className="text-[#D10043]">{fullname}</span>
          </h1>

          {/* Subtitle */}
          <p className="text-slate-500 text-xs sm:text-sm md:text-base font-medium leading-relaxed">
            Monitor your recruitment progress, track interview evaluations, and discover open career opportunities with Mariwasa Siam Ceramics.
          </p>

          {/* Inline Quick Stats Badges */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs font-bold text-slate-600 bg-slate-100/80 px-3 py-1 rounded-xl">
              <strong className="text-slate-900 font-black">{applicationCount}</strong>{' '}
              {applicationCount === 1 ? 'Application' : 'Applications'} Submitted
            </span>
            {interviewCount > 0 && (
              <span className="text-xs font-bold text-[#D10043] bg-pink-50 border border-pink-200/60 px-3 py-1 rounded-xl">
                <strong className="font-black">{interviewCount}</strong> Interview Scheduled
              </span>
            )}
          </div>

        </div>

        {/* Right Column: Primary Fast CTAs */}
        <div className="flex flex-wrap sm:flex-nowrap items-center gap-3 shrink-0">
          <button
            type="button"
            onClick={() => navigate('/candidate/findjobs')}
            className="w-full sm:w-auto px-6 py-3.5 rounded-2xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md shadow-[#D10043]/20 active:scale-[0.98]"
          >
            <Search size={15} />
            Explore Open Roles
            <ArrowRight size={15} />
          </button>

          <button
            type="button"
            onClick={() => navigate('/candidate/applicationtracking')}
            className="w-full sm:w-auto px-5 py-3.5 rounded-2xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-[0.98]"
          >
            <FileText size={15} className="text-slate-400" />
            Track Status
          </button>
        </div>

      </div>
    </div>
  );
};

export default WelcomeHeader;
