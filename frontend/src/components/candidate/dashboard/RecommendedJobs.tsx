import React, { useState } from 'react';
import { useNavigate } from '@/utils/navigation';
import {
  Sparkles,
  Briefcase,
  MapPin,
  Building2,
  Bookmark,
  ArrowRight,
  Clock,
  Layers,
  ChevronRight,
  TrendingUp
} from 'lucide-react';
import { useGetJobsQuery } from '../../../redux/api/apiSlice';
import CandidateJobDetailsModal from '../../modals/candidate/CandidateJobDetailsModal';
import { Job } from '../../../types';

interface RecommendedJobsProps {
  onBookmarkChange?: () => void;
}

const RecommendedJobs: React.FC<RecommendedJobsProps> = ({ onBookmarkChange }) => {
  const navigate = useNavigate();
  const { data: jobs = [], isLoading } = useGetJobsQuery({ include_inactive: false });

  // Modal State
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Bookmarking in localStorage
  const [bookmarkedIds, setBookmarkedIds] = useState<(string | number)[]>(() => {
    try {
      const saved = localStorage.getItem('candidate_bookmarked_jobs');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const handleToggleBookmark = (jobId: string | number | undefined, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (!jobId) return;

    let updated: (string | number)[];
    const isSaved = bookmarkedIds.some((id) => String(id) === String(jobId));

    if (isSaved) {
      updated = bookmarkedIds.filter((id) => String(id) !== String(jobId));
    } else {
      updated = [...bookmarkedIds, jobId];
    }

    setBookmarkedIds(updated);
    try {
      localStorage.setItem('candidate_bookmarked_jobs', JSON.stringify(updated));
    } catch (err) {
      console.error('Failed to save bookmarks:', err);
    }
    if (onBookmarkChange) onBookmarkChange();
  };

  const handleOpenDetails = (job: Job) => {
    setSelectedJob(job);
    setIsModalOpen(true);
  };

  const handleApply = (jobId: string | number | undefined) => {
    setIsModalOpen(false);
    if (jobId) {
      navigate(`/candidate/upload-resume/${jobId}`);
    } else {
      navigate('/candidate/findjobs');
    }
  };

  // Only take active jobs, limit to top 3
  const activeJobs = (jobs || []).filter((j: any) => j.is_active !== false);
  const displayJobs = activeJobs.slice(0, 3);

  return (
    <>
      <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-7 md:p-8 shadow-xs space-y-5">
        
        {/* HEADER */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#D10043] flex items-center justify-center shrink-0 border border-rose-100/80">
              <Sparkles size={18} className="text-[#D10043]" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                  Featured Openings
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                  Actively Hiring
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium mt-0.5">
                Current career opportunities matching Mariwasa talent pool
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => navigate('/candidate/findjobs')}
            className="text-xs font-black uppercase tracking-wider text-[#D10043] hover:text-slate-900 transition-colors flex items-center gap-1 self-end sm:self-auto cursor-pointer"
          >
            <span>View All ({activeJobs.length})</span>
            <ChevronRight size={14} />
          </button>
        </div>

        {/* LOADING SKELETON */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="p-4 rounded-2xl border border-slate-100 bg-slate-50/60 animate-pulse space-y-3"
              >
                <div className="h-4 bg-slate-200 rounded w-3/4" />
                <div className="h-3 bg-slate-100 rounded w-1/2" />
                <div className="h-8 bg-slate-200/60 rounded-xl mt-4" />
              </div>
            ))}
          </div>
        ) : displayJobs.length === 0 ? (
          <div className="py-8 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-200 p-6">
            <Briefcase size={26} className="mx-auto text-slate-300 mb-2" />
            <p className="text-xs sm:text-sm font-bold text-slate-700">No active positions posted at the moment</p>
            <p className="text-xs text-slate-400 mt-0.5">Please check back soon as our talent acquisition team updates listings.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
            {displayJobs.map((job: any) => {
              const jobId = job.job_id || job.id;
              const isSaved = bookmarkedIds.some((id) => String(id) === String(jobId));

              return (
                <div
                  key={jobId}
                  onClick={() => handleOpenDetails(job)}
                  className="group relative flex flex-col justify-between border border-slate-200/80 bg-white hover:bg-slate-50/30 rounded-2xl p-4 sm:p-5 hover:border-[#D10043]/30 hover:shadow-md transition-all duration-200 cursor-pointer text-left"
                >
                  <div className="space-y-3">
                    {/* Top Row: Department & Bookmark */}
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[10px] font-black uppercase tracking-wider text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md truncate max-w-[140px]">
                        {job.department || 'General'}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => handleToggleBookmark(jobId, e)}
                        title={isSaved ? 'Remove Bookmark' : 'Save Position'}
                        className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                          isSaved
                            ? 'text-amber-500 bg-amber-50 hover:bg-amber-100'
                            : 'text-slate-300 hover:text-slate-600 hover:bg-slate-100'
                        }`}
                      >
                        <Bookmark size={15} className={isSaved ? 'fill-amber-500' : ''} />
                      </button>
                    </div>

                    {/* Job Title & Location */}
                    <div>
                      <h4 className="text-sm sm:text-base font-black text-slate-900 group-hover:text-[#D10043] transition-colors leading-snug line-clamp-2">
                        {job.title || job.job_title || 'Position'}
                      </h4>
                      <div className="flex items-center gap-1 text-[11px] text-slate-400 font-semibold mt-1">
                        <MapPin size={12} className="shrink-0 text-slate-400" />
                        <span className="truncate">{job.location || 'Sto. Tomas, Batangas'}</span>
                      </div>
                    </div>

                    {/* Tags row */}
                    <div className="flex flex-wrap items-center gap-1.5 pt-1">
                      <span className="text-[10px] font-bold text-slate-600 bg-slate-50 border border-slate-200/60 px-2 py-0.5 rounded-md">
                        {job.job_type || 'Full-Time'}
                      </span>
                      {job.salary_range && job.salary_range !== 'Competitive / TBD' && (
                        <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 border border-emerald-200/50 px-2 py-0.5 rounded-md truncate max-w-[130px]">
                          {job.salary_range}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Bottom Action */}
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <span className="text-[11px] font-bold text-slate-400 group-hover:text-slate-700 transition-colors">
                      Quick View
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] font-black uppercase tracking-wider text-[#D10043] group-hover:translate-x-0.5 transition-transform">
                      Details <ArrowRight size={12} />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>

      {/* JOB DETAILS MODAL */}
      <CandidateJobDetailsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        job={selectedJob}
        onApply={handleApply}
        isBookmarked={selectedJob ? bookmarkedIds.some((id) => String(id) === String(selectedJob.id || selectedJob.job_id)) : false}
        onToggleBookmark={(id) => handleToggleBookmark(id)}
      />
    </>
  );
};

export default RecommendedJobs;
