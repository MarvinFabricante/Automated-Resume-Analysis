import React from 'react';
import { HelpCircle, AlertTriangle, Info } from 'lucide-react';
import { ClarificationQuestion, parseRequirementAnswers } from '../../utils/clarificationQuestions';

export const CLARIFICATION_HONESTY_REMINDER =
  "Please answer honestly. Your answers may be used to guide your interview, so it is best to share only what is true. It's okay to answer 'No' or 'Some experience'. That will not automatically disqualify you.";

export const CLARIFICATION_SUBMIT_CONFIRMATION =
  'By submitting, you confirm your answers are true to the best of your knowledge.';

export const ClarificationSubmitConfirmation: React.FC<{ className?: string }> = ({ className = '' }) => (
  <p
    role="note"
    data-testid="clarification-submit-confirmation"
    className={`flex items-start gap-2 text-xs sm:text-sm text-slate-700 bg-sky-50/80 border border-sky-200/80 rounded-xl px-3.5 py-2.5 leading-relaxed ${className}`.trim()}
  >
    <Info size={16} className="text-sky-700 shrink-0 mt-0.5" aria-hidden="true" />
    <span>{CLARIFICATION_SUBMIT_CONFIRMATION}</span>
  </p>
);

interface ClarificationQuestionsPanelProps {
  questions: ClarificationQuestion[];
  answers: Record<string, string>;
  onAnswerChange: (question: ClarificationQuestion, value: string) => void;
  reasons?: string[];
  jobTitle?: string;
}

const ClarificationQuestionsPanel: React.FC<ClarificationQuestionsPanelProps> = ({
  questions,
  answers,
  onAnswerChange,
  reasons,
  jobTitle,
}) => {
  if (!questions || questions.length === 0) {
    return null;
  }

  const displayJobTitle =
    jobTitle && jobTitle !== 'Position'
      ? jobTitle
      : questions.find((q) => q.job_title)?.job_title;

  return (
    <section
      id="section-clarification-questions"
      data-testid="clarification-questions-section"
      className="bg-amber-50/70 p-6 sm:p-8 md:p-10 rounded-2xl sm:rounded-[32px] shadow-sm border-2 border-amber-200/80"
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3 text-amber-800">
          <div className="p-2.5 bg-amber-100 rounded-xl border border-amber-200">
            <AlertTriangle size={20} className="text-amber-600" />
          </div>
          <div>
            <h2 className="font-black uppercase tracking-widest text-xs sm:text-sm text-amber-900">
              Follow-Up Clarification Questions
              {displayJobTitle ? ` — ${displayJobTitle}` : ''}
            </h2>
            <p className="text-xs text-amber-700 font-medium mt-0.5">
              {displayJobTitle
                ? `Tailored follow-up questions for ${displayJobTitle} based on your resume and role requirements.`
                : 'Some details in your resume were vague or incomplete. Please answer below to improve matching accuracy.'}
            </p>
          </div>
        </div>
        <span className="self-start sm:self-center px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-[10px] font-black uppercase tracking-wider border border-amber-200">
          Clarification Requested ({questions.length})
        </span>
      </div>

      <div
        role="note"
        aria-label="Honesty reminder"
        data-testid="clarification-honesty-reminder"
        className="mb-5 p-3.5 sm:p-4 bg-sky-50 border border-sky-200 rounded-2xl flex items-start gap-3 text-slate-800"
      >
        <Info size={18} className="text-sky-700 shrink-0 mt-0.5" aria-hidden="true" />
        <p className="text-xs sm:text-sm leading-relaxed font-medium">
          <span className="font-bold text-slate-900">Friendly reminder: </span>
          {CLARIFICATION_HONESTY_REMINDER}
        </p>
      </div>

      {reasons && reasons.length > 0 && (
        <div className="mb-5 p-3.5 bg-white/80 rounded-2xl border border-amber-200/70 text-xs text-amber-900 space-y-1">
          {reasons.map((r, i) => (
            <p key={i} className="font-medium flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0" />
              <span>{r}</span>
            </p>
          ))}
        </div>
      )}

      <div className="space-y-5">
        {questions.map((q) => {
          const inputId = `clarify-${q.id}`;
          return (
            <div key={q.id} className="bg-white p-4 sm:p-5 rounded-2xl border border-amber-200/80 shadow-2xs">
              <label
                htmlFor={inputId}
                className="flex items-start gap-2 text-sm font-bold text-slate-900 mb-2"
              >
                <HelpCircle size={17} className="text-[#D10043] shrink-0 mt-0.5" />
                <span>
                  {q.question}
                  {q.required && <span className="text-[#D10043] ml-1">*</span>}
                </span>
              </label>

              {q.type === 'requirement_group' ? (
                <div className="space-y-4">
                  {(q.items || []).map((item, index) => {
                    const values = parseRequirementAnswers(answers[q.id]);
                    const value = values[item.requirement];
                    const update = (patch: object) => onAnswerChange(q, JSON.stringify({
                      ...values, [item.requirement]: { ...value, ...patch },
                    }));
                    return (
                      <fieldset key={item.requirement} className="rounded-xl border border-slate-200 p-3">
                        <legend className="px-1 text-sm font-semibold">{item.requirement}</legend>
                        <p className="text-xs text-slate-500 mb-2">
                          {item.status === 'Possible match' ? `Possible match: ${(item.evidence || []).join(', ')}. Please confirm.` : 'Not confirmed until answered.'}
                        </p>
                        <div className="flex flex-wrap gap-4">
                          {([['yes', 'Yes with experience'], ['some', 'Some experience'], ['no', 'No']] as const).map(([answer, label]) => (
                            <label key={answer} className="flex items-center gap-2 text-sm">
                              <input type="checkbox" name={`${q.id}-${index}`} checked={value?.answer === answer}
                                onChange={() => {
                                  if (value?.answer === answer) {
                                    const next = { ...values }; delete next[item.requirement];
                                    onAnswerChange(q, JSON.stringify(next));
                                  } else update({ answer });
                                }} />
                              {label}
                            </label>
                          ))}
                        </div>
                        <div className="flex flex-wrap gap-3 mt-3">
                          <label className="text-xs text-slate-600">Years (optional)
                            <input type="number" min="0" step="0.5" value={value?.years ?? ''}
                              onChange={e => update({ years: e.target.value === '' ? undefined : Number(e.target.value) })}
                              className="block w-24 rounded border border-slate-200 p-2" />
                          </label>
                          <label className="text-xs text-slate-600 flex-1">Details (optional)
                            <input value={value?.details || ''} onChange={e => update({ details: e.target.value })}
                              className="block w-full rounded border border-slate-200 p-2" />
                          </label>
                        </div>
                      </fieldset>
                    );
                  })}
                </div>
              ) : <input
                id={inputId}
                data-testid={inputId}
                name={q.id}
                type={q.type === 'number' ? 'number' : 'text'}
                min={q.type === 'number' ? '0' : undefined}
                step={q.type === 'number' ? '0.5' : undefined}
                value={answers[q.id] ?? ''}
                onChange={(e) => onAnswerChange(q, e.target.value)}
                placeholder={q.placeholder || 'Type your answer here...'}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl py-2.5 px-4 text-slate-900 text-sm font-semibold focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all"
              />}

              {q.reason && (
                <p className="text-[11px] text-slate-500 font-medium mt-1.5 pl-6">
                  {q.reason}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default ClarificationQuestionsPanel;

