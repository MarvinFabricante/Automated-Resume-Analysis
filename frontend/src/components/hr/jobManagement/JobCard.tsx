import React from 'react';
import { 
  Briefcase, Building2, MapPin, Tag, 
  Eye, Edit3, Archive, ArchiveRestore, Trash2, Clock 
} from 'lucide-react';
import { Job } from '../../../types';

interface JobCardProps {
  job: Job;
  onEdit: (job: Job) => void;
  onView: (job: Job) => void;
  onArchive: (jobId: string | number | undefined, title: string) => void;
  onUnarchive: (jobId: string | number | undefined, title: string) => void;
  onDelete: (jobId: string | number | undefined, title: string) => void;
}

const JobCard: React.FC<JobCardProps> = ({ job, onEdit, onView, onArchive, onUnarchive, onDelete }) => {
  const skillsArray = typeof job.skills_requirements === 'string'
    ? job.skills_requirements.split(',').map((s: string) => s.trim()).filter(Boolean)
    : Array.isArray(job.skills_requirements)
    ? job.skills_requirements.filter(Boolean)
    : [];

  const jobTitle = job.job_title || job.title || 'Untitled Position';
  const jobId = job.job_id || String(job.id);
  const jobType = job.job_type || job.employment_type;

  return (
    <div className="bg-white p-4 sm:p-6 md:p-7 rounded-2xl sm:rounded-3xl border border-slate-100 shadow-xs hover:shadow-lg hover:border-pink-100 transition-all duration-300 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-5 sm:gap-6 group">
      {/* Main Details Section */}
      <div className="flex items-start gap-3.5 sm:gap-5 w-full lg:w-auto flex-grow min-w-0">
        {/* Job Icon */}
        <div className="w-11 h-11 sm:w-13 sm:h-13 rounded-xl sm:rounded-2xl border border-pink-100/80 bg-gradient-to-br from-pink-50 to-rose-50/70 shadow-xs group-hover:scale-105 transition-transform duration-300 flex items-center justify-center shrink-0 mt-0.5">
          <Briefcase className="w-5 h-5 sm:w-6 sm:h-6 text-[#D60041]" />
        </div>

        {/* Content Body */}
        <div className="flex-grow min-w-0">
          {/* Header Row: Title & Status/ID Badges */}
          <div className="flex flex-wrap items-center justify-between gap-2 sm:gap-3 mb-2">
            <h3 className="text-base sm:text-lg md:text-xl font-black text-slate-900 group-hover:text-[#D60041] transition-colors tracking-tight break-words">
              {jobTitle}
            </h3>

            {/* Badges Container */}
            <div className="flex items-center gap-2 shrink-0">
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border shadow-2xs ${
                job.is_active 
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200" 
                  : "bg-slate-100 text-slate-700 border-slate-300"
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${job.is_active ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
                {job.is_active ? "Active" : "Archived"}
              </span>

              {jobId && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-100 text-slate-600 border border-slate-200 shadow-2xs">
                  <Tag size={12} className="text-slate-400" />
                  <span className="tracking-tight">{jobId}</span>
                </span>
              )}
            </div>
          </div>

          {/* Position Metadata Badges */}
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 mb-3">
            {job.department && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/80 px-2.5 py-1 rounded-lg shadow-2xs">
                <Building2 size={13} className="text-slate-500 shrink-0" />
                <span className="truncate max-w-[160px] sm:max-w-none">{job.department}</span>
              </span>
            )}
            {job.location && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/80 px-2.5 py-1 rounded-lg shadow-2xs">
                <MapPin size={13} className="text-slate-500 shrink-0" />
                <span className="truncate max-w-[160px] sm:max-w-none">{job.location}</span>
              </span>
            )}
            {jobType && (
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/80 px-2.5 py-1 rounded-lg shadow-2xs">
                <Clock size={13} className="text-slate-500 shrink-0" />
                <span>{jobType}</span>
              </span>
            )}
          </div>

          {/* Structured Key Details: Salary & Skills */}
          {(job.salary_range || skillsArray.length > 0) && (
            <div className="bg-slate-50/80 p-3 sm:p-3.5 rounded-xl border border-slate-100 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              {/* Salary Section */}
              {job.salary_range && (
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500 shrink-0">
                    Salary:
                  </span>
                  <div className="inline-flex items-baseline gap-1 text-xs sm:text-sm font-black text-[#D60041] bg-white px-2.5 py-1 rounded-lg border border-rose-200/70 shadow-2xs">
                    <span>{job.salary_range}</span>
                    <span className="text-[11px] font-semibold text-slate-500">/ mo</span>
                  </div>
                </div>
              )}

              {/* Skills Requirements */}
              {skillsArray.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-500 shrink-0 mr-1">
                    Skills:
                  </span>
                  <div className="inline-flex flex-wrap gap-1.5 align-middle">
                    {skillsArray.slice(0, 4).map((skill: string, idx: number) => (
                      <span
                        key={idx}
                        className="bg-white border border-slate-200 text-slate-700 text-xs font-semibold px-2.5 py-0.5 rounded-md shadow-2xs hover:border-pink-300 transition-colors"
                      >
                        {skill}
                      </span>
                    ))}
                    {skillsArray.length > 4 && (
                      <span className="bg-slate-200/80 text-slate-600 text-xs font-bold px-2 py-0.5 rounded-md">
                        +{skillsArray.length - 4} more
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons: Responsive 2x2 grid on mobile, row on desktop */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:flex lg:flex-row gap-2 sm:gap-2.5 w-full lg:w-auto shrink-0 pt-3.5 lg:pt-0 border-t lg:border-t-0 border-slate-100">
        <button
          type="button"
          onClick={() => onView(job)}
          className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-2.5 bg-[#D60041] text-white rounded-xl text-xs font-bold hover:bg-[#b50037] active:scale-95 transition-all shadow-xs cursor-pointer min-h-[40px]"
          title="View full job details"
        >
          <Eye size={15} className="shrink-0" />
          <span>View</span>
        </button>

        <button
          type="button"
          onClick={() => onEdit(job)}
          className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-xs font-bold hover:bg-slate-50 hover:text-slate-900 active:scale-95 transition-all shadow-2xs cursor-pointer min-h-[40px]"
          title="Edit job requirements"
        >
          <Edit3 size={15} className="shrink-0" />
          <span>Edit</span>
        </button>

        {job.is_active ? (
          <button
            type="button"
            onClick={() => onArchive(job.job_id || job.id, jobTitle)}
            className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-2.5 bg-amber-50 border border-amber-200/90 text-amber-800 rounded-xl text-xs font-bold hover:bg-amber-100 active:scale-95 transition-all shadow-2xs cursor-pointer min-h-[40px]"
            title="Archive this job"
          >
            <Archive size={15} className="shrink-0" />
            <span>Archive</span>
          </button>
        ) : (
          <button
            type="button"
            onClick={() => onUnarchive(job.job_id || job.id, jobTitle)}
            className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-2.5 bg-emerald-50 border border-emerald-200/90 text-emerald-800 rounded-xl text-xs font-bold hover:bg-emerald-100 active:scale-95 transition-all shadow-2xs cursor-pointer min-h-[40px]"
            title="Unarchive this job"
          >
            <ArchiveRestore size={15} className="shrink-0" />
            <span>Unarchive</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => onDelete(job.job_id || job.id, jobTitle)}
          className="flex items-center justify-center gap-1.5 px-3 sm:px-4 py-2.5 bg-rose-50 border border-rose-200/90 text-rose-800 rounded-xl text-xs font-bold hover:bg-rose-100 active:scale-95 transition-all shadow-2xs cursor-pointer min-h-[40px]"
          title="Delete job permanently"
        >
          <Trash2 size={15} className="shrink-0" />
          <span>Remove</span>
        </button>
      </div>
    </div>
  );
};

export default JobCard;
