import { isNoValueRequirement, cleanRequirementInput, cleanRequirementList } from './criterionStatus';

export interface ClarificationQuestion {
  id: string;
  field: string;
  question: string;
  type?: string;
  placeholder?: string;
  required?: boolean;
  domain?: string;
  reason?: string;
  job_id?: string;
  job_title?: string;
  items?: Array<{ requirement: string; field: string; status?: string; evidence?: string[] }>;
}

export interface ClarificationResponse {
  field: string;
  requirement: string;
  answer: 'yes' | 'some' | 'no';
  years?: number;
  details?: string;
  confirmed_at?: string;
}

export function hasCompleteJobRequirements(job: any): boolean {
  return Boolean(job) && ['skills_requirements', 'certifications_requirements', 'experience_requirements']
    .every(field => Object.prototype.hasOwnProperty.call(job, field) && job[field] !== undefined);
}

export function parseRequirementAnswers(value: string): Record<string, Omit<ClarificationResponse, 'field' | 'requirement'>> {
  try {
    const parsed = JSON.parse(value || '{}');
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {};
  } catch { return {}; }
}

export function collectClarificationResponses(questions: ClarificationQuestion[], answers: Record<string, string>): ClarificationResponse[] {
  const confirmedAt = new Date().toISOString();
  return questions.flatMap(q => {
    if (q.type !== 'requirement_group') return [];
    const values = parseRequirementAnswers(answers[q.id]);
    return (q.items || []).flatMap(item => {
      const value = values[item.requirement];
      return value && ['yes', 'some', 'no'].includes(value.answer)
        ? [{ ...value, field: q.field, requirement: item.requirement, confirmed_at: value.confirmed_at || confirmedAt }] : [];
    });
  });
}

const skillKey = (value: string) => value.toLowerCase().replace(/[-–—]/g, ' ').replace(/\s+/g, ' ').trim();
const requirementItems = (value: any, splitSlash = true): string[] => cleanRequirementList(
  (Array.isArray(value) ? value.join('|') : String(value || '')).split(
    splitSlash ? /[,;|•●◦‣▪►✓\n]+|\s+\/\s+/ : /[,;|•●◦‣▪►✓\n]+/
  )
);
const PURE_DURATION_REQ_RE =
  /^(?:(?:minimum|min\.?|at\s+least)\s+(?:of\s+)?)?\d+(?:\.\d+)?(?:\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?)?\s*\+?\s*(?:years?|yrs?|months?|mos?)(?:\s+(?:of\s+)?(?:relevant|related|direct|professional|work|industry|hands[- ]on|practical|prior)?\s*(?:work\s+)?(?:experience|exp\.?))?(?:\s+(?:preferred|required|minimum))?\.?$/i;


const MFG_JOB_RE =
  /\b(?:manufactur\w*|production|factory|plant|operator|machin\w*|assembly|assembl\w*|warehouse|kiln|ceramic|welding|quality|qc|maintenance|industrial|technician)\b/i;

function hasExplicitExperienceDuration(
  extractedData: any,
  relevanceStr: string,
  extractedYears = 0
): boolean {
  const years = Number(extractedYears || extractedData?.years_experience || 0);
  const totalMonths = Number(extractedData?.total_experience_months || 0);
  if (years > 0 || totalMonths > 0) return true;

  const workExps = Array.isArray(extractedData?.work_experiences)
    ? extractedData.work_experiences
    : [];
  const hasDatedWorkExp = workExps.some(
    (we: any) =>
      we &&
      (Number(we.duration_months || 0) > 0 ||
        (Boolean(String(we.start_date || '').trim()) &&
          (Boolean(String(we.end_date || '').trim()) || Boolean(we.is_current))) ||
        /\b(?:19|20)\d{2}\b/.test(String(we.duration || we.dates || '')))
  );
  if (hasDatedWorkExp) return true;

  const combinedText = `${relevanceStr || ''} ${String(extractedData?.experience || '')}`;
  return (
    /\b\d+(?:\.\d+)?\s*(?:\+?\s*)?(?:years?|yrs?)\b/i.test(combinedText) ||
    /\b(?:19|20)\d{2}\s*[-–—to]+\s*(?:(?:19|20)\d{2}|present|current)\b/i.test(combinedText)
  );
}

