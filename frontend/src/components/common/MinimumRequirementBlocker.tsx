'use client';

import React from 'react';
import { ShieldAlert, FileUp, Briefcase, AlertCircle, Sparkles, Lightbulb } from 'lucide-react';

export function isBelowAcceptedRequirements(matchData: any): boolean {
  if (!matchData || typeof matchData !== 'object') return false;
  if (matchData.eligible_to_apply === false) return true;
  if (matchData.meets_threshold === false) return true;
  return false;
}

export function getEligibilityBlockReasons(matchData: any): string[] {
  if (!matchData || typeof matchData !== 'object') return [];
  if (Array.isArray(matchData.eligibility_reasons) && matchData.eligibility_reasons.length > 0) {
    return matchData.eligibility_reasons.filter(Boolean).map(String);
  }

  const reasons: string[] = [];
  const score = Number(matchData.match_percentage ?? 0);
  const minScore = Number(matchData.minimum_match_score ?? 30);

  if (matchData.meets_threshold === false || score < minScore) {
    reasons.push(
      `Your profile match score (${Math.round(score)}%) is below the accepted minimum requirement (${Math.round(minScore)}%).`
    );
  }
  if (Array.isArray(matchData.missing_skills) && matchData.missing_skills.length > 0) {
    reasons.push(
      `Missing required skills: ${matchData.missing_skills.slice(0, 5).join(', ')}${matchData.missing_skills.length > 5 ? ` (+${matchData.missing_skills.length - 5} more)` : ''}.`
    );
  }
  if (matchData.experience_below_minimum && matchData.experience_gaps) {
    reasons.push(String(matchData.experience_gaps));
  }
  if (reasons.length === 0 && matchData.eligible_to_apply === false) {
    reasons.push('Your profile does not meet the minimum accepted qualifications for this position.');
  }
  return reasons;
}

interface MinimumRequirementBlockerProps {
  matchData: any;
  jobTitle?: string;
  onUploadDifferent?: () => void;
  onBrowseJobs?: () => void;
  compact?: boolean;
  className?: string;
}

const MinimumRequirementBlocker: React.FC<MinimumRequirementBlockerProps> = ({
  matchData,
  jobTitle,
  onUploadDifferent,
  onBrowseJobs,
  compact = false,
  className = '',
}) => {
  if (!isBelowAcceptedRequirements(matchData)) return null;

  const score = Math.round(Number(matchData?.match_percentage ?? 0));
  const minScore = Math.round(Number(matchData?.minimum_match_score ?? 30));
  const reasons = getEligibilityBlockReasons(matchData);
  const aiVerified = Boolean(matchData?.ai_eligibility_verified || matchData?.ai_powered);
  const tips: string[] = Array.isArray(matchData?.recommendations)
    ? matchData.recommendations.filter(Boolean).map(String).slice(0, 2)
    : [];

  return (
    <div
      role="alert"
      data-testid="below-requirements-blocker"
      className={`bg-rose-50 border-2 border-rose-200 rounded-[24px] ${compact ? 'p-4 sm:p-5' : 'p-5 sm:p-7'} text-left shadow-sm animate-in fade-in duration-200 ${className}`}
    >
      <div className="flex flex-col sm:flex-row sm:items-start gap-4">
        <div className="w-12 h-12 rounded-2xl bg-rose-600 text-white flex items-center justify-center shrink-0 shadow-md shadow-rose-200">
          <ShieldAlert size={24} />
        </div>

        <div className="flex-1 min-w-0 space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-rose-600 text-white text-[10px] font-black uppercase tracking-widest">
                Application Blocked
              </span>
              <span className="px-2.5 py-0.5 rounded-full bg-white text-rose-700 border border-rose-200 text-[11px] font-black">
                Match: {score}% / Required: {minScore}%+
              </span>
              {aiVerified && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-black uppercase tracking-wider">
                  <Sparkles size={11} />
                  AI Verified
                </span>
              )}
            </div>
          </div>

          <div>
            <h4 className="text-base sm:text-lg font-black text-rose-950 leading-snug">
              Below Accepted Requirements{jobTitle ? ` for ${jobTitle}` : ''}
            </h4>
            <p className="text-xs sm:text-sm text-rose-800 font-medium mt-1 leading-relaxed">
              You cannot proceed with this application because your current qualifications fall below the accepted minimum requirements for this role.
            </p>
          </div>

          {reasons.length > 0 && (
            <ul className="space-y-1.5 bg-white/80 rounded-xl p-3.5 border border-rose-100">
              {reasons.map((reason, idx) => (
                <li key={idx} className="flex items-start gap-2 text-xs text-rose-900 font-semibold leading-relaxed">
                  <AlertCircle size={14} className="text-rose-600 shrink-0 mt-0.5" />
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          )}

          {tips.length > 0 && (
            <div className="bg-amber-50/80 border border-amber-200/80 rounded-xl p-3 space-y-1">
              <div className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-wider text-amber-800">
                <Lightbulb size={12} className="text-amber-600" />
                <span>How to Qualify</span>
              </div>
              {tips.map((tip, idx) => (
                <p key={idx} className="text-xs text-amber-950 font-medium leading-relaxed">
                  • {tip}
                </p>
              ))}
            </div>
          )}

          {(onUploadDifferent || onBrowseJobs) && (
            <div className="flex flex-wrap gap-2.5 pt-1">
              {onUploadDifferent && (
                <button
                  type="button"
                  onClick={onUploadDifferent}
                  className="px-4 py-2.5 rounded-xl bg-white hover:bg-rose-100/70 text-rose-900 border border-rose-200 text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <FileUp size={14} />
                  <span>Upload Updated Resume</span>
                </button>
              )}
              {onBrowseJobs && (
                <button
                  type="button"
                  onClick={onBrowseJobs}
                  className="px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-[#D60041] text-white text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Briefcase size={14} />
                  <span>Browse Matching Positions</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MinimumRequirementBlocker;
