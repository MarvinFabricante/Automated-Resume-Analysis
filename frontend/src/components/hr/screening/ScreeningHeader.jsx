import React from 'react';
import { 
  Download, Scale, LayoutGrid, List, Users, Clock, 
  Sparkles, CheckCircle2, Archive, RefreshCw, ChevronRight, Check
} from 'lucide-react';

const ScreeningHeader = ({ 
  stats = {
    total: 0,
    pending: 0,
    interview: 0,
    accepted: 0,
    highMatch: 0,
    archived: 0
  },
  activeStatusFilter,
  activeScoreFilter,
  onKpiClick,
  onExport,
  onNavigateCompare,
  selectedCount = 0,
  viewMode = 'cards',
  setViewMode,
  onRefresh,
  isRefreshing = false
}) => {
  const isTotalActive = (activeStatusFilter === 'All Status' || !activeStatusFilter) && (activeScoreFilter === 'All Scores' || !activeScoreFilter);
  const isPendingActive = activeStatusFilter === 'Pending';
  const isInterviewActive = activeStatusFilter === 'Interview' || activeStatusFilter === 'In Interview' || activeStatusFilter === 'Technical Interview' || activeStatusFilter === 'Final Interview';
  const isAcceptedActive = activeStatusFilter === 'Accepted';
  const isArchivedActive = activeStatusFilter === 'Archived';

  return (
    <div className="space-y-5 sm:space-y-6 mb-6 sm:mb-8">
      {/* Top Title & Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 sm:gap-3">
            <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-gray-900 tracking-tight">
              Resume Screening
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-rose-50 text-[#D60041] border border-rose-100/80">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D60041] animate-pulse"></span>
              ATS Portal
            </span>
            {isRefreshing && (
              <span className="inline-flex items-center gap-1 text-[11px] text-[#D60041] font-bold animate-pulse">
                <RefreshCw size={12} className="animate-spin" />
                <span className="hidden sm:inline">Syncing...</span>
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-gray-500 font-medium mt-1 leading-relaxed">
            Review applicant qualifications, AI match scores, schedule interviews, and manage talent pipeline.
          </p>
        </div>

        {/* Action Controls - Mobile Responsive Wrap */}
        <div className="flex items-center gap-2 sm:gap-2.5 self-start sm:self-auto shrink-0 w-full sm:w-auto justify-between sm:justify-end">
          {/* View Mode Switcher */}
          <div className="bg-gray-100/80 p-1 rounded-xl flex items-center border border-gray-200/80 shadow-inner">
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              title="Cards View"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 cursor-pointer ${
                viewMode === 'cards' 
                  ? 'bg-white text-[#D60041] shadow-sm' 
                  : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              <LayoutGrid size={15} />
              <span className="hidden md:inline">Cards</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              title="Table / Compact View"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold transition-all duration-200 cursor-pointer ${
                viewMode === 'table' 
                  ? 'bg-white text-[#D60041] shadow-sm' 
                  : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              <List size={15} />
              <span className="hidden md:inline">Table</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            {/* Compare Candidates button */}
            <button
              type="button"
              onClick={onNavigateCompare}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-2.5 border rounded-xl text-xs font-bold transition-all duration-200 shadow-sm cursor-pointer ${
                selectedCount >= 2 
                  ? 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 shadow-purple-50' 
                  : 'bg-white border-gray-200/90 text-gray-700 hover:border-purple-200 hover:text-purple-600'
              }`}
              title="Compare candidates side-by-side"
            >
              <Scale size={15} className={selectedCount >= 2 ? 'text-purple-600' : 'text-gray-400'} />
              <span className="hidden sm:inline">Compare</span>
              {selectedCount > 0 && (
                <span className="px-1.5 py-0.2 bg-purple-600 text-white rounded-full text-[10px] font-black">
                  {selectedCount}
                </span>
              )}
            </button>

            {/* Export List Button */}
            <button 
              type="button"
              onClick={onExport}
              className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 sm:py-2.5 bg-white border border-gray-200/90 rounded-xl text-xs font-bold text-gray-700 hover:border-pink-200 hover:text-[#D60041] hover:bg-pink-50/50 transition-all duration-200 shadow-sm group cursor-pointer"
              title="Export visible candidates to CSV"
            >
              <Download className="w-4 h-4 text-gray-400 group-hover:text-[#D60041] transition-colors" />
              <span className="hidden sm:inline">Export</span>
            </button>

            {/* Refresh Button */}
            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                title="Refresh candidates"
                className="p-2 sm:p-2.5 bg-white border border-gray-200/90 rounded-xl text-gray-500 hover:text-gray-900 hover:border-gray-300 transition-all shadow-sm cursor-pointer"
              >
                <RefreshCw size={15} className={isRefreshing ? 'animate-spin text-[#D60041]' : ''} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Interactive KPI Summary Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 sm:gap-3.5">
        
        {/* Total Candidates */}
        <button
          type="button"
          onClick={() => onKpiClick('all')}
          aria-label="Filter by all candidate applications"
          aria-pressed={isTotalActive}
          className={`relative text-left w-full p-3.5 sm:p-4 rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden group active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#D60041] ${
            isTotalActive
              ? 'bg-rose-50/90 border-2 border-[#D60041] ring-2 ring-[#D60041]/20 shadow-sm hover:bg-rose-100/80 hover:border-[#D60041]'
              : 'bg-white border border-gray-200/90 shadow-xs hover:border-rose-300 hover:bg-rose-50/40 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-colors ${
              isTotalActive ? 'text-[#D60041] font-black' : 'text-gray-600 group-hover:text-[#D60041]'
            }`}>
              Total
            </span>
            <div className={`p-1.5 rounded-lg transition-colors ${
              isTotalActive 
                ? 'bg-[#D60041] text-white shadow-xs' 
                : 'bg-gray-100 text-gray-600 group-hover:bg-rose-100 group-hover:text-[#D60041]'
            }`}>
              <Users size={14} />
            </div>
          </div>
          <p className={`text-xl sm:text-2xl font-black tracking-tight mt-1 transition-colors ${
            isTotalActive ? 'text-gray-950' : 'text-gray-900 group-hover:text-gray-950'
          }`}>
            {stats.total}
          </p>
          <div className={`flex items-center justify-between mt-2 pt-2 border-t text-[11px] font-semibold transition-colors ${
            isTotalActive 
              ? 'border-rose-200/80 text-rose-900' 
              : 'border-gray-100 group-hover:border-rose-100 text-gray-500 group-hover:text-gray-800'
          }`}>
            <span>Active pool</span>
            {isTotalActive ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-[#D60041] text-white text-[9px] font-black uppercase tracking-wider shadow-2xs">
                <Check size={10} strokeWidth={3} /> Active
              </span>
            ) : (
              <ChevronRight size={13} className="text-gray-300 group-hover:text-[#D60041] group-hover:translate-x-0.5 transition-all" />
            )}
          </div>
        </button>

        {/* Pending Review */}
        <button
          type="button"
          onClick={() => onKpiClick('pending')}
          aria-label="Filter by pending applications"
          aria-pressed={isPendingActive}
          className={`relative text-left w-full p-3.5 sm:p-4 rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden group active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-amber-500 ${
            isPendingActive
              ? 'bg-amber-50/90 border-2 border-amber-500 ring-2 ring-amber-500/20 shadow-sm hover:bg-amber-100/80 hover:border-amber-500'
              : 'bg-white border border-gray-200/90 shadow-xs hover:border-amber-300 hover:bg-amber-50/40 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-colors ${
              isPendingActive ? 'text-amber-900 font-black' : 'text-amber-700 group-hover:text-amber-800'
            }`}>
              Pending
            </span>
            <div className={`p-1.5 rounded-lg transition-colors ${
              isPendingActive 
                ? 'bg-amber-500 text-white shadow-xs' 
                : 'bg-amber-50 text-amber-600 group-hover:bg-amber-100 group-hover:text-amber-700'
            }`}>
              <Clock size={14} />
            </div>
          </div>
          <p className={`text-xl sm:text-2xl font-black tracking-tight mt-1 transition-colors ${
            isPendingActive ? 'text-amber-950' : 'text-gray-900 group-hover:text-amber-950'
          }`}>
            {stats.pending}
          </p>
          <div className={`flex items-center justify-between mt-2 pt-2 border-t text-[11px] font-semibold transition-colors ${
            isPendingActive 
              ? 'border-amber-200/80 text-amber-900' 
              : 'border-gray-100 group-hover:border-amber-100 text-amber-700 group-hover:text-amber-800'
          }`}>
            <span>Needs review</span>
            {isPendingActive ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-amber-500 text-white text-[9px] font-black uppercase tracking-wider shadow-2xs">
                <Check size={10} strokeWidth={3} /> Active
              </span>
            ) : (
              <ChevronRight size={13} className="text-gray-300 group-hover:text-amber-600 group-hover:translate-x-0.5 transition-all" />
            )}
          </div>
        </button>

        {/* In Interview */}
        <button
          type="button"
          onClick={() => onKpiClick('interview')}
          aria-label="Filter by candidates in interview"
          aria-pressed={isInterviewActive}
          className={`relative text-left w-full p-3.5 sm:p-4 rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden group active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-purple-500 ${
            isInterviewActive
              ? 'bg-purple-50/90 border-2 border-purple-500 ring-2 ring-purple-500/20 shadow-sm hover:bg-purple-100/80 hover:border-purple-500'
              : 'bg-white border border-gray-200/90 shadow-xs hover:border-purple-300 hover:bg-purple-50/40 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] sm:text-[11px] font-bold uppercase tracking-wider truncate pr-1 transition-colors ${
              isInterviewActive ? 'text-purple-900 font-black' : 'text-purple-700 group-hover:text-purple-800'
            }`}>
              Interview
            </span>
            <div className={`p-1.5 rounded-lg transition-colors ${
              isInterviewActive 
                ? 'bg-purple-600 text-white shadow-xs' 
                : 'bg-purple-50 text-purple-600 group-hover:bg-purple-100 group-hover:text-purple-700'
            }`}>
              <Clock size={14} />
            </div>
          </div>
          <p className={`text-xl sm:text-2xl font-black tracking-tight mt-1 transition-colors ${
            isInterviewActive ? 'text-purple-950' : 'text-gray-900 group-hover:text-purple-950'
          }`}>
            {stats.interview}
          </p>
          <div className={`flex items-center justify-between mt-2 pt-2 border-t text-[11px] font-semibold transition-colors ${
            isInterviewActive 
              ? 'border-purple-200/80 text-purple-900' 
              : 'border-gray-100 group-hover:border-purple-100 text-purple-700 group-hover:text-purple-800'
          }`}>
            <span>In process</span>
            {isInterviewActive ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-purple-600 text-white text-[9px] font-black uppercase tracking-wider shadow-2xs">
                <Check size={10} strokeWidth={3} /> Active
              </span>
            ) : (
              <ChevronRight size={13} className="text-gray-300 group-hover:text-purple-600 group-hover:translate-x-0.5 transition-all" />
            )}
          </div>
        </button>

        {/* Accepted / Hired */}
        <button
          type="button"
          onClick={() => onKpiClick('accepted')}
          aria-label="Filter by accepted candidates"
          aria-pressed={isAcceptedActive}
          className={`relative text-left w-full p-3.5 sm:p-4 rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden group active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-teal-500 ${
            isAcceptedActive
              ? 'bg-teal-50/90 border-2 border-teal-500 ring-2 ring-teal-500/20 shadow-sm hover:bg-teal-100/80 hover:border-teal-500'
              : 'bg-white border border-gray-200/90 shadow-xs hover:border-teal-300 hover:bg-teal-50/40 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-colors ${
              isAcceptedActive ? 'text-teal-900 font-black' : 'text-teal-700 group-hover:text-teal-800'
            }`}>
              Accepted
            </span>
            <div className={`p-1.5 rounded-lg transition-colors ${
              isAcceptedActive 
                ? 'bg-teal-600 text-white shadow-xs' 
                : 'bg-teal-50 text-teal-600 group-hover:bg-teal-100 group-hover:text-teal-700'
            }`}>
              <CheckCircle2 size={14} />
            </div>
          </div>
          <p className={`text-xl sm:text-2xl font-black tracking-tight mt-1 transition-colors ${
            isAcceptedActive ? 'text-teal-950' : 'text-gray-900 group-hover:text-teal-950'
          }`}>
            {stats.accepted}
          </p>
          <div className={`flex items-center justify-between mt-2 pt-2 border-t text-[11px] font-semibold transition-colors ${
            isAcceptedActive 
              ? 'border-teal-200/80 text-teal-900' 
              : 'border-gray-100 group-hover:border-teal-100 text-teal-700 group-hover:text-teal-800'
          }`}>
            <span>Hired talent</span>
            {isAcceptedActive ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-teal-600 text-white text-[9px] font-black uppercase tracking-wider shadow-2xs">
                <Check size={10} strokeWidth={3} /> Active
              </span>
            ) : (
              <ChevronRight size={13} className="text-gray-300 group-hover:text-teal-600 group-hover:translate-x-0.5 transition-all" />
            )}
          </div>
        </button>

        {/* Archived */}
        <button
          type="button"
          onClick={() => onKpiClick('archived')}
          aria-label="Filter by archived applications"
          aria-pressed={isArchivedActive}
          className={`relative text-left w-full p-3.5 sm:p-4 rounded-2xl transition-all duration-200 cursor-pointer overflow-hidden group active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-gray-600 ${
            isArchivedActive
              ? 'bg-gray-100 border-2 border-gray-700 ring-2 ring-gray-700/20 shadow-sm hover:bg-gray-200/80 hover:border-gray-800'
              : 'bg-white border border-gray-200/90 shadow-xs hover:border-gray-400 hover:bg-gray-50/70 hover:shadow-md'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] sm:text-[11px] font-bold uppercase tracking-wider transition-colors ${
              isArchivedActive ? 'text-gray-900 font-black' : 'text-gray-600 group-hover:text-gray-900'
            }`}>
              Archived
            </span>
            <div className={`p-1.5 rounded-lg transition-colors ${
              isArchivedActive 
                ? 'bg-gray-800 text-white shadow-xs' 
                : 'bg-gray-100 text-gray-600 group-hover:bg-gray-200 group-hover:text-gray-900'
            }`}>
              <Archive size={14} />
            </div>
          </div>
          <p className={`text-xl sm:text-2xl font-black tracking-tight mt-1 transition-colors ${
            isArchivedActive ? 'text-gray-950' : 'text-gray-900 group-hover:text-gray-950'
          }`}>
            {stats.archived}
          </p>
          <div className={`flex items-center justify-between mt-2 pt-2 border-t text-[11px] font-semibold transition-colors ${
            isArchivedActive 
              ? 'border-gray-300 text-gray-900' 
              : 'border-gray-100 group-hover:border-gray-200 text-gray-600 group-hover:text-gray-900'
          }`}>
            <span>Hidden records</span>
            {isArchivedActive ? (
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-gray-800 text-white text-[9px] font-black uppercase tracking-wider shadow-2xs">
                <Check size={10} strokeWidth={3} /> Active
              </span>
            ) : (
              <ChevronRight size={13} className="text-gray-300 group-hover:text-gray-700 group-hover:translate-x-0.5 transition-all" />
            )}
          </div>
        </button>

      </div>
    </div>
  );
};

export default ScreeningHeader;
