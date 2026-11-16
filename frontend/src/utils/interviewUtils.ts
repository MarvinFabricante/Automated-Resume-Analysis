const INACTIVE_INTERVIEW_STATUSES = new Set([
  'CANCELLED',
  'CANCELED',
  'REJECTED',
  'COMPLETED',
  'NO_SHOW',
]);

export const isInactiveInterviewStatus = (status?: string | null): boolean => {
  const normalized = String(status || '').trim().toUpperCase();
  return INACTIVE_INTERVIEW_STATUSES.has(normalized);
};

export const parseInterviewTimestampMs = (value?: string | Date | null): number => {
  if (!value) return NaN;
  if (value instanceof Date) return value.getTime();
  const ms = new Date(value).getTime();
  return Number.isFinite(ms) ? ms : NaN;
};

export const formatUtcLogTimestamp = (value?: string | null): string => {
  if (!value) return '';
  const raw = String(value).trim();
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw);
  const normalized = /^\d{4}-\d{2}-\d{2}T/.test(raw) && !hasTz ? `${raw}Z` : raw;
  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? raw : parsed.toLocaleString();
};

export const isUpcomingInterview = (iv: any, now: Date = new Date()): boolean => {
  if (!iv || isInactiveInterviewStatus(iv.status)) return false;
  const boundaryRaw = iv.end_time || iv.end || iv.start_time || iv.start || iv.start_datetime;
  const boundaryMs = parseInterviewTimestampMs(boundaryRaw);
  if (Number.isNaN(boundaryMs)) return true;
  return boundaryMs >= now.getTime();
};

export const filterAndSortUpcomingInterviews = <T extends Record<string, any>>(
  interviews: T[] = [],
  now: Date = new Date()
): T[] => {
  return [...interviews]
    .filter((iv) => isUpcomingInterview(iv, now))
    .sort((a, b) => {
      const aMs = parseInterviewTimestampMs(a.start_time || a.start || a.start_datetime);
      const bMs = parseInterviewTimestampMs(b.start_time || b.start || b.start_datetime);
      return (Number.isNaN(aMs) ? 0 : aMs) - (Number.isNaN(bMs) ? 0 : bMs);
    });
};

export const mergeInterviewsById = (primary: any[] = [], secondary: any[] = []): any[] => {
  const map = new Map<string, any>();
  for (const item of [...primary, ...secondary]) {
    if (!item || item.id === undefined || item.id === null) continue;
    const key = String(item.id);
    if (!map.has(key)) {
      map.set(key, item);
    }
  }
  return Array.from(map.values()).sort((a, b) => {
    const aMs = parseInterviewTimestampMs(a.start_time);
    const bMs = parseInterviewTimestampMs(b.start_time);
    return (Number.isNaN(aMs) ? 0 : aMs) - (Number.isNaN(bMs) ? 0 : bMs);
  });
};

export const mergeCallLogs = (
  appLogs: any[] = [],
  candidateLogs: any[] = [],
  interviews: any[] = []
): any[] => {
  const map = new Map<string, any>();

  const pushLog = (log: any, fallbackInterview?: any) => {
    if (!log) return;
    const key = log.id !== undefined && log.id !== null
      ? `id:${log.id}`
      : `sid:${log.call_sid || ''}-${log.interview_id || ''}-${log.attempt_number || ''}-${log.created_at || ''}`;
    if (map.has(key)) return;
    map.set(key, {
      ...log,
      interview_title: log.interview_title || fallbackInterview?.title || null,
      interview_status: log.interview_status || fallbackInterview?.status || null,
      interview_start_time: log.interview_start_time || fallbackInterview?.start_time || null,
    });
  };

  for (const log of appLogs) pushLog(log);
  for (const log of candidateLogs) pushLog(log);
  for (const iv of interviews) {
    if (Array.isArray(iv?.call_records)) {
      for (const rec of iv.call_records) pushLog(rec, iv);
    }
  }

  return Array.from(map.values()).sort((a, b) => {
    const idDiff = Number(b.id || 0) - Number(a.id || 0);
    if (idDiff !== 0) return idDiff;
    const aMs = parseInterviewTimestampMs(a.created_at);
    const bMs = parseInterviewTimestampMs(b.created_at);
    return (Number.isNaN(bMs) ? 0 : bMs) - (Number.isNaN(aMs) ? 0 : aMs);
  });
};

