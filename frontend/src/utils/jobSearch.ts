export interface SearchableJob {
  job_title?: string;
  title?: string;
  department?: string;
  location?: string;
  skills_requirements?: string | string[];
  description?: string;
  is_active?: boolean;
}

export interface SearchableCandidate {
  id?: number | string;
  name?: string;
  candidate_name?: string;
  email?: string;
  candidate_email?: string;
  preferredJob?: string;
  job_title?: string;
  position?: string;
  applied_job_title?: string;
  skills?: string | string[];
  status?: string;
  matchScore?: number | null;
  match_score?: number | null;
}

function normalizeSkills(skills: string | string[] | undefined): string {
  if (Array.isArray(skills)) return skills.join(', ').toLowerCase();
  return (skills || '').toLowerCase();
}

function splitWords(text: string): string[] {
  return text.split(/[\s,;/().\-–—]+/).filter(Boolean);
}

/**
 * Compute a relevance rank (lower = stronger match) for a job against a search query,
 * or `null` if the job does not match.
 *
 * - Single-letter queries (e.g. "J"): ONLY match jobs whose title (or a word in the title)
 *   starts with that letter, so unrelated jobs are never suggested.
 * - 2-character queries: match title (startsWith / word-startsWith / includes) or
 *   department/skill words starting with the query.
 * - 3+ character queries: full search across title, department, skills, location, and description.
 */
export function getJobSearchRank(job: SearchableJob, rawQuery: string): number | null {
  const query = rawQuery.toLowerCase().trim();
  if (!query) return 0;

  const title = (job.job_title || job.title || '').toLowerCase().trim();
  const titleWords = splitWords(title);

  if (title.startsWith(query)) return 0;
  if (titleWords.some((w) => w.startsWith(query))) return 1;

  // Single-letter search: only show jobs whose title (or a word in the title) starts with that letter
  if (query.length === 1) {
    return null;
  }

  const dept = (job.department || '').toLowerCase().trim();
  const deptWords = splitWords(dept);
  const skills = normalizeSkills(job.skills_requirements);
  const skillTokens = skills.split(/[,;\n•]+/).map((s) => s.trim()).filter(Boolean);

  if (title.includes(query)) return 2;

  if (
    dept.startsWith(query) ||
    deptWords.some((w) => w.startsWith(query)) ||
    skillTokens.some((s) => s.startsWith(query))
  ) {
    return 3;
  }

  if (query.length === 2) {
    return null;
  }

  const loc = (job.location || '').toLowerCase().trim();
  const desc = (job.description || '').toLowerCase();

  if (dept.includes(query) || skills.includes(query)) return 4;
  if (loc.includes(query)) return 5;
  if (desc.includes(query)) return 6;

  return null;
}

export function filterAndRankJobs<T extends SearchableJob>(jobs: T[], rawQuery: string): T[] {
  const query = rawQuery.trim();
  if (!query) return jobs;

  const scored: Array<{ job: T; rank: number; title: string }> = [];
  for (const job of jobs) {
    const rank = getJobSearchRank(job, query);
    if (rank !== null) {
      scored.push({
        job,
        rank,
        title: (job.job_title || job.title || '').toLowerCase(),
      });
    }
  }

  scored.sort((a, b) => a.rank - b.rank || a.title.localeCompare(b.title));
  return scored.map((item) => item.job);
}

/**
 * Compute a relevance rank (lower = stronger match) for a candidate/applicant against a search query,
 * or `null` if the candidate does not match.
 *
 * - Single-letter queries (e.g. "J"): ONLY match candidates whose full name or any name word
 *   (length >= 2, e.g. "John", "James") starts with that letter.
 * - 2-character queries: match name prefix, name word prefix, name substring, email local part prefix, or job title prefix.
 * - 3+ character queries: also match email local part, applied role, or skills.
 */
export function getCandidateSearchRank(candidate: SearchableCandidate, rawQuery: string): number | null {
  const query = rawQuery.toLowerCase().trim();
  if (!query) return 0;

  const name = (candidate.name || candidate.candidate_name || '').toLowerCase().trim();
  const nameWords = splitWords(name).filter((w) => w.length >= 2);

  if (name.startsWith(query)) return 0;
  if (nameWords.some((w) => w.startsWith(query))) return 1;

  // Single-letter search: only match candidates whose name (or a first/middle/last name word) starts with that letter
  if (query.length === 1) {
    return null;
  }

  const email = (candidate.email || candidate.candidate_email || '').toLowerCase().trim();
  const emailLocal = email.split('@')[0] || '';
  const role = (
    candidate.preferredJob ||
    candidate.job_title ||
    candidate.position ||
    candidate.applied_job_title ||
    ''
  )
    .toLowerCase()
    .trim();
  const roleWords = splitWords(role);

  if (name.includes(query)) return 2;
  if (emailLocal.startsWith(query)) return 3;
  if (role.startsWith(query) || roleWords.some((w) => w.startsWith(query))) return 4;

  if (query.length === 2) {
    return null;
  }

  const skills = normalizeSkills(candidate.skills);
  if (emailLocal.includes(query)) return 5;
  if (role.includes(query)) return 6;
  if (skills.includes(query)) return 7;

  return null;
}

export function filterAndRankCandidates<T extends SearchableCandidate>(
  candidates: T[],
  rawQuery: string
): T[] {
  const query = rawQuery.trim();
  if (!query) return candidates;

  const scored: Array<{ candidate: T; rank: number; name: string }> = [];
  for (const candidate of candidates) {
    const rank = getCandidateSearchRank(candidate, query);
    if (rank !== null) {
      scored.push({
        candidate,
        rank,
        name: (candidate.name || candidate.candidate_name || '').toLowerCase(),
      });
    }
  }

  scored.sort((a, b) => a.rank - b.rank || a.name.localeCompare(b.name));
  return scored.map((item) => item.candidate);
}