function buildFallbackJobQuestions(
  job: any,
  matchData: any,
  candidateSkills: string[],
  extractedYears: number,
  relevanceStr: string,
  extractedData?: any
): ClarificationQuestion[] {
  const jobTitle = String(job?.job_title || job?.title || '').trim();
  if (!jobTitle || jobTitle === 'Position') return [];

  const jobId = String(job?.job_id || job?.id || 'job');
  const slug = jobId.replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase() || 'job';
  const department = String(job?.department || '').trim();
  const jobText = `${jobTitle} ${department} ${job?.description || ''}`;
  const isMfgJob = MFG_JOB_RE.test(jobText);

  const questions: ClarificationQuestion[] = [];

  const expNotRequired =
    String(matchData?.experience_status || '').toLowerCase() === 'not required' ||
    isNoValueRequirement(job?.experience_requirements);
  const hasYears = hasExplicitExperienceDuration(extractedData, relevanceStr, extractedYears);
  if (!expNotRequired && !hasYears) {
    questions.push({
      id: `clarify_${slug}_years_experience`,
      field: 'years_experience',
      job_id: jobId,
      job_title: jobTitle,
      domain: department || (isMfgJob ? 'Manufacturing' : 'General'),
      type: 'number',
      placeholder: 'e.g. 2',
      required: true,
      question: isMfgJob
        ? `How many years of manufacturing experience do you have for the ${jobTitle} role?`
        : department
        ? `How many years of ${jobTitle} (${department}) experience do you have?`
        : `How many years of ${jobTitle} experience do you have?`,
      reason: `Clarifying direct experience duration for ${jobTitle}.`,
    });
  }

  for (const [field, requirement, candidate] of [
    ['skills', job?.skills_requirements, candidateSkills],
    ['certifications', job?.certifications_requirements, extractedData?.certifications_list || extractedData?.certifications],
    ['experience', job?.experience_requirements, extractedData?.experience || relevanceStr],
  ] as const) {
    const splitSlash = field !== 'certifications';
    const existing = new Set(requirementItems(candidate, splitSlash).map(skillKey));
    const items = requirementItems(requirement, splitSlash)
      .filter(item => !(field === 'experience' && hasYears && PURE_DURATION_REQ_RE.test(item.trim())))
      .filter(item => !existing.has(skillKey(item)))
      .map(requirement => ({ field, requirement, status: 'Not confirmed' }));
    if (items.length) questions.push({
      id: `clarify_${slug}_${field}`, field, job_id: jobId, job_title: jobTitle,
      type: 'requirement_group', items,
      question: field === 'certifications' ? 'Which of these certifications or licenses do you hold?' : 'Which of these requirements do you have experience with?',
      reason: 'Confirm each item. Unanswered items remain Not confirmed.',
    });
  }

  const lowJob = jobText.toLowerCase();
  let fitQ = `What daily responsibilities or accomplishments best qualify you for ${jobTitle}${department ? ` (${department})` : ''}?`;
  if (/\b(?:quality|qc|qa|inspection|audit)\b/.test(lowJob)) {
    fitQ = `What quality inspection standards, defect checks, or testing instruments have you used relevant to ${jobTitle}?`;
  } else if (/\b(?:maint|technician|mechanic|electric|engineer)\b/.test(lowJob)) {
    fitQ = `What equipment troubleshooting, preventive maintenance, or engineering systems have you handled for ${jobTitle}?`;
  } else if (isMfgJob) {
    fitQ = `What production lines, factory machinery, or shift operations have you handled relevant to ${jobTitle}?`;
  } else if (/\b(?:hr|human\s+resource|recruit|payroll)\b/.test(lowJob)) {
    fitQ = `What HR workflows (recruitment, timekeeping, payroll, or DOLE compliance) have you handled for ${jobTitle}?`;
  } else if (/\b(?:account|finance|bookkeep|audit|tax)\b/.test(lowJob)) {
    fitQ = `What accounting systems, tax compliance filings, or financial reporting tasks have you managed for ${jobTitle}?`;
  } else if (/\b(?:software|developer|programmer|it|data|network|cloud|backend|frontend)\b/.test(lowJob)) {
    fitQ = `What systems, codebases, or production deployments have you delivered relevant to ${jobTitle}?`;
  }

  const hasSubstantiveExp =
    Boolean(String(relevanceStr || '').trim()) ||
    Boolean(String(extractedData?.experience || '').trim()) ||
    (Array.isArray(extractedData?.work_experiences) &&
      extractedData.work_experiences.some(
        (we: any) =>
          we &&
          (Boolean(String(we.job_title || '').trim()) ||
            Boolean(String(we.responsibilities || we.description || '').trim()))
      ));
  if (!expNotRequired && (!hasSubstantiveExp || matchData?.relevant_experience_count === 0)) {
    questions.push({
      id: `clarify_${slug}_role_fit`,
      field: 'relevance',
      job_id: jobId,
      job_title: jobTitle,
      domain: department || 'General',
      type: 'text',
      placeholder: `Describe experience relevant to ${jobTitle}`,
      question: fitQ,
      reason: `Role-specific clarification for ${jobTitle}.`,
    });
  }

  return questions;
}

