import React, { useState, useMemo, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useSearchParams } from '@/utils/navigation';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ScheduleInterviewModal from '../../components/modals/hr/ScheduleInterviewModal';
import ViewCandidateDetailsModal from '../../components/modals/hr/ViewCandidateDetailsModal';

// Screening components
import ScreeningHeader from '../../components/hr/screening/ScreeningHeader';
import SearchAndFilter from '../../components/hr/screening/SearchAndFilter';
import BulkActionBar from '../../components/hr/screening/BulkActionBar';
import CandidateList from '../../components/hr/screening/CandidateList';
import Pagination from '../../components/hr/screening/Pagination';

import { AlertCircle, CheckCircle2, X, Archive, Sliders, Layers, List, Play, Sparkles } from 'lucide-react';
import {
  useGetApplicationsQuery,
  useUpdateApplicationStatusMutation,
  useDeleteApplicationMutation,
  useGetJobsQuery,
  useCreateShortlistRosterMutation
} from '../../redux/api/apiSlice';
import StartScreeningModal from '../../components/hr/screening/StartScreeningModal';
import FinalizeShortlistModal from '../../components/hr/screening/FinalizeShortlistModal';
import ScreeningWorkflowBoard from '../../components/hr/screening/ScreeningWorkflowBoard';
import ShortlistRostersList from '../../components/hr/screening/ShortlistRostersList';
import RosterPipelineModal from '../../components/hr/screening/RosterPipelineModal';
import { exportToCSV } from '../../utils/exportUtils';
import { filterAndRankJobs, filterAndRankCandidates } from '../../utils/jobSearch';
import {
  matchesPositionFilter,
  sortCandidatesByOption,
} from '../../utils/hrAnalytics';

interface ConfirmModalState {
  isOpen: boolean;
  title: string;
  message: string;
  onConfirm: (() => void) | null;
}

interface ToastState {
  message: string;
  type: 'success' | 'error';
}

