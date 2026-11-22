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

// ─── Canonical 1-8 Education Hierarchy (mirrors backend requirement_rules.py) ───

export const EDUCATION_LEVELS: Record<number, string> = {
  1: 'Elementary',
  2: 'High School (Junior High School)',
  3: 'Senior High School',
  4: 'Vocational / TESDA / Technical-Vocational',
  5: 'Associate / Short course (2-year)',
  6: "Bachelor's degree",
  7: "Post-graduate certificate / Master's",
  8: 'Doctorate',
};

export const EDUCATION_SHORT_LABELS: Record<number, string> = {
  1: 'Elementary',
  2: 'High School',
  3: 'Senior High School',
  4: 'Vocational / TESDA',
  5: 'Associate degree',
  6: "Bachelor's degree",
  7: "Master's degree",
  8: 'Doctorate',
};

const ONGOING_COMPLETED_LEVEL_MAP: Record<number, number> = {
  8: 7,
  7: 6,
  6: 3,
  5: 3,
  4: 3,
  3: 2,
  2: 1,
  1: 0,
};

const CLIENT_DOT_ABBR: Array<[RegExp, string]> = [
  [/\bph\.?\s*d\.?(?![a-z0-9])/gi, 'phd'],
  [/\bed\.?\s*d\.?(?![a-z0-9])/gi, 'edd'],
  [/\bd\.?\s*b\.?\s*a\.?(?![a-z0-9])/gi, 'dba'],
  [/\bm\.?\s*b\.?\s*a\.?(?![a-z0-9])/gi, 'mba'],
  [/\bm\.?\s*p\.?\s*a\.?(?![a-z0-9])/gi, 'mpa'],
  [/\bm\.?\s*i\.?\s*t\.?(?![a-z0-9])/gi, 'mit'],
  [/\bm\.?\s*s\.?\s*i\.?\s*t\.?(?![a-z0-9])/gi, 'msit'],
  [/\bm\.?\s*s\.?\s*c\.?\s*s\.?(?![a-z0-9])/gi, 'mscs'],
  [/\bm\.?\s*sc\.?(?![a-z0-9])/gi, 'msc'],
  [/\bm\.?\s*s\.?(?![a-z0-9])/gi, 'ms'],
  [/\bm\.?\s*a\.?(?![a-z0-9])/gi, 'ma'],
  [/\bm\.?\s*d\.?(?![a-z0-9])/gi, 'md'],
  [/\bj\.?\s*d\.?(?![a-z0-9])/gi, 'jd'],
  [/\bll\.?\s*b\.?(?![a-z0-9])/gi, 'llb'],
  [/\bb\.?\s*s\.?\s*b\.?\s*a\.?(?![a-z0-9])/gi, 'bsba'],
  [/\bb\.?\s*s\.?\s*i\.?\s*t\.?(?![a-z0-9])/gi, 'bsit'],
  [/\bb\.?\s*s\.?\s*c\.?\s*s\.?(?![a-z0-9])/gi, 'bscs'],
  [/\bb\.?\s*s\.?\s*a\.?(?![a-z0-9])/gi, 'bsa'],
  [/\bb\.?\s*s\.?(?![a-z0-9])/gi, 'bs'],
  [/\bb\.?\s*a\.?(?![a-z0-9])/gi, 'ba'],
  [/\ba\.?\s*b\.?(?![a-z0-9])/gi, 'ab'],
];

const CLIENT_MS_SOFTWARE_RE = /\bms\s+(?:office|word|excel|powerpoint|outlook|access|project|teams|visio|publisher|sql|windows|dos)\b/gi;
const CLIENT_ONGOING_RE = /\b(?:currently\s+(?:enrolled|studying|taking|pursuing)|ongoing|in\s+progress|continuing|undergraduate|undergrad|(?:1st|2nd|3rd|4th|5th|first|second|third|fourth|fifth)\s+year(?:\s+(?:college|university|shs|senior\s+high|high\s+school|vocational|associate|student|level|irregular))?|college\s+level|units\s+earned|(?:19|20)\d{2}\s*[-–—to]+\s*(?:present|current))\b/i;