function extractMatchJobId(matchObj: any): string {
  if (!matchObj) return '';
  if (matchObj.job_id) return String(matchObj.job_id);
  if (Array.isArray(matchObj.followup_questions)) {
    const qWithJob = matchObj.followup_questions.find((q: any) => q?.job_id);
    if (qWithJob?.job_id) return String(qWithJob.job_id);
  }
  return '';
}

export function getJobScopedState(state: any, jobId?: string) {
  const normalizedJobId = jobId ? String(jobId) : '';
  const stateJob = state?.job || null;
  const stateJobId = stateJob?.job_id || stateJob?.id ? String(stateJob.job_id || stateJob.id) : '';
  const jobMatches = !normalizedJobId || !stateJobId || stateJobId === normalizedJobId;

  const stateMatch = state?.matchData || null;
  const matchJobId = extractMatchJobId(stateMatch);
  const matchMatches =
    Boolean(stateMatch) &&
    ((!normalizedJobId && !matchJobId) ||
      (matchJobId ? matchJobId === normalizedJobId : jobMatches));

  return {
    job: jobMatches ? stateJob : null,
    match: matchMatches ? stateMatch : null,
  };
}

export function mergeInitialJobMatch(prev: any, next: any, jobId?: string) {
  if (!next) return prev;
  const normalizedJobId = jobId ? String(jobId) : '';
  const prevJobId = extractMatchJobId(prev);
  const sameJob = Boolean(prev) && (!prevJobId || !normalizedJobId || prevJobId === normalizedJobId);
  if (sameJob && Array.isArray(prev.followup_questions) && prev.followup_questions.length > 0) {
    return prev;
  }
  return next;
}

