import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  FolderArchive,
  Search,
  Filter,
  Upload,
  Download,
  Eye,
  Edit3,
  Calendar,
  Building2,
  FileText,
  User,
  Briefcase,
  Clock,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  SlidersHorizontal,
  ChevronLeft,
  ChevronRight,
  Layers,
  LayoutGrid,
  List,
  Sparkles,
  Info,
  ExternalLink,
  Tag
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ViewPhysicalResumeModal from '../../components/modals/hr/ViewPhysicalResumeModal';
import UploadPhysicalResumeModal from '../../components/modals/hr/UploadPhysicalResumeModal';
import EditPhysicalResumeModal from '../../components/modals/hr/EditPhysicalResumeModal';
import {
  useGetPhysicalResumesQuery,
  useGetPhysicalResumeStatsQuery,
  useGetJobsQuery,
} from '../../redux/api/apiSlice';
import { API_BASE_URL } from '../../services/api';
import { exportToCSV } from '../../utils/exportUtils';

const STATUS_FILTERS = [
  { label: 'All Resumes', value: 'All' },
  { label: 'Received', value: 'RECEIVED' },
  { label: 'Under Review', value: 'UNDER_REVIEW' },
  { label: 'Shortlisted', value: 'SHORTLISTED' },
  { label: 'Hired', value: 'HIRED' },
  { label: 'Archived', value: 'ARCHIVED' },
];

