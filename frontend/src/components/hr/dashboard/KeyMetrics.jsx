import React from 'react';
import { 
  FileText, Briefcase, Zap, Users, CheckCircle2, 
  Clock, XCircle, Award, TrendingUp, Sparkles, ChevronRight, ArrowUpRight
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const StatCard = ({ icon: Icon, label, value, subtext, badge, badgeColor, iconBg, iconColor, onClick }) => (
  <div 
    onClick={onClick}
    className={`relative flex flex-col justify-between p-5 sm:p-6 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl hover:border-pink-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group ${
      onClick ? 'cursor-pointer' : ''
    }`}
  >
    {/* Subtle top ambient glow */}
    <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-pink-50/60 to-transparent rounded-tr-3xl pointer-events-none group-hover:scale-110 transition-transform duration-500" />

    <div className="flex justify-between items-start mb-4 relative z-10">
      <div className={`w-12 h-12 rounded-2xl ${iconBg} flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner shrink-0`}>
        <Icon className={`h-6 w-6 ${iconColor}`} />
      </div>

      {badge && (
        <span className={`text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full border ${badgeColor}`}>
          {badge}
        </span>
      )}
    </div>

    <div className="relative z-10">
      <h4 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 mb-0.5">
        {value}
      </h4>
      <p className="text-[11px] sm:text-xs text-slate-500 font-bold tracking-wider uppercase">
        {label}
      </p>

      {subtext && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 text-[11px] font-semibold text-slate-600">
          <span>{subtext}</span>
          {onClick && (
            <ArrowUpRight size={13} className="text-slate-400 group-hover:text-[#D60041] transition-colors" />
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
    <div className="relative flex flex-col justify-between p-5 sm:p-6 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl hover:border-pink-200 hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group sm:col-span-2 xl:col-span-2">
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-pink-50 text-[#D60041] flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
            <Zap className="h-6 w-6" />
          </div>
          <div>
            <h4 className="text-sm font-black text-slate-900 tracking-tight">Application Pipeline</h4>
            <p className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider">{validTotal} candidates tracked</p>
          </div>
        </div>

        <span className="text-[10px] font-black tracking-widest text-[#D60041] uppercase bg-pink-50 border border-pink-100 px-3 py-1 rounded-full">
          Live Flow
        </span>
      </div>

      {/* Proportional Multi-Segment Progress Bar */}
      <div className="mb-4">
        <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
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

      {/* Breakdown Pills with interactive filter */}
      <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-100">
        <button
          onClick={() => onFilterClick && onFilterClick('PENDING')}
          className="text-left p-1.5 rounded-xl hover:bg-amber-50/60 transition-colors group/btn"
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">Pending</span>
          </div>
          <span className="text-base sm:text-lg font-black text-slate-900 group-hover/btn:text-amber-600">
            {pending}
          </span>
          <span className="text-[10px] font-bold text-slate-400 ml-1">({pendingPct}%)</span>
        </button>

        <button
          onClick={() => onFilterClick && onFilterClick('REVIEWED')}
          className="text-left p-1.5 rounded-xl hover:bg-blue-50/60 transition-colors group/btn"
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="w-2 h-2 rounded-full bg-blue-500"></span>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">Screened</span>
          </div>
          <span className="text-base sm:text-lg font-black text-slate-900 group-hover/btn:text-blue-600">
            {reviewed}
          </span>
          <span className="text-[10px] font-bold text-slate-400 ml-1">({reviewedPct}%)</span>
        </button>

        <button
          onClick={() => onFilterClick && onFilterClick('ACCEPTED')}
          className="text-left p-1.5 rounded-xl hover:bg-emerald-50/60 transition-colors group/btn"
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">Accepted</span>
          </div>
          <span className="text-base sm:text-lg font-black text-slate-900 group-hover/btn:text-emerald-600">
            {accepted}
          </span>
          <span className="text-[10px] font-bold text-slate-400 ml-1">({acceptedPct}%)</span>
        </button>

        <button
          onClick={() => onFilterClick && onFilterClick('REJECTED')}
          className="text-left p-1.5 rounded-xl hover:bg-slate-100 transition-colors group/btn"
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="w-2 h-2 rounded-full bg-slate-400"></span>
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tight">Archived</span>
          </div>
          <span className="text-base sm:text-lg font-black text-slate-900 group-hover/btn:text-slate-600">
            {rejected}
          </span>
          <span className="text-[10px] font-bold text-slate-400 ml-1">({rejectedPct}%)</span>
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
      <div className="flex justify-between items-center mb-4 sm:mb-5">
        <div>
          <h3 className="text-lg md:text-xl font-extrabold tracking-tight text-slate-900 flex items-center gap-2">
            Key Recruitment Metrics
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-black bg-rose-50 text-[#D60041] border border-rose-100">
              Live
            </span>
          </h3>
          <p className="text-xs text-slate-500 font-medium mt-0.5">
            Real-time pipeline analytics, applicant throughput, and ATS scoring performance
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4 sm:gap-5">
        {/* 1. Total Candidates & Resumes */}
        <StatCard
          icon={FileText}
          label="Total Applications"
          value={totalApps || totalCandidates || totalResumes}
          subtext={`${totalResumes} resumes parsed in ATS`}
          badge="Database"
          badgeColor="bg-slate-50 text-slate-600 border-slate-200"
          iconBg="bg-rose-50"
          iconColor="text-[#D60041]"
          onClick={() => navigate('/hr/screeningportal')}
        />

        {/* 2. Application Flow / Multi-Segment Progress (Takes 2 cols) */}
        <ApplicationFlowCard
          appStats={appStats}
          totalApps={totalApps}
          onFilterClick={handleFilterNavigation}
        />

        {/* 3. Active Positions */}
        <StatCard
          icon={Briefcase}
          label="Active Positions"
          value={activeJobsCount}
          subtext="Open hiring requisitions"
          badge="Hiring"
          badgeColor="bg-blue-50 text-blue-700 border-blue-200"
          iconBg="bg-blue-50"
          iconColor="text-blue-600"
          onClick={() => navigate('/admin/jobmanagement')}
        />

        {/* 4. High Match / Talent Quality Index */}
        <StatCard
          icon={Sparkles}
          label="Top Talent (≥80%)"
          value={highMatchCount}
          subtext={avgMatch > 0 ? `Avg match score: ${avgMatch}%` : 'High match score applicants'}
          badge="High Match"
          badgeColor="bg-emerald-50 text-emerald-700 border-emerald-200"
          iconBg="bg-emerald-50"
          iconColor="text-emerald-600"
          onClick={() => navigate('/hr/screeningportal')}
        />
      </div>
    </div>
  );
};

export default KeyMetrics;