function normalizeEduTextClient(text: string): string {
  let s = String(text || '').replace(/[’‘]/g, "'");
  s = s.replace(CLIENT_MS_SOFTWARE_RE, ' ');
  for (const [pat, repl] of CLIENT_DOT_ABBR) {
    s = s.replace(pat, repl);
  }
  s = s.replace(/\bk\s*[-–—]?\s*(?:to\s+)?12\b/gi, 'k12');
  s = s.replace(/\bpost[-\s]+grad(?:uate)?\b/gi, 'postgraduate');
  s = s.replace(/\btech(?:nical)?[-\s]+voc(?:ational)?\b/gi, 'technical vocational');
  s = s.replace(/\b([a-z]+)'s\b/gi, '$1');
  s = s.replace(/[,.;:()\[\]/|]+/g, ' ');
  return s.replace(/\s+/g, ' ').trim();
}

function detectRawLevelClient(norm: string, raw = ''): number | null {
  if (!norm) return null;
  if (/\b(?:phd|doctorate|doctoral|post[-\s]?doc(?:toral)?|doctor\s+of\s+[a-z]+|edd|dba|dmd)\b/i.test(norm)) return 8;
  if (/\b(?:post[-\s]?grad(?:uate)?(?:\s+(?:certificate|diploma|degree|studies))?|graduate\s+(?:certificate|diploma|degree|studies)|master(?:'?s|al)?(?:\s+(?:degree|of|in))?|mba|mpa|msit|mscs|maed|meng|mfa|llm|juris\s+doctor|jd)\b/i.test(norm)) return 7;
  if (/\b(?:bachelor(?:'?s)?(?:\s+(?:degree|of|in))?|baccalaureate|college\s+(?:graduate|degree|diploma)|university\s+(?:graduate|degree)|(?:4|four)[-\s]?year\s+(?:college|degree|course)|undergraduate\s+degree|bsba|bsit|bscs|bsis|bsa|bsma|bsat|bsce|bsme|bsee|bsece|bsie|bsche|bscpe|bsmse|bsn|bsmls|bshm|bshrm|bstm|bsca|bscrim|bsed|beed|bspsych|bsarch|bsarchi|bsbio|bschem|bsmath|bsstat|llb|bs|ba|ab|bsc)\b/i.test(norm)) return 6;
  if (/\b(?:associate(?:'?s)?(?:\s+(?:degree|of|in))?|(?:2|two)[-\s]?year\s+(?:degree|course|college(?:\s+level)?|diploma|program)|short\s+course)\b/i.test(norm)) return 5;
  if (/\b(?:senior\s+high(?:\s+school)?(?:\s+(?:graduate|diploma|completer))?|shs(?:\s+(?:graduate|diploma))?|k[-\s]?(?:to[-\s]?)?12|grade\s*(?:11|12)|gr\.?\s*(?:11|12)|(?:stem|abm|humss)\s*(?:strand|track)?|(?:general\s+academic|tvl)\s+(?:strand|track))\b/i.test(norm)) return 3;
  if (/\b(?:junior\s+high(?:\s+school)?(?:\s+(?:graduate|completer|diploma))?|jhs|high\s+school(?:\s+(?:graduate|diploma|completer))?|hs\s+(?:graduate|diploma)|secondary(?:\s+(?:education|school|graduate|diploma))?|als\s+completer|alternative\s+learning\s+system|grade\s*(?:7|8|9|10)|gr\.?\s*(?:7|8|9|10))\b/i.test(norm)) return 2;
  if (/\b(?:tesda|tech[-\s]?voc|technical[-\s]?vocational|vocational|tvet|nc\s*(?:i|ii|iii|iv|1|2|3|4)|nc(?:i|ii|iii|iv)|national\s+certificate(?:\s+(?:i|ii|iii|iv|1|2|3|4))?|trade\s+(?:course|school|certificate)|diploma)\b/i.test(norm)) return 4;
  if (/\b(?:elementary(?:\s+(?:school|education|graduate))?|primary\s+(?:school|education|graduate)|grade\s+school|grade\s*[1-6]|gr\.?\s*[1-6])\b/i.test(norm)) return 1;
  if (/\bACT\b/.test(raw || norm)) return 5;
  if (/\b(?:GAS|TVL)\b/.test(raw || norm)) return 3;
  if (/\bdoctor\b/i.test(norm)) return 8;
  if (/\b(?:ms|ma|msc|md)\b/i.test(norm)) return 7;
  if (/\bcollege\b/i.test(norm)) return 6;
  return null;
}

function parseSingleEduSegmentClient(
  text: string,
  isJobReq = false,
  explicitStatus?: string | null
): { level: number | null; pursuingLevel: number | null; isOngoing: boolean; recognized: boolean } {
  const cleaned = cleanRequirementInput(text);
  if (!cleaned) return { level: null, pursuingLevel: null, isOngoing: false, recognized: false };

  if (isJobReq && /\s+or\s+|\//i.test(cleaned)) {
    const parts = cleaned.split(/\s+or\s+|\//i).map((p) => p.trim()).filter(Boolean);
    const subLvls = parts
      .map((p) => detectRawLevelClient(normalizeEduTextClient(p), p))
      .filter((l): l is number => l !== null);
    if (subLvls.length >= 2) {
      const minLvl = Math.min(...subLvls);
      return { level: minLvl, pursuingLevel: minLvl, isOngoing: false, recognized: true };
    }
  }

  const rawLvl = detectRawLevelClient(normalizeEduTextClient(cleaned), cleaned);
  let isOngoing = false;
  if (explicitStatus) {
    const stLow = explicitStatus.trim().toLowerCase();
    if (['ongoing', 'undergrad', 'college level', 'enrolled', 'in progress'].some((k) => stLow.includes(k))) {
      isOngoing = true;
    }
  } else if (!isJobReq) {
    isOngoing = CLIENT_ONGOING_RE.test(cleaned);
  } else if (!/\bundergraduate\s+degree\b/i.test(cleaned) && CLIENT_ONGOING_RE.test(cleaned)) {
    isOngoing = true;
  }

  if (isOngoing) {
    const pursuing = rawLvl || 6;
    const completed = ONGOING_COMPLETED_LEVEL_MAP[pursuing] ?? 3;
    return { level: completed, pursuingLevel: pursuing, isOngoing: true, recognized: true };
  }
  if (rawLvl === null) {
    return { level: null, pursuingLevel: null, isOngoing: false, recognized: false };
  }
  return { level: rawLvl, pursuingLevel: rawLvl, isOngoing: false, recognized: true };
}

export function parseEducationLevelClient(
  text?: string | null,
  isJobReq = false,
  entries?: any[]
): {
  level: number | null;
  label: string | null;
  pursuingLevel: number | null;
  isOngoing: boolean;
  recognized: boolean;
  isNoValue: boolean;
} {
  const segs: Array<{ text: string; status?: string | null }> = [];
  if (!isJobReq && Array.isArray(entries) && entries.length > 0) {
    for (const e of entries) {
      if (!e || typeof e !== 'object') continue;
      const combined = [e.degree_or_course, e.raw_degree_or_course, e.education_level, e.major_or_specialization]
        .filter((p) => !isNoValueRequirement(p))
        .map((p) => String(p).trim())
        .join(' ');
      if (combined) segs.push({ text: combined, status: e.status });
    }
  }
  const normRaw = cleanRequirementInput(text);
  if (segs.length === 0 && normRaw) {
    if (isJobReq) {
      segs.push({ text: normRaw });
    } else {
      for (const part of normRaw.split(/[|\n;]+/)) {
        const cleanPart = cleanRequirementInput(part);
        if (cleanPart) segs.push({ text: cleanPart });
      }
    }
  }
  if (segs.length === 0) {
    return { level: null, label: null, pursuingLevel: null, isOngoing: false, recognized: false, isNoValue: true };
  }
  const recognized = segs
    .map((s) => parseSingleEduSegmentClient(s.text, isJobReq, s.status))
    .filter((p) => p.recognized && p.level !== null);
  if (recognized.length === 0) {
    return { level: null, label: null, pursuingLevel: null, isOngoing: false, recognized: false, isNoValue: false };
  }
  recognized.sort((a, b) => (b.level || 0) - (a.level || 0) || (a.isOngoing === b.isOngoing ? 0 : a.isOngoing ? 1 : -1));
  const best = recognized[0];
  return {
    level: best.level,
    label: best.level ? EDUCATION_SHORT_LABELS[best.level] : null,
    pursuingLevel: best.pursuingLevel,
    isOngoing: best.isOngoing,
    recognized: true,
    isNoValue: false,
  };
}

export function evaluateEducationClient(
  candText?: string | null,
  jobEduReq?: string | null,
  entries?: any[]
): {
  score: number;
  status: CriterionStatus;
  requiredEducation: string;
  candidateEducation: string;
  reason: string;
} {
  const candParsed = parseEducationLevelClient(candText, false, entries);
  if (isNoValueRequirement(jobEduReq)) {
    return {
      score: 100,
      status: 'Not required',
      requiredEducation: 'Not required',
      candidateEducation: candParsed.label || 'None provided',
      reason: 'Not required: No education requirement for this position.',
    };
  }
  const reqParsed = parseEducationLevelClient(jobEduReq, true);
  if (!reqParsed.recognized || reqParsed.level === null) {
    return {
      score: 50,
      status: 'Needs manual review',
      requiredEducation: String(jobEduReq || '').trim(),
      candidateEducation: candParsed.label || cleanRequirementInput(candText) || 'None provided',
      reason: `Needs manual review: Job education requirement ('${jobEduReq}') could not be automatically parsed.`,
    };
  }
  const reqLabel = EDUCATION_SHORT_LABELS[reqParsed.level] || String(jobEduReq);
  if (candParsed.isNoValue) {
    return {
      score: 0,
      status: 'Does not meet',
      requiredEducation: reqLabel,
      candidateEducation: 'None provided',
      reason: `Does not meet: Requires ${reqLabel}; no education details provided.`,
    };
  }
  if (!candParsed.recognized || candParsed.level === null) {
    const rawDisp = cleanRequirementInput(candText) || 'Unrecognized';
    return {
      score: 50,
      status: 'Needs manual review',
      requiredEducation: reqLabel,
      candidateEducation: rawDisp,
      reason: `Needs manual review: Candidate education ('${rawDisp}') could not be automatically verified against required ${reqLabel}.`,
    };
  }
  const candLabel = EDUCATION_SHORT_LABELS[candParsed.level] || '';
  if (candParsed.level > reqParsed.level) {
    return {
      score: 100,
      status: 'Exceeds requirement',
      requiredEducation: reqLabel,
      candidateEducation: candLabel,
      reason: `Exceeds requirement: Candidate has ${candLabel}, exceeding the required ${reqLabel}.`,
    };
  }
  if (candParsed.level === reqParsed.level) {
    return {
      score: 100,
      status: 'Meets requirement',
      requiredEducation: reqLabel,
      candidateEducation: candLabel,
      reason: `Meets requirement: Candidate has ${candLabel}, meeting the required ${reqLabel}.`,
    };
  }
  const score = Math.round((candParsed.level / reqParsed.level) * 100);
  if (candParsed.isOngoing && (candParsed.pursuingLevel || 0) >= reqParsed.level) {
    return {
      score,
      status: 'Partially meets',
      requiredEducation: reqLabel,
      candidateEducation: candLabel,
      reason: `Partially meets: Requires ${reqLabel}; candidate is currently an undergraduate/enrolled (highest completed level: ${candLabel}).`,
    };
  }
  return {
    score,
    status: 'Does not meet',
    requiredEducation: reqLabel,
    candidateEducation: candLabel,
    reason: `Does not meet: Requires ${reqLabel}; candidate has ${candLabel}.`,
  };
}

const CLIENT_CERT_STOP = new Set([
  'tesda', 'national', 'certificate', 'certification', 'certified', 'level', 'levels',
  'dole', 'osh', 'bosh', 'cosh', 'lean', 'six', 'sigma', 'sixsigma', 'scrum',
  'professional', 'master', 'civil', 'career', 'service', 'eligibility',
  'holder', 'holders', 'passer', 'passers', 'practitioner', 'training',
  'preferred', 'required', 'plus', 'advantage', 'desirable', 'highly', 'recommended',
  'optional', 'minimum', 'min', 'least', 'at', 'higher', 'above', 'equivalent',
  'similar', 'valid', 'active', 'current', 'accredited', 'agency', 'from', 'with',
  'must', 'have', 'is', 'be', 'in', 'of', 'for', 'and', 'or', 'the', 'a', 'an',
]);

const CLIENT_CERT_FAMILIES: Array<{ family: string; levels: Array<[number, RegExp]> }> = [
  {
    family: 'tesda_nc',
    levels: [
      [4, /\b(?:nc\s*(?:iv|4)|nciv|national\s+certificate\s*(?:iv|4))\b/i],
      [3, /\b(?:nc\s*(?:iii|3)|nciii|national\s+certificate\s*(?:iii|3))\b/i],
      [2, /\b(?:nc\s*(?:ii|2)|ncii|national\s+certificate\s*(?:ii|2))\b/i],
      [1, /\b(?:nc\s*(?:i|1)|nci|national\s+certificate\s*(?:i|1))\b/i],
    ],
  },
  {
    family: 'safety_officer',
    levels: [
      [4, /\b(?:so\s*4|safety\s+officer\s*(?:4|iv))\b/i],
      [3, /\b(?:so\s*3|safety\s+officer\s*(?:3|iii))\b/i],
      [2, /\b(?:so\s*2|safety\s+officer\s*(?:2|ii))\b/i],
      [1, /\b(?:so\s*1|safety\s+officer\s*(?:1|i))\b/i],
    ],
  },
  {
    family: 'six_sigma',
    levels: [
      [5, /\bmaster\s+black\s+belt\b/i],
      [4, /\bblack\s+belt\b/i],
      [3, /\bgreen\s+belt\b/i],
      [2, /\byellow\s+belt\b/i],
      [1, /\bwhite\s+belt\b/i],
    ],
  },
  {
    family: 'civil_service',
    levels: [
      [2, /\b(?:civil|career)\s+service\s+professional\b|\bcse\s+professional\b/i],
      [1, /\b(?:civil|career)\s+service\s+sub[-\s]?professional\b|\bcse\s+sub[-\s]?professional\b/i],
    ],
  },
  {
    family: 'scrum_psm',
    levels: [
      [3, /\bpsm\s*(?:iii|3)\b/i],
      [2, /\bpsm\s*(?:ii|2)\b/i],
      [1, /\bpsm\s*(?:i|1)\b/i],
    ],
  },
];

function parseGradedCertClient(text: string): { family: string; level: number; subject: string } | null {
  const norm = cleanRequirementInput(text);
  if (!norm) return null;
  for (const spec of CLIENT_CERT_FAMILIES) {
    for (const [lvl, pat] of spec.levels) {
      const m = pat.exec(norm);
      if (m) {
        const rem = `${norm.slice(0, m.index)} ${norm.slice(m.index + m[0].length)}`.toLowerCase();
        const subj = (rem.match(/[a-z0-9]+/g) || []).filter((t) => t.length >= 2 && !CLIENT_CERT_STOP.has(t)).join(' ');
        return { family: spec.family, level: lvl, subject: subj };
      }
    }
  }
  return null;
}

export function compareGradedCertificationClient(
  candCert: string,
  reqCert: string
): { matched: boolean; exceeds: boolean; score: number } | null {
  const reqInfo = parseGradedCertClient(reqCert);
  const candInfo = parseGradedCertClient(candCert);
  if (!reqInfo || !candInfo || reqInfo.family !== candInfo.family) return null;
  if (reqInfo.subject) {
    const reqTokens = new Set(reqInfo.subject.split(' ').filter(Boolean));
    const candTokens = new Set(candInfo.subject.split(' ').filter(Boolean));
    const allPresent = reqTokens.size > 0 && Array.from(reqTokens).every((t) => candTokens.has(t));
    if (!allPresent && !candInfo.subject.includes(reqInfo.subject) && !reqInfo.subject.includes(candInfo.subject)) {
      return { matched: false, exceeds: false, score: 0 };
    }
  }
  if (candInfo.level > reqInfo.level) return { matched: true, exceeds: true, score: 100 };
  if (candInfo.level === reqInfo.level) return { matched: true, exceeds: false, score: 100 };
  return { matched: false, exceeds: false, score: Math.round((candInfo.level / reqInfo.level) * 100) };
}
