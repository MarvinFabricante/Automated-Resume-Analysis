import React, { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { 
  X, MapPin, Briefcase, GraduationCap, Mail, Phone, 
  Target, TrendingUp, Lightbulb, CheckCircle2, XCircle, AlertTriangle,
  Zap, BarChart3, BookOpen, Award, Copy, Check, Calendar, Download,
  Building2, Clock, Sparkles, ShieldCheck, Printer, CheckCircle
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

/* ─── Types & Interfaces ─── */
export interface ViewCandidateDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidate: any;
  onOpenInterview?: (candidate: any) => void;
  onScheduleInterview?: (candidate: any) => void;
  onUpdateStatus?: (id: string | number, status: string) => Promise<any> | void;
}

type TabType = 'overview' | 'skills' | 'experience' | 'education' | 'recommendations' | 'all' | 'dossier';

/* ─── Fit Tier Helper ─── */
const getFitTier = (score: number) => {
  if (score >= 80) {
    return {
      label: 'Strong Match',
      tier: 'High Alignment',
      badgeBg: 'bg-emerald-50',
      badgeText: 'text-emerald-700',
      badgeBorder: 'border-emerald-200',
      accentColor: '#10b981',
      description: 'Candidate exhibits high alignment with core job description requirements.'
    };
  }
  if (score >= 65) {
    return {
      label: 'Good Match',
      tier: 'Moderate Alignment',
      badgeBg: 'bg-blue-50',
      badgeText: 'text-blue-700',
      badgeBorder: 'border-blue-200',
      accentColor: '#3b82f6',
      description: 'Solid candidate qualifications with manageable gaps in preferred criteria.'
    };
  }
  if (score >= 45) {
    return {
      label: 'Fair Match',
      tier: 'Partial Alignment',
      badgeBg: 'bg-amber-50',
      badgeText: 'text-amber-700',
      badgeBorder: 'border-amber-200',
      accentColor: '#f59e0b',
      description: 'Partially meets criteria; review skill gaps and experience relevance.'
    };
  }
  return {
    label: 'Low Match',
    tier: 'Significant Gaps',
    badgeBg: 'bg-rose-50',
    badgeText: 'text-rose-700',
    badgeBorder: 'border-rose-200',
    accentColor: '#ef4444',
    description: 'Extracted resume data reflects notable divergence from required qualifications.'
  };
};

/* ─── Score Ring ─── */
interface ScoreRingProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  color?: string;
}

const ScoreRing: React.FC<ScoreRingProps> = ({ score, size = 124, strokeWidth = 10, color }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedScore = Math.max(0, Math.min(100, score));
  const offset = circumference - (clampedScore / 100) * circumference;

  const getColor = () => {
    if (color) return color;
    if (score >= 80) return '#10b981';
    if (score >= 65) return '#3b82f6';
    if (score >= 45) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle 
          cx={size / 2} 
          cy={size / 2} 
          r={radius} 
          fill="none"
          stroke="#f1f5f9" 
          strokeWidth={strokeWidth} 
        />
        <circle 
          cx={size / 2} 
          cy={size / 2} 
          r={radius} 
          fill="none"
          stroke={getColor()} 
          strokeWidth={strokeWidth}
          strokeDasharray={circumference} 
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out" 
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-3xl font-black text-gray-900 tracking-tight leading-none">
          {Math.round(clampedScore)}
          <span className="text-base font-bold text-gray-400">%</span>
        </span>
        <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mt-1">
          ATS Score
        </span>
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
  barColor: string;
  bgColor: string;
  borderColor: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const PillarBar: React.FC<PillarBarProps> = ({ 
  label, 
  score, 
  weight, 
  color, 
  barColor, 
  bgColor, 
  borderColor, 
  icon: Icon 
}) => {
  const contribution = Math.round(score * (weight / 100));
  const clampedScore = Math.max(0, Math.min(100, score));

  return (
    <div className={`p-3 rounded-xl border ${borderColor} ${bgColor} transition-all duration-200 hover:shadow-xs`}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Icon size={13} className={color} />
          <span className="text-xs font-bold text-gray-800">{label}</span>
          <span className="text-[10px] font-semibold text-gray-400">({weight}%)</span>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className={`text-xs font-black ${color}`}>{Math.round(score)}%</span>
          <span className="text-[10px] font-semibold text-gray-400">→ {contribution} pts</span>
        </div>
      </div>
      <div className="w-full h-1.5 bg-white/80 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${barColor}`}
          style={{ width: `${clampedScore}%` }}
        />
      </div>
    </div>
  );
};

/* ─── Skill Tag Component ─── */
interface SkillTagProps {
  skill: string;
  type: 'matched' | 'missing' | 'neutral';
}

const SkillTag: React.FC<SkillTagProps> = ({ skill, type }) => {
  if (type === 'matched') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold tracking-tight bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs hover:bg-emerald-100/70 transition-colors">
        <CheckCircle2 size={13} className="text-emerald-600 shrink-0" />
        <span>{skill}</span>
      </span>
    );
  }
  if (type === 'missing') {
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold tracking-tight bg-rose-50 text-rose-700 border border-rose-200 shadow-2xs hover:bg-rose-100/70 transition-colors">
        <XCircle size={13} className="text-rose-500 shrink-0" />
        <span>{skill}</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-gray-50 text-gray-700 border border-gray-200/80 hover:bg-gray-100 transition-colors">
      <span>{skill}</span>
    </span>
  );
};

