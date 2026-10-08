import React, { useState } from 'react';
import { Briefcase, ArrowUpRight, ChevronRight, Calendar, CheckCircle2, Clock, MapPin, Building2, Layers } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const STAGE_LABELS = [
  'Submission',
  'Screening',
  'Technical Review',
  'Final Interview',
  'Decision'
];

const ApplicationList = ({ applications = [] }) => {
  const navigate = useNavigate();
  const [filterTab, setFilterTab] = useState('ALL');

  // Filter application tabs
  const filteredApps = applications.filter((app) => {
    if (filterTab === 'ALL') return true;
    const statusUpper = (app.status || '').toUpperCase();
    if (filterTab === 'REVIEW') {
      return statusUpper === 'PENDING' || statusUpper === 'REVIEWED';
    }
    if (filterTab === 'INTERVIEWS') {
      return statusUpper.includes('INTERVIEW');
    }
    if (filterTab === 'DECISION') {
      return statusUpper === 'ACCEPTED' || statusUpper === 'REJECTED';
    }
    return true;
  });

  return (
    <div className="bg-white border border-slate-200/80 rounded-[32px] p-6 sm:p-8 md:p-10 shadow-sm space-y-6 sm:space-y-8">
      
      {/* SECTION HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-100">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 sm:w-12 sm:h-12 bg-slate-900 rounded-2xl flex items-center justify-center text-white shrink-0 shadow-sm">
            <Briefcase size={22} className="text-[#D10043]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">Active Applications</h3>
              <span className="px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-700 font-mono text-xs font-black">
                {applications.length}
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5">Real-time status updates from Mariwasa Talent Acquisition</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => navigate('/candidate/applicationtracking')}
          className="text-xs font-black uppercase tracking-wider text-[#D10043] hover:text-slate-900 transition-colors flex items-center gap-1.5 self-end sm:self-auto"
        >
          Track All Pipeline <ArrowUpRight size={15} />
        </button>
      </div>

      {/* FILTER TABS */}
      <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 scrollbar-none">
        {[
          { key: 'ALL', label: `All (${applications.length})` },
          { key: 'REVIEW', label: 'Screening' },
          { key: 'INTERVIEWS', label: 'Interviewing' },
          { key: 'DECISION', label: 'Decisions' }
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setFilterTab(tab.key)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all shrink-0 ${
              filterTab === tab.key
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200/60'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* APPLICATIONS LIST */}
      <div className="space-y-5">
        {filteredApps.length === 0 ? (
          <div className="py-12 text-center bg-slate-50/60 rounded-3xl border border-dashed border-slate-200 p-6">
            <Layers size={28} className="mx-auto text-slate-300 mb-2" />
            <p className="text-sm font-bold text-slate-700">No applications match this filter</p>
            <p className="text-xs text-slate-400 mt-1">Switch filter tabs to review your other submissions.</p>
          </div>
        ) : (
          filteredApps.map((app) => {
            const currentStep = app.step || 1;
            const totalSteps = app.totalSteps || 5;
            const progressPercent = Math.min(100, Math.round((currentStep / totalSteps) * 100));

            return (
              <div
                key={app.id}
                onClick={() => navigate(`/candidate/applicationtracking/${app.id}`, { state: { application: app } })}
                className="group relative border border-slate-200/70 bg-white hover:bg-slate-50/40 rounded-[28px] p-6 sm:p-7 hover:border-[#D10043]/30 hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 cursor-pointer space-y-5"
              >
                {/* Header Information */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] font-black text-[#D10043] uppercase tracking-[0.2em] font-mono bg-[#D10043]/5 px-2 py-0.5 rounded-md border border-[#D10043]/10">
                        #ARA-88{app.id}
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                        <Calendar size={12} />
                        Applied {app.appliedDate}
                      </span>
                    </div>

                    <h4 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight group-hover:text-[#D10043] transition-colors">
                      {app.role}
                    </h4>
                    
                    <p className="text-xs text-slate-500 font-semibold flex items-center gap-1.5 mt-0.5">
                      <Building2 size={13} className="text-slate-400" />
                      {app.company}
                    </p>
                  </div>

                  {/* Status Badge */}
                  <div className={`px-3.5 py-1.5 rounded-full text-[10px] font-black uppercase tracking-wider border flex items-center gap-1.5 self-start sm:self-auto ${app.statusColor || 'text-slate-600 bg-slate-50 border-slate-200'}`}>
                    <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                    {app.status}
                  </div>
                </div>

                {/* 5-Stage Stepper Progress Tracker */}
                <div className="pt-2">
                  <div className="flex items-center justify-between text-xs font-bold mb-2">
                    <span className="text-slate-500 font-medium">Recruitment Stage</span>
                    <span className="text-slate-900 font-black">
                      Stage {currentStep} of {totalSteps}:{' '}
                      <span className="text-[#D10043]">{STAGE_LABELS[currentStep - 1] || 'In Review'}</span>
                    </span>
                  </div>

                  {/* Visual Stepper Nodes */}
                  <div className="grid grid-cols-5 gap-1.5 sm:gap-2">
                    {STAGE_LABELS.map((stageName, idx) => {
                      const stepNumber = idx + 1;
                      const isCompleted = stepNumber < currentStep;
                      const isCurrent = stepNumber === currentStep;

                      return (
                        <div key={idx} className="flex flex-col gap-1.5">
                          <div
                            className={`h-2 rounded-full transition-all duration-500 ${
                              isCompleted
                                ? 'bg-emerald-500'
                                : isCurrent
                                ? 'bg-[#D10043] animate-pulse'
                                : 'bg-slate-100'
                            }`}
                          />
                          <span className={`hidden sm:block text-[9px] font-bold uppercase tracking-wider truncate text-center ${
                            isCurrent
                              ? 'text-[#D10043]'
                              : isCompleted
                              ? 'text-slate-700'
                              : 'text-slate-300'
                          }`}>
                            {stageName}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Bottom CTA Row */}
                <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium hidden sm:inline">
                    Click to view detailed interview feedback & evaluation notes
                  </span>
                  <div className="flex items-center gap-1 text-[#D10043] font-black uppercase tracking-wider text-[11px] ml-auto group-hover:translate-x-1 transition-transform">
                    View Tracking Timeline
                    <ChevronRight size={15} />
                  </div>
                </div>

              </div>
            );
          })
        )}
      </div>

    </div>
  );
};

export default ApplicationList;