export function buildCandidateMatchPayload(
  formData: {
    skills: string[];
    jobTitle: string;
    company: string;
    relevance: string;
    degree: string;
    college: string;
    fullName: string;
    location: string;
  },
  clarificationQuestions: ClarificationQuestion[],
  clarificationAnswers: Record<string, string>,
  extractedData: any
) {
  const resolvedForm = finalizeFormWithClarifications(
    clarificationQuestions,
    clarificationAnswers,
    formData
  );
  const expParts: string[] = [];
  if (resolvedForm.jobTitle || resolvedForm.company) {
    expParts.push(`${resolvedForm.jobTitle || ''}${resolvedForm.company ? ` at ${resolvedForm.company}` : ''}`.trim());
  }
  if (extractedData?.experience) {
    expParts.push(extractedData.experience);
  }
  if (resolvedForm.relevance) {
    expParts.push(resolvedForm.relevance);
  }
  const experienceText = Array.from(new Set(expParts.filter(Boolean))).join(' | ');
  const yearsExp = resolveClarifiedYears(
    clarificationQuestions,
    clarificationAnswers,
    extractedData?.years_experience,
    resolvedForm.relevance
  );

  const cleanedSkills = cleanRequirementList(resolvedForm.skills);
  const cleanedDegree = cleanRequirementInput(resolvedForm.degree);
  const cleanedCollege = cleanRequirementInput(resolvedForm.college);
  const cleanedCerts = cleanRequirementInput(extractedData?.certifications || '');

  return {
    raw_text: extractedData?.raw_text || "",
    clarification_responses: collectClarificationResponses(clarificationQuestions, clarificationAnswers),
    skills: cleanedSkills.join(', '),
    skills_list: cleanedSkills,
    job_title: cleanRequirementInput(resolvedForm.jobTitle),
    company: cleanRequirementInput(resolvedForm.company),
    experience: experienceText,
    relevance: cleanRequirementInput(resolvedForm.relevance),
    years_experience: yearsExp,
    work_experiences: extractedData?.work_experiences || [],
    education: [cleanedDegree, cleanedCollege].filter(Boolean).join(' - '),
    highest_degree: cleanedDegree,
    highest_educational_attainment: cleanRequirementInput(extractedData?.highest_educational_attainment || ''),
    education_entries: extractedData?.education_entries || [],
    certifications: cleanedCerts || undefined,
    fullname: resolvedForm.fullName,
    location: resolvedForm.location,
  };
}

