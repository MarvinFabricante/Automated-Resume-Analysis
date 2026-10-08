import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  X, MapPin, Briefcase, Star, GraduationCap, Mail, Phone, 
  Target, TrendingUp, Lightbulb, CheckCircle2, XCircle, AlertTriangle,
  ChevronRight, Zap, BarChart3, BookOpen, Award, Copy, Check, Calendar, ExternalLink, Download
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

/* ─── Score Ring ─── */
const ScoreRing = ({ score, size = 120, strokeWidth = 10, color }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const getColor = () => {
    if (color) return color;
    if (score >= 80) return '#10b981';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke="#f1f5f9" strokeWidth={strokeWidth} />
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke={getColor()} strokeWidth={strokeWidth}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-black text-gray-900">{Math.round(score)}%</span>
      </div>
    </div>
  );
};

/* ─── Pillar Score Bar ─── */
const PillarBar = ({ label, score, weight, color, bgColor, borderColor, icon: Icon }) => {
  const contribution = Math.round(score * (weight / 100));
  return (
    <div className={`p-4 rounded-2xl border ${borderColor} ${bgColor} transition-all duration-300 hover:shadow-md`}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} className={color} />
          <span className={`text-[10px] font-bold uppercase tracking-widest ${color}`}>{label}</span>
        </div>
        <span className={`text-sm font-black ${color}`}>{Math.round(score)}%</span>
      </div>
      <div className="w-full h-2 bg-white/60 rounded-full overflow-hidden mb-2">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{ width: `${score}%`, backgroundColor: color.includes('blue') ? '#3b82f6' : color.includes('purple') ? '#8b5cf6' : '#f59e0b' }}
        />
      </div>
      <p className="text-[10px] font-semibold text-gray-500">
        Contributes <span className="font-black">{weight}%</span> to overall → <span className="font-black">{contribution}%</span> actual
      </p>
    </div>
  );
};

