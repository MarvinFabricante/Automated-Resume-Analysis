import { Job } from '../types';
import { isNoValueRequirement } from './criterionStatus';

export interface EvaluationFilters {
  skills: boolean;
  experience: boolean;
  certifications: boolean;
}

export interface ParsedJobRequirements {
  jobSkills: string[];
  jobExp: string;
  reqYears: number;
  expKeywords: string[];
  hasEduReq: boolean;
  jobEdu: string;
  hasCertReq: boolean;
  jobCert: string;
  certKeywords: string[];
}

export interface ComparableApplicationLike {
  id: number;
  job_id?: number | string;
  applied_job_id?: number | string;
  applied_job_title?: string;
  preferredJob?: string;
  job?: {
    id?: number | string;
    job_title?: string;
  };
  matchScore?: number;
  match_score?: number | null;
  skillsScore?: number;
  skills_score?: number;
  experienceScore?: number;
  experience_score?: number;
  educationScore?: number;
  education_score?: number;
  certificationsScore?: number;
  certifications_score?: number;
}

export interface PersonGroupLike<TApp extends ComparableApplicationLike = ComparableApplicationLike> {
  personKey: string;
  applications: TApp[];
}

export interface RankedPersonItem<
  TApp extends ComparableApplicationLike = ComparableApplicationLike,
  TGroup extends PersonGroupLike<TApp> = PersonGroupLike<TApp>,
> {
  person: TGroup;
  effectiveApp: TApp;
  appliedToSelectedJob: boolean;
  displayScore: number;
  sortScore: number;
  originalIndex: number;
}

const EXP_STOP_WORDS = new Set([
  'years', 'year', 'experience', 'preferably', 'preferred', 'plus', 'with',
  'have', 'from', 'role', 'work', 'least', 'must', 'should', 'about',
  'minimum', 'candidate',
]);

const CERT_STOP_WORDS = new Set([
  'certification', 'certified', 'license', 'licensed', 'preferred', 'plus',
  'with', 'have', 'must', 'required',
]);

/**
 * Determine whether an application targets the given job by ID, falling back
 * to case-insensitive title comparison only when no job ID is present.
 */
export function doesApplicationMatchJob(
  app: ComparableApplicationLike | null | undefined,
  job: Job | null | undefined
): boolean {
  if (!app || !job) return false;

  const appJobId = app.job_id ?? app.applied_job_id ?? app.job?.id;
  if (appJobId !== undefined && appJobId !== null && String(appJobId).trim() !== '') {
    const normAppJobId = String(appJobId).trim();
    if (job.id !== undefined && job.id !== null && normAppJobId === String(job.id).trim()) {
      return true;
    }
    if (job.job_id !== undefined && job.job_id !== null && normAppJobId === String(job.job_id).trim()) {
      return true;
    }
    return false;
  }

  const appTitle = String(app.applied_job_title || app.preferredJob || app.job?.job_title || '')
    .trim()
    .toLowerCase();
  const targetTitle = String(job.title || job.job_title || '')
    .trim()
    .toLowerCase();

  return Boolean(appTitle && targetTitle && appTitle === targetTitle);
}

/**
 * Return an application's unrounded score for the job it actually applied to,
 * respecting active evaluation pillar filters (used for tie-breaking decimal scores).
 */
export function getAppliedJobRawScore(
  app: ComparableApplicationLike,
  filters: EvaluationFilters
): number {
  const skillsScore = app.skillsScore ?? app.skills_score ?? 0;
  const expScore = app.experienceScore ?? app.experience_score ?? 0;
  const certScore = app.certifications_score ?? app.certificationsScore ?? 0;

  let totalWeight = 0;
  let rawScore = 0;

  if (filters?.skills) {
    totalWeight += 40;
    rawScore += skillsScore * 40;
  }
  if (filters?.experience) {
    totalWeight += 30;
    rawScore += expScore * 30;
  }
  if (filters?.certifications) {
    totalWeight += 10;
    rawScore += certScore * 10;
  }

  const originalScore = app.matchScore ?? app.match_score ?? 0;

  if (originalScore > 0) {
    if (
      (filters?.skills && filters?.experience && filters?.certifications) ||
      (skillsScore === 0 && expScore === 0 && certScore === 0)
    ) {
      return originalScore;
    }
    if (totalWeight > 0 && (skillsScore > 0 || expScore > 0 || certScore > 0)) {
      return rawScore / totalWeight;
    }
    return originalScore;
  }

  return totalWeight > 0 ? rawScore / totalWeight : 0;
}

/**
 * Return an application's authoritative rounded score for the job it actually applied to,
 * respecting active evaluation pillar filters.
 */
