import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  X, MapPin, Briefcase, Star, GraduationCap, Mail, Phone, 
  Target, TrendingUp, Lightbulb, CheckCircle2, XCircle, AlertTriangle,
  ChevronRight, Zap, BarChart3, BookOpen, Award, Copy, Check, Calendar, Download,
  Building2, Clock
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

/* ─── Score Ring ─── */
interface ScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
}

const ScoreRing: React.FC<ScoreRingProps> = ({ score, size = 120, strokeWidth = 10, color }) => {
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
interface PillarBarProps {
  label: string;
  score: number;
  weight: number;
  color: string;
  bgColor: string;
  borderColor: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const PillarBar: React.FC<PillarBarProps> = ({ label, score, weight, color, bgColor, borderColor, icon: Icon }) => {
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
interface SkillTagProps {
  skill: string;
  type: 'matched' | 'missing';
}

const SkillTag: React.FC<SkillTagProps> = ({ skill, type }) => (
  <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-[11px] font-bold tracking-tight border transition-all duration-200 ${
    type === 'matched' 
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
      : 'bg-rose-50 text-rose-600 border-rose-200'
  }`}>
    {type === 'matched' ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
    {skill}
  </span>
);

export interface ViewCandidateDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: any;
  onOpenInterview?: (candidate: any) => void;
  onScheduleInterview?: (candidate: any) => void;
  onUpdateStatus?: (id: string | number, status: string) => Promise<any> | void;
}

const ViewCandidateDetailsModal: React.FC<ViewCandidateDetailsModalProps> = ({ 
  isOpen, 
  onClose, 
  candidate, 
  onOpenInterview, 
  onScheduleInterview,
  onUpdateStatus 
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<'overview' | 'analysis' | 'resume'>('overview');

  if (!isOpen || !candidate) return null;

  const handleCopy = (text?: string, field?: string) => {
    if (!text || text === 'N/A' || !field) return;
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleInterviewAction = onOpenInterview || onScheduleInterview;

  const skillsContribution = Math.round((candidate.skillsScore || 0) * 0.40);
  const experienceContribution = Math.round((candidate.experienceScore || 0) * 0.40);
  const educationContribution = Math.round((candidate.educationScore || 0) * 0.20);
  const strengths = candidate.strengths || [];
  const weaknesses = candidate.weaknesses || [];
  const matchedSkills = candidate.matched_skills || [];
  const missingSkills = candidate.missing_skills || [];
  const candidateSkills = (candidate.skills && candidate.skills.length > 0) ? candidate.skills : matchedSkills;
  const calculatedContributionTotal = skillsContribution + experienceContribution + educationContribution;

  const formatMonths = (months?: number) => {
    if (!months || months <= 0) return null;
    const years = Math.floor(months / 12);
    const remainingMonths = months % 12;
    if (years > 0 && remainingMonths > 0) {
      return `${years} yr${years > 1 ? 's' : ''} ${remainingMonths} mo${remainingMonths > 1 ? 's' : ''}`;
    }
    if (years > 0) {
      return `${years} year${years > 1 ? 's' : ''}`;
    }
    return `${months} month${months > 1 ? 's' : ''}`;
  };

  const getEmpTypeBadge = (type?: string) => {
    const t = (type || 'Full-time').toLowerCase();
    if (t.includes('ojt') || t.includes('intern') || t.includes('practicum') || t.includes('trainee')) {
      return {
        bg: 'bg-orange-50 text-orange-700 border-orange-200',
        label: type || 'OJT / Internship'
      };
    }
    if (t.includes('contract') || t.includes('endo') || t.includes('agency')) {
      return {
        bg: 'bg-amber-50 text-amber-700 border-amber-200',
        label: type || 'Contractual'
      };
    }
    if (t.includes('part-time') || t.includes('part time')) {
      return {
        bg: 'bg-blue-50 text-blue-700 border-blue-200',
        label: type || 'Part-time'
      };
    }
    if (t.includes('seasonal')) {
      return {
        bg: 'bg-purple-50 text-purple-700 border-purple-200',
        label: type || 'Seasonal'
      };
    }
    return {
      bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      label: type || 'Full-time'
    };
  };

  const getEduLevelBadge = (level?: string) => {
    const l = (level || '').toLowerCase();
    if (l.includes('postgraduate') || l.includes('master') || l.includes('doctor')) {
      return { bg: 'bg-purple-50 text-purple-700 border-purple-200', label: level || 'Postgraduate' };
    }
    if (l.includes('tertiary') || l.includes('college') || l.includes('bachelor')) {
      return { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: level || 'Tertiary / College' };
    }
    if (l.includes('vocational') || l.includes('tesda') || l.includes('technical')) {
      return { bg: 'bg-teal-50 text-teal-700 border-teal-200', label: level || 'Vocational / Technical (TESDA)' };
    }
    if (l.includes('senior high') || l.includes('shs')) {
      return { bg: 'bg-orange-50 text-orange-700 border-orange-200', label: level || 'Senior High School (SHS)' };
    }
    if (l.includes('secondary') || l.includes('junior high') || l.includes('high school')) {
      return { bg: 'bg-slate-50 text-slate-700 border-slate-200', label: level || 'Secondary / High School' };
    }
    if (l.includes('primary') || l.includes('elementary')) {
      return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: level || 'Primary / Elementary' };
    }
    return { bg: 'bg-gray-50 text-gray-700 border-gray-200', label: level || 'Education' };
  };

  const getEduStatusBadge = (status?: string) => {
    const s = (status || '').toLowerCase();
    if (s.includes('undergrad') || s.includes('college level')) {
      return { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: status || 'Undergraduate / College Level' };
    }
    if (s.includes('ongoing') || s.includes('enrolled')) {
      return { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: status || 'Ongoing' };
    }
    if (s.includes('completed') || s.includes('completer')) {
      return { bg: 'bg-teal-50 text-teal-700 border-teal-200', label: status || 'Completed' };
    }
    return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: status || 'Graduated' };
  };

  const getCertCategoryBadge = (category?: string) => {
    const c = (category || '').toLowerCase();
    if (c.includes('prc') || c.includes('government') || c.includes('license')) {
      return { bg: 'bg-rose-50 text-rose-700 border-rose-200', label: category || 'PRC / Government License' };
    }
    if (c.includes('tesda') || c.includes('nc') || c.includes('vocational')) {
      return { bg: 'bg-teal-50 text-teal-700 border-teal-200', label: category || 'TESDA National Certificate' };
    }
    if (c.includes('safety') || c.includes('dole') || c.includes('oshc') || c.includes('first aid') || c.includes('bls') || c.includes('bosh')) {
      return { bg: 'bg-orange-50 text-orange-700 border-orange-200', label: category || 'Safety & Compliance' };
    }
    if (c.includes('it') || c.includes('tech') || c.includes('aws') || c.includes('cisco') || c.includes('microsoft')) {
      return { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: category || 'IT & Technical Certification' };
    }
    return { bg: 'bg-purple-50 text-purple-700 border-purple-200', label: category || 'Professional Certification' };
  };

  const extractedCertifications = useMemo(() => {
    if (candidate.certifications_details?.certifications && candidate.certifications_details.certifications.length > 0) {
      return candidate.certifications_details.certifications;
    }
    const raw = candidate.certifications || candidate.candidate_certifications || "";
    if (!raw) return [];
    const list = typeof raw === 'string'
      ? raw.split('|').map((s: string) => s.trim()).filter(Boolean)
      : (Array.isArray(raw) ? raw : []);

    return list.map((item: any) => {
      if (typeof item === 'object' && item !== null) return item;
      const name = String(item).trim();
      const lower = name.toLowerCase();
      let category = "Professional Certification";
      let issuer = "Accredited Body";

      if (lower.includes("prc") || lower.includes("registered engineer") || lower.includes("cpa") || lower.includes("lpt") || lower.includes("master plumber") || lower.includes("registered")) {
        category = "PRC / Government License";
        issuer = "PRC";
      } else if (lower.includes("tesda") || lower.includes("nc i") || lower.includes("nc ii") || lower.includes("nc iii")) {
        category = "TESDA National Certificate";
        issuer = "TESDA";
      } else if (lower.includes("bosh") || lower.includes("cosh") || lower.includes("dole") || lower.includes("first aid") || lower.includes("bls")) {
        category = "Safety & Compliance";
        issuer = lower.includes("red cross") ? "Philippine Red Cross" : "DOLE-OSHC";
      } else if (lower.includes("driver") || lower.includes("lto")) {
        category = "Government License";
        issuer = "LTO";
      } else if (lower.includes("civil service") || lower.includes("csc")) {
        category = "Civil Service Eligibility";
        issuer = "CSC";
      }

      return {
        canonical_name: name,
        category,
        issuing_organization: issuer,
        status: "Verified / Active"
      };
    });
  }, [candidate.certifications_details, candidate.certifications, candidate.candidate_certifications]);
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
                    {(candidate.name || 'C').charAt(0)}
                  </div>
                )}
              </div>
              <h2 className="text-lg font-black text-gray-900 tracking-tight">{candidate.name}</h2>
              <p className="text-xs text-gray-500 font-semibold mt-0.5">{candidate.preferredJob}</p>
            </div>

            {/* Overall Score Ring */}
            <div className="flex flex-col items-center mb-7">
              <ScoreRing score={candidate.matchScore || 0} />
              <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-3">Overall Match Score</p>
            </div>

            {/* Score Pillar Bars */}
            <div className="space-y-3 mb-7">
              <PillarBar label="Skills" score={candidate.skillsScore || 0} weight={40}
                color="text-blue-600" bgColor="bg-blue-50/70" borderColor="border-blue-100" icon={Zap} />
              <PillarBar label="Experience" score={candidate.experienceScore || 0} weight={40}
                color="text-purple-600" bgColor="bg-purple-50/70" borderColor="border-purple-100" icon={Briefcase} />
              <PillarBar label="Education" score={candidate.educationScore || 0} weight={20}
                color="text-amber-600" bgColor="bg-amber-50/70" borderColor="border-amber-100" icon={GraduationCap} />
              {candidate.certificationsScore !== undefined && candidate.certificationsScore > 0 && (
                <PillarBar label="Certifications" score={candidate.certificationsScore} weight={10}
                  color="text-rose-600" bgColor="bg-rose-50/70" borderColor="border-rose-100" icon={Award} />
              )}
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
                    <span className="text-base sm:text-lg font-black text-emerald-400">{Math.round(candidate.matchScore || 0)}% final match</span>
                    <span className="text-xs text-gray-400 font-semibold hidden sm:inline">based on skills, experience, education, and semantic role fit.</span>
                  </div>
                </>
              ) : (
                <>
                  <p className="text-xs sm:text-sm font-mono font-bold tracking-wide">
                    Overall = (Skills <span className="text-blue-400">{Math.round(candidate.skillsScore || 0)}%</span> × 0.40) + (Experience <span className="text-purple-400">{Math.round(candidate.experienceScore || 0)}%</span> × 0.40) + (Education <span className="text-amber-400">{Math.round(candidate.educationScore || 0)}%</span> × 0.20)
                  </p>
                  <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-white/10">
                    <span className="text-xs text-gray-400 font-semibold">Result:</span>
                    <span className="text-base sm:text-lg font-black text-emerald-400">
                      {skillsContribution}% + {experienceContribution}% + {educationContribution}% = {calculatedContributionTotal}%
                    </span>
                    {Math.round(candidate.matchScore || 0) !== calculatedContributionTotal && (
                      <span className="text-xs text-gray-400 font-semibold">Saved final score: {Math.round(candidate.matchScore || 0)}%</span>
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
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[9px] font-bold text-gray-400 uppercase">Education</p>
                    {candidate.highest_educational_attainment && (
                      <span className="text-[9px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                        {candidate.highest_educational_attainment}
                      </span>
                    )}
                  </div>
                  <p className="text-xs font-bold text-gray-800">
                    {[candidate.degree, candidate.college].filter(Boolean).join(" - ") || "Not provided"}
                  </p>
                </div>
                <div className="md:col-span-2 bg-white p-3 rounded-xl border border-gray-100">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[9px] font-bold text-gray-400 uppercase">Resume Experience / Relevance</p>
                    {candidate.total_experience_months ? (
                      <span className="text-[10px] font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded-md border border-purple-100 flex items-center gap-1">
                        <Clock size={10} />
                        {formatMonths(candidate.total_experience_months)}
                        {candidate.work_experiences?.length ? ` • ${candidate.work_experiences.length} ${candidate.work_experiences.length === 1 ? 'role' : 'roles'}` : ''}
                      </span>
                    ) : null}
                  </div>
                  <p className="text-xs font-medium text-gray-700 leading-relaxed">
                    {candidate.relevance || candidate.relevant_experience || "Not provided"}
                  </p>
                </div>
                <div className="md:col-span-2 bg-white p-3 rounded-xl border border-gray-100">
                  <p className="text-[9px] font-bold text-gray-400 uppercase mb-2">Parsed Skills</p>
                  <div className="flex flex-wrap gap-1.5">
                    {candidateSkills.length > 0 ? candidateSkills.map((skill: string, i: number) => (
                      <span key={i} className="px-3 py-1.5 bg-gray-50 text-gray-700 rounded-xl border border-gray-100 text-[11px] font-bold">
                        {skill}
                      </span>
                    )) : (
                      <span className="text-xs text-gray-400 italic">No skills were stored for this application.</span>
                    )}
                  </div>
                </div>
                <div className="md:col-span-2 bg-white p-3 rounded-xl border border-gray-100">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[9px] font-bold text-gray-400 uppercase">Licenses, Eligibility & Certifications</p>
                    {extractedCertifications.length > 0 && (
                      <span className="text-[10px] font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                        {extractedCertifications.length} {extractedCertifications.length === 1 ? 'credential' : 'credentials'}
                      </span>
                    )}
                  </div>
                  {extractedCertifications.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {extractedCertifications.map((c: any, i: number) => (
                        <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 text-rose-700 rounded-xl border border-rose-200 text-[11px] font-bold shadow-xs">
                          <Award size={12} className="text-rose-500 shrink-0" />
                          <span>{c.canonical_name || c}</span>
                          {c.issuing_organization && (
                            <span className="text-[9px] text-rose-500 font-semibold bg-white/80 px-1.5 py-0.5 rounded border border-rose-100">
                              {c.issuing_organization}
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 italic">No specific licenses or certifications listed in resume.</p>
                  )}
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
                  <p className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider mb-2">Why This Candidate Received {Math.round(candidate.matchScore || 0)}%</p>
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
                        ].filter(Boolean).slice(0, 3)).map((item: string, i: number) => (
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
                        ].filter(Boolean).slice(0, 3)).map((item: string, i: number) => (
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
                  <p className="text-[10px] font-semibold text-blue-600">{Math.round(candidate.skillsScore || 0)}% — Contributes 40% to overall</p>
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
                      matchedSkills.map((skill: string, i: number) => <SkillTag key={i} skill={skill} type="matched" />)
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
                      missingSkills.map((skill: string, i: number) => <SkillTag key={i} skill={skill} type="missing" />)
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
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 bg-purple-100 rounded-xl">
                    <Briefcase size={16} className="text-purple-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">2. Experience Match Breakdown</h3>
                    <p className="text-[10px] font-semibold text-purple-600">{Math.round(candidate.experienceScore || 0)}% — Contributes 40% to overall</p>
                  </div>
                </div>
                {/* Tenure Pill / Summary Pill */}
                {candidate.total_experience_months ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-50 text-purple-700 rounded-full border border-purple-200 text-xs font-bold shadow-xs">
                    <Clock size={12} className="text-purple-600" />
                    {formatMonths(candidate.total_experience_months)} Total
                  </span>
                ) : candidate.experience ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-50 text-purple-700 rounded-full border border-purple-200 text-xs font-bold shadow-xs">
                    <Clock size={12} className="text-purple-600" />
                    {candidate.experience} {Number(candidate.experience) === 1 ? 'year' : 'years'}
                  </span>
                ) : null}
              </div>

              <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5 space-y-4">
                {/* Structured Work Experience Timeline */}
                {candidate.work_experiences && candidate.work_experiences.length > 0 ? (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-1.5">
                        <TrendingUp size={13} className="text-purple-500" />
                        <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider">
                          Extracted Work History ({candidate.work_experiences.length} {candidate.work_experiences.length === 1 ? 'Role' : 'Roles'})
                        </span>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      {candidate.work_experiences.map((exp: any, idx: number) => {
                        const badge = getEmpTypeBadge(exp.employment_type);
                        const durationFormatted = formatMonths(exp.duration_months);
                        return (
                          <div 
                            key={idx} 
                            className="bg-white rounded-xl border border-gray-100/80 p-4 shadow-xs hover:border-purple-200 transition-all duration-200"
                          >
                            {/* Role Header */}
                            <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                              <div>
                                <h4 className="text-xs sm:text-sm font-bold text-gray-900 flex items-center gap-2">
                                  {exp.job_title}
                                  {badge && (
                                    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold border ${badge.bg}`}>
                                      {badge.label}
                                    </span>
                                  )}
                                </h4>
                                {exp.raw_job_title && exp.raw_job_title.toLowerCase() !== exp.job_title.toLowerCase() && (
                                  <p className="text-[11px] text-gray-400 italic">
                                    Resume title: "{exp.raw_job_title}"
                                  </p>
                                )}
                              </div>

                              {/* Dates & Duration */}
                              {(exp.start_date || exp.end_date || durationFormatted) && (
                                <div className="text-right flex flex-col items-end">
                                  <span className="text-xs font-semibold text-gray-700">
                                    {[exp.start_date, exp.end_date || 'Present'].filter(Boolean).join(' – ')}
                                  </span>
                                  {durationFormatted && (
                                    <span className="text-[10px] font-medium text-purple-600 flex items-center gap-1">
                                      <Clock size={10} />
                                      {durationFormatted}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>

                            {/* Employer & Location */}
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600 mb-3">
                              {exp.company_name && (
                                <div className="flex items-center gap-1.5 font-medium text-gray-700">
                                  <Building2 size={13} className="text-gray-400" />
                                  <span>{exp.company_name}</span>
                                </div>
                              )}
                              {exp.location && (
                                <div className="flex items-center gap-1.5 text-gray-500">
                                  <MapPin size={12} className="text-gray-400" />
                                  <span>{exp.location}</span>
                                </div>
                              )}
                            </div>

                            {/* Duties / Responsibilities */}
                            {exp.responsibilities && exp.responsibilities.length > 0 && (
                              <div className="mt-2.5 pt-2.5 border-t border-gray-100">
                                <p className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                                  Key Duties & Achievements
                                </p>
                                <ul className="space-y-1">
                                  {exp.responsibilities.map((duty: string, dIdx: number) => (
                                    <li key={dIdx} className="text-xs text-gray-600 flex items-start gap-2 leading-relaxed">
                                      <span className="text-purple-400 mt-1 shrink-0">•</span>
                                      <span>{duty}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  /* Fallback when no structured experiences are found */
                  <div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <TrendingUp size={13} className="text-purple-500" />
                      <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider">Relevant Experience Found</span>
                    </div>
                    <p className="text-xs text-gray-700 font-medium leading-relaxed bg-white p-3 rounded-xl border border-gray-100">
                      {candidate.relevant_experience || "Experience details extracted from resume parsing."}
                    </p>
                  </div>
                )}

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
              <div className="flex items-center justify-between gap-2.5 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 bg-amber-100 rounded-xl">
                    <GraduationCap size={16} className="text-amber-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">3. Educational Background & Academic Attainment</h3>
                    <p className="text-[10px] font-semibold text-amber-600">{Math.round(candidate.educationScore || 0)}% — Contributes 20% to overall</p>
                  </div>
                </div>
                {candidate.highest_educational_attainment && (
                  <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-50 rounded-full border border-amber-200">
                    <GraduationCap size={13} className="text-amber-600" />
                    <span className="text-xs font-bold text-amber-800">
                      {candidate.highest_educational_attainment}
                    </span>
                  </div>
                )}
              </div>

              <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5 space-y-4">
                {/* Structured Education History */}
                {candidate.education_entries && candidate.education_entries.length > 0 ? (
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-1.5">
                        <GraduationCap size={13} className="text-amber-600" />
                        <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">
                          Educational History & Certifications ({candidate.education_entries.length})
                        </span>
                      </div>
                      {candidate.highest_educational_attainment && (
                        <span className="text-[10px] font-semibold text-gray-500">
                          Highest: <span className="text-amber-700 font-bold">{candidate.highest_educational_attainment}</span>
                        </span>
                      )}
                    </div>

                    <div className="space-y-3">
                      {candidate.education_entries.map((edu: any, idx: number) => {
                        const levelBadge = getEduLevelBadge(edu.education_level);
                        const statusBadge = getEduStatusBadge(edu.status);
                        const displayDegree = edu.degree_or_course || edu.raw_degree_or_course || "Degree / Course";
                        const yearsDisplay = [edu.start_year, edu.end_year].filter(Boolean).join(' – ');

                        return (
                          <div 
                            key={idx}
                            className="bg-white p-4 rounded-xl border border-gray-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:border-amber-200 transition-colors"
                          >
                            {/* Card Header: Level Badge & Status Badge & Years */}
                            <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                              <div className="flex flex-wrap items-center gap-1.5">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${levelBadge.bg}`}>
                                  {levelBadge.label}
                                </span>
                                {edu.status && (
                                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${statusBadge.bg}`}>
                                    {statusBadge.label}
                                  </span>
                                )}
                              </div>
                              {yearsDisplay && (
                                <div className="text-right flex items-center gap-1 text-xs font-semibold text-gray-600">
                                  <Calendar size={11} className="text-gray-400" />
                                  <span>{yearsDisplay}</span>
                                </div>
                              )}
                            </div>

                            {/* Degree or Course */}
                            <h4 className="text-sm font-bold text-gray-900 leading-snug">
                              {displayDegree}
                            </h4>

                            {/* Major or Specialization */}
                            {edu.major_or_specialization && (
                              <p className="text-xs text-amber-700 font-medium mt-0.5">
                                Major / Specialization: <span className="font-semibold">{edu.major_or_specialization}</span>
                              </p>
                            )}

                            {/* Institution & Location */}
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600 mt-2">
                              {edu.institution_name && (
                                <div className="flex items-center gap-1.5 font-medium text-gray-700">
                                  <Building2 size={13} className="text-gray-400" />
                                  <span>{edu.institution_name}</span>
                                </div>
                              )}
                              {edu.location && (
                                <div className="flex items-center gap-1.5 text-gray-500">
                                  <MapPin size={12} className="text-gray-400" />
                                  <span>{edu.location}</span>
                                </div>
                              )}
                            </div>

                            {/* Honors & Awards */}
                            {edu.honors_and_awards && edu.honors_and_awards.length > 0 && (
                              <div className="mt-2.5 pt-2 border-t border-gray-100 flex flex-wrap items-center gap-1.5">
                                <Award size={12} className="text-amber-500 shrink-0" />
                                {edu.honors_and_awards.map((honor: string, hIdx: number) => (
                                  <span 
                                    key={hIdx}
                                    className="text-[10px] font-bold text-amber-800 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200/80"
                                  >
                                    {honor}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ) : (
                  /* Fallback when no structured entries exist */
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
                )}

                {/* Qualifications Lacking */}
                {(candidate.educationScore || 0) < 100 && (
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

            {/* ═══════ 4. LICENSES, ELIGIBILITY & CERTIFICATIONS ═══════ */}
            <section className={`mb-6 sm:mb-8 ${mobileTab === 'analysis' ? 'block' : 'hidden md:block'}`}>
              <div className="flex items-center justify-between gap-2.5 mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center justify-center w-8 h-8 bg-rose-100 rounded-xl">
                    <Award size={16} className="text-rose-600" />
                  </div>
                  <div>
                    <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">4. Licenses, Eligibility & Certifications</h3>
                    <p className="text-[10px] font-semibold text-rose-600">
                      PRC Licenses, TESDA National Certificates, Safety, Civil Service & Professional Credentials
                    </p>
                  </div>
                </div>
                {extractedCertifications.length > 0 && (
                  <div className="flex items-center gap-1.5 px-3 py-1 bg-rose-50 rounded-full border border-rose-200">
                    <Award size={13} className="text-rose-600" />
                    <span className="text-xs font-bold text-rose-800">
                      {extractedCertifications.length} {extractedCertifications.length === 1 ? 'Credential' : 'Credentials'}
                    </span>
                  </div>
                )}
              </div>

              <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5 space-y-4">
                {extractedCertifications.length > 0 ? (
                  <div className="space-y-3">
                    {extractedCertifications.map((c: any, idx: number) => {
                      const catBadge = getCertCategoryBadge(c.category);
                      return (
                        <div
                          key={idx}
                          className="bg-white p-4 rounded-xl border border-gray-200/80 shadow-[0_1px_3px_rgba(0,0,0,0.04)] hover:border-rose-200 transition-colors"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${catBadge.bg}`}>
                                {catBadge.label}
                              </span>
                              {c.status && (
                                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full border bg-emerald-50 text-emerald-700 border-emerald-200">
                                  {c.status}
                                </span>
                              )}
                            </div>
                            {c.issue_date && (
                              <div className="text-right flex items-center gap-1 text-xs font-semibold text-gray-600">
                                <Calendar size={11} className="text-gray-400" />
                                <span>{c.issue_date}</span>
                              </div>
                            )}
                          </div>

                          <h4 className="text-sm font-bold text-gray-900 leading-snug">
                            {c.canonical_name || c}
                          </h4>

                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600 mt-2">
                            {c.issuing_organization && (
                              <div className="flex items-center gap-1.5 font-medium text-gray-700">
                                <Building2 size={13} className="text-gray-400" />
                                <span>Issuer: {c.issuing_organization}</span>
                              </div>
                            )}
                            {c.credential_id_or_details && (
                              <div className="flex items-center gap-1.5 text-rose-600 font-medium">
                                <Award size={12} className="text-rose-400" />
                                <span>{c.credential_id_or_details}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="bg-white p-5 rounded-xl border border-gray-100 text-center py-6">
                    <Award size={26} className="text-gray-300 mx-auto mb-2" />
                    <p className="text-xs font-bold text-gray-700">No Specific Licenses or Certifications Detected</p>
                    <p className="text-[11px] text-gray-400 mt-0.5">The candidate did not list formal government licenses or certificates on this resume.</p>
                  </div>
                )}

                {/* Justification if provided */}
                {candidate.certifications_reason && (
                  <div className="pt-3 border-t border-gray-200/60">
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1">Assessment Justification</p>
                    <p className="text-xs text-gray-600 font-medium leading-relaxed">
                      {candidate.certifications_reason}
                    </p>
                  </div>
                )}
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
                    {candidate.recommendations.map((rec: string, i: number) => (
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
                {candidateSkills.map((skill: string, i: number) => (
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
          
          {handleInterviewAction && (
            <button
              onClick={() => {
                onClose();
                handleInterviewAction(candidate);
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
                link.download = `${(candidate.name || 'Candidate').replace(/\s+/g, '_')}_Resume`;
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
