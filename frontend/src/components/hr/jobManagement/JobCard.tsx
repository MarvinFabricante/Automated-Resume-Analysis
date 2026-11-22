import React from 'react';
import {
  Building2,
  MapPin,
  Eye,
  Edit3,
  Archive,
  ArchiveRestore,
  Trash2,
  Clock,
  Sliders,
  Users,
  Wallet,
  Calendar,
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

const formatShortDate = (dateStr?: string | null): string | null => {
  if (!dateStr) return null;
  const parsed = new Date(dateStr);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

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
  const postedDate = formatShortDate(job.created_at);
  const activeWeights = job.scoring_weights || DEFAULT_JOB_SCORING_WEIGHTS;
  const isCustomWeights = Boolean(
    job.scoring_weights && !areWeightsEqual(job.scoring_weights, DEFAULT_JOB_SCORING_WEIGHTS)
  );

  return (
    <div
      className={`bg-white rounded-2xl border border-l-[3px] transition-all duration-200 overflow-hidden group hover:shadow-md ${
        job.is_active
          ? 'border-slate-200/90 border-l-[#D10043] hover:border-slate-300'
          : 'border-slate-200/80 border-l-slate-300 bg-slate-50/40 hover:border-slate-300'
      }`}
    >
      <div className="p-4 sm:p-5 flex flex-col gap-3.5">
        {/* Top Row: Title, Code, Status + Right Applicant Metric & Actions */}
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3.5">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => onView(job)}
                className="text-left text-base sm:text-lg font-bold text-slate-900 group-hover:text-[#D10043] transition-colors tracking-tight break-words cursor-pointer"
              >
                {jobTitle}
              </button>

              {jobId && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-mono font-semibold bg-slate-100 text-slate-600 border border-slate-200/70">
                  {jobId}
                </span>
              )}

              <span
                className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold border ${
                  job.is_active
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200/80'
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    job.is_active ? 'bg-emerald-500' : 'bg-slate-400'
                  }`}
                />
                {job.is_active ? 'Active' : 'Archived'}
              </span>
            </div>

            {/* Clean Inline Metadata Row */}
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-slate-600">
              {job.department && (
                <span className="inline-flex items-center gap-1.5 font-medium text-slate-700">
                  <Building2 size={13} className="text-slate-400 shrink-0" />
                  <span>{job.department}</span>
                </span>
              )}
              {job.location && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin size={13} className="text-slate-400 shrink-0" />
                  <span>{job.location}</span>
                </span>
              )}
              {jobType && (
                <span className="inline-flex items-center gap-1.5">
                  <Clock size={13} className="text-slate-400 shrink-0" />
                  <span>{jobType}</span>
                </span>
              )}
              {job.salary_range && (
                <span className="inline-flex items-center gap-1.5 font-semibold text-slate-800">
                  <Wallet size={13} className="text-[#D10043] shrink-0" />
                  <span>{job.salary_range}</span>
                </span>
              )}
              {postedDate && (
                <span className="inline-flex items-center gap-1.5 text-slate-400">
                  <Calendar size={12} className="shrink-0" />
                  <span>Posted {postedDate}</span>
                </span>
              )}
            </div>
          </div>

          {/* Right Side: Applicant Count + Action Buttons */}
          <div className="flex flex-wrap items-center justify-between lg:justify-end gap-2 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-100">
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-50 border border-slate-200/80 text-xs font-semibold text-slate-700 tabular-nums mr-1">
              <Users size={13} className="text-indigo-500 shrink-0" />
              <span>{applicantCount}</span>
              <span className="text-slate-400 font-medium">
                {applicantCount === 1 ? 'applicant' : 'applicants'}
              </span>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => onView(job)}
                className="inline-flex items-center justify-center gap-1.5 h-8 px-3 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold transition-colors cursor-pointer"
                title="Preview full job details"
              >
                <Eye size={13} className="shrink-0" />
                <span>Preview</span>
              </button>

              <button
                type="button"
                onClick={() => onEdit(job)}
                className="inline-flex items-center justify-center gap-1.5 h-8 px-3 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-semibold hover:border-slate-300 hover:bg-slate-50 transition-colors cursor-pointer"
                title="Edit job details & scoring weights"
              >
                <Edit3 size={13} className="shrink-0" />
                <span>Edit</span>
              </button>

              {job.is_active ? (
                <button
                  type="button"
                  onClick={() => onArchive(job.job_id || job.id, jobTitle)}
                  className="inline-flex items-center justify-center gap-1.5 h-8 px-2.5 bg-white border border-slate-200 text-amber-700 rounded-lg text-xs font-semibold hover:bg-amber-50 hover:border-amber-200 transition-colors cursor-pointer"
                  title="Archive job posting"
                >
                  <Archive size={13} className="shrink-0" />
                  <span className="hidden sm:inline">Archive</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => onUnarchive(job.job_id || job.id, jobTitle)}
                  className="inline-flex items-center justify-center gap-1.5 h-8 px-2.5 bg-white border border-slate-200 text-emerald-700 rounded-lg text-xs font-semibold hover:bg-emerald-50 hover:border-emerald-200 transition-colors cursor-pointer"
                  title="Restore job posting"
                >
                  <ArchiveRestore size={13} className="shrink-0" />
                  <span className="hidden sm:inline">Restore</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => onDelete(job.job_id || job.id, jobTitle)}
                aria-label={`Remove ${jobTitle}`}
                className="inline-flex items-center justify-center h-8 w-8 bg-white border border-slate-200 text-slate-400 rounded-lg hover:bg-rose-50 hover:border-rose-200 hover:text-rose-600 transition-colors cursor-pointer"
                title="Delete job permanently"
              >
                <Trash2 size={13} className="shrink-0" />
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Strip: Skills + AI Scoring Weights */}
        <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
          {skillsArray.length > 0 ? (
            <div className="flex flex-wrap items-center gap-1.5 min-w-0">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mr-1">
                Skills
              </span>
              {skillsArray.slice(0, 5).map((skill: string, idx: number) => (
                <span
                  key={idx}
                  className="bg-slate-100/80 text-slate-700 text-xs font-medium px-2 py-0.5 rounded-md"
                >
                  {skill}
                </span>
              ))}
              {skillsArray.length > 5 && (
                <span className="text-slate-500 text-xs font-medium px-1.5 py-0.5">
                  +{skillsArray.length - 5} more
                </span>
              )}
            </div>
          ) : (
            <span className="text-xs text-slate-400 italic">No required skills specified</span>
          )}

          {/* Scoring Weights Summary */}
          <div
            className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs shrink-0 self-start sm:self-auto ${
              isCustomWeights
                ? 'bg-[#D10043]/5 border-[#D10043]/20 text-[#D10043]'
                : 'bg-slate-50 border-slate-200/80 text-slate-600'
            }`}
            title={WEIGHT_FIELDS.map(
              (f) => `${f.shortLabel}: ${Math.round((activeWeights[f.key] ?? 0) * 100)}%`
            ).join(' | ')}
          >
            <Sliders size={12} className="shrink-0" />
            <span className="font-semibold">{formatPrioritySummary(job.scoring_weights)}</span>
            <div
              className="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden flex shrink-0"
              aria-hidden="true"
            >
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
  );
};

export default JobCard;
