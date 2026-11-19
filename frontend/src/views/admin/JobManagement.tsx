import React, { useState, useMemo, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  X,
  Briefcase,
  Archive,
  Users,
  Sliders,
  Sparkles,
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

import { useGetJobsQuery, useArchiveJobMutation, useUnarchiveJobMutation, useDeleteJobMutation } from '../../redux/api/apiSlice';
import { Job, DEFAULT_JOB_SCORING_WEIGHTS } from '../../types';

interface ToastState {
  message: string;
  type: 'success' | 'error';
}

interface ConfirmModalState {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: (() => void) | null;
}

interface ModalState {
  type: 'create' | 'edit' | 'view' | null;
  selectedJob: Job | null;
}

const JobManagementPage: React.FC = () => {
  // RTK Query hook handles fetching, loading, error, and caching!
  const { data: jobs = [], isLoading, error: queryError } = useGetJobsQuery({ include_inactive: true });
  const error = queryError ? "Failed to sync with database. Please try again later." : null;

  const [archiveJob] = useArchiveJobMutation();
  const [unarchiveJob] = useUnarchiveJobMutation();
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

  const handleArchiveJob = async (jobId: number | string, jobTitle: string) => {
    setConfirmModal({
      isOpen: true,
      title: 'Archive Job',
      message: `Are you sure you want to archive "${jobTitle}"? This will close applications on the careers portal.`,
      onConfirm: async () => {
        try {
          await archiveJob(jobId).unwrap();
          showToastMessage(`Job "${jobTitle}" archived successfully!`, 'success');
        } catch (error) {
          console.error("Failed to archive job:", error);
          showToastMessage("Failed to archive job. Please try again.", 'error');
        }
      }
    });
  };

  const handleUnarchiveJob = async (jobId: number | string, jobTitle: string) => {
    try {
      await unarchiveJob(jobId).unwrap();
      showToastMessage(`Job "${jobTitle}" unarchived successfully!`, 'success');
    } catch (error) {
      console.error("Failed to unarchive job:", error);
      showToastMessage("Failed to unarchive job. Please try again.", 'error');
    }
  };

  const handleDeleteJob = async (jobId: number | string, jobTitle: string) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Job',
      message: `Are you sure you want to permanently remove "${jobTitle}"? This action cannot be undone and will delete all associated applications.`,
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

  // Filter & Presentation States
  const [searchQuery, setSearchQuery] = useState<string>("");
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

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const itemsPerPage = viewMode === 'table' ? 15 : 10;

  const metrics = useMemo(() => {
    const allJobs = jobs as Job[];
    const total = allJobs.length;
    const active = allJobs.filter((j) => j.is_active).length;
    const archived = total - active;
    const totalApplicants = allJobs.reduce((sum, j) => sum + Number(j.applicant_count ?? 0), 0);
    const customWeighted = allJobs.filter(
      (j) => Boolean(j.scoring_weights) && !areWeightsEqual(j.scoring_weights!, DEFAULT_JOB_SCORING_WEIGHTS)
    ).length;
    return { total, active, archived, totalApplicants, customWeighted };
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
    setSearchQuery("");
    setStatusFilter("All Status");
    setDeptFilter("All Departments");
    setCustomWeightsOnly(false);
    setSortBy("newest");
  };

  const suggestions = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];
    const seen = new Set<string>();
    const out: string[] = [];
    for (const job of jobs as Job[]) {
      const title = (job.job_title || job.title || "").trim();
      if (title && title.toLowerCase().includes(q) && !seen.has(title.toLowerCase())) {
        seen.add(title.toLowerCase());
        out.push(title);
        if (out.length >= 5) break;
      }
    }
    return out;
  }, [jobs, searchQuery]);

  const filteredJobs = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const list = (jobs as Job[]).filter(job => {
      const titleMatch = (job.job_title || job.title || "").toLowerCase();
      const idMatch = (job.job_id || String(job.id) || "").toLowerCase();
      const deptMatch = (job.department || "").toLowerCase();
      const skillsStr = Array.isArray(job.skills_requirements)
        ? job.skills_requirements.join(", ").toLowerCase()
        : (job.skills_requirements || "").toLowerCase();

      const matchesSearch = !q ||
        titleMatch.includes(q) ||
        idMatch.includes(q) ||
        deptMatch.includes(q) ||
        skillsStr.includes(q);

      const matchesStatus = statusFilter === "All Status" ||
        (statusFilter === "Active" ? job.is_active : !job.is_active);

      const matchesDept = deptFilter === "All Departments" ||
        job.department === deptFilter;

      const isCustom = Boolean(job.scoring_weights) &&
        !areWeightsEqual(job.scoring_weights!, DEFAULT_JOB_SCORING_WEIGHTS);
      const matchesWeights = !customWeightsOnly || isCustom;

      return matchesSearch && matchesStatus && matchesDept && matchesWeights;
    });

    return [...list].sort((a, b) => {
      if (sortBy === 'applicants') {
        return Number(b.applicant_count ?? 0) - Number(a.applicant_count ?? 0);
      }
      if (sortBy === 'title') {
        return (a.job_title || a.title || '').localeCompare(b.job_title || b.title || '');
      }
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

          {/* Interactive KPI Summary Strip */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
            <button
              type="button"
              onClick={() => {
                setStatusFilter("All Status");
                setCustomWeightsOnly(false);
              }}
              className={`text-left p-4 rounded-2xl border transition-all cursor-pointer group ${
                statusFilter === "All Status" && !customWeightsOnly
                  ? "bg-white border-[#D10043] shadow-md shadow-[#D10043]/10 ring-2 ring-[#D10043]/10"
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Total Positions</span>
                <span className="p-1.5 rounded-xl bg-gray-100 text-gray-600 group-hover:scale-110 transition-transform">
                  <Briefcase size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.total}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">All job requisitions</div>
            </button>

            <button
              type="button"
              onClick={() => {
                setStatusFilter("Active");
                setCustomWeightsOnly(false);
              }}
              className={`text-left p-4 rounded-2xl border transition-all cursor-pointer group ${
                statusFilter === "Active" && !customWeightsOnly
                  ? "bg-white border-emerald-500 shadow-md shadow-emerald-500/10 ring-2 ring-emerald-500/10"
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider">Active</span>
                <span className="p-1.5 rounded-xl bg-emerald-50 text-emerald-600 group-hover:scale-110 transition-transform">
                  <Sparkles size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.active}</div>
              <div className="text-[11px] font-medium text-emerald-600/80 mt-0.5 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                Live on careers page
              </div>
            </button>

            <button
              type="button"
              onClick={() => {
                setStatusFilter("Inactive");
                setCustomWeightsOnly(false);
              }}
              className={`text-left p-4 rounded-2xl border transition-all cursor-pointer group ${
                statusFilter === "Inactive" && !customWeightsOnly
                  ? "bg-white border-slate-500 shadow-md shadow-slate-500/10 ring-2 ring-slate-500/10"
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">Archived</span>
                <span className="p-1.5 rounded-xl bg-slate-100 text-slate-600 group-hover:scale-110 transition-transform">
                  <Archive size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.archived}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">Closed / paused roles</div>
            </button>

            <button
              type="button"
              onClick={() => setSortBy('applicants')}
              className={`text-left p-4 rounded-2xl border transition-all cursor-pointer group ${
                sortBy === 'applicants'
                  ? "bg-white border-indigo-500 shadow-md shadow-indigo-500/10 ring-2 ring-indigo-500/10"
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-indigo-600 uppercase tracking-wider">Applicants</span>
                <span className="p-1.5 rounded-xl bg-indigo-50 text-indigo-600 group-hover:scale-110 transition-transform">
                  <Users size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.totalApplicants}</div>
              <div className="text-[11px] font-medium text-indigo-600/80 mt-0.5">Click to sort by volume</div>
            </button>

            <button
              type="button"
              onClick={() => setCustomWeightsOnly((prev) => !prev)}
              className={`col-span-2 sm:col-span-1 text-left p-4 rounded-2xl border transition-all cursor-pointer group ${
                customWeightsOnly
                  ? "bg-white border-[#D10043] shadow-md shadow-[#D10043]/10 ring-2 ring-[#D10043]/10"
                  : "bg-white/90 border-gray-200/70 hover:border-gray-300 hover:shadow-xs"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-bold text-[#D10043] uppercase tracking-wider">Custom Weights</span>
                <span className="p-1.5 rounded-xl bg-pink-50 text-[#D10043] group-hover:scale-110 transition-transform">
                  <Sliders size={14} />
                </span>
              </div>
              <div className="text-2xl font-black text-gray-900">{isLoading ? '—' : metrics.customWeighted}</div>
              <div className="text-[11px] font-medium text-gray-400 mt-0.5">Non-default scoring rules</div>
            </button>
          </div>

          <JobSearchAndFilter
            searchQuery={searchQuery}
            setSearchQuery={setSearchQuery}
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
            totalFiltered={filteredJobs.length}
            totalCount={(jobs as Job[]).length}
            onResetFilters={resetAllFilters}
          />

          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  className="bg-white rounded-3xl border border-gray-200/70 p-6 animate-pulse space-y-4"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-2xl bg-gray-100" />
                      <div className="space-y-2">
                        <div className="h-5 w-52 bg-gray-200 rounded-lg" />
                        <div className="h-3.5 w-36 bg-gray-100 rounded-lg" />
                      </div>
                    </div>
                    <div className="h-9 w-28 bg-gray-100 rounded-xl" />
                  </div>
                  <div className="h-3 w-full bg-gray-100 rounded-lg" />
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
                onArchive={handleArchiveJob}
                onUnarchive={handleUnarchiveJob}
                onDelete={handleDeleteJob}
              />

              {/* Pagination Controls */}
              {totalPages > 1 && (
                <div className="mt-4 flex flex-col md:flex-row items-center justify-between gap-4 bg-white px-6 py-4 rounded-2xl sm:rounded-3xl shadow-xs border border-gray-200/80">
                  <div className="text-xs sm:text-sm text-slate-600 font-medium text-center md:text-left">
                    Showing <span className="font-bold text-slate-900">{((currentPage - 1) * itemsPerPage) + 1}</span> to <span className="font-bold text-slate-900">{Math.min(currentPage * itemsPerPage, filteredJobs.length)}</span> of <span className="font-bold text-slate-900">{filteredJobs.length}</span> positions
                  </div>

                  <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-4 w-full md:w-auto">
                    <button
                      onClick={handlePrevPage}
                      disabled={currentPage === 1}
                      className="group flex items-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2 rounded-xl bg-white border border-slate-200 shadow-2xs text-xs sm:text-sm font-bold text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95 cursor-pointer min-h-[38px]"
                    >
                      <ArrowRight size={16} className="rotate-180 group-hover:-translate-x-1 transition-transform" />
                      <span>Previous</span>
                    </button>

                    <div className="flex items-center gap-1.5 sm:gap-2 px-2">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Page</span>
                      <div className="px-3.5 py-1 rounded-lg bg-slate-100 border border-slate-200 font-black text-[#D10043] text-xs sm:text-sm shadow-inner">
                        {currentPage}
                      </div>
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">of {totalPages}</span>
                    </div>

                    <button
                      onClick={handleNextPage}
                      disabled={currentPage === totalPages}
                      className="group flex items-center gap-1.5 sm:gap-2 px-4 sm:px-5 py-2.5 rounded-xl bg-[#1A1A1A] text-white shadow-xs text-xs sm:text-sm font-bold hover:bg-[#D60041] disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95 cursor-pointer min-h-[40px]"
                    >
                      <span>Next</span>
                      <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
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
        <div className="fixed inset-0 bg-[#0c0d12]/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-md rounded-2xl sm:rounded-3xl md:rounded-[32px] border border-gray-100 shadow-2xl overflow-hidden p-5 sm:p-8 animate-in zoom-in-95 duration-300">
            <div className="flex items-center justify-center w-12 h-12 sm:w-14 sm:h-14 bg-rose-50 border-2 border-rose-100 rounded-2xl text-rose-600 mb-4 sm:mb-6 mx-auto">
              <AlertCircle className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>

            <h3 className="text-base sm:text-lg font-bold text-gray-900 text-center uppercase tracking-wider mb-2">
              {confirmModal.title}
            </h3>
            <p className="text-xs sm:text-sm text-gray-500 text-center font-medium leading-relaxed mb-6 sm:mb-8">
              {confirmModal.message}
            </p>

            <div className="flex gap-3 sm:gap-4">
              <button
                onClick={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                className="flex-1 py-2.5 sm:py-3 px-4 sm:px-5 border-2 border-gray-100 text-gray-500 rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-gray-50 transition-all duration-300 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (confirmModal.onConfirm) {
                    confirmModal.onConfirm();
                  }
                  setConfirmModal({ ...confirmModal, isOpen: false });
                }}
                className="flex-1 py-2.5 sm:py-3 px-4 sm:px-5 bg-rose-600 text-white rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-rose-700 hover:shadow-lg hover:shadow-rose-100 transition-all duration-300 cursor-pointer"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobManagementPage;
