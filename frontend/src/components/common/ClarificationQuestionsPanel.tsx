import React from 'react';
import { HelpCircle, AlertTriangle } from 'lucide-react';
import { ClarificationQuestion } from '../../utils/clarificationQuestions';

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

              <input
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
              />

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

