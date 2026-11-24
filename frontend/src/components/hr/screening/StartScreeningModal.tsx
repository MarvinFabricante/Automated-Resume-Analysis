import React, { useState } from 'react';
import { X, Sliders, Briefcase, Percent, Filter, Play } from 'lucide-react';

interface StartScreeningModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobs: any[];
  onStartScreening: (config: {
    jobId: number | string;
    jobTitle: string;
    minThreshold: number;
    statusFilters: string[];
  }) => void;
  initialJobId?: string | number;
}

const StartScreeningModal: React.FC<StartScreeningModalProps> = ({
  isOpen,
  onClose,
  jobs = [],
  onStartScreening,
  initialJobId,
}) => {
  const activeJobs = jobs.filter((j) => j.is_active !== false);

  const [selectedJobId, setSelectedJobId] = useState<string>(
    initialJobId ? String(initialJobId) : activeJobs[0]?.id ? String(activeJobs[0].id) : ''
  );
  const [minThreshold, setMinThreshold] = useState<number>(80);
  const [statusFilters, setStatusFilters] = useState<string[]>(['Submitted', 'Under Review']);

  if (!isOpen) return null;

  const toggleStatus = (status: string) => {
    setStatusFilters((prev) =>
      prev.includes(status) ? prev.filter((s) => s !== status) : [...prev, status]
    );
  };

  const handleRun = () => {
    const job = activeJobs.find((j) => String(j.id || j.job_id) === String(selectedJobId));
    onStartScreening({
      jobId: selectedJobId,
      jobTitle: job?.job_title || job?.title || 'Selected Position',
      minThreshold,
      statusFilters,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-white rounded-3xl shadow-2xl max-w-lg w-full p-6 sm:p-7 border border-slate-200 animate-in zoom-in-95 duration-200 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-rose-50 text-[#D60041] flex items-center justify-center font-bold">
              <Sliders size={20} />
            </div>
            <div>
              <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
                Start Screening Workflow
              </h3>
              <p className="text-xs text-slate-500">
                Choose a role and minimum match threshold to evaluate candidates.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Step 1: Select Position */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Briefcase size={14} className="text-[#D60041]" />
            <span>Target Job Position</span>
          </label>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs sm:text-sm font-semibold text-slate-800 focus:bg-white focus:border-[#D60041] focus:ring-2 focus:ring-[#D60041]/10 outline-none"
          >
            {activeJobs.map((j) => (
              <option key={j.id || j.job_id} value={j.id || j.job_id}>
                {j.job_title || j.title} ({j.department || 'General'})
              </option>
            ))}
          </select>
        </div>

        {/* Step 2: Minimum Match Percentage Slider (Default 80%) */}
        <div className="space-y-3 bg-slate-50 p-4 rounded-2xl border border-slate-200/80">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
              <Percent size={14} className="text-emerald-600" />
              <span>Minimum Match Threshold</span>
            </label>
            <span className="text-sm font-black text-emerald-700 bg-emerald-100/70 px-2.5 py-0.5 rounded-full border border-emerald-200">
              {minThreshold}%
            </span>
          </div>

          <input
            type="range"
            min="40"
            max="95"
            step="5"
            value={minThreshold}
            onChange={(e) => setMinThreshold(Number(e.target.value))}
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-[#D60041]"
          />
          <div className="flex justify-between text-[11px] font-semibold text-slate-400">
            <span>40% (Broader)</span>
            <span>80% (Recommended)</span>
            <span>95% (Strict)</span>
          </div>
        </div>

        {/* Step 3: Status Filters */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Filter size={14} className="text-slate-500" />
            <span>Include Application Statuses</span>
          </label>
          <div className="flex flex-wrap gap-2">
            {['Submitted', 'Under Review', 'Shortlisted'].map((st) => {
              const active = statusFilters.includes(st);
              return (
                <button
                  type="button"
                  key={st}
                  onClick={() => toggleStatus(st)}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border cursor-pointer ${
                    active
                      ? 'bg-rose-50 text-[#D60041] border-rose-200 shadow-2xs'
                      : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  {st}
                </button>
              );
            })}
          </div>
          <p className="text-[11px] text-slate-400">
            Withdrawn, Passed, and Not Selected applications are automatically excluded from shortlisting.
          </p>
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleRun}
            disabled={!selectedJobId}
            className="px-5 py-2.5 bg-[#D60041] hover:bg-[#b50037] text-white text-xs sm:text-sm font-bold rounded-xl shadow-md shadow-rose-200 transition-all flex items-center gap-2 cursor-pointer disabled:opacity-50"
          >
            <Play size={14} fill="currentColor" />
            <span>Run Screening</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default StartScreeningModal;
