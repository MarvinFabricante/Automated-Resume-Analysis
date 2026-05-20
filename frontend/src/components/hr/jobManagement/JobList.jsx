import React from 'react';
import { Search } from 'lucide-react';
import JobCard from './JobCard';

const JobList = ({ jobs, onEdit, onView, onArchive, onUnarchive, onDelete }) => {
  if (jobs.length === 0) {
    return (
      <div className="text-center py-24 bg-white rounded-[32px] border-2 border-dashed border-gray-200 text-gray-400 shadow-sm">
        <Search className="h-10 w-10 mx-auto text-gray-300 mb-4" />
        <p className="text-lg font-bold text-gray-500">No jobs found</p>
        <p className="text-sm mt-1">Try adjusting your filters or search query</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {jobs.map(job => (
        <JobCard
          key={job.id}
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
