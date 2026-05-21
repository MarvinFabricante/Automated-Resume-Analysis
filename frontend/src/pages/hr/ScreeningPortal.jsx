import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ScheduleInterviewModal from '../../components/modals/hr/ScheduleInterviewModal';
import ViewCandidateDetailsModal from '../../components/modals/hr/ViewCandidateDetailsModal';

// Screening components
import ScreeningHeader from '../../components/hr/screening/ScreeningHeader';
import SearchAndFilter from '../../components/hr/screening/SearchAndFilter';
import CandidateList from '../../components/hr/screening/CandidateList';

const MOCK_CANDIDATES = [
  {
    id: 1,
    name: "Sarah Jenkins",
    status: "Reviewed",
    preferredJob: "Senior Frontend Developer",
    skills: ["React", "TypeScript", "Tailwind CSS", "Node.js"],
    profileImage: null,
    date: "2026-04-12T10:30:00",
    location: "New York, NY",
    matchScore: 94
  },
  {
    id: 2,
    name: "Marcus Chen",
    status: "Pending",
    preferredJob: "UI/UX Designer",
    skills: ["Figma", "Adobe XD", "Prototyping", "User Research"],
    profileImage: null,
    date: "2026-04-14T14:20:00",
    location: "San Francisco, CA",
    matchScore: 88
  },
  {
    id: 3,
    name: "Elena Rodriguez",
    status: "Reviewed",
    preferredJob: "Product Manager",
    skills: ["Agile", "Scrum", "Jira", "Market Analysis"],
    profileImage: null,
    date: "2026-04-15T09:00:00",
    location: "Austin, TX",
    matchScore: 82
  },
  {
    id: 4,
    name: "Tariq Mahmood",
    status: "Pending",
    preferredJob: "Backend Engineer",
    skills: ["Python", "Django", "PostgreSQL", "AWS"],
    profileImage: null,
    date: "2026-04-15T11:00:00",
    location: "Chicago, IL",
    matchScore: 79
  },
  {
    id: 5,
    name: "Jessica Wu",
    status: "Reviewed",
    preferredJob: "Data Scientist",
    skills: ["Python", "TensorFlow", "Pandas", "SQL"],
    profileImage: null,
    date: "2026-04-15T16:45:00",
    location: "Seattle, WA",
    matchScore: 91
  },
];

import { AlertCircle, CheckCircle2, X } from 'lucide-react';
import { useGetApplicationsQuery, useUpdateApplicationStatusMutation, useDeleteApplicationMutation } from '../../redux/api/apiSlice';
import { exportToCSV } from '../../utils/exportUtils';

