import React from 'react';
import { Search, Filter, ArrowUpDown, X, Sparkles, RotateCcw } from 'lucide-react';

const SearchAndFilter = ({ 
  searchQuery, 
  setSearchQuery, 
  statusFilter, 
  setStatusFilter,
  jobFilter, 
  setJobFilter, 
  jobOptions = [], // array of { title, count } or string
  scoreFilter = 'All Scores',
  setScoreFilter,
  sortBy = 'match_desc',
  setSortBy,
  showSuggestions, 
  setShowSuggestions, 
  suggestions = [],
  onResetFilters,
  isFiltered = false
}) => {
  return (
    <div className="bg-white p-4 sm:p-6 md:p-8 rounded-2xl sm:rounded-[32px] border border-gray-100 shadow-sm mb-6 sm:mb-8 space-y-4">
      
      {/* Top Row: Omnisearch Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none z-10">
          <Search className="h-4 w-4 sm:h-5 sm:w-5 text-gray-400" />
        </div>
        
        <input
          type="text"
          placeholder="Search by candidate name, role, skills, email, or location..."
          className="w-full pl-11 pr-11 py-3 sm:py-3.5 bg-gray-50/50 border-2 border-gray-100 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-medium focus:outline-none focus:border-pink-200 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-200 relative z-10"
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
            className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-gray-600 z-20"
            title="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}

        {/* Suggestion Dropdown */}
        {showSuggestions && suggestions.length > 0 && (
          <ul className="absolute top-full left-0 w-full mt-2 bg-white border border-gray-100 rounded-xl sm:rounded-2xl shadow-xl z-50 overflow-hidden py-2 animate-in fade-in zoom-in-95 duration-150">
            {suggestions.map((item, idx) => {
              const name = typeof item === 'string' ? item : item.name;
              const subtext = typeof item === 'object' ? `${item.role || ''} ${item.score ? `• ${item.score}% Match` : ''}` : null;

              return (
                <li
                  key={idx}
                  className="px-4 sm:px-5 py-2.5 sm:py-3 hover:bg-pink-50 hover:text-[#D60041] cursor-pointer text-xs sm:text-sm font-semibold transition-colors flex items-center justify-between"
                  onMouseDown={() => {
                    setSearchQuery(name);
                    setShowSuggestions(false);
                  }}
                >
                  <div className="flex items-center gap-3">
                    <Search className="h-4 w-4 text-gray-300" />
                    <span>{name}</span>
                  </div>
                  {subtext && (
                    <span className="text-[11px] font-normal text-gray-400">{subtext}</span>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Bottom Controls Row: Job, Status, Score, and Sort Dropdowns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
        
        {/* 1. Job Position Filter */}
        <div className="relative">
          <label className="text-[10px] font-black uppercase tracking-wider text-gray-400 mb-1.5 block">Position</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <Filter className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <select
              className="w-full bg-gray-50/60 border border-gray-200 pl-9 pr-9 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate"
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
          <label className="text-[10px] font-black uppercase tracking-wider text-gray-400 mb-1.5 block">Status</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <Filter className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <select
              className="w-full bg-gray-50/60 border border-gray-200 pl-9 pr-9 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="All Status">All Statuses (Active)</option>
              <option value="Pending">Pending Review</option>
              <option value="Reviewed">Already Reviewed</option>
              <option value="Technical Interview">Technical Interview</option>
              <option value="Final Interview">Final Interview</option>
              <option value="Accepted">Accepted / Hired</option>
              <option value="Rejected">Rejected</option>
              <option value="Archived">Archived Applications</option>
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-gray-400">
              <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </div>
          </div>
        </div>

        {/* 3. Match Score Tier Filter */}
        <div className="relative">
          <label className="text-[10px] font-black uppercase tracking-wider text-gray-400 mb-1.5 block">AI Match Score</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <Sparkles className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <select
              className="w-full bg-gray-50/60 border border-gray-200 pl-9 pr-9 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate"
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
          <label className="text-[10px] font-black uppercase tracking-wider text-gray-400 mb-1.5 block">Sort By</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
              <ArrowUpDown className="h-3.5 w-3.5 text-gray-400" />
            </div>
            <select
              className="w-full bg-gray-50/60 border border-gray-200 pl-9 pr-9 py-2.5 rounded-xl text-xs font-bold text-gray-700 focus:outline-none focus:border-pink-300 focus:bg-white transition-all cursor-pointer appearance-none truncate"
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

      {/* Clear Filters Indicator */}
      {isFiltered && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-50 text-xs">
          <span className="text-gray-500 font-medium">Filtered search is currently active.</span>
          <button
            onClick={onResetFilters}
            className="flex items-center gap-1.5 text-xs font-bold text-[#D60041] hover:underline cursor-pointer"
          >
            <RotateCcw size={12} />
            <span>Reset All Filters</span>
          </button>
        </div>
      )}

    </div>
  );
};

export default SearchAndFilter;
