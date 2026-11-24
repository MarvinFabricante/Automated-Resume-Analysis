import React, { useState, useMemo, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useSearchParams } from '@/utils/navigation';
import {
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  X,
  Briefcase,
  Archive,
  Users,
  Sliders,
  Sparkles,
  Trash2,
} from 'lucide-react';

// Layout components
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import JobManagementHeader from '../../components/hr/jobManagement/JobManagementHeader';
import JobSearchAndFilter, {
  JobSortOption,
  JobViewMode,
} from '../../components/hr/jobManagement/JobSearchAndFilter';
import JobList from '../../components/hr/jobManagement/JobList';

// Modals
import CreateJobModal from '../../components/modals/hr/CreateJobModal';
import EditJobModal from '../../components/modals/hr/EditJobModal';
import ViewJobDetailsModal from '../../components/modals/hr/ViewJobDetailsModal';
import { areWeightsEqual } from '../../components/modals/hr/JobScoringWeightsEditor';

import {
  useGetJobsQuery,
  useLazyGetJobClosePreviewQuery,
  useChangeJobStatusMutation,
  useDeleteJobMutation,
} from '../../redux/api/apiSlice';
import { Job, DEFAULT_JOB_SCORING_WEIGHTS } from '../../types';
import { filterAndRankJobs } from '../../utils/jobSearch';

interface ToastState {
  message: string;
  type: 'success' | 'error';
}

interface ConfirmModalState {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: 'archive' | 'delete';
  onConfirm: (() => void) | null;
}

interface ModalState {
  type: 'create' | 'edit' | 'view' | null;
  selectedJob: Job | null;
}

