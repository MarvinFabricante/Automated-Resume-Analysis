import React from 'react';
import { CheckCircle2 } from 'lucide-react';

export interface RequirementEvaluation {
  field: string;
  requirement: string;
  status: string;
  source?: string | null;
  answer?: string;
  evidence?: string[];
  details?: string;
  years?: number | null;
  confirmed_at?: string | null;
}

export interface RequirementEvidenceProps {
  items?: RequirementEvaluation[];
  clarificationResponses?: Array<Record<string, any>>;
  confirmedAt?: string | null;
  title?: string;
  interviewHint?: string;
}

function formatConfirmationDate(value?: string | null): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function normalizeClarificationItems(
  items: RequirementEvaluation[],
  clarificationResponses?: Array<Record<string, any>>
): RequirementEvaluation[] {
  if (items.length > 0) return items;
  if (!Array.isArray(clarificationResponses) || clarificationResponses.length === 0) return [];
  return clarificationResponses
    .filter((r) => r && typeof r === 'object' && r.requirement && ['yes', 'some', 'no'].includes(String(r.answer || '').toLowerCase()))
    .map((r) => {
      const answer = String(r.answer).toLowerCase();
      return {
        field: String(r.field || 'requirement'),
        requirement: String(r.requirement),
        status: answer === 'no' ? 'Does not meet' : 'Meets requirement',
        source: 'Confirmed by applicant',
        answer,
        details: typeof r.details === 'string' ? r.details : undefined,
        years: typeof r.years === 'number' ? r.years : null,
        confirmed_at: typeof r.confirmed_at === 'string' ? r.confirmed_at : null,
      };
    });
}

export default function RequirementEvidence({
  items = [],
  clarificationResponses,
  confirmedAt,
  title = 'Requirement Confirmations & Evidence',
  interviewHint,
}: RequirementEvidenceProps) {
  const displayItems = normalizeClarificationItems(items, clarificationResponses);
  if (!displayItems.length) return null;

  const hasApplicantConfirmation =
    displayItems.some((item) => item.source === 'Confirmed by applicant') ||
    (Array.isArray(clarificationResponses) &&
      clarificationResponses.some((r) => r && ['yes', 'some', 'no'].includes(String(r.answer || '').toLowerCase())));

  const rawConfirmedDate =
    displayItems.find((item) => item.source === 'Confirmed by applicant' && item.confirmed_at)?.confirmed_at ||
    (Array.isArray(clarificationResponses)
      ? clarificationResponses.find((r) => r && typeof r.confirmed_at === 'string' && r.confirmed_at)?.confirmed_at
      : null) ||
    confirmedAt ||
    null;

  const formattedConfirmedDate = formatConfirmationDate(rawConfirmedDate);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 space-y-3">
      <div className="space-y-1.5">
        <h4 className="text-sm font-bold text-slate-900">{title}</h4>
        {interviewHint && (
          <p className="text-xs text-slate-600">{interviewHint}</p>
        )}
        {hasApplicantConfirmation && (
          <div
            data-testid="applicant-honesty-confirmation"
            className="flex flex-wrap items-center gap-2 rounded-lg border border-sky-200 bg-sky-50 px-3 py-2 text-xs text-slate-800"
          >
            <CheckCircle2 size={14} className="text-sky-700 shrink-0" aria-hidden="true" />
            <span className="font-semibold text-slate-900">
              Applicant confirmed the answers are true
            </span>
            {formattedConfirmedDate && (
              <span className="text-slate-600">• {formattedConfirmedDate}</span>
            )}
          </div>
        )}
      </div>
      {displayItems.map((item) => {
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
