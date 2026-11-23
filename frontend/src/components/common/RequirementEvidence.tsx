import React from 'react';

export interface RequirementEvaluation {
  field: string;
  requirement: string;
  status: string;
  source?: string | null;
  answer?: string;
  evidence?: string[];
  details?: string;
  years?: number | null;
}

export default function RequirementEvidence({ items = [] }: { items?: RequirementEvaluation[] }) {
  if (!items.length) return null;
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
      <h4 className="text-sm font-bold text-slate-900">Requirement Confirmations &amp; Evidence</h4>
      {items.map((item) => {
        const statusBadge =
          item.status === 'Does not meet'
            ? 'bg-rose-50 text-rose-700 border-rose-200'
            : item.status === 'Meets requirement'
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : item.status === 'Possible match'
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : 'bg-slate-100 text-slate-700 border-slate-200';
        const isApplicantConfirmed = item.source === 'Confirmed by applicant';
        return (
          <div key={`${item.field}:${item.requirement}`} className="border-t border-slate-100 pt-2.5 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-slate-900">{item.requirement}</span>
                {isApplicantConfirmed && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200">
                    Confirmed by applicant
                  </span>
                )}
              </div>
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${statusBadge}`}>
                {item.status}
              </span>
            </div>
            <p className="text-xs text-slate-600 mt-1">
              {item.source || 'Not confirmed — awaiting applicant confirmation'}
              {item.answer === 'some' ? ' — Some experience' : item.answer === 'yes' ? ' — Yes with experience' : item.answer === 'no' ? ' — Answered No' : ''}
            </p>
            {!!item.evidence?.length && (
              <p className="text-xs text-amber-700 mt-0.5">Related evidence: {item.evidence.join(', ')}</p>
            )}
            {item.years != null && <p className="text-xs text-slate-600 mt-0.5">{item.years} years</p>}
            {item.details && <p className="text-xs text-slate-600 mt-0.5">{item.details}</p>}
          </div>
        );
      })}
    </section>
  );
}
