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
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pb-2 border-b border-slate-200/70">
      <div className="space-y-1">
        <div className="inline-flex items-center gap-2 text-xs font-semibold text-slate-500">
          <span className="inline-flex items-center gap-1.5 text-[#D10043] font-bold">
            <Briefcase size={14} />
            Talent Acquisition
          </span>
          <span className="text-slate-300">/</span>
          <span>Job Requisitions</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
          Job Management
        </h1>
        <p className="text-sm text-slate-500 max-w-2xl">
          Publish open positions, monitor applicant volume, and configure per-role AI scoring weights.
        </p>
      </div>

      <div className="flex items-center gap-2.5 w-full md:w-auto shrink-0">
        {onExportCsv && (
          <button
            type="button"
            onClick={onExportCsv}
            disabled={!canExport}
            className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 h-10 px-4 rounded-xl bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 hover:border-slate-300 shadow-2xs text-sm font-semibold transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            title="Export filtered positions to CSV"
          >
            <Download size={15} className="text-slate-500" />
            <span>Export CSV</span>
          </button>
        )}

        <button
          type="button"
          onClick={onCreateJob}
          className="flex-1 md:flex-none inline-flex items-center justify-center gap-2 h-10 px-4.5 rounded-xl bg-[#D10043] hover:bg-[#B00038] text-white text-sm font-semibold shadow-sm shadow-[#D10043]/20 transition-colors cursor-pointer"
        >
          <Plus size={16} />
          <span>Create Position</span>
        </button>
      </div>
    </div>
  );
};

export default JobManagementHeader;
