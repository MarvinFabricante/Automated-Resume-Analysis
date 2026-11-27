import React, { useEffect, useId, useState } from 'react';
import { AlertCircle, Check, CheckCircle2, Globe, Sparkles, Video } from 'lucide-react';
import {
  MEETING_PLATFORMS,
  MeetingPlatform,
  PLATFORM_PLACEHOLDERS,
  applyMeetingLinkChange,
  detectMeetingPlatform,
  isMeetingLinkValidForPlatform,
  resolveMeetingPlatform,
  validMeetingLink,
  validateMeetingLinkForPlatform,
} from '../../../utils/meetingPlatform';

export { validMeetingLink };

export interface InterviewVenue {
  interviewType: string;
  location: string;
  meetingLink: string;
  instructions: string;
  platform: string;
}

export const emptyInterviewVenue: InterviewVenue = {
  interviewType: '',
  location: '',
  meetingLink: '',
  instructions: '',
  platform: '',
};

export function validInterviewVenue(value: InterviewVenue): boolean {
  return value.interviewType === 'Onsite'
    ? !!value.location.trim()
    : value.interviewType === 'Online' &&
        isMeetingLinkValidForPlatform(value.meetingLink, value.platform);
}

export function getInterviewVenueError(value: InterviewVenue): string | null {
  if (!value.interviewType) {
    return 'Choose an interview type (Onsite or Online).';
  }
  if (value.interviewType === 'Onsite') {
    return value.location.trim() ? null : 'Enter the interview location.';
  }
  if (value.interviewType === 'Online') {
    return validateMeetingLinkForPlatform(value.meetingLink, value.platform).error;
  }
  return 'Choose an interview type (Onsite or Online).';
}

export function venuePayload(value: InterviewVenue) {
  return {
    interview_type: value.interviewType,
    location: value.interviewType === 'Onsite' ? value.location.trim() : null,
    meeting_link: value.interviewType === 'Online' ? value.meetingLink.trim() : null,
    instructions: value.instructions.trim() || null,
    platform:
      value.interviewType === 'Online'
        ? resolveMeetingPlatform(value.meetingLink, value.platform)
        : null,
  };
}

const PLATFORM_STYLES: Record<
  MeetingPlatform,
  { active: string; dot: string; idle: string }
> = {
  'Google Meet': {
    active: 'bg-emerald-50 border-emerald-500 text-emerald-800 shadow-xs ring-1 ring-emerald-500/20',
    dot: 'bg-emerald-500',
    idle: 'bg-white border-gray-200 text-gray-700 hover:border-emerald-300 hover:bg-emerald-50/40',
  },
  Zoom: {
    active: 'bg-blue-50 border-blue-500 text-blue-800 shadow-xs ring-1 ring-blue-500/20',
    dot: 'bg-blue-500',
    idle: 'bg-white border-gray-200 text-gray-700 hover:border-blue-300 hover:bg-blue-50/40',
  },
  'Microsoft Teams': {
    active: 'bg-indigo-50 border-indigo-500 text-indigo-800 shadow-xs ring-1 ring-indigo-500/20',
    dot: 'bg-indigo-500',
    idle: 'bg-white border-gray-200 text-gray-700 hover:border-indigo-300 hover:bg-indigo-50/40',
  },
  Other: {
    active: 'bg-slate-100 border-slate-700 text-slate-900 shadow-xs ring-1 ring-slate-700/15',
    dot: 'bg-slate-500',
    idle: 'bg-white border-gray-200 text-gray-700 hover:border-slate-400 hover:bg-slate-50',
  },
};