/* ─── Main Modal Component ─── */
const ViewCandidateDetailsModal: React.FC<ViewCandidateDetailsModalProps> = ({ 
  isOpen, 
  onClose, 
  candidate, 
  onOpenInterview, 
  onScheduleInterview,
  onUpdateStatus 
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  if (!isOpen || !candidate) return null;

  const handleCopy = (text?: string, field?: string) => {
    if (!text || text === 'N/A' || !field) return;
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleInterviewAction = onOpenInterview || onScheduleInterview;

  // Normalized Candidate Details
  const candidateName = candidate.name || candidate.candidate_name || 'Candidate';
  const candidateRole = candidate.preferredJob || candidate.job_title || candidate.job?.job_title || 'Position Applied';
  const candidateDept = candidate.jobDepartment || candidate.job?.department || '';
  const candidateLocation = candidate.location || 'Location Not Specified';
  const candidateEmail = candidate.email || candidate.candidate_email || 'Not provided';
  const candidatePhone = candidate.phone || 'Not provided';
  const candidateCompany = candidate.company || 'Not provided';
  const currentStatus = candidate.status || 'Pending';

  // Scoring Values
  const matchScore = Math.round(candidate.matchScore ?? candidate.match_score ?? 0);
  const skillsScore = Math.round(candidate.skillsScore ?? candidate.skills_score ?? 0);
  const experienceScore = Math.round(candidate.experienceScore ?? candidate.experience_score ?? 0);
  const educationScore = Math.round(candidate.educationScore ?? candidate.education_score ?? 0);
  const certificationsScore = candidate.certificationsScore ?? candidate.certifications_score;

  const skillsContribution = Math.round(skillsScore * 0.40);
  const experienceContribution = Math.round(experienceScore * 0.40);
  const educationContribution = Math.round(educationScore * 0.20);
  const calculatedContributionTotal = skillsContribution + experienceContribution + educationContribution;

  const strengths: string[] = candidate.strengths || [];
  const weaknesses: string[] = candidate.weaknesses || [];
  const matchedSkills: string[] = candidate.matched_skills || [];
  const missingSkills: string[] = candidate.missing_skills || [];
  const candidateSkills: string[] = (candidate.skills && candidate.skills.length > 0) ? candidate.skills : matchedSkills;
  const recommendations: string[] = candidate.recommendations || [];

  const fitTier = getFitTier(matchScore);

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
      return { bg: 'bg-orange-50 text-orange-700 border-orange-200', label: type || 'OJT / Internship' };
    }
    if (t.includes('contract') || t.includes('endo') || t.includes('agency')) {
      return { bg: 'bg-amber-50 text-amber-700 border-amber-200', label: type || 'Contractual' };
    }
    if (t.includes('part-time') || t.includes('part time')) {
      return { bg: 'bg-blue-50 text-blue-700 border-blue-200', label: type || 'Part-time' };
    }
    if (t.includes('seasonal')) {
      return { bg: 'bg-purple-50 text-purple-700 border-purple-200', label: type || 'Seasonal' };
    }
    return { bg: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: type || 'Full-time' };
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

  const extractedCertifications = (() => {
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
  })();

  const fallbackAssessment = [
    candidate.skills_reason,
    candidate.experience_reason,
    candidate.education_reason
  ].filter(Boolean).join(' ');

  // Tab definitions
  const tabs: { id: TabType; label: string; count?: number; icon: React.ComponentType<{ size?: number; className?: string }> }[] = [
    { id: 'overview', label: 'Executive Overview', icon: Target },
    { id: 'skills', label: 'Skills Gap', count: missingSkills.length ? missingSkills.length : undefined, icon: Zap },
    { id: 'experience', label: 'Work History', count: candidate.work_experiences?.length || undefined, icon: Briefcase },
    { id: 'education', label: 'Education & Licenses', count: (candidate.education_entries?.length || 0) + extractedCertifications.length || undefined, icon: GraduationCap },
    { id: 'recommendations', label: 'Recommendations', count: recommendations.length || undefined, icon: Lightbulb },
    { id: 'all', label: 'Full Report', icon: BookOpen },
  ];

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-[#0c0d12]/70 backdrop-blur-md transition-all duration-200">
      <Helmet>
        <title>{candidateName} | ATS Match Analysis</title>
      </Helmet>

      <div className="bg-white w-full max-w-6xl max-h-[96vh] sm:max-h-[92vh] rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-250 border border-gray-100">
        
        {/* ═══════ TOP HEADER ═══════ */}
        <header className="px-4 sm:px-6 py-3.5 border-b border-gray-100 flex flex-wrap justify-between items-center bg-white sticky top-0 z-20 shrink-0 gap-3">
          <div className="flex items-center gap-3 min-w-0">
            {/* ATS Badge */}
            <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 border border-emerald-200/80 rounded-xl shrink-0">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <BarChart3 size={14} className="text-emerald-700" />
              <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider">ATS Analysis Report</span>
            </div>

            {/* Fit Tier Badge */}
            <span className={`hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold border ${fitTier.badgeBg} ${fitTier.badgeText} ${fitTier.badgeBorder}`}>
              <Sparkles size={12} />
              {fitTier.label} • {matchScore}%
            </span>

            {/* Status Selector */}
            {onUpdateStatus && (
              <div className="flex items-center gap-1.5 pl-2 border-l border-gray-200">
                <span className="hidden md:inline text-[10px] font-bold text-gray-400 uppercase tracking-wider">Status:</span>
                <select
                  value={currentStatus}
                  onChange={(e) => onUpdateStatus(candidate.id, e.target.value)}
                  className="px-2.5 py-1 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-xl text-xs font-bold text-gray-800 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer transition-colors"
                >
                  {['Pending', 'Reviewed', 'Technical Interview', 'Final Interview', 'Accepted', 'Rejected', 'Archived'].map((st) => (
                    <option key={st} value={st}>{st}</option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Header Action Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              title="Print or Save Report"
              className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 rounded-xl text-xs font-bold transition-colors cursor-pointer"
            >
              <Printer size={13} />
              <span>Print</span>
            </button>

            <button 
              onClick={onClose} 
              aria-label="Close Analysis Modal"
              className="p-1.5 sm:p-2 hover:bg-gray-100 rounded-xl transition-colors text-gray-400 hover:text-gray-700 cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* ═══════ MOBILE TAB SWITCHER ═══════ */}
        <div className="flex md:hidden border-b border-gray-200 bg-gray-50/90 p-1.5 gap-1 shrink-0 overflow-x-auto scrollbar-none">
          <button
            type="button"
            onClick={() => setActiveTab('dossier')}
            className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all whitespace-nowrap cursor-pointer ${
              activeTab === 'dossier'
                ? 'bg-white text-[#D60041] shadow-xs'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Profile
          </button>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 text-xs font-bold rounded-xl transition-all whitespace-nowrap flex items-center gap-1.5 cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-white text-[#D60041] shadow-xs'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  activeTab === tab.id ? 'bg-pink-50 text-[#D60041]' : 'bg-gray-200 text-gray-600'
                }`}>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ═══════ MAIN CONTENT BODY ═══════ */}
        <div className="flex flex-col md:flex-row flex-1 overflow-y-auto md:overflow-hidden min-h-0 bg-white">
          
          {/* ─── LEFT DOSSIER SIDEBAR ─── */}
          <aside className={`w-full md:w-[320px] bg-gradient-to-b from-slate-50/80 via-white to-slate-50/50 border-b md:border-b-0 md:border-r border-gray-200/80 p-5 sm:p-6 md:overflow-y-auto shrink-0 ${
            activeTab === 'dossier' ? 'block' : 'hidden md:block'
          }`}>
            {/* Candidate Identity */}
            <div className="text-center mb-6">
              <div className="relative w-20 h-20 rounded-2xl overflow-hidden border-4 border-white shadow-md mx-auto mb-3 bg-pink-50">
                {candidate.profileImage ? (
                  <img src={getAssetUrl(candidate.profileImage)} alt={candidateName} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[#D60041] text-2xl font-black bg-gradient-to-br from-pink-100 to-rose-50">
                    {candidateName.charAt(0)}
                  </div>
                )}
              </div>
              <h2 className="text-lg font-black text-gray-900 tracking-tight leading-snug">{candidateName}</h2>
              <p className="text-xs text-[#D60041] font-bold mt-0.5 flex items-center justify-center gap-1">
                <Briefcase size={12} />
                <span>{candidateRole}</span>
              </p>
              {candidateDept && (
                <p className="text-[11px] text-gray-500 font-medium">{candidateDept}</p>
              )}
            </div>

            {/* Score Ring Section */}
            <div className="flex flex-col items-center mb-6 p-4 bg-white rounded-2xl border border-gray-100 shadow-2xs">
              <ScoreRing score={matchScore} />
              <div className="mt-3 text-center">
                <span className={`inline-block px-3 py-1 rounded-full text-xs font-black border ${fitTier.badgeBg} ${fitTier.badgeText} ${fitTier.badgeBorder}`}>
                  {fitTier.label}
                </span>
                <p className="text-[10px] text-gray-400 font-semibold mt-1">
                  {candidate.ai_powered ? "Gemini 2.5 AI Powered Analysis" : "ATS Automated Rule Analysis"}
                </p>
              </div>
            </div>

            {/* Performance Pillars Matrix */}
            <div className="space-y-2.5 mb-6">
              <div className="flex items-center justify-between px-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Pillar Scoring Breakdown</span>
                <span className="text-[10px] font-bold text-gray-500">Weight</span>
              </div>
              
              <PillarBar 
                label="Skills Match" 
                score={skillsScore} 
                weight={40}
                color="text-blue-600" 
                barColor="bg-blue-500" 
                bgColor="bg-blue-50/50" 
                borderColor="border-blue-100" 
                icon={Zap} 
              />
              <PillarBar 
                label="Experience Fit" 
                score={experienceScore} 
                weight={40}
                color="text-purple-600" 
                barColor="bg-purple-500" 
                bgColor="bg-purple-50/50" 
                borderColor="border-purple-100" 
                icon={Briefcase} 
              />
              <PillarBar 
                label="Education Level" 
                score={educationScore} 
                weight={20}
                color="text-amber-600" 
                barColor="bg-amber-500" 
                bgColor="bg-amber-50/50" 
                borderColor="border-amber-100" 
                icon={GraduationCap} 
              />
              {certificationsScore !== undefined && certificationsScore > 0 && (
                <PillarBar 
                  label="Certifications" 
                  score={certificationsScore} 
                  weight={10}
                  color="text-rose-600" 
                  barColor="bg-rose-500" 
                  bgColor="bg-rose-50/50" 
                  borderColor="border-rose-100" 
                  icon={Award} 
                />
              )}
            </div>

            {/* Candidate Contact Snapshot */}
            <div className="p-3.5 bg-white rounded-2xl border border-gray-100 shadow-2xs space-y-2.5 mb-6 text-xs text-gray-600">
              <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">Contact & Dossier</p>
              
              <div className="flex items-center gap-2.5">
                <MapPin size={14} className="text-gray-400 shrink-0" />
                <span className="font-medium truncate">{candidateLocation}</span>
              </div>

              <div className="flex items-center justify-between group">
                <div className="flex items-center gap-2.5 min-w-0">
                  <Mail size={14} className="text-gray-400 shrink-0" />
                  <span className="font-medium truncate text-gray-800">{candidateEmail}</span>
                </div>
                {candidateEmail && candidateEmail !== "Not provided" && (
                  <button 
                    onClick={() => handleCopy(candidateEmail, 'email')}
                    title="Copy Email"
                    className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700 transition-colors shrink-0 ml-1 cursor-pointer"
                  >
                    {copiedField === 'email' ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  </button>
                )}
              </div>

              <div className="flex items-center justify-between group">
                <div className="flex items-center gap-2.5 min-w-0">
                  <Phone size={14} className="text-gray-400 shrink-0" />
                  <span className="font-medium truncate text-gray-800">{candidatePhone}</span>
                </div>
                {candidatePhone && candidatePhone !== "Not provided" && (
                  <button 
                    onClick={() => handleCopy(candidatePhone, 'phone')}
                    title="Copy Phone"
                    className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-700 transition-colors shrink-0 ml-1 cursor-pointer"
                  >
                    {copiedField === 'phone' ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  </button>
                )}
              </div>

              {candidateCompany && candidateCompany !== "Not provided" && (
                <div className="flex items-center gap-2.5 pt-1 border-t border-gray-100">
                  <Building2 size={14} className="text-gray-400 shrink-0" />
                  <span className="font-medium truncate text-gray-600">Prev: {candidateCompany}</span>
                </div>
              )}
            </div>

            {/* Quick Actions in Sidebar */}
            <div className="space-y-2">
              {handleInterviewAction && (
                <button
                  type="button"
                  onClick={() => {
                    onClose();
                    handleInterviewAction(candidate);
                  }}
                  className="w-full py-2.5 px-4 bg-[#D60041] hover:bg-[#b50037] text-white rounded-xl text-xs font-bold transition-all shadow-xs hover:shadow-md hover:shadow-pink-500/20 active:scale-[0.98] flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Calendar size={14} />
                  <span>Schedule Interview</span>
                </button>
              )}

              {candidate.resumeUrl ? (
                <button 
                  type="button"
                  onClick={() => {
                    const fullUrl = getAssetUrl(candidate.resumeUrl);
                    const link = document.createElement('a');
                    link.href = fullUrl;
                    link.download = `${candidateName.replace(/\s+/g, '_')}_Resume`;
                    link.target = '_blank';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  className="w-full py-2.5 px-4 bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-700 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Download size={14} />
                  <span>Download Resume</span>
                </button>
              ) : (
                <button 
                  disabled
                  className="w-full py-2.5 px-4 bg-gray-100 text-gray-400 rounded-xl text-xs font-bold cursor-not-allowed flex items-center justify-center gap-2 border border-gray-200"
                >
                  <Download size={14} />
                  <span>Resume Unavailable</span>
                </button>
              )}
            </div>
          </aside>

          {/* ─── RIGHT CONTENT AREA ─── */}
          <main className="flex-1 flex flex-col min-w-0 bg-white">
            
            {/* Desktop Navigation Tabs */}
            <div className="hidden md:flex border-b border-gray-200 bg-gray-50/60 px-6 pt-3 gap-2 shrink-0">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`pb-3 px-3 text-xs font-bold flex items-center gap-2 transition-all relative cursor-pointer border-b-2 ${
                      isActive
                        ? 'border-[#D60041] text-[#D60041]'
                        : 'border-transparent text-gray-500 hover:text-gray-800 hover:border-gray-300'
                    }`}
                  >
                    <Icon size={14} />
                    <span>{tab.label}</span>
                    {tab.count !== undefined && (
                      <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                        isActive ? 'bg-pink-100 text-[#D60041]' : 'bg-gray-200 text-gray-600'
                      }`}>
                        {tab.count}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            {/* Scrollable Tab Content Container */}
            <div className="flex-1 p-4 sm:p-6 md:p-8 overflow-y-auto">

              {/* ══════════ TAB 1: EXECUTIVE OVERVIEW ══════════ */}
              {(activeTab === 'overview' || activeTab === 'all') && (
                <div className="space-y-6 animate-in fade-in duration-150">
                  
                  {/* Hero Match Verdict Banner */}
                  <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white p-5 rounded-2xl shadow-md border border-slate-700/50">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-emerald-500/20 rounded-lg border border-emerald-500/30">
                          <Target size={16} className="text-emerald-400" />
                        </div>
                        <div>
                          <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-400">ATS Verdict & Score Formulation</span>
                          <h3 className="text-base font-black text-white">
                            {fitTier.label} • {matchScore}% Overall Match
                          </h3>
                        </div>
                      </div>
                      <span className="px-3 py-1 bg-white/10 rounded-full text-xs font-semibold text-slate-300 border border-white/10">
                        {fitTier.tier}
                      </span>
                    </div>

                    {candidate.ai_powered ? (
                      <div className="space-y-2 pt-2 border-t border-white/10 text-xs">
                        <p className="font-mono text-slate-200">
                          Overall = Gemini Semantic Fit <span className="text-emerald-400 font-bold">80%</span> + ATS Rule Validation <span className="text-blue-400 font-bold">20%</span>
                        </p>
                        <p className="text-slate-400 text-[11px]">
                          Evaluates semantic relevance across required skills, verified experience tenure, academic qualification, and certifications.
                        </p>
                      </div>
                    ) : (
                      <div className="space-y-2 pt-2 border-t border-white/10 text-xs">
                        <p className="font-mono text-slate-200">
                          Overall = (Skills <span className="text-blue-400 font-bold">{skillsScore}%</span> × 0.40) + (Experience <span className="text-purple-400 font-bold">{experienceScore}%</span> × 0.40) + (Education <span className="text-amber-400 font-bold">{educationScore}%</span> × 0.20)
                        </p>
                        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
                          <span>Weighted Contribution:</span>
                          <span className="font-bold text-emerald-400">
                            {skillsContribution}% + {experienceContribution}% + {educationContribution}% = {calculatedContributionTotal}%
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Quick Highlight Metrics Strip */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <div className="bg-blue-50/60 border border-blue-100 p-3.5 rounded-2xl">
                      <div className="flex items-center justify-between text-blue-700 mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider">Skills Score</span>
                        <Zap size={14} />
                      </div>
                      <p className="text-xl font-black text-blue-900">{skillsScore}%</p>
                      <p className="text-[10px] text-blue-600 font-medium mt-0.5">
                        {matchedSkills.length} Matched • {missingSkills.length} Missing
                      </p>
                    </div>

                    <div className="bg-purple-50/60 border border-purple-100 p-3.5 rounded-2xl">
                      <div className="flex items-center justify-between text-purple-700 mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider">Experience</span>
                        <Briefcase size={14} />
                      </div>
                      <p className="text-xl font-black text-purple-900">{experienceScore}%</p>
                      <p className="text-[10px] text-purple-600 font-medium mt-0.5">
                        {formatMonths(candidate.total_experience_months) || `${candidate.work_experiences?.length || 0} Roles`}
                      </p>
                    </div>

                    <div className="bg-amber-50/60 border border-amber-100 p-3.5 rounded-2xl">
                      <div className="flex items-center justify-between text-amber-700 mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider">Education</span>
                        <GraduationCap size={14} />
                      </div>
                      <p className="text-xl font-black text-amber-900">{educationScore}%</p>
                      <p className="text-[10px] text-amber-600 font-medium mt-0.5 truncate">
                        {candidate.highest_educational_attainment || "Degree Assessment"}
                      </p>
                    </div>

                    <div className="bg-rose-50/60 border border-rose-100 p-3.5 rounded-2xl">
                      <div className="flex items-center justify-between text-rose-700 mb-1">
                        <span className="text-[10px] font-bold uppercase tracking-wider">Credentials</span>
                        <Award size={14} />
                      </div>
                      <p className="text-xl font-black text-rose-900">
                        {extractedCertifications.length}
                      </p>
                      <p className="text-[10px] text-rose-600 font-medium mt-0.5">
                        PRC / TESDA / Licenses
                      </p>
                    </div>
                  </div>

                  {/* AI Comprehensive Assessment Narrative */}
                  <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-5">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles size={16} className="text-[#D60041]" />
                      <h4 className="text-xs font-bold text-gray-900 uppercase tracking-wider">
                        Executive Assessment Summary
                      </h4>
                    </div>
                    <p className="text-xs sm:text-sm text-gray-700 font-medium leading-relaxed">
                      {candidate.ai_summary || fallbackAssessment || "The candidate's resume was evaluated against the job description requirements using automated criteria matching."}
                    </p>
                  </div>

                  {/* Side-by-Side: Key Strengths vs Gaps / Red Flags */}
                  <div className="grid md:grid-cols-2 gap-4">
                    {/* Strengths */}
                    <div className="bg-emerald-50/50 border border-emerald-200/80 rounded-2xl p-4 sm:p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <CheckCircle2 size={16} className="text-emerald-600" />
                        <h4 className="text-xs font-black text-emerald-900 uppercase tracking-wider">
                          Key Strengths & Qualifications
                        </h4>
                      </div>
                      <div className="space-y-2.5">
                        {(strengths.length > 0 ? strengths : [
                          candidate.skills_reason,
                          candidate.experienceScore >= 60 ? candidate.experience_reason : "",
                          candidate.educationScore >= 60 ? candidate.education_reason : ""
                        ].filter(Boolean).slice(0, 4)).map((item, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-gray-700 leading-relaxed bg-white/80 p-2.5 rounded-xl border border-emerald-100">
                            <CheckCircle size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Gaps / Risks */}
                    <div className="bg-rose-50/50 border border-rose-200/80 rounded-2xl p-4 sm:p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <AlertTriangle size={16} className="text-rose-600" />
                        <h4 className="text-xs font-black text-rose-900 uppercase tracking-wider">
                          Critical Gaps & Attention Areas
                        </h4>
                      </div>
                      <div className="space-y-2.5">
                        {(weaknesses.length > 0 ? weaknesses : [
                          missingSkills.length ? `Missing required skills: ${missingSkills.slice(0, 3).join(', ')}.` : "",
                          candidate.experience_gaps ? `Experience gap: ${candidate.experience_gaps}` : "",
                          candidate.educationScore < 70 ? candidate.education_reason : ""
                        ].filter(Boolean).slice(0, 4)).map((item, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs text-gray-700 leading-relaxed bg-white/80 p-2.5 rounded-xl border border-rose-100">
                            <AlertTriangle size={14} className="text-rose-500 shrink-0 mt-0.5" />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Core Candidate Expertise Chips */}
                  <div className="p-4 bg-gray-50/80 rounded-2xl border border-gray-100">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-2.5">
                      Extracted Candidate Competencies ({candidateSkills.length})
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {candidateSkills.slice(0, 15).map((skill, i) => (
                        <span key={i} className="px-2.5 py-1 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-700 shadow-2xs">
                          {skill}
                        </span>
                      ))}
                      {candidateSkills.length > 15 && (
                        <span className="px-2.5 py-1 bg-gray-100 text-gray-500 rounded-xl text-xs font-bold">
                          +{candidateSkills.length - 15} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* ══════════ TAB 2: SKILLS GAP ANALYSIS ══════════ */}
              {(activeTab === 'skills' || activeTab === 'all') && (
                <div className="space-y-6 animate-in fade-in duration-150 pt-2">
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-gray-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
                        <Zap size={16} />
                      </div>
                      <div>
                        <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">Skills Alignment & Gap Analysis</h3>
                        <p className="text-xs text-blue-600 font-semibold">{skillsScore}% Score — Contributes 40% to overall match</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg text-xs font-bold">
                        {matchedSkills.length} Matched
                      </span>
                      <span className="px-2.5 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded-lg text-xs font-bold">
                        {missingSkills.length} Missing
                      </span>
                    </div>
                  </div>

                  {/* Matched Skills Found */}
                  <div className="bg-emerald-50/40 border border-emerald-100 rounded-2xl p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle2 size={16} className="text-emerald-600" />
                      <h4 className="text-xs font-black text-emerald-900 uppercase tracking-wider">
                        Matched Skills Found in Resume ({matchedSkills.length})
                      </h4>
                    </div>
                    {matchedSkills.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {matchedSkills.map((skill, idx) => (
                          <SkillTag key={idx} skill={skill} type="matched" />
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-gray-500 italic bg-white/80 p-3 rounded-xl border border-emerald-100">
                        No direct match found between the extracted resume skills and the explicit JD requirements.
                      </p>
                    )}
                  </div>

                  {/* Missing / Gap Skills */}
                  <div className="bg-rose-50/40 border border-rose-100 rounded-2xl p-5">
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-2">
                        <XCircle size={16} className="text-rose-600" />
                        <h4 className="text-xs font-black text-rose-900 uppercase tracking-wider">
                          Missing Required Skills ({missingSkills.length})
                        </h4>
                      </div>
                      <span className="text-[10px] font-bold text-rose-600 bg-white/80 px-2 py-0.5 rounded-md border border-rose-200">
                        High Priority Gaps
                      </span>
                    </div>
                    {missingSkills.length > 0 ? (
                      <div>
                        <div className="flex flex-wrap gap-2 mb-3">
                          {missingSkills.map((skill, idx) => (
                            <SkillTag key={idx} skill={skill} type="missing" />
                          ))}
                        </div>
                        <p className="text-[11px] text-rose-700 font-medium">
                          These technical competencies were specified in the job posting but were not identified in the candidate's resume.
                        </p>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 bg-white/80 p-3 rounded-xl border border-emerald-200 text-xs text-emerald-700 font-semibold">
                        <CheckCircle size={14} className="text-emerald-500" />
                        <span>All mandatory skills identified in the job description are present in the candidate profile!</span>
                      </div>
                    )}
                  </div>

                  {/* Full Candidate Skills Inventory */}
                  <div className="bg-gray-50/80 border border-gray-100 rounded-2xl p-5">
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                        All Extracted Resume Skills ({candidateSkills.length})
                      </h4>
                      <span className="text-[10px] text-gray-400 font-semibold">Parsed by NLP engine</span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {candidateSkills.map((skill, idx) => {
                        const isMatched = matchedSkills.includes(skill);
                        return (
                          <span
                            key={idx}
                            className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-colors ${
                              isMatched
                                ? 'bg-emerald-50 text-emerald-800 border-emerald-200 font-bold'
                                : 'bg-white text-gray-700 border-gray-200'
                            }`}
                          >
                            {skill}
                          </span>
                        );
                      })}
                    </div>
                  </div>

                  {/* Skills Assessment Justification */}
                  <div className="p-4 bg-white rounded-xl border border-gray-200 text-xs text-gray-600">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">ATS Evaluation Notes</p>
                    <p className="font-medium leading-relaxed">
                      {candidate.skills_reason || "Skills match was evaluated based on keyword matching, synonyms, and contextual role relevance."}
                    </p>
                  </div>
                </div>
              )}

              {/* ══════════ TAB 3: WORK HISTORY & EXPERIENCE ══════════ */}
              {(activeTab === 'experience' || activeTab === 'all') && (
                <div className="space-y-6 animate-in fade-in duration-150 pt-2">
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-gray-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600">
                        <Briefcase size={16} />
                      </div>
                      <div>
                        <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">Work Experience & Role History</h3>
                        <p className="text-xs text-purple-600 font-semibold">{experienceScore}% Score — Contributes 40% to overall match</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {candidate.total_experience_months ? (
                        <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-purple-50 text-purple-700 rounded-full border border-purple-200 text-xs font-bold">
                          <Clock size={12} className="text-purple-600" />
                          {formatMonths(candidate.total_experience_months)} Total
                        </span>
                      ) : null}
                    </div>
                  </div>

                  {/* Experience Gap Warning Callout */}
                  {candidate.experience_gaps && (
                    <div className="bg-amber-50/70 border border-amber-200 rounded-2xl p-4 flex items-start gap-3">
                      <AlertTriangle size={16} className="text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-xs font-bold text-amber-900 uppercase tracking-wider">Experience Tenure Gap</h4>
                        <p className="text-xs text-amber-800 font-medium mt-0.5">{candidate.experience_gaps}</p>
                      </div>
                    </div>
                  )}

                  {/* Timeline of Extracted Work Experiences */}
                  {candidate.work_experiences && candidate.work_experiences.length > 0 ? (
                    <div className="space-y-4">
                      {candidate.work_experiences.map((exp: any, idx: number) => {
                        const badge = getEmpTypeBadge(exp.employment_type);
                        const durationFormatted = formatMonths(exp.duration_months);

                        return (
                          <div 
                            key={idx}
                            className="bg-white rounded-2xl border border-gray-200 p-5 shadow-2xs hover:border-purple-200 hover:shadow-xs transition-all relative pl-6"
                          >
                            {/* Visual Timeline Marker */}
                            <div className="absolute left-0 top-6 bottom-6 w-1 bg-purple-200 rounded-r"></div>

                            <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                              <div>
                                <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                                  <span>{exp.job_title}</span>
                                  {badge && (
                                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${badge.bg}`}>
                                      {badge.label}
                                    </span>
                                  )}
                                </h4>
                                {exp.raw_job_title && exp.raw_job_title.toLowerCase() !== exp.job_title.toLowerCase() && (
                                  <p className="text-xs text-gray-400 italic">
                                    Resume title: "{exp.raw_job_title}"
                                  </p>
                                )}
                              </div>

                              <div className="text-right">
                                <span className="text-xs font-bold text-gray-700">
                                  {[exp.start_date, exp.end_date || 'Present'].filter(Boolean).join(' – ')}
                                </span>
                                {durationFormatted && (
                                  <p className="text-[10px] font-semibold text-purple-600">
                                    {durationFormatted}
                                  </p>
                                )}
                              </div>
                            </div>

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

                            {/* Duties */}
                            {exp.responsibilities && exp.responsibilities.length > 0 && (
                              <div className="mt-3 pt-3 border-t border-gray-100">
                                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                                  Key Responsibilities & Achievements
                                </p>
                                <ul className="space-y-1.5">
                                  {exp.responsibilities.map((duty: string, dIdx: number) => (
                                    <li key={dIdx} className="text-xs text-gray-600 flex items-start gap-2 leading-relaxed">
                                      <span className="text-purple-500 mt-1 shrink-0">•</span>
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
                  ) : (
                    <div className="bg-gray-50/80 rounded-2xl border border-gray-100 p-5">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1.5">Extracted Relevance</p>
                      <p className="text-xs text-gray-700 font-medium leading-relaxed bg-white p-4 rounded-xl border border-gray-100">
                        {candidate.relevant_experience || candidate.relevance || "No structured work experience entries were detected in the resume."}
                      </p>
                    </div>
                  )}

                  {/* Justification */}
                  <div className="p-4 bg-white rounded-xl border border-gray-200 text-xs text-gray-600">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">Experience Evaluation Assessment</p>
                    <p className="font-medium leading-relaxed">
                      {candidate.experience_reason || "Experience was evaluated against required role seniority, duration, and industry keywords."}
                    </p>
                  </div>
                </div>
              )}

              {/* ══════════ TAB 4: EDUCATION & CREDENTIALS ══════════ */}
              {(activeTab === 'education' || activeTab === 'all') && (
                <div className="space-y-6 animate-in fade-in duration-150 pt-2">
                  <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-gray-100">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600">
                        <GraduationCap size={16} />
                      </div>
                      <div>
                        <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">Academic Background & Professional Licenses</h3>
                        <p className="text-xs text-amber-600 font-semibold">{educationScore}% Score — Contributes 20% to overall match</p>
                      </div>
                    </div>

                    {candidate.highest_educational_attainment && (
                      <span className="px-3 py-1 bg-amber-50 text-amber-800 border border-amber-200 rounded-full text-xs font-bold">
                        {candidate.highest_educational_attainment}
                      </span>
                    )}
                  </div>

                  {/* Qualification Comparison Card */}
                  <div className="grid sm:grid-cols-2 gap-3 bg-slate-50 border border-slate-200 p-4 rounded-2xl">
                    <div className="bg-white p-3.5 rounded-xl border border-gray-200">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Required by Job</span>
                      <p className="text-sm font-black text-gray-900 mt-1">
                        {candidate.required_degree || "Standard Requirements"}
                      </p>
                    </div>
                    <div className="bg-white p-3.5 rounded-xl border border-gray-200">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-gray-400">Candidate Attainment</span>
                      <p className="text-sm font-black text-gray-900 mt-1">
                        {candidate.candidate_degree || candidate.degree || "Declared Attainment"}
                      </p>
                    </div>
                  </div>

                  {/* Structured Education History */}
                  {candidate.education_entries && candidate.education_entries.length > 0 ? (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-gray-700 uppercase tracking-wider">
                        Educational Institutions & Degrees ({candidate.education_entries.length})
                      </h4>
                      {candidate.education_entries.map((edu: any, idx: number) => {
                        const levelBadge = getEduLevelBadge(edu.education_level);
                        const statusBadge = getEduStatusBadge(edu.status);
                        const displayDegree = edu.degree_or_course || edu.raw_degree_or_course || "Degree / Course";
                        const yearsDisplay = [edu.start_year, edu.end_year].filter(Boolean).join(' – ');

                        return (
                          <div 
                            key={idx}
                            className="bg-white p-4 sm:p-5 rounded-2xl border border-gray-200 shadow-2xs hover:border-amber-200 transition-all"
                          >
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
                                  <Calendar size={12} className="text-gray-400" />
                                  <span>{yearsDisplay}</span>
                                </div>
                              )}
                            </div>

                            <h5 className="text-sm font-bold text-gray-900">{displayDegree}</h5>
                            
                            {edu.major_or_specialization && (
                              <p className="text-xs text-amber-700 font-medium mt-0.5">
                                Major / Specialization: <span className="font-semibold">{edu.major_or_specialization}</span>
                              </p>
                            )}

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
                          </div>
                        );
                      })}
                    </div>
                  ) : null}

                  {/* Professional Licenses, PRC & Certifications */}
                  <div className="pt-2">
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-2">
                        <Award size={16} className="text-rose-600" />
                        <h4 className="text-xs font-black text-rose-900 uppercase tracking-wider">
                          Licenses, Eligibility & Government Credentials
                        </h4>
                      </div>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-50 text-rose-700 border border-rose-200">
                        {extractedCertifications.length} Credential{extractedCertifications.length === 1 ? '' : 's'}
                      </span>
                    </div>

                    {extractedCertifications.length > 0 ? (
                      <div className="space-y-3">
                        {extractedCertifications.map((c: any, idx: number) => {
                          const catBadge = getCertCategoryBadge(c.category);
                          return (
                            <div 
                              key={idx}
                              className="bg-white p-4 rounded-xl border border-gray-200 shadow-2xs hover:border-rose-200 transition-colors"
                            >
                              <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
                                <div className="flex items-center gap-1.5">
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
                                  <span className="text-xs font-semibold text-gray-500">{c.issue_date}</span>
                                )}
                              </div>

                              <h5 className="text-sm font-bold text-gray-900">{c.canonical_name || c}</h5>

                              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-600 mt-2">
                                {c.issuing_organization && (
                                  <div className="flex items-center gap-1 text-gray-600">
                                    <ShieldCheck size={13} className="text-rose-500" />
                                    <span>Issuer: <strong className="text-gray-800">{c.issuing_organization}</strong></span>
                                  </div>
                                )}
                                {c.credential_id_or_details && (
                                  <span className="text-rose-600 font-semibold">{c.credential_id_or_details}</span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="bg-gray-50 p-5 rounded-2xl border border-gray-200/80 text-center">
                        <Award size={24} className="text-gray-300 mx-auto mb-2" />
                        <p className="text-xs font-bold text-gray-700">No Government Licenses or Certifications Detected</p>
                        <p className="text-[11px] text-gray-400 mt-0.5">Resume does not list PRC licenses, TESDA NC certificates, or safety accreditations.</p>
                      </div>
                    )}
                  </div>

                  {/* Justification */}
                  <div className="p-4 bg-white rounded-xl border border-gray-200 text-xs text-gray-600">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-1">Education Assessment Rationale</p>
                    <p className="font-medium leading-relaxed">
                      {candidate.education_reason || "Academic attainment was evaluated against the specified degree requirement and educational discipline."}
                    </p>
                  </div>
                </div>
              )}

              {/* ══════════ TAB 5: RECOMMENDATIONS ══════════ */}
              {(activeTab === 'recommendations' || activeTab === 'all') && (
                <div className="space-y-6 animate-in fade-in duration-150 pt-2">
                  <div className="flex items-center gap-2.5 pb-2 border-b border-gray-100">
                    <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600">
                      <Lightbulb size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-black text-gray-900 uppercase tracking-tight">AI Screening & Interview Recommendations</h3>
                      <p className="text-xs text-emerald-600 font-semibold">Actionable insights to probe qualifications during interview</p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {recommendations.length > 0 ? (
                      recommendations.map((rec, i) => (
                        <div key={i} className="flex items-start gap-3 bg-emerald-50/40 p-4 rounded-2xl border border-emerald-100">
                          <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-emerald-600 text-white text-xs font-black shrink-0 mt-0.5">
                            {i + 1}
                          </div>
                          <div>
                            <p className="text-xs sm:text-sm text-gray-800 font-medium leading-relaxed">
                              {rec}
                            </p>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="space-y-3">
                        <div className="flex items-start gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-200">
                          <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-[#D60041] text-white text-xs font-black shrink-0 mt-0.5">
                            1
                          </div>
                          <p className="text-xs text-gray-700 font-medium leading-relaxed">
                            Cross-examine experience claims and verify proficiency in missing skills during technical interview questioning.
                          </p>
                        </div>
                        <div className="flex items-start gap-3 bg-slate-50 p-4 rounded-2xl border border-slate-200">
                          <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-[#D60041] text-white text-xs font-black shrink-0 mt-0.5">
                            2
                          </div>
                          <p className="text-xs text-gray-700 font-medium leading-relaxed">
                            Verify original diplomas and certificates if candidate is invited to the final recruitment phase.
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

            </div>

            {/* ═══════ FOOTER ═══════ */}
            <footer className="p-3.5 sm:p-5 border-t border-gray-200 bg-slate-50/80 flex flex-wrap sm:flex-nowrap justify-between items-center gap-3 shrink-0">
              <div className="text-[11px] text-gray-400 font-medium">
                Application #{candidate.id} • Evaluated by Mariwasa ATS
              </div>

              <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
                <button 
                  type="button"
                  onClick={onClose} 
                  className="px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-xl text-xs font-bold hover:bg-gray-100 transition-all cursor-pointer"
                >
                  Close
                </button>

                {handleInterviewAction && (
                  <button
                    type="button"
                    onClick={() => {
                      onClose();
                      handleInterviewAction(candidate);
                    }}
                    className="px-4 py-2 bg-[#D60041] hover:bg-[#b50037] text-white rounded-xl text-xs font-bold transition-all shadow-xs hover:shadow-md hover:shadow-pink-500/20 active:scale-[0.98] inline-flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Calendar size={14} />
                    <span>Schedule Interview</span>
                  </button>
                )}
              </div>
            </footer>
          </main>
        </div>
      </div>
    </div>
  );
};

export default ViewCandidateDetailsModal;