const ScreeningPortal = () => {
  const { data: candidates = [], isLoading } = useGetApplicationsQuery();
  const [updateStatus] = useUpdateApplicationStatusMutation();
  const [deleteApplication] = useDeleteApplicationMutation();
  
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [jobFilter, setJobFilter] = useState("All Jobs");
  const [showSuggestions, setShowSuggestions] = useState(false);

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

  const handleExport = () => {
    exportToCSV(candidates, `Candidate_List_${new Date().toISOString().split('T')[0]}`);
  };

  const handleOpenInterview = (candidate) => {
    setSelectedCandidate(candidate);
    setInterviewModalOpen(true);
  };

  const handleOpenDetails = (candidate) => {
    setSelectedCandidate(candidate);
    setDetailsModalOpen(true);
  };

  const handleUpdateStatus = async (candidateId, newStatus) => {
    try {
      await updateStatus({ id: candidateId, status: newStatus }).unwrap();
      showToastMessage(`Status updated to ${newStatus} successfully!`, 'success');
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

  const handleDeleteApplication = async (candidateId) => {
    setConfirmModal({
      isOpen: true,
      title: 'Remove Candidate',
      message: 'Are you sure you want to remove this application? This action is permanent and cannot be undone.',
      onConfirm: async () => {
        try {
          await deleteApplication(candidateId).unwrap();
          showToastMessage("Candidate application removed successfully!", 'success');
        } catch (error) {
          console.error("Failed to delete application:", error);
          showToastMessage("Failed to delete application. Please try again.", 'error');
        }
      }
    });
  };

  const filteredCandidates = candidates.filter(c => {
    // Hide archived by default unless explicitly viewing archived
    if (statusFilter !== "Archived" && c.status.toLowerCase() === "archived") {
      return false;
    }

    const matchesStatus =
      statusFilter === "All Status" ||
      c.status.toLowerCase() === statusFilter.toLowerCase();
      
    const matchesJob = 
      jobFilter === "All Jobs" || 
      c.preferredJob === jobFilter;

    const q = searchQuery.toLowerCase();
    const matchesSearch =
      !searchQuery ||
      c.name.toLowerCase().includes(q) ||
      (c.preferredJob && c.preferredJob.toLowerCase().includes(q)) ||
      (c.skills && c.skills.some(s => s.toLowerCase().includes(q)));

    return matchesStatus && matchesJob && matchesSearch;
  }).sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));

  const uniqueJobs = ["All Jobs", ...new Set(candidates.map(c => c.preferredJob).filter(Boolean))];

  const suggestions = searchQuery.length > 0
    ? candidates.filter(c => c.name.toLowerCase().includes(searchQuery.toLowerCase())).map(c => c.name)
    : [];

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>HR - Screening Portal</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 w-full max-w-full px-4 sm:px-6 md:px-10 py-6 md:py-8 animate-in fade-in duration-500">
        <ScreeningHeader onExport={handleExport} />

        <SearchAndFilter 
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          jobFilter={jobFilter}
          setJobFilter={setJobFilter}
          uniqueJobs={uniqueJobs}
          showSuggestions={showSuggestions}
          setShowSuggestions={setShowSuggestions}
          suggestions={suggestions}
        />

        {jobFilter !== "All Jobs" && (
          <div className="mb-6 bg-pink-50 border border-pink-100 rounded-2xl p-4 flex items-center justify-between shadow-sm">
            <div>
              <h3 className="text-lg font-bold text-gray-800">Showing applicants for: <span className="text-[#D60041]">{jobFilter}</span></h3>
              <p className="text-sm text-gray-500 font-medium mt-1">
                Total Applicants: {filteredCandidates.length}
              </p>
            </div>
            <div className="px-4 py-2 bg-white rounded-xl text-xs font-bold text-[#D60041] border border-pink-100 shadow-sm uppercase tracking-wide">
              Ranked by AI Score
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-pink-100 border-t-[#D60041] rounded-full animate-spin mb-4"></div>
            <p className="text-gray-500 font-bold">Loading candidates...</p>
          </div>
        ) : (
          <CandidateList 
            candidates={filteredCandidates}
            onOpenDetails={handleOpenDetails}
            onOpenInterview={handleOpenInterview}
            onUpdateStatus={handleUpdateStatus}
            onArchiveApplication={handleArchiveApplication}
            onDeleteApplication={handleDeleteApplication}
          />
        )}
        </main>
      </div>

      <ScheduleInterviewModal
        isOpen={interviewModalOpen}
        onClose={() => setInterviewModalOpen(false)}
        candidate={selectedCandidate}
      />

      <ViewCandidateDetailsModal
        isOpen={detailsModalOpen}
        onClose={() => setDetailsModalOpen(false)}
        candidate={selectedCandidate}
      />

      {/* Confirm Modal */}
      {confirmModal.isOpen && (
        <div className="fixed inset-0 bg-[#0c0d12]/60 backdrop-blur-md flex items-center justify-center z-50 p-4 animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-md rounded-[32px] border border-gray-100 shadow-2xl overflow-hidden p-8 animate-in zoom-in-95 duration-300">
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
                onClick={() => setConfirmModal({ ...confirmModal, isOpen: false })}
                className="flex-1 py-3 px-5 border-2 border-gray-100 text-gray-500 rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-gray-50 transition-all duration-300"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  confirmModal.onConfirm();
                  setConfirmModal({ ...confirmModal, isOpen: false });
                }}
                className="flex-1 py-3 px-5 bg-rose-600 text-white rounded-xl text-xs font-bold uppercase tracking-wider hover:bg-rose-700 hover:shadow-lg hover:shadow-rose-100 transition-all duration-300"
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