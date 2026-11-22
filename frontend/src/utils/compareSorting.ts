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
 * Return an application's authoritative score for the job it actually applied to,
 * respecting active evaluation pillar filters.
 */
export function getAppliedJobScore(
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
      return Math.round(originalScore);
    }
    if (totalWeight > 0 && (skillsScore > 0 || expScore > 0 || certScore > 0)) {
      return Math.round(rawScore / totalWeight);
    }
    return Math.round(originalScore);
  }

  return totalWeight > 0 ? Math.round(rawScore / totalWeight) : 0;
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

  const jobExp = (job.experience_requirements || '').toLowerCase();
  const reqYearsMatch = jobExp.match(/(\d+)(?:\s*-\s*(\d+))?\+?\s*(?:years?|yrs?)/i);
  const reqYears = reqYearsMatch ? parseInt(reqYearsMatch[1], 10) : 0;
  const expKeywords = jobExp
    ? jobExp.split(/[\s,.;:]+/).filter(w => w.length > 3 && !EXP_STOP_WORDS.has(w))
    : [];

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
  evaluationFilters,
  personSelectedAppMap,
  scoreAgainstJob,
}: {
  personGroups: TGroup[];
  selectedJob: Job | undefined;
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
      return {
        person,
        effectiveApp,
        appliedToSelectedJob: false,
        displayScore: getAppliedJobScore(effectiveApp, evaluationFilters),
        originalIndex,
      };
    });
    return { appliedToJob: [], otherApplicants };
  }

  const parsedJob = preparseJobRequirements(selectedJob);
  const appliedToJob: RankedPersonItem<TApp, TGroup>[] = [];
  const otherApplicants: RankedPersonItem<TApp, TGroup>[] = [];

  personGroups.forEach((person, originalIndex) => {
    const manualId = personSelectedAppMap[person.personKey];
    const manualApp =
      manualId !== undefined ? person.applications.find(a => a.id === manualId) : undefined;

    const matchingApps = person.applications.filter(app =>
      doesApplicationMatchJob(app, selectedJob)
    );

    if (matchingApps.length > 0) {
      let bestMatchingApp = matchingApps[0];
      let bestMatchingScore = getAppliedJobScore(bestMatchingApp, evaluationFilters);
      for (let i = 1; i < matchingApps.length; i++) {
        const candidateScore = getAppliedJobScore(matchingApps[i], evaluationFilters);
        if (candidateScore > bestMatchingScore) {
          bestMatchingScore = candidateScore;
          bestMatchingApp = matchingApps[i];
        }
      }

      const effectiveApp = manualApp || bestMatchingApp;
      const displayScore = doesApplicationMatchJob(effectiveApp, selectedJob)
        ? getAppliedJobScore(effectiveApp, evaluationFilters)
        : scoreAgainstJob(effectiveApp, selectedJob, evaluationFilters, parsedJob);

      appliedToJob.push({
        person,
        effectiveApp,
        appliedToSelectedJob: true,
        displayScore,
        originalIndex,
      });
    } else {
      const effectiveApp = manualApp || person.applications[0];
      const displayScore = scoreAgainstJob(effectiveApp, selectedJob, evaluationFilters, parsedJob);

      otherApplicants.push({
        person,
        effectiveApp,
        appliedToSelectedJob: false,
        displayScore,
        originalIndex,
      });
    }
  });

  appliedToJob.sort((a, b) => (b.displayScore - a.displayScore) || (a.originalIndex - b.originalIndex));

  return { appliedToJob, otherApplicants };
}
