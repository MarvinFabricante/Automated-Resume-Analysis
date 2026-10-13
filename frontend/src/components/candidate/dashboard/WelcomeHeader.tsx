import React from 'react';
import { useNavigate } from '@/utils/navigation';
import { Sparkles, Calendar, Search, ArrowRight, FileText, CheckCircle2 } from 'lucide-react';

interface WelcomeHeaderProps {
  applicationCount?: number;
  interviewCount?: number;
}

const WelcomeHeader: React.FC<WelcomeHeaderProps> = ({ applicationCount = 0, interviewCount = 0 }) => {
  const navigate = useNavigate();
  const fullname = typeof localStorage !== 'undefined' ? (localStorage.getItem('fullname') || 'Candidate') : 'Candidate';

  // Dynamic greeting based on current hour
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  // Formatted date
  const todayFormatted = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  }).format(new Date());

  // Extract initial for avatar
  const initials = fullname
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((w: string) => w[0].toUpperCase())
    .join('') || 'C';

  return (
    <div className="relative overflow-hidden bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-7 md:p-8 shadow-xs mb-6 sm:mb-8">
      {/* Subtle ambient gradient accents */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-gradient-to-bl from-[#D10043]/5 via-rose-50/40 to-transparent rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-8 left-1/4 w-60 h-24 bg-slate-100/50 rounded-full blur-2xl pointer-events-none" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        
        {/* Left Column: Greeting, Avatar & Summary */}
        <div className="flex items-start sm:items-center gap-4 min-w-0">
          {/* Avatar icon */}
          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-2xl bg-gradient-to-tr from-[#D10043] to-rose-500 text-white font-black text-base sm:text-lg flex items-center justify-center shrink-0 shadow-md shadow-[#D10043]/20">
            {initials}
          </div>

          <div className="space-y-1.5 min-w-0">
            {/* Top metadata badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-[#D10043]/10 text-[#D10043] border border-[#D10043]/15">
                <Sparkles size={11} className="animate-pulse" />
                Candidate Portal
              </span>

              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-slate-500 bg-slate-50 border border-slate-200/60">
                <Calendar size={12} className="text-slate-400" />
                {todayFormatted}
              </span>
            </div>

            {/* Greeting Headline */}
            <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight truncate">
              {getGreeting()},{' '}
              <span className="text-[#D10043]">{fullname}</span>
            </h1>

            {/* Subtitle */}
            <p className="text-slate-500 text-xs sm:text-sm font-medium leading-relaxed max-w-xl">
              Track recruitment evaluations, review interview updates, and explore opportunities at Mariwasa Siam Ceramics.
            </p>

            {/* Status Pills */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-700 bg-slate-100/90 px-3 py-1 rounded-xl">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                <strong className="text-slate-900 font-black">{applicationCount}</strong>{' '}
                {applicationCount === 1 ? 'Application' : 'Applications'} in Pipeline
              </span>

              {interviewCount > 0 ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#D10043] bg-pink-50 border border-pink-200/60 px-3 py-1 rounded-xl">
                  <span className="w-2 h-2 rounded-full bg-[#D10043] animate-ping" />
                  <strong className="font-black">{interviewCount}</strong> Interview Scheduled
                </span>
              ) : (
                <span className="text-xs font-semibold text-slate-400 hidden sm:inline-block">
                  • Profile active in ATS matching
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Touch-friendly Quick Actions */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 shrink-0 pt-2 lg:pt-0 border-t sm:border-t-0 border-slate-100">
          <button
            type="button"
            onClick={() => navigate('/candidate/findjobs')}
            className="px-5 py-3 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm shadow-[#D10043]/20 active:scale-[0.98] cursor-pointer"
          >
            <Search size={14} />
            <span>Browse Open Roles</span>
            <ArrowRight size={14} />
          </button>

          <button
            type="button"
            onClick={() => navigate('/candidate/applicationtracking')}
            className="px-4 py-3 rounded-xl bg-slate-50 hover:bg-slate-100 border border-slate-200 text-slate-700 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer"
          >
            <FileText size={14} className="text-slate-400" />
            <span>Track Pipeline</span>
          </button>
        </div>

      </div>
    </div>
  );
};

export default WelcomeHeader;
