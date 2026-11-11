'use client';

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { getExperienceGapStatus } from '../../utils/clarificationQuestions';

interface ExperienceGapAlertProps {
  matchData?: any;
  job?: any;
  yearsExperience?: number | string | null;
  className?: string;
}

const ExperienceGapAlert: React.FC<ExperienceGapAlertProps> = ({
  matchData,
  job,
  yearsExperience,
  className = '',
}) => {
  const gap = getExperienceGapStatus(matchData, job, yearsExperience);
  if (!gap) return null;

  return (
    <div
      role="alert"
      data-testid="experience-gap-alert"
      className={`bg-rose-50/90 border border-rose-200 rounded-2xl p-4 sm:p-5 flex items-start gap-3.5 text-left ${className}`}
    >
      <div className="p-2 bg-white rounded-xl border border-rose-200 text-rose-600 shrink-0 shadow-2xs">
        <AlertTriangle size={18} />
      </div>
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-rose-600 text-white">
            Insufficient Experience
          </span>
          <h4 className="text-xs sm:text-sm font-black text-rose-950 uppercase tracking-wide">
            Gap Reported: Experience Below Minimum
          </h4>
        </div>
        <p className="text-xs sm:text-sm text-rose-900 font-semibold leading-relaxed">
          {gap.message}
        </p>
        {matchData?.experience_reason &&
          !/below minimum/i.test(matchData.experience_reason) && (
            <p className="text-xs text-rose-700 font-medium">
              {matchData.experience_reason}
            </p>
          )}
      </div>
    </div>
  );
};

export default ExperienceGapAlert;