export default function InterviewVenueFields({
  value,
  onChange,
  companyAddress = '',
}: {
  value: InterviewVenue;
  onChange: (value: InterviewVenue) => void;
  companyAddress?: string;
}) {
  const id = useId();
  const [switchNotice, setSwitchNotice] = useState<string | null>(null);

  useEffect(() => {
    if (value.interviewType !== 'Online' || !value.meetingLink.trim()) {
      setSwitchNotice(null);
    }
  }, [value.interviewType, value.meetingLink]);

  const field =
    'w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all';
  const error = 'text-xs text-red-700 mt-1';

  const linkValidation =
    value.interviewType === 'Online'
      ? validateMeetingLinkForPlatform(value.meetingLink, value.platform)
      : null;

  const placeholder =
    PLATFORM_PLACEHOLDERS[(value.platform as MeetingPlatform) || ''] ||
    PLATFORM_PLACEHOLDERS[''];

  const handleLinkChange = (nextLink: string) => {
    const { platform: nextPlatform, autoDetected, switchedFrom } =
      applyMeetingLinkChange(value.platform, nextLink);

    if (switchedFrom && autoDetected) {
      setSwitchNotice(
        `Detected ${autoDetected} link — platform switched from ${switchedFrom} to ${autoDetected}.`,
      );
    } else if (autoDetected && !value.platform) {
      setSwitchNotice(`Auto-detected ${autoDetected} from the meeting link.`);
    } else if (!nextLink.trim() || !autoDetected) {
      setSwitchNotice(null);
    }

    onChange({
      ...value,
      meetingLink: nextLink,
      platform: nextPlatform,
    });
  };

  const handleLinkBlur = () => {
    if (!value.platform && validMeetingLink(value.meetingLink)) {
      const detected = detectMeetingPlatform(value.meetingLink);
      if (detected) {
        setSwitchNotice(`Auto-detected ${detected} from the meeting link.`);
        onChange({ ...value, platform: detected });
      }
    }
  };

  const handlePlatformClick = (platform: MeetingPlatform) => {
    setSwitchNotice(null);
    onChange({ ...value, platform });
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div className={value.interviewType === 'Online' ? 'sm:col-span-2' : ''}>
        <label htmlFor={`${id}-type`} className="block text-sm font-semibold mb-1">
          Interview type *
        </label>
        <select
          id={`${id}-type`}
          className={field}
          required
          value={value.interviewType}
          aria-describedby={`${id}-type-error`}
          aria-invalid={!value.interviewType}
          onChange={(e) =>
            onChange({
              ...value,
              interviewType: e.target.value,
              location: value.location || companyAddress,
            })
          }
        >
          <option value="">Choose interview type</option>
          <option>Onsite</option>
          <option>Online</option>
        </select>
        {!value.interviewType && (
          <p id={`${id}-type-error`} className={error}>
            Choose Onsite or Online.
          </p>
        )}
      </div>

      {value.interviewType === 'Onsite' && (
        <>
          <div>
            <label htmlFor={`${id}-location`} className="block text-sm font-semibold mb-1">
              Location *
            </label>
            <input
              id={`${id}-location`}
              className={field}
              required
              value={value.location}
              aria-invalid={!value.location.trim()}
              aria-describedby={`${id}-location-error`}
              onChange={(e) => onChange({ ...value, location: e.target.value })}
            />
            {!value.location.trim() && (
              <p id={`${id}-location-error`} className={error}>
                Enter the interview location.
              </p>
            )}
          </div>
          <div className="sm:col-span-2">
            <label htmlFor={`${id}-instructions`} className="block text-sm font-semibold mb-1">
              Extra instructions (optional)
            </label>
            <textarea
              id={`${id}-instructions`}
              className={field}
              value={value.instructions}
              placeholder="Which gate, who to look for, or what to bring"
              onChange={(e) => onChange({ ...value, instructions: e.target.value })}
            />
          </div>
        </>
      )}

      {value.interviewType === 'Online' && (
        <>
          <div className="sm:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
              <span id={`${id}-platform-label`} className="block text-sm font-semibold text-gray-900">
                Platform
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-gray-500">
                <Sparkles size={12} className="text-[#D60041]" />
                {value.platform && linkValidation?.valid
                  ? `Matched to ${value.platform}`
                  : 'Auto-updates from the meeting link'}
              </span>
            </div>
            <div
              role="group"
              aria-labelledby={`${id}-platform-label`}
              className="grid grid-cols-2 sm:grid-cols-4 gap-2"
            >
              {MEETING_PLATFORMS.map((platform) => {
                const isSelected = value.platform === platform;
                const styles = PLATFORM_STYLES[platform];
                return (
                  <button
                    key={platform}
                    type="button"
                    aria-pressed={isSelected}
                    data-platform={platform}
                    onClick={() => handlePlatformClick(platform)}
                    className={`px-3 py-2 rounded-xl border text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
                      isSelected ? styles.active : styles.idle
                    }`}
                  >
                    {isSelected ? (
                      <Check size={13} className="shrink-0" />
                    ) : platform === 'Other' ? (
                      <Globe size={13} className="shrink-0 opacity-60" />
                    ) : (
                      <Video size={13} className="shrink-0 opacity-60" />
                    )}
                    <span className="truncate">{platform}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="sm:col-span-2">
            <label htmlFor={`${id}-link`} className="block text-sm font-semibold mb-1">
              Meeting link *
            </label>
            <input
              id={`${id}-link`}
              type="url"
              className={`${field} ${
                linkValidation && !linkValidation.valid && value.meetingLink.trim()
                  ? 'border-red-400 focus:border-red-500 focus:ring-red-200'
                  : linkValidation?.valid
                    ? 'border-emerald-400 focus:border-emerald-500 focus:ring-emerald-200'
                    : ''
              }`}
              required
              value={value.meetingLink}
              placeholder={placeholder}
              aria-invalid={Boolean(linkValidation && !linkValidation.valid)}
              aria-describedby={`${id}-link-feedback`}
              onChange={(e) => handleLinkChange(e.target.value)}
              onBlur={handleLinkBlur}
            />

            {linkValidation && !linkValidation.valid && (
              <div
                id={`${id}-link-feedback`}
                role="alert"
                className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-red-700 font-medium"
              >
                <span className="inline-flex items-start gap-1.5">
                  <AlertCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{linkValidation.error}</span>
                </span>
                {linkValidation.suggestedPlatform && (
                  <button
                    type="button"
                    onClick={() => handlePlatformClick(linkValidation.suggestedPlatform!)}
                    className="px-2 py-0.5 rounded-lg bg-red-50 hover:bg-red-100 border border-red-200 text-red-800 font-bold text-[11px] transition-colors cursor-pointer"
                  >
                    Switch to {linkValidation.suggestedPlatform}
                  </button>
                )}
              </div>
            )}

            {linkValidation?.valid && (
              <p
                id={`${id}-link-feedback`}
                className="mt-1.5 text-xs text-emerald-700 font-medium flex items-center gap-1.5"
              >
                <CheckCircle2 size={14} className="shrink-0" />
                <span>
                  {switchNotice ||
                    `Valid ${resolveMeetingPlatform(value.meetingLink, value.platform) || 'meeting'} link.`}
                </span>
              </p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
