import React from 'react';
import { 
  FileText, Briefcase, Zap, Users, CheckCircle2, 
  Clock, XCircle, Award, TrendingUp, Sparkles, ChevronRight, ArrowUpRight
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const StatCard = ({ icon: Icon, label, value, subtext, badge, badgeColor, iconBg, iconColor, onClick, className = '' }) => (
  <div 
    onClick={onClick}
    className={`relative flex flex-col justify-between p-3.5 sm:p-5 lg:p-6 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl hover:border-pink-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group ${
      onClick ? 'cursor-pointer' : ''
    } ${className}`}
  >
    {/* Subtle top ambient glow */}
    <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-pink-50/60 to-transparent rounded-tr-3xl pointer-events-none group-hover:scale-110 transition-transform duration-500" />

    <div className="flex justify-between items-start mb-2 sm:mb-4 relative z-10">
      <div className={`w-9 h-9 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl ${iconBg} flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner shrink-0`}>
        <Icon className={`h-4.5 w-4.5 sm:h-6 sm:w-6 ${iconColor}`} />
      </div>

      {badge && (
        <span className={`text-[8.5px] sm:text-[10px] font-black uppercase tracking-wider px-1.5 sm:px-2.5 py-0.5 sm:py-1 rounded-full border ${badgeColor}`}>
          {badge}
        </span>
      )}
    </div>

    <div className="relative z-10 min-w-0">
      <h4 className="text-xl sm:text-2xl lg:text-3xl font-black tracking-tight text-slate-900 mb-0.5 truncate">
        {value}
      </h4>
      <p className="text-[10px] sm:text-xs text-slate-500 font-bold tracking-wider uppercase truncate">
        {label}
      </p>

      {subtext && (
        <div className="flex items-center justify-between mt-2 sm:mt-3 pt-2 sm:pt-3 border-t border-slate-100 text-[9.5px] sm:text-[11px] font-semibold text-slate-500">
          <span className="truncate pr-1">{subtext}</span>
          {onClick && (
            <ArrowUpRight size={13} className="text-slate-400 group-hover:text-[#D60041] transition-colors shrink-0" />
          )}
        </div>
      )}
    </div>
  </div>
);

const ApplicationFlowCard = ({ appStats, totalApps, onFilterClick }) => {
  const pending = appStats?.pending || 0;
  const reviewed = appStats?.reviewed || 0;
  const accepted = appStats?.accepted || 0;
  const rejected = appStats?.rejected || 0;

  const validTotal = totalApps > 0 ? totalApps : (pending + reviewed + accepted + rejected) || 1;
  const pendingPct = Math.round((pending / validTotal) * 100);
  const reviewedPct = Math.round((reviewed / validTotal) * 100);
  const acceptedPct = Math.round((accepted / validTotal) * 100);
  const rejectedPct = Math.max(0, 100 - pendingPct - reviewedPct - acceptedPct);

  return (
    <div className="relative flex flex-col justify-between p-3.5 sm:p-5 lg:p-6 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl hover:border-pink-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group col-span-2 sm:col-span-2 lg:col-span-3 xl:col-span-2">
      <div className="flex justify-between items-center mb-2.5 sm:mb-4">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="w-9 h-9 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-pink-50 text-[#D60041] flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner shrink-0">
            <Zap className="h-4.5 w-4.5 sm:h-6 sm:w-6" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs sm:text-sm font-black text-slate-900 tracking-tight truncate">Application Pipeline</h4>
            <p className="text-[9.5px] sm:text-[11px] text-slate-400 font-semibold uppercase tracking-wider truncate">{validTotal} candidates</p>
          </div>
        </div>

        <span className="text-[8.5px] sm:text-[10px] font-black tracking-wider text-[#D60041] uppercase bg-pink-50 border border-pink-100 px-2 sm:px-2.5 py-0.5 sm:py-1 rounded-full shrink-0">
          Live Flow
        </span>
      </div>

      {/* Proportional Multi-Segment Progress Bar */}
      <div className="mb-2.5 sm:mb-3.5">
        <div className="h-2 sm:h-2.5 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
          <div 
            style={{ width: `${pendingPct}%` }} 
            className="bg-amber-400 h-full transition-all duration-700 hover:brightness-110" 
            title={`Pending: ${pending} (${pendingPct}%)`}
          />
          <div 
            style={{ width: `${reviewedPct}%` }} 
            className="bg-blue-500 h-full transition-all duration-700 hover:brightness-110" 
            title={`Reviewed: ${reviewed} (${reviewedPct}%)`}
          />
          <div 
            style={{ width: `${acceptedPct}%` }} 
            className="bg-emerald-500 h-full transition-all duration-700 hover:brightness-110" 
            title={`Accepted: ${accepted} (${acceptedPct}%)`}
          />
          <div 
            style={{ width: `${rejectedPct}%` }} 
            className="bg-slate-300 h-full transition-all duration-700 hover:brightness-110" 
            title={`Rejected: ${rejected} (${rejectedPct}%)`}
          />
        </div>
      </div>

      {/* Breakdown Pills with interactive filter (2x2 on mobile, 4x1 on tablet/desktop) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 sm:gap-2 pt-2 sm:pt-2.5 border-t border-slate-100">
        <button
          onClick={() => onFilterClick && onFilterClick('PENDING')}
          className="text-left p-1.5 sm:p-1.5 rounded-xl bg-amber-50/40 sm:bg-transparent hover:bg-amber-50/70 border border-amber-100/60 sm:border-transparent transition-colors group/btn min-w-0"
        >
          <div className="flex items-center gap-1 sm:gap-1.5 mb-0.5 min-w-0">
            <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-amber-400 shrink-0"></span>
            <span className="text-[9.5px] sm:text-[10px] font-bold text-slate-500 uppercase tracking-tight truncate">Pending</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-sm sm:text-base lg:text-lg font-black text-slate-900 group-hover/btn:text-amber-600">
              {pending}
            </span>
            <span className="text-[9px] sm:text-[10px] font-bold text-slate-400">({pendingPct}%)</span>
          </div>
        </button>

        <button
          onClick={() => onFilterClick && onFilterClick('REVIEWED')}
          className="text-left p-1.5 sm:p-1.5 rounded-xl bg-blue-50/40 sm:bg-transparent hover:bg-blue-50/70 border border-blue-100/60 sm:border-transparent transition-colors group/btn min-w-0"
        >
          <div className="flex items-center gap-1 sm:gap-1.5 mb-0.5 min-w-0">
            <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-blue-500 shrink-0"></span>
            <span className="text-[9.5px] sm:text-[10px] font-bold text-slate-500 uppercase tracking-tight truncate">Screened</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-sm sm:text-base lg:text-lg font-black text-slate-900 group-hover/btn:text-blue-600">
              {reviewed}
            </span>
            <span className="text-[9px] sm:text-[10px] font-bold text-slate-400">({reviewedPct}%)</span>
          </div>
        </button>

        <button
          onClick={() => onFilterClick && onFilterClick('ACCEPTED')}
          className="text-left p-1.5 sm:p-1.5 rounded-xl bg-emerald-50/40 sm:bg-transparent hover:bg-emerald-50/70 border border-emerald-100/60 sm:border-transparent transition-colors group/btn min-w-0"
        >
          <div className="flex items-center gap-1 sm:gap-1.5 mb-0.5 min-w-0">
            <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-emerald-500 shrink-0"></span>
            <span className="text-[9.5px] sm:text-[10px] font-bold text-slate-500 uppercase tracking-tight truncate">Accepted</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-sm sm:text-base lg:text-lg font-black text-slate-900 group-hover/btn:text-emerald-600">
              {accepted}
            </span>
            <span className="text-[9px] sm:text-[10px] font-bold text-slate-400">({acceptedPct}%)</span>
          </div>
        </button>

        <button
          onClick={() => onFilterClick && onFilterClick('REJECTED')}
          className="text-left p-1.5 sm:p-1.5 rounded-xl bg-slate-50 sm:bg-transparent hover:bg-slate-100 border border-slate-200/60 sm:border-transparent transition-colors group/btn min-w-0"
        >
          <div className="flex items-center gap-1 sm:gap-1.5 mb-0.5 min-w-0">
            <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-slate-400 shrink-0"></span>
            <span className="text-[9.5px] sm:text-[10px] font-bold text-slate-500 uppercase tracking-tight truncate">Archived</span>
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-sm sm:text-base lg:text-lg font-black text-slate-900 group-hover/btn:text-slate-600">
              {rejected}
            </span>
            <span className="text-[9px] sm:text-[10px] font-bold text-slate-400">({rejectedPct}%)</span>
          </div>
        </button>
      </div>
    </div>
  );
};

const KeyMetrics = ({ 
  activeJobsCount = 0, 
  totalCandidates = 0, 
  totalResumes = 0, 
  appStats = {}, 
  applications = [] 
}) => {
  const navigate = useNavigate();

  const totalApps = applications.length || (
    (appStats.pending || 0) + 
    (appStats.reviewed || 0) + 
    (appStats.accepted || 0) + 
    (appStats.rejected || 0)
  );

  const highMatchCount = applications.filter(a => (a.matchScore || 0) >= 80).length;
  const avgMatch = applications.length > 0 
    ? Math.round(applications.reduce((acc, a) => acc + (a.matchScore || 0), 0) / applications.length)
    : 0;

  const handleFilterNavigation = (status) => {
    navigate(`/hr/screeningportal?status=${status}`);
  };

  return (
    <div className="mb-6 sm:mb-8">
      <div className="flex justify-between items-center mb-3 sm:mb-5">
        <div>
          <h3 className="text-base sm:text-xl font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
            <span>Key Recruitment Metrics</span>
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[9px] sm:text-[10px] font-black bg-rose-50 text-[#D60041] border border-rose-100">
              Live
            </span>
          </h3>
          <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-0.5">
            Real-time pipeline analytics, applicant throughput, and ATS scoring performance
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-2.5 sm:gap-4 lg:gap-5">
        {/* 1. Total Candidates & Resumes (Col 1 on mobile) */}
        <StatCard
          icon={FileText}
          label="Total Applications"
          value={totalApps || totalCandidates || totalResumes}
          subtext={`${totalResumes} resumes in ATS`}
          badge="Live"
          badgeColor="bg-slate-50 text-slate-600 border-slate-200"
          iconBg="bg-rose-50"
          iconColor="text-[#D60041]"
          onClick={() => navigate('/hr/screeningportal')}
        />

        {/* 2. Active Positions (Col 2 on mobile) */}
        <StatCard
          icon={Briefcase}
          label="Active Positions"
          value={activeJobsCount}
          subtext="Open requisitions"
          badge="Hiring"
          badgeColor="bg-blue-50 text-blue-700 border-blue-200"
          iconBg="bg-blue-50"
          iconColor="text-blue-600"
          onClick={() => navigate('/admin/jobmanagement')}
        />

        {/* 3. Application Flow / Multi-Segment Progress (Spans 2 cols on mobile) */}
        <ApplicationFlowCard
          appStats={appStats}
          totalApps={totalApps}
          onFilterClick={handleFilterNavigation}
        />

        {/* 4. High Match / Talent Quality Index (Spans 2 cols on mobile, 1 col on desktop) */}
        <StatCard
          icon={Sparkles}
          label="Top Talent (≥80%)"
          value={highMatchCount}
          subtext={avgMatch > 0 ? `Avg match: ${avgMatch}%` : 'High match score applicants'}
          badge="High Match"
          badgeColor="bg-emerald-50 text-emerald-700 border-emerald-200"
          iconBg="bg-emerald-50"
          iconColor="text-emerald-600"
          onClick={() => navigate('/hr/screeningportal')}
          className="col-span-2 sm:col-span-1 lg:col-span-1 xl:col-span-1"
        />
      </div>
    </div>
  );
};

export default KeyMetrics;