const ScreeningPortal: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { data: candidates = [], isLoading, isFetching, refetch } = useGetApplicationsQuery();
  const [updateStatus] = useUpdateApplicationStatusMutation();
  const [deleteApplication] = useDeleteApplicationMutation();
  const { data: rawJobs = [] } = useGetJobsQuery();
  const [createShortlistRoster] = useCreateShortlistRosterMutation();

  // Active Main Tab: 'workflow' | 'shortlists' | 'pool'
  const [activeTab, setActiveTab] = useState<'workflow' | 'shortlists' | 'pool'>('workflow');

  // Screening Configuration
  const [screeningConfig, setScreeningConfig] = useState<{
    jobId: number | string;
    jobTitle: string;
    minThreshold: number;
    statusFilters: string[];
  } | null>(null);

  const [startModalOpen, setStartModalOpen] = useState<boolean>(false);
  const [finalizeModalOpen, setFinalizeModalOpen] = useState<boolean>(false);
  const [finalizeCandidateIds, setFinalizeCandidateIds] = useState<(number | string)[]>([]);
  const [activeRoster, setActiveRoster] = useState<any | null>(null);

  // Auto-initialize or update screeningConfig when URL ?job= param changes or jobs load
  useEffect(() => {
    if (rawJobs.length === 0) return;
    const jobParam = searchParams.get('job');
    if (jobParam) {
      const targetJob = rawJobs.find(
        (j: any) => (j.job_title || j.title || '').toLowerCase() === jobParam.toLowerCase()
      );
      if (
        targetJob &&
        (!screeningConfig ||
          screeningConfig.jobTitle.toLowerCase() !== (targetJob.job_title || targetJob.title || '').toLowerCase())
      ) {
        setScreeningConfig({
          jobId: targetJob.id || targetJob.job_id,
          jobTitle: targetJob.job_title || targetJob.title || 'Position',
          minThreshold: screeningConfig?.minThreshold ?? 80,
          statusFilters: screeningConfig?.statusFilters ?? ['Submitted', 'Under Review'],
        });
      }
      return;
    }

    if (!screeningConfig) {
      const defaultJob = rawJobs.find((j: any) => j.is_active !== false) || rawJobs[0];
      if (defaultJob) {
        setScreeningConfig({
          jobId: defaultJob.id || defaultJob.job_id,
          jobTitle: defaultJob.job_title || defaultJob.title || 'Position',
          minThreshold: 80,
          statusFilters: ['Submitted', 'Under Review'],
        });
      }
    }
  }, [rawJobs, screeningConfig, searchParams]);

  // Handle finalization of a shortlist roster
  const handleFinalizeShortlist = async (name: string, notes: string) => {
    if (!screeningConfig) return;
    await createShortlistRoster({
      job_id: Number(screeningConfig.jobId),
      name,
      notes,
      application_ids: finalizeCandidateIds.map(Number),
    }).unwrap();

    showToastMessage(`Shortlist roster "${name}" created with ${finalizeCandidateIds.length} candidates!`, 'success');
    refetch();
    setActiveTab('shortlists');
  };

  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("All Status");
  const [jobFilter, setJobFilter] = useState<string>("All Jobs");
  const [scoreFilter, setScoreFilter] = useState<string>("All Scores");
  const [sortBy, setSortBy] = useState<string>("match_desc");
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);
  const [includeArchived, setIncludeArchived] = useState<boolean>(false);

  // Sync URL query params into state (e.g. from HR Dashboard links or UniversalSearch)
  useEffect(() => {
    const statusParam = searchParams.get('status');
    const searchParam = searchParams.get('search');
    const jobParam = searchParams.get('job');
    const scoreParam = searchParams.get('score');
    const candidateIdParam = searchParams.get('candidateId');
    const tabParam = searchParams.get('tab');

    if (tabParam === 'shortlists' || tabParam === 'pool' || tabParam === 'workflow') {
      setActiveTab(tabParam);
    } else if (searchParam || statusParam || scoreParam) {
      setActiveTab('pool');
    }

    if (statusParam) {
      const upper = statusParam.toUpperCase();
      if (upper === 'PENDING' || upper === 'SUBMITTED') {
        setStatusFilter('Submitted');
      } else if (upper === 'REVIEWED' || upper === 'SCREENED' || upper === 'UNDER REVIEW') {
        setStatusFilter('Under Review');
      } else if (upper === 'SHORTLISTED') {
        setStatusFilter('Shortlisted');
      } else if (upper === 'INTERVIEWED') {
        setStatusFilter('Interviewed');
      } else if (upper === 'ACCEPTED' || upper === 'PASSED') {
        setStatusFilter('Passed');
      } else if (upper === 'REJECTED' || upper === 'ARCHIVED' || upper === 'NOT SELECTED') {
        setStatusFilter('Not Selected');
      } else if (upper === 'INTERVIEW') {
        setStatusFilter('Interview Scheduled');
      }
    }

    if (searchParam) {
      setSearchQuery(searchParam);
    }

    if (jobParam) {
      setJobFilter(jobParam);
    }

    if (scoreParam) {
      setScoreFilter(scoreParam);
    }

    if (candidateIdParam && candidates.length > 0) {
      const found = candidates.find((c: any) => String(c.id) === String(candidateIdParam));
      if (found) {
        setSelectedCandidate(found);
        setDetailsModalOpen(true);
      }
    }
  }, [searchParams, candidates]);

  // View & Pagination states
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [itemsPerPage, setItemsPerPage] = useState<number | 'all'>(10);

  // Selection state for Batch Actions & Comparison
  const [selectedIds, setSelectedIds] = useState<(string | number)[]>([]);

  // Modals state
  const [interviewModalOpen, setInterviewModalOpen] = useState<boolean>(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState<boolean>(false);
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);

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

  // Compute overall KPI statistics
  const stats = useMemo(() => {
    const nonArchived = candidates.filter((c: any) => {
      const st = (c.status || '').toLowerCase();
      return st !== 'archived' && st !== 'not selected';
    });
    return {
      total: nonArchived.length,
      pending: candidates.filter((c: any) => {
        const st = (c.status || '').toLowerCase();
        return st === 'submitted' || st === 'pending';
      }).length,
      interview: candidates.filter((c: any) => {
        const st = (c.status || '').toLowerCase();
        return ['interview scheduled', 'interviewed', 'technical interview', 'final interview'].includes(st);
      }).length,
      accepted: candidates.filter((c: any) => {
        const st = (c.status || '').toLowerCase();
        return st === 'shortlisted' || st === 'accepted' || st === 'passed';
      }).length,
      highMatch: nonArchived.filter((c: any) => (c.matchScore || 0) >= 80).length,
      archived: candidates.filter((c: any) => {
        const st = (c.status || '').toLowerCase();
        return st === 'archived' || st === 'not selected';
      }).length
    };
  }, [candidates]);

  // Compute job position options with applicant count
  const jobOptions = useMemo(() => {
    const counts: Record<string, number> = {};
    candidates.forEach((c: any) => {
      if (c.preferredJob) {
        counts[c.preferredJob] = (counts[c.preferredJob] || 0) + 1;
      }
    });
    return Object.entries(counts).map(([title, count]) => ({ title, count }));
  }, [candidates]);

  // Count hidden archived records that match current search query
  const hiddenArchivedMatchCount = useMemo(() => {
    if (!searchQuery.trim() || includeArchived || statusFilter === 'Archived' || statusFilter === 'All With Archived') {
      return 0;
    }
    const q = searchQuery.toLowerCase().trim();
    return candidates.filter((c: any) => {
      const isArchived = (c.status || '').toLowerCase() === 'archived';
      if (!isArchived) return false;
      const matchesName = c.name && c.name.toLowerCase().includes(q);
      const matchesJob = c.preferredJob && c.preferredJob.toLowerCase().includes(q);
      const matchesEmail = c.email && c.email.toLowerCase().includes(q);
      const matchesLocation = c.location && c.location.toLowerCase().includes(q);
      const matchesDegree = (c.degree || '').toLowerCase().includes(q) || (c.college || '').toLowerCase().includes(q);
      const matchesSkills = Array.isArray(c.skills) && c.skills.some((s: string) => (s || '').toLowerCase().includes(q));
      return matchesName || matchesJob || matchesEmail || matchesLocation || matchesDegree || matchesSkills;
    }).length;
  }, [candidates, searchQuery, includeArchived, statusFilter]);

  // Reset pagination whenever filters or sort order change
  useEffect(() => {
    setCurrentPage(1);
  }, [jobFilter, statusFilter, scoreFilter, sortBy, searchQuery, includeArchived]);

  // Filtering and sorting candidates
  const filteredCandidates = useMemo(() => {
    const filtered = candidates.filter((c: any) => {
      const rawStatus = (c.status || 'Submitted').toLowerCase();
      const normStatus = (
        rawStatus === 'pending' ? 'submitted' :
        rawStatus === 'reviewed' || rawStatus === 'screened' ? 'under review' :
        rawStatus === 'rejected' || rawStatus === 'archived' ? 'not selected' :
        rawStatus
      );

      // Status filtering
      if (statusFilter === "Archived" || statusFilter === "Not Selected") {
        if (normStatus !== "not selected" && rawStatus !== "archived") return false;
      } else if (statusFilter === "All With Archived") {
        // Show all including archived
      } else if (statusFilter === "All Status") {
        if (!includeArchived && (normStatus === "not selected" || rawStatus === "archived")) return false;
      } else if (statusFilter === "Interview" || statusFilter === "In Interview" || statusFilter === "Interview Scheduled") {
        if (!['interview scheduled', 'technical interview', 'final interview', 'interview'].includes(rawStatus)) return false;
      } else {
        if (normStatus !== statusFilter.toLowerCase() && rawStatus !== statusFilter.toLowerCase()) return false;
      }

      // Job position filtering (normalized match)
      if (!matchesPositionFilter(c, jobFilter)) {
        return false;
      }

      // Match Score filtering
      const score = c.matchScore || 0;
      if (scoreFilter === "90+" && score < 90) return false;
      if (scoreFilter === "80+" && score < 80) return false;
      if (scoreFilter === "60-79" && (score < 60 || score >= 80)) return false;
      if (scoreFilter === "<60" && score >= 60) return false;

      // Omnisearch (prefix-aware for 1-letter queries, full search for 2+ chars)
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        if (q.length === 1) {
          const nameWords = (c.name || '').toLowerCase().split(/[\s,;/().\-–—]+/).filter((w: string) => w.length >= 2);
          const jobWords = (c.preferredJob || '').toLowerCase().split(/[\s,;/().\-–—]+/).filter(Boolean);
          const matchesSingleLetter =
            (c.name || '').toLowerCase().startsWith(q) ||
            nameWords.some((w: string) => w.startsWith(q)) ||
            (c.preferredJob || '').toLowerCase().startsWith(q) ||
            jobWords.some((w: string) => w.startsWith(q));
          if (!matchesSingleLetter) return false;
        } else {
          const matchesName = c.name && c.name.toLowerCase().includes(q);
          const matchesJob = c.preferredJob && c.preferredJob.toLowerCase().includes(q);
          const matchesEmail = c.email && c.email.toLowerCase().includes(q);
          const matchesLocation = c.location && c.location.toLowerCase().includes(q);
          const matchesDegree = (c.degree || '').toLowerCase().includes(q) || (c.college || '').toLowerCase().includes(q);
          const matchesSkills = Array.isArray(c.skills) && c.skills.some((s: string) => (s || '').toLowerCase().includes(q));
          const matchesDept = c.jobDepartment && c.jobDepartment.toLowerCase().includes(q);
          const matchesCompany = c.company && c.company.toLowerCase().includes(q);
          const matchesSource = (c.source || '').toLowerCase().includes(q) || (c.import_origin || '').toLowerCase().includes(q);

          if (!matchesName && !matchesJob && !matchesEmail && !matchesLocation && !matchesDegree && !matchesSkills && !matchesDept && !matchesCompany && !matchesSource) {
            return false;
          }
        }
      }

      return true;
    });
    return sortCandidatesByOption(filtered, sortBy);
  }, [candidates, statusFilter, jobFilter, scoreFilter, searchQuery, sortBy, includeArchived]);

  // Paginated slice
  const paginatedCandidates = useMemo(() => {
    if (itemsPerPage === 'all') return filteredCandidates;
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredCandidates.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredCandidates, currentPage, itemsPerPage]);

  // Autocomplete suggestions divided into Jobs first, then Candidates under that
  const suggestions = useMemo(() => {
    const trimmed = searchQuery.trim();
    if (!trimmed) return [];

    // 1. Matching Jobs (same ranking as Candidate job search)
    const jobPool = rawJobs.length > 0
      ? rawJobs
      : jobOptions.map((opt) => ({
          job_title: opt.title,
          title: opt.title,
          applicant_count: opt.count,
        }));
    const matchedJobs = filterAndRankJobs(jobPool, trimmed)
      .slice(0, 5)
      .map((j: any) => {
        const title = j.job_title || j.title || 'Position';
        const optMatch = jobOptions.find((o) => o.title.toLowerCase() === title.toLowerCase());
        const appCount = optMatch?.count ?? j.applicant_count ?? 0;
        return {
          type: 'job' as const,
          name: title,
          role: `${j.department || 'Department'} • ${appCount} ${appCount === 1 ? 'applicant' : 'applicants'}`,
        };
      });

    // 2. Matching Candidates (ranked by name / word prefix)
    const matchedCandidates = filterAndRankCandidates(candidates, trimmed)
      .slice(0, 6)
      .map((c: any) => ({
        type: 'candidate' as const,
        name: c.name,
        email: c.email,
        role: c.preferredJob,
        score: Math.round(c.matchScore || 0),
      }));

    return [...matchedJobs, ...matchedCandidates];
  }, [candidates, rawJobs, jobOptions, searchQuery]);

  // Check if any non-default filter is applied
  const isFiltered = Boolean(
    searchQuery.trim() ||
    statusFilter !== "All Status" ||
    jobFilter !== "All Jobs" ||
    scoreFilter !== "All Scores" ||
    sortBy !== "match_desc" ||
    includeArchived
  );

  // Reset all filters
  const handleResetFilters = () => {
    setSearchQuery("");
    setStatusFilter("All Status");
    setJobFilter("All Jobs");
    setScoreFilter("All Scores");
    setSortBy("match_desc");
    setIncludeArchived(false);
    setCurrentPage(1);
  };

  // KPI Card quick filter handler
  const handleKpiClick = (type: string) => {
    setCurrentPage(1);

    if (type === 'all' ||
      (type === 'pending' && (statusFilter === 'Submitted' || statusFilter === 'Pending')) ||
      (type === 'interview' && (statusFilter === 'Interview Scheduled' || statusFilter === 'Interview')) ||
      (type === 'accepted' && (statusFilter === 'Shortlisted' || statusFilter === 'Accepted')) ||
      (type === 'archived' && (statusFilter === 'Not Selected' || statusFilter === 'Archived'))) {
      setStatusFilter("All Status");
      setScoreFilter("All Scores");
      setIncludeArchived(false);
      return;
    }

    switch (type) {
      case 'pending':
        setStatusFilter("Submitted");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'interview':
        setStatusFilter("Interview Scheduled");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'accepted':
        setStatusFilter("Shortlisted");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'archived':
        setStatusFilter("Not Selected");
        setScoreFilter("All Scores");
        setIncludeArchived(true);
        break;
      default:
        setStatusFilter("All Status");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
    }
  };

  // Skill click filter
  const handleSkillClick = (skill: string) => {
    setSearchQuery(skill);
    setCurrentPage(1);
  };

  // Selection toggle
  const handleToggleSelect = (candidateId: string | number) => {
    setSelectedIds(prev =>
      prev.includes(candidateId) ? prev.filter(id => id !== candidateId) : [...prev, candidateId]
    );
  };

  // Select all visible on current filtered set
  const allFilteredSelected = filteredCandidates.length > 0 && filteredCandidates.every((c: any) => selectedIds.includes(c.id));
  const handleToggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredCandidates.map((c: any) => c.id));
    }
  };

  // Export helper
  const exportCandidatesToCSV = (list: any[], filename: string) => {
    const formatted = list.map(c => ({
      "Candidate Name": c.name || "N/A",
      "Email": c.email || "N/A",
      "Phone": c.phone || "N/A",
      "Target Role": c.preferredJob || "N/A",
      "Match Score (%)": Math.round(c.matchScore || 0),
      "Skills Score (%)": Math.round(c.skillsScore || 0),
      "Experience Score (%)": Math.round(c.experienceScore || 0),
      "Education Score (%)": Math.round(c.educationScore || 0),
      "Status": c.status || "Pending",
      "Location": c.location || "N/A",
      "Applied Date": c.date ? new Date(c.date).toLocaleDateString() : "N/A",
      "Skills": Array.isArray(c.skills) ? c.skills.join(", ") : ""
    }));
    exportToCSV(formatted, filename);
  };

  const handleExport = () => {
    const listToExport = filteredCandidates.length > 0 ? filteredCandidates : candidates;
    exportCandidatesToCSV(listToExport, `Candidates_${jobFilter.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}`);
  };

  const handleBatchExport = () => {
    const selectedList = candidates.filter((c: any) => selectedIds.includes(c.id));
    exportCandidatesToCSV(selectedList, `Selected_Candidates_${new Date().toISOString().split('T')[0]}`);
  };

  // Compare candidates navigation
  const handleNavigateCompare = () => {
    if (selectedIds.length > 0) {
      navigate(`/hr/comparecandidates?ids=${selectedIds.join(',')}`);
    } else {
      navigate('/hr/comparecandidates');
    }
  };

  // Modals openers
  const handleOpenInterview = (candidate: any) => {
    setSelectedCandidate(candidate);
    setInterviewModalOpen(true);
  };

  const handleOpenDetails = (candidate: any) => {
    setSelectedCandidate(candidate);
    setDetailsModalOpen(true);
  };

  // Single candidate actions
  const handleUpdateStatus = async (candidateId: string | number, newStatus: string) => {
    try {
      await updateStatus({ id: candidateId, status: newStatus }).unwrap();
      showToastMessage(`Status updated to ${newStatus} & email sent to candidate!`, 'success');
      if (selectedCandidate && selectedCandidate.id === candidateId) {
        setSelectedCandidate((prev: any) => ({ ...prev, status: newStatus }));
      }
    } catch (error) {
      console.error("Failed to update status:", error);
      showToastMessage("Failed to update status. Please try again.", 'error');
    }
  };

  const handleArchiveApplication = async (candidateId: string | number) => {
    try {
      await updateStatus({ id: candidateId, status: "ARCHIVED" }).unwrap();
      showToastMessage("Candidate application archived successfully!", 'success');
    } catch (error) {
      console.error("Failed to archive application:", error);
      showToastMessage("Failed to archive application. Please try again.", 'error');
    }
  };

  const handleRestoreApplication = async (candidateId: string | number) => {
    try {
      await updateStatus({ id: candidateId, status: "Pending" }).unwrap();
      showToastMessage("Candidate application restored to Pending Review!", 'success');
    } catch (error) {
      console.error("Failed to restore application:", error);
      showToastMessage("Failed to restore application. Please try again.", 'error');
    }
  };

  const handleDeleteApplication = async (candidateId: string | number) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Candidate Application',
      message: 'Are you sure you want to permanently remove this candidate application? This action cannot be undone.',
      onConfirm: async () => {
        try {
          await deleteApplication(candidateId).unwrap();
          setSelectedIds(prev => prev.filter(id => id !== candidateId));
          showToastMessage("Candidate application removed successfully!", 'success');
        } catch (error) {
          console.error("Failed to delete application:", error);
          showToastMessage("Failed to delete application. Please try again.", 'error');
        }
      }
    });
  };

  // Batch actions
  const handleBatchStatusUpdate = async (newStatus: string) => {
    try {
      for (const id of selectedIds) {
        await updateStatus({ id, status: newStatus }).unwrap();
      }
      showToastMessage(`Updated ${selectedIds.length} candidates to ${newStatus} & dispatched email notifications!`, 'success');
      setSelectedIds([]);
    } catch (error) {
      console.error("Batch status update error:", error);
      showToastMessage("Failed to update some candidates. Please retry.", 'error');
    }
  };

  const handleBatchArchive = () => {
    setConfirmModal({
      isOpen: true,
      title: `Archive ${selectedIds.length} Candidates`,
      message: `Are you sure you want to archive ${selectedIds.length} selected applications? You can view or restore them under the Archived status tab.`,
      onConfirm: async () => {
        try {
          for (const id of selectedIds) {
            await updateStatus({ id, status: "ARCHIVED" }).unwrap();
          }
          showToastMessage(`Successfully archived ${selectedIds.length} applications!`, 'success');
          setSelectedIds([]);
        } catch (error) {
          console.error("Batch archive error:", error);
          showToastMessage("Failed to archive some applications.", 'error');
        }
      }
    });
  };

  const handleBatchDelete = () => {
    setConfirmModal({
      isOpen: true,
      title: `Delete ${selectedIds.length} Candidates`,
      message: `Are you sure you want to permanently remove ${selectedIds.length} selected applications? This cannot be undone.`,
      onConfirm: async () => {
        try {
          for (const id of selectedIds) {
            await deleteApplication(id).unwrap();
          }
          showToastMessage(`Successfully removed ${selectedIds.length} applications!`, 'success');
          setSelectedIds([]);
        } catch (error) {
          console.error("Batch delete error:", error);
          showToastMessage("Failed to delete some applications.", 'error');
        }
      }
    });
  };

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen flex flex-col font-sans">
      <Helmet>
        <title>Screening | Mariwasa Recruitment HR Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 w-full max-w-full min-w-0 px-3 sm:px-6 md:px-8 lg:px-10 py-4 sm:py-7 md:py-8 animate-in fade-in duration-300 overflow-x-hidden">

          {/* Main Mode Navigation Bar */}
          <div className="flex items-center justify-between gap-4 mb-6 pb-2 border-b border-gray-200/80 flex-wrap">
            <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-2xl">
              <button
                type="button"
                onClick={() => setActiveTab('workflow')}
                className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer ${activeTab === 'workflow'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
                  }`}
              >
                <Sliders size={15} className={activeTab === 'workflow' ? 'text-[#D60041]' : ''} />
                <span>Screening Workflow</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('shortlists')}
                className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer ${activeTab === 'shortlists'
                  ? 'bg-white text-purple-700 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
                  }`}
              >
                <Layers size={15} />
                <span>Shortlist Rosters</span>
              </button>

              <button
                type="button"
                onClick={() => setActiveTab('pool')}
                className={`px-4 py-2 rounded-xl text-xs sm:text-sm font-bold flex items-center gap-2 transition-all cursor-pointer ${activeTab === 'pool'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-gray-500 hover:text-gray-900'
                  }`}
              >
                <List size={15} />
                <span>All Candidates Database</span>
              </button>
            </div>

            {activeTab === 'workflow' && (
              <button
                type="button"
                onClick={() => setStartModalOpen(true)}
                className="px-4 py-2 bg-[#D60041] hover:bg-[#b50037] text-white text-xs sm:text-sm font-bold rounded-xl shadow-xs transition-all flex items-center gap-2 cursor-pointer"
              >
                <Play size={13} fill="currentColor" />
                <span>Start Screening</span>
              </button>
            )}
          </div>

          {/* ═══════ TAB 1: SCREENING WORKFLOW & BOARD ═══════ */}
          {activeTab === 'workflow' && (
            screeningConfig ? (
              <ScreeningWorkflowBoard
                jobTitle={screeningConfig.jobTitle}
                jobId={screeningConfig.jobId}
                minThreshold={screeningConfig.minThreshold}
                candidates={candidates}
                onOpenDetails={handleOpenDetails}
                onOpenFinalize={(ids) => {
                  setFinalizeCandidateIds(ids);
                  setFinalizeModalOpen(true);
                }}
                onChangeParams={() => setStartModalOpen(true)}
              />
            ) : (
              <div className="bg-white rounded-3xl border border-slate-200 p-12 text-center space-y-4">
                <Sliders size={40} className="mx-auto text-slate-300" />
                <h3 className="text-lg font-black text-slate-800">Ready to Screen Resumes</h3>
                <p className="text-xs text-slate-500 max-w-md mx-auto">
                  Select an open position and set your minimum match score to separate qualified applicants into recommended shortlists and the talent pool.
                </p>
                <button
                  type="button"
                  onClick={() => setStartModalOpen(true)}
                  className="px-5 py-2.5 bg-[#D60041] hover:bg-[#b50037] text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-rose-200 transition-all inline-flex items-center gap-2 cursor-pointer"
                >
                  <Play size={14} fill="currentColor" />
                  <span>Choose Role & Start Screening</span>
                </button>
              </div>
            )
          )}

          {/* ═══════ TAB 2: SHORTLIST ROSTERS ═══════ */}
          {activeTab === 'shortlists' && (
            <ShortlistRostersList
              onOpenRoster={(roster) => setActiveRoster(roster)}
              onStartScreening={() => {
                setStartModalOpen(true);
                setActiveTab('workflow');
              }}
            />
          )}

          {/* ═══════ TAB 3: ALL CANDIDATES DATABASE ═══════ */}
          {activeTab === 'pool' && (
            <>
              {/* Header & KPI Summary */}
              <ScreeningHeader
                stats={stats}
                activeStatusFilter={statusFilter}
                activeScoreFilter={scoreFilter}
                onKpiClick={handleKpiClick}
                onExport={handleExport}
                onNavigateCompare={handleNavigateCompare}
                selectedCount={selectedIds.length}
                viewMode={viewMode}
                setViewMode={setViewMode}
                onRefresh={refetch}
                isRefreshing={isFetching}
              />

              {/* Search, Position, Status, Score, and Sort Controls */}
              <SearchAndFilter
                searchQuery={searchQuery}
                setSearchQuery={(q: string) => {
                  setSearchQuery(q);
                  setCurrentPage(1);
                }}
                statusFilter={statusFilter}
                setStatusFilter={(st: string) => {
                  setStatusFilter(st);
                  setCurrentPage(1);
                }}
                jobFilter={jobFilter}
                setJobFilter={(job: string) => {
                  setJobFilter(job);
                  setCurrentPage(1);
                }}
                jobOptions={jobOptions}
                scoreFilter={scoreFilter}
                setScoreFilter={(sf: string) => {
                  setScoreFilter(sf);
                  setCurrentPage(1);
                }}
                sortBy={sortBy}
                setSortBy={setSortBy}
                showSuggestions={showSuggestions}
                setShowSuggestions={setShowSuggestions}
                suggestions={suggestions}
                onResetFilters={handleResetFilters}
                isFiltered={isFiltered}
                includeArchived={includeArchived}
                setIncludeArchived={(val: boolean) => {
                  setIncludeArchived(val);
                  setCurrentPage(1);
                }}
                archivedCount={stats.archived}
                hiddenArchivedMatchCount={hiddenArchivedMatchCount}
              />

              {/* Active Banner when Archived candidates are visible alongside active */}
              {includeArchived && statusFilter !== 'Archived' && (
                <div className="mb-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-3.5 sm:p-4 bg-amber-50/90 border border-amber-200/90 rounded-2xl text-xs sm:text-sm text-amber-900 shadow-xs animate-in fade-in duration-200">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 bg-amber-100 rounded-xl text-amber-800 shrink-0">
                      <Archive size={15} />
                    </div>
                    <div>
                      <span className="font-bold">Archived records visible:</span> Both active and archived candidate applications are included in the screening view.
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIncludeArchived(false)}
                    className="px-3 py-1.5 bg-amber-100 hover:bg-amber-200 text-amber-900 font-bold rounded-xl text-xs transition-all cursor-pointer whitespace-nowrap self-end sm:self-auto shadow-xs"
                  >
                    Hide Archived
                  </button>
                </div>
              )}

              {/* Job Filter Indicator Banner */}
              {jobFilter !== "All Jobs" && (
                <div className="mb-5 bg-pink-50/70 border border-pink-200/70 rounded-2xl p-3.5 sm:p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs animate-in fade-in duration-200">
                  <div>
                    <h3 className="text-sm sm:text-base font-bold text-gray-900">
                      Showing applicants for: <span className="text-[#D60041]">{jobFilter}</span>
                    </h3>
                    <p className="text-xs text-gray-500 font-medium mt-0.5">
                      Total matching applicants: <span className="font-bold text-gray-800">{filteredCandidates.length}</span>
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setJobFilter("All Jobs")}
                    className="px-3 py-1.5 bg-white hover:bg-gray-50 rounded-xl text-xs font-bold text-[#D60041] border border-pink-200 shadow-xs transition-all cursor-pointer self-end sm:self-auto"
                  >
                    Clear Position
                  </button>
                </div>
              )}

              {/* Bulk Action Bar (Visible when 1+ candidates selected) */}
              <BulkActionBar
                selectedCount={selectedIds.length}
                totalFilteredCount={filteredCandidates.length}
                allSelected={allFilteredSelected}
                onToggleSelectAll={handleToggleSelectAll}
                onClearSelection={() => setSelectedIds([])}
                onCompare={handleNavigateCompare}
                onBatchStatusUpdate={handleBatchStatusUpdate}
                onBatchArchive={handleBatchArchive}
                onBatchDelete={handleBatchDelete}
                onBatchExport={handleBatchExport}
              />

              {/* Candidates Content Area */}
              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-20 sm:py-24 bg-white rounded-2xl sm:rounded-3xl border border-gray-200/80 shadow-xs">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 border-3 sm:border-4 border-pink-100 border-t-[#D60041] rounded-full animate-spin mb-4"></div>
                  <p className="text-gray-600 font-bold text-xs sm:text-sm">Loading candidates...</p>
                  <p className="text-gray-400 text-xs mt-1">Retrieving ATS match scores from database</p>
                </div>
              ) : (
                <>
                  <CandidateList
                    candidates={paginatedCandidates}
                    viewMode={viewMode}
                    selectedIds={selectedIds}
                    onToggleSelect={handleToggleSelect}
                    onSelectAll={handleToggleSelectAll}
                    onOpenDetails={handleOpenDetails}
                    onOpenInterview={handleOpenInterview}
                    onUpdateStatus={handleUpdateStatus}
                    onArchiveApplication={handleArchiveApplication}
                    onRestoreApplication={handleRestoreApplication}
                    onDeleteApplication={handleDeleteApplication}
                    onSkillClick={handleSkillClick}
                    onResetFilters={handleResetFilters}
                  />

                  {/* Pagination Controls */}
                  <Pagination
                    currentPage={currentPage}
                    totalItems={filteredCandidates.length}
                    itemsPerPage={itemsPerPage}
                    onPageChange={setCurrentPage}
                    onItemsPerPageChange={(val: number | 'all') => {
                      setItemsPerPage(val);
                      setCurrentPage(1);
                    }}
                  />
                </>
              )}

              {/* End of Pool Tab */}
            </>
          )}

        </main>
      </div>

      {/* Start Screening Setup Modal */}
      <StartScreeningModal
        isOpen={startModalOpen}
        onClose={() => setStartModalOpen(false)}
        jobs={rawJobs}
        onStartScreening={(config) => {
          setScreeningConfig(config);
          setActiveTab('workflow');
        }}
        initialJobId={screeningConfig?.jobId}
      />

      {/* Finalize Shortlist Modal */}
      <FinalizeShortlistModal
        isOpen={finalizeModalOpen}
        onClose={() => setFinalizeModalOpen(false)}
        jobId={screeningConfig?.jobId || 0}
        jobTitle={screeningConfig?.jobTitle || 'Shortlist'}
        candidateIds={finalizeCandidateIds}
        onFinalize={handleFinalizeShortlist}
      />

      {/* Roster Pipeline Tracking Modal */}
      {activeRoster && (
        <RosterPipelineModal
          rosterId={activeRoster.id}
          isOpen={!!activeRoster}
          onClose={() => setActiveRoster(null)}
          onScheduleInterview={(c) => {
            setSelectedCandidate(c);
            setInterviewModalOpen(true);
          }}
          onOpenDetails={(c) => {
            setSelectedCandidate(c);
            setDetailsModalOpen(true);
          }}
        />
      )}

      {/* Schedule Interview Modal */}
      <ScheduleInterviewModal
        isOpen={interviewModalOpen}
        onClose={() => setInterviewModalOpen(false)}
        candidate={selectedCandidate}
        onScheduled={() => {
          showToastMessage('Interview scheduled successfully! Candidate marked as Interview Scheduled.', 'success');
          if (selectedCandidate) {
            setSelectedCandidate((prev: any) => ({ ...prev, status: 'Interview Scheduled' }));
          }
          refetch();
        }}
      />

      {/* View Candidate Details Modal */}
      <ViewCandidateDetailsModal
        isOpen={detailsModalOpen}
        onClose={() => setDetailsModalOpen(false)}
        candidate={selectedCandidate}
        onOpenInterview={handleOpenInterview}
        onUpdateStatus={handleUpdateStatus}
      />

      {/* Custom Confirmation Modal */}
      {confirmModal.isOpen && (
        <div className="fixed inset-0 bg-[#0c0d12]/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
          <div className="bg-white w-full max-w-md rounded-2xl sm:rounded-[32px] border border-gray-100 shadow-2xl overflow-hidden p-6 sm:p-8 animate-in zoom-in-95 duration-200">
            <div className="flex items-center justify-center w-14 h-14 bg-rose-50 border-2 border-rose-100 rounded-2xl text-rose-600 mb-6 mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>

            <h3 className="text-lg font-bold text-gray-900 text-center uppercase tracking-wider mb-2">
              {confirmModal.title}
            </h3>
            <p className="text-sm text-gray-500 text-center font-medium leading-relaxed mb-8">
              {confirmModal.message}
            </p>

            <div className="flex gap-4">
              <button
                type="button"
                onClick={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                className="flex-1 py-3 px-5 border-2 border-gray-100 text-gray-500 rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-gray-50 transition-all"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  confirmModal.onConfirm?.();
                  setConfirmModal({ ...confirmModal, isOpen: false });
                }}
                className="flex-1 py-3 px-5 bg-rose-600 text-white rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-rose-700 shadow-md shadow-rose-100 transition-all"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast Notification */}
      {toast && (
        <div className={`fixed bottom-6 right-6 flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl border animate-in slide-in-from-bottom-5 duration-300 z-50 ${toast.type === 'success'
          ? 'bg-emerald-50 border-emerald-100 text-emerald-800'
          : 'bg-rose-50 border-rose-100 text-rose-800'
          }`}>
          {toast.type === 'success' ? (
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          )}
          <span className="text-xs font-bold uppercase tracking-wider">{toast.message}</span>
          <button onClick={() => setToast(null)} className="ml-2 hover:opacity-75">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

export default ScreeningPortal;
