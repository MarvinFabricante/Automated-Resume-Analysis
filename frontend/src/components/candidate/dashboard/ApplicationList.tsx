import React, { useState, useMemo } from 'react';
import {
  Briefcase,
  ArrowUpRight,
  ChevronRight,
  Calendar,
  Building2,
  Layers,
  Clock,
  CheckCircle2,
  AlertCircle,
  MessageSquare
} from 'lucide-react';
import { useNavigate } from '@/utils/navigation';
import HelpTooltip from '@/components/common/HelpTooltip';
import { ApplicationThreadItem } from '@/services/chatService';

const STAGE_LABELS = [
  'Submitted',
  'Under Review',
  'Shortlisted',
  'Initial Interview'
];

interface ApplicationListProps {
  applications?: any[];
  threadsByAppId?: Record<string, ApplicationThreadItem>;
}

const ApplicationList: React.FC<ApplicationListProps> = ({ applications = [], threadsByAppId = {} }) => {
  const navigate = useNavigate();
  const [filterTab, setFilterTab] = useState<'ACTIVE' | 'COMPLETED' | 'WITHDRAWN' | 'ALL'>('ACTIVE');

  const getGroup = (app: any): 'active' | 'completed' | 'withdrawn' => {
    if (app.group === 'active' || app.group === 'completed' || app.group === 'withdrawn') {
      return app.group;
    }
    const s = (app.rawStatus || app.status || '').toUpperCase();
    if (s.includes('WITHDRAWN')) return 'withdrawn';
    if (
      s.includes('PASSED') ||
      s.includes('ENDORSED') ||
      s === 'NOT SELECTED' ||
      s === 'NOT_SELECTED' ||
      s === 'REJECTED' ||
      s === 'ARCHIVED' ||
      app.step === 0
    ) {
      return 'completed';
    }
    return 'active';
  };

  // Tab counts: Active, Completed, Withdrawn
  const counts = useMemo(() => {
    let active = 0;
    let completed = 0;
    let withdrawn = 0;

    applications.forEach((app) => {
      const grp = getGroup(app);
      if (grp === 'withdrawn') withdrawn++;
      else if (grp === 'completed') completed++;
      else active++;
    });

    return {
      all: applications.length,
      active,
      completed,
      withdrawn,
    };
  }, [applications]);

  // Filter application tabs
  const filteredApps = useMemo(() => {
    return applications.filter((app) => {
      if (filterTab === 'ALL') return true;
      return getGroup(app).toUpperCase() === filterTab;
    });
  }, [applications, filterTab]);

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-5 sm:p-7 md:p-8 shadow-xs space-y-5 sm:space-y-6">
      
      {/* SECTION HEADER */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 sm:w-11 sm:h-11 bg-slate-900 rounded-xl flex items-center justify-center text-white shrink-0 shadow-xs">
            <Briefcase size={20} className="text-[#D10043]" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">My Applications</h3>
              <HelpTooltip text="Active applications count toward the 3-active-application limit. Passed, Not selected, and Withdrawn applications free your slot immediately." />
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-mono text-xs font-black">
                {counts.active} / 3 active slots
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium mt-0.5">Real-time status updates from Mariwasa Talent Acquisition</p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => navigate('/candidate/applicationtracking')}
          className="text-xs font-black uppercase tracking-wider text-[#D10043] hover:text-slate-900 transition-colors flex items-center gap-1 self-end sm:self-auto cursor-pointer"
        >
          <span>Track All Pipeline</span>
          <ArrowUpRight size={14} />
        </button>
      </div>

      {/* FILTER TABS: Active, Completed, Withdrawn, All */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
        {([
          { key: 'ACTIVE', label: 'Active', count: counts.active },
          { key: 'COMPLETED', label: 'Completed', count: counts.completed },
          { key: 'WITHDRAWN', label: 'Withdrawn', count: counts.withdrawn },
          { key: 'ALL', label: 'All', count: counts.all },
        ] as const).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setFilterTab(tab.key)}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-1.5 cursor-pointer ${
              filterTab === tab.key
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200/60'
            }`}
          >
            <span>{tab.label}</span>
            <span
              className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono font-black ${
                filterTab === tab.key
                  ? 'bg-slate-800 text-slate-200'
                  : 'bg-slate-200/70 text-slate-600'
              }`}
            >
              {tab.count}
            </span>
          </button>
        ))}
      </div>

      {/* APPLICATIONS LIST */}
      <div className="space-y-4">
        {filteredApps.length === 0 ? (
          <div className="py-10 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-200 p-6 space-y-2.5">
            <Layers size={26} className="mx-auto text-slate-300" />
            <p className="text-sm font-bold text-slate-700">
              {filterTab === 'ACTIVE'
                ? 'You have no active applications right now'
                : filterTab === 'COMPLETED'
                ? 'No completed applications yet'
                : filterTab === 'WITHDRAWN'
                ? 'No withdrawn applications'
                : 'You have not applied to any positions yet'}
            </p>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              {filterTab === 'ACTIVE'
                ? 'Your account stays active and ready—explore open roles at Mariwasa whenever you are ready to apply.'
                : filterTab === 'COMPLETED'
                ? 'Passed and Not Selected outcomes along with your feedback reports will appear here.'
                : filterTab === 'WITHDRAWN'
                ? 'Any application you withdraw appears here for your records.'
                : 'Browse open roles and submit your resume to start tracking your progress.'}
            </p>
            {filterTab === 'ACTIVE' && (
              <button
                type="button"
                onClick={() => navigate('/candidate/findjobs')}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white text-xs font-bold transition-colors cursor-pointer"
              >
                <span>Browse Open Positions</span>
                <ArrowUpRight size={13} />
              </button>
            )}
          </div>
        ) : (
          filteredApps.map((app) => {
            const currentStep = app.step || 1;
            const totalSteps = app.totalSteps || 4;
            const isNotSelected = app.status === 'Not Selected' || app.status === 'Rejected' || app.step === 0;

            return (
              <div
                key={app.id}
                onClick={() => navigate(`/candidate/applicationtracking/${app.id}`, { state: { application: app } })}
                className="group relative border border-slate-200/80 bg-white hover:bg-slate-50/30 rounded-2xl p-4 sm:p-6 hover:border-[#D10043]/30 hover:shadow-md transition-all duration-200 cursor-pointer space-y-4"
              >
                {/* Header Information: Mobile-friendly stack */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2.5">
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-black text-[#D10043] uppercase tracking-wider font-mono bg-[#D10043]/5 px-2 py-0.5 rounded-md border border-[#D10043]/10">
                        #ARA-88{app.id}
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
                        <Calendar size={12} className="text-slate-400" />
                        Applied {app.appliedDate}
                      </span>
                    </div>

                    <h4 className="text-base sm:text-lg font-black text-slate-900 tracking-tight group-hover:text-[#D10043] transition-colors leading-snug">
                      {app.role}
                    </h4>
                    
                    <p className="text-xs text-slate-500 font-semibold flex items-center gap-1.5">
                      <Building2 size={13} className="text-slate-400 shrink-0" />
                      <span>{app.company}</span>
                    </p>
                  </div>

                  {/* Status & Message from HR Badges */}
                  <div className="flex items-center gap-2 flex-wrap self-start sm:self-auto shrink-0">
                    {threadsByAppId[String(app.id)] && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/candidate/messages?thread=${threadsByAppId[String(app.id)].id}`);
                        }}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black bg-rose-50 text-[#D10043] border border-rose-200 hover:bg-[#D10043] hover:text-white transition-colors cursor-pointer"
                      >
                        <MessageSquare size={11} />
                        <span>Message from HR</span>
                        {(threadsByAppId[String(app.id)].unread_count || 0) > 0 && (
                          <span className="px-1.5 py-0.2 rounded-full bg-[#D10043] text-white text-[9px] font-black">
                            {threadsByAppId[String(app.id)].unread_count}
                          </span>
                        )}
                      </button>
                    )}
                    <div className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-wider border flex items-center gap-1.5 ${app.statusColor || 'text-slate-600 bg-slate-50 border-slate-200'}`}>
                      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
                      <span>{app.status}</span>
                    </div>
                  </div>
                </div>

                {/* 4-Stage Stepper Progress Tracker */}
                <div className="pt-2 border-t border-slate-100/80 space-y-2">
                  <div className="flex items-center justify-between text-xs font-bold gap-2 flex-wrap">
                    <span className="text-slate-500 font-medium">Recruitment Progress</span>
                    <span className="text-slate-900 font-black flex items-center gap-1">
                      {isNotSelected ? (
                        <span className="text-rose-600 font-bold">Status: Not Selected</span>
                      ) : (
                        <>
                          <span>Stage {currentStep} of {totalSteps}:</span>
                          <span className="text-[#D10043] font-bold">
                            {STAGE_LABELS[currentStep - 1] || 'In Review'}
                          </span>
                        </>
                      )}
                    </span>
                  </div>

                  {/* Visual Stepper Nodes */}
                  <div className="grid grid-cols-4 gap-1.5">
                    {STAGE_LABELS.map((stageName, idx) => {
                      const stepNumber = idx + 1;
                      const isCompleted = !isNotSelected && stepNumber < currentStep;
                      const isCurrent = !isNotSelected && stepNumber === currentStep;

                      return (
                        <div key={idx} className="flex flex-col gap-1">
                          <div
                            className={`h-2 rounded-full transition-all duration-300 ${
                              isNotSelected
                                ? 'bg-slate-200'
                                : isCompleted
                                ? 'bg-emerald-500'
                                : isCurrent
                                ? 'bg-[#D10043]'
                                : 'bg-slate-100'
                            }`}
                          />
                          <span
                            className={`hidden sm:block text-[9px] font-bold uppercase tracking-wider truncate text-center ${
                              isNotSelected
                                ? 'text-slate-300'
                                : isCurrent
                                ? 'text-[#D10043]'
                                : isCompleted
                                ? 'text-slate-700'
                                : 'text-slate-300'
                            }`}
                          >
                            {stageName}
                          </span>
                        </div>
                      );
                    })}
                  </div>

                  {/* Post-Interview Note or Not Selected Note */}
                  {currentStep === 4 && !isNotSelected && (
                    <div className="p-2.5 rounded-xl bg-purple-50 border border-purple-100 text-xs text-purple-900 font-medium flex items-center gap-2">
                      <CheckCircle2 size={14} className="text-purple-600 shrink-0" />
                      <span>Thank you! HR will contact you directly about the next steps.</span>
                    </div>
                  )}

                  {isNotSelected && (
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 font-medium flex items-center gap-2">
                      <AlertCircle size={14} className="text-slate-400 shrink-0" />
                      <span>Thank you for your interest. We are proceeding with other applicants for this role.</span>
                    </div>
                  )}

                  {/* Mobile-Friendly Active Stage Pill (Visible on small screens) */}
                  {!isNotSelected && (
                    <div className="sm:hidden flex items-center gap-2 pt-1">
                      <span className="text-[10px] font-bold text-slate-500 bg-slate-50 border border-slate-200/60 px-2 py-0.5 rounded-md flex items-center gap-1">
                        <Clock size={11} className="text-[#D10043]" />
                        <span>Current: <strong>{STAGE_LABELS[currentStep - 1] || 'In Review'}</strong></span>
                      </span>
                    </div>
                  )}
                </div>

                {/* Bottom Action Row */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium text-[11px] hidden sm:inline">
                    Click to view application details & updates
                  </span>
                  <div className="flex items-center gap-1 text-[#D10043] font-black uppercase tracking-wider text-[11px] ml-auto group-hover:translate-x-0.5 transition-transform">
                    <span>View Tracking Details</span>
                    <ChevronRight size={14} />
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