export function getAppliedJobScore(
  app: ComparableApplicationLike,
  filters: EvaluationFilters
): number {
  return Math.round(getAppliedJobRawScore(app, filters));
}

/**
 * Return the application targeting `job` with the highest score (ties broken by
 * earliest occurrence in `applications`), or `undefined` if none match.
 */
export function pickBestMatchingApplication<TApp extends ComparableApplicationLike>(
  applications: TApp[],
  job: Job,
  filters: EvaluationFilters
): TApp | undefined {
  let bestApp: TApp | undefined;
  let bestScore = -Infinity;

  for (const app of applications) {
    if (!doesApplicationMatchJob(app, job)) continue;
    const score = getAppliedJobRawScore(app, filters);
    if (!bestApp || score > bestScore) {
      bestApp = app;
      bestScore = score;
    }
  }

  return bestApp;
}

/**
 * Pre-parse a job's skills, experience, and certification requirements once so
 * scoring a large list of applicants runs in linear O(N) time.
 */
export function preparseJobRequirements(job: Job): ParsedJobRequirements {
  let jobSkills: string[] = [];
  if (job.skills_requirements) {
    const raw = Array.isArray(job.skills_requirements)
      ? job.skills_requirements
      : String(job.skills_requirements).split(/[,;\n•|]+/);
    jobSkills = raw
      .map(s => String(s).trim().replace(/^[-*•\s]+/, '').replace(/[.,;:]+$/, '').toLowerCase())
      .filter(s => s.length > 0);
  } else if (job.description) {
    jobSkills = job.description.toLowerCase().split(/[\s,;]+/).filter(w => w.length > 3);
  } else {
    jobSkills = (job.title || job.job_title || '').toLowerCase().split(/[\s,]+/).filter(w => w.length > 2);
  }

  const rawExp = job.experience_requirements || '';
  const jobExp = isNoValueRequirement(rawExp) ? '' : rawExp.toLowerCase();
  const minPhraseMatch = jobExp.match(/(?:minimum|at\s+least|min)\s*(?:of\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)/i);
  const reqYearsMatch = jobExp.match(/(\d+)(?:\s*[-–—to]+\s*\d+)?\+?\s*(?:years?|yrs?)/i);
  const reqYears = minPhraseMatch
    ? parseInt(minPhraseMatch[1], 10)
    : reqYearsMatch
      ? parseInt(reqYearsMatch[1], 10)
      : 0;
  const expKeywords = jobExp
    ? jobExp.split(/[\s,.;:]+/).filter(w => w.length > 3 && !EXP_STOP_WORDS.has(w))
    : [];

  const jobEduRaw = job.education_requirements || '';
  const hasEduReq = !isNoValueRequirement(jobEduRaw);
  const jobEdu = hasEduReq ? String(jobEduRaw).trim() : '';

  const jobCertRaw = job.certifications_requirements || '';
  const hasCertReq = !isNoValueRequirement(jobCertRaw);
  const jobCert = jobCertRaw.toLowerCase().trim();
  const certKeywords = hasCertReq
    ? jobCert.split(/[\s,.;:]+/).filter(w => w.length > 2 && !CERT_STOP_WORDS.has(w))
    : [];

  return {
    jobSkills,
    jobExp,
    reqYears,
    expKeywords,
    hasEduReq,
    jobEdu,
    hasCertReq,
    jobCert,
    certKeywords,
  };
}

/**
 * Partition person groups into applicants who applied to `selectedJob` (sorted
 * descending by their score for that job) and everyone else (preserving order).
 */
export function partitionAndSortPersonGroups<
  TApp extends ComparableApplicationLike,
  TGroup extends PersonGroupLike<TApp>,
