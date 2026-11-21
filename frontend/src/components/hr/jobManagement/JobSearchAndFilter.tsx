import React from 'react';
import {
  Search,
  Building2,
  X,
  ArrowUpDown,
  LayoutGrid,
  List,
  RotateCcw,
  Sliders,
  ChevronDown,
} from 'lucide-react';

export type JobSortOption = 'newest' | 'applicants' | 'title';
export type JobViewMode = 'cards' | 'table';

interface StatusCounts {
  all: number;
  active: number;
  archived: number;
  customWeights: number;
}

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
  statusCounts?: StatusCounts;
  onResetFilters?: () => void;
}

const STATUS_TABS: Array<{ value: string; label: string; countKey: keyof StatusCounts }> = [
  { value: 'All Status', label: 'All Positions', countKey: 'all' },
  { value: 'Active', label: 'Active', countKey: 'active' },
  { value: 'Inactive', label: 'Archived', countKey: 'archived' },
];

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
  statusCounts,
  onResetFilters,
}) => {
  const hasActiveFilters =
    Boolean(searchQuery.trim()) ||
    statusFilter !== 'All Status' ||
    deptFilter !== 'All Departments' ||
    customWeightsOnly;

  return (
    <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-visible">
      {/* Top Bar: Status Segmented Tabs + Custom Weights + View Switcher */}
      <div className="px-4 sm:px-5 py-3 border-b border-slate-100 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        {/* Status Tabs */}
        <div
          role="tablist"
          aria-label="Filter jobs by status"
          className="inline-flex items-center gap-1 bg-slate-100/80 p-1 rounded-xl border border-slate-200/60 self-start overflow-x-auto max-w-full"
        >
          {STATUS_TABS.map((tab) => {
            const isActive = statusFilter === tab.value;
            const count = statusCounts ? statusCounts[tab.countKey] : undefined;
            return (
              <button
                key={tab.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setStatusFilter(tab.value)}
                className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap cursor-pointer ${
                  isActive
                    ? 'bg-white text-slate-900 shadow-2xs ring-1 ring-slate-200/70'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <span>{tab.label}</span>
                {count !== undefined && (
                  <span
                    className={`px-1.5 py-0.5 rounded-md text-[11px] font-bold tabular-nums ${
                      isActive
                        ? 'bg-[#D10043]/10 text-[#D10043]'
                        : 'bg-slate-200/70 text-slate-600'
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Right Quick Controls */}
        <div className="flex flex-wrap items-center justify-between sm:justify-end gap-2.5">
          {setCustomWeightsOnly && (
            <button
              type="button"
              onClick={() => setCustomWeightsOnly(!customWeightsOnly)}
              aria-pressed={customWeightsOnly}
              className={`inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold border transition-colors cursor-pointer ${
                customWeightsOnly
                  ? 'bg-[#D10043]/10 text-[#D10043] border-[#D10043]/30'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <Sliders size={13} />
              <span>Custom Weights</span>
              {statusCounts && statusCounts.customWeights > 0 && (
                <span
                  className={`px-1.5 py-0.2 rounded text-[10px] font-bold tabular-nums ${
                    customWeightsOnly
                      ? 'bg-[#D10043] text-white'
                      : 'bg-slate-100 text-slate-600'
                  }`}
                >
                  {statusCounts.customWeights}
                </span>
              )}
            </button>
          )}

          {setViewMode && (
            <div className="inline-flex items-center bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/60">
              <button
                type="button"
                onClick={() => setViewMode('cards')}
                aria-label="Card view"
                aria-pressed={viewMode === 'cards'}
                className={`h-7 px-2.5 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 transition-all cursor-pointer ${
                  viewMode === 'cards'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <LayoutGrid size={13} />
                <span>Cards</span>
              </button>
              <button
                type="button"
                onClick={() => setViewMode('table')}
                aria-label="Table view"
                aria-pressed={viewMode === 'table'}
                className={`h-7 px-2.5 rounded-md text-xs font-semibold inline-flex items-center gap-1.5 transition-all cursor-pointer ${
                  viewMode === 'table'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-800'
                }`}
              >
                <List size={13} />
                <span>Table</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Bar: Search Input + Department + Sort */}
      <div className="p-4 sm:px-5 sm:py-3.5 flex flex-col md:flex-row gap-3 items-stretch md:items-center">
        {/* Search Input */}
        <div className="relative flex-1 min-w-0">
          <label htmlFor="job-search-input" className="sr-only">
            Search Positions
          </label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none z-10">
              <Search className="h-4 w-4 text-slate-400" />
            </div>
            <input
              id="job-search-input"
              type="text"
              placeholder="Search by title, requisition ID, department, or skill..."
              className="w-full h-10 pl-10 pr-9 bg-slate-50/70 border border-slate-200 rounded-xl text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 transition-all"
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
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-700 z-20 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            )}

            {showSuggestions && suggestions.length > 0 && (
              <ul className="absolute top-full left-0 w-full mt-1.5 bg-white border border-slate-200 rounded-xl shadow-lg z-50 overflow-hidden py-1">
                {suggestions.map((title, idx) => (
                  <li
                    key={idx}
                    className="px-3.5 py-2 hover:bg-slate-50 hover:text-[#D10043] cursor-pointer text-sm font-medium transition-colors flex items-center gap-2.5 text-slate-700"
                    onMouseDown={() => {
                      setSearchQuery(title);
                      setShowSuggestions(false);
                    }}
                  >
                    <Search className="h-3.5 w-3.5 text-slate-300 shrink-0" />
                    <span className="truncate">{title}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Department & Sort Selects */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:flex items-center gap-2.5 shrink-0">
          <div className="relative md:w-52">
            <label htmlFor="job-dept-filter" className="sr-only">
              Filter by Department
            </label>
            <Building2 className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <select
              id="job-dept-filter"
              aria-label="Filter by Department"
              className="w-full h-10 bg-slate-50/70 border border-slate-200 pl-9 pr-8 rounded-xl text-xs sm:text-sm font-medium text-slate-700 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 transition-all cursor-pointer appearance-none truncate"
              value={deptFilter}
              onChange={(e) => setDeptFilter(e.target.value)}
            >
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
            <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {setSortBy && (
            <div className="relative md:w-44">
              <label htmlFor="job-sort-select" className="sr-only">
                Sort positions
              </label>
              <ArrowUpDown className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                id="job-sort-select"
                aria-label="Sort positions"
                className="w-full h-10 bg-slate-50/70 border border-slate-200 pl-9 pr-8 rounded-xl text-xs sm:text-sm font-medium text-slate-700 focus:outline-none focus:border-[#D10043] focus:bg-white focus:ring-3 focus:ring-[#D10043]/10 transition-all cursor-pointer appearance-none truncate"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as JobSortOption)}
              >
                <option value="newest">Newest First</option>
                <option value="applicants">Most Applicants</option>
                <option value="title">Title (A–Z)</option>
              </select>
              <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          )}
        </div>
      </div>

      {/* Active Filters & Results Count Strip */}
      {(totalFiltered !== undefined || hasActiveFilters) && (
        <div className="px-4 sm:px-5 py-2.5 bg-slate-50/60 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs rounded-b-2xl">
          <div className="flex flex-wrap items-center gap-2">
            {totalFiltered !== undefined && totalCount !== undefined && (
              <span className="text-slate-500">
                Showing <strong className="font-semibold text-slate-900 tabular-nums">{totalFiltered}</strong> of{' '}
                <strong className="font-semibold text-slate-900 tabular-nums">{totalCount}</strong> position
                {totalCount === 1 ? '' : 's'}
              </span>
            )}
            {deptFilter !== 'All Departments' && (
              <button
                type="button"
                onClick={() => setDeptFilter('All Departments')}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white text-slate-700 border border-slate-200 font-medium hover:border-slate-300 transition-colors cursor-pointer"
              >
                <span>Dept: {deptFilter}</span>
                <X size={12} className="text-slate-400" />
              </button>
            )}
            {customWeightsOnly && setCustomWeightsOnly && (
              <button
                type="button"
                onClick={() => setCustomWeightsOnly(false)}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#D10043]/10 text-[#D10043] border border-[#D10043]/20 font-medium hover:bg-[#D10043]/15 transition-colors cursor-pointer"
              >
                <span>Custom Weights</span>
                <X size={12} />
              </button>
            )}
          </div>

          {hasActiveFilters && onResetFilters && (
            <button
              type="button"
              onClick={onResetFilters}
              className="inline-flex items-center gap-1 text-xs font-semibold text-[#D10043] hover:text-[#B00038] transition-colors cursor-pointer"
            >
              <RotateCcw size={12} />
              <span>Reset filters</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default JobSearchAndFilter;
