import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from '@/utils/navigation';
import { filterAndRankJobs } from '../../utils/jobSearch';
import { Helmet } from 'react-helmet-async';
import {
  Briefcase,
  Search,
  X,
  MapPin,
  Clock,
  ArrowRight,
  Sparkles,
  Bookmark,
  Building2,
  LayoutGrid,
  List,
  FileText,
  FileUp,
  ChevronDown,
  Coins,
  RotateCcw
} from 'lucide-react';
import jobService from '../../services/jobService';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import CandidateJobDetailsModal from '../../components/modals/candidate/CandidateJobDetailsModal';
import { Job } from '../../types';

interface DisplayJob {
  id: string | number;
  job_id: string;
  title: string;
  department: string;
  location: string;
  job_type: string;
  salary_range: string;
  description: string;
  skills_requirements: string;
  education_requirements: string;
  certifications_requirements: string;
  experience_requirements: string;
  is_active: boolean;
}

const FindJob: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlSearch = searchParams.get('search') || '';

  // Data & Loading state
  const [jobs, setJobs] = useState<DisplayJob[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Search & Filter state (searchTerm is live-synced with the navigation bar search)
  const [searchTerm, setSearchTerm] = useState<string>(urlSearch);

  useEffect(() => {
    setSearchTerm(urlSearch);
  }, [urlSearch]);

  useEffect(() => {
    const handleNavbarSearch = (e: Event) => {
      const detail = (e as CustomEvent)?.detail;
      if (detail && detail.source === 'navbar') {
        setSearchTerm(String(detail.query ?? ''));
      }
    };
    const handlePopState = () => {
      const nextQ = new URLSearchParams(window.location.search).get('search') || '';
      setSearchTerm(nextQ);
    };
    window.addEventListener('candidate-job-search', handleNavbarSearch);
    window.addEventListener('popstate', handlePopState);
    return () => {
      window.removeEventListener('candidate-job-search', handleNavbarSearch);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);
  const [selectedDept, setSelectedDept] = useState<string>('All');
  const [selectedJobType, setSelectedJobType] = useState<string>('All');
  const [selectedLocation, setSelectedLocation] = useState<string>('All');
  const [sortBy, setSortBy] = useState<string>('featured');
  const [showSavedOnly, setShowSavedOnly] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Modal State for Job Details
  const [selectedJobForDetails, setSelectedJobForDetails] = useState<DisplayJob | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState<boolean>(false);

  // Bookmarking in localStorage
  const [bookmarkedIds, setBookmarkedIds] = useState<(string | number)[]>(() => {
    try {
      const saved = localStorage.getItem('candidate_bookmarked_jobs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Pagination State
  const [currentPage, setCurrentPage] = useState<number>(1);
  const itemsPerPage = 6;

  // Fetch Jobs on Mount
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        setIsLoading(true);
        const response = await jobService.getAllJobs();
        const rawJobs = Array.isArray(response.data) ? response.data : [];

        const transformedData: DisplayJob[] = rawJobs.map((job: any) => ({
          id: job.job_id || job.id,
          job_id: String(job.job_id || job.id || ''),
          title: job.job_title || job.title || 'Untitled Role',
          department: job.department || 'General',
          location: job.location || 'Remote',
          job_type: job.job_type || 'Full-Time',
          salary_range: job.salary_range || 'Competitive',
          description: job.description || '',
          skills_requirements: Array.isArray(job.skills_requirements)
            ? job.skills_requirements.join(', ')
            : job.skills_requirements || '',
          education_requirements: job.education_requirements || '',
          certifications_requirements: job.certifications_requirements || '',
          experience_requirements: job.experience_requirements || '',
          is_active: job.is_active ?? true
        }));

        setJobs(transformedData);
      } catch (error) {
        console.error('Failed to fetch jobs:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, []);

  // Bookmark Toggle Handler
  const handleToggleBookmark = (jobId: string | number) => {
    setBookmarkedIds((prev) => {
      const updated = prev.includes(jobId)
        ? prev.filter((id) => id !== jobId)
        : [...prev, jobId];
      try {
        localStorage.setItem('candidate_bookmarked_jobs', JSON.stringify(updated));
      } catch (err) {
        console.error('Failed to save bookmark:', err);
      }
      return updated;
    });
  };

  // Open Details Modal
  const handleOpenDetails = (job: DisplayJob) => {
    setSelectedJobForDetails(job);
    setIsDetailsModalOpen(true);
  };

  // Close Details Modal
  const handleCloseDetails = () => {
    setIsDetailsModalOpen(false);
    setSelectedJobForDetails(null);
  };

  // Direct Apply Handler
  const handleApply = (jobId: string | number) => {
    navigate(`/candidate/upload-resume/${jobId}`);
  };

  // Unique Filter Options
  const departments = useMemo(() => {
    const depts = new Set(jobs.map((j) => j.department).filter(Boolean));
    return ['All', ...Array.from(depts)];
  }, [jobs]);

  const jobTypes = useMemo(() => {
    const types = new Set(jobs.map((j) => j.job_type).filter(Boolean));
    return ['All', ...Array.from(types)];
  }, [jobs]);

  const locations = useMemo(() => {
    const locs = new Set(jobs.map((j) => j.location).filter(Boolean));
    return ['All', ...Array.from(locs)];
  }, [jobs]);

  // Department counts
  const deptCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    jobs.forEach((j) => {
      counts[j.department] = (counts[j.department] || 0) + 1;
    });
    return counts;
  }, [jobs]);

  // Filtering Logic
  const filteredJobs = useMemo(() => {
    const activeJobs = jobs.filter((j) => j.is_active !== false);
    const searchMatched = filterAndRankJobs(activeJobs, searchTerm);

    const result = searchMatched.filter((job) => {
      const matchesDept = selectedDept === 'All' || job.department === selectedDept;
      const matchesType = selectedJobType === 'All' || job.job_type === selectedJobType;
      const matchesLocation =
        selectedLocation === 'All' || job.location === selectedLocation;
      const matchesSaved = !showSavedOnly || bookmarkedIds.includes(job.id);

      return matchesDept && matchesType && matchesLocation && matchesSaved;
    });

    if (sortBy === 'title-asc') {
      result.sort((a, b) => a.title.localeCompare(b.title));
    } else if (sortBy === 'title-desc') {
      result.sort((a, b) => b.title.localeCompare(a.title));
    } else if (sortBy === 'department') {
      result.sort((a, b) => a.department.localeCompare(b.department));
    }

    return result;
  }, [
    jobs,
    searchTerm,
    selectedDept,
    selectedJobType,
    selectedLocation,
    showSavedOnly,
    bookmarkedIds,
    sortBy
  ]);

  // Reset page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedDept, selectedJobType, selectedLocation, showSavedOnly, sortBy]);

  // Pagination Calculations
  const totalPages = Math.ceil(filteredJobs.length / itemsPerPage) || 1;
  const paginatedJobs = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredJobs.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredJobs, currentPage, itemsPerPage]);

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1));
    const targetElement = document.getElementById('jobs-results-anchor');
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages));
    const targetElement = document.getElementById('jobs-results-anchor');
    if (targetElement) {
      targetElement.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const clearNavbarAndPageSearch = () => {
    setSearchTerm('');
    if (typeof window !== 'undefined') {
      window.history.replaceState(window.history.state, '', '/candidate/findjobs');
      window.dispatchEvent(
        new CustomEvent('candidate-job-search', {
          detail: { query: '', source: 'page' },
        })
      );
    }
  };

  const resetAllFilters = () => {
    clearNavbarAndPageSearch();
    setSelectedDept('All');
    setSelectedJobType('All');
    setSelectedLocation('All');
    setShowSavedOnly(false);
    setSortBy('featured');
  };

  const hasActiveFilters =
    searchTerm !== '' ||
    selectedDept !== 'All' ||
    selectedJobType !== 'All' ||
    selectedLocation !== 'All' ||
    showSavedOnly ||
    sortBy !== 'featured';

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] min-h-screen flex flex-col">
      <Helmet>
        <title>Open Positions | Mariwasa Recruitment</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-grow min-w-0">

          {/* CANDIDATE JOB WORKSPACE HEADER & FILTERS */}
          <section className="relative pt-6 sm:pt-8 pb-6 sm:pb-7 px-4 sm:px-6 lg:px-10 bg-white border-b border-slate-200/70">
            <div className="max-w-[1360px] mx-auto relative z-20 space-y-5">

              {/* Top Title + Resume Matcher Quick Action */}
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#D10043]/8 border border-[#D10043]/15 text-[#D10043] text-[11px] font-black uppercase tracking-wider mb-2">
                    <Sparkles size={13} className="text-[#D10043]" />
                    Open Positions
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                    Explore Open Roles at <span className="text-[#D10043]">Mariwasa</span>
                  </h1>
                  <p className="text-xs sm:text-sm text-slate-500 font-medium mt-1">
                    Use the top navigation search bar to look up jobs by letter or keyword, or filter roles below.
                  </p>
                </div>

                {/* Compact Candidate-Only Smart Match CTA */}
                <div className="flex flex-wrap items-center gap-2.5 bg-slate-900 text-white px-4 py-3 rounded-2xl shadow-sm shrink-0">
                  <div className="min-w-0">
                    <p className="text-[11px] font-black uppercase tracking-wider text-rose-300">
                      Not sure which role fits?
                    </p>
                    <p className="text-xs text-slate-300 font-medium">
                      Upload your resume to rank your best matches
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate('/candidate/smart-upload')}
                    className="px-4 py-2 rounded-xl bg-[#D10043] hover:bg-white hover:text-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all cursor-pointer shrink-0"
                  >
                    <FileUp size={14} />
                    <span>Match Resume</span>
                  </button>
                </div>
              </div>

              {/* FILTER BAR (No duplicate search bar; uses the navigation bar search) */}
              <div className="w-full bg-slate-50/70 p-3 sm:p-4 rounded-2xl sm:rounded-3xl border border-slate-200/80 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 flex-1">
                  {/* Department Dropdown */}
                  <div className="relative">
                    <Building2 className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={16} />
                    <select
                      aria-label="Filter by Department"
                      value={selectedDept}
                      onChange={(e) => setSelectedDept(e.target.value)}
                      className="w-full appearance-none pl-10 pr-8 py-2.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] text-xs sm:text-sm font-semibold text-slate-700 cursor-pointer transition-all truncate"
                    >
                      {departments.map((dept) => (
                        <option key={dept} value={dept}>
                          {dept === 'All'
                            ? 'All Departments'
                            : `${dept}${deptCounts[dept] ? ` (${deptCounts[dept]})` : ''}`}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={15} />
                  </div>

                  {/* Employment Type Dropdown */}
                  <div className="relative">
                    <Clock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={16} />
                    <select
                      aria-label="Filter by Employment Type"
                      value={selectedJobType}
                      onChange={(e) => setSelectedJobType(e.target.value)}
                      className="w-full appearance-none pl-10 pr-8 py-2.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] text-xs sm:text-sm font-semibold text-slate-700 cursor-pointer transition-all truncate"
                    >
                      {jobTypes.map((type) => (
                        <option key={type} value={type}>
                          {type === 'All' ? 'All Job Types' : type}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={15} />
                  </div>

                  {/* Location Dropdown */}
                  <div className="relative">
                    <MapPin className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={16} />
                    <select
                      aria-label="Filter by Location"
                      value={selectedLocation}
                      onChange={(e) => setSelectedLocation(e.target.value)}
                      className="w-full appearance-none pl-10 pr-8 py-2.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] text-xs sm:text-sm font-semibold text-slate-700 cursor-pointer transition-all truncate"
                    >
                      {locations.map((loc) => (
                        <option key={loc} value={loc}>
                          {loc === 'All' ? 'All Locations' : loc}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={15} />
                  </div>
                </div>

                {/* Active Search Chip + Saved Jobs + Reset */}
                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  {searchTerm.trim() !== '' && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 text-[#D10043] border border-rose-200 text-xs font-bold">
                      <span>Search: &ldquo;{searchTerm.trim()}&rdquo;</span>
                      <button
                        type="button"
                        aria-label="Clear active search filter"
                        onClick={clearNavbarAndPageSearch}
                        className="p-0.5 rounded-full hover:bg-rose-100 cursor-pointer"
                      >
                        <X size={13} />
                      </button>
                    </span>
                  )}

                  <button
                    type="button"
                    onClick={() => setShowSavedOnly(!showSavedOnly)}
                    className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all border cursor-pointer ${showSavedOnly
                        ? 'bg-pink-50 text-[#D10043] border-pink-200 shadow-xs'
                        : 'bg-white hover:bg-slate-100 text-slate-600 border-slate-200'
                      }`}
                  >
                    <Bookmark size={13} className={showSavedOnly ? 'fill-[#D10043]' : ''} />
                    Saved Jobs
                    {bookmarkedIds.length > 0 && (
                      <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-black ${showSavedOnly ? 'bg-[#D10043] text-white' : 'bg-slate-100 text-slate-600'
                        }`}>
                        {bookmarkedIds.length}
                      </span>
                    )}
                  </button>

                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={resetAllFilters}
                      className="inline-flex items-center gap-1 px-3 py-2 text-xs font-bold text-[#D10043] hover:bg-pink-50 rounded-xl transition-colors cursor-pointer"
                    >
                      <RotateCcw size={13} />
                      Reset
                    </button>
                  )}
                </div>
              </div>

            </div>
          </section>

          {/* MAIN RESULTS SECTION */}
          <section id="jobs-results-anchor" className="max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-10 py-6 sm:py-10">

            {/* TOOLBAR & CONTROLS */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8 sm:mb-10 pb-6 border-b border-slate-200/80">

              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                    {showSavedOnly
                      ? 'Your Saved Roles'
                      : searchTerm.trim()
                        ? `Results for "${searchTerm.trim()}"`
                        : 'Available Positions'}
                  </h2>
                  <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono text-xs font-black">
                    {filteredJobs.length}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-slate-500 font-medium mt-1">
                  {showSavedOnly
                    ? 'Review bookmarked positions and complete your applications'
                    : searchTerm.trim()
                      ? `Showing ${filteredJobs.length} matching role${filteredJobs.length === 1 ? '' : 's'} sorted by relevance`
                      : selectedDept !== 'All'
                        ? `Showing open roles in ${selectedDept}`
                        : 'Browse open roles across Mariwasa departments'}
                </p>
              </div>

              {/* View Mode & Sort Controls */}
              <div className="flex items-center gap-3 w-full sm:w-auto justify-between sm:justify-end">

                {/* Sort selector */}
                <div className="relative">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value)}
                    className="appearance-none pl-3.5 pr-8 py-2 bg-white border border-slate-200 rounded-xl text-xs font-bold text-slate-700 hover:border-slate-300 focus:ring-2 focus:ring-[#D10043]/10 cursor-pointer"
                  >
                    <option value="featured">Sort: Featured</option>
                    <option value="title-asc">Title (A - Z)</option>
                    <option value="title-desc">Title (Z - A)</option>
                    <option value="department">Department</option>
                  </select>
                  <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" size={14} />
                </div>

                {/* View Switcher */}
                <div className="flex items-center bg-white p-1 rounded-xl border border-slate-200 shadow-2xs">
                  <button
                    type="button"
                    onClick={() => setViewMode('grid')}
                    title="Grid View"
                    className={`p-2 rounded-lg transition-all ${viewMode === 'grid'
                        ? 'bg-[#D10043] text-white shadow-xs'
                        : 'text-slate-400 hover:text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    <LayoutGrid size={17} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode('list')}
                    title="List View"
                    className={`p-2 rounded-lg transition-all ${viewMode === 'list'
                        ? 'bg-[#D10043] text-white shadow-xs'
                        : 'text-slate-400 hover:text-slate-700 hover:bg-slate-50'
                      }`}
                  >
                    <List size={17} />
                  </button>
                </div>

              </div>

            </div>

            {/* LOADING STATE */}
            {isLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div
                    key={i}
                    className="bg-white rounded-[32px] p-7 border border-slate-100 shadow-sm space-y-5 animate-pulse"
                  >
                    <div className="flex items-center justify-between">
                      <div className="w-12 h-12 rounded-2xl bg-slate-100" />
                      <div className="w-20 h-6 rounded-full bg-slate-100" />
                    </div>
                    <div className="space-y-2">
                      <div className="h-6 bg-slate-100 rounded-lg w-3/4" />
                      <div className="h-4 bg-slate-100 rounded-lg w-1/2" />
                    </div>
                    <div className="h-12 bg-slate-50 rounded-xl" />
                    <div className="flex gap-2">
                      <div className="h-11 bg-slate-100 rounded-2xl flex-1" />
                      <div className="h-11 bg-slate-100 rounded-2xl flex-1" />
                    </div>
                  </div>
                ))}
              </div>
            ) : filteredJobs.length === 0 ? (

              /* EMPTY STATE */
              <div className="py-20 sm:py-24 text-center bg-white rounded-[36px] sm:rounded-[48px] border-2 border-dashed border-slate-200/80 px-6 max-w-2xl mx-auto shadow-xs">
                <div className="w-20 h-20 bg-pink-50 text-[#D10043] rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-sm">
                  <Search size={36} />
                </div>
                <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight mb-2">
                  No matching positions found
                </h3>
                <p className="text-slate-500 text-sm sm:text-base font-medium max-w-md mx-auto mb-8 leading-relaxed">
                  We couldn't find any job opportunities matching your current search parameters. Try adjusting keywords or clearing active filters.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-3">
                  <button
                    type="button"
                    onClick={resetAllFilters}
                    className="inline-flex items-center gap-2 px-6 py-3.5 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-2xl font-black text-xs uppercase tracking-wider transition-all"
                  >
                    <RotateCcw size={15} />
                    Reset all filters
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate('/candidate/smart-upload')}
                    className="inline-flex items-center gap-2 px-7 py-3.5 bg-[#D10043] hover:bg-slate-900 text-white rounded-2xl font-black text-xs uppercase tracking-wider transition-all shadow-lg shadow-[#D10043]/20 active:scale-95 cursor-pointer"
                  >
                    <FileUp size={15} />
                    <span>Upload Resume</span>
                  </button>
                </div>
              </div>

            ) : viewMode === 'grid' ? (

              /* GRID VIEW */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 sm:gap-8">
                {paginatedJobs.map((job) => {
                  const isBookmarked = bookmarkedIds.includes(job.id);

                  // Parse skill tags
                  const skills = typeof job.skills_requirements === 'string'
                    ? job.skills_requirements.split(/[,;\n•]+/).map((s) => s.trim()).filter(Boolean)
                    : [];

                  return (
                    <div
                      key={job.id}
                      className="group bg-white rounded-[32px] p-6 sm:p-7 border border-slate-100 hover:border-[#D10043]/20 hover:shadow-2xl hover:shadow-slate-200/70 hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between"
                    >
                      <div>
                        {/* Top Meta Bar */}
                        <div className="flex items-start justify-between gap-3 mb-5">
                          <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-2xl bg-slate-50 group-hover:bg-[#D10043]/10 border border-slate-100 flex items-center justify-center text-slate-400 group-hover:text-[#D10043] transition-colors duration-300">
                              <Building2 size={22} />
                            </div>
                            <div>
                              <span className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#D10043]">
                                {job.department}
                              </span>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                  {job.is_active ? 'Hiring Now' : 'Closed'}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Bookmark Toggle Button */}
                          <button
                            type="button"
                            onClick={() => handleToggleBookmark(job.id)}
                            title={isBookmarked ? 'Remove Bookmark' : 'Save Job'}
                            className={`p-2.5 rounded-xl border transition-all ${isBookmarked
                                ? 'bg-pink-50 text-[#D10043] border-pink-200 shadow-xs'
                                : 'text-slate-300 hover:text-[#D10043] hover:bg-pink-50/50 border-slate-100'
                              }`}
                          >
                            <Bookmark size={18} className={isBookmarked ? 'fill-[#D10043]' : ''} />
                          </button>
                        </div>

                        {/* Title */}
                        <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight group-hover:text-[#D10043] transition-colors line-clamp-2 leading-snug mb-3">
                          {job.title}
                        </h3>

                        {/* Attribute Badges */}
                        <div className="flex flex-wrap items-center gap-2 mb-4 text-xs font-bold text-slate-600">
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-50 border border-slate-100">
                            <MapPin size={13} className="text-[#D10043]" />
                            {job.location}
                          </span>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-50 border border-slate-100">
                            <Clock size={13} className="text-slate-400" />
                            {job.job_type}
                          </span>
                          {job.salary_range && (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-slate-50 border border-slate-100 text-slate-700">
                              <Coins size={13} className="text-amber-500" />
                              {job.salary_range}
                            </span>
                          )}
                        </div>

                        {/* Role Description Snippet */}
                        <p className="text-slate-500 text-xs sm:text-sm font-normal leading-relaxed line-clamp-3 mb-5">
                          {job.description || job.skills_requirements || 'Mariwasa Siam Ceramics invites qualified applicants to explore this position.'}
                        </p>

                        {/* Skills Chips */}
                        {skills.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 mb-6">
                            {skills.slice(0, 3).map((skill, sIdx) => (
                              <span
                                key={sIdx}
                                className="px-2.5 py-1 rounded-lg text-[11px] font-bold bg-slate-50 border border-slate-100 text-slate-600"
                              >
                                {skill}
                              </span>
                            ))}
                            {skills.length > 3 && (
                              <span className="px-2 py-1 rounded-lg text-[10px] font-black text-slate-400 bg-slate-50">
                                +{skills.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* ACTION BUTTONS (Details & Apply Now) */}
                      <div className="pt-5 border-t border-slate-100 flex items-center gap-2.5">

                        {/* DETAILS BUTTON */}
                        <button
                          type="button"
                          onClick={() => handleOpenDetails(job)}
                          className="flex-1 py-3.5 px-4 rounded-2xl border border-slate-200/90 hover:border-slate-300 hover:bg-slate-50 text-slate-700 font-black text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all active:scale-[0.98]"
                        >
                          <FileText size={15} className="text-slate-400" />
                          Details
                        </button>

                        {/* APPLY NOW BUTTON */}
                        <button
                          type="button"
                          onClick={() => handleApply(job.id)}
                          disabled={!job.is_active}
                          className={`flex-1 py-3.5 px-4 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-all shadow-md ${job.is_active
                              ? 'bg-[#D10043] text-white shadow-[#D10043]/20 hover:bg-slate-900 active:scale-[0.98]'
                              : 'bg-slate-100 text-slate-400 cursor-not-allowed shadow-none'
                            }`}
                        >
                          {job.is_active ? (
                            <>
                              Apply
                              <ArrowRight size={15} />
                            </>
                          ) : (
                            'Closed'
                          )}
                        </button>

                      </div>

                    </div>
                  );
                })}
              </div>

            ) : (

              /* LIST VIEW */
              <div className="space-y-4">
                {paginatedJobs.map((job) => {
                  const isBookmarked = bookmarkedIds.includes(job.id);
                  const skills = typeof job.skills_requirements === 'string'
                    ? job.skills_requirements.split(/[,;\n•]+/).map((s) => s.trim()).filter(Boolean)
                    : [];

                  return (
                    <div
                      key={job.id}
                      className="group bg-white rounded-3xl p-6 sm:p-7 border border-slate-100 hover:border-[#D10043]/20 hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 flex flex-col lg:flex-row lg:items-center justify-between gap-6"
                    >
                      {/* Left: Info */}
                      <div className="flex items-start gap-4 sm:gap-5 flex-1 min-w-0">
                        <div className="w-14 h-14 rounded-2xl bg-slate-50 group-hover:bg-[#D10043]/10 border border-slate-100 flex items-center justify-center text-slate-400 group-hover:text-[#D10043] transition-colors shrink-0">
                          <Building2 size={24} />
                        </div>

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2 mb-1">
                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#D10043]">
                              {job.department}
                            </span>
                            <span className="text-slate-300">•</span>
                            <span className="text-xs font-bold text-slate-500">
                              {job.location}
                            </span>
                            <span className="text-slate-300">•</span>
                            <span className="text-xs font-bold text-slate-500">
                              {job.job_type}
                            </span>
                          </div>

                          <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight group-hover:text-[#D10043] transition-colors truncate">
                            {job.title}
                          </h3>

                          <p className="text-slate-500 text-xs sm:text-sm font-normal line-clamp-1 mt-1 max-w-2xl">
                            {job.description || job.skills_requirements || 'Mariwasa position open for immediate consideration.'}
                          </p>

                          {skills.length > 0 && (
                            <div className="flex flex-wrap items-center gap-1.5 mt-2.5">
                              {skills.slice(0, 4).map((skill, sIdx) => (
                                <span
                                  key={sIdx}
                                  className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-slate-50 border border-slate-100 text-slate-600"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Right: Actions */}
                      <div className="flex items-center gap-2.5 shrink-0 pt-4 lg:pt-0 border-t lg:border-t-0 border-slate-100">

                        {/* Bookmark Button */}
                        <button
                          type="button"
                          onClick={() => handleToggleBookmark(job.id)}
                          title={isBookmarked ? 'Remove Bookmark' : 'Save Job'}
                          className={`p-3 rounded-2xl border transition-all ${isBookmarked
                              ? 'bg-pink-50 text-[#D10043] border-pink-200'
                              : 'text-slate-400 hover:text-[#D10043] hover:bg-pink-50/50 border-slate-200'
                            }`}
                        >
                          <Bookmark size={18} className={isBookmarked ? 'fill-[#D10043]' : ''} />
                        </button>

                        {/* Details Button */}
                        <button
                          type="button"
                          onClick={() => handleOpenDetails(job)}
                          className="px-5 py-3 rounded-2xl border border-slate-200 hover:bg-slate-50 text-slate-700 font-black text-xs uppercase tracking-wider flex items-center gap-2 transition-all"
                        >
                          <FileText size={15} className="text-slate-400" />
                          Details
                        </button>

                        {/* Apply Button */}
                        <button
                          type="button"
                          onClick={() => handleApply(job.id)}
                          disabled={!job.is_active}
                          className={`px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-wider flex items-center gap-2 transition-all shadow-md ${job.is_active
                              ? 'bg-[#D10043] text-white shadow-[#D10043]/20 hover:bg-slate-900 active:scale-[0.98]'
                              : 'bg-slate-100 text-slate-400 cursor-not-allowed shadow-none'
                            }`}
                        >
                          {job.is_active ? (
                            <>
                              Apply Now
                              <ArrowRight size={15} />
                            </>
                          ) : (
                            'Closed'
                          )}
                        </button>

                      </div>

                    </div>
                  );
                })}
              </div>

            )}

            {/* RESPONSIVE PAGINATION BAR */}
            {totalPages > 1 && (
              <div className="mt-12 sm:mt-16 flex flex-col sm:flex-row items-center justify-between gap-4 bg-white px-6 sm:px-8 py-5 sm:py-6 rounded-3xl shadow-lg shadow-slate-200/50 border border-slate-100">
                <div className="text-xs sm:text-sm text-slate-400 font-bold uppercase tracking-wider text-center sm:text-left">
                  Showing <span className="text-slate-900">{(currentPage - 1) * itemsPerPage + 1}</span> - <span className="text-slate-900">{Math.min(currentPage * itemsPerPage, filteredJobs.length)}</span> of <span className="text-slate-900">{filteredJobs.length}</span> positions
                </div>

                <div className="flex items-center gap-3 sm:gap-5">
                  <button
                    type="button"
                    onClick={handlePrevPage}
                    disabled={currentPage === 1}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white border border-slate-200 text-xs font-black uppercase tracking-wider text-slate-600 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-all active:scale-95"
                  >
                    <ArrowRight size={15} className="rotate-180" />
                    Prev
                  </button>

                  <div className="flex items-center gap-2">
                    <span className="w-9 h-9 flex items-center justify-center rounded-xl bg-slate-900 text-white font-black text-xs">
                      {currentPage}
                    </span>
                    <span className="text-xs font-bold text-slate-400">/ {totalPages}</span>
                  </div>

                  <button
                    type="button"
                    onClick={handleNextPage}
                    disabled={currentPage === totalPages}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#D10043] text-white text-xs font-black uppercase tracking-wider hover:bg-slate-900 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-md shadow-[#D10043]/20 active:scale-95"
                  >
                    Next
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            )}

          </section>

        </main>
      </div>

      {/* CANDIDATE JOB DETAILS MODAL */}
      <CandidateJobDetailsModal
        isOpen={isDetailsModalOpen}
        onClose={handleCloseDetails}
        job={selectedJobForDetails}
        onApply={handleApply}
        isBookmarked={selectedJobForDetails ? bookmarkedIds.includes(selectedJobForDetails.id) : false}
        onToggleBookmark={handleToggleBookmark}
      />

    </div>
  );
};

export default FindJob;
