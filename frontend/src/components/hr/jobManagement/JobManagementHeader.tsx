import React from 'react';
import { Plus } from 'lucide-react';

interface JobManagementHeaderProps {
  onCreateJob: () => void;
}

const JobManagementHeader: React.FC<JobManagementHeaderProps> = ({ onCreateJob }) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 sm:mb-8">
      <div>
        <div className="flex items-center gap-2 mb-1.5">
          <span className="inline-block w-2 h-2 rounded-full bg-[#D60041]" />
          <span className="text-xs font-bold uppercase tracking-widest text-[#D60041]">Careers & Positions</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-gray-900 tracking-tight">Job Management</h1>
        <p className="text-xs sm:text-sm text-gray-500 font-medium mt-1">Configure and monitor your organization's career opportunities</p>
      </div>
      <div className="flex items-center gap-2 w-full sm:w-auto">
        <button
          onClick={onCreateJob}
          className="w-full sm:w-auto justify-center flex items-center gap-2 px-5 sm:px-6 py-3 sm:py-3.5 bg-gray-900 text-white rounded-xl sm:rounded-2xl text-xs sm:text-sm font-bold hover:bg-black transition-all duration-300 shadow-sm hover:scale-[1.02] active:scale-[0.98] cursor-pointer"
        >
          <Plus className="w-4 h-4 text-[#D60041]" />
          Create Job
        </button>
      </div>
    </div>
  );
};

export default JobManagementHeader;
