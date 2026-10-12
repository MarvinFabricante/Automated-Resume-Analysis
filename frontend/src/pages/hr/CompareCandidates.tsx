import React, { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Search, CheckCircle2, XCircle, Users, ArrowLeft, Award, TrendingUp, AlertTriangle,
  Mail, Phone, MapPin, Briefcase, Star, Zap, BarChart3, Trophy, Sparkles,
  Check, Plus, Trash2, User, Table, LayoutGrid, SlidersHorizontal
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useGetApplicationsQuery, useGetJobsQuery } from '../../redux/api/apiSlice';
import { getAssetUrl } from '../../services/api';
import { Job, Application } from '../../types';

interface CandidateComparisonData extends Partial<Application> {
  id: number;
  name: string;
  preferredJob?: string;
  email?: string;
  phone?: string;
  location?: string;
  company?: string;
  relevance?: string;
  experience_reason?: string;
  skills?: string[];
  matched_skills?: string[];
  missing_skills?: string[];
  strengths?: string[];
  weaknesses?: string[];
  recommendations?: string[];
  skillsScore?: number;
  experienceScore?: number;
  certificationsScore?: number;
  certifications_score?: number;
  candidate_certifications?: string;
  certifications?: string;
  certifications_reason?: string;
  matchScore?: number;
  ai_summary?: string;
  profileImage?: string;
  isRuleBased?: boolean;
}