>({
  personGroups,
  selectedJob,
  parsedJob,
  evaluationFilters,
  personSelectedAppMap,
  scoreAgainstJob,
}: {
  personGroups: TGroup[];
  selectedJob: Job | undefined;
  parsedJob?: ParsedJobRequirements;
  evaluationFilters: EvaluationFilters;
  personSelectedAppMap: Record<string, number>;
  scoreAgainstJob: (
    app: TApp,
    job: Job,
    filters: EvaluationFilters,
    parsedJob: ParsedJobRequirements
  ) => number;
}): {
  appliedToJob: RankedPersonItem<TApp, TGroup>[];
  otherApplicants: RankedPersonItem<TApp, TGroup>[];
} {
  if (!selectedJob) {
    const otherApplicants = personGroups.map((person, originalIndex) => {
      const manualId = personSelectedAppMap[person.personKey];
      const effectiveApp =
        (manualId !== undefined ? person.applications.find(a => a.id === manualId) : undefined) ||
        person.applications[0];
      const rawScore = getAppliedJobRawScore(effectiveApp, evaluationFilters);
      return {
        person,
        effectiveApp,
        appliedToSelectedJob: false,
        displayScore: Math.round(rawScore),
        sortScore: rawScore,
        originalIndex,
      };
    });
    return { appliedToJob: [], otherApplicants };
  }

  const resolvedParsedJob = parsedJob || preparseJobRequirements(selectedJob);
  const appliedToJob: RankedPersonItem<TApp, TGroup>[] = [];
  const otherApplicants: RankedPersonItem<TApp, TGroup>[] = [];

  personGroups.forEach((person, originalIndex) => {
    const manualId = personSelectedAppMap[person.personKey];
    const manualApp =
      manualId !== undefined ? person.applications.find(a => a.id === manualId) : undefined;

    const bestMatchingApp = pickBestMatchingApplication(
      person.applications,
      selectedJob,
      evaluationFilters
    );

    if (bestMatchingApp) {
      const bestRawScore = getAppliedJobRawScore(bestMatchingApp, evaluationFilters);
      const effectiveApp = manualApp || bestMatchingApp;
      const effectiveMatchesJob = doesApplicationMatchJob(effectiveApp, selectedJob);
      const displayScore = effectiveMatchesJob
        ? getAppliedJobScore(effectiveApp, evaluationFilters)
        : scoreAgainstJob(effectiveApp, selectedJob, evaluationFilters, resolvedParsedJob);
      const sortScore = effectiveMatchesJob
        ? getAppliedJobRawScore(effectiveApp, evaluationFilters)
        : bestRawScore;

      appliedToJob.push({
        person,
        effectiveApp,
        appliedToSelectedJob: true,
        displayScore,
        sortScore,
        originalIndex,
      });
    } else {
      const effectiveApp = manualApp || person.applications[0];
      const displayScore = scoreAgainstJob(effectiveApp, selectedJob, evaluationFilters, resolvedParsedJob);

      otherApplicants.push({
        person,
        effectiveApp,
        appliedToSelectedJob: false,
        displayScore,
        sortScore: displayScore,
        originalIndex,
      });
    }
  });

  appliedToJob.sort((a, b) => (b.sortScore - a.sortScore) || (a.originalIndex - b.originalIndex));

  return { appliedToJob, otherApplicants };
}

/**
 * Keep every selected person selected when switching jobs, swapping a multi-application
 * candidate's selected ID to their matching application for `nextJob` when one exists.
 */
export function syncSelectedApplicationIdsForJob<TApp extends ComparableApplicationLike>({
  selectedIds,
  candidates,
  nextJob,
  evaluationFilters,
  isSamePerson,
}: {
  selectedIds: number[];
  candidates: TApp[];
  nextJob: Job | undefined;
  evaluationFilters: EvaluationFilters;
  isSamePerson: (a: TApp, b: TApp) => boolean;
}): number[] {
  if (!nextJob || selectedIds.length === 0) {
    return selectedIds;
  }

  const byId = new Map<number, TApp>();
  for (const cand of candidates) {
    byId.set(cand.id, cand);
  }

  const updated: number[] = [];
  const seen = new Set<number>();

  for (const id of selectedIds) {
    const currentApp = byId.get(id);
    let nextId = id;
    if (currentApp) {
      const personApps = candidates.filter((c) => isSamePerson(currentApp, c));
      const bestMatch = pickBestMatchingApplication(personApps, nextJob, evaluationFilters);
      if (bestMatch) {
        nextId = bestMatch.id;
      }
    }
    if (!seen.has(nextId)) {
      seen.add(nextId);
      updated.push(nextId);
    }
  }

  return updated;
}

/**
 * Sync the previewed application ID when selecting, changing, or clearing the target job:
 * picks the matching application for `nextJob` when present, or resets to the person's
 * default application when cleared.
 */
export function syncActiveApplicationIdForJob<TApp extends ComparableApplicationLike>({
  activeId,
  candidates,
  nextJob,
  evaluationFilters,
  isSamePerson,
}: {
  activeId: number | null;
  candidates: TApp[];
  nextJob: Job | undefined;
  evaluationFilters: EvaluationFilters;
  isSamePerson: (a: TApp, b: TApp) => boolean;
}): number | null {
  if (activeId === null) {
    return null;
  }

  const currentApp = candidates.find((c) => c.id === activeId);
  if (!currentApp) {
    return activeId;
  }

  const personApps = candidates.filter((c) => isSamePerson(currentApp, c));
  if (nextJob) {
    return pickBestMatchingApplication(personApps, nextJob, evaluationFilters)?.id ?? activeId;
  }

  return personApps[0]?.id ?? activeId;
}
