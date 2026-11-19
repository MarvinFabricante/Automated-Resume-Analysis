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
}

const JobList: React.FC<JobListProps> = ({
  jobs,
  viewMode = 'cards',
  onEdit,
  onView,
  onArchive,
  onUnarchive,
  onDelete,
}) => {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-14 sm:py-20 px-4 bg-white rounded-3xl border border-gray-200/80 shadow-xs">
        <div className="w-14 h-14 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-3.5 border border-gray-100">
          <Search className="w-6 h-6 text-gray-300" />
        </div>
        <h4 className="text-base font-extrabold text-gray-900">No matching positions found</h4>
        <p className="text-xs sm:text-sm text-gray-500 mt-1 max-w-sm mx-auto">
          Try clearing or adjusting your search query, status, or department filters.
        </p>
      </div>
    );
  }

  if (viewMode === 'table') {
    return (
      <div className="bg-white rounded-2xl sm:rounded-3xl border border-gray-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/90 border-b border-gray-200/80 text-[11px] font-bold uppercase tracking-wider text-gray-500">
                <th className="py-3.5 px-5">Position & Code</th>
                <th className="py-3.5 px-4">Department & Location</th>
                <th className="py-3.5 px-4">Compensation</th>
                <th className="py-3.5 px-4">Applicants</th>
                <th className="py-3.5 px-4">Scoring Weights</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs sm:text-sm">
              {jobs.map((job) => {
                const jobTitle = job.job_title || job.title || 'Untitled Position';
                const jobId = job.job_id || String(job.id);
                const applicantCount = Number(job.applicant_count ?? 0);
                const activeWeights = job.scoring_weights || DEFAULT_JOB_SCORING_WEIGHTS;
                const isCustomWeights = Boolean(
                  job.scoring_weights &&
                    !areWeightsEqual(job.scoring_weights, DEFAULT_JOB_SCORING_WEIGHTS)
                );

                return (
                  <tr
                    key={job.id || job.job_id}
                    className="hover:bg-pink-50/20 transition-colors group"
                  >
                    <td className="py-3.5 px-5 min-w-[210px]">
                      <button
                        type="button"
                        onClick={() => onView(job)}
                        className="font-bold text-gray-900 group-hover:text-[#D10043] transition-colors text-left cursor-pointer block"
                      >
                        {jobTitle}
                      </button>
                      <span className="text-[11px] font-mono font-semibold text-gray-400">
                        {jobId} {job.job_type ? `• ${job.job_type}` : ''}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-xs text-gray-600 min-w-[160px]">
                      <div className="font-semibold text-gray-800">{job.department || '—'}</div>
                      <div className="text-[11px] text-gray-400 truncate max-w-[180px]">
                        {job.location || '—'}
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-xs font-bold text-[#D10043] whitespace-nowrap">
                      {job.salary_range || '—'}
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold bg-indigo-50/80 text-indigo-700 border border-indigo-100">
                        <Users size={12} />
                        {applicantCount}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 min-w-[170px]">
                      <div className="flex flex-col gap-1">
                        <span
                          className={`inline-flex items-center gap-1 text-[11px] font-bold ${
                            isCustomWeights ? 'text-[#D10043]' : 'text-gray-600'
                          }`}
                        >
                          <Sliders size={11} />
                          {formatPrioritySummary(job.scoring_weights)}
                        </span>
                        <div className="w-24 h-1.5 rounded-full bg-gray-100 overflow-hidden flex">
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
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase border ${
                          job.is_active
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
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
                      <div className="inline-flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => onView(job)}
                          title="Preview"
                          aria-label={`Preview ${jobTitle}`}
                          className="p-2 rounded-xl bg-gray-50 hover:bg-gray-900 text-gray-600 hover:text-white transition-colors cursor-pointer"
                        >
                          <Eye size={14} />
                        </button>
                        <button
                          type="button"
                          onClick={() => onEdit(job)}
                          title="Edit"
                          aria-label={`Edit ${jobTitle}`}
                          className="p-2 rounded-xl bg-gray-50 hover:bg-pink-50 text-gray-600 hover:text-[#D10043] transition-colors cursor-pointer"
                        >
                          <Edit3 size={14} />
                        </button>
                        {job.is_active ? (
                          <button
                            type="button"
                            onClick={() => onArchive(job.job_id || job.id, jobTitle)}
                            title="Archive"
                            aria-label={`Archive ${jobTitle}`}
                            className="p-2 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-700 transition-colors cursor-pointer"
                          >
                            <Archive size={14} />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => onUnarchive(job.job_id || job.id, jobTitle)}
                            title="Restore"
                            aria-label={`Restore ${jobTitle}`}
                            className="p-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-700 transition-colors cursor-pointer"
                          >
                            <ArchiveRestore size={14} />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => onDelete(job.job_id || job.id, jobTitle)}
                          title="Remove"
                          aria-label={`Remove ${jobTitle}`}
                          className="p-2 rounded-xl bg-gray-50 hover:bg-rose-50 text-gray-500 hover:text-rose-700 transition-colors cursor-pointer"
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
    <div className="space-y-4">
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