interface EvaluationFilters {
  skills: boolean;
  experience: boolean;
  certifications: boolean;
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
  filters: EvaluationFilters
): CandidateComparisonData => {
  let skillsScore = 0;
  let expScore = 0;
  let certScore = 0;
  let matchedSkills = candidate.matched_skills || [];
  let missingSkills = candidate.missing_skills || [];

  if (job) {
    // 1. Skills Matching
    let jobSkills: string[] = [];
    if (job.skills_requirements) {
      jobSkills = Array.isArray(job.skills_requirements)
        ? job.skills_requirements.map((s: string) => s.trim().toLowerCase()).filter(Boolean)
        : job.skills_requirements.split(',').map((s: string) => s.trim().toLowerCase()).filter(Boolean);
    } else {
      jobSkills = job.title.toLowerCase().split(' ').filter(w => w.length > 2);
    }

    const candidateSkills = (candidate.skills || []).map(s => s.toLowerCase());
    matchedSkills = [];
    missingSkills = [];

    if (jobSkills.length > 0) {
      let matchCount = 0;
      jobSkills.forEach(reqSkill => {
        const hasSkill = candidateSkills.some(cs => cs.includes(reqSkill) || reqSkill.includes(cs));
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

    // 2. Experience Matching
    const jobExp = (job.experience_requirements || '').toLowerCase();
    const candExp = ((candidate.relevance || '') + ' ' + (candidate.experience_reason || '')).toLowerCase();

    if (jobExp) {
      const expKeywords = jobExp.split(/[\s,]+/).filter(w => w.length > 3);
      if (expKeywords.length > 0) {
        const matchCount = expKeywords.filter(kw => candExp.includes(kw)).length;
        expScore = Math.round((matchCount / expKeywords.length) * 100);
      } else {
        expScore = 80;
      }
    } else {
      expScore = candidate.experienceScore || 0;
    }

    // 3. Certifications Matching
    const jobCert = (job.certifications_requirements || '').toLowerCase();
    const candCert = ((candidate.candidate_certifications || '') + ' ' + (candidate.certifications || '') + ' ' + (candidate.skills || '')).toLowerCase();

    if (jobCert) {
      const certKeywords = jobCert.split(/[\s,]+/).filter(w => w.length > 3 && !['certification', 'certified'].includes(w));
      if (certKeywords.length > 0) {
        const matchCount = certKeywords.filter(kw => candCert.includes(kw)).length;
        certScore = Math.round((matchCount / certKeywords.length) * 100);
      } else {
        certScore = 80;
      }
    } else {
      certScore = candidate.certifications_score || candidate.certificationsScore || 0;
    }
  } else {
    // AI Scores
    skillsScore = candidate.skillsScore || 0;
    expScore = candidate.experienceScore || 0;
    certScore = candidate.certifications_score || candidate.certificationsScore || 0;
  }

  let totalWeight = 0;
  let rawScore = 0;

  if (filters?.skills) {
    totalWeight += 50;
    rawScore += skillsScore * 50;
  }
  if (filters?.experience) {
    totalWeight += 30;
    rawScore += expScore * 30;
  }
  if (filters?.certifications) {
    totalWeight += 20;
    rawScore += certScore * 20;
  }

  const matchScore = totalWeight > 0 ? Math.round(rawScore / totalWeight) : 0;

  return {
    ...candidate,
    matchScore,
    skillsScore,
    experienceScore: expScore,
    certificationsScore: certScore,
    matched_skills: matchedSkills.length > 0 ? matchedSkills : candidate.matched_skills,
    missing_skills: missingSkills.length > 0 ? missingSkills : candidate.missing_skills,
    isRuleBased: !!job
  };
};

const CompareCandidates: React.FC = () => {
  const { data: candidates = [], isLoading } = useGetApplicationsQuery();
  const { data: jobs = [] } = useGetJobsQuery();
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchParams] = useSearchParams();
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<number[]>([]);
  const [activeCandidateId, setActiveCandidateId] = useState<number | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [evaluationFilters, setEvaluationFilters] = useState<EvaluationFilters>({
    skills: true,
    experience: true,
    certifications: true
  });

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

  // Filter candidates based on search
  const filteredCandidates = useMemo(() => {
    return (candidates as CandidateComparisonData[]).filter(c => {
      const q = searchQuery.toLowerCase();
      const skillsMatch = c.skills && c.skills.some(s => s.toLowerCase().includes(q));
      return (
        c.name.toLowerCase().includes(q) ||
        (c.preferredJob && c.preferredJob.toLowerCase().includes(q)) ||
        skillsMatch
      );
    });
  }, [candidates, searchQuery]);

  // Set the first candidate as active by default if not set
  useEffect(() => {
    if (filteredCandidates.length > 0 && !activeCandidateId) {
      setActiveCandidateId(filteredCandidates[0].id);
    }
  }, [filteredCandidates, activeCandidateId]);

  const activeCandidate = useMemo(() => {
    return (candidates as CandidateComparisonData[]).find(c => c.id === activeCandidateId) || filteredCandidates[0] || null;
  }, [candidates, activeCandidateId, filteredCandidates]);

  const toggleSelection = (id: number) => {
    if (selectedCandidateIds.includes(id)) {
      setSelectedCandidateIds(prev => prev.filter(cId => cId !== id));
    } else {
      setSelectedCandidateIds(prev => [...prev, id]);
    }
  };

  const clearSelected = () => {
    setSelectedCandidateIds([]);
  };

  const selectedCandidatesData = useMemo(() => {
    const selected = (candidates as CandidateComparisonData[]).filter(c => selectedCandidateIds.includes(c.id));
    const selectedJob = (jobs as Job[]).find(j => j.id === parseInt(selectedJobId) || String(j.id) === selectedJobId);

    // Calculate score to reflect filter preferences even if job isn't selected
    const scoredCandidates = selected.map(c => calculateRuleBasedScore(c, selectedJob, evaluationFilters));

    // Sort by match score descending to automatically rank them
    return [...scoredCandidates].sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));
  }, [candidates, selectedCandidateIds, jobs, selectedJobId, evaluationFilters]);

  const categoryWinners = useMemo(() => {
    if (selectedCandidatesData.length === 0) return {};

    const getWinner = (key: 'skillsScore' | 'experienceScore' | 'certificationsScore') => {
      let maxScore = -1;
      let winner: CandidateComparisonData | null = null;
      selectedCandidatesData.forEach(c => {
        if ((c[key] || 0) > maxScore) {
          maxScore = c[key] || 0;
          winner = c;
        }
      });
      return winner;
    };

    return {
      skills: getWinner('skillsScore'),
      experience: getWinner('experienceScore'),
      certifications: getWinner('certificationsScore')
    };
  }, [selectedCandidatesData]);

  const winner = useMemo(() => {
    if (selectedCandidatesData.length === 0) return null;
    return selectedCandidatesData[0]; // Highest score
  }, [selectedCandidatesData]);

  const renderComparisonView = () => {
    if (!winner) return null;

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

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 sm:gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight">
                Side-by-Side Comparison
              </h1>
              <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5 sm:mt-1">
                Comparing {selectedCandidatesData.length} selected candidates for role suitability.
              </p>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto">
              <div className="px-3 py-1.5 bg-rose-50 border border-rose-100 rounded-xl text-[11px] sm:text-xs font-bold text-[#D60041] flex items-center gap-1.5 shadow-2xs">
                <Sparkles className="w-3.5 h-3.5" />
                <span>AI Ranked & Evaluated</span>
              </div>
            </div>
          </div>
        </div>

        {/* AI Recommendation / Winner Banner */}
        <div className="bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white rounded-2xl sm:rounded-3xl p-4 sm:p-7 md:p-8 mb-5 sm:mb-8 shadow-xl relative overflow-hidden border border-slate-800">
          <div className="absolute -right-10 -top-10 w-40 h-40 bg-[#D60041]/20 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute -left-10 -bottom-10 w-40 h-40 bg-blue-500/15 rounded-full blur-3xl pointer-events-none"></div>

          <div className="relative flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 sm:gap-6">
            <div className="flex-1">
              <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#D60041]/25 border border-[#D60041]/40 rounded-full text-[10px] sm:text-xs font-black text-[#FF3E74] uppercase tracking-wider mb-2 sm:mb-3">
                <Trophy className="w-3.5 h-3.5 text-amber-400" />
                <span>Top Recommended Match</span>
              </div>
              <h2 className="text-lg sm:text-2xl md:text-3xl font-black tracking-tight leading-tight">
                {winner.name} is the top match!
              </h2>
              <p className="text-slate-300 font-medium mt-1.5 sm:mt-2 max-w-3xl leading-relaxed text-xs sm:text-sm">
                Based on our {winner.isRuleBased ? 'rule-based analysis' : 'semantic AI analysis'} of skills, experience, and educational background, <span className="text-white font-bold">{winner.name}</span> has the highest matching index of <span className="text-[#FF3E74] font-black">{winner.matchScore}%</span>.
                {winner.ai_summary ? ` ${winner.ai_summary}` : ` Strong alignment demonstrated with requirements for ${winner.preferredJob}.`}
              </p>
            </div>

            {/* Mobile-Friendly Winner Snapshot Card */}
            <div className="bg-white/5 border border-white/10 p-3.5 sm:p-5 rounded-2xl shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl overflow-hidden border border-white/20 shrink-0 bg-white/10">
                  <img
                    src={getAvatarUrl(winner)}
                    alt={winner.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      (e.target as HTMLImageElement).src = `https://ui-avatars.com/api/?name=${encodeURIComponent(winner.name)}&background=fdf2f8&color=d81159&bold=true`;
                    }}
                  />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="text-xs sm:text-sm font-bold text-white truncate max-w-[150px] sm:max-w-[200px]">{winner.name}</p>
                    <span className="px-1.5 py-0.5 bg-amber-400/20 text-amber-300 border border-amber-400/30 rounded text-[9px] font-black uppercase shrink-0">#1 Top</span>
                  </div>
                  <p className="text-[11px] text-slate-300 font-semibold truncate mt-0.5">{winner.preferredJob}</p>
                </div>
              </div>

              <div className="flex items-center justify-between sm:justify-end gap-3 pt-2.5 sm:pt-0 border-t sm:border-t-0 border-white/10">
                <div className="text-left sm:text-right">
                  <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Match Score</p>
                  <p className="text-2xl sm:text-4xl font-black text-[#FF3E74] leading-tight">{winner.matchScore}%</p>
                </div>
                <div className="flex flex-wrap sm:flex-col gap-1 sm:gap-1 text-[9px] font-bold">
                  <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded border border-blue-500/30">Skills: {winner.skillsScore}%</span>
                  <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded border border-purple-500/30">Exp: {winner.experienceScore}%</span>
                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded border border-amber-500/30">Certs: {winner.certificationsScore || 0}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Category Winners Filter Display */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-4 mb-5 sm:mb-7">
          {evaluationFilters.skills && categoryWinners.skills && (
            <div className="bg-blue-50/60 border border-blue-100 rounded-2xl p-3 sm:p-4 flex items-center justify-between shadow-2xs">
              <div className="flex items-center gap-2.5 min-w-0">
                <div className="p-2 bg-blue-100 text-blue-600 rounded-xl shrink-0">
                  <Zap className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <p className="text-[9px] sm:text-[10px] font-black text-slate-400 uppercase tracking-wider">Top Skills Match</p>
                  <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.skills.name}</p>
                </div>
              </div>
              <span className="px-2 py-1 bg-blue-100/80 text-blue-700 rounded-lg text-xs font-black shrink-0">
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
                  <p className="text-[9px] sm:text-[10px] font-black text-slate-400 uppercase tracking-wider">Top Experience</p>
                  <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.experience.name}</p>
                </div>
              </div>
              <span className="px-2 py-1 bg-purple-100/80 text-purple-700 rounded-lg text-xs font-black shrink-0">
                {categoryWinners.experience.experienceScore}%
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
                  <p className="text-[9px] sm:text-[10px] font-black text-slate-400 uppercase tracking-wider">Top Certifications</p>
                  <p className="text-xs sm:text-sm font-bold text-slate-800 truncate">{categoryWinners.certifications.name}</p>
                </div>
              </div>
              <span className="px-2 py-1 bg-amber-100/80 text-amber-700 rounded-lg text-xs font-black shrink-0">
                {categoryWinners.certifications.certificationsScore || 0}%
              </span>
            </div>
          )}
        </div>

        {/* View Mode Switcher for Mobile & Tablet */}
        <div className="flex items-center justify-between gap-2 mb-3 sm:mb-4">
          <div className="flex items-center gap-2 min-w-0">
            <h3 className="text-xs sm:text-base font-black text-slate-900 tracking-tight truncate">Comparison Results</h3>
            <span className="text-[10px] sm:text-[11px] font-bold text-slate-400 shrink-0">({selectedCandidatesData.length})</span>
          </div>

          {/* Toggle between Sticky Matrix Table and Card Scorecards with intact labels */}
          <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200/80 shrink-0 shadow-2xs">
            <button
              type="button"
              onClick={() => setCompareViewMode('table')}
              className={`px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] sm:text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                compareViewMode === 'table' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Side-by-side Table Matrix"
            >
              <Table size={13} className={compareViewMode === 'table' ? 'text-[#D60041]' : ''} />
              <span>Table Matrix</span>
            </button>
            <button
              type="button"
              onClick={() => setCompareViewMode('cards')}
              className={`px-2.5 sm:px-3 py-1.5 rounded-lg text-[11px] sm:text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                compareViewMode === 'cards' ? 'bg-white text-slate-900 shadow-2xs' : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Card Scorecards"
            >
              <LayoutGrid size={13} className={compareViewMode === 'cards' ? 'text-[#D60041]' : ''} />
              <span>Scorecards</span>
            </button>
          </div>
        </div>

        {/* 1. TABLE MATRIX VIEW (With Sticky Left Criteria Column) */}
        {compareViewMode === 'table' ? (
          <div>
            {/* Mobile swipe helper badge (< sm) */}
            <div className="sm:hidden flex items-center justify-between px-3 py-1.5 bg-rose-50/70 border border-rose-100 rounded-xl mb-2.5 text-[11px] font-bold text-rose-800 shadow-2xs">
              <span className="flex items-center gap-1.5">
                <span>↔</span>
                <span>Swipe left/right to compare</span>
              </span>
              <span className="text-[10px] bg-white px-2 py-0.5 rounded-md border border-rose-200/70 text-[#D60041] font-black">
                Labels Pinned
              </span>
            </div>

            <div className="bg-white border border-slate-200/90 rounded-2xl sm:rounded-3xl shadow-xs overflow-hidden">
              <div className="overflow-x-auto custom-scrollbar relative overscroll-x-contain">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-slate-50/90 border-b border-slate-200/90">
                      {/* Sticky Column 1 Header with fixed intact width */}
                      <th className="sticky left-0 z-30 bg-slate-100/95 backdrop-blur-md p-3 sm:p-5 text-left text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5">
                          <SlidersHorizontal size={13} className="text-slate-500 shrink-0" />
                          <span>Criteria</span>
                        </div>
                      </th>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <th
                          key={candidate.id}
                          className={`p-3 sm:p-5 text-left min-w-[210px] max-w-[250px] sm:min-w-[270px] relative snap-start ${
                            idx === 0 ? 'bg-rose-50/25' : ''
                          }`}
                        >
                          {idx === 0 && (
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
                              <div className="flex items-center gap-1.5">
                                <span className={`px-1.5 py-0.5 rounded text-[9px] font-black uppercase shrink-0 ${
                                  idx === 0 ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                                }`}>
                                  Rank #{idx + 1}
                                </span>
                                {idx === 0 && <Trophy className="w-3 h-3 text-amber-500 shrink-0" />}
                              </div>
                              <h4 className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate mt-0.5">{candidate.name}</h4>
                              <p className="text-[10px] sm:text-[11px] text-slate-500 font-semibold truncate">{candidate.preferredJob}</p>
                            </div>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>

                  <tbody className="divide-y divide-slate-100">
                    {/* Row 1: Match Percentage */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <TrendingUp size={13} className="text-[#D60041] shrink-0" />
                          <span>Match Score</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="flex items-center gap-2 sm:gap-3">
                            <span className={`text-lg sm:text-2xl font-black ${idx === 0 ? 'text-[#D60041]' : 'text-slate-900'}`}>
                              {candidate.matchScore}%
                            </span>
                            <div className="flex-1 max-w-[80px] sm:max-w-[120px] bg-slate-100 rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${idx === 0 ? 'bg-[#D60041]' : 'bg-slate-700'}`}
                                style={{ width: `${candidate.matchScore}%` }}
                              />
                            </div>
                          </div>
                          {idx === 0 && (
                            <span className="text-[9px] font-black text-[#D60041] uppercase tracking-wider mt-1 block">Top Match</span>
                          )}
                        </td>
                      ))}
                    </tr>

                    {/* Row 2: Pillar Scores */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <BarChart3 size={13} className="text-blue-500 shrink-0" />
                          <span>Pillar Scores</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 space-y-2 sm:space-y-2.5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div>
                            <div className="flex justify-between text-[10px] sm:text-[11px] font-bold mb-0.5">
                              <span className={evaluationFilters.skills ? 'text-slate-600' : 'text-slate-300 line-through'}>Skills</span>
                              <span className="text-blue-600">{candidate.skillsScore}%</span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-1.5">
                              <div className="h-1.5 rounded-full bg-blue-500" style={{ width: `${candidate.skillsScore}%` }} />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[10px] sm:text-[11px] font-bold mb-0.5">
                              <span className={evaluationFilters.experience ? 'text-slate-600' : 'text-slate-300 line-through'}>Experience</span>
                              <span className="text-purple-600">{candidate.experienceScore}%</span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-1.5">
                              <div className="h-1.5 rounded-full bg-purple-500" style={{ width: `${candidate.experienceScore}%` }} />
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-[10px] sm:text-[11px] font-bold mb-0.5">
                              <span className={evaluationFilters.certifications ? 'text-slate-600' : 'text-slate-300 line-through'}>Certifications</span>
                              <span className="text-amber-600">{candidate.certificationsScore || 0}%</span>
                            </div>
                            <div className="w-full bg-slate-100 rounded-full h-1.5">
                              <div className="h-1.5 rounded-full bg-amber-500" style={{ width: `${candidate.certificationsScore || 0}%` }} />
                            </div>
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* Row 3: Matched Skills */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <CheckCircle2 size={13} className="text-emerald-500 shrink-0" />
                          <span>Matched Skills</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="flex flex-wrap gap-1 sm:gap-1.5">
                            {candidate.matched_skills && candidate.matched_skills.length > 0 ? (
                              candidate.matched_skills.map((skill, i) => (
                                <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 sm:px-2.5 sm:py-1 bg-emerald-50 text-emerald-700 border border-emerald-200/80 rounded-md text-[9px] sm:text-[10px] font-bold">
                                  <Check className="w-2.5 h-2.5" />
                                  <span>{skill}</span>
                                </span>
                              ))
                            ) : (
                              <span className="text-[11px] text-slate-400 italic">None matched</span>
                            )}
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* Row 4: Missing Skills */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
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
                                <span key={i} className="inline-flex items-center gap-1 px-1.5 py-0.5 sm:px-2.5 sm:py-1 bg-rose-50 text-rose-700 border border-rose-200/80 rounded-md text-[9px] sm:text-[10px] font-bold">
                                  <XCircle className="w-2.5 h-2.5" />
                                  <span>{skill}</span>
                                </span>
                              ))
                            ) : (
                              <span className="text-[11px] text-emerald-600 font-bold">All Requirements Met</span>
                            )}
                          </div>
                        </td>
                      ))}
                    </tr>

                    {/* Row 5: Core Strengths */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Star size={13} className="text-emerald-500 shrink-0" />
                          <span>Strengths</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <ul className="space-y-1 sm:space-y-1.5 text-[11px] sm:text-xs text-slate-700 font-medium">
                            {(candidate.strengths && candidate.strengths.slice(0, 3).map((strength, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0 stroke-[2.5px]" />
                                <span>{strength}</span>
                              </li>
                            ))) || <span className="italic text-slate-400">N/A</span>}
                          </ul>
                        </td>
                      ))}
                    </tr>

                    {/* Row 6: Gaps & Weaknesses */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <AlertTriangle size={13} className="text-amber-500 shrink-0" />
                          <span>Gaps & Weaknesses</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <ul className="space-y-1 sm:space-y-1.5 text-[11px] sm:text-xs text-slate-700 font-medium">
                            {(candidate.weaknesses && candidate.weaknesses.slice(0, 3).map((weakness, i) => (
                              <li key={i} className="flex items-start gap-1.5">
                                <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                                <span>{weakness}</span>
                              </li>
                            ))) || <span className="italic text-slate-400">N/A</span>}
                          </ul>
                        </td>
                      ))}
                    </tr>

                    {/* Row 7: Experience Relevance */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Briefcase size={13} className="text-purple-500 shrink-0" />
                          <span>Experience</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 text-[11px] sm:text-xs text-slate-700 leading-relaxed ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <span className="font-bold text-slate-900 block">{candidate.company || "Company Unspecified"}</span>
                          <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">{candidate.relevance || "Role unspecified"}</span>
                          <p className="line-clamp-3 text-slate-500 text-[10px] sm:text-[11px]">{candidate.experience_reason || "No details provided"}</p>
                        </td>
                      ))}
                    </tr>

                    {/* Row 8: Certifications */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Award size={13} className="text-amber-500 shrink-0" />
                          <span>Certifications</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 text-[11px] sm:text-xs text-slate-700 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <p className="font-bold text-slate-900">{candidate.candidate_certifications || candidate.certifications || "None specified"}</p>
                          <p className="text-[10px] text-slate-400 mt-0.5 italic">{candidate.certifications_reason}</p>
                        </td>
                      ))}
                    </tr>

                    {/* Row 9: Contact Details */}
                    <tr className="hover:bg-slate-50/40 transition-colors">
                      <td className="sticky left-0 z-20 bg-slate-50/95 backdrop-blur-md p-3 sm:p-5 text-[11px] sm:text-xs font-black text-slate-700 uppercase tracking-wider w-[125px] min-w-[125px] max-w-[125px] sm:w-56 sm:min-w-[220px] sm:max-w-[220px] shrink-0 border-r-2 border-slate-200 shadow-[3px_0_8px_rgba(0,0,0,0.05)]">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Mail size={13} className="text-slate-500 shrink-0" />
                          <span>Contact Info</span>
                        </div>
                      </td>
                      {selectedCandidatesData.map((candidate, idx) => (
                        <td key={candidate.id} className={`p-3 sm:p-5 space-y-1.5 text-[11px] sm:text-xs text-slate-600 ${idx === 0 ? 'bg-rose-50/15' : ''}`}>
                          <div className="flex items-center gap-1.5 truncate">
                            <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate">{candidate.email || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-1.5 truncate">
                            <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate">{candidate.phone || 'N/A'}</span>
                          </div>
                          <div className="flex items-center gap-1.5 truncate">
                            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate">{candidate.location || 'N/A'}</span>
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
                  className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                    scorecardFilter === 'all'
                      ? 'bg-slate-900 text-white shadow-2xs'
                      : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  All Candidates ({selectedCandidatesData.length})
                </button>
                {selectedCandidatesData.map((cand, i) => (
                  <button
                    key={cand.id}
                    type="button"
                    onClick={() => setScorecardFilter(cand.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all flex items-center gap-1.5 cursor-pointer ${
                      scorecardFilter === cand.id
                        ? 'bg-[#D60041] text-white shadow-2xs'
                        : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    {i === 0 && <Trophy size={11} className={scorecardFilter === cand.id ? 'text-amber-300' : 'text-amber-500'} />}
                    <span>{cand.name.split(' ')[0]}</span>
                    <span className="text-[10px] opacity-80 font-black">({cand.matchScore}%)</span>
                  </button>
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
              {displayedCandidatesInScorecards.map((candidate) => {
                const actualRank = selectedCandidatesData.findIndex(c => c.id === candidate.id) + 1;
                const isTopMatch = actualRank === 1;

                return (
                  <div
                    key={candidate.id}
                    className={`bg-white border rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-xs flex flex-col justify-between transition-all ${
                      isTopMatch ? 'border-rose-200 ring-2 ring-rose-100 shadow-md' : 'border-slate-200/90'
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
                            <p className="text-xs text-slate-500 font-semibold truncate mt-0.5">{candidate.preferredJob}</p>
                          </div>
                        </div>

                        <div className="text-right shrink-0">
                          <span className={`inline-flex items-center gap-1 text-[10px] font-black uppercase px-2 py-0.5 rounded-full ${
                            isTopMatch ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
                          }`}>
                            {isTopMatch && <Trophy size={11} className="text-amber-600" />}
                            Rank #{actualRank}
                          </span>
                          <p className="text-2xl font-black text-[#D60041] mt-0.5 leading-tight">{candidate.matchScore}%</p>
                        </div>
                      </div>

                      {/* 3 Pillar Breakdown Cards */}
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1.5">Pillar Scores</p>
                        <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
                          <div className="bg-blue-50/60 border border-blue-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-black text-blue-700">{candidate.skillsScore}%</p>
                            <p className="text-[9px] font-bold text-slate-400 uppercase mt-0.5">Skills</p>
                            <div className="w-full bg-blue-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-blue-500" style={{ width: `${candidate.skillsScore}%` }} />
                            </div>
                          </div>
                          <div className="bg-purple-50/60 border border-purple-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-black text-purple-700">{candidate.experienceScore}%</p>
                            <p className="text-[9px] font-bold text-slate-400 uppercase mt-0.5">Exp</p>
                            <div className="w-full bg-purple-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-purple-500" style={{ width: `${candidate.experienceScore}%` }} />
                            </div>
                          </div>
                          <div className="bg-amber-50/60 border border-amber-100/80 rounded-xl p-2 text-center">
                            <p className="text-xs font-black text-amber-700">{candidate.certificationsScore || 0}%</p>
                            <p className="text-[9px] font-bold text-slate-400 uppercase mt-0.5">Certs</p>
                            <div className="w-full bg-amber-100 rounded-full h-1 mt-1">
                              <div className="h-1 rounded-full bg-amber-500" style={{ width: `${candidate.certificationsScore || 0}%` }} />
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* AI Summary / Quote if present */}
                      {candidate.ai_summary && (
                        <div className="bg-rose-50/40 border border-rose-100/80 rounded-xl p-3 text-xs text-slate-700 italic leading-relaxed">
                          <span className="font-bold text-[#D60041] not-italic block text-[10px] uppercase tracking-wider mb-0.5">AI Summary</span>
                          "{candidate.ai_summary}"
                        </div>
                      )}

                      {/* Core Strengths */}
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1.5">Key Strengths</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 space-y-1.5">
                          {candidate.strengths && candidate.strengths.length > 0 ? (
                            candidate.strengths.slice(0, 3).map((strength, i) => (
                              <div key={i} className="flex items-start gap-1.5 text-xs text-slate-700 font-medium leading-snug">
                                <Check className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0 stroke-[2.5px]" />
                                <span>{strength}</span>
                              </div>
                            ))
                          ) : (
                            <p className="text-xs text-slate-400 italic">No specific strengths listed</p>
                          )}
                        </div>
                      </div>

                      {/* Areas for Improvement / Gaps */}
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1.5">Identified Gaps</p>
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
                          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1">Matched Skills</p>
                          <div className="flex flex-wrap gap-1">
                            {candidate.matched_skills && candidate.matched_skills.length > 0 ? (
                              candidate.matched_skills.map((skill, i) => (
                                <span key={i} className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded text-[10px] font-bold">
                                  {skill}
                                </span>
                              ))
                            ) : (
                              <span className="text-slate-400 italic text-[11px]">None</span>
                            )}
                          </div>
                        </div>

                        <div>
                          <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1">Missing Skills</p>
                          <div className="flex flex-wrap gap-1">
                            {candidate.missing_skills && candidate.missing_skills.length > 0 ? (
                              candidate.missing_skills.map((skill, i) => (
                                <span key={i} className="px-2 py-0.5 bg-rose-50 text-rose-700 border border-rose-100 rounded text-[10px] font-bold">
                                  {skill}
                                </span>
                              ))
                            ) : (
                              <span className="text-emerald-600 font-bold text-[11px]">All Required Skills Met</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Work Experience Summary */}
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1">Experience</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 text-xs text-slate-700">
                          <p className="font-bold text-slate-900">{candidate.company || "Company Unspecified"}</p>
                          <p className="text-[10px] uppercase font-bold text-slate-400">{candidate.relevance || "Role unspecified"}</p>
                          {candidate.experience_reason && (
                            <p className="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">{candidate.experience_reason}</p>
                          )}
                        </div>
                      </div>

                      {/* Certifications Summary */}
                      <div>
                        <p className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-1">Certifications</p>
                        <div className="bg-slate-50/70 border border-slate-100 rounded-xl p-2.5 text-xs text-slate-700">
                          <p className="font-bold text-slate-900">{candidate.candidate_certifications || candidate.certifications || "None specified"}</p>
                          {candidate.certifications_reason && (
                            <p className="text-[10px] text-slate-400 mt-0.5 italic">{candidate.certifications_reason}</p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Contact Footer */}
                    <div className="pt-3 mt-4 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
                      <div className="flex items-center gap-1.5 truncate">
                        <Mail size={12} className="text-slate-400 shrink-0" />
                        <span className="truncate">{candidate.email || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1.5 truncate">
                        <Phone size={12} className="text-slate-400 shrink-0" />
                        <span className="truncate">{candidate.phone || 'N/A'}</span>
                      </div>
                      <div className="flex items-center gap-1.5 truncate">
                        <MapPin size={12} className="text-slate-400 shrink-0" />
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
          <p className="text-center sm:text-right text-[11px] text-slate-400 font-medium">
            Comparing {selectedCandidatesData.length} selected candidates
          </p>
        </div>
      </div>
    );
  };

  const renderSelectionView = () => (
    <div className="animate-in fade-in duration-500 flex flex-col min-h-0 lg:h-[calc(100vh-140px)]">
      {/* Top Search and Comparison Info */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 mb-4 sm:mb-6 shrink-0">
        <div>
          <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight">
            Compare Candidates
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-0.5 sm:mt-1">
            Select candidates from the list to view their full resume details, then compare side-by-side.
          </p>
        </div>

        {/* Counter & Compare Button */}
        <div className="flex items-center gap-2.5 sm:gap-3 w-full sm:w-auto">
          <div className="bg-white border border-slate-200/90 rounded-xl sm:rounded-2xl px-3.5 sm:px-5 py-2 sm:py-3 shadow-2xs flex items-center justify-between sm:justify-start gap-2.5 sm:gap-3 flex-1 sm:flex-initial">
            <div className="flex items-center gap-2.5 sm:gap-3">
              <div className="w-7 h-7 sm:w-8 sm:h-8 bg-rose-50 border border-rose-100 text-[#D60041] rounded-xl flex items-center justify-center font-black text-xs sm:text-sm shrink-0">
                {selectedCandidateIds.length}
              </div>
              <div>
                <p className="text-[9px] sm:text-[10px] font-black text-slate-400 uppercase tracking-wider leading-none">Ready</p>
                <p className="text-xs font-bold text-slate-900 leading-tight">Selected</p>
              </div>
            </div>
            {selectedCandidateIds.length > 0 && (
              <button
                type="button"
                onClick={clearSelected}
                className="p-1 hover:bg-rose-50 text-rose-500 rounded-lg hover:text-rose-600 transition-colors ml-1 cursor-pointer"
                title="Clear Selection"
                aria-label="Clear Selection"
              >
                <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </button>
            )}
          </div>

          <button
            type="button"
            disabled={selectedCandidateIds.length < 2}
            onClick={() => setIsComparing(true)}
            className={`flex items-center justify-center gap-2 px-4 sm:px-6 py-2.5 sm:py-3.5 rounded-xl sm:rounded-2xl font-bold text-xs sm:text-sm transition-all shadow-xs flex-1 sm:flex-initial text-center cursor-pointer ${
              selectedCandidateIds.length >= 2
                ? 'bg-slate-900 hover:bg-black text-white hover:scale-[1.02] active:scale-[0.98]'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed border border-slate-200/60'
            }`}
          >
            <TrendingUp className="w-4 h-4 text-[#D60041] shrink-0" />
            <span className="whitespace-nowrap">Compare ({selectedCandidateIds.length})</span>
          </button>
        </div>
      </div>

      {/* Mobile Tab Switcher (< 1024px) */}
      <div className="lg:hidden flex bg-slate-100 p-1 rounded-2xl mb-4 border border-slate-200/80 shadow-2xs shrink-0">
        <button
          type="button"
          onClick={() => setMobileTab('list')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
            mobileTab === 'list'
              ? 'bg-white text-slate-900 shadow-xs'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <Users size={14} className={mobileTab === 'list' ? 'text-[#D60041]' : ''} />
          <span>Candidate List ({filteredCandidates.length})</span>
        </button>
        <button
          type="button"
          onClick={() => setMobileTab('profile')}
          className={`flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer ${
            mobileTab === 'profile'
              ? 'bg-white text-slate-900 shadow-xs'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <User size={14} className={mobileTab === 'profile' ? 'text-[#D60041]' : ''} />
          <span className="truncate">{activeCandidate ? activeCandidate.name.split(' ')[0] + "'s Details" : 'Preview Profile'}</span>
        </button>
      </div>

      {/* Split-Screen Selection Area */}
      <div className="flex flex-col lg:flex-row flex-1 gap-4 sm:gap-6 min-h-0 mb-6 lg:overflow-hidden">

        {/* LEFT COLUMN: Candidate Search and List */}
        <div
          className={`w-full lg:w-[380px] bg-white border border-slate-200/90 rounded-2xl sm:rounded-3xl shadow-xs flex flex-col shrink-0 overflow-hidden ${
            mobileTab === 'list' ? 'flex' : 'hidden lg:flex'
          } max-h-[560px] lg:max-h-none`}
        >
          <div className="p-3.5 sm:p-4 border-b border-slate-100 bg-slate-50/50 shrink-0 space-y-3">
            {/* Job Profile Filter */}
            <div>
              <label className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-500 mb-1.5 block">
                Compare Against Job Profile
              </label>
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-[#D60041] transition-all font-semibold text-xs sm:text-sm text-slate-800 cursor-pointer"
              >
                <option value="">-- Use Original AI Match Scores --</option>
                {(jobs as Job[]).map(job => (
                  <option key={job.id} value={job.id}>{job.title}</option>
                ))}
              </select>
            </div>

            {/* Evaluation Criteria Checklist */}
            <div>
              <label className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-500 mb-1.5 block">
                Evaluation Criteria
              </label>
              <div className="grid grid-cols-3 gap-1.5 sm:gap-2">
                <button
                  type="button"
                  onClick={() => setEvaluationFilters(prev => ({ ...prev, skills: !prev.skills }))}
                  className={`flex items-center justify-center gap-1.5 px-2 py-1.5 sm:py-2 rounded-xl border text-[10px] sm:text-xs font-bold transition-all cursor-pointer ${
                    evaluationFilters.skills
                      ? 'bg-blue-50 text-blue-700 border-blue-200 shadow-2xs'
                      : 'bg-white text-slate-400 border-slate-200 hover:text-slate-600'
                  }`}
                >
                  <div className={`w-3.5 h-3.5 rounded flex items-center justify-center transition-all ${
                    evaluationFilters.skills ? 'bg-blue-600 text-white' : 'border border-slate-300'
                  }`}>
                    {evaluationFilters.skills && <Check className="w-2.5 h-2.5 stroke-[3px]" />}
                  </div>
                  <span>Skills</span>
                </button>

                <button
                  type="button"
                  onClick={() => setEvaluationFilters(prev => ({ ...prev, experience: !prev.experience }))}
                  className={`flex items-center justify-center gap-1.5 px-2 py-1.5 sm:py-2 rounded-xl border text-[10px] sm:text-xs font-bold transition-all cursor-pointer ${
                    evaluationFilters.experience
                      ? 'bg-purple-50 text-purple-700 border-purple-200 shadow-2xs'
                      : 'bg-white text-slate-400 border-slate-200 hover:text-slate-600'
                  }`}
                >
                  <div className={`w-3.5 h-3.5 rounded flex items-center justify-center transition-all ${
                    evaluationFilters.experience ? 'bg-purple-600 text-white' : 'border border-slate-300'
                  }`}>
                    {evaluationFilters.experience && <Check className="w-2.5 h-2.5 stroke-[3px]" />}
                  </div>
                  <span>Experience</span>
                </button>

                <button
                  type="button"
                  onClick={() => setEvaluationFilters(prev => ({ ...prev, certifications: !prev.certifications }))}
                  className={`flex items-center justify-center gap-1.5 px-2 py-1.5 sm:py-2 rounded-xl border text-[10px] sm:text-xs font-bold transition-all cursor-pointer ${
                    evaluationFilters.certifications
                      ? 'bg-amber-50 text-amber-700 border-amber-200 shadow-2xs'
                      : 'bg-white text-slate-400 border-slate-200 hover:text-slate-600'
                  }`}
                >
                  <div className={`w-3.5 h-3.5 rounded flex items-center justify-center transition-all ${
                    evaluationFilters.certifications ? 'bg-amber-600 text-white' : 'border border-slate-300'
                  }`}>
                    {evaluationFilters.certifications && <Check className="w-2.5 h-2.5 stroke-[3px]" />}
                  </div>
                  <span>Certs</span>
                </button>
              </div>
            </div>

            {/* Candidate Search Box */}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search candidates or skills..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-[#D60041] transition-all font-semibold text-xs sm:text-sm text-slate-800"
              />
            </div>
          </div>

          {/* Scrollable Candidate Items List */}
          <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2 space-y-1 custom-scrollbar">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-16">
                <div className="w-8 h-8 border-3 border-rose-100 border-t-[#D60041] rounded-full animate-spin mb-2"></div>
                <p className="text-slate-400 text-xs font-bold">Loading applicants...</p>
              </div>
            ) : filteredCandidates.length === 0 ? (
              <div className="text-center py-12 px-4">
                <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-2.5 border border-slate-100">
                  <Users className="w-5 h-5 text-slate-300" />
                </div>
                <h4 className="text-xs sm:text-sm font-bold text-slate-800">No candidates found</h4>
                <p className="text-[11px] text-slate-400 mt-0.5">Try searching another name or skill.</p>
              </div>
            ) : (
              filteredCandidates.map(candidate => {
                const isSelected = selectedCandidateIds.includes(candidate.id);
                const isActive = activeCandidateId === candidate.id;

                return (
                  <div
                    key={candidate.id}
                    onClick={() => {
                      setActiveCandidateId(candidate.id);
                      if (window.innerWidth < 1024) setMobileTab('profile');
                    }}
                    className={`p-3 rounded-xl border transition-all duration-200 cursor-pointer flex items-center gap-2.5 sm:gap-3 relative group ${
                      isActive
                        ? 'bg-rose-50/30 border-[#D60041]/30 shadow-2xs'
                        : 'bg-white border-transparent hover:bg-slate-50'
                    }`}
                  >
                    {/* Checkbox for Selection */}
                    <div
                      className="shrink-0 cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelection(candidate.id);
                      }}
                    >
                      <div className={`w-5 h-5 sm:w-6 sm:h-6 rounded-lg border-2 flex items-center justify-center transition-all ${
                        isSelected
                          ? 'bg-[#D60041] border-[#D60041] shadow-xs'
                          : 'border-slate-300 bg-white group-hover:border-[#D60041]'
                      }`}>
                        {isSelected && <Check className="w-3 h-3 text-white stroke-[3.5px]" />}
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <h4 className="text-xs sm:text-sm font-bold text-slate-900 truncate tracking-tight">{candidate.name}</h4>
                      <p className="text-[11px] text-slate-500 font-semibold truncate mt-0.5">{candidate.preferredJob}</p>

                      {candidate.skills && candidate.skills.length > 0 && (
                        <div className="flex gap-1 overflow-hidden mt-1">
                          {candidate.skills.slice(0, 3).map((skill, idx) => (
                            <span key={idx} className="px-1.5 py-0.2 bg-slate-50 text-slate-500 border border-slate-100 rounded text-[9px] font-bold truncate">
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="text-right shrink-0">
                      <span className={`text-xs font-black px-2 py-0.5 rounded-lg ${
                        (candidate.matchScore || 0) >= 85
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                          : (candidate.matchScore || 0) >= 70
                            ? 'bg-amber-50 text-amber-700 border border-amber-100'
                            : 'bg-slate-50 text-slate-600 border border-slate-100'
                      }`}>
                        {calculateRuleBasedScore(candidate, (jobs as Job[]).find(j => j.id === parseInt(selectedJobId) || String(j.id) === selectedJobId), evaluationFilters).matchScore || 0}%
                      </span>
                    </div>

                    {isActive && (
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-[#D60041] rounded-l-full" />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Full Resume Details (Detailed Profile View) */}
        <div
          className={`flex-1 bg-white border border-slate-200/90 rounded-2xl sm:rounded-3xl shadow-xs flex flex-col min-h-0 ${
            mobileTab === 'profile' ? 'flex' : 'hidden lg:flex'
          } overflow-hidden`}
        >
          {/* Mobile Back to List Button (< 1024px) */}
          <div className="lg:hidden p-3 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between shrink-0">
            <button
              type="button"
              onClick={() => setMobileTab('list')}
              className="flex items-center gap-1.5 text-xs font-bold text-slate-600 hover:text-[#D60041] transition-colors cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Candidates List</span>
            </button>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Candidate Details</span>
          </div>

          {activeCandidate ? (
            <div className="flex-grow flex flex-col min-h-0 overflow-y-auto lg:overflow-hidden lg:h-full">
              {/* Profile Card Header */}
              <div className="p-4 sm:p-6 lg:p-7 border-b border-slate-100 bg-slate-50/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-6 shrink-0">
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
                    <h2 className="text-base sm:text-2xl font-black text-slate-900 tracking-tight leading-tight truncate">
                      {activeCandidate.name}
                    </h2>
                    <p className="text-xs sm:text-sm text-slate-500 font-semibold mt-0.5 truncate">{activeCandidate.preferredJob}</p>
                    <div className="flex flex-wrap items-center gap-2 mt-1 sm:mt-1.5">
                      <div className="flex items-center gap-1 text-[10px] sm:text-[11px] text-slate-400 font-bold uppercase truncate">
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{activeCandidate.location || 'N/A'}</span>
                      </div>
                      <div className="w-1 h-1 rounded-full bg-slate-300"></div>
                      <div className="flex items-center gap-1 text-[10px] sm:text-[11px] text-slate-400 font-bold uppercase truncate">
                        <Mail className="w-3.5 h-3.5 shrink-0" />
                        <span className="truncate">{activeCandidate.email || "N/A"}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Score & Add/Remove to Comparison Button */}
                <div className="flex items-center justify-between sm:justify-end gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                  <div className="text-left sm:text-right">
                    <p className="text-[9px] sm:text-[10px] font-black text-slate-400 uppercase tracking-wider">Suitability</p>
                    <p className="text-xl sm:text-2xl font-black text-[#D60041] leading-none mt-0.5">
                      {calculateRuleBasedScore(activeCandidate, (jobs as Job[]).find(j => j.id === parseInt(selectedJobId) || String(j.id) === selectedJobId), evaluationFilters).matchScore || 0}%
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => toggleSelection(activeCandidate.id)}
                    className={`flex items-center gap-1.5 sm:gap-2 px-3.5 sm:px-5 py-2 sm:py-2.5 rounded-xl text-xs font-bold transition-all border cursor-pointer ${
                      selectedCandidateIds.includes(activeCandidate.id)
                        ? 'bg-rose-50 text-rose-600 border-rose-200 hover:bg-rose-100/70'
                        : 'bg-[#D60041] text-white border-[#D60041] hover:bg-rose-700 shadow-2xs hover:shadow-rose-100'
                    }`}
                  >
                    {selectedCandidateIds.includes(activeCandidate.id) ? (
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
              </div>

              {/* Scrollable Detail Body */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-7 space-y-5 sm:space-y-6 custom-scrollbar">
                {/* 3 Pillar Score Breakdown Cards */}
                <div>
                  <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400 mb-2 sm:mb-3">Score Breakdown</h4>
                  <div className="grid grid-cols-3 gap-2 sm:gap-4">
                    <div className={`p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all ${
                      evaluationFilters.skills ? 'bg-blue-50/50 border-blue-100' : 'bg-slate-50/50 border-slate-100 opacity-60'
                    }`}>
                      <div className="flex justify-center mb-1">
                        <Zap className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${evaluationFilters.skills ? 'text-blue-500' : 'text-slate-400'}`} />
                      </div>
                      <p className={`text-base sm:text-xl font-black ${evaluationFilters.skills ? 'text-blue-700' : 'text-slate-500'}`}>
                        {activeCandidate.skillsScore || 0}%
                      </p>
                      <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">Skills</p>
                    </div>

                    <div className={`p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all ${
                      evaluationFilters.experience ? 'bg-purple-50/50 border-purple-100' : 'bg-slate-50/50 border-slate-100 opacity-60'
                    }`}>
                      <div className="flex justify-center mb-1">
                        <Briefcase className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${evaluationFilters.experience ? 'text-purple-500' : 'text-slate-400'}`} />
                      </div>
                      <p className={`text-base sm:text-xl font-black ${evaluationFilters.experience ? 'text-purple-700' : 'text-slate-500'}`}>
                        {activeCandidate.experienceScore || 0}%
                      </p>
                      <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">Experience</p>
                    </div>

                    <div className={`p-2.5 sm:p-4 border rounded-xl sm:rounded-2xl text-center transition-all ${
                      evaluationFilters.certifications ? 'bg-amber-50/50 border-amber-100' : 'bg-slate-50/50 border-slate-100 opacity-60'
                    }`}>
                      <div className="flex justify-center mb-1">
                        <Award className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${evaluationFilters.certifications ? 'text-amber-500' : 'text-slate-400'}`} />
                      </div>
                      <p className={`text-base sm:text-xl font-black ${evaluationFilters.certifications ? 'text-amber-700' : 'text-slate-500'}`}>
                        {activeCandidate.certificationsScore || 0}%
                      </p>
                      <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">Certs</p>
                    </div>
                  </div>
                </div>

                {/* AI Summary */}
                {activeCandidate.ai_summary && (
                  <div className="bg-gradient-to-r from-rose-50/40 to-pink-50/30 border border-rose-100/80 rounded-2xl p-4 sm:p-5 shadow-2xs">
                    <div className="flex items-center gap-1.5 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-[#D60041]" />
                      <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-[#D60041]">AI Evaluation Summary</h4>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium italic">
                      "{activeCandidate.ai_summary}"
                    </p>
                  </div>
                )}

                {/* Work Experience & Certifications Details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400 mb-2">Work Experience</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-4 space-y-3">
                      <div>
                        <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Company / Last Position</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-800">{activeCandidate.company || "Not Specified"}</p>
                      </div>
                      <div>
                        <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Relevance</p>
                        <p className="text-xs font-semibold text-slate-600 leading-relaxed">{activeCandidate.relevance || "No parsed work history details"}</p>
                      </div>
                      {activeCandidate.experience_reason && (
                        <div className="pt-2.5 border-t border-slate-200/60">
                          <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Experience Analysis</p>
                          <p className="text-xs text-slate-600 leading-relaxed">{activeCandidate.experience_reason}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400 mb-2">Certifications</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-4 space-y-3">
                      <div>
                        <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Certifications Held</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-800">{activeCandidate.candidate_certifications || activeCandidate.certifications || "None Specified"}</p>
                      </div>
                      {activeCandidate.certifications_reason && (
                        <div className="pt-2.5 border-t border-slate-200/60">
                          <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Certifications Analysis</p>
                          <p className="text-xs text-slate-600 leading-relaxed">{activeCandidate.certifications_reason}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Skills Analysis */}
                <div className="space-y-3">
                  <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400">Skills Evaluation</h4>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
                    <div className="bg-emerald-50/40 border border-emerald-100 rounded-2xl p-3.5 sm:p-4">
                      <h5 className="flex items-center gap-1.5 text-[10px] font-black text-emerald-800 uppercase tracking-wider mb-2.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Matched Required Skills</span>
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeCandidate.matched_skills && activeCandidate.matched_skills.length > 0 ? (
                          activeCandidate.matched_skills.map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 sm:px-2.5 sm:py-1 bg-white text-emerald-700 border border-emerald-200/80 rounded-md text-[10px] font-bold">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-slate-400 italic">No exact matches stored</span>
                        )}
                      </div>
                    </div>

                    <div className="bg-rose-50/40 border border-rose-100 rounded-2xl p-3.5 sm:p-4">
                      <h5 className="flex items-center gap-1.5 text-[10px] font-black text-rose-800 uppercase tracking-wider mb-2.5">
                        <XCircle className="w-3.5 h-3.5 text-rose-500" />
                        <span>Missing Required Skills</span>
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeCandidate.missing_skills && activeCandidate.missing_skills.length > 0 ? (
                          activeCandidate.missing_skills.map((skill, i) => (
                            <span key={i} className="px-2 py-0.5 sm:px-2.5 sm:py-1 bg-white text-rose-700 border border-rose-200/80 rounded-md text-[10px] font-bold">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-emerald-600 font-bold">All Requirements Satisfied</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {activeCandidate.skills_reason && (
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-3.5 sm:p-4">
                      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Skills Justification</p>
                      <p className="text-xs text-slate-600 leading-relaxed font-semibold">{activeCandidate.skills_reason}</p>
                    </div>
                  )}
                </div>

                {/* Key Strengths & Weaknesses */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                  <div>
                    <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400 mb-2">Core Strengths</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-3.5 sm:p-4 space-y-2">
                      {activeCandidate.strengths && activeCandidate.strengths.length > 0 ? (
                        activeCandidate.strengths.map((str, i) => (
                          <div key={i} className="flex gap-2 items-start text-xs text-slate-700 font-medium">
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                            <span>{str}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-400 italic">No specific strengths listed</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400 mb-2">Areas for Improvement</h4>
                    <div className="bg-slate-50/60 border border-slate-100 rounded-2xl p-3.5 sm:p-4 space-y-2">
                      {activeCandidate.weaknesses && activeCandidate.weaknesses.length > 0 ? (
                        activeCandidate.weaknesses.map((weak, i) => (
                          <div key={i} className="flex gap-2 items-start text-xs text-slate-700 font-medium">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                            <span>{weak}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-slate-400 italic">No specific gaps identified</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* AI Recommendations */}
                {activeCandidate.recommendations && activeCandidate.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-[10px] sm:text-xs font-black uppercase tracking-wider text-slate-400 mb-2">AI Recommendations</h4>
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
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
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
            <span className="w-7 h-7 rounded-xl bg-[#D60041] text-white flex items-center justify-center font-black text-xs shadow-xs">
              {selectedCandidateIds.length}
            </span>
            <div>
              <p className="text-xs font-bold leading-none text-white">Candidates Ready</p>
              <p className="text-[10px] text-slate-400 leading-none mt-0.5">Tap to compare side-by-side</p>
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
    <div className="bg-[#FCFCFC] text-slate-800 antialiased min-h-screen font-sans flex flex-col selection:bg-rose-100 selection:text-[#D60041]">
      <Helmet>
        <title>HR - Compare Candidates</title>
      </Helmet>

      <Header />

      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 w-full max-w-full px-3.5 sm:px-6 md:px-8 lg:px-10 py-4 sm:py-6 flex flex-col min-h-0 overflow-y-auto lg:overflow-hidden">
          {isComparing ? renderComparisonView() : renderSelectionView()}
        </main>
      </div>
    </div>
  );
};

export default CompareCandidates;