/* ─── Skill Tag ─── */
const SkillTag = ({ skill, type }) => (
  <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-[11px] font-bold tracking-tight border transition-all duration-200 ${
    type === 'matched' 
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
      : 'bg-rose-50 text-rose-600 border-rose-200'
  }`}>
    {type === 'matched' ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
    {skill}
  </span>
);

const ViewCandidateDetailsModal = ({ isOpen, onClose, candidate, onOpenInterview, onUpdateStatus }) => {
  const [copiedField, setCopiedField] = useState(null);
  const [mobileTab, setMobileTab] = useState('overview'); // 'overview' | 'analysis' | 'resume'

  if (!isOpen || !candidate) return null;

  const handleCopy = (text, field) => {
    if (!text || text === 'N/A') return;
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const skillsContribution = Math.round((candidate.skillsScore || 0) * 0.40);
  const experienceContribution = Math.round((candidate.experienceScore || 0) * 0.40);
  const educationContribution = Math.round((candidate.educationScore || 0) * 0.20);
  const strengths = candidate.strengths || [];
  const weaknesses = candidate.weaknesses || [];
  const matchedSkills = candidate.matched_skills || [];
  const missingSkills = candidate.missing_skills || [];
  const candidateSkills = (candidate.skills && candidate.skills.length > 0) ? candidate.skills : matchedSkills;
  const calculatedContributionTotal = skillsContribution + experienceContribution + educationContribution;
  const hasStoredBreakdown = Boolean(
    matchedSkills.length ||
    missingSkills.length ||
    candidate.skills_reason ||
    candidate.experience_reason ||
    candidate.education_reason
  );
  const hasAiInsights = Boolean(candidate.ai_summary || strengths.length || weaknesses.length);
  const fallbackAssessment = [
    candidate.skills_reason,
    candidate.experience_reason,
    candidate.education_reason
  ].filter(Boolean).join(' ');

  const currentStatus = candidate.status || 'Pending';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-[#0c0d12]/60 backdrop-blur-sm">
      <Helmet>
        <title>{candidate.name} | ATS Analysis</title>
      </Helmet>
      <div className="bg-white w-full max-w-6xl max-h-[96vh] sm:max-h-[92vh] rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-250">
        
        {/* ─── Header ─── */}
        <div className="px-3.5 sm:px-6 py-3 sm:py-4 border-b border-gray-100 flex justify-between items-center bg-white sticky top-0 z-10 shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 border border-emerald-100 rounded-xl shrink-0">
              <BarChart3 size={13} className="text-emerald-600 shrink-0" />
              <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider truncate">ATS Analysis</span>
            </div>
            {onUpdateStatus && (
              <div className="flex items-center gap-1.5 pl-2 border-l border-gray-100">
                <span className="hidden sm:inline text-[10px] font-bold text-gray-400 uppercase tracking-wider">Status:</span>
                <select
                  value={currentStatus}
                  onChange={(e) => onUpdateStatus(candidate.id, e.target.value)}
                  className="px-2 py-0.5 bg-gray-50 border border-gray-200 rounded-lg text-xs font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer"
                >
                  {['Pending', 'Reviewed', 'Technical Interview', 'Final Interview', 'Accepted', 'Rejected', 'Archived'].map((st) => (
                    <option key={st} value={st}>{st}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
          <button onClick={onClose} className="p-1.5 sm:p-2 hover:bg-gray-100 rounded-xl transition-colors text-gray-400 hover:text-gray-600 cursor-pointer">
            <X size={18} />
          </button>
        </div>

        {/* ─── Mobile Segment Switcher ─── */}
        <div className="flex md:hidden border-b border-gray-100 bg-gray-50/80 p-1.5 gap-1 shrink-0">
          <button
            type="button"
            onClick={() => setMobileTab('overview')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              mobileTab === 'overview'
                ? 'bg-white text-[#D60041] shadow-xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Overview
          </button>
          <button
            type="button"
            onClick={() => setMobileTab('analysis')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              mobileTab === 'analysis'
                ? 'bg-white text-[#D60041] shadow-xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Breakdown
          </button>
          <button
            type="button"
            onClick={() => setMobileTab('resume')}
            className={`flex-1 py-1.5 text-xs font-bold rounded-xl transition-all cursor-pointer ${
              mobileTab === 'resume'
                ? 'bg-white text-[#D60041] shadow-xs'
                : 'text-gray-500 hover:text-gray-900'
            }`}
          >
            Resume Data
          </button>
        </div>

        <div className="flex flex-col md:flex-row flex-1 overflow-y-auto md:overflow-hidden min-h-0">
          {/* ─── LEFT SIDEBAR ─── */}
          <div className={`w-full md:w-[320px] bg-gradient-to-b from-gray-50/80 to-white border-b md:border-b-0 md:border-r border-gray-100 p-4 sm:p-6 md:overflow-y-auto shrink-0 ${
            mobileTab === 'overview' ? 'block' : 'hidden md:block'
          }`}>
            {/* Candidate Profile */}
            <div className="text-center mb-6 sm:mb-7">
              <div className="w-20 h-20 rounded-2xl overflow-hidden border-4 border-white shadow-lg mx-auto mb-4 bg-pink-50">
                {candidate.profileImage ? (
                  <img src={getAssetUrl(candidate.profileImage)} alt={candidate.name} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#d81159] text-2xl font-black bg-gradient-to-br from-pink-100 to-pink-50">
                    {candidate.name.charAt(0)}
                  </div>
                )}
              </div>
              <h2 className="text-lg font-black text-gray-900 tracking-tight">{candidate.name}</h2>
              <p className="text-xs text-gray-500 font-semibold mt-0.5">{candidate.preferredJob}</p>
            </div>

            {/* Overall Score Ring */}
            <div className="flex flex-col items-center mb-7">
              <ScoreRing score={candidate.matchScore} />
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-3">Overall Match Score</p>
            </div>

            {/* Score Pillar Bars */}
            <div className="space-y-3 mb-7">
              <PillarBar label="Skills" score={candidate.skillsScore} weight={40}
                color="text-blue-600" bgColor="bg-blue-50/70" borderColor="border-blue-100" icon={Zap} />
              <PillarBar label="Experience" score={candidate.experienceScore} weight={40}
                color="text-purple-600" bgColor="bg-purple-50/70" borderColor="border-purple-100" icon={Briefcase} />
              <PillarBar label="Education" score={candidate.educationScore} weight={20}
                color="text-amber-600" bgColor="bg-amber-50/70" borderColor="border-amber-100" icon={GraduationCap} />
            </div>

            {/* Contact Info */}
            <div className="space-y-3 pt-5 border-t border-gray-100">
              <div className="flex items-center gap-3 text-gray-500">
                <MapPin size={14} className="text-gray-400 shrink-0" />
                <span className="text-xs font-medium">{candidate.location}</span>
              </div>
              <div className="flex items-center justify-between text-gray-500 group">
                <div className="flex items-center gap-3 min-w-0">
                  <Mail size={14} className="text-gray-400 shrink-0" />
                  <span className="text-xs font-medium truncate">{candidate.email || "N/A"}</span>
                </div>
                {candidate.email && candidate.email !== "N/A" && (
                  <button 
                    onClick={() => handleCopy(candidate.email, 'email')}
                    title="Copy Email"
                    className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700 transition-colors shrink-0 ml-2"
                  >
                    {copiedField === 'email' ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  </button>
                )}
              </div>
              <div className="flex items-center justify-between text-gray-500 group">
                <div className="flex items-center gap-3 min-w-0">
                  <Phone size={14} className="text-gray-400 shrink-0" />
                  <span className="text-xs font-medium">{candidate.phone || "N/A"}</span>
                </div>
                {candidate.phone && candidate.phone !== "N/A" && (
                  <button 
                    onClick={() => handleCopy(candidate.phone, 'phone')}
                    title="Copy Phone"
                    className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700 transition-colors shrink-0 ml-2"
                  >
                    {copiedField === 'phone' ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* ─── RIGHT: DETAILED ANALYSIS ─── */}
          <div className={`flex-1 p-3.5 sm:p-6 md:p-8 md:overflow-y-auto bg-white ${mobileTab !== 'overview' ? 'block' : 'hidden md:block'}`}>

            {/* Formula Banner */}
            <div className={`bg-gradient-to-r from-gray-900 to-gray-800 text-white p-4 sm:p-5 rounded-2xl mb-6 sm:mb-8 shadow-lg ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2 mb-3">
                <Target size={16} className="text-emerald-400" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">Score Explanation</span>
              </div>
              {candidate.ai_powered ? (
                <>
                  <p className="text-xs sm:text-sm font-mono font-bold tracking-wide">
                    Overall = Gemini semantic analysis <span className="text-emerald-400">80%</span> + ATS rule validation <span className="text-blue-400">20%</span>
                  </p>
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/10">
                    <span className="text-xs text-gray-400 font-semibold">Result:</span>
                    <span className="text-base sm:text-lg font-black text-emerald-400">{Math.round(candidate.matchScore)}% final match</span>
                    <span className="text-xs text-gray-400 font-semibold hidden sm:inline">based on skills, experience, education, and semantic role fit.</span>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs sm:text-sm font-mono font-bold tracking-wide">
                    Overall = (Skills <span className="text-blue-400">{Math.round(candidate.skillsScore)}%</span> × 0.40) + (Experience <span className="text-purple-400">{Math.round(candidate.experienceScore)}%</span> × 0.40) + (Education <span className="text-amber-400">{Math.round(candidate.educationScore)}%</span> × 0.20)
                  </p>
                  <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-white/10">
                    <span className="text-xs text-gray-400 font-semibold">Result:</span>
                    <span className="text-base sm:text-lg font-black text-emerald-400">
                      {skillsContribution}% + {experienceContribution}% + {educationContribution}% = {calculatedContributionTotal}%
                    </span>
                    {Math.round(candidate.matchScore) !== calculatedContributionTotal && (
                      <span className="text-xs text-gray-400 font-semibold">Saved final score: {Math.round(candidate.matchScore)}%</span>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* ═══════ CANDIDATE RESUME DETAILS ═══════ */}
            <section className={`mb-6 sm:mb-8 ${mobileTab === 'resume' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex items-center justify-center w-8 h-8 bg-gray-100 rounded-xl">
                  <Mail size={16} className="text-gray-700" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">Candidate Resume Details</h3>
                  <p className="text-[10px] font-semibold text-gray-500">Parsed resume and submitted application information</p>
                </div>
              </div>

              <div className="grid md:grid-cols-2 gap-3 bg-gray-50/80 rounded-2xl border border-gray-100 p-5">
                <div className="bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Email</p>
                  <p className="text-xs font-bold text-gray-800 break-all">{candidate.email || "Not provided"}</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Phone</p>
                  <p className="text-xs font-bold text-gray-800">{candidate.phone || "Not provided"}</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Candidate Location</p>
                  <p className="text-xs font-bold text-gray-800">{candidate.location || "Not provided"}</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Target Job</p>
                  <p className="text-xs font-bold text-gray-800">{candidate.preferredJob || "Not provided"}</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Company / Previous Company</p>
                  <p className="text-xs font-bold text-gray-800">{candidate.company || "Not provided"}</p>
                </div>
                <div className="bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Education</p>
                  <p className="text-xs font-bold text-gray-800">
                    {[candidate.degree, candidate.college].filter(Boolean).join(" - ") || "Not provided"}
                  </p>
                </div>
                <div className="md:col-span-2 bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-1">Resume Experience / Relevance</p>
                  <p className="text-xs font-medium text-gray-700 leading-relaxed">
                    {candidate.relevance || candidate.relevant_experience || "Not provided"}
                  </p>
                </div>
                <div className="md:col-span-2 bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-2">Parsed Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {candidateSkills.length > 0 ? candidateSkills.map((skill, i) => (
                      <span key={i} className="px-3 py-1.5 bg-gray-50 text-gray-700 rounded-xl border border-gray-100 text-[11px] font-bold">
                        {skill}
                      </span>
                    )) : (
                      <span className="text-xs text-gray-400 italic">No skills were stored for this application.</span>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* ═══════ AI ASSESSMENT SUMMARY ═══════ */}
            <section className={`mb-6 sm:mb-8 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex items-center justify-center w-8 h-8 bg-emerald-100 rounded-xl">
                  <BookOpen size={16} className="text-emerald-600" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">Comprehensive Match Analysis</h3>
                  <p className="text-[10px] font-semibold text-emerald-600">
                    {candidate.ai_powered ? "Gemini-assisted assessment output" : "ATS assessment based on available scoring details"}
                  </p>
                </div>
              </div>

              <div className="bg-emerald-50/60 rounded-2xl border border-emerald-100 p-5 space-y-4">
                <div className="bg-white/80 p-4 rounded-xl border border-emerald-100/70">
                  <p className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider mb-2">Why This Candidate Received {Math.round(candidate.matchScore)}%</p>
                  <p className="text-xs text-gray-700 font-medium leading-relaxed">
                    {candidate.ai_summary || fallbackAssessment || "The score is based on how closely the candidate's extracted resume details align with the job requirements."}
                  </p>
                </div>

                {(hasAiInsights || fallbackAssessment) && (
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="bg-white/80 p-4 rounded-xl border border-emerald-100/70">
                      <div className="flex items-center gap-1.5 mb-3">
                        <CheckCircle2 size={13} className="text-emerald-500" />
                        <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Key Strengths</span>
                      </div>
                      <div className="space-y-2">
                        {(strengths.length ? strengths : [
                          candidate.skills_reason,
                          candidate.experienceScore >= 70 ? candidate.experience_reason : "",
                          candidate.educationScore >= 70 ? candidate.education_reason : ""
                        ].filter(Boolean).slice(0, 3)).map((item, i) => (
                          <p key={i} className="text-xs text-gray-700 font-medium leading-relaxed flex gap-2">
                            <CheckCircle2 size={12} className="text-emerald-500 shrink-0 mt-0.5" />
                            <span>{item}</span>
                          </p>
                        ))}
                      </div>
                    </div>

                    <div className="bg-white/80 p-4 rounded-xl border border-amber-100/80">
                      <div className="flex items-center gap-1.5 mb-3">
                        <AlertTriangle size={13} className="text-amber-500" />
                        <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">Risk Areas / Gaps</span>
                      </div>
                      <div className="space-y-2">
                        {(weaknesses.length ? weaknesses : [
                          missingSkills.length ? `Missing important skills: ${missingSkills.join(', ')}.` : "",
                          candidate.experienceScore < 70 ? candidate.experience_reason : "",
                          candidate.educationScore < 70 ? candidate.education_reason : ""
                        ].filter(Boolean).slice(0, 3)).map((item, i) => (
                          <p key={i} className="text-xs text-gray-700 font-medium leading-relaxed flex gap-2">
                            <AlertTriangle size={12} className="text-amber-500 shrink-0 mt-0.5" />
                            <span>{item}</span>
                          </p>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* ═══════ 1. SKILLS MATCH BREAKDOWN ═══════ */}
            <section className={`mb-6 sm:mb-8 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex items-center justify-center w-8 h-8 bg-blue-100 rounded-xl">
                  <Zap size={16} className="text-blue-600" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">1. Skills Match Breakdown</h3>
                  <p className="text-[10px] font-semibold text-blue-600">{Math.round(candidate.skillsScore)}% — Contributes 40% to overall</p>
                </div>
              </div>

              <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5 space-y-4">
                {/* Matched Skills */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <CheckCircle2 size={13} className="text-emerald-500" />
                    <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Matched Skills Found</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {matchedSkills.length > 0 ? (
                      matchedSkills.map((skill, i) => <SkillTag key={i} skill={skill} type="matched" />)
                    ) : (
                      <span className="text-xs text-gray-400 italic">
                        {hasStoredBreakdown ? "No matching skills detected" : "Matched skills were not stored for this application."}
                      </span>
                    )}
                  </div>
                </div>

                {/* Missing Skills */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <XCircle size={13} className="text-rose-500" />
                    <span className="text-[10px] font-bold text-rose-600 uppercase tracking-wider">Missing / Gap Skills</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {missingSkills.length > 0 ? (
                      missingSkills.map((skill, i) => <SkillTag key={i} skill={skill} type="missing" />)
                    ) : matchedSkills.length > 0 ? (
                      <span className="text-xs text-emerald-600 font-semibold">All required skills identified by the analysis are present.</span>
                    ) : (
                      <span className="text-xs text-gray-400 italic">Missing skill details were not stored for this application.</span>
                    )}
                  </div>
                </div>

                {/* Justification */}
                <div className="pt-3 border-t border-gray-200/60">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Justification</p>
                  <p className="text-xs text-gray-600 font-medium leading-relaxed">
                    {candidate.skills_reason || "Skills were analyzed against the job description requirements."}
                  </p>
                </div>
              </div>
            </section>

            {/* ═══════ 2. EXPERIENCE MATCH BREAKDOWN ═══════ */}
            <section className={`mb-6 sm:mb-8 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex items-center justify-center w-8 h-8 bg-purple-100 rounded-xl">
                  <Briefcase size={16} className="text-purple-600" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">2. Experience Match Breakdown</h3>
                  <p className="text-[10px] font-semibold text-purple-600">{Math.round(candidate.experienceScore)}% — Contributes 40% to overall</p>
                </div>
              </div>

              <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5 space-y-4">
                {/* Relevant Experience */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <TrendingUp size={13} className="text-purple-500" />
                    <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider">Relevant Experience Found</span>
                  </div>
                  <p className="text-xs text-gray-700 font-medium leading-relaxed bg-white p-3 rounded-xl border border-gray-100">
                    {candidate.relevant_experience || "Experience details extracted from resume parsing."}
                  </p>
                </div>

                {/* Experience Gaps */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <AlertTriangle size={13} className="text-amber-500" />
                    <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">Experience Gaps</span>
                  </div>
                  <div className="flex items-center gap-3 bg-white p-3 rounded-xl border border-gray-100">
                    <span className="text-xs text-gray-600 font-semibold">
                      {candidate.experience_gaps || "No specific gaps identified."}
                    </span>
                  </div>
                </div>

                {/* Justification */}
                <div className="pt-3 border-t border-gray-200/60">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Justification</p>
                  <p className="text-xs text-gray-600 font-medium leading-relaxed">
                    {candidate.experience_reason || "Experience was analyzed based on extracted years and role relevance."}
                  </p>
                </div>
              </div>
            </section>

            {/* ═══════ 3. EDUCATION MATCH BREAKDOWN ═══════ */}
            <section className={`mb-6 sm:mb-8 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex items-center justify-center w-8 h-8 bg-amber-100 rounded-xl">
                  <GraduationCap size={16} className="text-amber-600" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">3. Education & Certification Breakdown</h3>
                  <p className="text-[10px] font-semibold text-amber-600">{Math.round(candidate.educationScore)}% — Contributes 20% to overall</p>
                </div>
              </div>

              <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5 space-y-4">
                {/* Qualifications Met */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <Award size={13} className="text-emerald-500" />
                    <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider">Target Qualifications Met</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-white p-3 rounded-xl border border-gray-100">
                      <p className="text-[9px] font-bold text-gray-400 uppercase mb-0.5">Candidate Degree</p>
                      <p className="text-sm font-bold text-gray-800">
                        {candidate.candidate_degree || candidate.degree || "Not specified"}
                      </p>
                    </div>
                    <div className="bg-white p-3 rounded-xl border border-gray-100">
                      <p className="text-[9px] font-bold text-gray-400 uppercase mb-0.5">Required Degree</p>
                      <p className="text-sm font-bold text-gray-800">
                        {candidate.required_degree || "Any"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Qualifications Lacking */}
                {candidate.educationScore < 100 && (
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <AlertTriangle size={13} className="text-amber-500" />
                      <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider">Qualifications Lacking</span>
                    </div>
                    <p className="text-xs text-gray-600 font-medium bg-white p-3 rounded-xl border border-gray-100">
                      {candidate.required_degree && candidate.candidate_degree && candidate.required_degree !== "Any"
                        ? `The JD requires a ${candidate.required_degree} degree, but the candidate holds a ${candidate.candidate_degree} degree.`
                        : "No significant education gaps detected."
                      }
                    </p>
                  </div>
                )}

                {/* Justification */}
                <div className="pt-3 border-t border-gray-200/60">
                  <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Justification</p>
                  <p className="text-xs text-gray-600 font-medium leading-relaxed">
                    {candidate.education_reason || "Education was analyzed based on degree level and field of study."}
                  </p>
                </div>
              </div>
            </section>

            {/* ═══════ OPTIMIZATION RECOMMENDATIONS ═══════ */}
            <section className={`mb-6 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center gap-2.5 mb-4">
                <div className="flex items-center justify-center w-8 h-8 bg-gradient-to-br from-emerald-100 to-teal-100 rounded-xl">
                  <Lightbulb size={16} className="text-emerald-600" />
                </div>
                <div>
                  <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">Optimization Recommendations</h3>
                  <p className="text-[10px] font-semibold text-emerald-600">Actionable steps to improve alignment</p>
                </div>
              </div>

              <div className="bg-gradient-to-br from-emerald-50/80 to-teal-50/50 rounded-2xl border border-emerald-100 p-5">
                {(candidate.recommendations && candidate.recommendations.length > 0) ? (
                  <div className="space-y-3">
                    {candidate.recommendations.map((rec, i) => (
                      <div key={i} className="flex gap-3 items-start bg-white/70 p-3.5 rounded-xl border border-emerald-100/60">
                        <div className="flex items-center justify-center w-6 h-6 bg-emerald-100 rounded-lg shrink-0 mt-0.5">
                          <span className="text-[10px] font-black text-emerald-700">{i + 1}</span>
                        </div>
                        <p className="text-xs text-gray-700 font-medium leading-relaxed">{rec}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="flex gap-3 items-start bg-white/70 p-3.5 rounded-xl border border-emerald-100/60">
                      <ChevronRight size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                      <p className="text-xs text-gray-700 font-medium leading-relaxed">
                        Tailor the resume summary to mirror the exact language and keywords used in the job description for maximum ATS compatibility.
                      </p>
                    </div>
                    <div className="flex gap-3 items-start bg-white/70 p-3.5 rounded-xl border border-emerald-100/60">
                      <ChevronRight size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                      <p className="text-xs text-gray-700 font-medium leading-relaxed">
                        Quantify achievements with metrics (e.g., "Improved page load by 40%") to strengthen experience relevance.
                      </p>
                    </div>
                    <div className="flex gap-3 items-start bg-white/70 p-3.5 rounded-xl border border-emerald-100/60">
                      <ChevronRight size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                      <p className="text-xs text-gray-700 font-medium leading-relaxed">
                        Include relevant certifications or professional development courses to bolster the education section.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </section>

            {/* ─── Core Expertise Tags ─── */}
            <section className={`mb-4 pt-6 border-t border-gray-100 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-tight mb-4 flex items-center gap-2">
                <Star size={16} className="text-[#d81159]" /> Core Expertise
              </h3>
              <div className="flex flex-wrap gap-2">
                {candidateSkills.map((skill, i) => (
                  <span key={i} className="px-3.5 py-1.5 bg-gray-50 text-gray-700 rounded-xl border border-gray-100 text-xs font-semibold hover:bg-pink-50 hover:border-pink-100 hover:text-[#d81159] transition-all duration-150 cursor-default">
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          </div>
        </div>

        {/* ─── Footer ─── */}
        <div className="p-4 sm:p-6 border-t border-gray-100 bg-gray-50/50 flex flex-wrap sm:flex-nowrap justify-end gap-2.5 sm:gap-3 shrink-0">
          <button onClick={onClose} className="w-full sm:w-auto px-5 sm:px-6 py-2.5 bg-white border border-gray-200 text-gray-600 rounded-xl text-xs sm:text-sm font-bold hover:bg-gray-50 transition-all text-center">
            Close Preview
          </button>
          
          {onOpenInterview && (
            <button
              onClick={() => {
                onClose();
                onOpenInterview(candidate);
              }}
              className="w-full sm:w-auto px-5 sm:px-6 py-2.5 bg-gray-900 text-white rounded-xl text-xs sm:text-sm font-bold hover:bg-gray-800 transition-all inline-flex items-center justify-center gap-2 text-center shadow-sm"
            >
              <Calendar size={15} />
              Schedule Interview
            </button>
          )}

          {candidate.resumeUrl ? (
            <button 
              onClick={() => {
                const fullUrl = getAssetUrl(candidate.resumeUrl);
                const link = document.createElement('a');
                link.href = fullUrl;
                link.download = `${candidate.name.replace(/\s+/g, '_')}_Resume`;
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
              }}
              className="w-full sm:w-auto px-5 sm:px-6 py-2.5 bg-[#d81159] text-white rounded-xl text-xs sm:text-sm font-bold hover:shadow-lg hover:shadow-pink-200 transition-all inline-flex items-center justify-center gap-2 text-center"
            >
              <Download size={15} />
              Download Resume
            </button>
          ) : (
            <button 
              disabled
              className="w-full sm:w-auto px-5 sm:px-6 py-2.5 bg-gray-200 text-gray-400 rounded-xl text-xs sm:text-sm font-bold cursor-not-allowed inline-flex items-center justify-center gap-2 text-center"
              title="Resume file not available"
            >
              <Download size={15} />
              Resume Unavailable
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ViewCandidateDetailsModal;
