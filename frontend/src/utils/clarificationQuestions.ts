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
}

const MFG_JOB_RE =
  /\b(?:manufactur\w*|production|factory|plant|operator|machin\w*|assembly|assembl\w*|warehouse|kiln|ceramic|welding|quality|qc|maintenance|industrial|technician)\b/i;

function buildFallbackJobQuestions(
  job: any,
  matchData: any,
  candidateSkills: string[],
  extractedYears: number,
  relevanceStr: string
): ClarificationQuestion[] {
  const jobTitle = String(job?.job_title || job?.title || '').trim();
  if (!jobTitle || jobTitle === 'Position') return [];

  const jobId = String(job?.job_id || job?.id || 'job');
  const slug = jobId.replace(/[^a-zA-Z0-9]+/g, '_').toLowerCase() || 'job';
  const department = String(job?.department || '').trim();
  const jobText = `${jobTitle} ${department} ${job?.description || ''}`;
  const isMfgJob = MFG_JOB_RE.test(jobText);

  const questions: ClarificationQuestion[] = [];

  const hasYears =
    extractedYears > 0 || /\b\d+(?:\.\d+)?\s*(?:\+?\s*)?(?:years?|yrs?)\b/i.test(relevanceStr);
  if (!hasYears || matchData?.experience_score === undefined || Number(matchData.experience_score) < 70) {
    questions.push({
      id: `clarify_${slug}_years_experience`,
      field: 'years_experience',
      job_id: jobId,
      job_title: jobTitle,
      domain: department || (isMfgJob ? 'Manufacturing' : 'General'),
      type: 'number',
      placeholder: 'e.g. 2',
      required: !hasYears,
      question: isMfgJob
        ? `How many years of manufacturing experience do you have for the ${jobTitle} role?`
        : department
        ? `How many years of ${jobTitle} (${department}) experience do you have?`
        : `How many years of ${jobTitle} experience do you have?`,
      reason: `Clarifying direct experience duration for ${jobTitle}.`,
    });
  }

  const missingFromMatch: string[] = Array.isArray(matchData?.missing_skills)
    ? matchData.missing_skills.slice(0, 5)
    : [];
  const rawReqSkills = String(job?.skills_requirements || '')
    .split(/[,;\n|]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const candLower = candidateSkills.map((s) => s.toLowerCase());
  const missingFromReq = rawReqSkills
    .filter((req) => !candLower.some((cs) => cs.includes(req.toLowerCase()) || req.toLowerCase().includes(cs)))
    .slice(0, 5);
  const missingSkills = missingFromMatch.length > 0 ? missingFromMatch : missingFromReq;

  if (missingSkills.length > 0) {
    questions.push({
      id: `clarify_${slug}_skills`,
      field: 'skills',
      job_id: jobId,
      job_title: jobTitle,
      domain: department || 'General',
      type: 'text',
      placeholder: `e.g. ${missingSkills.slice(0, 3).join(', ')}`,
      question: `For ${jobTitle}, which of these required skills have you used: ${missingSkills.join(', ')}?`,
      reason: `Required skills for ${jobTitle} not explicitly found in resume.`,
    });
  } else if (rawReqSkills.length > 0 || candidateSkills.length > 0) {
    const sample = (rawReqSkills.length > 0 ? rawReqSkills : candidateSkills).slice(0, 3);
    questions.push({
      id: `clarify_${slug}_skills`,
      field: 'skills',
      job_id: jobId,
      job_title: jobTitle,
      domain: department || 'General',
      type: 'text',
      placeholder: `Describe work using ${sample.slice(0, 2).join(', ')}`,
      question: `For ${jobTitle}, please highlight your practical work with ${sample.join(', ')}.`,
      reason: `Confirming practical proficiency for ${jobTitle}.`,
    });
  }

  const reqCerts = String(job?.certifications_requirements || '').trim();
  if (reqCerts && reqCerts.toLowerCase() !== 'none') {
    questions.push({
      id: `clarify_${slug}_certifications`,
      field: 'certifications',
      job_id: jobId,
      job_title: jobTitle,
      domain: department || 'General',
      type: 'text',
      placeholder: `e.g. ${reqCerts}`,
      question: `For ${jobTitle}, do you hold any preferred or required certifications/licenses (${reqCerts})?`,
      reason: `${jobTitle} specifies certification requirements.`,
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
  const expParts: string[] = [];
  if (formData.jobTitle || formData.company) {
    expParts.push(`${formData.jobTitle || ''}${formData.company ? ` at ${formData.company}` : ''}`.trim());
  }
  if (extractedData?.experience) {
    expParts.push(extractedData.experience);
  }
  if (formData.relevance) {
    expParts.push(formData.relevance);
  }
  const experienceText = Array.from(new Set(expParts.filter(Boolean))).join(' | ');
  const yearsExp = resolveClarifiedYears(
    clarificationQuestions,
    clarificationAnswers,
    extractedData?.years_experience,
    formData.relevance
  );

  return {
    skills: formData.skills.join(', '),
    skills_list: formData.skills,
    job_title: formData.jobTitle,
    company: formData.company,
    experience: experienceText,
    relevance: formData.relevance,
    years_experience: yearsExp,
    work_experiences: extractedData?.work_experiences || [],
    education: [formData.degree, formData.college].filter(Boolean).join(' - '),
    highest_degree: formData.degree,
    education_entries: extractedData?.education_entries || [],
    certifications: extractedData?.certifications || undefined,
    fullname: formData.fullName,
    location: formData.location,
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

  const jobQuestions: ClarificationQuestion[] =
    backendJobQuestionsRaw.length > 0
      ? backendJobQuestionsRaw.map((q, i) => normalizeQ(q, i, 'clarify_job'))
      : buildFallbackJobQuestions(activeJob, activeMatch, candSkills, extractedYears, relevanceStr);

  const hasResumeContext = Boolean(
    state?.extractedData || state?.fileName || state?.rawText || state?.isSmart
  );
  const hasExplicitYears =
    extractedYears > 0 || /\b\d+(?:\.\d+)?\s*(?:\+?\s*)?(?:years?|yrs?)\b/i.test(relevanceStr);

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
    const key = q.field || q.id;
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
    const parts = trimmed.split(/\s*[-–—|]\s*/);
    if (parts.length >= 2) {
      return {
        ...prev,
        degree: prev.degree.trim() ? prev.degree : parts[0].trim(),
        college: prev.college.trim() ? prev.college : parts[1].trim(),
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
    const ans = (answers[q.id] || '').trim();
    if (!ans) continue;
    updated = applyClarificationAnswerToFormData(q, ans, updated);
    if (q.field === 'skills') {
      const newSkills = ans
        .split(/[,;\n|]+/)
        .map((s) => s.trim())
        .filter(Boolean);
      const existingLower = new Set(updated.skills.map((s) => s.toLowerCase()));
      const merged = [...updated.skills];
      for (const sk of newSkills) {
        if (!existingLower.has(sk.toLowerCase())) {
          merged.push(sk);
          existingLower.add(sk.toLowerCase());
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
