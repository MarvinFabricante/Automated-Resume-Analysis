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
  const isTotalActive = activeStatusFilter === 'All Status' && activeScoreFilter === 'All Scores';
  const isPendingActive = activeStatusFilter === 'Pending';
  const isHighMatchActive = activeScoreFilter === '80+';
  const isInterviewActive = activeStatusFilter === 'Technical Interview' || activeStatusFilter === 'Final Interview';
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
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-2.5 sm:gap-3.5">
        
        {/* Total Candidates */}
        <div
          onClick={() => onKpiClick('all')}
          role="button"
          tabIndex={0}
          className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden group ${
            isTotalActive
              ? 'bg-gradient-to-br from-gray-900 to-gray-800 text-white border-gray-900 shadow-md ring-2 ring-gray-900/10'
              : 'bg-white border-gray-200/80 hover:border-gray-300 hover:shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className={`text-[10px] font-bold uppercase tracking-wider ${isTotalActive ? 'text-gray-300' : 'text-gray-500'}`}>
              Total
            </span>
            <div className={`p-1.5 rounded-lg ${isTotalActive ? 'bg-white/10 text-white' : 'bg-gray-100 text-gray-500'}`}>
              <Users size={13} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-black tracking-tight">{stats.total}</p>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-black/5 dark:border-white/10 text-[10px] font-semibold">
            <span className={isTotalActive ? 'text-gray-300' : 'text-gray-400'}>Active pool</span>
            {isTotalActive && <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>}
          </div>
        </div>

        {/* Pending Review */}
        <div
          onClick={() => onKpiClick('pending')}
          role="button"
          tabIndex={0}
          className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden group ${
            isPendingActive
              ? 'bg-amber-50/80 border-amber-400 ring-2 ring-amber-400/20 text-amber-950 shadow-sm'
              : 'bg-white border-gray-200/80 hover:border-amber-300 hover:shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700">
              Pending
            </span>
            <div className={`p-1.5 rounded-lg ${isPendingActive ? 'bg-amber-200/70 text-amber-800' : 'bg-amber-50 text-amber-600'}`}>
              <Clock size={13} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-black tracking-tight text-amber-950">{stats.pending}</p>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-amber-200/50 text-[10px] font-semibold text-amber-700">
            <span>Needs review</span>
            {isPendingActive && <Check size={12} className="text-amber-700" />}
          </div>
        </div>

        {/* Top Match (>=80%) */}
        <div
          onClick={() => onKpiClick('highMatch')}
          role="button"
          tabIndex={0}
          className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden group ${
            isHighMatchActive
              ? 'bg-emerald-50/80 border-emerald-400 ring-2 ring-emerald-400/20 text-emerald-950 shadow-sm'
              : 'bg-white border-gray-200/80 hover:border-emerald-300 hover:shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 truncate pr-1">
              Top Match
            </span>
            <div className={`p-1.5 rounded-lg ${isHighMatchActive ? 'bg-emerald-200/70 text-emerald-800' : 'bg-emerald-50 text-emerald-600'}`}>
              <Sparkles size={13} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-black tracking-tight text-emerald-950">{stats.highMatch}</p>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-emerald-200/50 text-[10px] font-semibold text-emerald-700">
            <span>Score ≥ 80%</span>
            {isHighMatchActive && <Check size={12} className="text-emerald-700" />}
          </div>
        </div>

        {/* In Interview */}
        <div
          onClick={() => onKpiClick('interview')}
          role="button"
          tabIndex={0}
          className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden group ${
            isInterviewActive
              ? 'bg-purple-50/80 border-purple-400 ring-2 ring-purple-400/20 text-purple-950 shadow-sm'
              : 'bg-white border-gray-200/80 hover:border-purple-300 hover:shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 truncate pr-1">
              Interview
            </span>
            <div className={`p-1.5 rounded-lg ${isInterviewActive ? 'bg-purple-200/70 text-purple-800' : 'bg-purple-50 text-purple-600'}`}>
              <Clock size={13} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-black tracking-tight text-purple-950">{stats.interview}</p>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-purple-200/50 text-[10px] font-semibold text-purple-700">
            <span>In process</span>
            {isInterviewActive && <Check size={12} className="text-purple-700" />}
          </div>
        </div>

        {/* Accepted / Hired */}
        <div
          onClick={() => onKpiClick('accepted')}
          role="button"
          tabIndex={0}
          className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden group ${
            isAcceptedActive
              ? 'bg-teal-50/80 border-teal-400 ring-2 ring-teal-400/20 text-teal-950 shadow-sm'
              : 'bg-white border-gray-200/80 hover:border-teal-300 hover:shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-teal-700">
              Accepted
            </span>
            <div className={`p-1.5 rounded-lg ${isAcceptedActive ? 'bg-teal-200/70 text-teal-800' : 'bg-teal-50 text-teal-600'}`}>
              <CheckCircle2 size={13} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-black tracking-tight text-teal-950">{stats.accepted}</p>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-teal-200/50 text-[10px] font-semibold text-teal-700">
            <span>Hired talent</span>
            {isAcceptedActive && <Check size={12} className="text-teal-700" />}
          </div>
        </div>

        {/* Archived */}
        <div
          onClick={() => onKpiClick('archived')}
          role="button"
          tabIndex={0}
          className={`relative p-3.5 sm:p-4 rounded-2xl border transition-all duration-200 cursor-pointer overflow-hidden group ${
            isArchivedActive
              ? 'bg-gray-100 border-gray-400 ring-2 ring-gray-400/20 text-gray-900 shadow-sm'
              : 'bg-white border-gray-200/80 hover:border-gray-300 hover:shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
              Archived
            </span>
            <div className={`p-1.5 rounded-lg ${isArchivedActive ? 'bg-gray-300 text-gray-900' : 'bg-gray-100 text-gray-500'}`}>
              <Archive size={13} />
            </div>
          </div>
          <p className="text-xl sm:text-2xl font-black tracking-tight text-gray-900">{stats.archived}</p>
          <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-200 text-[10px] font-semibold text-gray-500">
            <span>Hidden records</span>
            {isArchivedActive && <Check size={12} className="text-gray-700" />}
          </div>
        </div>

      </div>
    </div>
  );
};

export default ScreeningHeader;
