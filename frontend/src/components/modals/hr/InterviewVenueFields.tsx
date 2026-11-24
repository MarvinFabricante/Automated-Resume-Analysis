import React, { useId } from 'react';

export interface InterviewVenue {
  interviewType: string;
  location: string;
  meetingLink: string;
  instructions: string;
  platform: string;
}
export const emptyInterviewVenue: InterviewVenue = { interviewType: '', location: '', meetingLink: '', instructions: '', platform: '' };
export function validMeetingLink(value: string): boolean {
  try {
    const url = new URL(value.trim());
    return value.trim().startsWith('https://') && !!url.hostname && !url.username && !/\s/.test(value.trim());
  } catch { return false; }
}
export function validInterviewVenue(value: InterviewVenue): boolean {
  return value.interviewType === 'Onsite' ? !!value.location.trim()
    : value.interviewType === 'Online' && validMeetingLink(value.meetingLink);
}
export function venuePayload(value: InterviewVenue) {
  return {
    interview_type: value.interviewType,
    location: value.interviewType === 'Onsite' ? value.location.trim() : null,
    meeting_link: value.interviewType === 'Online' ? value.meetingLink.trim() : null,
    instructions: value.instructions.trim() || null,
    platform: value.interviewType === 'Online' ? value.platform || null : null,
  };
}
export default function InterviewVenueFields({ value, onChange, companyAddress = '' }: {
  value: InterviewVenue; onChange: (value: InterviewVenue) => void; companyAddress?: string;
}) {
  const id = useId();
  const field = 'w-full px-4 py-2.5 border border-gray-300 rounded-xl text-sm text-gray-900 bg-white';
  const error = 'text-xs text-red-700 mt-1';
  return <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
    <div>
      <label htmlFor={`${id}-type`} className="block text-sm font-semibold mb-1">Interview type *</label>
      <select id={`${id}-type`} className={field} required value={value.interviewType}
        aria-describedby={`${id}-type-error`} aria-invalid={!value.interviewType}
        onChange={e => onChange({ ...value, interviewType: e.target.value, location: value.location || companyAddress })}>
        <option value="">Choose interview type</option><option>Onsite</option><option>Online</option>
      </select>
      {!value.interviewType && <p id={`${id}-type-error`} className={error}>Choose Onsite or Online.</p>}
    </div>
    {value.interviewType === 'Onsite' && <>
      <div>
        <label htmlFor={`${id}-location`} className="block text-sm font-semibold mb-1">Location *</label>
        <input id={`${id}-location`} className={field} required value={value.location}
          aria-invalid={!value.location.trim()} aria-describedby={`${id}-location-error`}
          onChange={e => onChange({ ...value, location: e.target.value })} />
        {!value.location.trim() && <p id={`${id}-location-error`} className={error}>Enter the interview location.</p>}
      </div>
      <div className="sm:col-span-2">
        <label htmlFor={`${id}-instructions`} className="block text-sm font-semibold mb-1">Extra instructions (optional)</label>
        <textarea id={`${id}-instructions`} className={field} value={value.instructions}
          placeholder="Which gate, who to look for, or what to bring"
          onChange={e => onChange({ ...value, instructions: e.target.value })} />
      </div>
    </>}
    {value.interviewType === 'Online' && <>
      <div>
        <label htmlFor={`${id}-link`} className="block text-sm font-semibold mb-1">Meeting link *</label>
        <input id={`${id}-link`} type="url" className={field} required value={value.meetingLink}
          placeholder="https://meet.google.com/..." aria-invalid={!validMeetingLink(value.meetingLink)}
          aria-describedby={`${id}-link-error`} onChange={e => onChange({ ...value, meetingLink: e.target.value })} />
        {!validMeetingLink(value.meetingLink) && <p id={`${id}-link-error`} className={error}>Enter a valid meeting URL starting with https://.</p>}
      </div>
      <div>
        <label htmlFor={`${id}-platform`} className="block text-sm font-semibold mb-1">Platform (optional)</label>
        <select id={`${id}-platform`} className={field} value={value.platform} onChange={e => onChange({ ...value, platform: e.target.value })}>
          <option value="">Choose platform</option>
          {['Google Meet', 'Zoom', 'Microsoft Teams', 'Other'].map(platform => <option key={platform}>{platform}</option>)}
        </select>
      </div>
    </>}
  </div>;
}