export function deriveClarificationQuestions(
  state: any,
  formData?: {
    relevance?: string;
    jobTitle?: string;
    company?: string;
    degree?: string;
    skills?: string[];
  },
  jobOverride?: any,
  matchOverride?: any
): ClarificationQuestion[] {
  const activeJob = jobOverride || state?.job || null;
  const activeJobId = String(activeJob?.job_id || activeJob?.id || '');
  const rawMatch = matchOverride || state?.matchData || null;
  const matchJobId = extractMatchJobId(rawMatch);
  const activeMatch =
    rawMatch && (!activeJobId || !matchJobId || matchJobId === activeJobId) ? rawMatch : null;

  const normalizeQ = (q: any, idx: number, prefix: string): ClarificationQuestion => ({
    id: q.id || `${prefix}_${idx}`,
    field: q.field || 'general',
    question: q.question,
    type: q.type || 'text',
    placeholder: q.placeholder || 'Enter clarification details...',
    required: Boolean(q.required),
    domain: q.domain || 'General',
    reason: q.reason || '',
    job_id: q.job_id,
    job_title: q.job_title,
    items: q.items,
  });

  const resumeQuestionsRaw: any[] = Array.isArray(state?.extractedData?.clarification_questions)
    ? state.extractedData.clarification_questions
    : Array.isArray(state?.clarification_questions)
    ? state.clarification_questions
    : [];
  const resumeQuestions = resumeQuestionsRaw.map((q, i) => normalizeQ(q, i, 'clarify_resume'));

  const backendJobQuestionsRaw: any[] = Array.isArray(activeMatch?.followup_questions)
    ? activeMatch.followup_questions
    : Array.isArray(activeMatch?.clarification_questions)
    ? activeMatch.clarification_questions
    : [];

  const extractedYears = Number(state?.extractedData?.years_experience || 0);
  const relevanceStr =
    formData?.relevance || state?.experience?.relevance || state?.extractedData?.relevance || '';
  const candSkills: string[] = Array.isArray(formData?.skills)
    ? formData.skills
    : Array.isArray(state?.skills)
    ? state.skills
    : [];

  const hasExplicitYears = hasExplicitExperienceDuration(
    state?.extractedData,
    relevanceStr,
    extractedYears
  );

  const fallbackQuestions = buildFallbackJobQuestions(
    activeJob,
    activeMatch,
    candSkills,
    extractedYears,
    relevanceStr,
    state?.extractedData
  );
  const rawJobQuestions: ClarificationQuestion[] = backendJobQuestionsRaw.length > 0
    ? backendJobQuestionsRaw.map((q, i) => normalizeQ(q, i, 'clarify_job'))
    : fallbackQuestions;

  // Older/cached match responses may contain only some of the questions. A
  // nonempty response must never suppress coverage of the full job requirements.
  if (backendJobQuestionsRaw.length > 0) {
    const evidence = Array.isArray(activeMatch?.requirement_evaluations)
      ? activeMatch.requirement_evaluations : [];
    for (const fallback of fallbackQuestions.filter(q => q.type === 'requirement_group')) {
      const covered = new Set(rawJobQuestions
        .filter(q => q.field === fallback.field && q.type === 'requirement_group')
        .flatMap(q => (q.items || []).map(item => skillKey(item.requirement))));
      const items = (fallback.items || []).filter(item => !covered.has(skillKey(item.requirement)))
        .filter(item => !evidence.some((row: any) => row.field === fallback.field &&
          skillKey(String(row.requirement || '')) === skillKey(item.requirement) &&
          row.source === 'Resume' && row.status === 'Meets requirement'));
      if (!items.length) continue;
      const index = rawJobQuestions.findIndex(q => q.id === fallback.id && q.type === 'requirement_group');
      if (index >= 0) {
        rawJobQuestions[index] = { ...rawJobQuestions[index], items: [...(rawJobQuestions[index].items || []), ...items] };
      } else {
        // Legacy text prompts sometimes use the same id as the new group.
        // Keep their saved text separate from the group's JSON answers.
        const id = rawJobQuestions.some(q => q.id === fallback.id)
          ? `${fallback.id}_requirements` : fallback.id;
        rawJobQuestions.push({ ...fallback, id, items });
      }
    }
  }

  const jobQuestions = hasExplicitYears
    ? rawJobQuestions.filter((q) => q.field !== 'years_experience')
    : rawJobQuestions;

  const hasResumeContext = Boolean(
    state?.extractedData || state?.fileName || state?.rawText || state?.isSmart
  );

  if (
    hasResumeContext &&
    !hasExplicitYears &&
    !resumeQuestions.some((q) => q.field === 'years_experience') &&
    !jobQuestions.some((q) => q.field === 'years_experience')
  ) {
    resumeQuestions.unshift({
      id: 'clarify_manufacturing_experience_years',
      field: 'years_experience',
      question: 'How many years of manufacturing experience do you have?',
      type: 'number',
      placeholder: 'e.g. 2 (enter 0 if none)',
      required: true,
      domain: 'Manufacturing',
      reason: 'Resume did not clearly state total years of manufacturing or relevant experience.',
    });
  }

  if (
    hasResumeContext &&
    !resumeQuestions.some((q) => q.field === 'job_title_company') &&
    (!String(formData?.company ?? state?.experience?.company ?? '').trim() ||
      !String(formData?.jobTitle ?? state?.experience?.title ?? '').trim())
  ) {
    resumeQuestions.push({
      id: 'clarify_role_and_employer',
      field: 'job_title_company',
      question:
        'What was your specific job title, employer/company name, and main tasks in your recent role?',
      type: 'text',
      placeholder: 'e.g. Production Operator at Mariwasa Siam Ceramics',
      required: false,
      domain: 'General',
      reason: 'Recent job title or company name was not clearly identified.',
    });
  }

  // Merge job-specific questions first so job-tailored questions take precedence per field
  const combined = [...jobQuestions, ...resumeQuestions];
  const byField = new Map<string, ClarificationQuestion>();
  for (const q of combined) {
    if (!q.question) continue;
    const key = q.type === 'requirement_group' ? q.id : q.field || q.id;
    if (!byField.has(key)) {
      byField.set(key, q);
    }
  }
  return Array.from(byField.values());
}

export function applyClarificationAnswerToFormData<
  T extends {
    jobTitle: string;
    company: string;
    relevance: string;
    degree: string;
    college: string;
    skills: string[];
  }
