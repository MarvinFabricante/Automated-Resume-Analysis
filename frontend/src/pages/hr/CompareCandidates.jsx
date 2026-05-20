import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  Search, CheckCircle2, XCircle, Users, ArrowLeft, Award, TrendingUp, AlertTriangle,
  Mail, Phone, MapPin, Briefcase, GraduationCap, Star, Zap, BarChart3, Trophy, Sparkles, Check, Plus, Trash2
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useGetApplicationsQuery, useGetJobsQuery } from '../../redux/api/apiSlice';

const calculateRuleBasedScore = (candidate, job) => {
  if (!job) return candidate; // Fallback to original if no job selected

  // 1. Skills Matching (50%)
  let skillsScore = 0;
  let jobSkills = [];
  if (job.skills_requirements) {
    jobSkills = job.skills_requirements.split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  } else {
    jobSkills = job.title.toLowerCase().split(' ').filter(w => w.length > 2); 
  }
  
  const candidateSkills = (candidate.skills || []).map(s => s.toLowerCase());
  let matchedSkills = [];
  let missingSkills = [];
  
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

  // 2. Experience Matching (30%)
  let expScore = 0;
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

  // 3. Education Matching (20%)
  let eduScore = 0;
  const jobEdu = (job.education_requirements || '').toLowerCase();
  const candEdu = ((candidate.degree || '') + ' ' + (candidate.college || '')).toLowerCase();
  
  if (jobEdu) {
    if (jobEdu.includes('bachelor') && candEdu.includes('bachelor')) eduScore = 100;
    else if (jobEdu.includes('master') && candEdu.includes('master')) eduScore = 100;
    else {
       const eduKeywords = jobEdu.split(/[\s,]+/).filter(w => w.length > 3);
       if (eduKeywords.length > 0) {
         const matchCount = eduKeywords.filter(kw => candEdu.includes(kw)).length;
         eduScore = Math.round((matchCount / eduKeywords.length) * 100);
       } else {
         eduScore = 80;
       }
    }
  } else {
    eduScore = candidate.educationScore || 0;
  }
  
  const matchScore = Math.round((skillsScore * 0.5) + (expScore * 0.3) + (eduScore * 0.2));
  
  return {
    ...candidate,
    matchScore,
    skillsScore,
    experienceScore: expScore,
    educationScore: eduScore,
    matched_skills: matchedSkills.length > 0 ? matchedSkills : candidate.matched_skills,
    missing_skills: missingSkills.length > 0 ? missingSkills : candidate.missing_skills,
    isRuleBased: true
  };
};

