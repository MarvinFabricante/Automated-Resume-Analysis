export interface NotificationTemplateItem {
  key: string;
  label: string;
  description: string;
  supports_sms: boolean;
  placeholders: string[];
  email_subject: string;
  email_message: string;
  sms_message: string;
}

export const INTERVIEW_PLACEHOLDERS = [
  'candidate_name',
  'candidate_email',
  'job_title',
  'interview_title',
  'date',
  'start_time',
  'end_time',
  'time_range',
  'interviewer_name',
  'interviewer_email',
  'location',
  'meeting_link',
  'location_line',
  'notes',
  'notes_line',
  'reason',
  'reason_line',
  'email_note',
  'company_name',
];

export const DEFAULT_NOTIFICATION_TEMPLATES: Record<string, NotificationTemplateItem> = {
  interview_scheduled: {
    key: 'interview_scheduled',
    label: 'Interview Scheduled',
    description: 'Sent to candidates via Email & SMS when HR schedules an interview.',
    supports_sms: true,
    placeholders: INTERVIEW_PLACEHOLDERS,
    email_subject: 'Interview Scheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'We are pleased to inform you that an interview has been scheduled for your application for the position of {job_title} at {company_name}. Please review the complete schedule information below and be ready at least 10 minutes before your scheduled time.',
    sms_message:
      'Mariwasa HR: Hello {candidate_name}! Your {interview_title} for {job_title} is scheduled on {date} at {time_range} with {interviewer_name}.{location_line}{notes_line}{email_note} Please be ready 10 mins early. Thank you!',
  },
  interview_rescheduled: {
    key: 'interview_rescheduled',
    label: 'Interview Rescheduled',
    description: 'Sent via Email & SMS when HR moves an interview to a new date or time.',
    supports_sms: true,
    placeholders: INTERVIEW_PLACEHOLDERS,
    email_subject: 'Rescheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'Please be advised that your interview schedule for the position of {job_title} has been updated. Below are your new interview details and venue/meeting information.',
    sms_message:
      'Mariwasa HR Update: Hello {candidate_name}! Your {interview_title} for {job_title} has been rescheduled to {date} at {time_range} with {interviewer_name}.{location_line}{notes_line}{email_note} Thank you!',
  },
  interview_canceled: {
    key: 'interview_canceled',
    label: 'Interview Canceled',
    description: 'Sent via Email & SMS when HR cancels a scheduled interview session.',
    supports_sms: true,
    placeholders: INTERVIEW_PLACEHOLDERS,
    email_subject: 'Canceled: {interview_title} - {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'Please be advised that the scheduled interview for the position of {job_title} on {date} at {time_range} has been canceled. The calendar event has been removed from all participant schedules.',
    sms_message:
      'Mariwasa HR Update: Hello {candidate_name}, your {interview_title} for {job_title} scheduled on {date} at {time_range} has been canceled.{reason_line}{email_note} Thank you.',
  },
  candidate_rescheduled: {
    key: 'candidate_rescheduled',
    label: 'Candidate Self-Reschedule Confirmation',
    description: 'Sent via Email & SMS after a candidate confirms a rescheduled slot.',
    supports_sms: true,
    placeholders: INTERVIEW_PLACEHOLDERS,
    email_subject: 'Rescheduled: {interview_title} - {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'Your interview reschedule for the position of {job_title} has been confirmed for {date} at {time_range}. Please review your updated schedule details below.',
    sms_message:
      'Mariwasa HR Update: Hello {candidate_name}! Your new {interview_title} schedule for {job_title} on {date} at {time_range} with {interviewer_name} is confirmed.{location_line}{email_note} Thank you!',
  },
  application_status_reviewed: {
    key: 'application_status_reviewed',
    label: 'Application Status: Under Review',
    description: 'Email sent when an application moves to Reviewed / Under Review.',
    supports_sms: false,
    placeholders: ['candidate_name', 'job_title', 'status', 'notes', 'company_name'],
    email_subject: 'Application Status Update: {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'Thank you for applying for the position of {job_title} at {company_name}. We are pleased to inform you that our Talent Acquisition team has officially reviewed your resume and credentials.',
    sms_message: '',
  },
  application_status_shortlisted: {
    key: 'application_status_shortlisted',
    label: 'Application Status: Shortlisted / Accepted',
    description: 'Email sent when an application is shortlisted or accepted.',
    supports_sms: false,
    placeholders: ['candidate_name', 'job_title', 'status', 'notes', 'company_name'],
    email_subject: 'Congratulations: Application Shortlisted for {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'We are thrilled to inform you that following a comprehensive evaluation of your background and credentials, your application for the position of {job_title} at {company_name} has been officially accepted and shortlisted!',
    sms_message: '',
  },
  application_status_rejected: {
    key: 'application_status_rejected',
    label: 'Application Status: Not Selected / Rejected',
    description: 'Email sent when an application is marked as Not Selected / Rejected.',
    supports_sms: false,
    placeholders: ['candidate_name', 'job_title', 'status', 'notes', 'company_name'],
    email_subject: 'Application Update: {job_title} | Mariwasa Siam Ceramics',
    email_message:
      'Thank you for your interest in joining {company_name} and for the time, energy, and dedication you invested in applying for the position of {job_title}.',
    sms_message: '',
  },
};

