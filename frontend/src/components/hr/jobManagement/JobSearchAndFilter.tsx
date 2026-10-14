import React from 'react';
import { Search, Filter, Building2 } from 'lucide-react';

interface JobSearchAndFilterProps {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  statusFilter: string;
  setStatusFilter: (filter: string) => void;
  deptFilter: string;
  setDeptFilter: (filter: string) => void;
  departments: string[];
  showSuggestions: boolean;
  setShowSuggestions: (show: boolean) => void;
  suggestions: string[];
}

const JobSearchAndFilter: React.FC<JobSearchAndFilterProps> = ({
  searchQuery,
  setSearchQuery,
  statusFilter,
  setStatusFilter,
  deptFilter,
  setDeptFilter,
  departments,
  showSuggestions,
  setShowSuggestions,
  suggestions
}) => {
  return (
    <div className="bg-white p-4 sm:p-6 md:p-7 rounded-2xl sm:rounded-3xl md:rounded-[32px] border border-gray-100 shadow-sm mb-6 sm:mb-8 flex flex-col md:flex-row gap-4 md:items-end">
      {/* Search Input with Clear Label */}
      <div className="relative flex-grow min-w-0">
        <label htmlFor="job-search-input" className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-2">
          <Search className="w-4 h-4 text-[#D60041]" />
          <span>Search Positions</span>
        </label>
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 sm:pl-4 flex items-center pointer-events-none z-10">
            <Search className="h-4 w-4 sm:h-5 sm:w-5 text-gray-400" />
          </div>
          <input
            id="job-search-input"
            type="text"
            placeholder="Search by title or job ID..."
            className="w-full pl-10 sm:pl-11 pr-4 py-2.5 sm:py-3.5 bg-gray-50/50 border-2 border-gray-100 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-medium focus:outline-none focus:border-pink-100 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-300 relative z-10"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
          />

          {showSuggestions && suggestions.length > 0 && (
            <ul className="absolute top-full left-0 w-full mt-2 bg-white border border-gray-100 rounded-2xl shadow-lg z-50 overflow-hidden py-2">
              {suggestions.map((title, idx) => (
                <li
                  key={idx}
                  className="px-4 sm:px-5 py-2.5 sm:py-3 hover:bg-pink-50 hover:text-[#D60041] cursor-pointer text-xs sm:text-sm font-semibold transition-colors flex items-center gap-3"
                  onClick={() => {
                    setSearchQuery(title);
                    setShowSuggestions(false);
                  }}
                >
                  <Search className="h-3.5 w-3.5 sm:h-4 sm:w-4 text-gray-300" />
                  {title}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Filter Dropdowns Container: 2-column grid on mobile/tablet, row on desktop */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:flex md:items-end gap-3 sm:gap-4 shrink-0">
        {/* Status Filter */}
        <div className="relative w-full md:w-48 shrink-0">
          <label htmlFor="job-status-filter" className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-2">
            <Filter className="w-4 h-4 text-[#D60041]" />
            <span>Posting Status</span>
          </label>
          <div className="relative">
            <select
              id="job-status-filter"
              aria-label="Filter by Status"
              className="w-full bg-gray-50/50 border-2 border-gray-100 pl-3.5 sm:pl-4 pr-9 py-2.5 sm:py-3.5 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold text-gray-700 focus:outline-none focus:border-pink-100 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-300 cursor-pointer appearance-none truncate"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="All Status">All Statuses</option>
              <option value="Active">Active Jobs</option>
              <option value="Inactive">Inactive Jobs</option>
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 sm:pr-4 flex items-center pointer-events-none">
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </div>
          </div>
        </div>

        {/* Department Filter */}
        <div className="relative w-full md:w-56 shrink-0">
          <label htmlFor="job-dept-filter" className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-[#D60041]" />
            <span>Department</span>
          </label>
          <div className="relative">
            <select
              id="job-dept-filter"
              aria-label="Filter by Department"
              className="w-full bg-gray-50/50 border-2 border-gray-100 pl-3.5 sm:pl-4 pr-9 py-2.5 sm:py-3.5 rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold text-gray-700 focus:outline-none focus:border-pink-100 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-300 cursor-pointer appearance-none truncate"
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
            >
              {departments.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
            <div className="absolute inset-y-0 right-0 pr-3 sm:pr-4 flex items-center pointer-events-none">
              <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default JobSearchAndFilter;
