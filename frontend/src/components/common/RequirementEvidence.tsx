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
  return <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
    <h4 className="text-sm font-bold text-slate-900">Requirement confirmations</h4>
    {items.map(item => <div key={`${item.field}:${item.requirement}`} className="border-t border-slate-100 pt-2 text-sm">
      <div className="flex flex-wrap justify-between gap-2">
        <span className="font-semibold">{item.requirement}</span>
        <span className={item.status === 'Does not meet' ? 'text-red-700' : item.status === 'Meets requirement' ? 'text-emerald-700' : 'text-slate-600'}>{item.status}</span>
      </div>
      <p className="text-xs text-slate-600">{item.source || 'Awaiting applicant confirmation'}{item.answer === 'some' ? ' — Some experience' : ''}</p>
      {!!item.evidence?.length && <p className="text-xs text-slate-600">Related evidence: {item.evidence.join(', ')}</p>}
      {item.years != null && <p className="text-xs text-slate-600">{item.years} years</p>}
      {item.details && <p className="text-xs text-slate-600">{item.details}</p>}
    </div>)}
  </section>;
}
