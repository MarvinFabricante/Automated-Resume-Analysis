import React from 'react';
import {
  CheckCircle2,
  Clock,
  Award,
  XCircle,
  Ban,
  Calendar,
  MinusCircle,
  PauseCircle,
  Info,
} from 'lucide-react';
import {
  ComputedApplicationTracker,
  ComputedTrackerStage,
} from '../../utils/applicationTracker';

interface ApplicationStageTrackerProps {
  tracker: ComputedApplicationTracker;
  audience?: 'candidate' | 'hr';
  compact?: boolean;
  className?: string;
}

const StageCircle: React.FC<{ stage: ComputedTrackerStage; isOnHold?: boolean }> = ({
  stage,
  isOnHold,
}) => {
  if (stage.state === 'done') {
    if (stage.outcome === 'not_selected') {
      return (
        <div className="w-8 h-8 rounded-xl bg-rose-50 border border-rose-200 text-rose-600 flex items-center justify-center shrink-0">
          <XCircle size={16} />
        </div>
      );
    }
    if (stage.outcome === 'passed') {
      return (
        <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-sm shadow-emerald-600/20">
          <Award size={16} />
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-xl bg-emerald-500 text-white flex items-center justify-center shrink-0 shadow-xs">
        <CheckCircle2 size={16} />
      </div>
    );
  }

  if (stage.state === 'active') {
    if (isOnHold) {
      return (
        <div className="w-8 h-8 rounded-xl bg-amber-50 border-2 border-amber-400 text-amber-700 flex items-center justify-center shrink-0">
          <PauseCircle size={16} />
        </div>
      );
    }
    if (stage.outcome === 'awaiting') {
      return (
        <div className="w-8 h-8 rounded-xl bg-amber-50 border-2 border-amber-500 text-amber-700 flex items-center justify-center shrink-0 shadow-xs">
          <Clock size={16} />
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-xl bg-[#D60041] text-white flex items-center justify-center shrink-0 shadow-sm shadow-[#D60041]/25 ring-4 ring-rose-100">
        {stage.key === 'interview_scheduled' ? <Calendar size={15} /> : <Clock size={15} />}
      </div>
    );
  }

  if (stage.state === 'not_applicable') {
    return (
      <div className="w-8 h-8 rounded-xl bg-slate-100 border border-slate-200 text-slate-400 flex items-center justify-center shrink-0">
        <MinusCircle size={15} />
      </div>
    );
  }

  return (
    <div className="w-8 h-8 rounded-xl bg-white border-2 border-slate-200 text-slate-400 text-xs font-black flex items-center justify-center shrink-0">
      {stage.index + 1}
    </div>
  );
};

const ApplicationStageTracker: React.FC<ApplicationStageTrackerProps> = ({
  tracker,
  audience = 'candidate',
  compact = false,
  className = '',
}) => {
  // Withdrawn end-state: replace active tracker with clear banner + read-only history
  if (tracker.isWithdrawn && tracker.withdrawalInfo) {
    const { withdrawnDateLabel, reasonCategory, detailNote } = tracker.withdrawalInfo;
    return (
      <div className={`space-y-4 ${className}`} data-testid="withdrawn-application-banner">
        <div className="rounded-2xl border border-slate-300 bg-slate-50 p-4 sm:p-5">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-slate-200 text-slate-700 flex items-center justify-center shrink-0">
              <Ban size={18} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-slate-200 text-slate-700">
                  Withdrawn
                </span>
                <h4 className="text-sm sm:text-base font-black text-slate-900">
                  {withdrawnDateLabel
                    ? `This application was withdrawn on ${withdrawnDateLabel}`
                    : 'This application was withdrawn'}
                </h4>
              </div>
              <p className="text-xs sm:text-sm font-semibold text-slate-600 mt-1">
                Reason: <span className="text-slate-900 font-bold">{reasonCategory}</span>
                {detailNote ? ` — ${detailNote}` : ''}
              </p>
              <p className="text-xs text-slate-500 mt-1">
                {audience === 'candidate'
                  ? 'This application is closed and read-only. Your application history is preserved below.'
                  : 'This application is withdrawn and read-only. It cannot be shortlisted, scheduled, or edited.'}
              </p>
            </div>
          </div>
        </div>

        {/* Candidate view shows read-only stage history; HR side shows Withdrawn badge & banner only (no tracker) */}
        {audience === 'candidate' && (
          <div className="rounded-2xl border border-slate-200/80 bg-white p-4">
            <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-3">
              Application History (Read-Only)
            </p>
            <div className={compact ? 'grid grid-cols-1 sm:grid-cols-5 gap-2.5' : 'space-y-3'}>
              {tracker.stages.map((stage) => {
                const isNA = stage.state === 'not_applicable';
                return (
                  <div
                    key={stage.key}
                    className={`flex items-start gap-2.5 p-2.5 rounded-xl border ${
                      isNA
                        ? 'bg-slate-50/70 border-slate-100 opacity-70'
                        : 'bg-emerald-50/40 border-emerald-100'
                    }`}
                  >
                    <StageCircle stage={stage} />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span
                          className={`text-xs font-bold ${
                            isNA ? 'text-slate-400' : 'text-slate-800'
                          }`}
                        >
                          {stage.label}
                        </span>
                        <span
                          className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase tracking-wider ${
                            isNA
                              ? 'bg-slate-200/80 text-slate-500'
                              : 'bg-emerald-100 text-emerald-700'
                          }`}
                        >
                          {isNA ? 'Not applicable' : 'Done'}
                        </span>
                        {stage.skipped && stage.skippedNote && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                            {stage.skippedNote}
                          </span>
                        )}
                      </div>
                      {stage.dateLabel && !isNA && (
                        <p className="text-[10px] text-slate-500 font-medium mt-0.5">
                          {stage.dateLabel}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`space-y-3.5 ${className}`} data-testid="application-stage-tracker">
      {/* 5-Stage Pipeline Steps */}
      <div
        className={
          compact
            ? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5'
            : 'space-y-3'
        }
      >
        {tracker.stages.map((stage) => {
          const isDone = stage.state === 'done';
          const isActive = stage.state === 'active';
          const isNA = stage.state === 'not_applicable';

          let cardClass = 'bg-slate-50/70 border-slate-200/70';
          if (isDone && stage.outcome === 'passed') {
            cardClass = 'bg-emerald-50/80 border-emerald-200';
          } else if (isDone && stage.outcome === 'not_selected') {
            cardClass = 'bg-rose-50/70 border-rose-200';
          } else if (isDone) {
            cardClass = 'bg-emerald-50/40 border-emerald-200/70';
          } else if (isActive && stage.outcome === 'awaiting') {
            cardClass = 'bg-amber-50/70 border-amber-300 shadow-xs';
          } else if (isActive) {
            cardClass = 'bg-rose-50/50 border-[#D60041]/30 shadow-xs';
          } else if (isNA) {
            cardClass = 'bg-slate-50/50 border-slate-100 opacity-70';
          }

          let badgeClass = 'bg-slate-100 text-slate-500';
          if (isDone && stage.outcome === 'passed') {
            badgeClass = 'bg-emerald-600 text-white';
          } else if (isDone && stage.outcome === 'not_selected') {
            badgeClass = 'bg-rose-100 text-rose-700';
          } else if (isDone) {
            badgeClass = 'bg-emerald-100 text-emerald-700';
          } else if (isActive && (stage.outcome === 'awaiting' || tracker.isOnHold)) {
            badgeClass = 'bg-amber-100 text-amber-800';
          } else if (isActive) {
            badgeClass = 'bg-[#D60041] text-white';
          }

          return (
            <div
              key={stage.key}
              className={`rounded-2xl border p-3 transition-colors ${cardClass}`}
            >
              <div className="flex items-start gap-2.5">
                <StageCircle stage={stage} isOnHold={tracker.isOnHold && isActive} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-1.5">
                    <span
                      className={`text-xs sm:text-sm font-black leading-tight ${
                        isNA ? 'text-slate-400' : 'text-slate-900'
                      }`}
                    >
                      {stage.label}
                    </span>
                    {stage.badgeText && (
                      <span
                        className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase tracking-wider shrink-0 ${badgeClass}`}
                      >
                        {stage.badgeText}
                      </span>
                    )}
                  </div>

                  {stage.skipped && stage.skippedNote && (
                    <div className="mt-1">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                        {stage.skippedNote}
                      </span>
                    </div>
                  )}

                  {!compact && (
                    <p
                      className={`text-xs mt-1 leading-relaxed ${
                        isNA ? 'text-slate-400' : 'text-slate-600'
                      }`}
                    >
                      {stage.subtitle}
                    </p>
                  )}

                  {stage.dateLabel && !isNA && (
                    <p className="text-[10px] font-semibold text-slate-400 mt-1">
                      {stage.dateLabel}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Initial Interview Result Outcome Callout */}
      {tracker.resultOutcome === 'passed' && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 flex items-start gap-3">
          <Award size={18} className="text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm">
            <p className="font-black text-emerald-900">
              Passed Initial Interview – Endorsed for next stage
            </p>
            <p className="text-emerald-800 font-medium mt-0.5">
              {audience === 'candidate'
                ? 'Congratulations! HR will contact you outside the system regarding the next stage of your application. This record is now read-only.'
                : 'Applicant passed the initial interview and has been endorsed for the next stage. This record is now read-only.'}
            </p>
          </div>
        </div>
      )}

      {tracker.resultOutcome === 'not_selected' && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 flex items-start gap-3">
          <Info size={18} className="text-slate-600 shrink-0 mt-0.5" />
          <div className="text-xs sm:text-sm">
            <p className="font-black text-slate-900">Not selected</p>
            <p className="text-slate-600 font-medium mt-0.5">
              {audience === 'candidate'
                ? 'Thank you for applying with Mariwasa. Your resume feedback report remains viewable in your portal.'
                : 'Application marked as Not selected. The applicant can still view their feedback report.'}
            </p>
          </div>
        </div>
      )}

      {tracker.resultOutcome === 'awaiting' && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 p-3.5 flex items-start gap-2.5">
          <Clock size={16} className="text-amber-600 shrink-0 mt-0.5" />
          <p className="text-xs font-semibold text-amber-900">
            {audience === 'candidate'
              ? 'Your initial interview date has passed. Status is awaiting result until HR records the outcome.'
              : 'Interview date has passed with no result recorded yet. Record Passed Initial Interview or Not selected when ready.'}
          </p>
        </div>
      )}
    </div>
  );
};

export default ApplicationStageTracker;