const PhysicalResumes: React.FC = () => {
  // Query parameters
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('All');
  const [jobFilter, setJobFilter] = useState<string>('');
  const [page, setPage] = useState<number>(1);
  const [limit, setLimit] = useState<number>(12);
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // API Data
  const {
    data: resumesData,
    isLoading,
    isFetching,
    refetch,
  } = useGetPhysicalResumesQuery({
    search: searchQuery,
    status: statusFilter !== 'All' ? statusFilter : undefined,
    job_id: jobFilter ? parseInt(jobFilter) : undefined,
    page,
    limit,
  });

  const { data: statsData, refetch: refetchStats } = useGetPhysicalResumeStatsQuery();
  const { data: jobs = [] } = useGetJobsQuery();


  // Toast notification
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  };

  const handleCopyLocation = (e: React.MouseEvent, id: number, location: string) => {
    e.stopPropagation();
    navigator.clipboard.writeText(location);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
    showToast(`Copied location ref: "${location}"`, 'success');
  };

  const handleOpenView = (resume: any) => {
    setSelectedResume(resume);
    setViewModalOpen(true);
  };

  const handleOpenEdit = (resume: any) => {
    setSelectedResume(resume);
    setEditModalOpen(true);
  };

  // Modals state
  const [viewModalOpen, setViewModalOpen] = useState<boolean>(false);
  const [uploadModalOpen, setUploadModalOpen] = useState<boolean>(false);
  const [editModalOpen, setEditModalOpen] = useState<boolean>(false);
  const [selectedResume, setSelectedResume] = useState<any>(null);

  const handleDirectDownload = (e: React.MouseEvent, resume: any) => {
    e.stopPropagation();
    const downloadUrl = `${API_BASE_URL}/hr/physical-resumes/${resume.id}/download`;
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', resume.filename || `${resume.candidate_name.replace(/\s+/g, '_')}_Physical_Resume`);
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Downloading ${resume.filename}...`, 'success');
  };

  const handleExportCSV = () => {
    const items = resumesData?.items || [];
    if (items.length === 0) {
      showToast('No records available to export.', 'error');
      return;
    }
    const exportData = items.map((r: any) => ({
      ID: r.id,
      'Candidate Name': r.candidate_name,
      'Target Position': r.target_job_title || 'N/A',
      'Physical Location': r.physical_location || 'N/A',
      Status: r.status,
      'Submission Date': r.submission_date ? r.submission_date.split('T')[0] : 'N/A',
      'Filename': r.filename,
      'File Size': r.formatted_file_size || 'N/A',
      'Email': r.candidate_email || 'N/A',
      'Phone': r.candidate_phone || 'N/A',
      'Archived By': r.hr_name || 'HR Staff',
      'Notes': r.notes || '',
    }));
    exportToCSV(exportData, `Mariwasa_Physical_Resumes_${new Date().toISOString().split('T')[0]}`);
    showToast('Catalog exported to CSV successfully.', 'success');
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr.split('T')[0] || 'N/A';
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: '2-digit',
        year: 'numeric',
      });
    } catch {
      return dateStr.split('T')[0] || 'N/A';
    }
  };

  const statusColor = (status: string) => {
    switch ((status || '').toUpperCase()) {
      case 'RECEIVED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'UNDER_REVIEW':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'SHORTLISTED':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'HIRED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'ARCHIVED':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  const items = resumesData?.items || [];
  const totalItems = resumesData?.total || 0;
  const totalPages = resumesData?.total_pages || 1;

  return (
    <div className="flex h-screen bg-[#F8FAFC] overflow-hidden">
      <Helmet>
        <title>Physical Resume Storage | Mariwasa HR Portal</title>
      </Helmet>

      {/* SIDEBAR */}
      <Sidebar />

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* TOP HEADER */}
        <Header />

        {/* SCROLLABLE VIEW CONTAINER */}
        <main className="flex-1 overflow-y-auto px-3.5 sm:px-6 lg:px-8 py-4 sm:py-6 space-y-4 sm:space-y-6 custom-scrollbar">
          {/* TOAST ALERT */}
          {toast && (
            <div
              className={`fixed top-20 right-4 sm:right-6 z-50 flex items-center space-x-2.5 px-4 py-3 rounded-2xl shadow-xl border text-xs font-bold animate-in slide-in-from-top-4 duration-300 max-w-[90vw] sm:max-w-md ${
                toast.type === 'success'
                  ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                  : 'bg-rose-50 text-rose-800 border-rose-200'
              }`}
            >
              {toast.type === 'success' ? (
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
              ) : (
                <AlertCircle size={16} className="text-rose-600 shrink-0" />
              )}
              <span className="truncate">{toast.message}</span>
            </div>
          )}

          {/* PAGE HERO BANNER */}
          <section className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 rounded-2xl sm:rounded-3xl p-5 sm:p-8 text-white relative overflow-hidden shadow-xl shadow-slate-900/10">
            <div className="absolute top-0 right-0 w-96 h-96 bg-[#D60041]/20 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none" />
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-5 sm:gap-6">
              <div className="max-w-2xl min-w-0">
                <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 backdrop-blur-md border border-white/15 text-pink-300 text-xs font-bold mb-3">
                  <FolderArchive size={14} className="shrink-0" />
                  <span className="truncate">Physical Storage & Walk-In Submissions</span>
                </div>
                <h1 className="text-xl sm:text-2xl md:text-3xl font-black tracking-tight text-white leading-tight">
                  Hard-Copy Resume Storage Vault
                </h1>
                <p className="text-xs sm:text-sm text-slate-300 font-medium mt-2 leading-relaxed">
                  Store, index, and organize physically submitted resumes with filing cabinet references. View documents directly in the application without downloading, or export full archives on demand.
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    refetch();
                    refetchStats();
                    showToast('Data refreshed.', 'success');
                  }}
                  className="p-2.5 sm:p-3 bg-white/10 hover:bg-white/15 border border-white/10 rounded-xl sm:rounded-2xl text-white transition-all cursor-pointer"
                  title="Refresh repository"
                  aria-label="Refresh repository"
                >
                  <RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} />
                </button>

                <button
                  type="button"
                  onClick={handleExportCSV}
                  className="px-3.5 sm:px-4 py-2.5 sm:py-3 bg-white/10 hover:bg-white/15 border border-white/15 text-white rounded-xl sm:rounded-2xl text-xs font-bold transition-all flex items-center gap-1.5 sm:gap-2 cursor-pointer"
                >
                  <Download size={15} />
                  <span>Export CSV</span>
                </button>

                <button
                  type="button"
                  onClick={() => setUploadModalOpen(true)}
                  className="px-4 sm:px-5 py-2.5 sm:py-3 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl sm:rounded-2xl text-xs font-black shadow-lg shadow-pink-600/30 active:scale-95 transition-all flex items-center gap-2 cursor-pointer"
                >
                  <Upload size={16} />
                  <span>Upload Physical Resume</span>
                </button>
              </div>
            </div>
          </section>

          {/* METRIC CARDS */}
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <div className="bg-white p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-xs flex items-center space-x-3 sm:space-x-4 min-w-0">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-pink-50 text-[#D60041] flex items-center justify-center shrink-0">
                <FolderArchive className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-lg sm:text-2xl font-black text-slate-900 leading-tight">
                  {statsData?.total_stored ?? totalItems}
                </p>
                <p className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5 truncate">
                  Stored Physical Resumes
                </p>
              </div>
            </div>

            <div className="bg-white p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-xs flex items-center space-x-3 sm:space-x-4 min-w-0">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                <Calendar className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-lg sm:text-2xl font-black text-slate-900 leading-tight">
                  {statsData?.received_this_month ?? 0}
                </p>
                <p className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5 truncate">
                  Received This Month
                </p>
              </div>
            </div>

            <div className="bg-white p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-xs flex items-center space-x-3 sm:space-x-4 min-w-0">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-lg sm:text-2xl font-black text-slate-900 leading-tight">
                  {(statsData?.status_counts?.SHORTLISTED ?? 0) + (statsData?.status_counts?.UNDER_REVIEW ?? 0)}
                </p>
                <p className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5 truncate">
                  In Review / Shortlist
                </p>
              </div>
            </div>

            <div className="bg-white p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-xs flex items-center space-x-3 sm:space-x-4 min-w-0">
              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
                <Layers className="w-5 h-5 sm:w-6 sm:h-6" />
              </div>
              <div className="min-w-0">
                <p className="text-lg sm:text-2xl font-black text-slate-900 leading-tight">
                  {statsData?.status_counts?.RECEIVED ?? 0}
                </p>
                <p className="text-[10px] sm:text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5 truncate">
                  Unreviewed / New
                </p>
              </div>
            </div>
          </section>

          {/* SEARCH, STATUS TABS & TOOLBAR */}
          <section className="bg-white p-3.5 sm:p-5 rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-xs space-y-3.5 sm:space-y-4">
            {/* Status Pills */}
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 -mx-1 px-1 custom-scrollbar">
              {STATUS_FILTERS.map((tab) => {
                const isActive = statusFilter === tab.value;
                return (
                  <button
                    key={tab.value}
                    type="button"
                    onClick={() => {
                      setStatusFilter(tab.value);
                      setPage(1);
                    }}
                    className={`px-3 sm:px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap cursor-pointer ${
                      isActive
                        ? 'bg-[#D60041] text-white shadow-xs'
                        : 'bg-slate-50 text-slate-600 hover:bg-slate-100 hover:text-slate-900 border border-slate-100'
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Search Input, Job Filter & View Toggle (Fully Responsive across Mobile & Desktop) */}
            <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3 pt-2 border-t border-slate-100">
              <div className="flex-1 flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3">
                {/* Search Bar */}
                <div className="relative flex-1">
                  <Search size={16} className="absolute left-3.5 top-3 text-slate-400 pointer-events-none" />
                  <input
                    type="text"
                    placeholder="Search candidate name, location ref, notes..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setPage(1);
                    }}
                    className={`w-full pl-10 ${searchQuery ? 'pr-16' : 'pr-4'} py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all`}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-2.5 text-xs text-slate-400 hover:text-slate-600 font-bold px-1.5 py-0.5 rounded cursor-pointer"
                    >
                      Clear
                    </button>
                  )}
                </div>

                {/* Job Filter Dropdown - Accessible on Mobile & Desktop */}
                <div className="w-full sm:w-60 md:w-64 shrink-0">
                  <div className="relative">
                    <select
                      value={jobFilter}
                      onChange={(e) => {
                        setJobFilter(e.target.value);
                        setPage(1);
                      }}
                      className="w-full pl-3.5 pr-8 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-semibold text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] appearance-none cursor-pointer truncate"
                    >
                      <option value="">All Requisitions</option>
                      {jobs.map((j: any) => (
                        <option key={j.id} value={j.id}>
                          {j.title || j.job_title}
                        </option>
                      ))}
                    </select>
                    <SlidersHorizontal size={13} className="absolute right-3 top-3.5 text-slate-400 pointer-events-none" />
                  </div>
                </div>
              </div>

              {/* View Mode Toggle & Counter */}
              <div className="flex items-center justify-between lg:justify-end gap-2 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
                <span className="text-xs font-bold text-slate-500">
                  Showing <strong className="text-slate-900">{items.length}</strong> of {totalItems}
                </span>

                <div className="bg-slate-100 p-1 rounded-xl flex items-center space-x-1 border border-slate-200">
                  <button
                    type="button"
                    onClick={() => setViewMode('grid')}
                    title="Grid view"
                    className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                      viewMode === 'grid' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-400 hover:text-slate-700'
                    }`}
                  >
                    <LayoutGrid size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('table')}
                    title="Table view"
                    className={`p-1.5 rounded-lg transition-all cursor-pointer ${
                      viewMode === 'table' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-400 hover:text-slate-700'
                    }`}
                  >
                    <List size={16} />
                  </button>
                </div>
              </div>
            </div>
          </section>

          {/* MAIN LISTINGS SECTION */}
          {isLoading ? (
            <div className="py-24 flex flex-col items-center justify-center space-y-3">
              <div className="w-10 h-10 border-4 border-[#D60041] border-t-transparent rounded-full animate-spin" />
              <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                Loading physical resume vault...
              </p>
            </div>
          ) : items.length === 0 ? (
            /* EMPTY STATE */
            <div className="py-16 sm:py-24 bg-white rounded-2xl sm:rounded-3xl border border-slate-200/80 text-center px-4 flex flex-col items-center justify-center">
              <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl sm:rounded-3xl bg-pink-50 text-[#D60041] flex items-center justify-center mb-4 shadow-sm">
                <FolderArchive size={32} className="sm:w-9 sm:h-9" />
              </div>
              <h3 className="text-base sm:text-lg font-black text-slate-900 mb-1">
                No Physical Resumes Found
              </h3>
              <p className="text-xs sm:text-sm text-slate-500 font-medium max-w-md mb-6 leading-relaxed">
                {searchQuery || statusFilter !== 'All' || jobFilter
                  ? 'No records match your active search or filter criteria. Try adjusting your search term or clearing filters.'
                  : 'There are no walk-in or hard-copy physical resumes archived yet. Click below to upload and assign filing locations.'}
              </p>
              {searchQuery || statusFilter !== 'All' || jobFilter ? (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setStatusFilter('All');
                    setJobFilter('');
                    setPage(1);
                  }}
                  className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-all cursor-pointer"
                >
                  Reset All Filters
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setUploadModalOpen(true)}
                  className="px-5 py-2.5 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold shadow-xs hover:shadow-md transition-all flex items-center gap-2 cursor-pointer"
                >
                  <Upload size={15} />
                  <span>Upload Physical Resume Now</span>
                </button>
              )}
            </div>
          ) : viewMode === 'grid' ? (
            /* GRID VIEW */
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-5">
              {items.map((resume: any) => {
                const ext = (resume.filename.split('.').pop() || '').toUpperCase();
                return (
                  <div
                    key={resume.id}
                    onClick={() => handleOpenView(resume)}
                    className="group bg-white rounded-2xl sm:rounded-3xl border border-slate-200/80 hover:border-pink-300 p-4 sm:p-5 shadow-xs hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-200 flex flex-col justify-between cursor-pointer relative overflow-hidden"
                  >
                    {/* Top status & format */}
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-2.5">
                        <span
                          className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${statusColor(
                            resume.status
                          )}`}
                        >
                          {resume.status}
                        </span>

                        <span className="text-[10px] font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded-md uppercase">
                          {ext || 'DOC'}
                        </span>
                      </div>

                      {/* Candidate Name & Title */}
                      <h4 className="text-sm font-black text-slate-900 group-hover:text-[#D60041] transition-colors truncate" title={resume.candidate_name}>
                        {resume.candidate_name}
                      </h4>
                      <p className="text-xs text-slate-500 font-semibold truncate mt-0.5 flex items-center gap-1.5" title={resume.target_job_title || 'General Applicant'}>
                        <Briefcase size={13} className="text-slate-400 shrink-0" />
                        <span className="truncate">{resume.target_job_title || 'General Applicant'}</span>
                      </p>

                      {/* PHYSICAL FILING LOCATION TAG (Prominent) */}
                      <div className="mt-3 p-2.5 rounded-xl bg-slate-50 border border-slate-100 group-hover:bg-pink-50/50 group-hover:border-pink-100 transition-colors">
                        <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">
                          <span className="flex items-center gap-1 text-[#D60041]">
                            <FolderArchive size={11} className="shrink-0" /> Physical Storage Ref
                          </span>
                          <button
                            type="button"
                            onClick={(e) => handleCopyLocation(e, resume.id, resume.physical_location)}
                            className="text-slate-400 hover:text-slate-700 cursor-pointer p-0.5 rounded"
                            title="Copy location reference"
                            aria-label="Copy location reference"
                          >
                            {copiedId === resume.id ? (
                              <Check size={12} className="text-emerald-500" />
                            ) : (
                              <Copy size={12} />
                            )}
                          </button>
                        </div>
                        <p className="text-xs font-black text-slate-800 break-words line-clamp-2">
                          {resume.physical_location || 'General HR Archive'}
                        </p>
                      </div>

                      {/* File Details & Hand-in Date */}
                      <div className="mt-3 space-y-1 text-[11px] text-slate-500 font-medium">
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1">
                            <Calendar size={12} className="text-slate-400 shrink-0" /> Hand-in Date:
                          </span>
                          <span className="font-semibold text-slate-700">
                            {formatDate(resume.submission_date)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="flex items-center gap-1">
                            <FileText size={12} className="text-slate-400 shrink-0" /> Size:
                          </span>
                          <span className="font-semibold text-slate-700">
                            {resume.formatted_file_size || 'N/A'}
                          </span>
                        </div>
                      </div>

                      {/* Notes snippet */}
                      {resume.notes && (
                        <p className="mt-2 text-[11px] text-slate-500 italic line-clamp-1 border-t border-slate-100 pt-1.5" title={resume.notes}>
                          "{resume.notes}"
                        </p>
                      )}
                    </div>

                    {/* CARD FOOTER ACTION BUTTONS */}
                    <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-1.5">
                      {/* VIEW RESUME (Inline view without downloading) */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenView(resume);
                        }}
                        className="flex-1 py-2 px-2.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                        title="View resume inside application"
                      >
                        <Eye size={13} className="text-[#D60041] shrink-0" />
                        <span>View</span>
                      </button>

                      {/* DOWNLOAD BUTTON */}
                      <button
                        type="button"
                        onClick={(e) => handleDirectDownload(e, resume)}
                        className="py-2 px-3 bg-pink-50 hover:bg-[#D60041] text-[#D60041] hover:text-white rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer"
                        title="Download resume file"
                      >
                        <Download size={13} className="shrink-0" />
                        <span>Download</span>
                      </button>

                      {/* EDIT BUTTON */}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenEdit(resume);
                        }}
                        className="p-2 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
                        title="Edit filing details"
                        aria-label="Edit filing details"
                      >
                        <Edit3 size={14} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* TABLE VIEW (With horizontal scroll wrapper & minimum width) */
            <div className="bg-white rounded-2xl sm:rounded-3xl border border-slate-200/80 shadow-xs overflow-hidden">
              <div className="overflow-x-auto custom-scrollbar">
                <table className="w-full text-left text-xs min-w-[760px]">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-black uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="px-5 py-3.5">Candidate</th>
                      <th className="px-4 py-3.5">Target Position</th>
                      <th className="px-4 py-3.5">Physical Filing Location</th>
                      <th className="px-4 py-3.5">Hand-in Date</th>
                      <th className="px-4 py-3.5">File Details</th>
                      <th className="px-4 py-3.5">Status</th>
                      <th className="px-5 py-3.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {items.map((resume: any) => (
                      <tr
                        key={resume.id}
                        onClick={() => handleOpenView(resume)}
                        className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                      >
                        <td className="px-5 py-3.5">
                          <p className="font-black text-slate-900">{resume.candidate_name}</p>
                          <p className="text-[11px] text-slate-400 font-medium">
                            {resume.candidate_email || resume.candidate_phone || 'No contact info'}
                          </p>
                        </td>
                        <td className="px-4 py-3.5 font-bold text-slate-800">
                          {resume.target_job_title || 'General Applicant'}
                        </td>
                        <td className="px-4 py-3.5">
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 font-bold text-xs">
                            <FolderArchive size={12} className="text-[#D60041] shrink-0" />
                            <span className="truncate max-w-[200px]">{resume.physical_location || 'General HR Archive'}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3.5 text-slate-600 font-semibold whitespace-nowrap">
                          {formatDate(resume.submission_date)}
                        </td>
                        <td className="px-4 py-3.5 text-slate-500">
                          <p className="font-semibold text-slate-700 truncate max-w-[160px]" title={resume.filename}>{resume.filename}</p>
                          <p className="text-[10px] text-slate-400">{resume.formatted_file_size || 'N/A'}</p>
                        </td>
                        <td className="px-4 py-3.5 whitespace-nowrap">
                          <span
                            className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border ${statusColor(
                              resume.status
                            )}`}
                          >
                            {resume.status}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right space-x-1.5 whitespace-nowrap">
                          {/* VIEW INLINE */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenView(resume);
                            }}
                            className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-lg text-xs font-bold transition-all inline-flex items-center gap-1 cursor-pointer"
                          >
                            <Eye size={12} className="text-[#D60041]" />
                            <span>View</span>
                          </button>

                          {/* DOWNLOAD */}
                          <button
                            type="button"
                            onClick={(e) => handleDirectDownload(e, resume)}
                            className="px-2.5 py-1.5 bg-pink-50 hover:bg-[#D60041] text-[#D60041] hover:text-white rounded-lg text-xs font-bold transition-all inline-flex items-center gap-1 cursor-pointer"
                          >
                            <Download size={12} />
                            <span>Download</span>
                          </button>

                          {/* EDIT */}
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleOpenEdit(resume);
                            }}
                            className="p-1.5 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-lg cursor-pointer"
                            title="Edit filing details"
                            aria-label="Edit filing details"
                          >
                            <Edit3 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* PAGINATION (Responsive for mobile & desktop) */}
          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white px-4 sm:px-5 py-3 rounded-2xl border border-slate-200/80 shadow-xs">
              <span className="text-xs font-bold text-slate-500">
                Page <strong className="text-slate-900">{page}</strong> of {totalPages} ({totalItems} total)
              </span>

              <div className="flex items-center space-x-1 overflow-x-auto max-w-full py-0.5">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  className="p-1.5 sm:p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  title="Previous page"
                  aria-label="Previous page"
                >
                  <ChevronLeft size={16} />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                  .map((p, idx, arr) => (
                    <React.Fragment key={p}>
                      {idx > 0 && arr[idx - 1] !== p - 1 && (
                        <span className="px-1.5 text-xs text-slate-400">...</span>
                      )}
                      <button
                        type="button"
                        onClick={() => setPage(p)}
                        className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                          page === p
                            ? 'bg-[#D60041] text-white shadow-xs'
                            : 'text-slate-600 hover:bg-slate-100 border border-slate-200'
                        }`}
                      >
                        {p}
                      </button>
                    </React.Fragment>
                  ))}
                <button
                  type="button"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                  className="p-1.5 sm:p-2 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
                  title="Next page"
                  aria-label="Next page"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* IN-BROWSER RESUME VIEWER MODAL */}
      <ViewPhysicalResumeModal
        isOpen={viewModalOpen}
        onClose={() => setViewModalOpen(false)}
        resume={selectedResume}
        onEdit={(res) => {
          setViewModalOpen(false);
          handleOpenEdit(res);
        }}
      />

      {/* UPLOAD PHYSICAL RESUME MODAL */}
      <UploadPhysicalResumeModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onSuccess={(result) => {
          showToast(`Successfully archived physical resume for ${result.candidate_name}.`, 'success');
          refetch();
          refetchStats();
        }}
      />

      {/* EDIT MODAL */}
      <EditPhysicalResumeModal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        resume={selectedResume}
        onSuccess={(result) => {
          showToast(`Updated filing details for ${result.candidate_name}.`, 'success');
          refetch();
          refetchStats();
        }}
      />

    </div>
  );
};

export default PhysicalResumes;
