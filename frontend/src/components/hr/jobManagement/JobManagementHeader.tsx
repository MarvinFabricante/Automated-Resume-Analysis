import React from 'react';
import { Briefcase, Download, Plus } from 'lucide-react';

interface JobManagementHeaderProps {
  onCreateJob: () => void;
  onExportCsv?: () => void;
  canExport?: boolean;
}

const JobManagementHeader: React.FC<JobManagementHeaderProps> = ({
  onCreateJob,
  onExportCsv,
  canExport = false,
}) => {
  return (
    <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-5">
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-gray-200/80 shadow-xs text-[11px] font-black text-gray-500 mb-2.5 tracking-wider uppercase">
          <Briefcase size={13} className="text-[#D10043]" />
          Careers & Requisitions
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-gray-900">
          Job Management
        </h1>
        <p className="text-sm text-gray-500 font-medium mt-1.5 max-w-2xl leading-relaxed">
          Publish open positions, track applicant volume, and fine-tune per-job AI scoring priorities across departments.
        </p>
      </div>

      <div className="flex items-center gap-3 w-full md:w-auto shrink-0">
        {onExportCsv && (
          <button
            type="button"
            onClick={onExportCsv}
            disabled={!canExport}
            className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-2xl bg-white hover:bg-gray-50 text-gray-700 border border-gray-200/90 shadow-xs hover:border-gray-300 text-sm font-semibold transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            title="Export filtered positions to CSV"
          >
            <Download size={16} className="text-gray-500" />
            <span>Export CSV</span>
          </button>
        )}

        <button
          type="button"
          onClick={onCreateJob}
          className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 bg-gradient-to-r from-[#D10043] to-[#B00038] hover:from-[#c2003e] hover:to-[#9e0032] text-white px-5 py-2.5 rounded-2xl text-sm font-bold shadow-md shadow-red-500/20 hover:scale-[1.01] active:scale-[0.99] transition-all cursor-pointer"
        >
          <Plus size={17} />
          <span>Create Position</span>
        </button>
      </div>
    </div>
  );
};

export default JobManagementHeader;
