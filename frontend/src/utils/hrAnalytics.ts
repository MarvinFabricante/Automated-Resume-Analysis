const ANALYTICS_PALETTE = ['#D60041', '#F43F5E', '#3B82F6', '#10B981', '#8B5CF6', '#F59E0B'];

export interface AnalyticsBucket {
  label: string;
  value: number;
  percentage: string;
  color: string;
  avg_score?: number;
  statusKey?: string;
}

export function extractAppUtcDateIso(dateInput?: string | null): string | null {
  if (!dateInput) return null;
  const raw = String(dateInput).trim();
  if (!raw) return null;
  // Naive ISO timestamps from FastAPI (e.g. "2026-11-11T05:10:00") are stored in UTC
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw);
  const normalized = /^\d{4}-\d{2}-\d{2}T/.test(raw) && !hasTz ? `${raw}Z` : raw;
  const parsed = new Date(normalized);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().split('T')[0];
}

export function computeAverageMatchScore(
  applications: any[] = [],
  backendAverage?: number | null
): number {
  if (Array.isArray(applications) && applications.length > 0) {
    const sum = applications.reduce((acc, app) => {
      const rawScore = app?.match_score ?? app?.matchScore ?? 0;
      const numeric = Number(rawScore);
      return acc + (Number.isFinite(numeric) ? numeric : 0);
    }, 0);
    return Number((sum / applications.length).toFixed(1));
  }
  const fallback = Number(backendAverage ?? 0);
  return Number.isFinite(fallback) ? Number(fallback.toFixed(1)) : 0;
}

export function computePositionDistribution(
  applications: any[] = [],
  backendPositions: any[] = []
): AnalyticsBucket[] {
  if (Array.isArray(applications) && applications.length > 0) {
    const map = new Map<string, { count: number; scoreSum: number }>();
    for (const app of applications) {
      const title = String(
        app?.preferredJob || app?.job?.job_title || app?.job_title || 'Unspecified'
      ).trim() || 'Unspecified';
      const rawScore = Number(app?.match_score ?? app?.matchScore ?? 0);
      const score = Number.isFinite(rawScore) ? rawScore : 0;
      const prev = map.get(title) || { count: 0, scoreSum: 0 };
      map.set(title, { count: prev.count + 1, scoreSum: prev.scoreSum + score });
    }
    const total = applications.length;
    return Array.from(map.entries())
      .sort((a, b) => b[1].count - a[1].count || a[0].localeCompare(b[0]))
      .map(([label, stats], idx) => ({
        label,
        value: stats.count,
        avg_score: Number((stats.scoreSum / stats.count).toFixed(1)),
        color: ANALYTICS_PALETTE[idx % ANALYTICS_PALETTE.length],
        percentage: `${Math.round((stats.count / total) * 100)}%`,
      }));
  }
  return Array.isArray(backendPositions) ? backendPositions : [];
}

export function computeSkillsDistribution(
  applications: any[] = [],
  backendSkills: any[] = []
): AnalyticsBucket[] {
  if (Array.isArray(applications) && applications.length > 0) {
    const counts = new Map<string, { label: string; count: number }>();
    for (const app of applications) {
      const rawSkills = app?.skills;
      if (!rawSkills) continue;
      const tokens = Array.isArray(rawSkills)
        ? rawSkills.map((s: any) => String(s).trim()).filter(Boolean)
        : String(rawSkills)
          .split(/[|,;•\n]+/)
          .map((s) => s.trim())
          .filter(Boolean);

      const seenInApp = new Set<string>();
      for (const tok of tokens) {
        const key = tok.toLowerCase();
        if (seenInApp.has(key)) continue;
        seenInApp.add(key);
        const existing = counts.get(key);
        if (existing) {
          existing.count += 1;
        } else {
          counts.set(key, { label: tok, count: 1 });
        }
      }
    }
    const total = applications.length;
    return Array.from(counts.values())
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
      .map((item, idx) => ({
        label: item.label,
        value: item.count,
        color: ANALYTICS_PALETTE[idx % ANALYTICS_PALETTE.length],
        percentage: `${Math.round((item.count / total) * 100)}%`,
      }));
  }
  return Array.isArray(backendSkills) ? backendSkills : [];
}

