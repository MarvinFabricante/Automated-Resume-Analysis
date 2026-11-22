import React, { useEffect, useRef } from 'react';
import {
  X,
  Target,
  Cpu,
  Briefcase,
  GraduationCap,
  CheckCircle2,
  XCircle,
  ArrowRight,
  FileText,
  Clock,
  MapPin,
  Sparkles,
} from 'lucide-react';
import HelpTooltip from '../common/HelpTooltip';
import {
  resolveCriterionStatus,
  getCriterionStatusBadgeStyle,
} from '../../utils/criterionStatus';

interface DetailedAnalysisDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  match: any;
  candidateName?: string;
  triggerRef?: React.RefObject<HTMLButtonElement | null>;
  onViewDescription: () => void;
  onStartApplication: () => void;
}

/**
 * Transforms third-person candidate descriptions into natural Grade-8 second-person text.
 * Example: "John Doe matches 2 of 4 skills." -> "Your resume matches 2 of 4 skills."
 * Example: "Gap reported: experience below minimum — Required: 2 yrs | Candidate: 0 yrs"
 *       -> "Experience: this job asks for 2 years; your resume shows 0."
 */
export function formatSecondPersonText(text: string | undefined | null, candidateName?: string): string {
  if (!text) return '';

  let formatted = String(text);

  // Simplify standard gap reporting pattern
  formatted = formatted.replace(
    /Gap reported:\s*experience below minimum\s*—\s*Required:\s*(\d+)\s*yrs?\s*\|\s*Candidate:\s*(\d+)\s*yrs?(\s*\([^)]*\))?/gi,
    (_match, req, cand) => `Experience: this job asks for ${req} year${Number(req) === 1 ? '' : 's'}; your resume shows ${cand}.`
  );

  // Replace candidate name occurrences
  if (candidateName && candidateName.trim().length > 1) {
    const escapedName = candidateName.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const nameRegexPossessive = new RegExp(`${escapedName}['’]s`, 'gi');
    const nameRegex = new RegExp(escapedName, 'gi');
    formatted = formatted.replace(nameRegexPossessive, 'Your');
    formatted = formatted.replace(nameRegex, 'You');
  }

  // Replace generic third-person references (phrase-specific before standalone noun)
  formatted = formatted.replace(/\bthe candidate['’]s\b/gi, 'your');
  formatted = formatted.replace(/\bcandidate['’]s\b/gi, 'your');
  formatted = formatted.replace(/\bthe applicant['’]s\b/gi, 'your');
  formatted = formatted.replace(/\bcandidate\s+education\b/gi, 'your education');
  formatted = formatted.replace(/\bcandidate\s+certifications?\b/gi, (m) =>
    m.toLowerCase().endsWith('s') ? 'your certifications' : 'your certification'
  );
  formatted = formatted.replace(/\bcandidate\s+experience\b/gi, 'your experience');
  formatted = formatted.replace(/\bcandidate\s+skills?\b/gi, (m) =>
    m.toLowerCase().endsWith('s') ? 'your skills' : 'your skill'
  );
  formatted = formatted.replace(/\bcandidate\s+holds\b/gi, 'you hold');
  formatted = formatted.replace(/\bcandidate\s+listed\b/gi, 'you listed');
  formatted = formatted.replace(/\bcandidate\s+has\b/gi, 'you have');
  formatted = formatted.replace(/\bthe candidate\b/gi, 'you');
  formatted = formatted.replace(/\bcandidate\b/gi, 'you');
  formatted = formatted.replace(/\bthe applicant\b/gi, 'you');

  // Fix verb agreement for second-person "You"
  formatted = formatted.replace(/\bYou matches\b/g, 'You match');
  formatted = formatted.replace(/\byou matches\b/g, 'you match');
  formatted = formatted.replace(/\bYou demonstrates\b/g, 'You demonstrate');
  formatted = formatted.replace(/\byou demonstrates\b/g, 'you demonstrate');
  formatted = formatted.replace(/\bYou lacks\b/g, 'You lack');
  formatted = formatted.replace(/\byou lacks\b/g, 'you lack');
  formatted = formatted.replace(/\bYou requires\b/g, 'You require');
  formatted = formatted.replace(/\byou requires\b/g, 'you require');
  formatted = formatted.replace(/\bYou shows\b/g, 'You show');
  formatted = formatted.replace(/\byou shows\b/g, 'you show');
  formatted = formatted.replace(/\bYou holds\b/g, 'You hold');
  formatted = formatted.replace(/\byou holds\b/g, 'you hold');
  formatted = formatted.replace(/\bYou exceeds\b/g, 'You exceed');
  formatted = formatted.replace(/\byou exceeds\b/g, 'you exceed');
  formatted = formatted.replace(/\bYou meets\b/g, 'You meet');
  formatted = formatted.replace(/\byou meets\b/g, 'you meet');
  formatted = formatted.replace(/\bYou is\b/g, 'You are');
  formatted = formatted.replace(/\byou is\b/g, 'you are');
  formatted = formatted.replace(/\bYou has\b/g, 'You have');
  formatted = formatted.replace(/\byou has\b/g, 'you have');

  // Capitalize sentence beginnings
  formatted = formatted.replace(/(^\s*|[.?!]\s+)([a-z])/g, (_m, pre, ch) => pre + ch.toUpperCase());

  return formatted.trim();
}

const DetailedAnalysisDrawer: React.FC<DetailedAnalysisDrawerProps> = ({
  isOpen,
  onClose,
  match,
  candidateName,
  triggerRef,
  onViewDescription,
  onStartApplication,
}) => {
  const drawerRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Focus trap & escape key handler
  useEffect(() => {
    if (!isOpen) return;

    // Body scroll lock
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    // Focus close button initially
    const timer = setTimeout(() => {
      closeButtonRef.current?.focus();
    }, 50);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab' && drawerRef.current) {
        const focusable = drawerRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      clearTimeout(timer);
      document.body.style.overflow = originalOverflow;
      document.removeEventListener('keydown', handleKeyDown);
      // Return focus to trigger button
      triggerRef?.current?.focus();
    };
  }, [isOpen, onClose, triggerRef]);

  if (!isOpen || !match) return null;

  const score = Math.round(match.match_percentage || 0);
  const scoreColor = score >= 70 ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
    : score >= 40 ? 'text-amber-700 bg-amber-50 border-amber-200'
    : 'text-rose-700 bg-rose-50 border-rose-200';

  const skillsReason = formatSecondPersonText(match.skills_reason, candidateName);
  const expReason = formatSecondPersonText(match.experience_reason || match.experience_explanation, candidateName);
  const eduReason = formatSecondPersonText(match.education_reason, candidateName);
  const certsReason = formatSecondPersonText(match.certifications_reason || match.certification_explanation, candidateName);
  const aiSummary = formatSecondPersonText(match.ai_summary, candidateName);

  const skillsStatus = resolveCriterionStatus({
    explicitStatus: match.skills_status,
    reason: match.skills_reason,
    score: match.skills_score,
  });
  const expStatus = resolveCriterionStatus({
    explicitStatus: match.experience_status,
    reason: match.experience_reason,
    score: match.experience_score,
    isBelowMinimum: Boolean(match.experience_below_minimum),
  });
  const eduStatus = resolveCriterionStatus({
    explicitStatus: match.education_status,
    reason: match.education_reason,
    score: match.education_score,
  });
  const certsStatus = resolveCriterionStatus({
    explicitStatus: match.certifications_status,
    reason: match.certifications_reason || match.certification_explanation,
    score: match.certifications_score,
  });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      className="fixed inset-0 z-50 overflow-hidden"
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity duration-200 animate-in fade-in motion-reduce:transition-none"
        aria-hidden="true"
      />

      {/* Drawer Container (Desktop right panel / Mobile bottom sheet) */}
      <div className="fixed inset-0 flex justify-end pointer-events-none">
        <div
          ref={drawerRef}
          className="pointer-events-auto w-full md:max-w-xl bg-white shadow-2xl flex flex-col h-full max-h-screen md:h-full md:rounded-l-3xl rounded-t-3xl md:rounded-tr-none border-l border-slate-200 animate-in slide-in-from-right duration-200 max-md:animate-in max-md:slide-in-from-bottom motion-reduce:transition-none motion-reduce:animate-none overflow-hidden"
        >
          {/* Header */}
          <div className="p-5 sm:p-6 border-b border-slate-100 flex items-start justify-between gap-4 bg-gradient-to-r from-slate-50/80 to-white shrink-0">
            <div className="min-w-0 pr-2">
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <span className="text-[10px] font-black uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-rose-50 text-[#D10043] border border-rose-100">
                  {match.department || 'Open Position'}
                </span>
                <span className={`text-[11px] font-black px-2.5 py-0.5 rounded-full border ${scoreColor}`}>
                  {score}% Match
                </span>
              </div>
              <h2
                id="drawer-title"
                className="text-lg sm:text-xl font-black text-slate-900 tracking-tight leading-snug break-words"
              >
                {match.job_title}
              </h2>
              <div className="flex items-center gap-3 text-xs text-slate-500 font-medium mt-1">
                <span className="flex items-center gap-1">
                  <MapPin size={12} className="text-slate-400" />
                  {match.location || 'Sto. Tomas, Batangas'}
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock size={12} className="text-slate-400" />
                  {match.job_type || 'Full-time'}
                </span>
              </div>
            </div>

            <button
              ref={closeButtonRef}
              type="button"
              onClick={onClose}
              aria-label="Close panel"
              className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D10043]"
            >
              <X size={20} />
            </button>
          </div>

          {/* Scrollable Body Content */}
          <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6 custom-scrollbar">

            {/* Overall Match Summary */}
            {aiSummary && (
              <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-xs text-slate-700 leading-relaxed font-medium">
                <p className="font-bold text-slate-900 mb-1 flex items-center gap-1.5">
                  <Sparkles size={14} className="text-[#D10043]" />
                  How well you fit this job
                </p>
                <p>{aiSummary}</p>
              </div>
            )}

            {/* Why You Fit This Role */}
            <section className="space-y-3">
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                  <Target size={14} className="text-[#D10043]" />
                  Why you fit this role
                </h3>
                <HelpTooltip text="A plain-language summary of how your skills and background match this job's daily needs." />
              </div>

              <div className="space-y-2.5">
                {skillsReason && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <p className="text-xs font-bold text-slate-900">Skills Alignment</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getCriterionStatusBadgeStyle(skillsStatus).badgeClass}`}>
                        {skillsStatus}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{skillsReason}</p>
                  </div>
                )}

                {expReason && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <p className="text-xs font-bold text-slate-900">Experience Background</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getCriterionStatusBadgeStyle(expStatus).badgeClass}`}>
                        {expStatus}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{expReason}</p>
                  </div>
                )}

                {eduReason && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <p className="text-xs font-bold text-slate-900">Education</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getCriterionStatusBadgeStyle(eduStatus).badgeClass}`}>
                        {eduStatus}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{eduReason}</p>
                  </div>
                )}

                {certsReason && (
                  <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <p className="text-xs font-bold text-slate-900">Certifications & Trainings</p>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getCriterionStatusBadgeStyle(certsStatus).badgeClass}`}>
                        {certsStatus}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 leading-relaxed">{certsReason}</p>
                  </div>
                )}
              </div>
            </section>

            {/* Skills You Have */}
            <section className="space-y-3">
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                  <Cpu size={14} className="text-emerald-600" />
                  Skills you have
                </h3>
                <HelpTooltip text="Specific skills detected on your resume that match what this position asks for." />
              </div>

              {match.matched_skills && match.matched_skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {match.matched_skills.map((skill: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200/60 flex items-center gap-1"
                    >
                      <CheckCircle2 size={12} className="text-emerald-600 shrink-0" />
                      <span>{skill}</span>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No exact skill matches detected yet.</p>
              )}
            </section>

            {/* Transferable Skills (if any) */}
            {match.transferable_skills && match.transferable_skills.length > 0 && (
              <section className="space-y-3">
                <div className="flex items-center gap-1.5">
                  <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                    <Sparkles size={14} className="text-blue-600" />
                    Transferable skills
                  </h3>
                  <HelpTooltip text="Skills from your experience that can be applied to this role." />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {match.transferable_skills.map((skill: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-blue-50 text-blue-800 border border-blue-200/60"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {/* Skills You Can Add */}
            <section className="space-y-3">
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-900 flex items-center gap-1.5">
                  <XCircle size={14} className="text-amber-500" />
                  Skills you can add
                </h3>
                <HelpTooltip text="Skills mentioned in the job description that were not detected on your resume." />
              </div>

              {match.missing_skills && match.missing_skills.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {match.missing_skills.map((skill: string, idx: number) => (
                    <span
                      key={idx}
                      className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200/60"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-emerald-700 font-medium flex items-center gap-1">
                  <CheckCircle2 size={13} />
                  <span>You have all required skills for this job!</span>
                </p>
              )}
            </section>

          </div>

          {/* Sticky Drawer Footer Actions */}
          <div className="p-4 sm:p-5 border-t border-slate-200 bg-white flex flex-col sm:flex-row items-stretch gap-2.5 shrink-0 shadow-lg">
            <button
              type="button"
              onClick={() => {
                onClose();
                onViewDescription();
              }}
              className="flex-1 py-3 px-4 rounded-xl border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 font-bold text-xs uppercase tracking-wider transition-colors cursor-pointer text-center"
            >
              View Full Description
            </button>
            <button
              type="button"
              onClick={() => {
                onClose();
                onStartApplication();
              }}
              className="flex-[1.5] py-3 px-5 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm shadow-[#D10043]/20 active:scale-[0.98] cursor-pointer"
            >
              <span>Start Application</span>
              <ArrowRight size={14} />
            </button>
          </div>

        </div>
      </div>
    </div>
  );
};

export default DetailedAnalysisDrawer;
