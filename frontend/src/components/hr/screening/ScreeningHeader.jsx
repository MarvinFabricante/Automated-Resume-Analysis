import React from 'react';
import { 
  Download, Scale, LayoutGrid, List, Users, Clock, 
  Sparkles, CheckCircle2, Archive, RefreshCw 
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
  return (
    <div className="space-y-6 mb-8">
      {/* Top Title & Top Action Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-black text-gray-900 tracking-tight">Resume Screening</h1>
            {isRefreshing && (
              <span className="flex items-center gap-1.5 text-xs text-[#D60041] font-bold">
                <RefreshCw size={12} className="animate-spin" />
                Syncing
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 font-medium mt-1">
            Review, evaluate AI match ratings, schedule interviews, and screen candidates.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* View Mode Switcher */}
          <div className="bg-gray-100 p-1 rounded-xl flex items-center border border-gray-200">
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              title="Cards View"
              className={`p-2 rounded-lg transition-all ${
                viewMode === 'cards' 
                  ? 'bg-white text-[#D60041] shadow-sm font-bold' 
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <LayoutGrid size={16} />
            </button>
            <button
              type="button"
              onClick={() => setViewMode('table')}
              title="Table / Compact View"
              className={`p-2 rounded-lg transition-all ${
                viewMode === 'table' 
                  ? 'bg-white text-[#D60041] shadow-sm font-bold' 
                  : 'text-gray-500 hover:text-gray-900'
              }`}
            >
              <List size={16} />
            </button>
          </div>

          {/* Compare Candidates button */}
          <button
            type="button"
            onClick={onNavigateCompare}
            className={`flex items-center gap-2 px-4 sm:px-5 py-2.5 sm:py-3 border rounded-xl text-xs sm:text-sm font-bold transition-all duration-200 shadow-sm ${
              selectedCount >= 2 
                ? 'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100 shadow-purple-50' 
                : 'bg-white border-gray-200 text-gray-700 hover:border-purple-200 hover:text-purple-600'
            }`}
          >
            <Scale size={16} className={selectedCount >= 2 ? 'text-purple-600' : 'text-gray-400'} />
            <span>Compare Candidates</span>
            {selectedCount > 0 && (
              <span className="px-2 py-0.5 bg-purple-600 text-white rounded-full text-[10px] font-black">
                {selectedCount}
              </span>
            )}
          </button>

          {/* Export List Button */}
          <button 
            type="button"
            onClick={onExport}
            className="flex items-center gap-2 px-4 sm:px-5 py-2.5 sm:py-3 bg-white border border-gray-200 rounded-xl text-xs sm:text-sm font-bold text-gray-700 hover:border-pink-200 hover:text-[#D60041] hover:bg-pink-50/50 transition-all duration-200 shadow-sm group"
          >
            <Download className="w-4 h-4 text-gray-400 group-hover:text-[#D60041] transition-colors" />
            <span>Export List</span>
          </button>

          {/* Refresh Button */}
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              title="Refresh candidates"
              className="p-2.5 sm:p-3 bg-white border border-gray-200 rounded-xl text-gray-500 hover:text-gray-900 hover:border-gray-300 transition-all shadow-sm"
            >
              <RefreshCw size={16} className={isRefreshing ? 'animate-spin text-[#D60041]' : ''} />
            </button>
          )}
        </div>
      </div>

      {/* Interactive KPI Summary Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        
        {/* Total Candidates */}
        <div
          onClick={() => onKpiClick('all')}
          className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer ${
            activeStatusFilter === 'All Status' && activeScoreFilter === 'All Scores'
              ? 'bg-gray-900 text-white border-gray-900 shadow-md ring-2 ring-gray-900/10'
              : 'bg-white border-gray-100 hover:border-gray-200 shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider opacity-70">Total</span>
            <Users size={14} className="opacity-60" />
          </div>
          <p className="text-xl sm:text-2xl font-black">{stats.total}</p>
        </div>

        {/* Pending Review */}
        <div
          onClick={() => onKpiClick('pending')}
          className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer ${
            activeStatusFilter === 'Pending'
              ? 'bg-amber-500 text-white border-amber-500 shadow-md ring-2 ring-amber-500/20'
              : 'bg-white border-gray-100 hover:border-amber-200 shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-amber-600">Pending</span>
            <Clock size={14} className="text-amber-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black">{stats.pending}</p>
        </div>

        {/* Top Match (>=80%) */}
        <div
          onClick={() => onKpiClick('highMatch')}
          className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer ${
            activeScoreFilter === '80+'
              ? 'bg-emerald-600 text-white border-emerald-600 shadow-md ring-2 ring-emerald-600/20'
              : 'bg-white border-gray-100 hover:border-emerald-200 shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600">Top Match (≥80%)</span>
            <Sparkles size={14} className="text-emerald-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black">{stats.highMatch}</p>
        </div>

        {/* In Interview */}
        <div
          onClick={() => onKpiClick('interview')}
          className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer ${
            activeStatusFilter === 'Technical Interview' || activeStatusFilter === 'Final Interview'
              ? 'bg-purple-600 text-white border-purple-600 shadow-md ring-2 ring-purple-600/20'
              : 'bg-white border-gray-100 hover:border-purple-200 shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600">In Interview</span>
            <Clock size={14} className="text-purple-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black">{stats.interview}</p>
        </div>

        {/* Accepted / Hired */}
        <div
          onClick={() => onKpiClick('accepted')}
          className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer ${
            activeStatusFilter === 'Accepted'
              ? 'bg-teal-600 text-white border-teal-600 shadow-md ring-2 ring-teal-600/20'
              : 'bg-white border-gray-100 hover:border-teal-200 shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-teal-600">Accepted</span>
            <CheckCircle2 size={14} className="text-teal-500" />
          </div>
          <p className="text-xl sm:text-2xl font-black">{stats.accepted}</p>
        </div>

        {/* Archived */}
        <div
          onClick={() => onKpiClick('archived')}
          className={`p-3.5 sm:p-4 rounded-2xl border transition-all cursor-pointer ${
            activeStatusFilter === 'Archived'
              ? 'bg-gray-700 text-white border-gray-700 shadow-md ring-2 ring-gray-700/20'
              : 'bg-white border-gray-100 hover:border-gray-200 shadow-sm text-gray-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">Archived</span>
            <Archive size={14} className="text-gray-400" />
          </div>
          <p className="text-xl sm:text-2xl font-black">{stats.archived}</p>
        </div>

      </div>
    </div>
  );
};

export default ScreeningHeader;
