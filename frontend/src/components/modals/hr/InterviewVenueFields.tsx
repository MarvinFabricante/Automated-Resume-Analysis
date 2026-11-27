import React, { useId } from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  detectMeetingPlatform,
  resolveMeetingPlatform,
  validMeetingLink,
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
    : value.interviewType === 'Online' && validMeetingLink(value.meetingLink);
}

export function getInterviewVenueError(value: InterviewVenue): string | null {
  if (!value.interviewType) {
    return 'Choose an interview type (Onsite or Online).';
  }
  if (value.interviewType === 'Onsite') {
    return value.location.trim() ? null : 'Enter the interview location.';
  }
  if (value.interviewType === 'Online') {
    return validMeetingLink(value.meetingLink)
      ? null
      : 'Enter a valid meeting URL starting with https://.';
  }
  return 'Choose an interview type (Onsite or Online).';
}

export function venuePayload(value: InterviewVenue) {
  const autoPlatform =
    value.interviewType === 'Online'
      ? resolveMeetingPlatform(value.meetingLink, value.platform)
      : null;

  return {
    interview_type: value.interviewType,
    location: value.interviewType === 'Onsite' ? value.location.trim() : null,
    meeting_link: value.interviewType === 'Online' ? value.meetingLink.trim() : null,
    instructions: value.instructions.trim() || null,
    platform: autoPlatform,
  };
}

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

  const field =
    'w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-900 bg-white focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] transition-all';
  const error = 'text-xs text-red-700 mt-1';

  const isOnline = value.interviewType === 'Online';
  const hasLinkText = Boolean(value.meetingLink && value.meetingLink.trim());
  const isValidLink = hasLinkText && validMeetingLink(value.meetingLink);
  const detectedPlatform = hasLinkText ? detectMeetingPlatform(value.meetingLink) : null;

  const handleLinkChange = (nextLink: string) => {
    const autoPlatform = detectMeetingPlatform(nextLink) || '';
    onChange({
      ...value,
      meetingLink: nextLink,
      platform: autoPlatform,
    });
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div className={isOnline ? 'sm:col-span-2' : ''}>
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

      {isOnline && (
        <div className="sm:col-span-2">
          <label htmlFor={`${id}-link`} className="block text-sm font-semibold mb-1">
            Meeting link *
          </label>
          <input
            id={`${id}-link`}
            type="url"
            className={`${field} ${
              hasLinkText && !isValidLink
                ? 'border-red-400 focus:border-red-500 focus:ring-red-200'
                : isValidLink
                  ? 'border-emerald-400 focus:border-emerald-500 focus:ring-emerald-200'
                  : ''
            }`}
            required
            value={value.meetingLink}
            placeholder="https://meet.google.com/... or https://zoom.us/j/..."
            aria-invalid={hasLinkText && !isValidLink}
            aria-describedby={`${id}-link-feedback`}
            onChange={(e) => handleLinkChange(e.target.value)}
          />

          {hasLinkText && !isValidLink && (
            <p
              id={`${id}-link-feedback`}
              role="alert"
              className="mt-1.5 text-xs text-red-700 font-medium flex items-center gap-1.5"
            >
              <AlertCircle size={14} className="shrink-0" />
              <span>Enter a valid meeting URL starting with https://.</span>
            </p>
          )}

          {isValidLink && (
            <p
              id={`${id}-link-feedback`}
              className="mt-1.5 text-xs text-emerald-700 font-medium flex items-center gap-1.5"
            >
              <CheckCircle2 size={14} className="shrink-0" />
              <span>
                {detectedPlatform && detectedPlatform !== 'Other'
                  ? `Valid ${detectedPlatform} link.`
                  : 'Valid meeting link.'}
              </span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
