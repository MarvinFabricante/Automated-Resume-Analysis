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
  return 'bg-slate-100 text-slate-700 border-slate-200';
};

