import React from 'react';
import { Search } from 'lucide-react';
import JobCard from './JobCard';
import { Job } from '../../../types';

interface JobListProps {
  jobs: Job[];
  onEdit: (job: Job) => void;
  onView: (job: Job) => void;
  onArchive: (jobId: string | number | undefined, title: string) => void;
  onUnarchive: (jobId: string | number | undefined, title: string) => void;
  onDelete: (jobId: string | number | undefined, title: string) => void;
}

const JobList: React.FC<JobListProps> = ({ jobs, onEdit, onView, onArchive, onUnarchive, onDelete }) => {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-16 px-4 bg-white rounded-[32px] border border-gray-100 shadow-sm">
        <div className="w-14 h-14 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-3 border border-gray-100">
          <Search className="w-6 h-6 text-gray-300" />
        </div>
        <h4 className="text-sm font-bold text-gray-900">No jobs found</h4>
        <p className="text-xs text-gray-400 mt-1">Try adjusting your filters or search query.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {jobs.map(job => (
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
