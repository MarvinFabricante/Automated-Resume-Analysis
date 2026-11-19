export interface SearchableJob {
  job_title?: string;
  title?: string;
  department?: string;
  location?: string;
  skills_requirements?: string | string[];
  description?: string;
  is_active?: boolean;
}

function normalizeSkills(skills: string | string[] | undefined): string {
  if (Array.isArray(skills)) return skills.join(', ').toLowerCase();
  return (skills || '').toLowerCase();
}

function splitWords(text: string): string[] {
  return text.split(/[\s,;/()\-–—]+/).filter(Boolean);
}

/**
 * Compute a relevance rank (lower = stronger match) for a job against a search query,
 * or `null` if the job does not match.
 *
 * - Single-letter queries (e.g. "S"): ONLY match jobs whose title (or a word in the title)
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
