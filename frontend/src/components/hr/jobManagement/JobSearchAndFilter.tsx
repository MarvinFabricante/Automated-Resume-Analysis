import React from 'react';
import { Search, Filter } from 'lucide-react';

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
    <div className="bg-white p-8 rounded-[32px] border border-gray-100 shadow-sm mb-8 flex flex-col md:flex-row gap-5">
      <div className="relative flex-grow">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none z-10">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        <input
          type="text"
          placeholder="Search by title or job ID..."
          className="w-full pl-11 pr-4 py-3.5 bg-gray-50/50 border-2 border-gray-100 rounded-2xl text-sm font-medium focus:outline-none focus:border-pink-100 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-300 relative z-10"
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
                className="px-5 py-3 hover:bg-pink-50 hover:text-[#D60041] cursor-pointer text-sm font-semibold transition-colors flex items-center gap-3"
                onClick={() => {
                  setSearchQuery(title);
                  setShowSuggestions(false);
                }}
              >
                <Search className="h-4 w-4 text-gray-300" />
                {title}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="relative w-full md:w-56 shrink-0">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Filter className="h-4 w-4 text-gray-400" />
        </div>
        <select
          className="w-full bg-gray-50/50 border-2 border-gray-100 pl-11 pr-10 py-3.5 rounded-2xl text-sm font-bold text-gray-700 focus:outline-none focus:border-pink-100 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-300 cursor-pointer appearance-none"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="All Status">All Statuses</option>
          <option value="Active">Active Jobs</option>
          <option value="Inactive">Inactive Jobs</option>
        </select>
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
          <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
          </svg>
        </div>
      </div>

      <div className="relative w-full md:w-64 shrink-0">
        <select
          className="w-full bg-gray-50/50 border-2 border-gray-100 pl-4 pr-10 py-3.5 rounded-2xl text-sm font-bold text-gray-700 focus:outline-none focus:border-pink-100 focus:bg-white focus:ring-4 focus:ring-pink-50 transition-all duration-300 cursor-pointer appearance-none"
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
        >
          {departments.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
        <div className="absolute inset-y-0 right-0 pr-4 flex items-center pointer-events-none">
          <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
          </svg>
        </div>
      </div>
    </div>
  );
};

export default JobSearchAndFilter;