>(question: ClarificationQuestion, rawValue: string, prev: T): T {
  const val = rawValue;
  if (question.field === 'years_experience') {
    const trimmed = val.trim();
    if (!trimmed) {
      return prev;
    }
    const yearsNum = Number(trimmed);
    const label = /manufacturing/i.test(question.question)
      ? 'years of manufacturing experience'
      : 'years of experience';
    const nextPhrase = !Number.isNaN(yearsNum) ? `${yearsNum} ${label}` : `${trimmed} ${label}`;
    const existing = (prev.relevance || '').trim();
    if (!existing) {
      return { ...prev, relevance: nextPhrase };
    }
    if (/^\d+(?:\.\d+)?\s*(?:\+?\s*)?years?\s+of(?:\s+manufacturing)?\s+experience/i.test(existing)) {
      return {
        ...prev,
        relevance: existing.replace(
          /^\d+(?:\.\d+)?\s*(?:\+?\s*)?years?\s+of(?:\s+manufacturing)?\s+experience/i,
          nextPhrase
        ),
      };
    }
    return { ...prev, relevance: `${nextPhrase} — ${existing}` };
  }

  if (question.field === 'job_title_company') {
    const trimmed = val.trim();
    if (!trimmed) return prev;
    const atParts = trimmed.split(/\s+at\s+|\s*@\s*/i);
    if (atParts.length >= 2) {
      const role = atParts[0].trim();
      const comp = atParts.slice(1).join(' at ').trim();
      return {
        ...prev,
        jobTitle: prev.jobTitle.trim() ? prev.jobTitle : role,
        company: prev.company.trim() ? prev.company : comp,
      };
    }
    return prev.company.trim() ? prev : { ...prev, company: trimmed };
  }

  if (question.field === 'education') {
    const trimmed = val.trim();
    if (!trimmed) return prev;
    const parts = trimmed.split(/\s*[-–—|]\s*/).map((p) => p.trim()).filter(Boolean);
    if (parts.length >= 2) {
      const yearOnlyRe = /^(?:19|20)\d{2}(?:\s*(?:to|present|current))?$/i;
      const collegeCandidate = parts.slice(1).find((p) => !yearOnlyRe.test(p)) || '';
      return {
        ...prev,
        degree: prev.degree.trim() ? prev.degree : parts[0],
        college: prev.college.trim() ? prev.college : collegeCandidate,
      };
    }
    return prev.degree.trim() ? prev : { ...prev, degree: trimmed };
  }

  return prev;
}

export function finalizeFormWithClarifications<
  T extends {
    jobTitle: string;
    company: string;
    relevance: string;
    degree: string;
    college: string;
    skills: string[];
  }
>(
  questions: ClarificationQuestion[],
  answers: Record<string, string>,
  formData: T
): T {
  let updated = { ...formData };
  for (const q of questions) {
    if (q.type === 'requirement_group') continue;
    const ans = (answers[q.id] || '').trim();
    if (!ans || isNoValueRequirement(ans)) continue;
    updated = applyClarificationAnswerToFormData(q, ans, updated);
    if (q.field === 'skills') {
      const newSkills = requirementItems(ans);
      const existingLower = new Set(updated.skills.map(skillKey));
      const merged = [...updated.skills];
      for (const sk of newSkills) {
        if (!existingLower.has(skillKey(sk))) {
          merged.push(sk);
          existingLower.add(skillKey(sk));
        }
      }
      updated = { ...updated, skills: merged };
    } else if (q.field === 'relevance') {
      const existing = (updated.relevance || '').trim();
      if (!existing.includes(ans)) {
        updated = {
          ...updated,
          relevance: existing ? `${existing} | ${ans}` : ans,
        };
      }
    }
  }
  return updated;
}

export function resolveClarifiedYears(
  questions: ClarificationQuestion[],
  answers: Record<string, string>,
  fallbackYears?: number | string | null,
  relevance?: string
): number {
  for (const q of questions) {
    if (q.field === 'years_experience') {
      const raw = (answers[q.id] ?? '').trim();
      if (raw !== '' && !Number.isNaN(Number(raw))) {
        return Math.max(0, Number(raw));
      }
    }
  }
  if (fallbackYears && Number(fallbackYears) > 0) {
    return Number(fallbackYears);
  }
  if (relevance) {
    const m = relevance.match(/(\d+(?:\.\d+)?)\s*(?:\+?\s*)?(?:years?|yrs?)/i);
    if (m) return Number(m[1]);
  }
  return 0;
}

