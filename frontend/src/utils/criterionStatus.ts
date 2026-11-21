export type CriterionStatus =
  | 'Meets requirement'
  | 'Exceeds requirement'
  | 'Partially meets'
  | 'Not required'
  | 'Needs manual review'
  | 'Does not meet';

export const VALID_CRITERION_STATUSES: CriterionStatus[] = [
  'Meets requirement',
  'Exceeds requirement',
  'Partially meets',
  'Not required',
  'Needs manual review',
  'Does not meet',
];

export const NO_VALUE_MARKERS = new Set<string>([
  '',
  'none',
  'none required',
  'none specified',
  'none provided',
  'none yet',
  'n/a',
  'na',
  'n.a',
  'not applicable',
  'not required',
  'not specified',
  'not provided',
  'no requirement',
  'no requirements',
  'no specific requirement',
  'no specific requirements',
  'no education required',
  'no education provided',
  'no experience required',
  'no experience provided',
  'no work experience required',
  'no skills required',
  'no certification',
  'no certifications',
  'no certification found',
  'no certification required',
  'no certifications required',
  'no specific certification',
  'no specific certifications',
  'no specific certification required',
  'no specific certifications required',
  'no experience',
  'no work experience',
  'no prior experience',
  'no relevant experience',
  'no',
  'wala',
  'walang requirement',
  'nil',
  'null',
  'unspecified',
  'unknown',
  'any',
  'optional',
  '-',
  '--',
  '---',
]);

/**
 * Returns true only when the WHOLE normalized value is a no-value marker.
 * Real requirements containing 'none' inside other text (e.g. 'None of the above, but must know Excel')
 * return false.
 */
export function isNoValueRequirement(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  const collapsed = String(value).replace(/\s+/g, ' ').trim();
  if (!collapsed) return true;
  if (/^[-–—_./,\s]+$/.test(collapsed)) return true;

  const key = collapsed
    .replace(/\s*\/\s*/g, '/')
    .toLowerCase()
    .replace(/[.\s,;:!?]+$/, '')
    .trim();

  return NO_VALUE_MARKERS.has(key);
}

/**
 * Normalizes user input before saving/submitting: returns "" when no requirement / no value,
 * otherwise preserves the trimmed single-spaced requirement string.
 */
export function cleanRequirementInput(value?: string | null): string {
  if (value === null || value === undefined) return '';
  if (isNoValueRequirement(value)) return '';
  return String(value).replace(/\s+/g, ' ').trim();
}

export function cleanRequirementList(items?: unknown[] | string | null): string[] {
  if (!items) return [];
  const rawList = Array.isArray(items)
    ? items.flatMap((it) => String(it ?? '').split(/[|,\n;•]/))
    : String(items).split(/[|,\n;•]/);
  const cleaned: string[] = [];
  const seen = new Set<string>();
  for (const raw of rawList) {
    const item = cleanRequirementInput(raw);
    if (!item) continue;
    const key = item.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      cleaned.push(item);
    }
  }
  return cleaned;
}

export function extractCriterionStatus(reason?: string | null): CriterionStatus | null {
  if (!reason) return null;
  const trimmed = String(reason).trim();
  const low = trimmed.toLowerCase();
  for (const status of VALID_CRITERION_STATUSES) {
    const sLow = status.toLowerCase();
    if (low === sLow || low.startsWith(`${sLow}:`)) {
      return status;
    }
  }
  return null;
}

export function resolveCriterionStatus(params: {
  explicitStatus?: string | null;
  reason?: string | null;
  score?: number | null;
  isBelowMinimum?: boolean;
}): CriterionStatus {
  const { explicitStatus, reason, score, isBelowMinimum } = params;
  if (explicitStatus) {
    const matchedExplicit = VALID_CRITERION_STATUSES.find(
      (s) => s.toLowerCase() === String(explicitStatus).trim().toLowerCase()
    );
    if (matchedExplicit) return matchedExplicit;
  }

  const extracted = extractCriterionStatus(reason);
  if (extracted) return extracted;

  const rLow = String(reason || '').toLowerCase();
  if (rLow.includes('no requirement') || rLow.includes('not required') || rLow.includes('no certification requirement') || rLow.includes('no education requirement') || rLow.includes('no experience requirement') || rLow.includes('no specific skills requirement')) {
    return 'Not required';
  }
  if (rLow.includes('manual review')) {
    return 'Needs manual review';
  }
  if (rLow.includes('exceeds') || rLow.includes('exceeding')) {
    return 'Exceeds requirement';
  }

  const numScore = Number(score ?? 0);
  if (isBelowMinimum) {
    return numScore >= 40 ? 'Partially meets' : 'Does not meet';
  }
  if (numScore >= 95) return 'Meets requirement';
  if (numScore >= 75) return 'Meets requirement';
  if (numScore >= 40) return 'Partially meets';
  return 'Does not meet';
}

export function stripStatusPrefix(reason?: string | null): string {
  if (!reason) return '';
  const trimmed = String(reason).trim();
  for (const status of VALID_CRITERION_STATUSES) {
    const prefix = `${status}:`;
    if (trimmed.toLowerCase().startsWith(prefix.toLowerCase())) {
      return trimmed.slice(prefix.length).trim();
    }
  }
  return trimmed;
}

export function getCriterionStatusBadgeStyle(status: CriterionStatus): {
  badgeClass: string;
  textClass: string;
  barClass: string;
  isFailure: boolean;
} {
  switch (status) {
    case 'Exceeds requirement':
      return {
        badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
        textClass: 'text-emerald-700',
        barClass: 'bg-emerald-500',
        isFailure: false,
      };
    case 'Meets requirement':
      return {
        badgeClass: 'bg-green-50 text-green-700 border-green-200',
        textClass: 'text-green-700',
        barClass: 'bg-green-500',
        isFailure: false,
      };
    case 'Partially meets':
      return {
        badgeClass: 'bg-amber-50 text-amber-700 border-amber-200',
        textClass: 'text-amber-700',
        barClass: 'bg-amber-500',
        isFailure: false,
      };
    case 'Not required':
      return {
        badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
        textClass: 'text-slate-600',
        barClass: 'bg-slate-400',
        isFailure: false,
      };
    case 'Needs manual review':
      return {
        badgeClass: 'bg-indigo-50 text-indigo-700 border-indigo-200',
        textClass: 'text-indigo-700',
        barClass: 'bg-indigo-500',
        isFailure: false,
      };
    case 'Does not meet':
    default:
      return {
        badgeClass: 'bg-rose-50 text-rose-700 border-rose-200',
        textClass: 'text-rose-700',
        barClass: 'bg-rose-500',
        isFailure: true,
      };
  }
}
