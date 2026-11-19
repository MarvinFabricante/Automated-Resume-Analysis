import React from 'react';
import {
  Briefcase,
  Building2,
  MapPin,
  Tag,
  Eye,
  Edit3,
  Archive,
  ArchiveRestore,
  Trash2,
  Clock,
  Sliders,
  Users,
  Wallet,
} from 'lucide-react';
import { Job, DEFAULT_JOB_SCORING_WEIGHTS } from '../../../types';
import {
  WEIGHT_FIELDS,
  areWeightsEqual,
  formatPrioritySummary,
} from '../../modals/hr/JobScoringWeightsEditor';

interface JobCardProps {
  job: Job;
  onEdit: (job: Job) => void;
  onView: (job: Job) => void;
  onArchive: (jobId: string | number | undefined, title: string) => void;
  onUnarchive: (jobId: string | number | undefined, title: string) => void;
  onDelete: (jobId: string | number | undefined, title: string) => void;
}

const JobCard: React.FC<JobCardProps> = ({
  job,
  onEdit,
  onView,
  onArchive,
  onUnarchive,
  onDelete,
}) => {
  const skillsArray =
    typeof job.skills_requirements === 'string'
      ? job.skills_requirements.split(',').map((s: string) => s.trim()).filter(Boolean)
      : Array.isArray(job.skills_requirements)
      ? job.skills_requirements.filter(Boolean)
      : [];

  const jobTitle = job.job_title || job.title || 'Untitled Position';
  const jobId = job.job_id || String(job.id);
  const jobType = job.job_type || job.employment_type;
  const applicantCount = Number(job.applicant_count ?? 0);
  const activeWeights = job.scoring_weights || DEFAULT_JOB_SCORING_WEIGHTS;
  const isCustomWeights = Boolean(
    job.scoring_weights && !areWeightsEqual(job.scoring_weights, DEFAULT_JOB_SCORING_WEIGHTS)
  );

  return (
    <div
      className={`bg-white rounded-2xl sm:rounded-3xl border transition-all duration-300 overflow-hidden group hover:shadow-lg ${
        job.is_active
          ? 'border-gray-200/80 hover:border-pink-200'
          : 'border-slate-200/80 bg-slate-50/40 hover:border-slate-300'
      }`}
    >
      {/* Subtle Top Status Bar */}
      <div
        className={`h-1 w-full ${
          job.is_active
            ? 'bg-gradient-to-r from-[#D10043] via-rose-400 to-pink-300'
            : 'bg-slate-300'
        }`}
      />

      <div className="p-5 sm:p-6 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-5">
        {/* Left Main Content */}
        <div className="flex items-start gap-4 w-full lg:w-auto flex-grow min-w-0">
          {/* Icon */}
          <div
            className={`w-12 h-12 rounded-2xl border flex items-center justify-center shrink-0 mt-0.5 transition-transform duration-300 group-hover:scale-105 ${
              job.is_active
                ? 'border-pink-100 bg-gradient-to-br from-pink-50 to-rose-50 text-[#D10043]'
                : 'border-slate-200 bg-slate-100 text-slate-500'
            }`}
          >
            <Briefcase className="w-5 h-5" />
          </div>

          <div className="flex-grow min-w-0 space-y-3">
            {/* Title + Status + ID + Applicant Count */}
            <div className="flex flex-wrap items-center justify-between gap-2.5">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    onClick={() => onView(job)}
                    className="text-left text-base sm:text-lg font-extrabold text-slate-900 group-hover:text-[#D10043] transition-colors tracking-tight break-words cursor-pointer"
                  >
                    {jobTitle}
                  </button>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider border ${
                      job.is_active
                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                        : 'bg-slate-100 text-slate-600 border-slate-200'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        job.is_active ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'
                      }`}
                    />
                    {job.is_active ? 'Active' : 'Archived'}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 shrink-0">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold bg-indigo-50/80 text-indigo-700 border border-indigo-100">
                  <Users size={13} className="shrink-0" />
                  <span>
                    {applicantCount} {applicantCount === 1 ? 'Applicant' : 'Applicants'}
                  </span>
                </span>
                {jobId && (
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs font-mono font-bold bg-slate-100 text-slate-600 border border-slate-200/80">
                    <Tag size={11} className="text-slate-400" />
                    <span>{jobId}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Metadata Row */}
            <div className="flex flex-wrap items-center gap-2">
              {job.department && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/70 px-2.5 py-1 rounded-lg">
                  <Building2 size={13} className="text-slate-400 shrink-0" />
                  <span className="truncate max-w-[180px] sm:max-w-none">{job.department}</span>
                </span>
              )}
              {job.location && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/70 px-2.5 py-1 rounded-lg">
                  <MapPin size={13} className="text-slate-400 shrink-0" />
                  <span className="truncate max-w-[180px] sm:max-w-none">{job.location}</span>
                </span>
              )}
              {jobType && (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 bg-slate-50 border border-slate-200/70 px-2.5 py-1 rounded-lg">
                  <Clock size={13} className="text-slate-400 shrink-0" />
                  <span>{jobType}</span>
                </span>
              )}
              {job.salary_range && (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold text-[#D10043] bg-rose-50/70 border border-rose-200/70 px-2.5 py-1 rounded-lg">
                  <Wallet size={13} className="shrink-0" />
                  <span>{job.salary_range}</span>
                </span>
              )}
            </div>

            {/* Bottom Strip: Skills + Scoring Weights Mini Visualization */}
            <div className="pt-2.5 border-t border-gray-100 flex flex-col xl:flex-row xl:items-center justify-between gap-3">
              {/* Skills */}
              {skillsArray.length > 0 ? (
                <div className="flex flex-wrap items-center gap-1.5 min-w-0">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1">
                    Skills:
                  </span>
                  {skillsArray.slice(0, 4).map((skill: string, idx: number) => (
                    <span
                      key={idx}
                      className="bg-slate-50 border border-slate-200/80 text-slate-700 text-xs font-semibold px-2.5 py-0.5 rounded-lg"
                    >
                      {skill}
                    </span>
                  ))}
                  {skillsArray.length > 4 && (
                    <span className="bg-slate-100 text-slate-500 text-xs font-bold px-2 py-0.5 rounded-lg">
                      +{skillsArray.length - 4} more
                    </span>
                  )}
                </div>
              ) : (
                <span className="text-xs text-slate-400 italic">No required skills specified</span>
              )}

              {/* Scoring Weights Pill + Micro Bar */}
              <div
                className={`inline-flex items-center gap-2.5 px-3 py-1.5 rounded-xl border text-xs shrink-0 self-start xl:self-auto ${
                  isCustomWeights
                    ? 'bg-pink-50/60 border-pink-200/80 text-[#D10043]'
                    : 'bg-gray-50 border-gray-200/80 text-gray-600'
                }`}
                title={WEIGHT_FIELDS.map(
                  (f) => `${f.shortLabel}: ${Math.round((activeWeights[f.key] ?? 0) * 100)}%`
                ).join(' | ')}
              >
                <Sliders size={12} className="shrink-0" />
                <span className="font-bold">{formatPrioritySummary(job.scoring_weights)}</span>
                <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden flex shrink-0" aria-hidden="true">
                  {WEIGHT_FIELDS.map((field) => (
                    <div
                      key={field.key}
                      style={{ width: `${Math.round((activeWeights[field.key] ?? 0) * 100)}%` }}
                      className={`${field.color} h-full`}
                    />
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Action Controls */}
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap lg:flex-nowrap items-center gap-2 w-full lg:w-auto shrink-0 pt-3 lg:pt-0 border-t lg:border-t-0 border-gray-100">
          <button
            type="button"
            onClick={() => onView(job)}
            className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-gray-900 text-white rounded-xl text-xs font-bold hover:bg-black active:scale-95 transition-all cursor-pointer min-h-[38px]"
            title="Preview full job details"
          >
            <Eye size={14} className="shrink-0" />
            <span>Preview</span>
          </button>

          <button
            type="button"
            onClick={() => onEdit(job)}
            className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl text-xs font-bold hover:border-[#D10043]/40 hover:text-[#D10043] hover:bg-pink-50/30 active:scale-95 transition-all cursor-pointer min-h-[38px]"
            title="Edit job details & scoring weights"
          >
            <Edit3 size={14} className="shrink-0" />
            <span>Edit</span>
          </button>

          {job.is_active ? (
            <button
              type="button"
              onClick={() => onArchive(job.job_id || job.id, jobTitle)}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-amber-50/80 border border-amber-200 text-amber-800 rounded-xl text-xs font-bold hover:bg-amber-100 active:scale-95 transition-all cursor-pointer min-h-[38px]"
              title="Archive job posting"
            >
              <Archive size={14} className="shrink-0" />
              <span>Archive</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onUnarchive(job.job_id || job.id, jobTitle)}
              className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-emerald-50/80 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold hover:bg-emerald-100 active:scale-95 transition-all cursor-pointer min-h-[38px]"
              title="Restore job posting"
            >
              <ArchiveRestore size={14} className="shrink-0" />
              <span>Restore</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => onDelete(job.job_id || job.id, jobTitle)}
            aria-label={`Remove ${jobTitle}`}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 bg-white border border-gray-200 text-gray-500 rounded-xl text-xs font-bold hover:bg-rose-50 hover:border-rose-200 hover:text-rose-700 active:scale-95 transition-all cursor-pointer min-h-[38px]"
            title="Delete job permanently"
          >
            <Trash2 size={14} className="shrink-0" />
            <span className="sm:hidden">Remove</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default JobCard;