const JobManagementPage: React.FC = () => {
  const [showArchived, setShowArchived] = useState<boolean>(false);
  // RTK Query hook handles fetching, loading, error, and caching!
  const { data: jobs = [], isLoading, error: queryError } = useGetJobsQuery({
    include_inactive: true,
    include_archived: showArchived,
  });
  const error = queryError ? "Failed to sync with database. Please try again later." : null;

  const [triggerClosePreview] = useLazyGetJobClosePreviewQuery();
  const [changeJobStatus] = useChangeJobStatusMutation();
  const [deleteJob] = useDeleteJobMutation();

  // Custom Toast Notification State
  const [toast, setToast] = useState<ToastState | null>(null);

  // Custom Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState<ConfirmModalState>({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null
  });

  const showToastMessage = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  const handleCloseJob = async (jobId: number | string | undefined, jobTitle: string) => {
    if (!jobId) return;
    let affectedCount = 0;
    let protectedCount = 0;
    try {
      const preview = await triggerClosePreview(jobId).unwrap();
      affectedCount = Number(preview?.affected_count ?? 0);
      protectedCount = Number(preview?.protected_count ?? 0);
    } catch {
      // fallback if preview fails
    }
    const impactLine =
      affectedCount > 0
        ? `${affectedCount} non-shortlisted applicant(s) will automatically be set to Not Selected (reason: "Position closed") and notified once.`
        : 'No non-shortlisted applicants will be set to Not Selected.';
    const protectedLine =
      protectedCount > 0
        ? ` ${protectedCount} shortlisted or in-interview applicant(s) will continue undisturbed.`
        : '';

    setConfirmModal({
      isOpen: true,
      title: `Close "${jobTitle}"`,
      message: `Closing this position stops new applications immediately. ${impactLine}${protectedLine} You can still reopen a Closed job later.`,
      confirmLabel: 'Close Job Opening',
      variant: 'archive',
      onConfirm: async () => {
        try {
          const res = await changeJobStatus({ jobId, status: 'CLOSED' }).unwrap();
          const count = Number(res?.auto_not_selected_count ?? 0);
          showToastMessage(
            count > 0
              ? `Closed "${jobTitle}". ${count} non-shortlisted applicant(s) set to Not Selected.`
              : `Job "${jobTitle}" closed successfully.`,
            'success'
          );
        } catch (err: any) {
          showToastMessage(err?.data?.detail || "Failed to close job.", 'error');
        }
      },
    });
  };

  const handleReopenJob = async (jobId: number | string | undefined, jobTitle: string) => {
    if (!jobId) return;
    try {
      await changeJobStatus({ jobId, status: 'ACTIVE' }).unwrap();
      showToastMessage(`Job "${jobTitle}" reopened and is now Active.`, 'success');
    } catch (err: any) {
      showToastMessage(err?.data?.detail || "Failed to reopen job.", 'error');
    }
  };

  const handlePublishJob = async (jobId: number | string | undefined, jobTitle: string) => {
    if (!jobId) return;
    try {
      await changeJobStatus({ jobId, status: 'ACTIVE' }).unwrap();
      showToastMessage(`Job "${jobTitle}" published and is now Active.`, 'success');
    } catch (err: any) {
      showToastMessage(err?.data?.detail || "Failed to publish job.", 'error');
    }
  };

  const handleArchiveJob = async (jobId: number | string | undefined, jobTitle: string) => {
    if (!jobId) return;
    setConfirmModal({
      isOpen: true,
      title: 'Archive Position',
      message: `Are you sure you want to archive "${jobTitle}"? Archived jobs are hidden from normal lists and applicant views (kept in reports and analytics) and cannot be reopened.`,
      confirmLabel: 'Archive Position',
      variant: 'archive',
      onConfirm: async () => {
        try {
          await changeJobStatus({ jobId, status: 'ARCHIVED' }).unwrap();
          showToastMessage(`Job "${jobTitle}" archived successfully.`, 'success');
        } catch (err: any) {
          console.error("Failed to archive job:", err);
          showToastMessage(err?.data?.detail || "Failed to archive job. Please try again.", 'error');
        }
      }
    });
  };

  const handleUnarchiveJob = async (jobId: number | string | undefined, jobTitle: string) => {
    return handleReopenJob(jobId, jobTitle);
  };

  const handleDeleteJob = async (jobId: number | string, jobTitle: string) => {
    setConfirmModal({
      isOpen: true,
      title: 'Delete Position Permanently',
      message: `Are you sure you want to permanently remove "${jobTitle}"? This action cannot be undone and will delete all associated applications.`,
      confirmLabel: 'Delete Permanently',
      variant: 'delete',
      onConfirm: async () => {
        try {
          await deleteJob(jobId).unwrap();
          showToastMessage(`Job "${jobTitle}" removed successfully!`, 'success');
        } catch (error) {
          console.error("Failed to delete job:", error);
          showToastMessage("Failed to delete job. Please try again.", 'error');
        }
      }
    });
  };

  const [searchParams] = useSearchParams();
  const urlSearch = searchParams.get('search') || '';
  const urlJobId = searchParams.get('jobId') || '';

  // Filter & Presentation States
  const [searchQuery, setSearchQuery] = useState<string>(urlSearch);

  useEffect(() => {
    setSearchQuery(urlSearch);
  }, [urlSearch]);

  useEffect(() => {
    const handleNavbarSearch = (e: Event) => {
      const detail = (e as CustomEvent)?.detail;
      if (detail && detail.source === 'navbar') {
        setSearchQuery(String(detail.query ?? ''));
      }
    };
    const handlePopState = () => {
      const nextQ = new URLSearchParams(window.location.search).get('search') || '';
      setSearchQuery(nextQ);
    };
    window.addEventListener('admin-job-search', handleNavbarSearch);
    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('admin-job-search', handleNavbarSearch);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const updateSearchQuery = (val: string) => {
    setSearchQuery(val);
    if (typeof window !== 'undefined') {
      const trimmed = val.trim();
      const nextUrl = trimmed
        ? `/admin/jobmanagement?search=${encodeURIComponent(trimmed)}`
        : '/admin/jobmanagement';
      window.history.replaceState(window.history.state, '', nextUrl);
      window.dispatchEvent(
        new CustomEvent('admin-job-search', {
          detail: { query: val, source: 'page' },
        })
      );
    }
  };
  const [statusFilter, setStatusFilter] = useState<string>("All Status");
  const [deptFilter, setDeptFilter] = useState<string>("All Departments");
  const [customWeightsOnly, setCustomWeightsOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<JobSortOption>("newest");
  const [viewMode, setViewMode] = useState<JobViewMode>("cards");
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);

  const [modalState, setModalState] = useState<ModalState>({
    type: null,
    selectedJob: null
  });

  // Open job details modal when navigated directly from UniversalSearch with ?jobId=
  useEffect(() => {
    if (!urlJobId || !(jobs as Job[]).length) return;
    const matched = (jobs as Job[]).find(
      (j) => String(j.job_id || j.id) === urlJobId || String(j.id) === urlJobId
    );
    if (matched) {
      setModalState({ type: 'view', selectedJob: matched });
      if (typeof window !== 'undefined') {
        const params = new URLSearchParams(window.location.search);
        params.delete('jobId');
        const nextQuery = params.toString();
        const nextUrl = nextQuery ? `/admin/jobmanagement?${nextQuery}` : '/admin/jobmanagement';
        window.history.replaceState(window.history.state, '', nextUrl);
      }
    }
  }, [urlJobId, jobs]);

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const itemsPerPage = viewMode === 'table' ? 15 : 10;

  const metrics = useMemo(() => {
    const allJobs = jobs as Job[];
    const getSt = (j: Job) => (j.status || (j.is_active ? 'ACTIVE' : 'ARCHIVED')).toUpperCase();
    const total = allJobs.length;
    const active = allJobs.filter((j) => getSt(j) === 'ACTIVE').length;
    const closed = allJobs.filter((j) => getSt(j) === 'CLOSED').length;
    const draft = allJobs.filter((j) => getSt(j) === 'DRAFT').length;
    const archived = allJobs.filter((j) => getSt(j) === 'ARCHIVED').length;
    const totalApplicants = allJobs.reduce((sum, j) => sum + Number(j.applicant_count ?? 0), 0);
    const customWeighted = allJobs.filter(
      (j) => Boolean(j.scoring_weights) && !areWeightsEqual(j.scoring_weights!, DEFAULT_JOB_SCORING_WEIGHTS)
    ).length;
    return { total, active, closed, draft, archived, totalApplicants, customWeighted };
  }, [jobs]);

  const departments = useMemo(() => {
    const defaults = [
      "Human Resources",
      "Engineering",
      "Information Technology",
      "Marketing",
      "Finance",
      "Operations",
      "Quality Assurance",
      "Maintenance",
      "Environmental",
    ];
    const fromJobs = (jobs as Job[])
      .map((j) => (j.department || "").trim())
      .filter(Boolean);
    return ["All Departments", ...Array.from(new Set([...defaults, ...fromJobs]))];
  }, [jobs]);

  const closeModal = () => setModalState({ type: null, selectedJob: null });

  const handleMutationSuccess = () => {
    closeModal();
  };

  const resetAllFilters = () => {
    updateSearchQuery("");
    setStatusFilter("All Status");
    setDeptFilter("All Departments");
    setCustomWeightsOnly(false);
    setSortBy("newest");
  };

  const suggestions = useMemo(() => {
    const q = searchQuery.trim();
    if (!q) return [];
    const ranked = filterAndRankJobs(jobs as Job[], q);
    const seen = new Set<string>();
    const out: string[] = [];
    for (const job of ranked) {
      const title = (job.job_title || job.title || "").trim();
      if (title && !seen.has(title.toLowerCase())) {
        seen.add(title.toLowerCase());
        out.push(title);
        if (out.length >= 5) break;
      }
    }
    return out;
  }, [jobs, searchQuery]);

  const filteredJobs = useMemo(() => {
    const q = searchQuery.trim();
    const rankedBySearch = q ? filterAndRankJobs(jobs as Job[], q) : (jobs as Job[]);

    // Also include direct job_id / id matches if not already in rankedBySearch
    const searchMatched = q
      ? (() => {
          const ql = q.toLowerCase();
          const seenIds = new Set(rankedBySearch.map((j) => j.id));
          const idMatches = (jobs as Job[]).filter(
            (j) =>
              !seenIds.has(j.id) &&
              (j.job_id || String(j.id) || "").toLowerCase().includes(ql)
          );
          return [...rankedBySearch, ...idMatches];
        })()
      : rankedBySearch;

    const list = searchMatched.filter(job => {
      const st = (job.status || (job.is_active ? 'ACTIVE' : 'ARCHIVED')).toUpperCase();
      const matchesStatus =
        statusFilter === "All Status" ||
        (statusFilter === "Active" && st === 'ACTIVE') ||
        (statusFilter === "Closed" && st === 'CLOSED') ||
        (statusFilter === "Draft" && st === 'DRAFT') ||
        (statusFilter === "Inactive" && (st === 'ARCHIVED' || st === 'CLOSED'));

      const matchesDept = deptFilter === "All Departments" ||
        job.department === deptFilter;

      const isCustom = Boolean(job.scoring_weights) &&
        !areWeightsEqual(job.scoring_weights!, DEFAULT_JOB_SCORING_WEIGHTS);
      const matchesWeights = !customWeightsOnly || isCustom;

      return matchesStatus && matchesDept && matchesWeights;
    });

    if (sortBy === 'applicants') {
      return [...list].sort((a, b) => Number(b.applicant_count ?? 0) - Number(a.applicant_count ?? 0));
    }
    if (sortBy === 'title') {
      return [...list].sort((a, b) => (a.job_title || a.title || '').localeCompare(b.job_title || b.title || ''));
    }
    // Preserve relevance order when actively searching, otherwise newest first
    if (q) {
      return list;
    }
    return [...list].sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : Number(a.id || 0);
      const dateB = b.created_at ? new Date(b.created_at).getTime() : Number(b.id || 0);
      return dateB - dateA;
    });
  }, [jobs, searchQuery, statusFilter, deptFilter, customWeightsOnly, sortBy]);

  const handleExportCSV = () => {
    if (filteredJobs.length === 0) return;
    const headers = ['Job ID', 'Title', 'Department', 'Location', 'Type', 'Salary', 'Applicants', 'Status'];
    const escape = (val: unknown) => `"${String(val ?? '').replace(/"/g, '""')}"`;
    const rows = filteredJobs.map((j) => [
      escape(j.job_id || j.id),
      escape(j.job_title || j.title),
      escape(j.department),
      escape(j.location),
      escape(j.job_type || j.employment_type),
      escape(j.salary_range),
      Number(j.applicant_count ?? 0),
      escape(j.is_active ? 'Active' : 'Archived'),
    ].join(','));
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `job-postings-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
    showToastMessage(`Exported ${filteredJobs.length} job posting(s) to CSV.`, 'success');
  };

  // Handle page reset on filter change
  const [prevFilters, setPrevFilters] = useState({ searchQuery, statusFilter, deptFilter, customWeightsOnly, sortBy, viewMode });
  if (
    prevFilters.searchQuery !== searchQuery ||
    prevFilters.statusFilter !== statusFilter ||
    prevFilters.deptFilter !== deptFilter ||
    prevFilters.customWeightsOnly !== customWeightsOnly ||
    prevFilters.sortBy !== sortBy ||
    prevFilters.viewMode !== viewMode
  ) {
    setPrevFilters({ searchQuery, statusFilter, deptFilter, customWeightsOnly, sortBy, viewMode });
    setCurrentPage(1);
  }

  // Scroll to top when page changes
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [currentPage]);

  const totalPages = Math.ceil(filteredJobs.length / itemsPerPage);
  const paginatedJobs = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredJobs.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredJobs, currentPage, itemsPerPage]);

  const handlePrevPage = () => setCurrentPage(prev => Math.max(prev - 1, 1));
  const handleNextPage = () => setCurrentPage(prev => Math.min(prev + 1, totalPages));

  return (
    <div className="bg-[#FAFAFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col relative">
      <div className="absolute top-0 left-0 w-full h-[300px] bg-gradient-to-b from-[#D10043]/5 via-[#D10043]/2 to-transparent pointer-events-none z-0" />

      <Helmet><title>Job Management | Mariwasa Recruitment Admin Portal</title></Helmet>
      <Header />

      {/* Top-Right Floating Toast Notification */}
      {toast && (
        <div className="fixed top-20 right-6 z-50 flex items-center gap-3 px-4 py-3 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl border border-gray-100 text-sm font-semibold transition-all duration-300 animate-in fade-in slide-in-from-top-3">
          {toast.type === 'success' ? (
            <CheckCircle2 className="text-emerald-500 shrink-0" size={20} />
          ) : (
            <AlertCircle className="text-rose-500 shrink-0" size={20} />
          )}
          <span className="text-gray-800">{toast.message}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            className="text-gray-400 hover:text-gray-600 p-1 rounded-lg transition-colors ml-2 cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>
      )}

      <div className="flex flex-1 relative">
        <Sidebar />
        <main className="flex-1 min-w-0 max-w-[1500px] mx-auto px-4 sm:px-8 lg:px-10 py-8 sm:py-10 w-full overflow-x-hidden flex flex-col gap-6 animate-in fade-in duration-500">
          <JobManagementHeader
            onCreateJob={() => setModalState({ type: 'create', selectedJob: null })}
            onExportCsv={handleExportCSV}
            canExport={filteredJobs.length > 0}
          />

          {/* Executive KPI Summary Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            <button
              type="button"
              onClick={() => {
                setStatusFilter("All Status");
                setCustomWeightsOnly(false);
              }}
              className={`text-left p-4 rounded-2xl border bg-white transition-all cursor-pointer group ${
                statusFilter === "All Status" && !customWeightsOnly
                  ? "border-[#D10043]/60 ring-2 ring-[#D10043]/10 shadow-xs"
                  : "border-slate-200/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Total Positions
                </span>
                <span className="p-1.5 rounded-lg bg-slate-100 text-slate-600">
                  <Briefcase size={14} />
                </span>
              </div>
              <div className="text-2xl font-bold text-slate-900 tabular-nums">
                {isLoading ? '—' : metrics.total}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">All job requisitions</div>
            </button>

            <button
              type="button"
              onClick={() => {
                setStatusFilter("Active");
                setCustomWeightsOnly(false);
              }}
              className={`text-left p-4 rounded-2xl border bg-white transition-all cursor-pointer group ${
                statusFilter === "Active" && !customWeightsOnly
                  ? "border-emerald-500/60 ring-2 ring-emerald-500/10 shadow-xs"
                  : "border-slate-200/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider">
                  Active
                </span>
                <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
                  <Sparkles size={14} />
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900 tabular-nums">
                  {isLoading ? '—' : metrics.active}
                </span>
                {!isLoading && metrics.total > 0 && (
                  <span className="text-[11px] font-semibold text-emerald-600 tabular-nums">
                    {Math.round((metrics.active / metrics.total) * 100)}%
                  </span>
                )}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">Live on careers page</div>
            </button>

            <button
              type="button"
              onClick={() => {
                setStatusFilter("Inactive");
                setCustomWeightsOnly(false);
              }}
              className={`text-left p-4 rounded-2xl border bg-white transition-all cursor-pointer group ${
                statusFilter === "Inactive" && !customWeightsOnly
                  ? "border-slate-400 ring-2 ring-slate-400/15 shadow-xs"
                  : "border-slate-200/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  Archived
                </span>
                <span className="p-1.5 rounded-lg bg-slate-100 text-slate-600">
                  <Archive size={14} />
                </span>
              </div>
              <div className="text-2xl font-bold text-slate-900 tabular-nums">
                {isLoading ? '—' : metrics.archived}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">Closed or paused roles</div>
            </button>

            <button
              type="button"
              onClick={() => setSortBy(sortBy === 'applicants' ? 'newest' : 'applicants')}
              className={`text-left p-4 rounded-2xl border bg-white transition-all cursor-pointer group ${
                sortBy === 'applicants'
                  ? "border-indigo-400 ring-2 ring-indigo-500/10 shadow-xs"
                  : "border-slate-200/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-indigo-700 uppercase tracking-wider">
                  Applicants
                </span>
                <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
                  <Users size={14} />
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold text-slate-900 tabular-nums">
                  {isLoading ? '—' : metrics.totalApplicants}
                </span>
                {!isLoading && metrics.total > 0 && (
                  <span className="text-[11px] font-medium text-slate-400 tabular-nums">
                    ~{Math.round(metrics.totalApplicants / metrics.total)} / role
                  </span>
                )}
              </div>
              <div className="text-[11px] text-indigo-600/80 mt-0.5">
                {sortBy === 'applicants' ? 'Sorted by volume' : 'Click to sort by volume'}
              </div>
            </button>

            <button
              type="button"
              onClick={() => setCustomWeightsOnly((prev) => !prev)}
              className={`col-span-2 sm:col-span-1 text-left p-4 rounded-2xl border bg-white transition-all cursor-pointer group ${
                customWeightsOnly
                  ? "border-[#D10043]/60 ring-2 ring-[#D10043]/10 shadow-xs"
                  : "border-slate-200/80 hover:border-slate-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold text-[#D10043] uppercase tracking-wider">
                  Custom Weights
                </span>
                <span className="p-1.5 rounded-lg bg-[#D10043]/10 text-[#D10043]">
                  <Sliders size={14} />
                </span>
              </div>
              <div className="text-2xl font-bold text-slate-900 tabular-nums">
                {isLoading ? '—' : metrics.customWeighted}
              </div>
              <div className="text-[11px] text-slate-400 mt-0.5">Non-default AI scoring</div>
            </button>
          </div>

          <JobSearchAndFilter
            searchQuery={searchQuery}
            setSearchQuery={updateSearchQuery}
            statusFilter={statusFilter}
            setStatusFilter={setStatusFilter}
            deptFilter={deptFilter}
            setDeptFilter={setDeptFilter}
            departments={departments}
            showSuggestions={showSuggestions}
            setShowSuggestions={setShowSuggestions}
            suggestions={suggestions}
            sortBy={sortBy}
            setSortBy={setSortBy}
            viewMode={viewMode}
            setViewMode={setViewMode}
            customWeightsOnly={customWeightsOnly}
            setCustomWeightsOnly={setCustomWeightsOnly}
            showArchived={showArchived}
            setShowArchived={setShowArchived}
            totalFiltered={filteredJobs.length}
            totalCount={(jobs as Job[]).length}
            statusCounts={{
              all: metrics.total,
              active: metrics.active,
              closed: metrics.closed,
              draft: metrics.draft,
              archived: metrics.archived,
              customWeights: metrics.customWeighted,
            }}
            onResetFilters={resetAllFilters}
          />

          {searchQuery.trim() !== '' && (
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3 bg-white border border-slate-200/80 rounded-2xl px-4 py-3 shadow-xs">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="text-sm sm:text-base font-bold text-slate-900">
                  Results for &ldquo;{searchQuery.trim()}&rdquo;
                </h2>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono text-xs font-bold">
                  {filteredJobs.length}
                </span>
                <span className="text-xs text-slate-500">
                  Showing {filteredJobs.length} matching {filteredJobs.length === 1 ? 'role' : 'roles'} sorted by relevance
                </span>
              </div>
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-rose-50 text-[#D60041] border border-rose-200 text-xs font-bold">
                <span>Search: &ldquo;{searchQuery.trim()}&rdquo;</span>
                <button
                  type="button"
                  aria-label="Clear active search filter"
                  onClick={() => updateSearchQuery('')}
                  className="p-0.5 rounded-full hover:bg-rose-100 cursor-pointer"
                >
                  <X size={13} />
                </button>
              </span>
            </div>
          )}

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  className="bg-white rounded-2xl border border-slate-200/80 p-5 animate-pulse space-y-3"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="space-y-2">
                      <div className="h-5 w-56 bg-slate-200 rounded-md" />
                      <div className="h-3.5 w-72 bg-slate-100 rounded-md" />
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="h-8 w-20 bg-slate-100 rounded-lg" />
                      <div className="h-8 w-16 bg-slate-100 rounded-lg" />
                    </div>
                  </div>
                  <div className="pt-2 border-t border-slate-100 flex justify-between">
                    <div className="h-5 w-48 bg-slate-100 rounded-md" />
                    <div className="h-5 w-32 bg-slate-100 rounded-md" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="bg-rose-50 border border-rose-200 text-rose-700 p-5 rounded-2xl text-center text-sm font-semibold">
              {error}
            </div>
          ) : (
            <>
              <JobList
                jobs={paginatedJobs}
                viewMode={viewMode}
                onEdit={(job) => setModalState({ type: 'edit', selectedJob: job })}
                onView={(job) => setModalState({ type: 'view', selectedJob: job })}
                onCloseJob={handleCloseJob}
                onReopenJob={handleReopenJob}
                onPublishJob={handlePublishJob}
                onArchive={handleArchiveJob}
                onUnarchive={handleUnarchiveJob}
                onDelete={handleDeleteJob}
                onResetFilters={resetAllFilters}
              />

              {/* Enterprise Pagination Controls */}
              {totalPages > 1 && (
                <div className="mt-2 flex flex-col sm:flex-row items-center justify-between gap-3 bg-white px-5 py-3.5 rounded-2xl border border-slate-200/90 shadow-2xs">
                  <div className="text-xs sm:text-sm text-slate-500">
                    Showing{' '}
                    <span className="font-semibold text-slate-900 tabular-nums">
                      {(currentPage - 1) * itemsPerPage + 1}
                    </span>
                    –
                    <span className="font-semibold text-slate-900 tabular-nums">
                      {Math.min(currentPage * itemsPerPage, filteredJobs.length)}
                    </span>{' '}
                    of{' '}
                    <span className="font-semibold text-slate-900 tabular-nums">
                      {filteredJobs.length}
                    </span>{' '}
                    positions
                  </div>

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      onClick={handlePrevPage}
                      disabled={currentPage === 1}
                      className="inline-flex items-center gap-1 h-8 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                    >
                      <ChevronLeft size={14} />
                      <span>Prev</span>
                    </button>

                    <div className="flex items-center gap-1">
                      {Array.from({ length: totalPages }, (_, i) => i + 1)
                        .filter(
                          (page) =>
                            page === 1 ||
                            page === totalPages ||
                            Math.abs(page - currentPage) <= 1
                        )
                        .reduce<Array<number | 'ellipsis'>>((acc, page, idx, arr) => {
                          if (idx > 0 && page - arr[idx - 1] > 1) {
                            acc.push('ellipsis');
                          }
                          acc.push(page);
                          return acc;
                        }, [])
                        .map((item, idx) =>
                          item === 'ellipsis' ? (
                            <span
                              key={`ellipsis-${idx}`}
                              className="px-1.5 text-xs text-slate-400 select-none"
                            >
                              …
                            </span>
                          ) : (
                            <button
                              key={item}
                              type="button"
                              onClick={() => setCurrentPage(item)}
                              aria-current={currentPage === item ? 'page' : undefined}
                              className={`h-8 min-w-[32px] px-2 rounded-lg text-xs font-semibold tabular-nums transition-colors cursor-pointer ${
                                currentPage === item
                                  ? 'bg-[#D10043] text-white shadow-2xs'
                                  : 'bg-white border border-slate-200 text-slate-700 hover:bg-slate-50'
                              }`}
                            >
                              {item}
                            </button>
                          )
                        )}
                    </div>

                    <button
                      type="button"
                      onClick={handleNextPage}
                      disabled={currentPage === totalPages}
                      className="inline-flex items-center gap-1 h-8 px-3 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
                    >
                      <span>Next</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>

      <CreateJobModal
        isOpen={modalState.type === 'create'}
        onClose={closeModal}
        onSuccess={handleMutationSuccess}
      />

      <EditJobModal
        isOpen={modalState.type === 'edit'}
        jobData={modalState.selectedJob}
        onClose={closeModal}
        onSuccess={handleMutationSuccess}
      />

      <ViewJobDetailsModal
        isOpen={modalState.type === 'view'}
        job={modalState.selectedJob}
        onEdit={(job) => setModalState({ type: 'edit', selectedJob: job })}
        onClose={closeModal}
      />

      {/* Confirm Modal */}
      {confirmModal.isOpen && (
        <div className="fixed inset-0 bg-slate-950/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-md rounded-2xl border border-slate-200 shadow-2xl overflow-hidden p-6 sm:p-7 animate-in zoom-in-95 duration-200">
            <div
              className={`flex items-center justify-center w-12 h-12 rounded-xl mb-4 mx-auto border ${
                confirmModal.variant === 'archive'
                  ? 'bg-amber-50 border-amber-200 text-amber-600'
                  : 'bg-rose-50 border-rose-200 text-rose-600'
              }`}
            >
              {confirmModal.variant === 'archive' ? (
                <Archive className="w-5 h-5" />
              ) : (
                <Trash2 className="w-5 h-5" />
              )}
            </div>

            <h3 className="text-base sm:text-lg font-bold text-slate-900 text-center mb-1.5">
              {confirmModal.title}
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 text-center leading-relaxed mb-6">
              {confirmModal.message}
            </p>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                className="flex-1 h-10 px-4 border border-slate-200 text-slate-700 rounded-xl text-xs sm:text-sm font-semibold hover:bg-slate-50 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  if (confirmModal.onConfirm) {
                    confirmModal.onConfirm();
                  }
                  setConfirmModal({ ...confirmModal, isOpen: false });
                }}
                className={`flex-1 h-10 px-4 text-white rounded-xl text-xs sm:text-sm font-semibold transition-colors cursor-pointer ${
                  confirmModal.variant === 'archive'
                    ? 'bg-amber-600 hover:bg-amber-700'
                    : 'bg-rose-600 hover:bg-rose-700'
                }`}
              >
                {confirmModal.confirmLabel || 'Confirm'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobManagementPage;
