import React from 'react';
import { Plus } from 'lucide-react';

const JobManagementHeader = ({ onCreateJob }) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
      <div>
        <h1 className="text-3xl font-black text-gray-900 tracking-tight">Job Management</h1>
        <p className="text-gray-500 font-medium mt-1">Configure and monitor your organization's career opportunities</p>
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={onCreateJob}
          className="flex items-center gap-2 px-6 py-3.5 bg-gray-900 text-white rounded-2xl text-sm font-bold hover:bg-black transition-all duration-300 shadow-sm hover:scale-[1.02] active:scale-[0.98]"
        >
          <Plus className="w-4 h-4 text-[#D60041]" />
          Create Job
        </button>
      </div>
    </div>
  );
};

export default JobManagementHeader;
