import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
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

import { AlertCircle, CheckCircle2, X, Archive } from 'lucide-react';
import { 
  useGetApplicationsQuery, 
  useUpdateApplicationStatusMutation, 
  useDeleteApplicationMutation 
} from '../../redux/api/apiSlice';
import { exportToCSV } from '../../utils/exportUtils';

const ScreeningPortal = () => {
  const navigate = useNavigate();
  const { data: candidates = [], isLoading, isFetching, refetch } = useGetApplicationsQuery();
  const [updateStatus] = useUpdateApplicationStatusMutation();
  const [deleteApplication] = useDeleteApplicationMutation();
  
  // Filter & Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [jobFilter, setJobFilter] = useState("All Jobs");
  const [scoreFilter, setScoreFilter] = useState("All Scores");
  const [sortBy, setSortBy] = useState("match_desc");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [includeArchived, setIncludeArchived] = useState(false);

  // View & Pagination states
  const [viewMode, setViewMode] = useState("cards"); // 'cards' | 'table'
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);

  // Selection state for Batch Actions & Comparison
  const [selectedIds, setSelectedIds] = useState([]);

  // Modals state
  const [interviewModalOpen, setInterviewModalOpen] = useState(false);
  const [detailsModalOpen, setDetailsModalOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  // Custom Toast Notification State
  const [toast, setToast] = useState(null);

  // Custom Confirmation Modal State
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    title: '',
    message: '',
    onConfirm: null
  });

  const showToastMessage = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => {
      setToast(null);
    }, 4000);
  };

  // Compute overall KPI statistics
  const stats = useMemo(() => {
    const nonArchived = candidates.filter(c => (c.status || '').toLowerCase() !== 'archived');
    return {
      total: nonArchived.length,
      pending: candidates.filter(c => (c.status || '').toLowerCase() === 'pending').length,
      interview: candidates.filter(c => ['technical interview', 'final interview'].includes((c.status || '').toLowerCase())).length,
      accepted: candidates.filter(c => (c.status || '').toLowerCase() === 'accepted').length,
      highMatch: nonArchived.filter(c => (c.matchScore || 0) >= 80).length,
      archived: candidates.filter(c => (c.status || '').toLowerCase() === 'archived').length
    };
  }, [candidates]);

  // Compute job position options with applicant count
  const jobOptions = useMemo(() => {
    const counts = {};
    candidates.forEach(c => {
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
    return candidates.filter(c => {
      const isArchived = (c.status || '').toLowerCase() === 'archived';
      if (!isArchived) return false;
      const matchesName = c.name && c.name.toLowerCase().includes(q);
      const matchesJob = c.preferredJob && c.preferredJob.toLowerCase().includes(q);
      const matchesEmail = c.email && c.email.toLowerCase().includes(q);
      const matchesLocation = c.location && c.location.toLowerCase().includes(q);
      const matchesDegree = (c.degree || '').toLowerCase().includes(q) || (c.college || '').toLowerCase().includes(q);
      const matchesSkills = Array.isArray(c.skills) && c.skills.some(s => (s || '').toLowerCase().includes(q));
      return matchesName || matchesJob || matchesEmail || matchesLocation || matchesDegree || matchesSkills;
    }).length;
  }, [candidates, searchQuery, includeArchived, statusFilter]);

  // Filtering and sorting candidates
  const filteredCandidates = useMemo(() => {
    return candidates.filter(c => {
      const candidateStatus = (c.status || 'Pending').toLowerCase();

      // Status filtering
      if (statusFilter === "Archived") {
        if (candidateStatus !== "archived") return false;
      } else if (statusFilter === "All With Archived") {
        // Show all including archived
      } else if (statusFilter === "All Status") {
        if (!includeArchived && candidateStatus === "archived") return false;
      } else {
        if (candidateStatus !== statusFilter.toLowerCase()) return false;
      }

      // Job position filtering
      if (jobFilter !== "All Jobs" && c.preferredJob !== jobFilter) {
        return false;
      }

      // Match Score filtering
      const score = c.matchScore || 0;
      if (scoreFilter === "90+" && score < 90) return false;
      if (scoreFilter === "80+" && score < 80) return false;
      if (scoreFilter === "60-79" && (score < 60 || score >= 80)) return false;
      if (scoreFilter === "<60" && score >= 60) return false;

      // Omnisearch
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesName = c.name && c.name.toLowerCase().includes(q);
        const matchesJob = c.preferredJob && c.preferredJob.toLowerCase().includes(q);
        const matchesEmail = c.email && c.email.toLowerCase().includes(q);
        const matchesLocation = c.location && c.location.toLowerCase().includes(q);
        const matchesDegree = (c.degree || '').toLowerCase().includes(q) || (c.college || '').toLowerCase().includes(q);
        const matchesSkills = Array.isArray(c.skills) && c.skills.some(s => (s || '').toLowerCase().includes(q));

        if (!matchesName && !matchesJob && !matchesEmail && !matchesLocation && !matchesDegree && !matchesSkills) {
          return false;
        }
      }

      return true;
    }).sort((a, b) => {
      switch (sortBy) {
        case 'match_asc':
          return (a.matchScore || 0) - (b.matchScore || 0);
        case 'date_desc':
          return new Date(b.date || 0) - new Date(a.date || 0);
        case 'date_asc':
          return new Date(a.date || 0) - new Date(b.date || 0);
        case 'name_asc':
          return (a.name || '').localeCompare(b.name || '');
        case 'name_desc':
          return (b.name || '').localeCompare(a.name || '');
        case 'match_desc':
        default:
          return (b.matchScore || 0) - (a.matchScore || 0);
      }
    });
  }, [candidates, statusFilter, jobFilter, scoreFilter, searchQuery, sortBy, includeArchived]);

  // Paginated slice
  const paginatedCandidates = useMemo(() => {
    if (itemsPerPage === 'all') return filteredCandidates;
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredCandidates.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredCandidates, currentPage, itemsPerPage]);

  // Autocomplete suggestions based on search query
  const suggestions = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase().trim();
    return candidates
      .filter(c => (c.name || '').toLowerCase().includes(q))
      .slice(0, 6)
      .map(c => ({
        name: c.name,
        role: c.preferredJob,
        score: Math.round(c.matchScore || 0)
      }));
  }, [candidates, searchQuery]);

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
  const handleKpiClick = (type) => {
    setCurrentPage(1);
    switch (type) {
      case 'all':
        setStatusFilter("All Status");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'pending':
        setStatusFilter("Pending");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'highMatch':
        setStatusFilter("All Status");
        setScoreFilter("80+");
        setIncludeArchived(false);
        break;
      case 'interview':
        setStatusFilter("Technical Interview");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'accepted':
        setStatusFilter("Accepted");
        setScoreFilter("All Scores");
        setIncludeArchived(false);
        break;
      case 'archived':
        setStatusFilter("Archived");
        setScoreFilter("All Scores");
        setIncludeArchived(true);
        break;
      default:
        break;
    }
  };

  // Skill click filter
  const handleSkillClick = (skill) => {
    setSearchQuery(skill);
    setCurrentPage(1);
  };

  // Selection toggle
  const handleToggleSelect = (candidateId) => {
    setSelectedIds(prev => 
      prev.includes(candidateId) ? prev.filter(id => id !== candidateId) : [...prev, candidateId]
    );
  };

  // Select all visible on current filtered set
  const allFilteredSelected = filteredCandidates.length > 0 && filteredCandidates.every(c => selectedIds.includes(c.id));
  const handleToggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredCandidates.map(c => c.id));
    }
  };

  // Export helper
  const exportCandidatesToCSV = (list, filename) => {
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
    const selectedList = candidates.filter(c => selectedIds.includes(c.id));
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
  const handleOpenInterview = (candidate) => {
    setSelectedCandidate(candidate);
    setInterviewModalOpen(true);
  };

  const handleOpenDetails = (candidate) => {
    setSelectedCandidate(candidate);
    setDetailsModalOpen(true);
  };

  // Single candidate actions
  const handleUpdateStatus = async (candidateId, newStatus) => {
    try {
      await updateStatus({ id: candidateId, status: newStatus }).unwrap();
      showToastMessage(`Status updated to ${newStatus} successfully!`, 'success');
      // If modal candidate is updated, sync local state
      if (selectedCandidate && selectedCandidate.id === candidateId) {
        setSelectedCandidate(prev => ({ ...prev, status: newStatus }));
      }
    } catch (error) {
      console.error("Failed to update status:", error);
      showToastMessage("Failed to update status. Please try again.", 'error');
    }
  };

  const handleArchiveApplication = async (candidateId) => {
    try {
      await updateStatus({ id: candidateId, status: "ARCHIVED" }).unwrap();
      showToastMessage("Candidate application archived successfully!", 'success');
    } catch (error) {
      console.error("Failed to archive application:", error);
      showToastMessage("Failed to archive application. Please try again.", 'error');
    }
  };

  const handleRestoreApplication = async (candidateId) => {
    try {
      await updateStatus({ id: candidateId, status: "Pending" }).unwrap();
      showToastMessage("Candidate application restored to Pending Review!", 'success');
    } catch (error) {
      console.error("Failed to restore application:", error);
      showToastMessage("Failed to restore application. Please try again.", 'error');
    }
  };

  const handleDeleteApplication = async (candidateId) => {
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
  const handleBatchStatusUpdate = async (newStatus) => {
    try {
      for (const id of selectedIds) {
        await updateStatus({ id, status: newStatus }).unwrap();
      }
      showToastMessage(`Updated ${selectedIds.length} candidates to ${newStatus}!`, 'success');
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
        <title>HR - Screening Portal</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 w-full max-w-full min-w-0 px-3.5 sm:px-6 md:px-8 lg:px-10 py-5 sm:py-7 md:py-8 animate-in fade-in duration-300 overflow-x-hidden">
          
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
            setSearchQuery={(q) => {
              setSearchQuery(q);
              setCurrentPage(1);
            }}
            statusFilter={statusFilter}
            setStatusFilter={(st) => {
              setStatusFilter(st);
              setCurrentPage(1);
            }}
            jobFilter={jobFilter}
            setJobFilter={(job) => {
              setJobFilter(job);
              setCurrentPage(1);
            }}
            jobOptions={jobOptions}
            scoreFilter={scoreFilter}
            setScoreFilter={(sf) => {
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
            setIncludeArchived={(val) => {
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
                onItemsPerPageChange={(val) => {
                  setItemsPerPage(val);
                  setCurrentPage(1);
                }}
              />
            </>
          )}

        </main>
      </div>

      {/* Schedule Interview Modal */}
      <ScheduleInterviewModal
        isOpen={interviewModalOpen}
        onClose={() => setInterviewModalOpen(false)}
        candidate={selectedCandidate}
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
          <div className="bg-white w-full max-w-md rounded-[32px] border border-gray-100 shadow-2xl overflow-hidden p-8 animate-in zoom-in-95 duration-200">
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
                  confirmModal.onConfirm();
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
        <div className={`fixed bottom-6 right-6 flex items-center gap-3 px-5 py-4 rounded-2xl shadow-2xl border animate-in slide-in-from-bottom-5 duration-300 z-50 ${
          toast.type === 'success' 
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