export const isRealCandidateEmail = (email?: string | null): boolean => {
  const clean = (email || '').trim();
  return Boolean(clean && clean.includes('@') && !clean.toLowerCase().endsWith('.local'));
};

export const renderNotificationTemplate = (
  templateText: string,
  context: Record<string, string | undefined | null>
): string => {
  if (!templateText) return '';
  const rendered = templateText.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key) => {
    if (Object.prototype.hasOwnProperty.call(context, key)) {
      return context[key] ?? '';
    }
    return match;
  });
  return rendered
    .replace(/[ \t]{2,}/g, ' ')
    .replace(/\s+([.,!?])/g, '$1')
    .trim();
};

export const buildInterviewTemplateContext = (params: {
  candidateName?: string;
  candidateEmail?: string;
  jobTitle?: string;
  interviewTitle?: string;
  startTime?: string | Date;
  endTime?: string | Date;
  interviewerName?: string;
  interviewerEmail?: string;
  location?: string;
  meetingLink?: string;
  notes?: string;
  reason?: string;
}): Record<string, string> => {
  const startDt = params.startTime ? new Date(params.startTime) : null;
  const endDt = params.endTime ? new Date(params.endTime) : null;
  const validStart = startDt && !Number.isNaN(startDt.getTime()) ? startDt : null;
  const validEnd = endDt && !Number.isNaN(endDt.getTime()) ? endDt : null;

  const dateStr = validStart
    ? validStart.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'short',
        day: '2-digit',
        year: 'numeric',
      })
    : 'TBD Date';
  const startStr = validStart
    ? validStart.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
    : 'TBD';
  const endStr = validEnd
    ? validEnd.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
    : '';
  const timeRange = endStr ? `${startStr} - ${endStr}` : startStr;

  const cleanLoc = (params.location || '').trim();
  const cleanLink = (params.meetingLink || '').trim();
  const cleanNotes = (params.notes || '').trim();
  const cleanReason = (params.reason || '').trim();
  const cleanEmail = isRealCandidateEmail(params.candidateEmail) ? (params.candidateEmail || '').trim() : '';

  let locationLine = '';
  if (cleanLoc && cleanLink) {
    locationLine = ` Venue: ${cleanLoc} | Meeting Link: ${cleanLink}.`;
  } else if (cleanLink) {
    locationLine = ` Meeting Link: ${cleanLink}.`;
  } else if (cleanLoc) {
    locationLine = ` Venue: ${cleanLoc}.`;
  }

  const trimmedNotes = cleanNotes.length <= 140 ? cleanNotes : `${cleanNotes.slice(0, 137)}...`;
  const notesLine = cleanNotes ? ` Notes: ${trimmedNotes}.` : '';
  const trimmedReason = cleanReason.length <= 140 ? cleanReason : `${cleanReason.slice(0, 137)}...`;
  const reasonLine = cleanReason ? ` Reason: ${trimmedReason}.` : '';
  const emailNote = cleanEmail ? ` Full details sent to ${cleanEmail}.` : '';

  return {
    candidate_name: (params.candidateName || 'Candidate').trim(),
    candidate_email: cleanEmail,
    job_title: (params.jobTitle || 'Position').trim(),
    interview_title: (params.interviewTitle || 'Interview').trim(),
    date: dateStr,
    start_time: startStr,
    end_time: endStr,
    time_range: timeRange,
    interviewer_name: (params.interviewerName || 'Mariwasa HR Panel').trim(),
    interviewer_email: (params.interviewerEmail || '').trim(),
    location: cleanLoc || 'To be confirmed by HR',
    meeting_link: cleanLink,
    location_line: locationLine,
    notes: cleanNotes,
    notes_line: notesLine,
    reason: cleanReason,
    reason_line: reasonLine,
    email_note: emailNote,
    company_name: 'Mariwasa Siam Ceramics, Inc.',
  };
};