export interface ExperienceGapStatus {
  belowMinimum: boolean;
  requiredYears: number;
  candidateYears: number;
  gapYears: number;
  message: string;
}

export function parseRequiredYearsFromJob(job?: any): number {
  if (job && 'experience_requirements' in job && isNoValueRequirement(job.experience_requirements)) {
    return 0;
  }
  const reqText = String(
    job?.experience_requirements || job?.description || ''
  ).trim();
  if (!reqText || isNoValueRequirement(reqText)) return 0;

  if (/^\d+$/.test(reqText)) {
    const val = Number(reqText);
    return val > 0 && val <= 50 ? val : 0;
  }

  const rangeMatch = reqText.match(
    /\b(\d+)\s*(?:-|–|—|to)\s*\d+\s*\+?\s*(?:years?|yrs?)\b/i
  );
  if (rangeMatch) {
    const val = Number(rangeMatch[1]);
    if (val > 0 && val <= 50) return val;
  }

  const explicitMatch =
    reqText.match(/(?:minimum|at\s+least|min)\s*(?:of\s+)?(\d+)\s*\+?\s*(?:years?|yrs?)/i) ||
    reqText.match(/\b(\d+)\s*\+?\s*(?:years?|yrs?)\b/i);
  if (explicitMatch) {
    const val = Number(explicitMatch[1]);
    if (val > 0 && val <= 50) return val;
  }
  return 0;
}

export function getExperienceGapStatus(
  matchData?: any,
  job?: any,
  candidateYearsOverride?: number | string | null
): ExperienceGapStatus | null {
  if (
    String(matchData?.experience_status || '').trim().toLowerCase() === 'not required' ||
    (job && 'experience_requirements' in job && isNoValueRequirement(job.experience_requirements))
  ) {
    return null;
  }
  const reqFromJob = parseRequiredYearsFromJob(job);
  const gapStr = String(matchData?.experience_gaps || '').trim();
  const parsedGap = gapStr.match(/Required:\s*(\d+)\s*yrs?\s*\|\s*Candidate:\s*(\d+)/i);

  const requiredYears = parsedGap ? Number(parsedGap[1]) : reqFromJob;
  const candidateYears =
    candidateYearsOverride !== undefined && candidateYearsOverride !== null && candidateYearsOverride !== ''
      ? Math.max(0, Number(candidateYearsOverride) || 0)
      : parsedGap
      ? Number(parsedGap[2])
      : 0;

  const flaggedBelow =
    Boolean(matchData?.experience_below_minimum) ||
    /below minimum/i.test(gapStr) ||
    /below minimum/i.test(String(matchData?.experience_reason || '')) ||
    (requiredYears > 0 && candidateYears < requiredYears);

  if (!flaggedBelow || (requiredYears <= 0 && !matchData?.experience_below_minimum)) {
    return null;
  }

  const effectiveReq = requiredYears > 0 ? requiredYears : 1;
  const gapYears =
    Number(matchData?.experience_gap_years) > 0
      ? Number(matchData.experience_gap_years)
      : Math.max(0, effectiveReq - candidateYears);

  const candLabel = `${candidateYears} yr${candidateYears !== 1 ? 's' : ''}`;
  const reqLabel = `${effectiveReq} yr${effectiveReq !== 1 ? 's' : ''}`;
  const shortLabel = `${gapYears} yr${gapYears !== 1 ? 's' : ''}`;
  const defaultMsg = `Gap reported: experience below minimum — Required: ${reqLabel} | Candidate: ${candLabel} (${shortLabel} short).`;

  return {
    belowMinimum: true,
    requiredYears: effectiveReq,
    candidateYears,
    gapYears,
    message: gapStr && /below minimum/i.test(gapStr) ? gapStr : defaultMsg,
  };
}
