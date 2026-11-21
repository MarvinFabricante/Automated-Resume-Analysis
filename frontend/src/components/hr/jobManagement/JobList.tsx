import React from 'react';
import {
  Search,
  Eye,
  Edit3,
  Archive,
  ArchiveRestore,
  Trash2,
  Users,
  Sliders,
  RotateCcw,
} from 'lucide-react';
import JobCard from './JobCard';
import { Job, DEFAULT_JOB_SCORING_WEIGHTS } from '../../../types';
import { JobViewMode } from './JobSearchAndFilter';
import {
  WEIGHT_FIELDS,
  areWeightsEqual,
  formatPrioritySummary,
} from '../../modals/hr/JobScoringWeightsEditor';

interface JobListProps {
  jobs: Job[];
  viewMode?: JobViewMode;
  onEdit: (job: Job) => void;
  onView: (job: Job) => void;
  onArchive: (jobId: string | number | undefined, title: string) => void;
  onUnarchive: (jobId: string | number | undefined, title: string) => void;
  onDelete: (jobId: string | number | undefined, title: string) => void;
  onResetFilters?: () => void;
}

const JobList: React.FC<JobListProps> = ({
  jobs,
  viewMode = 'cards',
  onEdit,
  onView,
  onArchive,
  onUnarchive,
  onDelete,
  onResetFilters,
}) => {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-14 sm:py-20 px-4 bg-white rounded-2xl border border-slate-200/90 shadow-2xs">
        <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center mx-auto mb-3.5 border border-slate-200/70">
          <Search className="w-5 h-5 text-slate-400" />
        </div>
        <h4 className="text-base font-bold text-slate-900">No matching positions found</h4>
        <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
          Try adjusting your search query, status tab, or department filters.
        </p>
        {onResetFilters && (
          <button
            type="button"
            onClick={onResetFilters}
            className="mt-4 inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition-colors cursor-pointer"
          >
            <RotateCcw size={13} />
            <span>Reset all filters</span>
          </button>
        )}
      </div>
    );
  }

  if (viewMode === 'table') {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50/90 border-b border-slate-200/80 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                <th className="py-3 px-5">Position & Code</th>
                <th className="py-3 px-4">Department & Location</th>
                <th className="py-3 px-4">Compensation</th>
                <th className="py-3 px-4">Applicants</th>
                <th className="py-3 px-4">Scoring Weights</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs sm:text-sm">
              {jobs.map((job) => {
                const jobTitle = job.job_title || job.title || 'Untitled Position';
                const jobId = job.job_id || String(job.id);
                const jobType = job.job_type || job.employment_type;
                const applicantCount = Number(job.applicant_count ?? 0);
                const activeWeights = job.scoring_weights || DEFAULT_JOB_SCORING_WEIGHTS;
                const isCustomWeights = Boolean(
                  job.scoring_weights &&
                    !areWeightsEqual(job.scoring_weights, DEFAULT_JOB_SCORING_WEIGHTS)
                );

                return (
                  <tr
                    key={job.id || job.job_id}
                    className="hover:bg-slate-50/80 transition-colors group"
                  >
                    <td className="py-3.5 px-5 min-w-[220px]">
                      <button
                        type="button"
                        onClick={() => onView(job)}
                        className="font-semibold text-slate-900 group-hover:text-[#D10043] transition-colors text-left cursor-pointer block"
                      >
                        {jobTitle}
                      </button>
                      <span className="text-[11px] font-mono text-slate-400">
                        {jobId}
                        {jobType ? ` • ${jobType}` : ''}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-xs text-slate-600 min-w-[160px]">
                      <div className="font-medium text-slate-800">{job.department || '—'}</div>
                      <div className="text-[11px] text-slate-400 truncate max-w-[190px]">
                        {job.location || '—'}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-xs font-semibold text-slate-800 whitespace-nowrap">
                      {job.salary_range || '—'}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100/80 text-slate-700 border border-slate-200/70 tabular-nums">
                        <Users size={12} className="text-indigo-500" />
                        {applicantCount}
                      </span>
                    </td>

                    <td
                      className="py-3.5 px-4 min-w-[170px]"
                      title={WEIGHT_FIELDS.map(
                        (f) => `${f.shortLabel}: ${Math.round((activeWeights[f.key] ?? 0) * 100)}%`
                      ).join(' | ')}
                    >
                      <div className="flex flex-col gap-1.5">
                        <span
                          className={`inline-flex items-center gap-1.5 text-[11px] font-semibold ${
                            isCustomWeights ? 'text-[#D10043]' : 'text-slate-600'
                          }`}
                        >
                          <Sliders size={11} />
                          {formatPrioritySummary(job.scoring_weights)}
                        </span>
                        <div className="w-24 h-1.5 rounded-full bg-slate-100 overflow-hidden flex">
                          {WEIGHT_FIELDS.map((field) => (
                            <div
                              key={field.key}
                              style={{
                                width: `${Math.round((activeWeights[field.key] ?? 0) * 100)}%`,
                              }}
                              className={`${field.color} h-full`}
                            />
                          ))}
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
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
                    </td>

                    <td className="py-3.5 px-5 text-right whitespace-nowrap">
                      <div className="inline-flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => onView(job)}
                          title="Preview"
                          aria-label={`Preview ${jobTitle}`}
                          className="p-2 rounded-lg text-slate-500 hover:bg-slate-900 hover:text-white transition-colors cursor-pointer"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => onEdit(job)}
                          title="Edit"
                          aria-label={`Edit ${jobTitle}`}
                          className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-[#D10043] transition-colors cursor-pointer"
                        >
                          <Edit3 size={14} />
                        </button>
                        {job.is_active ? (
                          <button
                            type="button"
                            onClick={() => onArchive(job.job_id || job.id, jobTitle)}
                            title="Archive"
                            aria-label={`Archive ${jobTitle}`}
                            className="p-2 rounded-lg text-amber-600 hover:bg-amber-50 transition-colors cursor-pointer"
                          >
                            <Archive size={14} />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onUnarchive(job.job_id || job.id, jobTitle)}
                            title="Restore"
                            aria-label={`Restore ${jobTitle}`}
                            className="p-2 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors cursor-pointer"
                          >
                            <ArchiveRestore size={14} />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onDelete(job.job_id || job.id, jobTitle)}
                          title="Remove"
                          aria-label={`Remove ${jobTitle}`}
                          className="p-2 rounded-lg text-slate-400 hover:bg-rose-50 hover:text-rose-600 transition-colors cursor-pointer"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => (
        <JobCard
          key={job.id || job.job_id}
          job={job}
          onEdit={onEdit}
          onView={onView}
          onArchive={onArchive}
          onUnarchive={onUnarchive}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};

export default JobList;
