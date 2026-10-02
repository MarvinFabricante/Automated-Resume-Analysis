import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import jobService from '../../../services/jobService';
import {
  ChevronDown,
  Briefcase,
  Search,
  X,
  MapPin,
  Clock,
  ArrowRight,
  CircleDot
} from 'lucide-react';
import Footer from '../../../components/layout/Footer';
import Header from '../../../components/layout/Header';

const CareersPage = () => {
  const navigate = useNavigate();

  const [jobs, setJobs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDept, setSelectedDept] = useState('All Departments');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const JOBS_PER_PAGE = 10;

  useEffect(() => {
    const fetchPublicJobs = async () => {
      try {
        setIsLoading(true);
        const response = await jobService.getAllJobs();

        const rawData = Array.isArray(response.data) ? response.data : [];

        const dynamicJobs = rawData.map(job => ({
          ...job,
          title: job.job_title || "Untitled Position",
          department: job.department || "General",
          location: job.location || "Philippines",
          job_type: job.job_type || "Full-time",
          salary_range: job.salary_range || "Competitive",
          is_active: Boolean(job.is_active),
          skills_requirements: job.skills_requirements || job.description || "No specific requirements listed."
        }));

        setJobs(dynamicJobs);
      } catch (error) {
        console.error("Error loading careers:", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPublicJobs();
  }, []);

  // Reset to first page when search or department changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, selectedDept]);

  // Scroll to top when page changes
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' });
  }, [currentPage]);

  const departments = useMemo(() => {
    return ['All Departments', ...new Set(jobs.map(job => job.department))];
  }, [jobs]);

  const filteredJobs = useMemo(() => {
    return jobs.filter(job => {
      const matchesSearch =
        job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        job.department.toLowerCase().includes(searchTerm.toLowerCase()) ||
        job.skills_requirements.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesDept = selectedDept === 'All Departments' || job.department === selectedDept;

      return matchesSearch && matchesDept;
    });
  }, [jobs, searchTerm, selectedDept]);

  // Pagination Logic
  const totalPages = Math.ceil(filteredJobs.length / JOBS_PER_PAGE);
  const paginatedJobs = filteredJobs.slice(
    (currentPage - 1) * JOBS_PER_PAGE,
    currentPage * JOBS_PER_PAGE
  );

  const searchSuggestions = searchTerm
    ? [...new Set(jobs
      .filter(job => job.title.toLowerCase().includes(searchTerm.toLowerCase()))
      .map(job => job.title))]
    : [];

  return (
    <div className="bg-[transparent] text-gray-800 antialiased font-sans min-h-screen flex flex-col selection:bg-pink-100 selection:text-pink-900">
      <Helmet>
        <title>Careers - Mariwasa Portal</title>
      </Helmet>
      <Header />

      <main className="flex-grow max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12 md:py-16 lg:py-24 w-full">

        <div className="text-center mb-8 sm:mb-16 relative">
          <div className="inline-block p-1.5 rounded-full bg-white shadow-sm border border-gray-100 mb-4 sm:mb-8">
            <div className="flex items-center gap-2 sm:gap-3 px-3 py-1">
              <Briefcase size={16} className="text-[#D60041]" />
              <span className="text-[11px] sm:text-xs font-semibold uppercase tracking-wider text-gray-600">Open Positions</span>
            </div>
          </div>
          <h1 className="text-3xl sm:text-4xl md:text-6xl font-normal tracking-tight text-gray-900 mb-3 sm:mb-6 leading-tight">
            Find Your <span className="font-semibold text-[#D60041]">Career</span> at Mariwasa
          </h1>
          <p className="text-gray-600 text-sm sm:text-lg md:text-xl max-w-2xl mx-auto font-normal leading-relaxed px-2">
            Explore exciting opportunities in ceramic manufacturing. Join our team of innovators and help build the homes of tomorrow.
          </p>
        </div>

        <div className="w-full mb-8 sm:mb-16 relative z-20">
          <div className="bg-white p-2.5 sm:p-3 rounded-2xl md:rounded-full shadow-sm border border-gray-100 flex flex-col md:flex-row gap-3 relative">
            <div className="relative flex-grow">
              <Search className="absolute left-5 sm:left-6 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="text"
                placeholder="Search jobs by title or skills..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setShowSuggestions(true);
                }}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                className="w-full pl-12 sm:pl-14 pr-10 sm:pr-12 py-3 sm:py-3.5 bg-gray-50/50 border border-transparent hover:bg-gray-50 focus:bg-white focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all text-xs sm:text-sm font-medium outline-none z-30 relative rounded-xl sm:rounded-full"
              />
              {searchTerm && (
                <button
                  onClick={() => setSearchTerm('')}
                  className="absolute right-3.5 sm:right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700 bg-gray-200/50 hover:bg-gray-200 p-1.5 rounded-full transition-colors z-40"
                >
                  <X size={14} />
                </button>
              )}

              {showSuggestions && searchSuggestions.length > 0 && (
                <div className="absolute top-[calc(100%+8px)] left-0 w-full bg-white border border-gray-100 rounded-2xl md:rounded-[24px] shadow-lg z-20 overflow-hidden flex flex-col py-2">
                  {searchSuggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        setSearchTerm(suggestion);
                        setShowSuggestions(false);
                      }}
                      className="w-full text-left px-5 sm:px-6 py-2.5 sm:py-3 hover:bg-red-50 text-xs sm:text-sm font-medium text-gray-700 transition-colors flex items-center gap-3"
                    >
                      <Search size={14} className="text-gray-400" />
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className="relative w-full md:w-64 shrink-0">
              <select
                value={selectedDept}
                onChange={(e) => setSelectedDept(e.target.value)}
                className="w-full appearance-none px-5 sm:px-6 py-3 sm:py-3.5 bg-gray-50/50 border border-transparent hover:bg-gray-50 rounded-xl sm:rounded-full focus:bg-white focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] text-xs sm:text-sm font-medium text-gray-700 cursor-pointer outline-none transition-all"
              >
                {departments.map(dept => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
              </select>
              <ChevronDown className="absolute right-5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
            </div>
          </div>

          <div className="mt-6 sm:mt-8 flex items-center justify-center gap-3 sm:gap-4">
            <div className="h-px flex-grow max-w-[40px] sm:max-w-[60px] bg-gray-200"></div>
            <p className="text-[11px] sm:text-xs font-semibold text-gray-500 uppercase tracking-wider text-center">
              {isLoading ? 'Loading Positions...' : `Showing ${filteredJobs.length} Career Opportunities`}
            </p>
            <div className="h-px flex-grow max-w-[40px] sm:max-w-[60px] bg-gray-200"></div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-8 sm:mb-12 items-stretch">
          {isLoading ? (
            <div className="col-span-full py-20 text-center text-gray-400 animate-pulse">
              Fetching the latest opportunities...
            </div>
          ) : paginatedJobs.length > 0 ? (
            paginatedJobs.map((job) => (
              <div 
                key={job.id} 
                onClick={() => navigate(`/apply/${job.job_id}`, { state: { job } })}
                className="bg-white p-5 sm:p-6 md:p-8 rounded-2xl sm:rounded-[32px] border border-gray-100 shadow-sm hover:shadow-md transition-all duration-300 group flex flex-col relative overflow-hidden cursor-pointer"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-red-50 rounded-bl-[100px] opacity-0 group-hover:opacity-50 transition-opacity duration-300"></div>

                <div className="flex justify-between items-start gap-2 mb-4 sm:mb-6 relative z-10">
                  <div>
                    <span className="inline-block px-3 py-1 rounded-full bg-red-50 text-[10px] font-bold uppercase tracking-wider text-[#D60041] mb-2 sm:mb-4">
                      {job.department}
                    </span>
                    <h3 className="text-xl sm:text-2xl font-semibold text-gray-900 group-hover:text-[#D60041] transition-colors leading-tight pr-2 tracking-tight">
                      {job.title}
                    </h3>
                  </div>
                  <div className={`shrink-0 flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${job.is_active ? 'bg-green-50 text-green-700 ring-1 ring-green-600/20' : 'bg-gray-100 text-gray-500 ring-1 ring-gray-200'}`}>
                    <CircleDot size={10} className={job.is_active ? "animate-pulse" : ""} />
                    {job.is_active ? 'Active' : 'Closed'}
                  </div>
                </div>

                <p className="text-gray-600 text-xs sm:text-sm leading-relaxed mb-6 sm:mb-8 font-normal line-clamp-3 relative z-10 flex-grow">
                  {job.skills_requirements}
                </p>

                <div className="bg-gray-50/50 rounded-xl sm:rounded-[24px] p-4 sm:p-5 mb-6 sm:mb-8 mt-auto relative z-10 border border-gray-100">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-3 sm:gap-y-4">
                    <div className="flex items-center gap-3 text-xs font-medium text-gray-600">
                      <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white flex items-center justify-center shadow-sm shrink-0">
                        <MapPin size={14} className="text-gray-400" />
                      </div>
                      <span className="truncate">{job.location}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs font-medium text-gray-600">
                      <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white flex items-center justify-center shadow-sm shrink-0">
                        <Clock size={14} className="text-gray-400" />
                      </div>
                      <span>{job.job_type}</span>
                    </div>
                    <div className="sm:col-span-2 flex items-center gap-3 text-xs font-semibold text-gray-900">
                      <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-white flex items-center justify-center shadow-sm shrink-0">
                        <div className="w-2.5 h-2.5 rounded-full bg-[#D60041]" />
                      </div>
                      <span>{job.salary_range}</span>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-2.5 sm:gap-3 relative z-10">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/job-details/${job.job_id}`, { state: { job } });
                    }}
                    className="flex-1 py-3 sm:py-3.5 rounded-full border border-gray-200 font-medium text-xs sm:text-sm text-gray-700 hover:bg-gray-50 hover:border-gray-300 transition-all text-center"
                  >
                    Details
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/apply/${job.job_id}`, { state: { job } });
                    }}
                    disabled={!job.is_active}
                    className="flex-[2] py-3 sm:py-3.5 rounded-full bg-[#1A1A1A] text-white font-medium text-xs sm:text-sm flex items-center justify-center gap-2 hover:bg-[#D60041] transition-colors disabled:opacity-50 disabled:cursor-not-allowed group/btn text-center"
                  >
                    {job.is_active ? 'Apply Now' : 'Closed'}
                    {job.is_active && <ArrowRight size={16} className="group-hover/btn:translate-x-1 transition-transform" />}
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full py-16 sm:py-24 text-center bg-white rounded-2xl sm:rounded-[32px] border border-dashed border-gray-200 shadow-sm px-4">
              <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gray-50 text-gray-300 rounded-full flex items-center justify-center mx-auto mb-4 sm:mb-6">
                <Search size={28} />
              </div>
              <h3 className="text-gray-900 font-semibold text-lg sm:text-xl mb-2">No matching roles found</h3>
              <p className="text-gray-500 text-xs sm:text-sm mb-6 sm:mb-8 max-w-sm mx-auto">We couldn't find any positions matching your search. Try adjusting your filters or search terms.</p>
              <button
                onClick={() => { setSearchTerm(''); setSelectedDept('All Departments'); }}
                className="px-6 sm:px-8 py-2.5 sm:py-3 rounded-full bg-red-50 text-[#D60041] font-medium text-xs sm:text-sm hover:bg-red-100 transition-colors"
              >
                Clear All Filters
              </button>
            </div>
          )}
        </div>

        {/* Pagination UI */}
        {filteredJobs.length > JOBS_PER_PAGE && (
          <div className="mt-8 sm:mt-12 flex flex-col sm:flex-row items-center justify-between gap-4 sm:gap-6 bg-white px-5 sm:px-8 py-4 sm:py-6 rounded-2xl sm:rounded-[32px] shadow-sm border border-gray-100 mb-12 sm:mb-24">
            <div className="text-xs sm:text-sm text-gray-500 font-medium text-center sm:text-left">
              Showing <span className="font-bold text-gray-900">{((currentPage - 1) * JOBS_PER_PAGE) + 1}</span> to <span className="font-bold text-gray-900">{Math.min(currentPage * JOBS_PER_PAGE, filteredJobs.length)}</span> of <span className="font-bold text-gray-900">{filteredJobs.length}</span> positions
            </div>

            <div className="flex items-center gap-3 sm:gap-6">
              <button
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="group flex items-center gap-1.5 sm:gap-2 px-4 sm:px-6 py-2.5 sm:py-3 rounded-full bg-white border border-gray-100 shadow-sm text-xs sm:text-sm font-semibold text-gray-600 hover:bg-gray-50 hover:border-gray-200 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
              >
                <ArrowRight size={16} className="rotate-180 group-hover:-translate-x-1 transition-transform" />
                <span>Prev</span>
              </button>

              <div className="flex items-center gap-2 sm:gap-3">
                <span className="text-[10px] sm:text-xs font-bold text-gray-400 uppercase tracking-widest hidden xs:inline">Page</span>
                <div className="px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-white border border-gray-100 shadow-inner font-black text-[#D60041] text-xs sm:text-sm">
                  {currentPage}
                </div>
                <span className="text-[10px] sm:text-xs font-bold text-gray-400 uppercase tracking-widest">/ {totalPages}</span>
              </div>

              <button
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="group flex items-center gap-1.5 sm:gap-2 px-4 sm:px-6 py-2.5 sm:py-3 rounded-full bg-[#1A1A1A] text-white shadow-lg text-xs sm:text-sm font-semibold hover:bg-[#D60041] disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
              >
                <span>Next</span>
                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>
        )}

      </main>

      <Footer />
    </div>
  );
};

export default CareersPage;