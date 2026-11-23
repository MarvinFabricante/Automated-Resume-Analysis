import RequirementEvidence from '../../components/common/RequirementEvidence';
import styles from './CompareCandidates.module.css';
import React, { useState, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from '@/utils/navigation';
import { Helmet } from 'react-helmet-async';
import {
  Search, CheckCircle2, XCircle, Users, ArrowLeft, Award, TrendingUp, AlertTriangle,
  Mail, Phone, MapPin, Briefcase, Star, Zap, BarChart3, Trophy, Sparkles,
  Check, Plus, User, Table, LayoutGrid, SlidersHorizontal,
  Download, Printer, Save, FileText, GraduationCap, X, Scale
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useGetApplicationsQuery, useGetJobsQuery, useCompareCandidatesMutation } from '../../redux/api/apiSlice';
import HelpTooltip from '../../components/common/HelpTooltip';
import api, { getAssetUrl } from '../../services/api';
import { Job, Application } from '../../types';
import {
  isNoValueRequirement,
  resolveCriterionStatus,
  getCriterionStatusBadgeStyle,
  evaluateEducationClient,
  compareGradedCertificationClient,
} from '../../utils/criterionStatus';
import {
  EvaluationFilters,
  ParsedJobRequirements,
  RankedPersonItem,
  doesApplicationMatchJob,
  partitionAndSortPersonGroups,
  preparseJobRequirements,
  syncSelectedApplicationIdsForJob,
  syncActiveApplicationIdForJob,
} from '../../utils/compareSorting';

interface CandidateComparisonData extends Partial<Application> {
  id: number;
  name: string;
  preferredJob?: string;
  applied_job_title?: string;
  applied_job_id?: number;
  applicant_id?: number;
  email?: string;
  phone?: string;
  location?: string;
  company?: string;
  job_title?: string;
  relevance?: string;
  skills_reason?: string;
  experience_reason?: string;
  education_reason?: string;
  certifications_reason?: string;
  skills_status?: string;
  experience_status?: string;
  education_status?: string;
  certifications_status?: string;
  required_degree?: string;
  candidate_degree?: string;
  required_certifications?: string;
  skills?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
  requirement_evaluations?: import('../../components/common/RequirementEvidence').RequirementEvaluation[];
  transferable_skills?: string[];
  strengths?: string[];
  weaknesses?: string[];
  recommendations?: string[];
  skillsScore?: number;
  experienceScore?: number;
  educationScore?: number;
  education_score?: number;
  education_needs_manual_review?: boolean;
  highest_educational_attainment?: string;
  degree?: string;
  certificationsScore?: number;
  certifications_score?: number;
  candidate_certifications?: string;
  certifications?: string;
  completeness_score?: number;
  completeness_status?: string;
  missing_sections?: string[];
  hr_shortlist_notes?: string;
  matchScore?: number;
  ai_summary?: string;
  profileImage?: string;
  isRuleBased?: boolean;
}

const getAvatarUrl = (candidate: CandidateComparisonData | null): string => {
  if (!candidate) return "";
  const profileImage = candidate.profileImage;
  return profileImage
    ? getAssetUrl(profileImage)
    : (`https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`);
};

const calculateRuleBasedScore = (
  candidate: CandidateComparisonData,
  job: Job | undefined,
  filters: EvaluationFilters,
  parsedJob?: ParsedJobRequirements
): CandidateComparisonData => {
  let skillsScore = 0;
  let expScore = 0;
  let eduScore = candidate.education_score ?? candidate.educationScore ?? 0;
  let certScore = 0;
  let eduEval: ReturnType<typeof evaluateEducationClient> | null = null;
  let matchedSkills = candidate.matched_skills || [];
  let missingSkills = candidate.missing_skills || [];

  if (job) {
    const req = parsedJob || preparseJobRequirements(job);

    // 1. Skills Matching
    const jobSkills = req.jobSkills;

    const rawCandSkills = Array.isArray(candidate.skills)
      ? candidate.skills
      : typeof candidate.skills === 'string'
        ? (candidate.skills as string).split(/[,;\n•●◦‣|]+|\s+\/\s+/)
        : [];

    const normSkill = (val: string) =>
      String(val).replace(/\t/g, ' ').replace(/[-–—]/g, ' ').replace(/\s+/g, ' ').trim().toLowerCase();

    const candSkillTokens = new Set<string>();
    rawCandSkills.forEach(s => {
      const clean = normSkill(s);
      if (clean) {
        candSkillTokens.add(clean);
      }
    });

    if (Array.isArray(candidate.matched_skills)) {
      candidate.matched_skills.forEach(s => {
        const clean = normSkill(s);
        if (clean) candSkillTokens.add(clean);
      });
    }

    matchedSkills = [];
    missingSkills = [];

    if (jobSkills.length > 0) {
      let matchCount = 0;
      jobSkills.forEach(reqSkill => {
        const normReq = normSkill(reqSkill);
        const hasSkill = Boolean(normReq && candSkillTokens.has(normReq));
        if (hasSkill) {
          matchCount++;
          matchedSkills.push(reqSkill);
        } else {
          missingSkills.push(reqSkill);
        }
      });
      skillsScore = Math.round((matchCount / jobSkills.length) * 100);
    } else {
      skillsScore = 100;
    }

    // 2. Experience Matching (>= hierarchy: more experience never penalizes)
    const jobExp = req.jobExp;
    const candExpParts = [
      candidate.relevance,
      candidate.relevant_experience,
      candidate.experience_reason,
      candidate.preferredJob,
      candidate.company,
      candidate.job_title,
      Array.isArray(candidate.work_experiences)
        ? candidate.work_experiences.map((w: any) => `${w?.job_title || ''} ${w?.company_name || ''} ${w?.description || ''}`).join(' ')
        : ''
    ].filter(Boolean).join(' ').toLowerCase();

    if (jobExp) {
      const reqYears = req.reqYears;

      let candYears = 0;
      if (candidate.total_experience_months && candidate.total_experience_months > 0) {
        candYears = Math.round(candidate.total_experience_months / 12);
      } else {
        const candYearsMatch = candExpParts.match(/(\d+)\+?\s*(?:years?|yrs?)/i);
        if (candYearsMatch) candYears = parseInt(candYearsMatch[1], 10);
      }

      const expKeywords = req.expKeywords;

      let keywordScore = 0;
      if (expKeywords.length > 0) {
        const matchCount = expKeywords.filter(kw => candExpParts.includes(kw)).length;
        keywordScore = Math.round((matchCount / expKeywords.length) * 100);
      } else {
        keywordScore = 80;
      }

      if (reqYears > 0 && candYears > 0) {
        const yearsScore = candYears >= reqYears ? 100 : Math.min(100, Math.round((candYears / reqYears) * 100));
        expScore = expKeywords.length > 0 ? Math.round((yearsScore * 0.5) + (keywordScore * 0.5)) : yearsScore;
      } else if (reqYears > 0 && candYears === 0) {
        expScore = keywordScore > 0 ? keywordScore : (candidate.experienceScore || candidate.experience_score || 0);
      } else {
        expScore = keywordScore > 0 ? keywordScore : (candidate.experienceScore || candidate.experience_score || (candExpParts.length > 10 ? 75 : 0));
      }
    } else {
      expScore = 100;
    }

    // 3. Education Matching (shared 1-8 hierarchy + ongoing + manual review rules)
    const candEduText = [
      candidate.candidate_degree,
      candidate.degree,
      candidate.highest_educational_attainment,
    ]
      .filter((v) => !isNoValueRequirement(v))
      .join(' | ');
    eduEval = evaluateEducationClient(candEduText, req.jobEdu, candidate.education_entries);
    eduScore = eduEval.score;

    // 4. Certifications Matching (including graded certs like NC I-IV, SO1-4, Six Sigma belts)
    const hasCertReq = req.hasCertReq;
    const jobCert = req.jobCert;
    const rawCandCert = [
      candidate.candidate_certifications,
      candidate.certifications,
    ]
      .filter((v) => !isNoValueRequirement(v))
      .join(', ');
    const candCert = rawCandCert.toLowerCase();

    if (hasCertReq) {
      const candItems = rawCandCert.split(/[|,\n;•]+/).map((s) => s.trim()).filter(Boolean);
      let gradedScore: number | null = null;
      for (const item of candItems) {
        const graded = compareGradedCertificationClient(item, jobCert);
        if (graded !== null) {
          gradedScore = gradedScore === null ? graded.score : Math.max(gradedScore, graded.score);
        }
      }
      if (gradedScore !== null) {
        certScore = gradedScore;
      } else {
        const certKeywords = req.certKeywords;
        if (certKeywords.length > 0) {
          const matchCount = certKeywords.filter(kw => candCert.includes(kw)).length;
          certScore = Math.round((matchCount / certKeywords.length) * 100);
        } else {
          certScore = jobCert.split(/[\s,]+/).some(w => w.length > 3 && candCert.includes(w)) ? 100 : 0;
        }
      }
    } else {
      // Certification not required for this job — automatic full credit at normal weight
      certScore = 100;
    }
  } else {
    // Original AI Scores
    skillsScore = candidate.skillsScore ?? candidate.skills_score ?? 0;
    expScore = candidate.experienceScore ?? candidate.experience_score ?? 0;
    eduScore = candidate.education_score ?? candidate.educationScore ?? 0;
    certScore = candidate.certifications_score ?? candidate.certificationsScore ?? 0;
  }

  const evidence = candidate.requirement_evaluations || [];
  const skillEvidence = evidence.filter(item => item.field === 'skills');
  if (skillEvidence.length) {
    matchedSkills = skillEvidence.filter(item => item.status === 'Meets requirement').map(item => item.requirement);
    missingSkills = skillEvidence.filter(item => item.status === 'Does not meet').map(item => item.requirement);
    skillsScore = Math.round(matchedSkills.length / skillEvidence.length * 100);
  }
  if (evidence.some(item => item.field === 'experience')) expScore = candidate.experience_score ?? candidate.experienceScore ?? 0;
  if (evidence.some(item => item.field === 'certifications')) certScore = candidate.certifications_score ?? candidate.certificationsScore ?? 0;

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
  const compScore = candidate.completeness_score ?? 100;
  if (job) {
    totalWeight += 20;
    rawScore += (eduScore * 15) + (compScore * 5);
  }

  let matchScore = 0;
  const originalScore = candidate.matchScore ?? candidate.match_score ?? 0;

  if (!job && originalScore > 0) {
    // When using original AI match scores, preserve the existing score unless specific filters are toggled
    if ((filters?.skills && filters?.experience && filters?.certifications) || (skillsScore === 0 && expScore === 0 && certScore === 0)) {
      matchScore = Math.round(originalScore);
    } else if (totalWeight > 0 && (skillsScore > 0 || expScore > 0 || certScore > 0)) {
      matchScore = Math.round(rawScore / totalWeight);
    } else {
      matchScore = Math.round(originalScore);
    }
  } else {
    matchScore = totalWeight > 0 ? Math.round(rawScore / totalWeight) : 0;
  }

  return {
    ...candidate,
    matchScore,
    skillsScore,
    experienceScore: expScore,
    educationScore: eduScore,
    education_score: eduScore,
    ...(eduEval
      ? {
          education_status: eduEval.status,
          education_reason: eduEval.reason,
          required_degree: eduEval.requiredEducation,
          candidate_degree: eduEval.candidateEducation,
          education_needs_manual_review: eduEval.status === 'Needs manual review',
        }
      : {}),
    certificationsScore: certScore,
    matched_skills: matchedSkills,
    missing_skills: missingSkills,
    isRuleBased: !!job
  };
};

const EMPTY_CANDIDATES: CandidateComparisonData[] = [];
const EMPTY_JOBS: Job[] = [];

const isSamePerson = (c1: CandidateComparisonData, c2: CandidateComparisonData): boolean => {
  if (c1.id === c2.id) return true;
  if (c1.applicant_id && c2.applicant_id && c1.applicant_id === c2.applicant_id) return true;
  const email1 = (c1.email || (c1 as any).candidate_email || '').trim().toLowerCase();
  const email2 = (c2.email || (c2 as any).candidate_email || '').trim().toLowerCase();
  if (email1 && email2 && email1 === email2) return true;
  const phone1 = (c1.phone || '').replace(/[^0-9]/g, '');
  const phone2 = (c2.phone || '').replace(/[^0-9]/g, '');
  if (phone1 && phone2 && phone1.length >= 7 && phone1 === phone2) return true;
  return false;
};

const CompareCandidates: React.FC = () => {
  const { data: candidates = EMPTY_CANDIDATES, isLoading, isError: candidatesError, refetch: refetchCandidates } = useGetApplicationsQuery();
  const { data: jobs = EMPTY_JOBS } = useGetJobsQuery();
  const listScrollRef = useRef<HTMLDivElement | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchParams] = useSearchParams();
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<number[]>([]);
  const [activeCandidateId, setActiveCandidateId] = useState<number | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [selectedRefJobId, setSelectedRefJobId] = useState<string>("");
  const [personSelectedAppMap, setPersonSelectedAppMap] = useState<Record<string, number>>({});
  const [evaluationFilters, setEvaluationFilters] = useState<EvaluationFilters>({
    skills: true,
    experience: true,
    certifications: true
  });

  const [compareCandidatesMutation, { data: serverComparison, isLoading: isComparingServer, error: serverCompareError }] = useCompareCandidatesMutation();

  // Mobile responsiveness helpers
  const [mobileTab, setMobileTab] = useState<'list' | 'profile'>('list'); // 'list' | 'profile' for mobile selection view
  const [compareViewMode, setCompareViewMode] = useState<'table' | 'cards'>('table'); // 'table' | 'cards' for comparison view
  const [scorecardFilter, setScorecardFilter] = useState<string | number>('all'); // 'all' | candidateId for mobile scorecard view

  // Pre-load candidates from query param (e.g., ?ids=1,2,3)
  useEffect(() => {
    const idsParam = searchParams.get('ids');
    if (idsParam) {
      const ids = idsParam.split(',').map(id => parseInt(id.trim(), 10)).filter(id => !isNaN(id));
      if (ids.length > 0) {
        setSelectedCandidateIds(ids);
        setIsComparing(true);
        setActiveCandidateId(ids[0]);
      }
    }
  }, [searchParams]);

  // Synchronize reference position from server comparison
  useEffect(() => {
    if (isComparing && serverComparison?.reference_job?.id && !selectedRefJobId) {
      setSelectedRefJobId(String(serverComparison.reference_job.id));
    }
  }, [isComparing, serverComparison, selectedRefJobId]);

  // Trigger server-side cross-job re-scoring when comparing
  useEffect(() => {
    if (isComparing && selectedCandidateIds.length >= 2) {
      const refJobIdValue = selectedRefJobId || selectedJobId;
      compareCandidatesMutation({
        application_ids: selectedCandidateIds,
        reference_job_id: refJobIdValue ? parseInt(refJobIdValue, 10) : undefined,
      });
    }
  }, [isComparing, selectedCandidateIds, selectedRefJobId, selectedJobId, compareCandidatesMutation]);

  const handleSelectedJobChange = (nextJobId: string) => {
    const nextJob = nextJobId
      ? (jobs as Job[]).find(j => String(j.id) === String(nextJobId))
      : undefined;

    setSelectedJobId(nextJobId);
    setSelectedRefJobId(nextJobId);
    setPersonSelectedAppMap({});
    setSelectedCandidateIds(prev =>
      syncSelectedApplicationIdsForJob({
        selectedIds: prev,
        candidates: candidates as CandidateComparisonData[],
        nextJob,
        evaluationFilters,
        isSamePerson,
      })
    );
    setActiveCandidateId(prev =>
      syncActiveApplicationIdForJob({
        activeId: prev,
        candidates: candidates as CandidateComparisonData[],
        nextJob,
        evaluationFilters,
        isSamePerson,
      })
    );
    if (listScrollRef.current) {
      listScrollRef.current.scrollTop = 0;
    }
  };

  const selectedJob = useMemo(
    () => (jobs as Job[]).find(j => String(j.id) === String(selectedJobId)),
    [jobs, selectedJobId]
  );

  const parsedSelectedJob = useMemo(
    () => (selectedJob ? preparseJobRequirements(selectedJob) : undefined),
    [selectedJob]
  );

  // Filter candidates based on search
  const filteredCandidates = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return candidates as CandidateComparisonData[];
    return (candidates as CandidateComparisonData[]).filter(c => {
      const skillsMatch = Array.isArray(c.skills) && c.skills.some(s => String(s || '').toLowerCase().includes(q));
      const roleText = (c.preferredJob || c.applied_job_title || '').toLowerCase();
      return (
        (c.name || '').toLowerCase().includes(q) ||
        roleText.includes(q) ||
        skillsMatch
      );
    });
  }, [candidates, searchQuery]);

  // Group candidates into unique persons (enforce comparing different people only)
  interface PersonGroup {
    personKey: string;
    primaryApplicantId?: number;
    name: string;
    email: string;
    phone: string;
    applications: CandidateComparisonData[];
  }

  const personGroups = useMemo<PersonGroup[]>(() => {
    const groups: { [key: string]: PersonGroup } = {};
    filteredCandidates.forEach(cand => {
      const rawEmail = (cand.email || (cand as any).candidate_email || '').trim().toLowerCase();
      const rawPhone = (cand.phone || '').replace(/[^0-9]/g, '');
      const key = cand.applicant_id
        ? `uid_${cand.applicant_id}`
        : (rawEmail ? `email_${rawEmail}` : (rawPhone.length >= 7 ? `phone_${rawPhone}` : `id_${cand.id}`));

      if (!groups[key]) {
        groups[key] = {
          personKey: key,
          primaryApplicantId: cand.applicant_id,
          name: cand.name,
          email: cand.email || (cand as any).candidate_email || '',
          phone: cand.phone || '',
          applications: [cand]
        };
      } else {
        groups[key].applications.push(cand);
      }
    });
    return Object.values(groups);
  }, [filteredCandidates]);

  // Partition into applicants for the selected job (sorted by score desc) and other applicants
  const { appliedToJob, otherApplicants } = useMemo(
    () =>
      partitionAndSortPersonGroups<CandidateComparisonData, PersonGroup>({
        personGroups,
        selectedJob,
        parsedJob: parsedSelectedJob,
        evaluationFilters,
        personSelectedAppMap,
        scoreAgainstJob: (app, job, filters, parsedJob) =>
          calculateRuleBasedScore(app, job, filters, parsedJob).matchScore || 0,
      }),
    [personGroups, selectedJob, parsedSelectedJob, evaluationFilters, personSelectedAppMap]
  );

  // Set the first candidate as active by default if not set
  useEffect(() => {
    if (filteredCandidates.length > 0 && !activeCandidateId) {
      const firstItem = appliedToJob[0] || otherApplicants[0];
      setActiveCandidateId(firstItem ? firstItem.effectiveApp.id : filteredCandidates[0].id);
    }
  }, [filteredCandidates, activeCandidateId, appliedToJob, otherApplicants]);

  const activeCandidate = useMemo(() => {
    return (candidates as CandidateComparisonData[]).find(c => c.id === activeCandidateId) || filteredCandidates[0] || null;
  }, [candidates, activeCandidateId, filteredCandidates]);

  const activeCandidateAppliedToSelectedJob = useMemo(() => {
    return Boolean(activeCandidate && selectedJob && doesApplicationMatchJob(activeCandidate, selectedJob));
  }, [activeCandidate, selectedJob]);

  const activeCandidateEvaluated = useMemo(() => {
    if (!activeCandidate) return null;
    if (selectedJob && !activeCandidateAppliedToSelectedJob) {
      return calculateRuleBasedScore(activeCandidate, selectedJob, evaluationFilters, parsedSelectedJob);
    }
    return calculateRuleBasedScore(activeCandidate, undefined, evaluationFilters);
  }, [activeCandidate, selectedJob, parsedSelectedJob, activeCandidateAppliedToSelectedJob, evaluationFilters]);

  const toggleSelection = (id: number) => {
    const candidateToToggle = (candidates as CandidateComparisonData[]).find(c => c.id === id);
    if (!candidateToToggle) return;

    if (selectedCandidateIds.includes(id)) {
      setSelectedCandidateIds(prev => prev.filter(cId => cId !== id));
      return;
    }

    // Check if another application belonging to the same person is already in the comparison
    const existingConflict = (candidates as CandidateComparisonData[]).find(c =>
      selectedCandidateIds.includes(c.id) && c.id !== id && isSamePerson(candidateToToggle, c)
    );

    if (existingConflict) {
      alert("This applicant is already in the comparison. Comparison is for choosing between different people.");
      return;
    }

    setSelectedCandidateIds(prev => [...prev, id]);
  };

  const togglePersonSelection = (person: PersonGroup, preferredAppId?: number) => {
    const isSel = person.applications.some(a => selectedCandidateIds.includes(a.id));
    if (isSel) {
      const personAppIds = new Set(person.applications.map(a => a.id));
      setSelectedCandidateIds(prev => prev.filter(id => !personAppIds.has(id)));
    } else {
      const chosenId = preferredAppId || personSelectedAppMap[person.personKey] || person.applications[0].id;
      const personAppIds = new Set(person.applications.map(a => a.id));
      setSelectedCandidateIds(prev => [...prev.filter(id => !personAppIds.has(id)), chosenId]);
    }
  };

  const clearSelected = () => {
    setSelectedCandidateIds([]);
  };

  const selectedCandidatesData = useMemo(() => {
    // If server comparison returned candidates scored against reference job, baseline against that
    if (serverComparison?.candidates && serverComparison.candidates.length > 0) {
      const mapped = serverComparison.candidates.map((sc: any) => {
        const localApp = (candidates as CandidateComparisonData[]).find(c => c.id === sc.application_id);
        return {
          ...(localApp || {}),
          id: sc.application_id,
          name: sc.name,
          email: sc.email,
          phone: sc.phone,
          location: sc.location,
          preferredJob: sc.applied_job_title,
          applied_job_title: sc.applied_job_title,
          applied_job_id: sc.applied_job_id,
          matchScore: sc.match_score,
          skillsScore: sc.skills_score,
          experienceScore: sc.experience_score,
          educationScore: sc.education_score,
          education_score: sc.education_score,
          certificationsScore: sc.certifications_score,
          completeness_score: sc.completeness_score,
          skills_status: sc.skills_status || localApp?.skills_status,
          experience_status: sc.experience_status || localApp?.experience_status,
          education_status: sc.education_status || localApp?.education_status,
          education_needs_manual_review: Boolean(sc.education_needs_manual_review ?? localApp?.education_needs_manual_review),
          certifications_status: sc.certifications_status || localApp?.certifications_status,
          skills_reason: sc.skills_reason || localApp?.skills_reason,
          experience_reason: sc.experience_reason || localApp?.experience_reason,
          education_reason: sc.education_reason || localApp?.education_reason,
          certifications_reason: sc.certifications_reason || localApp?.certifications_reason,
          required_degree: sc.required_degree || localApp?.required_degree,
          candidate_degree: sc.candidate_degree || localApp?.candidate_degree,
          required_certifications: sc.required_certifications || localApp?.required_certifications,
          matched_skills: sc.matched_skills || [],
          missing_skills: sc.missing_skills || [],
          requirement_evaluations: sc.requirement_evaluations || localApp?.requirement_evaluations || [],
          transferable_skills: sc.transferable_skills || [],
          ai_summary: sc.ai_summary,
          strengths: sc.strengths,
          weaknesses: sc.weaknesses,
          status: sc.status,
          highest_educational_attainment: sc.degree || sc.candidate_degree || localApp?.highest_educational_attainment,
          candidate_certifications: !isNoValueRequirement(sc.certifications) ? sc.certifications : (!isNoValueRequirement(localApp?.candidate_certifications) ? localApp?.candidate_certifications : undefined),
          relevance: sc.relevance || localApp?.relevance,
        };
      });
      return [...mapped].sort((a: any, b: any) => (b.matchScore || 0) - (a.matchScore || 0));
    }

    const selected = (candidates as CandidateComparisonData[]).filter(c => selectedCandidateIds.includes(c.id));
    const fallbackRefJob = (jobs as Job[]).find(j => j.id === parseInt(selectedRefJobId || selectedJobId) || String(j.id) === (selectedRefJobId || selectedJobId));

    // Calculate score to reflect filter preferences even if job isn't selected
    const scoredCandidates = selected.map(c => calculateRuleBasedScore(c, fallbackRefJob, evaluationFilters));

    // Sort by match score descending to automatically rank them
    return [...scoredCandidates].sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));
  }, [serverComparison, candidates, selectedCandidateIds, jobs, selectedRefJobId, selectedJobId, evaluationFilters]);

  const isAllZero = useMemo(() => {
    return selectedCandidatesData.length > 0 && selectedCandidatesData.every(c => (c.matchScore || 0) === 0);
  }, [selectedCandidatesData]);

  const hasTiedWinner = useMemo(() => {
    if (selectedCandidatesData.length < 2 || isAllZero) return false;
    return (selectedCandidatesData[0].matchScore || 0) > 0 &&
      selectedCandidatesData[0].matchScore === selectedCandidatesData[1].matchScore;
  }, [selectedCandidatesData, isAllZero]);

  const categoryWinners = useMemo(() => {
    if (selectedCandidatesData.length === 0 || isAllZero) return {};

    const getWinner = (key: keyof CandidateComparisonData) => {
      let maxScore = 0;
      let winnerCandidate: CandidateComparisonData | null = null;
      selectedCandidatesData.forEach(c => {
        const val = Number(c[key]) || 0;
        if (val > maxScore) {
          maxScore = val;
          winnerCandidate = c;
        }
      });
      return maxScore > 0 ? winnerCandidate : null;
    };

    return {
      match: getWinner('matchScore'),
      skills: getWinner('skillsScore'),
      experience: getWinner('experienceScore'),
      education: getWinner('education_score'),
      certifications: getWinner('certificationsScore'),
      completeness: getWinner('completeness_score'),
    };
  }, [selectedCandidatesData, isAllZero]);

  const [candidateNotes, setCandidateNotes] = useState<{ [id: number]: string }>({});
  const [savingNotes, setSavingNotes] = useState<{ [id: number]: boolean }>({});
  const [savedSuccess, setSavedSuccess] = useState<{ [id: number]: boolean }>({});

  useEffect(() => {
    selectedCandidatesData.forEach(c => {
      if (c.hr_shortlist_notes && candidateNotes[c.id] === undefined) {
        setCandidateNotes(prev => ({ ...prev, [c.id]: c.hr_shortlist_notes || '' }));
      }
    });
  }, [selectedCandidatesData]);

  const handleSaveNote = async (candidateId: number) => {
    const note = candidateNotes[candidateId] || '';
    try {
      setSavingNotes(prev => ({ ...prev, [candidateId]: true }));
      await api.patch(`/applications/${candidateId}/notes`, { hr_shortlist_notes: note });
      setSavedSuccess(prev => ({ ...prev, [candidateId]: true }));
      setTimeout(() => {
        setSavedSuccess(prev => ({ ...prev, [candidateId]: false }));
      }, 2500);
    } catch (err) {
      console.error("Failed to save shortlist note:", err);
    } finally {
      setSavingNotes(prev => ({ ...prev, [candidateId]: false }));
    }
  };

  const exportToCSV = () => {
    if (selectedCandidatesData.length === 0) return;
    const refTitle = serverComparison?.reference_job?.job_title || 'Reference Position';
    const headers = ['Criteria', ...selectedCandidatesData.map((c, i) => `"${c.name} (Rank #${i + 1})"`)];
    const rows = [
      ['Reference Evaluation Position', `"${refTitle}"`],
      ...(serverComparison?.note ? [['Cross-Position Comparison Notice', `"${serverComparison.note}"`]] : []),
      ['Role / Position Applied For', ...selectedCandidatesData.map(c => `"${c.applied_job_title || c.preferredJob || c.job_title || ''}"`)],
      ['Overall Match Score', ...selectedCandidatesData.map(c => `${c.matchScore || 0}%`)],
      ['Skills Match Score', ...selectedCandidatesData.map(c => `${c.skillsScore || 0}%`)],
      ['Work Experience Score', ...selectedCandidatesData.map(c => `${c.experienceScore || 0}%`)],
      ['Educational Attainment', ...selectedCandidatesData.map(c => `"${c.highest_educational_attainment || c.degree || 'Not specified'}"`)],
      ['Education Score', ...selectedCandidatesData.map(c => `${c.education_score || 0}%`)],
      ['Certifications Score', ...selectedCandidatesData.map(c => `${c.certificationsScore || 0}%`)],
      ['Resume Completeness', ...selectedCandidatesData.map(c => `${c.completeness_score || 100}% (${c.completeness_status || 'Complete'})`)],
      ['Matched Skills', ...selectedCandidatesData.map(c => `"${(c.matched_skills || []).join('; ')}"`)],
      ['Transferable Skills', ...selectedCandidatesData.map(c => `"${(c.transferable_skills || []).join('; ')}"`)],
      ['Candidate Email', ...selectedCandidatesData.map(c => `"${c.email || ''}"`)],
      ['Candidate Phone', ...selectedCandidatesData.map(c => `"${c.phone || ''}"`)],
      ['HR Shortlisting Notes', ...selectedCandidatesData.map(c => `"${(candidateNotes[c.id] ?? c.hr_shortlist_notes ?? '').replace(/"/g, '""')}"`)],
    ];

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `Candidate_Comparison_Matrix_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportToPDF = () => {
    window.print();
  };

  const winner = useMemo(() => {
    if (selectedCandidatesData.length === 0) return null;
    return selectedCandidatesData[0]; // Highest score
  }, [selectedCandidatesData]);

  const renderComparisonView = () => {
    if (selectedCandidatesData.length === 0 || !winner) return (
      <div className={styles.emptyState} role="status">
        <Users size={32} /><h1>{isLoading ? 'Loading your comparison…' : 'Choose candidates to compare'}</h1>
        <p>{isLoading ? 'Preparing the selected profiles.' : 'Select at least two available candidates from the directory.'}</p>
        <button type="button" onClick={() => setIsComparing(false)}>Back to candidate selection</button>
      </div>
    );

    const displayedCandidatesInScorecards = scorecardFilter === 'all'
      ? selectedCandidatesData
      : selectedCandidatesData.filter(c => c.id === scorecardFilter);

    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
        {/* Navigation & Header */}
        <div className="mb-4 sm:mb-8">
          <button
            onClick={() => setIsComparing(false)}
            className="inline-flex items-center text-xs sm:text-sm font-bold text-slate-500 hover:text-[#D60041] transition-colors mb-2.5 sm:mb-4 group cursor-pointer"
          >
            <div className="p-1.5 bg-slate-100 rounded-lg group-hover:bg-rose-50 group-hover:text-[#D60041] mr-2 transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </div>
            Back to Candidate Selection
          </button>

          <div className={styles.pageHeader}>
            <div>
              <h1>
                Candidate comparison
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5 sm:mt-1">
                Comparing {selectedCandidatesData.length} selected candidates for role suitability.
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              <div className="px-3 py-1.5 bg-rose-50 border border-rose-100 rounded-xl text-xs font-bold text-[#D60041] flex items-center gap-1.5 shadow-2xs">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Match score overview</span>
              </div>
            </div>
          </div>

          {/* Reference Position Selector */}
          <div className={styles.referenceBar}>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-rose-50 text-[#D60041] flex items-center justify-center shrink-0">
                <Briefcase size={16} />
              </div>
              <div>
                <label htmlFor="compare-for-select" className="text-xs font-semibold text-slate-800 flex items-center gap-1.5">
                  Compare for Reference Position:
                  <HelpTooltip text="All candidates are evaluated and scored against this reference role, including transferable skills." />
                </label>
                <p className="text-xs text-slate-500 font-medium">Scores and category rankings adapt to this position</p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <select
                id="compare-for-select"
                value={selectedRefJobId || serverComparison?.reference_job?.id || ''}
                onChange={(e) => setSelectedRefJobId(e.target.value)}
                className="px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-xl text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-[#D60041] cursor-pointer min-w-[200px]"
              >
                {(jobs as Job[]).map((job) => (
                  <option key={job.id} value={job.id}>
                    {job.title || (job as any).job_title}
                  </option>
                ))}
              </select>
              {isComparingServer && (
                <span role="status" className="text-xs text-slate-500 shrink-0">Updating scores…</span>
              )}
            </div>
          </div>

          {/* Cross-Job Comparison Note */}
          {(serverComparison?.is_cross_job || serverComparison?.note) && (
            <div className="mt-4 bg-amber-50/90 border border-amber-200 rounded-2xl p-4 flex items-start gap-3 shadow-2xs">
              <div className="w-7 h-7 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 mt-0.5">
                <Zap size={15} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-amber-900">Cross-Position Comparison Notice</p>
                <p className="text-xs text-amber-800 mt-0.5">
                  {serverComparison?.note || `Candidates applied for different positions. Scores are based on ${serverComparison?.reference_job?.job_title || 'the reference position'} and include transferable skills.`}
                </p>
              </div>
            </div>
          )}

          {serverCompareError && (
            <div className="mt-4 bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-center gap-3 text-rose-800 text-xs font-bold">
              <AlertTriangle size={16} className="text-[#D60041] shrink-0" />
              <span>{(serverCompareError as any)?.data?.detail || 'Comparison error: Candidates must be different people.'}</span>
            </div>
          )}
        </div>

        <section className={styles.resultSummary} aria-label="Comparison summary" aria-busy={isComparingServer}>
          <div>
            <p className={styles.summaryEyebrow}><Scale size={16} /> COMPARISON INSIGHT</p>
            <h2>{isAllZero ? 'Review the evidence behind each match' : hasTiedWinner ? 'A closer look at your leading candidates' : `${winner.name} has the highest match score`}</h2>
            <p>{isAllZero
              ? 'All selected candidates currently have a 0% match score. Review the reference role and individual criteria below.'
              : hasTiedWinner
                ? `The highest score is shared at ${winner.matchScore}%. Compare skills, experience, and qualifications to see where candidates differ.`
                : 'Explore the strengths, gaps, and qualifications behind the scores before recording your assessment.'}</p>
          </div>
          <div className={styles.summaryNumbers}>
            <div><strong>{selectedCandidatesData.length}</strong><span>Candidates compared</span></div>
            <div><strong>{winner.matchScore || 0}<small>%</small></strong><span>Highest match score</span></div>
          </div>
        </section>

        {/* Category Winners Filter Display */}
        {(categoryWinners.skills || categoryWinners.experience || categoryWinners.education || categoryWinners.certifications) && (
          <div className={styles.categoryHighlights}>
            {evaluationFilters.skills && categoryWinners.skills && (
              <div className="bg-blue-50/60 border border-blue-100 rounded-2xl p-3 sm:p-4 flex items-center justify-between shadow-2xs">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 bg-blue-100 text-blue-600 rounded-xl shrink-0">
                    <Zap className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Top Skills Match</p>
                    <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.skills.name}</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-blue-100/80 text-blue-700 rounded-lg text-xs font-semibold shrink-0">
                  {categoryWinners.skills.skillsScore}%
                </span>
              </div>
            )}
            {evaluationFilters.experience && categoryWinners.experience && (
              <div className="bg-purple-50/60 border border-purple-100 rounded-2xl p-3 sm:p-4 flex items-center justify-between shadow-2xs">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 bg-purple-100 text-purple-600 rounded-xl shrink-0">
                    <Briefcase className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Top Experience</p>
                    <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.experience.name}</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-purple-100/80 text-purple-700 rounded-lg text-xs font-semibold shrink-0">
                  {categoryWinners.experience.experienceScore}%
                </span>
              </div>
            )}
            {categoryWinners.education && (
              <div className="bg-emerald-50/60 border border-emerald-100 rounded-2xl p-3 sm:p-4 flex items-center justify-between shadow-2xs">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 bg-emerald-100 text-emerald-600 rounded-xl shrink-0">
                    <GraduationCap className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Top Education</p>
                    <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.education.name}</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-emerald-100/80 text-emerald-700 rounded-lg text-xs font-semibold shrink-0">
                  {categoryWinners.education.education_score ?? categoryWinners.education.educationScore ?? 0}%
                </span>
              </div>
            )}
            {evaluationFilters.certifications && categoryWinners.certifications && (
              <div className="bg-amber-50/60 border border-amber-100 rounded-2xl p-3 sm:p-4 flex items-center justify-between shadow-2xs">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="p-2 bg-amber-100 text-amber-600 rounded-xl shrink-0">
                    <Award className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Top Certifications</p>
                    <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.certifications.name}</p>
                  </div>
                </div>
                <span className="px-2 py-1 bg-amber-100/80 text-amber-700 rounded-lg text-xs font-semibold shrink-0">
                  {categoryWinners.certifications.certificationsScore || 0}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* View Mode Switcher for Mobile & Tablet */}
        <div className={styles.resultsToolbar}>
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-xs sm:text-base font-semibold text-slate-900 tracking-tight truncate">Comparison Results</h3>
            <span className="text-xs font-bold text-slate-500 shrink-0">({selectedCandidatesData.length})</span>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-end">
            <button
              type="button"
              onClick={exportToCSV}
              className="px-2.5 sm:px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-700 hover:text-[#D60041] hover:border-rose-200 text-xs font-bold transition-all flex items-center gap-1.5 shadow-2xs cursor-pointer"
              title="Export comparison to CSV"
            >
              <Download size={13} className="text-[#D60041]" />
              <span className="hidden sm:inline">Export CSV</span>
              <span className="sm:hidden">CSV</span>
            </button>
            <button
              type="button"
              onClick={exportToPDF}
              className="px-2.5 sm:px-3 py-1.5 rounded-xl bg-white border border-slate-200 text-slate-700 hover:text-[#D60041] hover:border-rose-200 text-xs font-bold transition-all flex items-center gap-1.5 shadow-2xs cursor-pointer"
              title="Print comparison or save as PDF"
            >
              <Printer size={13} className="text-[#D60041]" />
              <span className="hidden sm:inline">Print / PDF</span>
              <span className="sm:hidden">PDF</span>
            </button>

            {/* Toggle between Sticky Matrix Table and Card Scorecards with intact labels */}
            <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200/80 shrink-0 shadow-2xs">
              <button
                type="button"
                aria-pressed={compareViewMode === 'table'}
                onClick={() => setCompareViewMode('table')}
                className={`px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${compareViewMode === 'table' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
                  }`}
                title="Side-by-side Table Matrix"
              >
                <Table size={13} className={compareViewMode === 'table' ? 'text-[#D60041]' : ''} />
                <span>Table Matrix</span>
              </button>
              <button
                type="button"
                aria-pressed={compareViewMode === 'cards'}
                onClick={() => setCompareViewMode('cards')}
                className={`px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${compareViewMode === 'cards' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
                  }`}
                title="Card Scorecards"
              >
                <LayoutGrid size={13} className={compareViewMode === 'cards' ? 'text-[#D60041]' : ''} />
                <span>Scorecards</span>
              </button>
            </div>
          </div>
        </div>

        {/* 1. TABLE MATRIX VIEW (With Sticky Left Criteria Column) */}
        {compareViewMode === 'table' ? (
          <div>
            {/* Mobile swipe helper badge (< sm) */}
            <div className="sm:hidden flex items-center justify-between px-3 py-1.5 bg-rose-50/70 border border-rose-100 rounded-xl mb-2.5 text-xs font-bold text-rose-800 shadow-2xs">
              <span className="flex items-center gap-1.5">
                <span>↔</span>
                <span>Swipe left/right to compare</span>
              </span>
              <span className="text-xs bg-white px-2 py-0.5 rounded-md border border-rose-200/70 text-[#D60041] font-semibold">
                Labels Pinned
              </span>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
              <div className={styles.matrixScroll} tabIndex={0} role="region" aria-label="Candidate comparison table; scroll horizontally to see all candidates">
                <table className={styles.matrix}>
                  <caption className="sr-only">Candidate scores, qualifications, and assessment notes</caption>
                  <thead>
                    <tr className="bg-slate-50/90 border-b border-slate-200/90">
                      {/* Sticky Column 1 Header with fixed intact width */}
                      <th className="sticky left-0 z-30 bg-slate-100/95 backdrop-blur-md p-3 sm:p-5 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5">
                          <SlidersHorizontal size={13} className="text-slate-500 shrink-0" />
                          <span>Criteria</span>
                        </div>
                      </th>
                      {selectedCandidatesData.map((candidate, idx) => {
                        const isTop = !isAllZero && (candidate.matchScore || 0) > 0 && candidate.matchScore === selectedCandidatesData[0].matchScore;
                        return (
                          <th
                            key={candidate.id}
                            className={`p-3 sm:p-5 text-left min-w-[210px] max-w-[250px] sm:min-w-[270px] relative snap-start ${isTop ? 'bg-rose-50/25' : ''
                              }`}
                          >
                            {isTop && (
                              <div className="absolute top-0 left-0 right-0 h-1 bg-[#D60041]" />
                            )}
                            <div className="flex items-center gap-2.5">
                              <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl overflow-hidden border border-rose-100 shadow-2xs shrink-0 bg-rose-50">
                                <img
                                  src={getAvatarUrl(candidate)}
                                  alt={candidate.name}
                                  className="w-full h-full object-cover"
                                  onError={(e) => {
                                    (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`;
                                  }}
                                />
                              </div>
                              <div className="min-w-0">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span className={`px-1.5 py-0.5 rounded text-xs font-semibold uppercase shrink-0 ${isTop ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                                    }`}>
                                    {isAllZero ? 'Unranked' : `Rank #${idx + 1}`}
                                  </span>
                                  {isTop && <Trophy className="w-3 h-3 text-amber-500 shrink-0" />}
                                  {(candidate.completeness_status === 'Incomplete' || (candidate.completeness_score !== undefined && candidate.completeness_score < 70)) && (
                                    <span className="px-1.5 py-0.5 rounded text-xs font-semibold uppercase bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-0.5" title="Incomplete Profile (REQ058)">
                                      <AlertTriangle className="w-2.5 h-2.5 shrink-0" />
                                      <span>Incomplete</span>
                                    </span>
                                  )}
                                </div>
                                <h4 className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate mt-0.5">{candidate.name}</h4>
                                <p className="text-xs text-slate-500 font-semibold truncate">Applied for: {candidate.applied_job_title || candidate.preferredJob}</p>
                              </div>
                            </div>
                          </th>
                        );
                      })}
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {/* Row 1: Match Percentage */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <TrendingUp size={13} className="text-[#D60041] shrink-0" />
                          <span>Match Score</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate) => {
                        const isTop = !isAllZero && (candidate.matchScore || 0) > 0 && candidate.matchScore === selectedCandidatesData[0].matchScore;
                        return (
                          <td key={candidate.id} className={`p-3 sm:p-5 ${isTop ? 'bg-rose-50/15' : ''}`}>
                            <div className="flex items-center gap-2 sm:gap-3">
                              <span className={`text-lg sm:text-2xl font-semibold ${isTop ? 'text-[#D60041]' : (candidate.matchScore || 0) === 0 ? 'text-slate-500' : 'text-slate-900'}`}>
                                {candidate.matchScore}%
                              </span>
                              <div className="flex-1 max-w-[80px] sm:max-w-[120px] bg-slate-100 rounded-full h-2">
                                <div
                                  className={`h-2 rounded-full ${isTop ? 'bg-[#D60041]' : (candidate.matchScore || 0) === 0 ? 'bg-slate-300' : 'bg-slate-700'}`}
                                  style={{ width: `${candidate.matchScore}%` }}
                                />
                              </div>
                            </div>
                            {isTop ? (
                              <span className="text-xs font-semibold text-[#D60041] uppercase tracking-wider mt-1 block">Top Match</span>
                            ) : (candidate.matchScore || 0) === 0 ? (
                              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-1 block">No Match</span>
                            ) : null}
                          </td>
                        );
                      })}
                    </tr>

                    {/* Row 2: Pillar Scores */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <BarChart3 size={13} className="text-blue-500 shrink-0" />
                          <span>Pillar Scores</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate) => {
                        const isTop = !isAllZero && (candidate.matchScore || 0) > 0 && candidate.matchScore === selectedCandidatesData[0].matchScore;
                        return (
                          <td key={candidate.id} className={`p-3 sm:p-5 space-y-2 sm:space-y-2.5 ${isTop ? 'bg-rose-50/15' : ''}`}>
                            <div>
                              <div className="flex justify-between text-xs font-bold mb-0.5">
                                <span className={evaluationFilters.skills ? 'text-slate-600' : 'text-slate-300 line-through'}>Skills</span>
                                <span className="text-blue-600">{candidate.skillsScore}%</span>
                              </div>
                              <div className="w-full bg-slate-100 rounded-full h-1.5">
                                <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${candidate.skillsScore}%` }} />
                              </div>
                            </div>
                            <div>
                              <div className="flex justify-between text-xs font-bold mb-0.5">
                                <span className={evaluationFilters.experience ? 'text-slate-600' : 'text-slate-300 line-through'}>Experience</span>
                                <span className="text-purple-600">{candidate.experienceScore}%</span>
                              </div>
                              <div className="w-full bg-slate-100 rounded-full h-1.5">
                                <div className="h-1.5 rounded-full bg-purple-500" style={{ width: `${candidate.experienceScore}%` }} />
                              </div>
                            </div>
                            <div>
                              <div className="flex justify-between text-xs font-bold mb-0.5">
                                <span className="text-slate-600">Education</span>
                                <span className="text-emerald-600">{candidate.education_score ?? candidate.educationScore ?? 0}%</span>
                              </div>
                              <div className="w-full bg-slate-100 rounded-full h-1.5">
                                <div className="h-1.5 rounded-full bg-emerald-500" style={{ width: `${candidate.education_score ?? candidate.educationScore ?? 0}%` }} />
                              </div>
                            </div>
                            <div>
                              <div className="flex justify-between text-xs font-bold mb-0.5">
                                <span className={evaluationFilters.certifications ? 'text-slate-600' : 'text-slate-300 line-through'}>Certifications</span>
                                <span className="text-amber-600">{candidate.certificationsScore || 0}%</span>
                              </div>
                              <div className="w-full bg-slate-100 rounded-full h-1.5">
                                <div className="h-1.5 rounded-full bg-amber-500" style={{ width: `${candidate.certificationsScore || 0}%` }} />
                              </div>
                            </div>
                          </td>
                        );
                      })}
                    </tr>

                    {/* Row 3: Skills Alignment (Direct & Transferable) */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                          <span>Skills Alignment</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="space-y-2">
                            <div>
                              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1">Direct Matches</span>
                              <div className="flex flex-wrap gap-1 sm:gap-1.5">
                                {candidate.matched_skills && candidate.matched_skills.length > 0 ? (
                                  candidate.matched_skills.map((skill, i) => (
                                    <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 sm:px-2.5 sm:py-1 bg-emerald-50 text-emerald-700 border border-emerald-200/80 rounded-md text-xs font-bold">
                                      <Check className="w-2.5 h-2.5" />
                                      <span>{skill}</span>
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-slate-500 italic">None matched</span>
                                )}
                              </div>
                            </div>

                            {candidate.transferable_skills && candidate.transferable_skills.length > 0 && (
                              <div className="pt-2 border-t border-slate-100">
                                <span className="text-xs font-bold uppercase tracking-wider text-purple-700 mb-1 flex items-center gap-1">
                                  <Zap size={10} /> Transferable Skills
                                </span>
                                <div className="flex flex-wrap gap-1 sm:gap-1.5">
                                  {candidate.transferable_skills.map((skill, i) => (
                                    <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 sm:px-2 sm:py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded-md text-xs font-bold">
                                      <span>{skill}</span>
                                      <span className="text-xs bg-purple-100 text-purple-800 px-1 rounded uppercase font-semibold">Transferable</span>
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* Row 4: Missing Skills */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <XCircle size={13} className="text-rose-500 shrink-0" />
                          <span>Missing Skills</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="flex flex-wrap gap-1 sm:gap-1.5">
                            {candidate.missing_skills && candidate.missing_skills.length > 0 ? (
                              candidate.missing_skills.map((skill, i) => (
                                <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 sm:px-2.5 sm:py-1 bg-rose-50 text-rose-700 border border-rose-200/80 rounded-md text-xs font-bold">
                                  <XCircle className="w-2.5 h-2.5" />
                                  <span>{skill}</span>
                                </span>
                              ))
                            ) : (
                              <span className="text-xs text-emerald-600 font-bold">All Requirements Met</span>
                            )}
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* Row 5: Core Strengths */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Star size={13} className="text-emerald-500 shrink-0" />
                          <span>Strengths</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <ul className="space-y-1 sm:space-y-1.5 text-xs text-slate-700 font-medium">
                            {(candidate.strengths && candidate.strengths.slice(0, 3).map((strength, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0 stroke-[2.5px]" />
                                <span>{strength}</span>
                              </li>
                            ))) || <span className="italic text-slate-500">N/A</span>}
                          </ul>
                        </td>
                      ))}
                    </tr>

                    {/* Row 6: Gaps & Weaknesses */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <AlertTriangle size={13} className="text-amber-500 shrink-0" />
                          <span>Gaps & Weaknesses</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <ul className="space-y-1 sm:space-y-1.5 text-xs text-slate-700 font-medium">
                            {(candidate.weaknesses && candidate.weaknesses.slice(0, 3).map((weakness, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                                <span>{weakness}</span>
                              </li>
                            ))) || <span className="italic text-slate-500">N/A</span>}
                          </ul>
                        </td>
                      ))}
                    </tr>

                    {/* Row 7: Experience Relevance */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Briefcase size={13} className="text-purple-500 shrink-0" />
                          <span>Experience</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => {
                        const expStatus = resolveCriterionStatus({
                          explicitStatus: candidate.experience_status,
                          reason: candidate.experience_reason,
                          score: candidate.experienceScore ?? 0,
                        });
                        return (
                          <td key={candidate.id} className={`p-3 sm:p-5 text-xs text-slate-700 leading-relaxed ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="font-bold text-slate-900">{!isNoValueRequirement(candidate.company) ? candidate.company : "Company Unspecified"}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold border shrink-0 ${getCriterionStatusBadgeStyle(expStatus).badgeClass}`}>
                                {expStatus}
                              </span>
                            </div>
                            <span className="text-xs uppercase font-bold text-slate-500 block mb-0.5">{!isNoValueRequirement(candidate.relevance) ? candidate.relevance : "Role unspecified"}</span>
                            <p className="line-clamp-3 text-slate-500 text-xs">{candidate.experience_reason || "No details provided"}</p>
                          </td>
                        );
                      })}
                    </tr>

                    {/* Row 7b: Education & Attainment */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <GraduationCap size={13} className="text-emerald-600 shrink-0" />
                          <span>Education</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => {
                        const eduScore = candidate.education_score ?? candidate.educationScore ?? 0;
                        const eduStatus = resolveCriterionStatus({
                          explicitStatus: candidate.education_status,
                          reason: candidate.education_reason,
                          score: eduScore,
                        });
                        const rawCandEdu = candidate.candidate_degree || candidate.degree || candidate.highest_educational_attainment;
                        const candEduDisplay = !isNoValueRequirement(rawCandEdu) ? rawCandEdu : "None provided";
                        const reqEduDisplay = candidate.required_degree || serverComparison?.reference_job?.education_requirements || selectedJob?.education_requirements;
                        return (
                          <td key={candidate.id} className={`p-3 sm:p-5 text-xs text-slate-700 leading-relaxed ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="font-bold text-slate-900">{candEduDisplay}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold border shrink-0 ${getCriterionStatusBadgeStyle(eduStatus).badgeClass}`}>
                                {eduStatus}
                              </span>
                            </div>
                            {!isNoValueRequirement(reqEduDisplay) && (
                              <span className="text-xs font-semibold text-slate-500 block mb-0.5">
                                Required: {reqEduDisplay}
                              </span>
                            )}
                            <p className="line-clamp-3 text-slate-500 text-xs">
                              {candidate.education_reason || "No education evaluation details provided"}
                            </p>
                          </td>
                        );
                      })}
                    </tr>

                    {/* Row 8: Certifications */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Award size={13} className="text-amber-500 shrink-0" />
                          <span>Certifications</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => {
                        const rawCert = candidate.candidate_certifications || candidate.certifications;
                        const displayCert = !isNoValueRequirement(rawCert) ? rawCert : "None provided";
                        const certStatus = resolveCriterionStatus({
                          explicitStatus: candidate.certifications_status,
                          reason: candidate.certifications_reason,
                          score: candidate.certificationsScore ?? candidate.certifications_score ?? 0,
                        });
                        return (
                          <td key={candidate.id} className={`p-3 sm:p-5 text-xs text-slate-700 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <p className="font-bold text-slate-900">{displayCert}</p>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold border shrink-0 ${getCriterionStatusBadgeStyle(certStatus).badgeClass}`}>
                                {certStatus}
                              </span>
                            </div>
                            <p className="text-xs text-slate-500 mt-0.5">{candidate.certifications_reason}</p>
                          </td>
                        );
                      })}
                    </tr>

                    {/* Row 9: Contact Details */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Mail size={13} className="text-slate-500 shrink-0" />
                          <span>Contact Info</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 space-y-1.5 text-xs text-slate-600 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="flex items-center gap-1.5 truncate">
                            <Mail className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                            <span className="truncate">{candidate.email || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-1.5 truncate">
                            <Phone className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                            <span className="truncate">{candidate.phone || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-1.5 truncate">
                            <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                            <span className="truncate">{candidate.location || 'N/A'}</span>
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* Row 10: Profile Completeness (REQ058) */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
                          <span>Completeness</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => {
                        const isIncomplete = candidate.completeness_status === 'Incomplete' || (candidate.completeness_score !== undefined && candidate.completeness_score < 70);
                        return (
                          <td key={candidate.id} className={`p-3 sm:p-5 text-xs ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                            {isIncomplete ? (
                              <div className="space-y-1">
                                <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 font-bold text-xs">
                                  <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />
                                  <span>Incomplete Profile ({candidate.completeness_score || 0}%)</span>
                                </div>
                                {candidate.missing_sections && candidate.missing_sections.length > 0 && (
                                  <p className="text-xs text-amber-700 font-medium">
                                    Missing: {candidate.missing_sections.join(', ')}
                                  </p>
                                )}
                              </div>
                            ) : (
                              <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 font-bold text-xs">
                                <CheckCircle2 className="w-3 h-3 text-emerald-600 shrink-0" />
                                <span>Complete Profile ({candidate.completeness_score || 100}%)</span>
                              </div>
                            )}
                          </td>
                        );
                      })}
                    </tr>

                    {/* Row 11: HR Shortlisting Notes (REQ056) */}
                    <tr className="hover:bg-slate-50/40 transition-colors bg-slate-50/20">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-xs font-semibold text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <FileText size={13} className="text-[#D60041] shrink-0" />
                          <span>HR Notes</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 text-xs ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="space-y-1.5">
                            <textarea
                              rows={3}
                              value={candidateNotes[candidate.id] ?? candidate.hr_shortlist_notes ?? ''}
                              onChange={(e) => setCandidateNotes(prev => ({ ...prev, [candidate.id]: e.target.value }))}
                              placeholder="Add evaluation note or comment..."
                              className="w-full text-xs p-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-[#D60041] bg-white text-slate-800 resize-none"
                            />
                            <div className="flex items-center justify-between">
                              {savedSuccess[candidate.id] ? (
                                <span className="text-xs font-bold text-emerald-600 flex items-center gap-1">
                                  <Check className="w-3 h-3" /> Saved to profile
                                </span>
                              ) : (
                                <span className="text-xs text-slate-500">Inline shortlisting note</span>
                              )}
                              <button
                                type="button"
                                disabled={savingNotes[candidate.id]}
                                onClick={() => handleSaveNote(candidate.id)}
                                className="px-2.5 py-1 bg-slate-900 hover:bg-[#D60041] text-white rounded-md text-xs font-bold transition-colors flex items-center gap-1 shadow-2xs cursor-pointer disabled:opacity-50"
                              >
                                <Save size={10} />
                                <span>{savingNotes[candidate.id] ? 'Saving...' : 'Save Note'}</span>
                              </button>
                            </div>
                          </div>
                        </td>
                      ))}
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          /* 2. CARD-BY-CARD COMPARISON (Mobile Optimized Complete Dossiers) */
          <div>
            {/* Mobile candidate selector pills */}
            {selectedCandidatesData.length > 1 && (
              <div className="flex items-center gap-1.5 overflow-x-auto pb-2.5 mb-3.5 custom-scrollbar">
                <button
                  type="button"
                  onClick={() => setScorecardFilter('all')}
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${scorecardFilter === 'all'
                    ? 'bg-slate-900 text-white shadow-2xs'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                    }`}
                >
                  All Candidates ({selectedCandidatesData.length})
                </button>
                {selectedCandidatesData.map((cand, i) => {
                  const isTop = !isAllZero && (cand.matchScore || 0) > 0 && cand.matchScore === selectedCandidatesData[0].matchScore;
                  return (
                    <button
                      key={cand.id}
                      type="button"
                      onClick={() => setScorecardFilter(cand.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer ${scorecardFilter === cand.id
                        ? 'bg-[#D60041] text-white shadow-2xs'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                        }`}
                    >
                      {isTop && <Trophy size={11} className={scorecardFilter === cand.id ? 'text-amber-300' : 'text-amber-500'} />}
                      <span>{cand.name.split(' ')[0]}</span>
                      <span className="text-xs opacity-80 font-semibold">({cand.matchScore}%)</span>
                    </button>
                  );
                })}
              </div>
            )}

            <div className={styles.scorecardGrid}>
              {displayedCandidatesInScorecards.map((candidate) => {
                const actualRank = selectedCandidatesData.findIndex(c => c.id === candidate.id) + 1;
                const isTopMatch = !isAllZero && (candidate.matchScore || 0) > 0 && candidate.matchScore === selectedCandidatesData[0].matchScore;
                const isZeroScore = (candidate.matchScore || 0) === 0;

                return (
                  <div
                    key={candidate.id}
                    className={`bg-white border rounded-2xl p-4 sm:p-6 shadow-xs flex flex-col justify-between transition-all ${isTopMatch ? 'border-rose-200 ring-2 ring-rose-100 shadow-md' : 'border-slate-200/90'
                      }`}
                  >
                    <div className="space-y-4">
                      {/* Card Header & Rank */}
                      <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-100">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-12 h-12 rounded-xl overflow-hidden border border-rose-100 shadow-2xs shrink-0 bg-rose-50">
                            <img
                              src={getAvatarUrl(candidate)}
                              alt={candidate.name}
                              className="w-full h-full object-cover"
                              onError={(e) => {
                                (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(candidate.name)}&background=fdf2f8&color=d81159&bold=true`;
                              }}
                            />
                          </div>
                          <div className="min-w-0">
                            <h4 className="text-sm sm:text-base font-bold text-slate-900 truncate">{candidate.name}</h4>
                            <p className="text-xs text-slate-500 font-semibold truncate mt-0.5">Applied for: {candidate.applied_job_title || candidate.preferredJob}</p>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className={`inline-flex items-center gap-1 text-xs font-semibold uppercase px-2 py-0.5 rounded-full ${isTopMatch
                            ? 'bg-amber-100 text-amber-800'
                            : isZeroScore
                              ? 'bg-slate-100 text-slate-500'
                              : 'bg-slate-100 text-slate-600'
                            }`}>
                            {isTopMatch && <Trophy size={11} className="text-amber-600" />}
                            {isZeroScore ? 'No Match' : `Rank #${actualRank}`}
                          </span>
                          <p className={`text-2xl font-semibold mt-0.5 leading-tight ${isZeroScore ? 'text-slate-500' : 'text-[#D60041]'}`}>
                            {candidate.matchScore}%
                          </p>
                        </div>
                      </div>

                      {/* 4 Pillar Breakdown Cards */}
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Pillar Scores</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 sm:gap-2">
                          <div className="bg-blue-50/60 border border-blue-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-semibold text-blue-700">{candidate.skillsScore}%</p>
                            <p className="text-xs font-bold text-slate-500 uppercase mt-0.5">Skills</p>
                            <div className="w-full bg-blue-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-blue-500" style={{ width: `${candidate.skillsScore}%` }} />
                            </div>
                          </div>
                          <div className="bg-purple-50/60 border border-purple-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-semibold text-purple-700">{candidate.experienceScore}%</p>
                            <p className="text-xs font-bold text-slate-500 uppercase mt-0.5">Exp</p>
                            <div className="w-full bg-purple-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-purple-500" style={{ width: `${candidate.experienceScore}%` }} />
                            </div>
                          </div>
                          <div className="bg-emerald-50/60 border border-emerald-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-semibold text-emerald-700">{candidate.education_score ?? candidate.educationScore ?? 0}%</p>
                            <p className="text-xs font-bold text-slate-500 uppercase mt-0.5">Edu</p>
                            <div className="w-full bg-emerald-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-emerald-500" style={{ width: `${candidate.education_score ?? candidate.educationScore ?? 0}%` }} />
                            </div>
                          </div>
                          <div className="bg-amber-50/60 border border-amber-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-semibold text-amber-700">{candidate.certificationsScore || 0}%</p>
                            <p className="text-xs font-bold text-slate-500 uppercase mt-0.5">Certs</p>
                            <div className="w-full bg-amber-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-amber-500" style={{ width: `${candidate.certificationsScore || 0}%` }} />
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* AI Summary / Quote if present */}
                      {candidate.ai_summary && (
                        <div className="bg-rose-50/40 border border-rose-100/80 rounded-xl p-3 text-xs text-slate-700 italic leading-relaxed">
                          <span className="font-bold text-[#D60041] not-italic block text-xs uppercase tracking-wider mb-0.5">AI Summary</span>
                          "{candidate.ai_summary}"
                        </div>
                      )}

                      {/* Core Strengths */}
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Key Strengths</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 space-y-1.5">
                          {candidate.strengths && candidate.strengths.length > 0 ? (
                            candidate.strengths.slice(0, 3).map((strength, i) => (
                              <div key={i} className="flex items-start gap-1.5 text-xs text-slate-700 font-medium leading-snug">
                                <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0 stroke-[2.5px]" />
                                <span>{strength}</span>
                              </div>
                            ))
                          ) : (
                            <p className="text-xs text-slate-500 italic">No specific strengths listed</p>
                          )}
                        </div>
                      </div>

                      {/* Areas for Improvement / Gaps */}
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Identified Gaps</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 space-y-1.5">
                          {candidate.weaknesses && candidate.weaknesses.length > 0 ? (
                            candidate.weaknesses.slice(0, 3).map((gap, i) => (
                              <div key={i} className="flex items-start gap-1.5 text-xs text-slate-700 font-medium leading-snug">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                                <span>{gap}</span>
                              </div>
                            ))
                          ) : (
                            <p className="text-xs text-emerald-600 font-bold">No notable gaps identified</p>
                          )}
                        </div>
                      </div>

                      {/* Matched & Missing Skills */}
                      <div className="space-y-2.5 pt-1">
                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Matched Skills</p>
                          <div className="flex flex-wrap gap-1">
                            {candidate.matched_skills && candidate.matched_skills.length > 0 ? (
                              candidate.matched_skills.map((skill, i) => (
                                <span key={i} className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded text-xs font-bold">
                                  {skill}
                                </span>
                              ))
                            ) : (
                              <span className="text-slate-500 italic text-xs">None</span>
                            )}
                          </div>
                        </div>

                        {candidate.transferable_skills && candidate.transferable_skills.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold uppercase tracking-wider text-purple-700 mb-1 flex items-center gap-1">
                              <Zap size={10} /> Transferable Skills
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {candidate.transferable_skills.map((skill, i) => (
                                <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded text-xs font-bold">
                                  {skill}
                                  <span className="text-xs bg-purple-100 text-purple-800 ml-1 px-1 rounded uppercase font-semibold">Transferable</span>
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        <div>
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Missing Skills</p>
                          <div className="flex flex-wrap gap-1">
                            {candidate.missing_skills && candidate.missing_skills.length > 0 ? (
                              candidate.missing_skills.map((skill, i) => (
                                <span key={i} className="px-2 py-0.5 bg-rose-50 text-rose-700 border border-rose-100 rounded text-xs font-bold">
                                  {skill}
                                </span>
                              ))
                            ) : (
                              <span className="text-emerald-600 font-bold text-xs">All Required Skills Met</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Work Experience Summary */}
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Experience</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 text-xs text-slate-700">
                          <p className="font-bold text-slate-900">{!isNoValueRequirement(candidate.company) ? candidate.company : "Company Unspecified"}</p>
                          <p className="text-xs uppercase font-bold text-slate-500">{!isNoValueRequirement(candidate.relevance) ? candidate.relevance : "Role unspecified"}</p>
                          {candidate.experience_reason && (
                            <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">{candidate.experience_reason}</p>
                          )}
                        </div>
                      </div>

                      {/* Education Summary */}
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Education</p>
                          {(() => {
                            const eduSt = resolveCriterionStatus({
                              explicitStatus: candidate.education_status,
                              reason: candidate.education_reason,
                              score: candidate.education_score ?? candidate.educationScore ?? 0,
                            });
                            return (
                              <span className={`px-1.5 py-0.5 rounded-full text-xs font-bold border ${getCriterionStatusBadgeStyle(eduSt).badgeClass}`}>
                                {eduSt}
                              </span>
                            );
                          })()}
                        </div>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 text-xs text-slate-700">
                          <p className="font-bold text-slate-900">
                            {!isNoValueRequirement(candidate.candidate_degree || candidate.degree || candidate.highest_educational_attainment)
                              ? (candidate.candidate_degree || candidate.degree || candidate.highest_educational_attainment)
                              : "None provided"}
                          </p>
                          {!isNoValueRequirement(candidate.required_degree) && (
                            <p className="text-xs font-semibold text-slate-500 mt-0.5">Required: {candidate.required_degree}</p>
                          )}
                          {candidate.education_reason && (
                            <p className="text-xs text-slate-500 mt-0.5 line-clamp-2 leading-relaxed">{candidate.education_reason}</p>
                          )}
                        </div>
                      </div>

                      {/* Certifications Summary */}
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">Certifications</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 text-xs text-slate-700">
                          <p className="font-bold text-slate-900">
                            {!isNoValueRequirement(candidate.candidate_certifications || candidate.certifications)
                              ? (candidate.candidate_certifications || candidate.certifications)
                              : "None provided"}
                          </p>
                          {candidate.certifications_reason && (
                            <p className="text-xs text-slate-500 mt-0.5">{candidate.certifications_reason}</p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Contact Footer */}
                    <div className="pt-3 mt-4 border-t border-slate-100 text-xs text-slate-500 space-y-1">
                      <div className="flex items-center gap-1.5 truncate">
                        <Mail size={12} className="text-slate-500 shrink-0" />
                        <span className="truncate">{candidate.email || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1.5 truncate">
                        <Phone size={12} className="text-slate-500 shrink-0" />
                        <span className="truncate">{candidate.phone || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1.5 truncate">
                        <MapPin size={12} className="text-slate-500 shrink-0" />
                        <span className="truncate">{candidate.location || 'N/A'}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Bottom Back / Switch Action */}
        <div className="mt-8 pt-6 border-t border-slate-200/80 flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setIsComparing(false)}
            className="w-full sm:w-auto px-5 py-2.5 bg-white border border-slate-200 text-slate-700 hover:text-slate-900 font-bold text-xs sm:text-sm rounded-xl shadow-2xs flex items-center justify-center gap-2 hover:bg-slate-50 transition-all cursor-pointer"
          >
            <ArrowLeft size={14} />
            <span>Back to Candidate Selection</span>
          </button>
          <p className="text-center sm:text-right text-xs text-slate-500 font-medium">
            Comparing {selectedCandidatesData.length} selected candidates
          </p>
        </div>
      </div>
    );
  };

  const renderPersonRow = (item: RankedPersonItem<CandidateComparisonData, PersonGroup>) => {
    const { person, effectiveApp, appliedToSelectedJob, displayScore } = item;
    const isSelected = person.applications.some(a => selectedCandidateIds.includes(a.id));
    const isActive = person.applications.some(a => activeCandidateId === a.id);
    const hasMultiple = person.applications.length > 1;

    return (
      <div key={person.personKey} className={styles.personRow} data-active={isActive} data-selected={isSelected}>
        <div className={styles.personRowMain}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => togglePersonSelection(person, effectiveApp.id)}
            aria-label={`Select ${person.name} for comparison`}
            className={styles.candidateCheckbox}
          />
          <button type="button" className={styles.personPreview} aria-pressed={isActive} onClick={() => {
            setActiveCandidateId(effectiveApp.id);
            if (window.innerWidth < 1024) setMobileTab('profile');
          }}>
            <span className={styles.personAvatar} aria-hidden="true">{person.name.split(' ').filter(Boolean).slice(0, 2).map(part => part[0]).join('')}</span>
            <span className={styles.personIdentity}>
              <strong>{person.name}</strong>
              <span>{effectiveApp.applied_job_title || effectiveApp.preferredJob || 'Position not specified'}</span>
              <span className={styles.personMeta}>{appliedToSelectedJob ? 'Applied to this role' : 'View profile'}{hasMultiple ? ` · ${person.applications.length} applications` : ''}</span>
            </span>
            <span className={styles.personScore}>{displayScore}%<small>match</small></span>
          </button>
        </div>

        {/* Position selector when person applied for multiple roles */}
        {hasMultiple && (
          <div className="pl-8 pt-1 flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
            <span className="text-xs font-bold text-slate-500 whitespace-nowrap">Compare for:</span>
            <select
              aria-label={`Application to compare for ${person.name}`}
              value={effectiveApp.id}
              onChange={(e) => {
                const newId = parseInt(e.target.value, 10);
                setPersonSelectedAppMap(prev => ({ ...prev, [person.personKey]: newId }));
                if (isSelected) {
                  const personAppIds = new Set(person.applications.map(a => a.id));
                  setSelectedCandidateIds(prev => [...prev.filter(id => !personAppIds.has(id)), newId]);
                }
                setActiveCandidateId(newId);
              }}
              className="w-full text-xs font-semibold bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-2 py-0.5 text-slate-800 cursor-pointer focus:outline-none focus:ring-1 focus:ring-rose-500/30 truncate"
            >
              {person.applications.map((app) => (
                <option key={app.id} value={app.id}>
                  {app.preferredJob || app.applied_job_title || app.job_title || 'Position'} (Application #{app.id})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>
    );
  };

  const renderSelectionView = () => (
    <div className={styles.selectionView}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>MARIWASA / TALENT ACQUISITION</p>
          <h1>Compare candidates</h1>
          <p className={styles.intro}>Bring the right people into focus. Explore profiles and compare their fit for your role.</p>
        </div>
        <span className={styles.workspaceBadge}><Scale size={17} /> Talent assessment</span>
      </header>

      <section className={styles.selectionTray} aria-label="Candidates selected for comparison">
        <div className={styles.trayContent}>
          <div className={styles.trayHeading}>
            <span className={styles.trayIcon}><Users size={20} /></span>
            <div><h2>Your comparison shortlist <span>({selectedCandidateIds.length})</span></h2>
              <p aria-live="polite">{selectedCandidateIds.length < 2 ? `Select ${2 - selectedCandidateIds.length} more ${selectedCandidateIds.length === 1 ? 'candidate' : 'candidates'} to start comparing.` : 'Ready to explore their strengths side by side.'}</p>
            </div>
          </div>
          {selectedCandidateIds.length > 0 && (
            <div className={styles.selectedChips}>
              {(candidates as CandidateComparisonData[]).filter(candidate => selectedCandidateIds.includes(candidate.id)).map(candidate => (
                <button type="button" key={candidate.id} onClick={() => toggleSelection(candidate.id)} aria-label={`Remove ${candidate.name} from comparison`}>
                  <span>{candidate.name}</span><X size={14} />
                </button>
              ))}
            </div>
          )}
        </div>
        <div className={styles.trayActions}>
          {selectedCandidateIds.length > 0 && <button type="button" className={styles.clearButton} onClick={clearSelected}>Clear selection</button>}
          <button type="button" disabled={selectedCandidateIds.length < 2} onClick={() => setIsComparing(true)} className={styles.primaryButton}>
            <Scale size={17} /> Compare candidates
          </button>
        </div>
      </section>

      {/* Mobile Tab Switcher (< 1024px) */}
      <div className="lg:hidden flex bg-slate-100 p-1 rounded-2xl mb-4 border border-slate-200/80 shadow-2xs shrink-0">
        <button
          type="button"
          aria-pressed={mobileTab === 'list'}
          onClick={() => setMobileTab('list')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${mobileTab === 'list'
            ? 'bg-white text-slate-900 shadow-xs'
            : 'text-slate-500 hover:text-slate-800'
            }`}
        >
          <Users size={14} className={mobileTab === 'list' ? 'text-[#D60041]' : ''} />
          <span>Candidate List ({personGroups.length})</span>
        </button>
        <button
          type="button"
          aria-pressed={mobileTab === 'profile'}
          onClick={() => setMobileTab('profile')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${mobileTab === 'profile'
            ? 'bg-white text-slate-900 shadow-xs'
            : 'text-slate-500 hover:text-slate-800'
            }`}
        >
          <User size={14} className={mobileTab === 'profile' ? 'text-[#D60041]' : ''} />
          <span className="truncate">{activeCandidate ? activeCandidate.name.split(' ')[0] + "'s Details" : 'Preview Profile'}</span>
        </button>
      </div>

      {/* Split-Screen Selection Area */}
      <div className={styles.selectionGrid}>

        {/* LEFT COLUMN: Candidate Search and List */}
        <div
          data-panel="candidate-list"
          className={`w-full lg:w-[380px] bg-white border border-slate-200/90 rounded-2xl shadow-xs flex flex-col shrink-0 overflow-hidden ${mobileTab === 'list' ? 'flex' : 'hidden lg:flex'
            } max-h-[560px] lg:max-h-none`}
        >
          <div className={styles.listControls}>
            <div className={styles.panelHeading}><h2>Candidate directory</h2><span>{personGroups.length} found</span></div>
            {/* Job Profile Filter */}
            <div>
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <label htmlFor="compare-against-job-select" className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
                  Reference position
                </label>
                {selectedJobId && (
                  <button
                    type="button"
                    onClick={() => handleSelectedJobChange("")}
                    className="text-xs font-bold text-[#D60041] hover:underline cursor-pointer"
                  >
                    Clear
                  </button>
                )}
              </div>
              <select
                id="compare-against-job-select"
                value={selectedJobId}
                onChange={(e) => handleSelectedJobChange(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-[#D60041] transition-all font-semibold text-xs sm:text-sm text-slate-800 cursor-pointer"
              >
                <option value="">Original application scores</option>
                {(jobs as Job[]).map(job => (
                  <option key={job.id} value={job.id}>{job.title || job.job_title}</option>
                ))}
              </select>
            </div>

            {/* Evaluation Criteria Checklist */}
            <div>
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5 block">
                Evaluation Criteria
              </label>
              <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
                <button
                  type="button"
                  aria-pressed={evaluationFilters.skills}
                  data-control="criterion"
                  onClick={() => setEvaluationFilters(prev => ({ ...prev, skills: !prev.skills }))}
                  className={`flex items-center justify-center gap-1.5 px-2 py-1.5 sm:py-2 rounded-xl border text-xs font-bold transition-all cursor-pointer ${evaluationFilters.skills
                    ? 'bg-blue-50 text-blue-700 border-blue-200 shadow-2xs'
                    : 'bg-white text-slate-500 border-slate-200 hover:text-slate-600'
                    }`}
                >
                  <div className={`w-3.5 h-3.5 rounded flex items-center justify-center transition-all ${evaluationFilters.skills ? 'bg-blue-600 text-white' : 'border border-slate-300'
                    }`}>
                    {evaluationFilters.skills && <Check className="w-2.5 h-2.5 stroke-[3px]" />}
                  </div>
                  <span>Skills</span>
                </button>

                <button
                  type="button"
                  aria-pressed={evaluationFilters.experience}
                  data-control="criterion"
                  onClick={() => setEvaluationFilters(prev => ({ ...prev, experience: !prev.experience }))}
                  className={`flex items-center justify-center gap-1.5 px-2 py-1.5 sm:py-2 rounded-xl border text-xs font-bold transition-all cursor-pointer ${evaluationFilters.experience
                    ? 'bg-purple-50 text-purple-700 border-purple-200 shadow-2xs'
                    : 'bg-white text-slate-500 border-slate-200 hover:text-slate-600'
                    }`}
                >
                  <div className={`w-3.5 h-3.5 rounded flex items-center justify-center transition-all ${evaluationFilters.experience ? 'bg-purple-600 text-white' : 'border border-slate-300'
                    }`}>
                    {evaluationFilters.experience && <Check className="w-2.5 h-2.5 stroke-[3px]" />}
                  </div>
                  <span>Experience</span>
                </button>

                <button
                  type="button"
                  aria-pressed={evaluationFilters.certifications}
                  data-control="criterion"
                  onClick={() => setEvaluationFilters(prev => ({ ...prev, certifications: !prev.certifications }))}
                  className={`flex items-center justify-center gap-1.5 px-2 py-1.5 sm:py-2 rounded-xl border text-xs font-bold transition-all cursor-pointer ${evaluationFilters.certifications
                    ? 'bg-amber-50 text-amber-700 border-amber-200 shadow-2xs'
                    : 'bg-white text-slate-500 border-slate-200 hover:text-slate-600'
                    }`}
                >
                  <div className={`w-3.5 h-3.5 rounded flex items-center justify-center transition-all ${evaluationFilters.certifications ? 'bg-amber-600 text-white' : 'border border-slate-300'
                    }`}>
                    {evaluationFilters.certifications && <Check className="w-2.5 h-2.5 stroke-[3px]" />}
                  </div>
                  <span>Certs</span>
                </button>
              </div>
            </div>

            {/* Candidate Search Box */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                aria-label="Search candidates by name, role, or skill"
                placeholder="Search name, role, or skill…"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-10 py-2 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-[#D60041] transition-all font-semibold text-xs sm:text-sm text-slate-800"
              />
              {searchQuery && <button type="button" className={styles.clearSearch} onClick={() => setSearchQuery('')} aria-label="Clear candidate search"><X size={16} /></button>}
            </div>
          </div>

          {/* Scrollable Candidate Items List */}
          <div ref={listScrollRef} className={styles.candidateList}>
            {isLoading ? (
              <div role="status" className="flex flex-col items-center justify-center py-16">
                <div className="w-8 h-8 border-3 border-rose-100 border-t-[#D60041] rounded-full animate-spin mb-2"></div>
                <p className="text-slate-500 text-xs font-bold">Loading applicants...</p>
              </div>
            ) : candidatesError ? (
              <div className={styles.emptyState} role="alert">
                <AlertTriangle size={24} /><h3>Couldn’t load candidates</h3>
                <p>Please try again to continue your comparison.</p>
                <button type="button" onClick={() => refetchCandidates()}>Try again</button>
              </div>
            ) : personGroups.length === 0 ? (
              <div className="text-center py-12 px-4">
                <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-2.5 border border-slate-100">
                  <Users className="w-5 h-5 text-slate-300" />
                </div>
                <h4 className="text-xs sm:text-sm font-bold text-slate-800">No candidates found</h4>
                <p className="text-xs text-slate-500 mt-0.5">{searchQuery ? 'Try another name, role, or skill.' : 'Candidates will appear here once applications are available.'}</p>
                {searchQuery && <button type="button" className="text-sm text-[#9b2346] mt-4 hover:underline" onClick={() => setSearchQuery('')}>Clear search</button>}
              </div>
            ) : selectedJob ? (
              <>
                <div className="px-2.5 py-1.5 bg-emerald-50/70 border border-emerald-100 rounded-xl flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-800">
                    Applied to this job ({appliedToJob.length})
                  </span>
                </div>

                {appliedToJob.length > 0 ? (
                  <div className="divide-y divide-slate-100 space-y-1">
                    {appliedToJob.map(renderPersonRow)}
                  </div>
                ) : (
                  <p className="px-3 py-3 text-xs font-medium text-slate-500 italic">
                    No applicants applied to this job yet.
                  </p>
                )}

                {otherApplicants.length > 0 && (
                  <>
                    <div className="pt-2 pb-1">
                      <div className="border-t border-slate-200 mb-2" />
                      <div className="px-2.5 py-1.5 bg-slate-100/80 border border-slate-200/70 rounded-xl flex items-center justify-between">
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-600">
                          Other applicants ({otherApplicants.length})
                        </span>
                      </div>
                    </div>
                    <div className="divide-y divide-slate-100 space-y-1">
                      {otherApplicants.map(renderPersonRow)}
                    </div>
                  </>
                )}
              </>
            ) : (
              <div className="divide-y divide-slate-100 space-y-1">
                {otherApplicants.map(renderPersonRow)}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Full Resume Details (Detailed Profile View) */}
        <div
          data-panel="profile"
          className={`flex-1 bg-white border border-slate-200/90 rounded-2xl shadow-xs flex flex-col min-h-0 ${mobileTab === 'profile' ? 'flex' : 'hidden lg:flex'
            } overflow-hidden`}
        >
          {/* Mobile Back to List Button (< 1024px) */}
          <div className="lg:hidden p-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between shrink-0">
            <button
              type="button"
              aria-pressed={mobileTab === 'list'}
          onClick={() => setMobileTab('list')}
              className="flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-[#D60041] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Candidates List</span>
            </button>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Candidate Details</span>
          </div>

          {activeCandidate ? (
            <div className="flex-grow flex flex-col min-h-0 overflow-y-auto lg:overflow-hidden lg:h-full">
              {/* Profile Card Header */}
              <div className={styles.profileHeader}>
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-xl sm:rounded-2xl overflow-hidden border border-rose-100 shadow-2xs shrink-0 bg-rose-50">
                    <img
                      src={getAvatarUrl(activeCandidate)}
                      alt={activeCandidate.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(activeCandidate.name)}&background=fdf2f8&color=d81159&bold=true`;
                      }}
                    />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-base sm:text-2xl font-semibold text-slate-900 tracking-tight leading-tight truncate">
                        {activeCandidate.name}
                      </h2>
                      {activeCandidateAppliedToSelectedJob && (
                        <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-semibold uppercase tracking-wider shrink-0">
                          Applied
                        </span>
                      )}
                    </div>
                    <p className="text-xs sm:text-sm text-slate-500 font-semibold mt-0.5 truncate">{activeCandidate.applied_job_title || activeCandidate.preferredJob}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-1 sm:mt-1.5">
                      <div className="flex items-center gap-1 text-xs text-slate-500 font-bold uppercase truncate">
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{activeCandidate.location || 'N/A'}</span>
                      </div>
                      <div className="w-1 h-1 rounded-full bg-slate-300"></div>
                      <div className="flex items-center gap-1 text-xs text-slate-500 font-bold uppercase truncate">
                        <Mail className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{activeCandidate.email || "N/A"}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Score & Add/Remove to Comparison Button */}
                <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                  <div className="text-left sm:text-right">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Suitability</p>
                    {(() => {
                      const activeScore = activeCandidateEvaluated?.matchScore || 0;
                      return (
                        <p className={`text-xl sm:text-2xl font-semibold leading-none mt-0.5 ${activeScore > 0 ? 'text-[#D60041]' : 'text-slate-500'}`}>
                          {activeScore}%
                        </p>
                      );
                    })()}
                  </div>

                  {(() => {
                    const personAppIds = new Set(
                      (candidates as CandidateComparisonData[])
                        .filter(c => isSamePerson(activeCandidate, c))
                        .map(c => c.id)
                    );
                    const isSelected = selectedCandidateIds.some(id => personAppIds.has(id));

                    return (
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => {
                            if (isSelected) {
                              setSelectedCandidateIds(prev => prev.filter(id => !personAppIds.has(id)));
                            } else {
                              toggleSelection(activeCandidate.id);
                            }
                          }}
                          className={`flex items-center gap-1.5 sm:gap-2 px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-xl text-xs font-bold transition-all border cursor-pointer ${isSelected
                              ? 'bg-rose-50 text-rose-600 border-rose-200 hover:bg-rose-100/70'
                              : 'bg-[#D60041] text-white border-[#D60041] hover:bg-rose-700 shadow-2xs hover:shadow-rose-100'
                            }`}
                        >
                          {isSelected ? (
                            <>
                              <XCircle className="w-3.5 h-3.5" />
                              <span>Remove from Compare</span>
                            </>
                          ) : (
                            <>
                              <Plus className="w-3.5 h-3.5" />
                              <span>Add to Compare</span>
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })()}
                </div>
              </div>

              {/* Scrollable Detail Body */}
              <div className={styles.profileBody}>
                {/* 4 Pillar Score Breakdown Cards */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 sm:mb-3">Score Breakdown</h4>
                  <div data-section="profile-scores" className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-4">
                    <div className={`p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all ${evaluationFilters.skills ? 'bg-blue-50/50 border-blue-100' : 'bg-slate-50/50 border-slate-100 opacity-60'
                      }`}>
                      <div className="flex justify-center mb-1">
                        <Zap className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${evaluationFilters.skills ? 'text-blue-500' : 'text-slate-500'}`} />
                      </div>
                      <p className={`text-base sm:text-xl font-semibold ${evaluationFilters.skills ? 'text-blue-700' : 'text-slate-500'}`}>
                        {activeCandidateEvaluated?.skillsScore || 0}%
                      </p>
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-0.5">Skills</p>
                    </div>

                    <div className={`p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all ${evaluationFilters.experience ? 'bg-purple-50/50 border-purple-100' : 'bg-slate-50/50 border-slate-100 opacity-60'
                      }`}>
                      <div className="flex justify-center mb-1">
                        <Briefcase className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${evaluationFilters.experience ? 'text-purple-500' : 'text-slate-500'}`} />
                      </div>
                      <p className={`text-base sm:text-xl font-semibold ${evaluationFilters.experience ? 'text-purple-700' : 'text-slate-500'}`}>
                        {activeCandidateEvaluated?.experienceScore || 0}%
                      </p>
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-0.5">Experience</p>
                    </div>

                    <div className="p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all bg-emerald-50/50 border-emerald-100">
                      <div className="flex justify-center mb-1">
                        <GraduationCap className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-emerald-500" />
                      </div>
                      <p className="text-base sm:text-xl font-semibold text-emerald-700">
                        {activeCandidateEvaluated?.education_score ?? activeCandidateEvaluated?.educationScore ?? 0}%
                      </p>
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-0.5">Education</p>
                    </div>

                    <div className={`p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all ${evaluationFilters.certifications ? 'bg-amber-50/50 border-amber-100' : 'bg-slate-50/50 border-slate-100 opacity-60'
                      }`}>
                      <div className="flex justify-center mb-1">
                        <Award className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${evaluationFilters.certifications ? 'text-amber-500' : 'text-slate-500'}`} />
                      </div>
                      <p className={`text-base sm:text-xl font-semibold ${evaluationFilters.certifications ? 'text-amber-700' : 'text-slate-500'}`}>
                        {activeCandidateEvaluated?.certificationsScore || 0}%
                      </p>
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mt-0.5">Certs</p>
                    </div>
                  </div>
                </div>

                {/* AI Summary */}
                {activeCandidate.ai_summary && (
                  <div className="bg-gradient-to-r from-rose-50/40 to-pink-50/30 border border-rose-100/80 rounded-2xl p-4 sm:p-5 shadow-2xs">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-[#D60041]" />
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-[#D60041]">AI Evaluation Summary</h4>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium italic">
                      "{activeCandidate.ai_summary}"
                    </p>
                  </div>
                )}

                {/* Education Attainment Preview */}
                {activeCandidateEvaluated && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Education Alignment</h4>
                      {(() => {
                        const eduSt = resolveCriterionStatus({
                          explicitStatus: activeCandidateEvaluated.education_status,
                          reason: activeCandidateEvaluated.education_reason,
                          score: activeCandidateEvaluated.education_score ?? activeCandidateEvaluated.educationScore ?? 0,
                        });
                        return (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${getCriterionStatusBadgeStyle(eduSt).badgeClass}`}>
                            {eduSt}
                          </span>
                        );
                      })()}
                    </div>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-4 space-y-2">
                      <p className="text-xs sm:text-sm font-bold text-slate-800">
                        {!isNoValueRequirement(activeCandidateEvaluated.candidate_degree || activeCandidate.degree || activeCandidate.highest_educational_attainment)
                          ? (activeCandidateEvaluated.candidate_degree || activeCandidate.degree || activeCandidate.highest_educational_attainment)
                          : "None Specified"}
                      </p>
                      {activeCandidateEvaluated.education_reason && (
                        <p className="text-xs text-slate-600 leading-relaxed">{activeCandidateEvaluated.education_reason}</p>
                      )}
                    </div>
                  </div>
                )}

                {/* Work Experience & Certifications Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Work Experience</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-4 space-y-3">
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-0.5">Company / Last Position</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-800">{activeCandidate.company || "Not Specified"}</p>
                      </div>
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-0.5">Relevance</p>
                        <p className="text-xs font-semibold text-slate-600 leading-relaxed">{activeCandidate.relevance || "No parsed work history details"}</p>
                      </div>
                      {activeCandidate.experience_reason && (
                        <div className="pt-2.5 border-t border-slate-200/60">
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-0.5">Experience Analysis</p>
                          <p className="text-xs text-slate-600 leading-relaxed">{activeCandidate.experience_reason}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Certifications</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-4 space-y-3">
                      <div>
                        <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-0.5">Certifications Held</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-800">{activeCandidate.candidate_certifications || activeCandidate.certifications || "None Specified"}</p>
                      </div>
                      {activeCandidate.certifications_reason && (
                        <div className="pt-2.5 border-t border-slate-200/60">
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-0.5">Certifications Analysis</p>
                          <p className="text-xs text-slate-600 leading-relaxed">{activeCandidate.certifications_reason}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Skills Analysis */}
                <div className="space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Skills Evaluation</h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
                    <div className="bg-emerald-50/40 border border-emerald-100 rounded-2xl p-3.5 sm:p-4">
                      <h5 className="flex items-center gap-1.5 text-xs font-semibold text-emerald-800 uppercase tracking-wider mb-2.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Matched Required Skills</span>
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeCandidate.matched_skills && activeCandidate.matched_skills.length > 0 ? (
                          activeCandidate.matched_skills.map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 sm:px-2.5 sm:py-1 bg-white text-emerald-700 border border-emerald-200/80 rounded-md text-xs font-bold">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500 italic">No exact matches stored</span>
                        )}
                      </div>
                    </div>

                    <div className="bg-rose-50/40 border border-rose-100 rounded-2xl p-3.5 sm:p-4">
                      <h5 className="flex items-center gap-1.5 text-xs font-semibold text-rose-800 uppercase tracking-wider mb-2.5">
                        <XCircle className="w-3.5 h-3.5 text-rose-500" />
                        <span>Missing Required Skills</span>
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeCandidate.missing_skills && activeCandidate.missing_skills.length > 0 ? (
                          activeCandidate.missing_skills.map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 sm:px-2.5 sm:py-1 bg-white text-rose-700 border border-rose-200/80 rounded-md text-xs font-bold">
                              {skill}
                            </span>
                          ))
                        ) : (activeCandidate.requirement_evaluations || []).some(
                            (r) => r.field === 'skills' && (r.status === 'Not confirmed' || r.status === 'Possible match')
                          ) ? (
                          <span className="text-xs text-slate-600 font-semibold">
                            No confirmed failures — unconfirmed skills await applicant response
                          </span>
                        ) : (
                          <span className="text-xs text-emerald-600 font-bold">All Requirements Satisfied</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <RequirementEvidence items={activeCandidate.requirement_evaluations} />

                  {activeCandidate.skills_reason && (
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-3.5 sm:p-4">
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Skills Justification</p>
                      <p className="text-xs text-slate-600 leading-relaxed font-semibold">{activeCandidate.skills_reason}</p>
                    </div>
                  )}
                </div>

                {/* Key Strengths & Weaknesses */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Core Strengths</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-3.5 sm:p-4 space-y-2">
                      {activeCandidate.strengths && activeCandidate.strengths.length > 0 ? (
                        activeCandidate.strengths.map((str, i) => (
                          <div key={i} className="flex gap-2 items-start text-xs text-slate-700 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                            <span>{str}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-500 italic">No specific strengths listed</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Areas for Improvement</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-3.5 sm:p-4 space-y-2">
                      {activeCandidate.weaknesses && activeCandidate.weaknesses.length > 0 ? (
                        activeCandidate.weaknesses.map((weak, i) => (
                          <div key={i} className="flex gap-2 items-start text-xs text-slate-700 font-medium">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                            <span>{weak}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-500 italic">No specific gaps identified</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* AI Recommendations */}
                {activeCandidate.recommendations && activeCandidate.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">AI Recommendations</h4>
                    <div className="bg-emerald-50/30 border border-emerald-100 rounded-2xl p-3.5 sm:p-4 space-y-2">
                      {activeCandidate.recommendations.map((rec, i) => (
                        <div key={i} className="flex gap-2 items-start text-xs text-slate-700 font-medium">
                          <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400 shrink-0 mt-0.5" />
                          <span>{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-50/30">
              <div className="w-14 h-14 bg-slate-100 rounded-2xl flex items-center justify-center mb-3 border border-slate-200">
                <Users className="w-6 h-6 text-slate-300" />
              </div>
              <h3 className="text-sm sm:text-base font-bold text-slate-900">No Candidate Selected</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Select an applicant from the list to see their complete resume information and score breakdown.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Floating Action Bar (< 1024px) when 2+ candidates selected */}
      {selectedCandidateIds.length >= 2 && (
        <div className="lg:hidden fixed bottom-4 inset-x-3.5 z-40 bg-slate-900/95 backdrop-blur-md text-white p-3 rounded-2xl shadow-2xl border border-slate-800 flex items-center justify-between animate-in slide-in-from-bottom-4">
          <div className="flex items-center gap-2.5">
            <span className="w-7 h-7 rounded-xl bg-[#D60041] text-white flex items-center justify-center font-semibold text-xs shadow-xs">
              {selectedCandidateIds.length}
            </span>
            <div>
              <p className="text-xs font-bold leading-none text-white">Candidates Ready</p>
              <p className="text-xs text-slate-500 leading-none mt-0.5">Tap to compare side-by-side</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsComparing(true)}
            className="px-4 py-2 bg-[#D60041] hover:bg-rose-700 text-white font-bold text-xs rounded-xl flex items-center gap-1.5 shadow-sm active:scale-95 transition-all cursor-pointer"
          >
            <TrendingUp size={14} />
            <span>Compare Now</span>
          </button>
        </div>
      )}
    </div>
  );

  return (
    <div className="bg-[#F8FAFC] text-slate-800 antialiased min-h-screen font-sans flex flex-col selection:bg-rose-100 selection:text-[#D60041]">
      <Helmet>
        <title>Candidate Comparison | Mariwasa Recruitment HR Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className={styles.workspace}>
          {isComparing ? renderComparisonView() : renderSelectionView()}
        </main>
      </div>
    </div>
  );
};

export default CompareCandidates;
