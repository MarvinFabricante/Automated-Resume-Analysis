import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useLocation, useNavigate } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import { filterAndRankJobs, filterAndRankCandidates } from '../../utils/jobSearch';
import { 
  useGetJobsQuery, 
  useGetApplicationsSummaryQuery,
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
  category: 'Jobs' | 'Candidates' | 'Applicants' | 'Shortlists' | 'My Applications';
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
  const location = useLocation();
  const isOnCandidateFindJobs = location.pathname === '/candidate/findjobs';
  const isOnAdminJobManagement = location.pathname === '/admin/jobmanagement';
  const isOnLiveJobPage = isOnCandidateFindJobs || isOnAdminJobManagement;
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState(() => {
    if (
      typeof window !== 'undefined' &&
      (window.location.pathname === '/candidate/findjobs' ||
        window.location.pathname === '/admin/jobmanagement')
    ) {
      return new URLSearchParams(window.location.search).get('search') || '';
    }
    return '';
  });
  const [debouncedQuery, setDebouncedQuery] = useState(query.trim());
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState<number>(-1);

  // Sync navbar input with ?search= when landing on /candidate/findjobs or /admin/jobmanagement
  useEffect(() => {
    if (isOnLiveJobPage && typeof window !== 'undefined') {
      const urlQ = new URLSearchParams(window.location.search).get('search') || '';
      setQuery(urlQ);
      setDebouncedQuery(urlQ.trim());
    }
  }, [isOnLiveJobPage]);

  useEffect(() => {
    const handleSync = (e: Event) => {
      const detail = (e as CustomEvent)?.detail;
      if (detail && detail.source === 'page') {
        const nextQ = String(detail.query ?? '');
        setQuery(nextQ);
        setDebouncedQuery(nextQ.trim());
      }
    };
    window.addEventListener('candidate-job-search', handleSync);
    window.addEventListener('admin-job-search', handleSync);
    return () => {
      window.removeEventListener('candidate-job-search', handleSync);
      window.removeEventListener('admin-job-search', handleSync);
    };
  }, []);

  const syncPageJobSearch = (val: string) => {
    if (!isOnLiveJobPage || typeof window === 'undefined') return;
    const trimmed = val.trim();
    const basePath = isOnAdminJobManagement ? '/admin/jobmanagement' : '/candidate/findjobs';
    const eventName = isOnAdminJobManagement ? 'admin-job-search' : 'candidate-job-search';
    const nextUrl = trimmed
      ? `${basePath}?search=${encodeURIComponent(trimmed)}`
      : basePath;
    window.history.replaceState(window.history.state, '', nextUrl);
    window.dispatchEvent(
      new CustomEvent(eventName, {
        detail: { query: val, source: 'navbar' },
      })
    );
  };

  const { user: userEmail, role: userRole } = useSelector((state: RootState) => state.auth);
  const normRole = (userRole || '').toUpperCase();
  const isCandidate = normRole === 'CANDIDATE';
  const isHR = normRole === 'HR';
  const isAdmin = normRole === 'ADMIN';

  // Fetch jobs (cached via RTK query — preloaded for Candidate, HR, and Admin for instant job search)
  const { data: rawJobs = [], isLoading: isLoadingJobs } = useGetJobsQuery(undefined);

  // Fetch HR applications summary so HR candidate search responds instantaneously alongside server search
  const { data: hrApplicationsSummary = [] } = useGetApplicationsSummaryQuery(undefined, {
    skip: !isHR,
  });

  // Fetch candidate applications if logged in as candidate
  const { data: candidateApps = [] } = useGetCandidateApplicationsQuery(userEmail || '', {
    skip: !isCandidate || !userEmail
  });

  // HR Universal Search (searches Jobs, Candidates/Applicants, Shortlists on the server)
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

    // ─── HR UNIVERSAL SEARCH RESULTS (1. Jobs first — same ranking as Candidate, 2. Candidates under Jobs, 3. Shortlists) ───
    if (isHR) {
      const items: SearchResultItem[] = [];

      // Compute applicant count per job title from summary if not present on job object
      const jobApplicantCounts = new Map<string, number>();
      if (Array.isArray(hrApplicationsSummary)) {
        for (const app of hrApplicationsSummary) {
          const jt = (app.preferredJob || app.job_title || app.applied_job_title || '').toLowerCase().trim();
          if (jt) {
            jobApplicantCounts.set(jt, (jobApplicantCounts.get(jt) || 0) + 1);
          }
        }
      }

      // 1. Jobs (ranked identically to Candidate job search via filterAndRankJobs)
      const jobsSource = rawJobs.length > 0 ? rawJobs : (Array.isArray(hrSearchData?.jobs) ? hrSearchData.jobs : []);
      const rankedHRJobs = filterAndRankJobs(jobsSource, debouncedQuery);

      for (const j of rankedHRJobs.slice(0, 8)) {
        const jobTitle = j.job_title || j.title || 'Position';
        const jobId = j.id ?? j.job_id ?? jobTitle;
        const countFromSummary = jobApplicantCounts.get(jobTitle.toLowerCase().trim());
        const appCount = Number(j.applicant_count ?? countFromSummary ?? 0);

        items.push({
          id: `hr-job-${jobId}`,
          type: 'hr-job',
          category: 'Jobs',
          title: jobTitle,
          subtitle: `${j.department || 'General'} • ${j.location || 'Mariwasa'}`,
          tag: `${appCount} ${appCount === 1 ? 'applicant' : 'applicants'}`,
          tagColor: 'bg-blue-50 text-blue-700 border-blue-200',
          url: `/hr/screeningportal?job=${encodeURIComponent(jobTitle)}`,
          data: j,
        });
      }

      // 2. Candidates (under Jobs — deduplicated by email and ranked via filterAndRankCandidates)
      const combinedCandidatesPool: any[] = [];
      const seenCandidateEmails = new Set<string>();

      const pushCandidateToPool = (c: any) => {
        const emailKey = (c.email || c.candidate_email || '').toLowerCase().trim();
        const nameKey = (c.name || c.candidate_name || '').toLowerCase().trim();
        const dedupeKey = emailKey || `${nameKey}-${c.id}`;
        if (!dedupeKey || seenCandidateEmails.has(dedupeKey)) return;
        seenCandidateEmails.add(dedupeKey);
        combinedCandidatesPool.push(c);
      };

      if (Array.isArray(hrApplicationsSummary)) {
        for (const app of hrApplicationsSummary) {
          pushCandidateToPool(app);
        }
      }
      if (Array.isArray(hrSearchData?.applicants)) {
        for (const app of hrSearchData.applicants) {
          pushCandidateToPool(app);
        }
      }

      const rankedCandidates = filterAndRankCandidates(combinedCandidatesPool, debouncedQuery);
      for (const app of rankedCandidates.slice(0, 8)) {
        const email = app.email || app.candidate_email || '';
        const candidateName = app.name || app.candidate_name || 'Candidate';
        const appliedRole = app.preferredJob || app.position || app.job_title || app.applied_job_title || 'Applicant';
        const matchScore = app.matchScore ?? app.match_score;
        const statusLabel = app.status || 'Submitted';

        items.push({
          id: `hr-applicant-${app.id || email || candidateName}`,
          type: 'hr-applicant',
          category: 'Candidates',
          title: candidateName,
          subtitle: `${appliedRole}${email ? ` • ${email}` : ''}`,
          tag:
            typeof matchScore === 'number' && matchScore > 0
              ? `${Math.round(matchScore)}% Match • ${statusLabel}`
              : statusLabel,
          tagColor:
            statusLabel === 'Shortlisted'
              ? 'bg-purple-50 text-purple-700 border-purple-200'
              : 'bg-rose-50 text-[#D60041] border-rose-200',
          url: email
            ? `/hr/applicant/${encodeURIComponent(email)}`
            : `/hr/screeningportal?search=${encodeURIComponent(candidateName)}`,
          data: app,
        });
      }

      // 3. Shortlists
      if (Array.isArray(hrSearchData?.shortlists)) {
        for (const s of hrSearchData.shortlists) {
          items.push({
            id: `hr-shortlist-${s.id}`,
            type: 'hr-shortlist',
            category: 'Shortlists',
            title: s.name || 'Shortlist Roster',
            subtitle: `Position: ${s.job_title || 'General'}`,
            tag: `${s.total_candidates ?? s.candidate_count ?? 0} candidates`,
            tagColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
            url: `/hr/screeningportal?tab=shortlists&rosterId=${s.id}`,
            data: s,
          });
        }
      }

      return items;
    }

    // ─── ADMIN JOB SEARCH RESULTS (mirrors candidate job search, routed to /admin/jobmanagement) ───
    if (isAdmin) {
      const rankedAdminJobs = filterAndRankJobs(rawJobs, debouncedQuery);
      return rankedAdminJobs.slice(0, 10).map((job: any) => {
        const jobId = String(job.job_id || job.id || '');
        const jobTitle = job.job_title || job.title || 'Untitled Role';
        const appCount = Number(job.applicant_count ?? 0);
        return {
          id: `admin-job-${jobId}`,
          type: 'job',
          category: 'Jobs',
          title: jobTitle,
          subtitle: `${job.department || 'Mariwasa Siam Ceramics'} • ${job.location || 'Sto. Tomas, Batangas'}`,
          location: job.location || 'Sto. Tomas, Batangas',
          tag: job.is_active === false
            ? 'Archived'
            : `${appCount} ${appCount === 1 ? 'applicant' : 'applicants'}`,
          tagColor: job.is_active === false
            ? 'bg-slate-100 text-slate-500 border-slate-200'
            : 'bg-blue-50 text-blue-700 border-blue-200',
          url: `/admin/jobmanagement?search=${encodeURIComponent(jobTitle)}&jobId=${encodeURIComponent(jobId)}`,
          data: job,
        };
      });
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
  }, [debouncedQuery, rawJobs, hrApplicationsSummary, candidateApps, isCandidate, isHR, isAdmin, hrSearchData]);

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
        if (isOnLiveJobPage) {
          syncPageJobSearch(trimmed);
          setIsOpen(false);
          return;
        }
        const targetUrl = isAdmin
          ? `/admin/jobmanagement?search=${encodeURIComponent(trimmed)}`
          : isCandidate
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

  const totalJobMatches = useMemo(() => {
    if (!debouncedQuery || isHR) return 0;
    const jobsPool = isAdmin ? rawJobs : rawJobs.filter((job: any) => job.is_active !== false);
    return filterAndRankJobs(jobsPool, debouncedQuery).length;
  }, [debouncedQuery, isHR, isAdmin, rawJobs]);

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
    ? "Search jobs, candidates, shortlists... (Press / or Ctrl+K)" 
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
            const nextVal = e.target.value;
            setQuery(nextVal);
            setIsOpen(true);
            syncPageJobSearch(nextVal);
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
              syncPageJobSearch('');
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

      {/* Results Dropdown (suppressed on /candidate/findjobs and /admin/jobmanagement where matching jobs live-render directly on the page) */}
      {isOpen && debouncedQuery && !isOnLiveJobPage && (
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
                    {category === 'Jobs' && <Briefcase size={12} className="text-blue-500" />}
                    {(category === 'Candidates' || category === 'Applicants') && <Users size={12} className="text-[#D60041]" />}
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
                              {(item.category === 'Candidates' || item.category === 'Applicants') && <User size={15} className="text-[#D60041]" />}
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
              {!isHR && totalJobMatches > 0 && (
                <div className="p-2 bg-slate-50/70">
                  <button
                    type="button"
                    onClick={() => {
                      const targetUrl = isAdmin
                        ? `/admin/jobmanagement?search=${encodeURIComponent(debouncedQuery)}`
                        : `/candidate/findjobs?search=${encodeURIComponent(debouncedQuery)}`;
                      setIsOpen(false);
                      setQuery('');
                      if (onCloseMobile) onCloseMobile();
                      navigate(targetUrl);
                    }}
                    className="w-full py-2 px-3 rounded-xl text-xs font-bold text-[#D60041] hover:bg-rose-50 transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <span>
                      View all {totalJobMatches} matching job{totalJobMatches === 1 ? '' : 's'}
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