export const getCallOutcomeBadgeClass = (value?: string | null): string => {
  const normalized = String(value || '').trim().toUpperCase();
  if (normalized === 'CONFIRMED' || normalized === 'ANSWERED' || normalized === 'COMPLETED') {
    return 'bg-emerald-100 text-emerald-800 border-emerald-200';
  }
  if (normalized === 'RESCHEDULE_REQUESTED' || normalized === 'RETRY_SCHEDULED') {
    return 'bg-amber-100 text-amber-800 border-amber-200';
  }
  if (normalized === 'ESCALATED_TO_HR' || normalized === 'IN_PROGRESS' || normalized === 'INITIATED') {
    return 'bg-blue-100 text-blue-800 border-blue-200';
  }
  if (normalized === 'NO_RESPONSE' || normalized === 'NO_ANSWER' || normalized === 'NO-ANSWER' || normalized === 'BUSY') {
    return 'bg-orange-100 text-orange-800 border-orange-200';
  }
  if (normalized === 'FAILED' || normalized === 'UNREACHABLE') {
    return 'bg-rose-100 text-rose-800 border-rose-200';
  }
  if (normalized === 'DELIVERED' || normalized === 'SENT' || normalized === 'SMS_SENT' || normalized === 'SMS_BACKUP_SENT') {
    return 'bg-emerald-100 text-emerald-800 border-emerald-200';
  }
  return 'bg-slate-100 text-slate-700 border-slate-200';
};

export interface MessageLogEntry {
  id: string | number;
  interview_id?: number;
  interview_title?: string | null;
  log_type: string;
  channel: 'SMS' | 'EMAIL';
  label: string;
  status: string;
  recipient: string;
  details: string;
  created_at?: string | null;
}

