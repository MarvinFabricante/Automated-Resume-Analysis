import React from 'react';
import { Search, Filter, ArrowUpDown, X, Sparkles, RotateCcw, Archive, Eye, Check } from 'lucide-react';

const SearchAndFilter = ({ 
  searchQuery, 
  setSearchQuery, 
  statusFilter, 
  setStatusFilter, 
  jobFilter, 
  setJobFilter, 
  jobOptions = [],
  scoreFilter = 'All Scores',
  setScoreFilter,
  sortBy = 'match_desc',
  setSortBy,
  showSuggestions, 
  setShowSuggestions, 
  suggestions = [],
  onResetFilters,
  isFiltered = false,
  includeArchived = false,
  setIncludeArchived,
  archivedCount = 0,
  hiddenArchivedMatchCount = 0
}) => {
  // Check active state for each individual filter
  const isJobActive = jobFilter !== "All Jobs";
  const isStatusActive = statusFilter !== "All Status";
  const isScoreActive = scoreFilter !== "All Scores";
  const isSortActive = sortBy !== "match_desc";
  const isSearchActive = Boolean(searchQuery.trim());

  return (
    <div className="bg-white p-3.5 sm:p-5 md:p-6 rounded-2xl sm:rounded-3xl border border-gray-200/80 shadow-sm mb-5 sm:mb-7 space-y-3.5 sm:space-y-4">
      
      {/* Top Row: Omnisearch Input + Quick Archived View Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
        {/* Omnisearch */}
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none z-10">
            <Search className="h-4 w-4 text-gray-400" />
          </div>
          
          <input
            type="text"
            placeholder="Search candidate name, position, skill, email, college..."
            className="w-full pl-10 pr-9 py-2.5 sm:py-3 bg-gray-50/70 border border-gray-200 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-medium placeholder-gray-400 focus:outline-none focus:border-[#D60041]/40 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-200 relative z-10"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          />

          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery('')}
              className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-gray-400 hover:text-gray-600 z-20 cursor-pointer"
              title="Clear search query"
            >
              <X className="h-4 w-4" />
            </button>
          )}

          {/* Suggestion Dropdown */}
          {showSuggestions && suggestions.length > 0 && (
            <ul className="absolute top-full left-0 w-full mt-1.5 bg-white border border-gray-100 rounded-xl sm:rounded-2xl shadow-xl z-50 overflow-hidden py-1.5 animate-in fade-in zoom-in-95 duration-150 max-h-64 overflow-y-auto">
              {suggestions.map((item, idx) => {
                const name = typeof item === 'string' ? item : item.name;
                const subtext = typeof item === 'object' ? `${item.role || ''} ${item.score ? `• ${item.score}% Match` : ''}` : null;

                return (
                  <li
                    key={idx}
                    className="px-3.5 sm:px-4 py-2 hover:bg-pink-50 hover:text-[#D60041] cursor-pointer text-xs sm:text-sm font-semibold transition-colors flex items-center justify-between"
                    onMouseDown={() => {
                      setSearchQuery(name);
                      setShowSuggestions(false);
                    }}
                  >
                    <div className="flex items-center gap-2.5 truncate pr-2">
                      <Search className="h-3.5 w-3.5 text-gray-400 shrink-0" />
                      <span className="truncate">{name}</span>
                    </div>
                    {subtext && (
                      <span className="text-[11px] font-normal text-gray-400 shrink-0">{subtext}</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Quick Archive Controls - Responsive grouping */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 self-end sm:self-auto w-full sm:w-auto">
          <button
            type="button"
            onClick={() => {
              if (statusFilter === 'Archived') {
                setStatusFilter('All Status');
                if (setIncludeArchived) setIncludeArchived(false);
              } else {
                if (setIncludeArchived) setIncludeArchived(!includeArchived);
              }
            }}
            className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3 sm:px-3.5 py-2.5 sm:py-3 rounded-xl sm:rounded-2xl text-xs font-bold transition-all border shadow-sm cursor-pointer whitespace-nowrap ${
              includeArchived || statusFilter === 'Archived' || statusFilter === 'All With Archived'
                ? 'bg-amber-500 hover:bg-amber-600 text-white border-amber-500 shadow-amber-500/20 ring-2 ring-amber-500/20'
                : 'bg-white hover:bg-amber-50/70 text-gray-700 hover:text-amber-800 border-gray-200'
            }`}
            title="Toggle viewing archived candidates alongside active ones"
          >
            <Archive size={14} className={includeArchived || statusFilter === 'Archived' || statusFilter === 'All With Archived' ? 'text-white' : 'text-amber-500'} />
            <span>{includeArchived ? 'Archived Visible' : (statusFilter === 'Archived' ? 'In Archive' : 'Show Archive')}</span>
            {archivedCount > 0 && (
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-black ${
                includeArchived || statusFilter === 'Archived' || statusFilter === 'All With Archived'
                  ? 'bg-black/20 text-white'
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {archivedCount}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              if (statusFilter === 'Archived') {
                setStatusFilter('All Status');
              } else {
                setStatusFilter('Archived');
              }
            }}
            className={`flex-1 sm:flex-none flex items-center justify-center gap-1 px-3 py-2.5 sm:py-3 rounded-xl sm:rounded-2xl text-xs font-bold transition-all border shadow-sm cursor-pointer whitespace-nowrap ${
              statusFilter === 'Archived'
                ? 'bg-gray-800 text-white border-gray-800 ring-2 ring-gray-800/20'
                : 'bg-gray-50 hover:bg-gray-100 text-gray-600 hover:text-gray-900 border-gray-200'
            }`}
            title="Filter directly to archived applications only"
          >
            <span>{statusFilter === 'Archived' ? 'Exit Archived' : 'Archived Only'}</span>
          </button>
        </div>
      </div>

      {/* Dynamic Notification when Search query matches an archived candidate that is currently hidden */}
      {hiddenArchivedMatchCount > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-amber-50/90 border border-amber-200/80 rounded-xl sm:rounded-2xl text-xs text-amber-900 shadow-sm animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-amber-100 rounded-lg text-amber-700 shrink-0">
              <Archive size={14} />
            </div>
            <div>
              <span className="font-bold">Archived match found:</span> <strong>{hiddenArchivedMatchCount}</strong> archived application(s) match your search query.
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIncludeArchived && setIncludeArchived(true)}
            className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-xs font-bold transition-all cursor-pointer shadow-sm self-start sm:self-auto flex items-center gap-1.5"
          >
            <Eye size={12} />
            <span>Show Archived</span>
          </button>
        </div>
      )}

      {/* Bottom Controls Row: Job, Status, Score, and Sort Dropdowns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3 pt-1">
        
        {/* 1. Job Position Filter */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-black uppercase tracking-wider text-gray-400">Position</label>
            {isJobActive && <span className="w-1.5 h-1.5 rounded-full bg-[#D60041]"></span>}
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Filter className={`h-3.5 w-3.5 ${isJobActive ? 'text-[#D60041]' : 'text-gray-400'}`} />
            </div>
            <select
              className={`w-full border pl-8.5 pr-8 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate ${
                isJobActive ? 'bg-pink-50/40 border-pink-200 text-[#D60041]' : 'bg-gray-50/70 border-gray-200'
              }`}
              value={jobFilter}
              onChange={(e) => setJobFilter(e.target.value)}
            >
              <option value="All Jobs">All Positions</option>
              {jobOptions.map((opt, idx) => {
                const title = typeof opt === 'string' ? opt : opt.title;
                const count = typeof opt === 'object' ? opt.count : null;
                if (!title || title === "All Jobs") return null;
                return (
                  <option key={idx} value={title}>
                    {title} {count !== null ? `(${count})` : ''}
                  </option>
                );
              })}
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-gray-400">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>
        </div>

        {/* 2. Application Status Filter */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-black uppercase tracking-wider text-gray-400">Status</label>
            {isStatusActive && <span className="w-1.5 h-1.5 rounded-full bg-[#D60041]"></span>}
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Filter className={`h-3.5 w-3.5 ${isStatusActive ? 'text-[#D60041]' : 'text-gray-400'}`} />
            </div>
            <select
              className={`w-full border pl-8.5 pr-8 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate ${
                isStatusActive ? 'bg-pink-50/40 border-pink-200 text-[#D60041]' : 'bg-gray-50/70 border-gray-200'
              }`}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="All Status">All Active Statuses</option>
              <option value="All With Archived">All Applications (Include Archived)</option>
              <option value="Archived">Archived Applications Only {archivedCount > 0 ? `(${archivedCount})` : ''}</option>
              <option value="Pending">Pending Review</option>
              <option value="Reviewed">Reviewed</option>
              <option value="Interview">All Interviews</option>
              <option value="Technical Interview">Technical Interview</option>
              <option value="Final Interview">Final Interview</option>
              <option value="Accepted">Accepted / Hired</option>
              <option value="Rejected">Rejected</option>
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-gray-400">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>
        </div>

        {/* 3. Match Score Tier Filter */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-black uppercase tracking-wider text-gray-400">AI Match Score</label>
            {isScoreActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>}
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Sparkles className={`h-3.5 w-3.5 ${isScoreActive ? 'text-emerald-600' : 'text-gray-400'}`} />
            </div>
            <select
              className={`w-full border pl-8.5 pr-8 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate ${
                isScoreActive ? 'bg-emerald-50/40 border-emerald-200 text-emerald-800' : 'bg-gray-50/70 border-gray-200'
              }`}
              value={scoreFilter}
              onChange={(e) => setScoreFilter(e.target.value)}
            >
              <option value="All Scores">All Match Scores</option>
              <option value="90+">Top Match (90% - 100%)</option>
              <option value="80+">Strong Fit (80% - 100%)</option>
              <option value="60-79">Moderate Fit (60% - 79%)</option>
              <option value="<60">Low Fit (Below 60%)</option>
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-gray-400">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>
        </div>

        {/* 4. Sort By Filter */}
        <div className="relative">
          <div className="flex items-center justify-between mb-1">
            <label className="text-[10px] font-black uppercase tracking-wider text-gray-400">Sort By</label>
            {isSortActive && <span className="w-1.5 h-1.5 rounded-full bg-purple-500"></span>}
          </div>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <ArrowUpDown className={`h-3.5 w-3.5 ${isSortActive ? 'text-purple-600' : 'text-gray-400'}`} />
            </div>
            <select
              className={`w-full border pl-8.5 pr-8 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate ${
                isSortActive ? 'bg-purple-50/40 border-purple-200 text-purple-800' : 'bg-gray-50/70 border-gray-200'
              }`}
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="match_desc">Match Score: High to Low</option>
              <option value="match_asc">Match Score: Low to High</option>
              <option value="date_desc">Applied: Newest First</option>
              <option value="date_asc">Applied: Oldest First</option>
              <option value="name_asc">Name: A to Z</option>
              <option value="name_desc">Name: Z to A</option>
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-gray-400">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>
        </div>

      </div>

      {/* Active Filter Chips & Clear All */}
      {isFiltered && (
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-gray-100 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mr-1">Active Filters:</span>
            
            {isSearchActive && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-gray-100 text-gray-800 rounded-lg text-[11px] font-semibold border border-gray-200">
                Search: "{searchQuery}"
                <button type="button" onClick={() => setSearchQuery('')} className="hover:text-rose-600 cursor-pointer">
                  <X size={12} />
                </button>
              </span>
            )}

            {isJobActive && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-pink-50 text-[#D60041] rounded-lg text-[11px] font-semibold border border-pink-100">
                Job: {jobFilter}
                <button type="button" onClick={() => setJobFilter('All Jobs')} className="hover:text-rose-700 cursor-pointer">
                  <X size={12} />
                </button>
              </span>
            )}

            {isStatusActive && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-purple-50 text-purple-700 rounded-lg text-[11px] font-semibold border border-purple-100">
                Status: {statusFilter}
                <button type="button" onClick={() => setStatusFilter('All Status')} className="hover:text-purple-900 cursor-pointer">
                  <X size={12} />
                </button>
              </span>
            )}

            {isScoreActive && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-lg text-[11px] font-semibold border border-emerald-100">
                Score: {scoreFilter}
                <button type="button" onClick={() => setScoreFilter('All Scores')} className="hover:text-emerald-900 cursor-pointer">
                  <X size={12} />
                </button>
              </span>
            )}

            {includeArchived && statusFilter !== 'Archived' && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 text-amber-800 rounded-lg text-[11px] font-semibold border border-amber-200">
                Including Archived
                <button type="button" onClick={() => setIncludeArchived && setIncludeArchived(false)} className="hover:text-amber-950 cursor-pointer">
                  <X size={12} />
                </button>
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={onResetFilters}
            className="flex items-center gap-1.5 text-xs font-bold text-[#D60041] hover:text-[#B50037] hover:underline cursor-pointer ml-auto"
          >
            <RotateCcw size={12} />
            <span>Reset All</span>
          </button>
        </div>
      )}

    </div>
  );
};

export default SearchAndFilter;
