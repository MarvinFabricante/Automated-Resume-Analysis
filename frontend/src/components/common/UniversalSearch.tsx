import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import { filterAndRankJobs } from '../../utils/jobSearch';
import { 
  useGetJobsQuery, 
  useGetCandidateApplicationsQuery,
  useUniversalSearchHRQuery
} from '../../redux/api/apiSlice';
import {
  Search,
  X,
  Briefcase,
  MapPin,
  Building2,
  FileText,
  Clock,
  ArrowRight,
  Command,
  User,
  Users,
  Layers,
  Sparkles,
  Loader2
} from 'lucide-react';

interface UniversalSearchProps {
  isMobileExpanded?: boolean;
  onCloseMobile?: () => void;
  className?: string;
}

interface SearchResultItem {
  id: string;
  type: 'job' | 'application' | 'hr-applicant' | 'hr-job' | 'hr-shortlist';
  category: 'Applicants' | 'Jobs' | 'Shortlists' | 'My Applications';
  title: string;
  subtitle: string;
  tag?: string;
  tagColor?: string;
  location?: string;
  url: string;
  data: any;
}

const UniversalSearch: React.FC<UniversalSearchProps> = ({
  isMobileExpanded = false,
  onCloseMobile,
  className = ''
}) => {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  const { user: userEmail, role: userRole } = useSelector((state: RootState) => state.auth);
  const normRole = (userRole || '').toUpperCase();
  const isCandidate = normRole === 'CANDIDATE';
  const isHR = normRole === 'HR' || normRole === 'ADMIN';

  // Fetch jobs (cached via RTK query)
  const { data: rawJobs = [], isLoading: isLoadingJobs } = useGetJobsQuery(undefined, {
    skip: isHR && !debouncedQuery,
  });

  // Fetch candidate applications if logged in as candidate
  const { data: candidateApps = [] } = useGetCandidateApplicationsQuery(userEmail || '', {
    skip: !isCandidate || !userEmail
  });

  // HR Universal Search (searches Applicants, Jobs, Shortlists on the server)
  const { data: hrSearchData, isFetching: isFetchingHR } = useUniversalSearchHRQuery(
    debouncedQuery,
    { skip: !isHR || !debouncedQuery || debouncedQuery.length < 1 }
  );

  // Debounce query
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, 120);
    return () => clearTimeout(handler);
  }, [query]);

  // Global hotkeys: '/' and 'Ctrl+K' / 'Cmd+K'
  useEffect(() => {
    const handleGlobalKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInputActive =
        activeEl instanceof HTMLInputElement ||
        activeEl instanceof HTMLTextAreaElement ||
        (activeEl as HTMLElement)?.isContentEditable;

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
        return;
      }

      if (e.key === '/' && !isInputActive) {
        e.preventDefault();
        inputRef.current?.focus();
        setIsOpen(true);
      }
    };

    window.addEventListener('keydown', handleGlobalKeyDown);
    return () => window.removeEventListener('keydown', handleGlobalKeyDown);
  }, []);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Build items based on role
  const results = useMemo<SearchResultItem[]>(() => {
    if (!debouncedQuery) return [];
    const q = debouncedQuery.toLowerCase();

    // ─── HR & ADMIN UNIVERSAL SEARCH RESULTS ───
    if (isHR && hrSearchData) {
      const items: SearchResultItem[] = [];

      // 1. Applicants
      if (Array.isArray(hrSearchData.applicants)) {
        for (const app of hrSearchData.applicants) {
          items.push({
            id: `hr-applicant-${app.id || app.email}`,
            type: 'hr-applicant',
            category: 'Applicants',
            title: app.name || 'Candidate',
            subtitle: `${app.position || 'Applicant'} • ${app.email}`,
            tag: app.status || 'Submitted',
            tagColor: app.status === 'Shortlisted' ? 'bg-purple-50 text-purple-700' : 'bg-rose-50 text-[#D60041]',
            url: `/hr/applicant/${encodeURIComponent(app.email)}`,
            data: app,
          });
        }
      }

      // 2. Jobs
      if (Array.isArray(hrSearchData.jobs)) {
        for (const j of hrSearchData.jobs) {
          items.push({
            id: `hr-job-${j.id}`,
            type: 'hr-job',
            category: 'Jobs',
            title: j.job_title || 'Position',
            subtitle: `${j.department || 'General'} • ${j.location || 'Mariwasa'}`,
            tag: `${j.applicant_count || 0} applicants`,
            tagColor: 'bg-blue-50 text-blue-700',
            url: `/hr/screening?job=${encodeURIComponent(j.job_title)}`,
            data: j,
          });
        }
      }

      // 3. Shortlists
      if (Array.isArray(hrSearchData.shortlists)) {
        for (const s of hrSearchData.shortlists) {
          items.push({
            id: `hr-shortlist-${s.id}`,
            type: 'hr-shortlist',
            category: 'Shortlists',
            title: s.name || 'Shortlist Roster',
            subtitle: `Position: ${s.job_title || 'General'}`,
            tag: `${s.total_candidates || 0} candidates`,
            tagColor: 'bg-emerald-50 text-emerald-700',
            url: `/hr/screening?tab=shortlists&rosterId=${s.id}`,
            data: s,
          });
        }
      }

      return items;
    }

    // ─── CANDIDATE SEARCH RESULTS ───
    const activeJobs = rawJobs.filter((job: any) => job.is_active !== false);
    const rankedJobs = filterAndRankJobs(activeJobs, debouncedQuery);
    const matchedJobs: SearchResultItem[] = rankedJobs.slice(0, 10).map((job: any) => {
      const jobId = String(job.job_id || job.id || '');
      return {
        id: `job-${jobId}`,
        type: 'job',
        category: 'Jobs',
        title: job.job_title || job.title || 'Untitled Role',
        subtitle: `${job.department || 'Mariwasa Siam Ceramics'} • ${job.location || 'Sto. Tomas, Batangas'}`,
        location: job.location || 'Sto. Tomas, Batangas',
        tag: job.job_type || 'Full-Time',
        tagColor: 'bg-slate-100 text-slate-700',
        url: `/job-details/${jobId}`,
        data: job,
      };
    });

    const matchedApps: SearchResultItem[] = [];
    if (isCandidate && Array.isArray(candidateApps)) {
      for (const app of candidateApps) {
        const role = (app.role || app.preferredJob || '').toLowerCase();
        const status = (app.status || '').toLowerCase();
        const comp = (app.company || '').toLowerCase();

        const matchesApp =
          q.length === 1
            ? role.startsWith(q) || role.split(/[\s,;/()\-–—]+/).some((w: string) => w.startsWith(q))
            : role.includes(q) || status.includes(q) || comp.includes(q);

        if (matchesApp) {
          matchedApps.push({
            id: `app-${app.id}`,
            type: 'application',
            category: 'My Applications',
            title: app.role || app.preferredJob || 'Application',
            subtitle: `Applied ${app.appliedDate || 'recently'}`,
            tag: app.status || 'Submitted',
            tagColor: app.statusColor || 'bg-pink-50 text-[#D10043]',
            url: `/candidate/applicationtracking`,
            data: app
          });
        }
        if (matchedApps.length >= 3) break;
      }
    }

    return [...matchedJobs, ...matchedApps];
  }, [debouncedQuery, rawJobs, candidateApps, isCandidate, isHR, hrSearchData]);

  // Reset selected index when query changes
  useEffect(() => {
    setSelectedIndex(-1);
  }, [debouncedQuery]);

  const handleSelectResult = (item: SearchResultItem) => {
    setIsOpen(false);
    setQuery('');
    if (onCloseMobile) onCloseMobile();
    navigate(item.url, { state: item.type === 'job' ? { job: item.data } : undefined });
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
      if (onCloseMobile) onCloseMobile();
      return;
    }

    if (e.key === 'Enter') {
      const trimmed = query.trim();
      if (!trimmed) return;
      e.preventDefault();

      if (isOpen && selectedIndex >= 0 && selectedIndex < results.length) {
        handleSelectResult(results[selectedIndex]);
        return;
      }

      if (!isHR) {
        const targetUrl = isCandidate
          ? `/candidate/findjobs?search=${encodeURIComponent(trimmed)}`
          : `/careerspage`;
        setIsOpen(false);
        setQuery('');
        if (onCloseMobile) onCloseMobile();
        navigate(targetUrl);
        return;
      }

      if (results.length > 0) {
        handleSelectResult(results[0]);
      }
      return;
    }

    if (!isOpen || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev < results.length - 1 ? prev + 1 : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev > 0 ? prev - 1 : results.length - 1));
    }
  };

  const totalCandidateJobMatches = useMemo(() => {
    if (!debouncedQuery || isHR) return 0;
    const activeJobs = rawJobs.filter((job: any) => job.is_active !== false);
    return filterAndRankJobs(activeJobs, debouncedQuery).length;
  }, [debouncedQuery, isHR, rawJobs]);

  // Group results by category
  const groupedResults = useMemo(() => {
    const groups: Record<string, SearchResultItem[]> = {};
    for (const item of results) {
      if (!groups[item.category]) groups[item.category] = [];
      groups[item.category].push(item);
    }
    return groups;
  }, [results]);

  const placeholderText = isHR 
    ? "Search applicants, jobs, shortlists... (Press / or Ctrl+K)" 
    : "Search jobs, departments, locations... (Press / or Ctrl+K)";

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Search Input Bar */}
      <div className="relative flex items-center">
        <div className="absolute left-3.5 text-slate-400 pointer-events-none flex items-center">
          {isFetchingHR ? <Loader2 size={16} className="animate-spin text-[#D60041]" /> : <Search size={16} />}
        </div>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholderText}
          aria-label="Universal search"
          className="w-full pl-10 pr-16 py-2.5 bg-slate-50 hover:bg-slate-100/80 focus:bg-white text-xs sm:text-sm text-slate-800 placeholder:text-slate-400 rounded-2xl border border-slate-200/90 focus:border-[#D60041] focus:ring-4 focus:ring-[#D60041]/10 transition-all outline-none"
        />

        {query ? (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              setDebouncedQuery('');
              inputRef.current?.focus();
            }}
            className="absolute right-3 p-1 text-slate-400 hover:text-slate-600 rounded-lg cursor-pointer"
            aria-label="Clear search"
          >
            <X size={14} />
          </button>
        ) : (
          <div className="hidden sm:flex items-center gap-1 absolute right-3 pointer-events-none text-[11px] font-semibold text-slate-400 bg-white border border-slate-200 px-1.5 py-0.5 rounded-md shadow-2xs">
            <span>/</span>
          </div>
        )}
      </div>

      {/* Results Dropdown */}
      {isOpen && debouncedQuery && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-2xl shadow-2xl border border-slate-200/90 overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-150 max-h-[460px] overflow-y-auto">
          {!isHR && isLoadingJobs && results.length === 0 ? (
            <div className="p-8 text-center flex flex-col items-center gap-2">
              <Loader2 size={20} className="animate-spin text-[#D60041]" />
              <p className="text-xs font-semibold text-slate-500">Searching jobs...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-sm font-semibold text-slate-700">No results found</p>
              <p className="text-xs text-slate-400 mt-1">
                We couldn't find anything matching "{debouncedQuery}". Try a different name, job title, or keyword.
              </p>
            </div>
          ) : (
            <div className="py-2 divide-y divide-slate-100">
              {Object.entries(groupedResults).map(([category, items]) => (
                <div key={category} className="py-2">
                  <div className="px-4 py-1 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                    {category === 'Applicants' && <Users size={12} className="text-[#D60041]" />}
                    {category === 'Jobs' && <Briefcase size={12} className="text-blue-500" />}
                    {category === 'Shortlists' && <Layers size={12} className="text-emerald-500" />}
                    <span>{category} ({items.length})</span>
                  </div>

                  <div className="space-y-0.5 mt-1">
                    {items.map((item) => {
                      const flatIndex = results.findIndex(r => r.id === item.id);
                      const isHighlighted = flatIndex === selectedIndex;

                      return (
                        <div
                          key={item.id}
                          onClick={() => handleSelectResult(item)}
                          onMouseEnter={() => setSelectedIndex(flatIndex)}
                          className={`px-4 py-2.5 mx-1.5 rounded-xl cursor-pointer flex items-center justify-between gap-3 transition-colors ${
                            isHighlighted ? 'bg-rose-50/80 text-slate-900' : 'hover:bg-slate-50 text-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200/60 flex items-center justify-center shrink-0">
                              {item.category === 'Applicants' && <User size={15} className="text-slate-600" />}
                              {item.category === 'Jobs' && <Briefcase size={15} className="text-blue-600" />}
                              {item.category === 'Shortlists' && <Layers size={15} className="text-emerald-600" />}
                              {item.category === 'My Applications' && <FileText size={15} className="text-[#D60041]" />}
                            </div>
                            <div className="min-w-0">
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {item.title}
                              </p>
                              <p className="text-[11px] text-slate-500 truncate">
                                {item.subtitle}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {item.tag && (
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${item.tagColor || 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                                {item.tag}
                              </span>
                            )}
                            <ArrowRight size={14} className="text-slate-300" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
              {!isHR && totalCandidateJobMatches > 0 && (
                <div className="p-2 bg-slate-50/70">
                  <button
                    type="button"
                    onClick={() => {
                      const targetUrl = `/candidate/findjobs?search=${encodeURIComponent(debouncedQuery)}`;
                      setIsOpen(false);
                      setQuery('');
                      if (onCloseMobile) onCloseMobile();
                      navigate(targetUrl);
                    }}
                    className="w-full py-2 px-3 rounded-xl text-xs font-bold text-[#D60041] hover:bg-rose-50 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <span>
                      View all {totalCandidateJobMatches} matching job{totalCandidateJobMatches === 1 ? '' : 's'}
                    </span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default UniversalSearch;