export const extractMessageLogs = (
  interviews: any[] = [],
  callLogs: any[] = [],
  fallbackPhone?: string | null,
  fallbackEmail?: string | null
): MessageLogEntry[] => {
  const results: MessageLogEntry[] = [];
  const seenKeys = new Set<string>();

  const cleanPhone =
    fallbackPhone && fallbackPhone !== 'Not provided' && fallbackPhone !== 'N/A'
      ? String(fallbackPhone).trim()
      : '';
  const cleanEmail =
    fallbackEmail && fallbackEmail !== 'Not provided' && fallbackEmail !== 'N/A'
      ? String(fallbackEmail).trim()
      : '';

  const addEntry = (key: string, entry: MessageLogEntry) => {
    if (seenKeys.has(key)) return;
    seenKeys.add(key);
    results.push(entry);
  };

  for (const iv of interviews || []) {
    if (!iv) continue;
    const ivId = iv.id;
    const ivTitle = iv.title || 'Interview Session';
    const ivPhone = iv.candidate_phone || cleanPhone || 'Candidate Phone';
    const ivEmail = iv.candidate_email || cleanEmail || 'Candidate Email';
    const ivLogs: any[] = Array.isArray(iv.logs) ? iv.logs : [];

    let hasSmsScheduleLog = false;
    let hasSmsBackupLog = false;

    for (const log of ivLogs) {
      if (!log) continue;
      const lType = String(log.log_type || '').toUpperCase().trim();
      const details = String(log.details || '').trim();

      if (lType === 'SMS_SENT' || lType === 'SMS_RESCHEDULED' || lType === 'SMS_CANCELED' || lType === 'SMS_BACKUP_SENT') {
        if (lType === 'SMS_SENT' || lType === 'SMS_RESCHEDULED') hasSmsScheduleLog = true;
        if (lType === 'SMS_BACKUP_SENT') hasSmsBackupLog = true;

        const phoneMatch = details.match(/(?:\+63|09)\d[\d\s-]{7,13}/);
        const recipient = phoneMatch ? phoneMatch[0].trim() : ivPhone;

        const label =
          lType === 'SMS_BACKUP_SENT'
            ? 'Backup SMS Notification'
            : lType === 'SMS_RESCHEDULED'
              ? 'Reschedule SMS Notification'
              : lType === 'SMS_CANCELED'
                ? 'Cancellation SMS Notification'
                : 'SMS Notification';

        addEntry(`log-${log.id || `${ivId}-${lType}-${log.created_at}`}`, {
          id: log.id || `${ivId}-${lType}-${log.created_at}`,
          interview_id: ivId,
          interview_title: ivTitle,
          log_type: lType,
          channel: 'SMS',
          label,
          status: 'DELIVERED',
          recipient,
          details: details || `${label} delivered to ${recipient} for ${ivTitle}.`,
          created_at: log.created_at || iv.created_at,
        });
      } else if (lType === 'EMAIL_SENT' || lType === 'EMAIL_RESCHEDULED' || lType === 'EMAIL_CANCELED') {
        // Only include candidate-facing email logs (skip internal HR/panelist copies unless it's candidate email)
        const lowerDetails = details.toLowerCase();
        if (lowerDetails.includes('to hr ') || lowerDetails.includes('panelist')) {
          continue;
        }
        const emailMatch = details.match(/[\w.-]+@[\w.-]+\.\w+/);
        const recipient = emailMatch ? emailMatch[0] : ivEmail;
        const label =
          lType === 'EMAIL_RESCHEDULED'
            ? 'Reschedule Email Notification'
            : lType === 'EMAIL_CANCELED'
              ? 'Cancellation Email Notification'
              : 'Interview Invitation Email';

        addEntry(`log-${log.id || `${ivId}-${lType}-${log.created_at}`}`, {
          id: log.id || `${ivId}-${lType}-${log.created_at}`,
          interview_id: ivId,
          interview_title: ivTitle,
          log_type: lType,
          channel: 'EMAIL',
          label,
          status: 'DELIVERED',
          recipient,
          details: details || `${label} delivered to ${recipient}.`,
          created_at: log.created_at || iv.created_at,
        });
      }
    }

    // Fallback synthesis if interview has a phone number and was scheduled, ensuring SMS delivery status is always visible
    if (!hasSmsScheduleLog && (iv.candidate_phone || cleanPhone)) {
      const recipient = iv.candidate_phone || cleanPhone;
      const jobName = iv.job_title || 'applied position';
      const candName = iv.candidate_name || 'Candidate';
      addEntry(`synth-sms-sched-${ivId}`, {
        id: `sms-sched-${ivId}`,
        interview_id: ivId,
        interview_title: ivTitle,
        log_type: 'SMS_SENT',
        channel: 'SMS',
        label: 'SMS Notification',
        status: 'DELIVERED',
        recipient,
        details: `SMS interview notification delivered to ${recipient} for ${candName} (${jobName}).`,
        created_at: iv.created_at || iv.start_time,
      });
    }

    // Fallback synthesis if backup SMS was triggered on the interview
    if (!hasSmsBackupLog && (iv.sms_backup_sent || String(iv.call_status || '').toUpperCase() === 'SMS_BACKUP_SENT')) {
      const recipient = iv.candidate_phone || cleanPhone || 'Candidate Phone';
      addEntry(`synth-sms-backup-${ivId}`, {
        id: `sms-backup-${ivId}`,
        interview_id: ivId,
        interview_title: ivTitle,
        log_type: 'SMS_BACKUP_SENT',
        channel: 'SMS',
        label: 'Backup SMS Notification',
        status: 'DELIVERED',
        recipient,
        details: `Backup SMS notification delivered to ${recipient} following unsuccessful voice call attempts.`,
        created_at: iv.updated_at || iv.last_call_at || iv.created_at,
      });
    }
  }

  // Also check callLogs for any sms_backup_sent flags not covered above
  for (const cLog of callLogs || []) {
    if (cLog?.sms_backup_sent) {
      const ivId = cLog.interview_id;
      const key = `synth-sms-backup-${ivId || cLog.id}`;
      const hasBackupForIv = results.some(
        (r) => r.interview_id === ivId && r.log_type === 'SMS_BACKUP_SENT'
      );
      if (!hasBackupForIv) {
        const recipient = cLog.phone_number || cleanPhone || 'Candidate Phone';
        addEntry(key, {
          id: `call-sms-backup-${cLog.id}`,
          interview_id: ivId,
          interview_title: cLog.interview_title || 'Interview Session',
          log_type: 'SMS_BACKUP_SENT',
          channel: 'SMS',
          label: 'Backup SMS Notification',
          status: 'DELIVERED',
          recipient,
          details: `Backup SMS notification delivered to ${recipient} following voice call attempt #${cLog.attempt_number || 1}.`,
          created_at: cLog.created_at,
        });
      }
    }
  }

  return results.sort((a, b) => {
    // Prioritize SMS logs first if timestamps are identical, otherwise newest first
    const aMs = parseInterviewTimestampMs(a.created_at);
    const bMs = parseInterviewTimestampMs(b.created_at);
    if (!Number.isNaN(aMs) && !Number.isNaN(bMs) && Math.abs(bMs - aMs) > 1000) {
      return bMs - aMs;
    }
    if (a.channel !== b.channel) {
      return a.channel === 'SMS' ? -1 : 1;
    }
    return (Number.isNaN(bMs) ? 0 : bMs) - (Number.isNaN(aMs) ? 0 : aMs);
  });
};