export function computeDepartmentDistribution(
  applications: any[] = [],
  backendDepartments: any[] = []
): AnalyticsBucket[] {
  if (Array.isArray(applications) && applications.length > 0) {
    const counts = new Map<string, number>();
    for (const app of applications) {
      const deptRaw = app?.jobDepartment || app?.job?.department || '';
      const dept = deptRaw && deptRaw !== 'N/A' ? String(deptRaw).trim() : 'General';
      counts.set(dept, (counts.get(dept) || 0) + 1);
    }
    const total = applications.length;
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
      .map(([label, value], idx) => ({
        label,
        value,
        color: ANALYTICS_PALETTE[idx % ANALYTICS_PALETTE.length],
        percentage: `${Math.round((value / total) * 100)}%`,
      }));
  }
  const hasRealBackend =
    Array.isArray(backendDepartments) &&
    backendDepartments.some((d: any) => (d?.value || 0) > 0);
  if (hasRealBackend) return backendDepartments;
  if (Array.isArray(backendDepartments) && backendDepartments.length > 0) return backendDepartments;
  return [
    { label: 'Engineering', value: 0, color: '#D60041', percentage: '0%' },
    { label: 'Operations', value: 0, color: '#3B82F6', percentage: '0%' },
    { label: 'Human Resources', value: 0, color: '#10B981', percentage: '0%' },
  ];
}

export type CandidateSortOption =
  | 'date_desc'
  | 'date_asc'
  | 'match_desc'
  | 'match_asc'
  | 'name_asc'
  | 'name_desc'
  | string;

export function extractAppTimestampMs(dateInput?: string | null): number {
  if (!dateInput) return 0;
  const raw = String(dateInput).trim();
  if (!raw) return 0;
  const hasTz = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw);
  const normalized = /^\d{4}-\d{2}-\d{2}T/.test(raw) && !hasTz ? `${raw}Z` : raw;
  const ms = new Date(normalized).getTime();
  return Number.isFinite(ms) ? ms : 0;
}

export function getCandidatePosition(candidate: any): string {
  return String(
    candidate?.preferredJob || candidate?.job?.job_title || candidate?.job_title || ''
  ).trim();
}

export function getCandidateScore(candidate: any): number {
  const raw = Number(candidate?.match_score ?? candidate?.matchScore ?? 0);
  return Number.isFinite(raw) ? raw : 0;
}

export function matchesPositionFilter(candidate: any, positionFilter?: string): boolean {
  const normalized = String(positionFilter || '').trim();
  if (!normalized || normalized === 'ALL' || normalized === 'All Jobs') return true;
  return getCandidatePosition(candidate).toLowerCase() === normalized.toLowerCase();
}

export function sortCandidatesByOption<T = any>(
  list: T[],
  sortBy: CandidateSortOption = 'match_desc'
): T[] {
  if (!Array.isArray(list) || list.length <= 1) return Array.isArray(list) ? [...list] : [];
  const needName = sortBy === 'name_asc' || sortBy === 'name_desc';
  const wrapped = list.map((item: any) => ({
    item,
    score: getCandidateScore(item),
    time: extractAppTimestampMs(item?.created_at || item?.date),
    id: Number(item?.id || 0),
    nameLower: needName ? String(item?.name || item?.candidate_name || '').toLowerCase() : '',
  }));

  wrapped.sort((a, b) => {
    switch (sortBy) {
      case 'match_asc':
        if (a.score !== b.score) return a.score - b.score;
        if (b.time !== a.time) return b.time - a.time;
        return b.id - a.id;
      case 'date_desc':
        if (b.time !== a.time) return b.time - a.time;
        if (b.score !== a.score) return b.score - a.score;
        return b.id - a.id;
      case 'date_asc':
        if (a.time !== b.time) return a.time - b.time;
        if (b.score !== a.score) return b.score - a.score;
        return a.id - b.id;
      case 'name_asc': {
        const cmp = a.nameLower.localeCompare(b.nameLower);
        return cmp !== 0 ? cmp : b.time - a.time;
      }
      case 'name_desc': {
        const cmp = b.nameLower.localeCompare(a.nameLower);
        return cmp !== 0 ? cmp : b.time - a.time;
      }
      case 'match_desc':
      default:
        if (b.score !== a.score) return b.score - a.score;
        if (b.time !== a.time) return b.time - a.time;
        return b.id - a.id;
    }
  });

  return wrapped.map((entry) => entry.item);
}

