import React from 'react';
import {
  Search,
  Filter,
  Building2,
  X,
  ArrowUpDown,
  LayoutGrid,
  List,
  RotateCcw,
} from 'lucide-react';

export type JobSortOption = 'newest' | 'applicants' | 'title';
export type JobViewMode = 'cards' | 'table';

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
  sortBy?: JobSortOption;
  setSortBy?: (sort: JobSortOption) => void;
  viewMode?: JobViewMode;
  setViewMode?: (mode: JobViewMode) => void;
  customWeightsOnly?: boolean;
  setCustomWeightsOnly?: (val: boolean) => void;
  totalFiltered?: number;
  totalCount?: number;
  onResetFilters?: () => void;
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
  suggestions,
  sortBy = 'newest',
  setSortBy,
  viewMode = 'cards',
  setViewMode,
  customWeightsOnly = false,
  setCustomWeightsOnly,
  totalFiltered,
  totalCount,
  onResetFilters,
}) => {
  const hasActiveFilters =
    Boolean(searchQuery.trim()) ||
    statusFilter !== 'All Status' ||
    deptFilter !== 'All Departments' ||
    customWeightsOnly;

  return (
    <div className="bg-white/95 backdrop-blur-xs p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-gray-200/80 shadow-xs space-y-4">
      <div className="flex flex-col xl:flex-row gap-3.5 xl:items-end">
        {/* Search Input */}
        <div className="relative flex-grow min-w-0">
          <label
            htmlFor="job-search-input"
            className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5"
          >
            <Search className="w-3.5 h-3.5 text-[#D10043]" />
            <span>Search Positions</span>
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none z-10">
              <Search className="h-4 w-4 text-gray-400" />
            </div>
            <input
              id="job-search-input"
              type="text"
              placeholder="Search by title, job ID, department, or skill..."
              className="w-full pl-10 pr-10 py-2.5 bg-gray-50/70 border border-gray-200 rounded-xl text-xs sm:text-sm font-medium text-gray-800 placeholder:text-gray-400 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-200 relative z-10"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowSuggestions(true);
              }}
              onFocus={() => setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 180)}
            />
            {searchQuery && (
              <button
                type="button"
                aria-label="Clear search"
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-700 z-20 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            )}

            {showSuggestions && suggestions.length > 0 && (
              <ul className="absolute top-full left-0 w-full mt-1.5 bg-white border border-gray-200 rounded-2xl shadow-xl z-50 overflow-hidden py-1.5">
                {suggestions.map((title, idx) => (
                  <li
                    key={idx}
                    className="px-4 py-2 hover:bg-pink-50 hover:text-[#D10043] cursor-pointer text-xs sm:text-sm font-semibold transition-colors flex items-center gap-2.5 text-gray-700"
                    onMouseDown={() => {
                      setSearchQuery(title);
                      setShowSuggestions(false);
                    }}
                  >
                    <Search className="h-3.5 w-3.5 text-gray-300 shrink-0" />
                    <span className="truncate">{title}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Filters & Controls */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:flex xl:items-end gap-3 shrink-0">
          {/* Status Filter */}
          <div className="w-full xl:w-40">
            <label
              htmlFor="job-status-filter"
              className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5"
            >
              <Filter className="w-3.5 h-3.5 text-[#D10043]" />
              <span>Status</span>
            </label>
            <div className="relative">
              <select
                id="job-status-filter"
                aria-label="Filter by Status"
                className="w-full bg-gray-50/70 border border-gray-200 pl-3.5 pr-8 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-gray-700 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all cursor-pointer appearance-none truncate"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="All Status">All Statuses</option>
                <option value="Active">Active Only</option>
                <option value="Inactive">Archived Only</option>
              </select>
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {/* Department Filter */}
          <div className="w-full xl:w-48">
            <label
              htmlFor="job-dept-filter"
              className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5"
            >
              <Building2 className="w-3.5 h-3.5 text-[#D10043]" />
              <span>Department</span>
            </label>
            <div className="relative">
              <select
                id="job-dept-filter"
                aria-label="Filter by Department"
                className="w-full bg-gray-50/70 border border-gray-200 pl-3.5 pr-8 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-gray-700 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all cursor-pointer appearance-none truncate"
                value={deptFilter}
                onChange={(e) => setDeptFilter(e.target.value)}
              >
                {departments.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
              <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </div>

          {/* Sort Dropdown */}
          {setSortBy && (
            <div className="w-full xl:w-44">
              <label
                htmlFor="job-sort-select"
                className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center gap-1.5"
              >
                <ArrowUpDown className="w-3.5 h-3.5 text-[#D10043]" />
                <span>Sort By</span>
              </label>
              <div className="relative">
                <select
                  id="job-sort-select"
                  aria-label="Sort positions"
                  className="w-full bg-gray-50/70 border border-gray-200 pl-3.5 pr-8 py-2.5 rounded-xl text-xs sm:text-sm font-semibold text-gray-700 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all cursor-pointer appearance-none truncate"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as JobSortOption)}
                >
                  <option value="newest">Newest First</option>
                  <option value="applicants">Most Applicants</option>
                  <option value="title">Title (A–Z)</option>
                </select>
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                  <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </div>
          )}

          {/* View Mode Toggle */}
          {setViewMode && (
            <div className="flex flex-col">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1.5">
                View
              </span>
              <div className="inline-flex bg-gray-100 p-1 rounded-xl border border-gray-200/80 h-[42px]">
                <button
                  type="button"
                  onClick={() => setViewMode('cards')}
                  aria-label="Card view"
                  aria-pressed={viewMode === 'cards'}
                  className={`px-3 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                    viewMode === 'cards'
                      ? 'bg-white text-gray-900 shadow-xs'
                      : 'text-gray-500 hover:text-gray-800'
                  }`}
                >
                  <LayoutGrid size={14} />
                  <span>Cards</span>
                </button>
                <button
                  type="button"
                  onClick={() => setViewMode('table')}
                  aria-label="Table view"
                  aria-pressed={viewMode === 'table'}
                  className={`px-3 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                    viewMode === 'table'
                      ? 'bg-white text-gray-900 shadow-xs'
                      : 'text-gray-500 hover:text-gray-800'
                  }`}
                >
                  <List size={14} />
                  <span>Table</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Results & Active Filters Strip */}
      {(totalFiltered !== undefined || hasActiveFilters) && (
        <div className="pt-3 border-t border-gray-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            {totalFiltered !== undefined && totalCount !== undefined && (
              <span className="text-gray-500 font-medium">
                Showing <strong className="text-gray-900">{totalFiltered}</strong> of{' '}
                <strong className="text-gray-900">{totalCount}</strong> position{totalCount === 1 ? '' : 's'}
              </span>
            )}
            {customWeightsOnly && setCustomWeightsOnly && (
              <button
                type="button"
                onClick={() => setCustomWeightsOnly(false)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-pink-50 text-[#D10043] border border-pink-200 font-bold hover:bg-pink-100 transition-colors cursor-pointer"
              >
                <span>Custom Weights Only</span>
                <X size={12} />
              </button>
            )}
          </div>

          {hasActiveFilters && onResetFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-[#D10043] hover:text-[#B00038] transition-colors cursor-pointer"
            >
              <RotateCcw size={13} />
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default JobSearchAndFilter;