const CompareCandidates = () => {
  const { data: candidates = [], isLoading } = useGetApplicationsQuery();
  const { data: jobs = [], isLoading: isLoadingJobs } = useGetJobsQuery();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCandidateIds, setSelectedCandidateIds] = useState([]);
  const [activeCandidateId, setActiveCandidateId] = useState(null);
  const [isComparing, setIsComparing] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState("");

  // Filter candidates based on search
  const filteredCandidates = useMemo(() => {
    return candidates.filter(c => {
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
  useMemo(() => {
    if (filteredCandidates.length > 0 && !activeCandidateId) {
      setActiveCandidateId(filteredCandidates[0].id);
    }
  }, [filteredCandidates, activeCandidateId]);

  const activeCandidate = useMemo(() => {
    return candidates.find(c => c.id === activeCandidateId) || filteredCandidates[0] || null;
  }, [candidates, activeCandidateId, filteredCandidates]);

  const toggleSelection = (id) => {
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
    const selected = candidates.filter(c => selectedCandidateIds.includes(c.id));
    const selectedJob = jobs.find(j => j.id === parseInt(selectedJobId) || j.id === selectedJobId);
    
    let scoredCandidates = selected;
    if (selectedJob) {
      scoredCandidates = selected.map(c => calculateRuleBasedScore(c, selectedJob));
    }
    
    // Sort by match score descending to automatically rank them
    return [...scoredCandidates].sort((a, b) => (b.matchScore || 0) - (a.matchScore || 0));
  }, [candidates, selectedCandidateIds, jobs, selectedJobId]);

  const winner = useMemo(() => {
    if (selectedCandidatesData.length === 0) return null;
    return selectedCandidatesData[0]; // Since it is sorted, the first one is the highest score
  }, [selectedCandidatesData]);

  const renderComparisonView = () => {
    if (!winner) return null;

    return (
      <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
        {/* Navigation / Header */}
        <div className="mb-8">
          <button 
            onClick={() => setIsComparing(false)}
            className="flex items-center text-sm font-bold text-gray-500 hover:text-[#D60041] transition-colors mb-4 group"
          >
            <div className="p-1.5 bg-gray-100 rounded-lg group-hover:bg-pink-100 mr-2 transition-colors">
              <ArrowLeft className="w-4 h-4" />
            </div>
             Back to Candidate Selection
          </button>
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-3xl font-black text-gray-900 tracking-tight">Side-by-Side Comparison</h1>
              <p className="text-gray-500 font-medium mt-1">Comparing {selectedCandidatesData.length} selected candidates for the role suitability.</p>
            </div>
            
            <div className="flex items-center gap-2">
              <div className="px-4 py-2 bg-pink-50 border border-pink-100 rounded-xl text-xs font-bold text-[#D60041] flex items-center gap-1.5 shadow-sm">
                <Sparkles className="w-3.5 h-3.5" />
                AI Ranked & Evaluated
              </div>
            </div>
          </div>
        </div>

        {/* AI Recommendation / Winner Banner */}
        <div className="bg-gradient-to-r from-gray-900 via-slate-800 to-gray-950 text-white rounded-[32px] p-8 mb-8 shadow-xl relative overflow-hidden border border-gray-800">
          <div className="absolute -right-10 -top-10 w-40 h-40 bg-[#D60041]/10 rounded-full blur-3xl"></div>
          <div className="absolute -left-10 -bottom-10 w-40 h-40 bg-blue-500/10 rounded-full blur-3xl"></div>
          
          <div className="relative flex flex-col lg:flex-row items-start lg:items-center justify-between gap-8">
            <div className="flex-1">
              <div className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-[#D60041]/20 border border-[#D60041]/40 rounded-full text-xs font-bold text-[#FF3E74] uppercase tracking-wider mb-4">
                <Trophy className="w-4 h-4 text-amber-400" />
                Top Recommended Candidate
              </div>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tight leading-tight">
                {winner.name} is the most qualified candidate!
              </h2>
              <p className="text-gray-300 font-medium mt-2 max-w-3xl leading-relaxed text-sm sm:text-base">
                Based on our {winner.isRuleBased ? 'rule-based analysis' : 'semantic AI analysis'} of skills, experience, and educational background, <span className="text-white font-bold">{winner.name}</span> has the highest matching index of <span className="text-[#FF3E74] font-black">{winner.matchScore}%</span>. 
                {winner.ai_summary ? ` ${winner.ai_summary}` : ` They demonstrate strong alignment with the requirements for the position of ${winner.preferredJob}.`}
              </p>
            </div>
            
            <div className="flex items-center gap-4 bg-white/5 border border-white/10 p-5 rounded-[24px] shrink-0">
              <div className="text-center">
                <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Top Score</p>
                <p className="text-5xl font-black text-[#FF3E74] tracking-tight">{winner.matchScore}%</p>
              </div>
              <div className="w-px h-12 bg-white/10"></div>
              <div>
                <p className="text-xs font-bold text-white">{winner.name}</p>
                <p className="text-[11px] text-gray-400 font-semibold mt-0.5">{winner.preferredJob}</p>
                <div className="flex gap-1.5 mt-2">
                  <span className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded text-[9px] font-bold border border-blue-500/30">Skills: {winner.skillsScore}%</span>
                  <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-[9px] font-bold border border-purple-500/30">Exp: {winner.experienceScore}%</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Side-by-Side Comparison Matrix */}
        <div className="bg-white border border-gray-100 rounded-[32px] shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-50/55 border-b border-gray-100">
                  <th className="p-6 text-left text-[11px] font-black text-gray-400 uppercase tracking-widest w-64 shrink-0 bg-gray-50/30">
                    Criteria Comparison
                  </th>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <th key={candidate.id} className={`p-6 text-left min-w-[280px] relative ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      {idx === 0 && (
                        <div className="absolute top-0 left-0 right-0 h-1 bg-[#D60041]" />
                      )}
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-gradient-to-br from-pink-50 to-rose-50 border border-pink-100 rounded-xl flex items-center justify-center text-[#D60041] font-black text-lg shadow-sm shrink-0">
                          {candidate.name.charAt(0)}
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <h4 className="text-base font-bold text-gray-950 tracking-tight">{candidate.name}</h4>
                            {idx === 0 && <Trophy className="w-4 h-4 text-amber-500 shrink-0" />}
                          </div>
                          <p className="text-xs text-gray-500 font-semibold">{candidate.preferredJob}</p>
                        </div>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              
              <tbody className="divide-y divide-gray-100">
                {/* Overall Suitability */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Match Percentage
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <div className="flex items-center gap-3">
                        <span className={`text-2xl font-black ${idx === 0 ? 'text-[#D60041]' : 'text-gray-900'}`}>
                          {candidate.matchScore}%
                        </span>
                        <div className="flex-1 max-w-[120px] bg-gray-100 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${idx === 0 ? 'bg-[#D60041]' : 'bg-gray-700'}`} 
                            style={{ width: `${candidate.matchScore}%` }}
                          />
                        </div>
                      </div>
                      {idx === 0 && (
                        <span className="text-[10px] font-black text-[#D60041] uppercase tracking-wider mt-1 block">Highest Score</span>
                      )}
                    </td>
                  ))}
                </tr>

                {/* Score Breakdown Bars */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Pillar Scores
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 space-y-3.5 ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <div>
                        <div className="flex justify-between text-[11px] font-bold mb-1">
                          <span className="text-gray-500 uppercase">Skills ({candidate.skillsScore}%)</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-1.5">
                          <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${candidate.skillsScore}%` }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] font-bold mb-1">
                          <span className="text-gray-500 uppercase">Experience ({candidate.experienceScore}%)</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-1.5">
                          <div className="bg-purple-500 h-1.5 rounded-full" style={{ width: `${candidate.experienceScore}%` }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-[11px] font-bold mb-1">
                          <span className="text-gray-500 uppercase">Education ({candidate.educationScore}%)</span>
                        </div>
                        <div className="w-full bg-gray-100 rounded-full h-1.5">
                          <div className="bg-amber-500 h-1.5 rounded-full" style={{ width: `${candidate.educationScore}%` }} />
                        </div>
                      </div>
                    </td>
                  ))}
                </tr>

                {/* Matched Skills */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Matched Skills
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <div className="flex flex-wrap gap-1.5">
                        {candidate.matched_skills && candidate.matched_skills.length > 0 ? (
                          candidate.matched_skills.map((skill, i) => (
                            <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-lg text-[10px] font-bold">
                              <Check className="w-2.5 h-2.5" />
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400 italic">None matched</span>
                        )}
                      </div>
                    </td>
                  ))}
                </tr>

                {/* Missing Skills */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Missing Skills
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <div className="flex flex-wrap gap-1.5">
                        {candidate.missing_skills && candidate.missing_skills.length > 0 ? (
                          candidate.missing_skills.map((skill, i) => (
                            <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-rose-50 text-rose-700 border border-rose-100 rounded-lg text-[10px] font-bold">
                              <XCircle className="w-2.5 h-2.5" />
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-emerald-600 font-semibold">Perfect Skills Match!</span>
                        )}
                      </div>
                    </td>
                  ))}
                </tr>

                {/* Core Strengths */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Strengths
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <ul className="space-y-1.5 text-xs text-gray-700 font-medium">
                        {candidate.strengths && candidate.strengths.slice(0, 3).map((strength, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
                            <span>{strength}</span>
                          </li>
                        )) || <span className="italic text-gray-400">N/A</span>}
                      </ul>
                    </td>
                  ))}
                </tr>

                {/* Areas for Improvement */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Gaps & Weaknesses
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <ul className="space-y-1.5 text-xs text-gray-700 font-medium">
                        {candidate.weaknesses && candidate.weaknesses.slice(0, 3).map((weakness, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                            <span>{weakness}</span>
                          </li>
                        )) || <span className="italic text-gray-400">N/A</span>}
                      </ul>
                    </td>
                  ))}
                </tr>

                {/* Experience & Previous Roles */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Experience Relevance
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 text-xs text-gray-700 leading-relaxed font-medium ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <div className="mb-2">
                        <span className="font-bold text-gray-900 block">{candidate.company || "Unknown Company"}</span>
                        <span className="text-[10px] uppercase font-black text-gray-400">{candidate.relevance || "Role detail unspecified"}</span>
                      </div>
                      <p className="line-clamp-4 text-gray-500">{candidate.experience_reason || "No detail provided"}</p>
                    </td>
                  ))}
                </tr>

                {/* Education */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Education & Credentials
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 text-xs text-gray-700 font-medium ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <p className="font-bold text-gray-900">{candidate.degree || "Degree not specified"}</p>
                      <p className="text-gray-500 mt-0.5">{candidate.college || "Institution not specified"}</p>
                      <p className="text-[10px] text-gray-400 mt-2 font-semibold italic">{candidate.education_reason}</p>
                    </td>
                  ))}
                </tr>

                {/* Recommendations */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Recommendations
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 text-xs text-gray-600 font-medium ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <ul className="space-y-1">
                        {candidate.recommendations && candidate.recommendations.slice(0, 2).map((rec, i) => (
                          <li key={i} className="flex gap-1.5 items-start">
                            <span className="text-emerald-600 font-bold shrink-0">✓</span>
                            <span>{rec}</span>
                          </li>
                        )) || <span className="italic text-gray-400">None available</span>}
                      </ul>
                    </td>
                  ))}
                </tr>

                {/* Contact Information */}
                <tr className="hover:bg-gray-50/30">
                  <td className="p-6 font-bold text-xs text-gray-500 uppercase tracking-wider bg-gray-50/10">
                    Contact Details
                  </td>
                  {selectedCandidatesData.map((candidate, idx) => (
                    <td key={candidate.id} className={`p-6 space-y-2 text-xs text-gray-500 font-medium ${idx === 0 ? 'bg-pink-50/10' : ''}`}>
                      <div className="flex items-center gap-2">
                        <Mail className="w-3.5 h-3.5 text-gray-400" />
                        <span>{candidate.email}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Phone className="w-3.5 h-3.5 text-gray-400" />
                        <span>{candidate.phone}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin className="w-3.5 h-3.5 text-gray-400" />
                        <span>{candidate.location}</span>
                      </div>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const renderSelectionView = () => (
    <div className="animate-in fade-in duration-500 flex flex-col h-[calc(100vh-140px)]">
      {/* Top Search and Comparison Info */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6 shrink-0">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">Compare Candidates</h1>
          <p className="text-gray-500 font-medium mt-1">Select candidates on the list to view their full resume details, then compare side-by-side.</p>
        </div>
        
        {/* Floating / Active Compare Stats */}
        <div className="flex items-center gap-3">
          <div className="bg-white border border-gray-100 rounded-2xl px-5 py-3 shadow-sm flex items-center gap-3">
            <div className="w-8 h-8 bg-pink-50 border border-pink-100 text-[#D60041] rounded-xl flex items-center justify-center font-black text-sm">
              {selectedCandidateIds.length}
            </div>
            <div>
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">To Compare</p>
              <p className="text-xs font-bold text-gray-900">Candidates Selected</p>
            </div>
            {selectedCandidateIds.length > 0 && (
              <button 
                onClick={clearSelected}
                className="p-1.5 hover:bg-rose-50 text-rose-500 rounded-lg hover:text-rose-600 transition-colors ml-2"
                title="Clear Selection"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>

          <button
            disabled={selectedCandidateIds.length < 2}
            onClick={() => setIsComparing(true)}
            className={`flex items-center gap-2 px-6 py-3.5 rounded-2xl font-bold text-sm transition-all shadow-sm ${
              selectedCandidateIds.length >= 2 
                ? 'bg-gray-900 hover:bg-black text-white cursor-pointer hover:scale-[1.02] active:scale-[0.98]'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed border border-gray-100'
            }`}
          >
            <TrendingUp className="w-4 h-4 text-[#D60041]" />
            Compare Now
          </button>
        </div>
      </div>

      {/* Split-Screen Selection Area */}
      <div className="flex flex-col lg:flex-row flex-1 gap-6 overflow-hidden min-h-0 mb-6">
        
        {/* LEFT COLUMN: Candidate Search and List */}
        <div className="w-full lg:w-[380px] bg-white border border-gray-100 rounded-[28px] shadow-sm flex flex-col overflow-hidden shrink-0">
          
          <div className="p-4 border-b border-gray-50 bg-gray-50/40 shrink-0 space-y-3">
            <div>
              <label className="text-[10px] font-black uppercase tracking-widest text-gray-500 mb-1.5 block">Compare Against Job Profile</label>
              <select 
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-pink-500/20 focus:border-[#D60041] transition-all font-medium text-sm text-gray-700"
              >
                <option value="">-- Use Original AI Scores --</option>
                {jobs.map(job => (
                  <option key={job.id} value={job.id}>{job.title}</option>
                ))}
              </select>
            </div>
            
            <div className="relative">
              <Search className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
              <input 
                type="text" 
                placeholder="Search candidates or skills..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-11 pr-4 py-2 bg-white border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-pink-500/20 focus:border-[#D60041] transition-all font-medium text-sm"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-gray-50 p-2 space-y-1.5 scrollbar-hide">
            {isLoading ? (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="w-10 h-10 border-4 border-pink-100 border-t-[#D60041] rounded-full animate-spin mb-3"></div>
                <p className="text-gray-400 text-xs font-bold">Loading applicants...</p>
              </div>
            ) : filteredCandidates.length === 0 ? (
              <div className="text-center py-16 px-4">
                <div className="w-14 h-14 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-3 border border-gray-100">
                  <Users className="w-6 h-6 text-gray-300" />
                </div>
                <h4 className="text-sm font-bold text-gray-900">No candidates found</h4>
                <p className="text-xs text-gray-400 mt-1">Try searching another name or skill.</p>
              </div>
            ) : (
              filteredCandidates.map(candidate => {
                const isSelected = selectedCandidateIds.includes(candidate.id);
                const isActive = activeCandidateId === candidate.id;

                return (
                  <div 
                    key={candidate.id}
                    onClick={() => setActiveCandidateId(candidate.id)}
                    className={`p-3.5 rounded-2xl border transition-all duration-300 cursor-pointer flex items-center gap-3 relative group ${
                      isActive 
                        ? 'bg-pink-50/20 border-[#D60041]/30 shadow-sm'
                        : 'bg-white border-transparent hover:bg-gray-50/60'
                    }`}
                  >
                    <div 
                      className="shrink-0"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleSelection(candidate.id);
                      }}
                    >
                      <div className={`w-5.5 h-5.5 rounded-lg border flex items-center justify-center transition-all ${
                        isSelected 
                          ? 'bg-[#D60041] border-[#D60041] scale-105 shadow-md shadow-pink-500/10' 
                          : 'border-gray-300 bg-white group-hover:border-[#D60041]'
                      }`}>
                        {isSelected && <Check className="w-3.5 h-3.5 text-white stroke-[3px]" />}
                      </div>
                    </div>

                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-gray-900 truncate tracking-tight">{candidate.name}</h4>
                      <p className="text-xs text-gray-500 font-semibold truncate mt-0.5">{candidate.preferredJob}</p>
                      
                      {candidate.skills && candidate.skills.length > 0 && (
                        <div className="flex gap-1 overflow-hidden mt-1.5">
                          {candidate.skills.slice(0, 3).map((skill, idx) => (
                            <span key={idx} className="px-1.5 py-0.5 bg-gray-50 text-gray-500 border border-gray-100 rounded text-[9px] font-bold whitespace-nowrap">
                              {skill}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="text-right shrink-0">
                      <span className={`text-xs font-black px-2 py-1 rounded-lg ${
                        candidate.matchScore >= 85 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' 
                          : candidate.matchScore >= 70 
                            ? 'bg-amber-50 text-amber-600 border border-amber-100' 
                            : 'bg-gray-50 text-gray-500 border border-gray-100'
                      }`}>
                        {candidate.matchScore || 0}%
                      </span>
                    </div>

                    {isActive && (
                      <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#D60041] rounded-l-full" />
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Full Resume Details (Detailed Profile View) */}
        <div className="flex-1 bg-white border border-gray-100 rounded-[28px] shadow-sm flex flex-col overflow-hidden">
          {activeCandidate ? (
            <div className="flex-grow flex flex-col overflow-hidden h-full">
              {/* Profile Card Header */}
              <div className="p-6 sm:p-8 border-b border-gray-50 bg-gray-50/15 flex flex-col sm:flex-row sm:items-center justify-between gap-6 shrink-0">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 bg-gradient-to-br from-pink-100 to-pink-50 border border-pink-100 rounded-2xl flex items-center justify-center text-[#D60041] font-black text-2xl shadow-sm shrink-0">
                    {activeCandidate.name.charAt(0)}
                  </div>
                  <div>
                    <h2 className="text-xl sm:text-2xl font-black text-gray-900 tracking-tight leading-tight">{activeCandidate.name}</h2>
                    <p className="text-sm text-gray-500 font-semibold mt-1">{activeCandidate.preferredJob}</p>
                    <div className="flex flex-wrap gap-2 mt-2">
                      <div className="flex items-center gap-1 text-[11px] text-gray-400 font-bold uppercase">
                        <MapPin className="w-3.5 h-3.5 shrink-0" />
                        <span>{activeCandidate.location}</span>
                      </div>
                      <div className="w-1 h-1 rounded-full bg-gray-300 mt-2"></div>
                      <div className="flex items-center gap-1 text-[11px] text-gray-400 font-bold uppercase">
                        <Mail className="w-3.5 h-3.5 shrink-0" />
                        <span>{activeCandidate.email || "N/A"}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Suitability</p>
                    <p className="text-2xl font-black text-[#D60041]">{activeCandidate.matchScore}%</p>
                  </div>
                  
                  <button
                    onClick={() => toggleSelection(activeCandidate.id)}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl text-xs font-black uppercase tracking-wider transition-all border ${
                      selectedCandidateIds.includes(activeCandidate.id)
                        ? 'bg-rose-50 text-rose-600 border-rose-100 hover:bg-rose-100/70'
                        : 'bg-[#D60041] text-white border-[#D60041] hover:bg-rose-700 shadow-sm hover:shadow-rose-100'
                    }`}
                  >
                    {selectedCandidateIds.includes(activeCandidate.id) ? (
                      <>
                        <XCircle className="w-4 h-4" />
                        Remove from Compare
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        Add to Compare
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Scrollable Detail Body */}
              <div className="flex-1 overflow-y-auto p-6 sm:p-8 space-y-8 scrollbar-hide">
                {/* Score Breakdown Cards */}
                <div>
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3.5">Score Breakdown</h4>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="p-4 bg-blue-50/50 border border-blue-100/50 rounded-2xl text-center">
                      <div className="flex justify-center mb-1"><Zap className="w-4 h-4 text-blue-500" /></div>
                      <p className="text-lg font-black text-blue-600">{activeCandidate.skillsScore || 0}%</p>
                      <p className="text-[9px] font-black text-gray-400 uppercase tracking-wide mt-0.5">Skills</p>
                    </div>
                    <div className="p-4 bg-purple-50/50 border border-purple-100/50 rounded-2xl text-center">
                      <div className="flex justify-center mb-1"><Briefcase className="w-4 h-4 text-purple-500" /></div>
                      <p className="text-lg font-black text-purple-600">{activeCandidate.experienceScore || 0}%</p>
                      <p className="text-[9px] font-black text-gray-400 uppercase tracking-wide mt-0.5">Experience</p>
                    </div>
                    <div className="p-4 bg-amber-50/50 border border-amber-100/50 rounded-2xl text-center">
                      <div className="flex justify-center mb-1"><GraduationCap className="w-4 h-4 text-amber-500" /></div>
                      <p className="text-lg font-black text-amber-600">{activeCandidate.educationScore || 0}%</p>
                      <p className="text-[9px] font-black text-gray-400 uppercase tracking-wide mt-0.5">Education</p>
                    </div>
                  </div>
                </div>

                {/* AI Summary */}
                {activeCandidate.ai_summary && (
                  <div className="bg-pink-50/10 border border-pink-100/20 rounded-[24px] p-5 shadow-sm bg-gradient-to-r from-pink-50/10 to-rose-50/10">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-4 h-4 text-[#D60041]" />
                      <h4 className="text-[10px] font-black uppercase tracking-widest text-[#D60041]">AI Evaluation Summary</h4>
                    </div>
                    <p className="text-xs sm:text-sm text-gray-700 leading-relaxed font-medium italic">
                      "{activeCandidate.ai_summary}"
                    </p>
                  </div>
                )}

                {/* Resume Overview details */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3">Work Experience</h4>
                    <div className="bg-gray-50/50 border border-gray-100 rounded-2xl p-4.5 space-y-4">
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Company / Last Position</p>
                        <p className="text-sm font-bold text-gray-800">{activeCandidate.company || "Not Specified"}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Experience Relevance</p>
                        <p className="text-xs font-semibold text-gray-600 leading-relaxed">{activeCandidate.relevance || "No parsed work history details"}</p>
                      </div>
                      {activeCandidate.experience_reason && (
                        <div className="pt-3 border-t border-gray-200/50">
                          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Experience Analysis</p>
                          <p className="text-xs text-gray-600 leading-relaxed">{activeCandidate.experience_reason}</p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3">Education</h4>
                    <div className="bg-gray-50/50 border border-gray-100 rounded-2xl p-4.5 space-y-4">
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Degree</p>
                        <p className="text-sm font-bold text-gray-800">{activeCandidate.degree || "Not Specified"}</p>
                      </div>
                      <div>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">College / University</p>
                        <p className="text-xs font-bold text-gray-600">{activeCandidate.college || "Not Specified"}</p>
                      </div>
                      {activeCandidate.education_reason && (
                        <div className="pt-3 border-t border-gray-200/50">
                          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Education Analysis</p>
                          <p className="text-xs text-gray-600 leading-relaxed">{activeCandidate.education_reason}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Skills Analysis */}
                <div className="space-y-4">
                  <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-2">Skills Evaluation</h4>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-emerald-50/30 border border-emerald-100/50 rounded-2xl p-4">
                      <h5 className="flex items-center gap-1.5 text-[10px] font-black text-emerald-800 uppercase tracking-wider mb-3">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                        Matched Required Skills
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeCandidate.matched_skills && activeCandidate.matched_skills.length > 0 ? (
                          activeCandidate.matched_skills.map((skill, i) => (
                            <span key={i} className="px-2.5 py-1.5 bg-white text-emerald-700 border border-emerald-100 rounded-lg text-[10px] font-bold">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-gray-400 italic">No exact matches stored</span>
                        )}
                      </div>
                    </div>

                    <div className="bg-rose-50/30 border border-rose-100/50 rounded-2xl p-4">
                      <h5 className="flex items-center gap-1.5 text-[10px] font-black text-rose-800 uppercase tracking-wider mb-3">
                        <XCircle className="w-3.5 h-3.5 text-rose-500" />
                        Missing Required Skills
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {activeCandidate.missing_skills && activeCandidate.missing_skills.length > 0 ? (
                          activeCandidate.missing_skills.map((skill, i) => (
                            <span key={i} className="px-2.5 py-1.5 bg-white text-rose-700 border border-rose-100 rounded-lg text-[10px] font-bold">
                              {skill}
                            </span>
                          ))
                        ) : (
                          <span className="text-xs text-emerald-600 font-semibold">All requirements satisfied!</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {activeCandidate.skills_reason && (
                    <div className="bg-gray-50/50 border border-gray-100 rounded-2xl p-4.5">
                      <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Skills Justification</p>
                      <p className="text-xs text-gray-600 leading-relaxed font-semibold">{activeCandidate.skills_reason}</p>
                    </div>
                  )}
                </div>

                {/* Key Strengths and Weaknesses */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3">Core Strengths</h4>
                    <div className="bg-gray-50/50 border border-gray-100 rounded-2xl p-4.5 space-y-2.5">
                      {activeCandidate.strengths && activeCandidate.strengths.length > 0 ? (
                        activeCandidate.strengths.map((str, i) => (
                          <div key={i} className="flex gap-2.5 items-start text-xs text-gray-700 font-medium">
                            <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                            <span>{str}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-400 italic">No specific strengths stored</p>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3">Areas for Improvement</h4>
                    <div className="bg-gray-50/50 border border-gray-100 rounded-2xl p-4.5 space-y-2.5">
                      {activeCandidate.weaknesses && activeCandidate.weaknesses.length > 0 ? (
                        activeCandidate.weaknesses.map((weak, i) => (
                          <div key={i} className="flex gap-2.5 items-start text-xs text-gray-700 font-medium">
                            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                            <span>{weak}</span>
                          </div>
                        ))
                      ) : (
                        <p className="text-xs text-gray-400 italic">No specific weaknesses identified</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                {activeCandidate.recommendations && activeCandidate.recommendations.length > 0 && (
                  <div>
                    <h4 className="text-[10px] font-black uppercase tracking-widest text-gray-400 mb-3">AI Recommendations</h4>
                    <div className="bg-emerald-50/20 border border-emerald-100/50 rounded-2xl p-4.5 space-y-2.5">
                      {activeCandidate.recommendations.map((rec, i) => (
                        <div key={i} className="flex gap-2.5 items-start text-xs text-gray-700 font-medium">
                          <Star className="w-4 h-4 text-amber-400 fill-amber-400 shrink-0 mt-0.5" />
                          <span>{rec}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-gray-50/30">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                <Users className="w-8 h-8 text-gray-300" />
              </div>
              <h3 className="text-lg font-bold text-gray-900">No Candidate Selected</h3>
              <p className="text-sm text-gray-400 mt-1 max-w-sm">Select an applicant from the list on the left to see their complete resume information and score breakdown.</p>
            </div>
          )}
        </div>

      </div>
    </div>
  );

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>HR - Compare Candidates</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1 pt-[81px]">
        <Sidebar />
        <main className="flex-1 w-full max-w-[1400px] mx-auto px-4 sm:px-6 md:px-8 py-6 lg:ml-64 flex flex-col overflow-hidden">
          {isComparing ? renderComparisonView() : renderSelectionView()}
        </main>
      </div>
    </div>
  );
};

export default CompareCandidates;

