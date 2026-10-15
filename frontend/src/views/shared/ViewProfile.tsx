import React, { useState, useEffect } from 'react';
import profileService from '../../services/profileService';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from '@/utils/navigation';
import {
  User,
  Mail,
  MapPin,
  Briefcase,
  ShieldCheck,
  Edit3,
  ArrowLeft,
  Calendar,
  Zap,
  CheckCircle2,
  TrendingUp,
  Globe,
  Award,
  Link as LinkIcon,
  Clock,
  FileText,
  Users,
  Building2,
  Phone,
  Sparkles,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useDispatch, useSelector } from 'react-redux';
import { updateProfileImage } from '../../redux/slices/authSlice';
import { RootState } from '../../redux/store';

interface UserProfileData {
  id?: number;
  fullname?: string;
  email?: string;
  current_job_title?: string;
  position?: string;
  location?: string;
  bio?: string;
  phone?: string;
  profile_image_url?: string;
  resume_url?: string;
  skills?: string[];
  highest_degree?: string;
  university?: string;
  experience_years?: number;
  company_name?: string;
  current_company?: string;
  department?: string;
  managed_region?: string;
  applications_count?: number | string;
  interviews_count?: number | string;
  offers_count?: number | string;
  screened_count?: number | string;
  job_posts_count?: number | string;
  reports_count?: number | string;
  users_count?: number | string;
  jobs_count?: number | string;
  audits_count?: number | string;
  governance_scope?: string;
  resumes_count?: number | string;
  active_hr_count?: number | string;
  active_candidates_count?: number | string;
}

const ViewProfile: React.FC = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfileData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const userEmail = localStorage.getItem('saved_email') || 'user@system.com';
  const userRole = (localStorage.getItem('role') || 'CANDIDATE').toUpperCase();
  const userId = localStorage.getItem('user_id');
  const dispatch = useDispatch();
  const { profileImageUrl } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!userId) {
        setLoading(false);
        return;
      }
      try {
        const response = await profileService.getProfile(userRole, userId);
        const data = response.data;
        if (data.id === parseInt(userId) && data.profile_image_url) {
          dispatch(updateProfileImage(data.profile_image_url));
        }
        setProfile(data);
      } catch (err) {
        console.error("Failed to fetch profile:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [userRole, userId, dispatch]);

  const isCandidate = userRole === 'CANDIDATE';
  const isHR = userRole === 'HR';
  const isAdmin = userRole === 'ADMIN';

  const settingsPath = isAdmin ? '/admin/settings' : isHR ? '/hr/settings' : '/candidate/settings';

  const profileData = {
    name: profile?.fullname || (isCandidate ? "Candidate User" : isHR ? "HR Recruiter" : "System Administrator"),
    title: profile?.position || profile?.current_job_title || (isCandidate ? "Job Seeker" : isHR ? "Talent Acquisition Officer" : "Lead Platform Administrator"),
    department: profile?.department || (isAdmin ? "IT Platform & Security Operations" : isHR ? "Human Resources" : ""),
    location: profile?.location || (isAdmin ? "Sto. Tomas Plant & Enterprise HQ, Batangas" : "Location not set"),
    phone: profile?.phone || "",
    bio: profile?.bio || (isCandidate
      ? "Welcome to your Mariwasa candidate profile. Add your professional summary and core skills in settings to maximize your job match score."
      : isHR
      ? "HR Recruitment Specialist managing talent pipelines, automated resume screening, and candidate interview schedules at Mariwasa."
      : "Enterprise System Administrator supervising platform access control, AI resume screening algorithm calibration, and recruitment pipeline compliance across Mariwasa Siam Ceramics."),
    since: isCandidate ? "Joined Career Portal" : isAdmin ? "System Governance" : "Active Member",
    stats: isCandidate ? [
      { label: "Applications", value: profile?.applications_count ?? 0, icon: <FileText size={18} /> },
      { label: "Interviews", value: profile?.interviews_count ?? 0, icon: <Calendar size={18} /> },
      { label: "Job Offers", value: profile?.offers_count ?? 0, icon: <Award size={18} /> }
    ] : isHR ? [
      { label: "Screened", value: profile?.screened_count ?? 0, icon: <Users size={18} /> },
      { label: "Job Openings", value: profile?.job_posts_count ?? 0, icon: <Briefcase size={18} /> },
      { label: "Interviews", value: profile?.reports_count ?? 0, icon: <Calendar size={18} /> }
    ] : [
      { label: "Directory Users", value: profile?.users_count ?? 0, icon: <Users size={18} /> },
      { label: "Job Requisitions", value: profile?.jobs_count ?? 0, icon: <Briefcase size={18} /> },
      { label: "Resumes Indexed", value: profile?.resumes_count ?? 0, icon: <FileText size={18} /> }
    ]
  };

  // Highlights connected to real features
  const highlights = isCandidate ? [
    {
      label: "Experience",
      value: profile?.experience_years !== undefined ? `${profile.experience_years} Years Exp` : "Entry Level",
      icon: <Clock size={16} />
    },
    {
      label: "Education",
      value: profile?.highest_degree || "Degree Pending",
      icon: <Award size={16} />
    },
    {
      label: "Organization",
      value: profile?.current_company || "Open to Opportunities",
      icon: <Briefcase size={16} />
    }
  ] : isHR ? [
    {
      label: "Department",
      value: profile?.department || "Talent Acquisition",
      icon: <Briefcase size={16} />
    },
    {
      label: "Organization",
      value: profile?.company_name || "Mariwasa Siam Ceramics",
      icon: <Building2 size={16} />
    },
    {
      label: "Portal Role",
      value: profile?.position || "Recruitment Lead",
      icon: <ShieldCheck size={16} />
    }
  ] : [
    {
      label: "Operational HQ",
      value: profile?.managed_region || "Main Plant & Enterprise HQ",
      icon: <Building2 size={16} />
    },
    {
      label: "Administrative Dept",
      value: profile?.department || "IT & Platform Operations",
      icon: <Briefcase size={16} />
    },
    {
      label: "Governance Scope",
      value: profile?.governance_scope || "Full Platform Governance",
      icon: <ShieldCheck size={16} />
    }
  ];

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - {userRole.charAt(0) + userRole.slice(1).toLowerCase()} Profile</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-grow min-w-0 w-full overflow-x-hidden">

          {/* Hero Banner Header */}
          <div className="relative h-40 sm:h-52 md:h-64 lg:h-72 w-full bg-slate-900 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-[#D10043]/45 via-slate-900/90 to-slate-950 opacity-90" />
            <div className="absolute inset-0 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px] opacity-10" />

            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 md:px-8 h-full relative flex items-start justify-between pt-4 sm:pt-6 md:pt-8">
              <button
                onClick={() => navigate(-1)}
                className="inline-flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-xl bg-black/40 hover:bg-black/60 backdrop-blur-md border border-white/15 text-white/90 hover:text-white text-[11px] sm:text-xs font-black uppercase tracking-wider transition-all shadow-md group active:scale-95 cursor-pointer"
              >
                <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform" />
                <span>Back</span>
              </button>

              <div className="inline-flex items-center gap-1.5 px-3 py-1 sm:px-3.5 sm:py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/15 text-white text-[10px] sm:text-xs font-black uppercase tracking-widest shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-[#D10043] animate-pulse" />
                <span>{userRole} Profile</span>
              </div>
            </div>
          </div>

          {/* Profile Body Container */}
          <div className="max-w-[1400px] mx-auto px-3.5 sm:px-6 md:px-8 -mt-14 sm:-mt-20 md:-mt-24 lg:-mt-28 relative z-10 pb-12 sm:pb-20">
            <div className="flex flex-col lg:flex-row gap-5 sm:gap-6 lg:gap-8">

              {/* Left Column: Avatar, Profile Details & Contact Info */}
              <div className="w-full lg:w-[360px] xl:w-[390px] shrink-0">
                <div className="bg-white border border-slate-100 rounded-2xl sm:rounded-3xl lg:rounded-[36px] p-5 sm:p-7 lg:p-8 shadow-xl shadow-slate-200/50 text-center animate-in fade-in slide-in-from-bottom-6 duration-700">

                  {/* Avatar */}
                  <div className="relative inline-block mb-3.5 sm:mb-6">
                    <div className="w-24 h-24 sm:w-32 sm:h-32 md:w-36 md:h-36 rounded-2xl sm:rounded-3xl md:rounded-[32px] bg-slate-50 border-4 border-white shadow-xl overflow-hidden flex items-center justify-center text-slate-300 mx-auto">
                      {profileImageUrl ? (
                        <img 
                          src={profileImageUrl} 
                          alt="Profile" 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            (e.target as HTMLImageElement).style.display = 'none';
                            const next = (e.target as HTMLImageElement).nextSibling as HTMLElement;
                            if (next) next.style.display = 'flex';
                          }}
                        />
                      ) : null}
                      <div className={`fallback-icon items-center justify-center w-full h-full ${profileImageUrl ? 'hidden' : 'flex'}`}>
                        {isCandidate ? <User size={44} className="sm:w-16 sm:h-16" /> : <ShieldCheck size={44} className="sm:w-16 sm:h-16" />}
                      </div>
                    </div>
                    <div className="absolute -bottom-1 -right-1 sm:-bottom-1.5 sm:-right-1.5 w-7 h-7 sm:w-8 sm:h-8 bg-green-500 rounded-lg sm:rounded-xl border-2 sm:border-3 border-white flex items-center justify-center shadow-md">
                      <CheckCircle2 size={14} className="text-white" strokeWidth={3} />
                    </div>
                  </div>

                  {/* Name and Title */}
                  <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight mb-1 break-words">
                    {profileData.name}
                  </h2>
                  <p className="text-[#D10043] font-black text-xs uppercase tracking-wider sm:tracking-widest mb-3 sm:mb-5 break-words">
                    {profileData.title}
                  </p>

                  {/* Location Badge */}
                  <div className="flex items-center justify-center gap-1.5 mb-4 sm:mb-6 bg-slate-50 py-1.5 px-3 rounded-xl border border-slate-100 w-fit max-w-full mx-auto">
                    <MapPin size={13} className="text-slate-400 shrink-0" />
                    <span className="text-[10px] sm:text-[11px] font-black text-slate-500 uppercase tracking-wider truncate">
                      {profileData.location}
                    </span>
                  </div>

                  {/* Edit Profile CTA Button */}
                  <button
                    onClick={() => navigate(settingsPath)}
                    className="w-full py-3 sm:py-3.5 bg-slate-900 text-white rounded-xl sm:rounded-2xl font-black uppercase tracking-wider text-xs hover:bg-[#D10043] transition-all shadow-md active:scale-[0.98] flex items-center justify-center gap-2 mb-4 min-h-[44px] cursor-pointer"
                  >
                    <Edit3 size={15} /> <span>Edit Profile & Credentials</span>
                  </button>

                  {/* Quick Meta Details */}
                  <div className="pt-4 sm:pt-6 mt-4 sm:mt-6 border-t border-slate-100 space-y-2.5 sm:space-y-3">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                      <span>Role Scope</span>
                      <span className="text-slate-900 font-extrabold">{isAdmin ? "Full System Governance" : userRole}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                      <span>Status</span>
                      <span className="text-green-600 font-extrabold flex items-center gap-1">
                        <CheckCircle2 size={13} className="text-green-500" />
                        {isAdmin ? "Root Administrator" : "Verified Account"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider">
                      <span>Portal Type</span>
                      <span className="text-slate-900 font-extrabold">{profileData.since}</span>
                    </div>
                  </div>
                </div>

                {/* Contact Information Card */}
                <div className="mt-4 sm:mt-6 bg-white border border-slate-100 rounded-2xl sm:rounded-3xl p-5 sm:p-7 shadow-lg shadow-slate-200/40 animate-in fade-in slide-in-from-bottom-6 duration-700 delay-100">
                  <h3 className="text-xs sm:text-sm font-black text-slate-900 tracking-wider uppercase mb-4 sm:mb-6 flex items-center gap-2">
                    <Mail size={16} className="text-[#D10043]" />
                    <span>Contact Details</span>
                  </h3>
                  <div className="space-y-3.5 sm:space-y-5">
                    {/* Email */}
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 bg-slate-50 rounded-xl flex items-center justify-center text-[#D10043] shrink-0 border border-slate-100 mt-0.5">
                        <Mail size={15} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-0.5">Email Address</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-900 break-all" title={userEmail}>
                          {userEmail}
                        </p>
                      </div>
                    </div>

                    {/* Phone */}
                    {profileData.phone && (
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 bg-slate-50 rounded-xl flex items-center justify-center text-[#D10043] shrink-0 border border-slate-100 mt-0.5">
                          <Phone size={15} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-0.5">Phone Number</p>
                          <p className="text-xs sm:text-sm font-bold text-slate-900 break-words">
                            {profileData.phone}
                          </p>
                        </div>
                      </div>
                    )}

                    {/* Timezone */}
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 bg-slate-50 rounded-xl flex items-center justify-center text-[#D10043] shrink-0 border border-slate-100 mt-0.5">
                        <Globe size={15} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-wider mb-0.5">System Timezone</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-900">GMT+8 (Philippine Standard Time)</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Key Metrics, Professional Bio & Application Feature Hub */}
              <div className="flex-grow space-y-4 sm:space-y-6 lg:space-y-8 min-w-0 w-full">

                {/* Role Key Metrics */}
                <div className="grid grid-cols-3 gap-2 sm:gap-4 lg:gap-5 animate-in fade-in slide-in-from-right-6 duration-700">
                  {profileData.stats.map((stat, idx) => (
                    <div
                      key={idx}
                      className="bg-white border border-slate-100 rounded-2xl sm:rounded-3xl p-3 sm:p-5 shadow-sm hover:shadow-md transition-all flex flex-col sm:flex-row items-center sm:items-start text-center sm:text-left gap-1.5 sm:gap-3.5"
                    >
                      <div className="p-2 sm:p-2.5 rounded-xl bg-pink-50 text-[#D10043] shrink-0">
                        {stat.icon}
                      </div>
                      <div className="min-w-0 flex-1 w-full">
                        <p className="text-lg sm:text-2xl font-black text-slate-900 leading-tight">
                          {stat.value}
                        </p>
                        <p className="text-[9px] sm:text-xs font-bold text-slate-400 uppercase tracking-wider truncate mt-0.5">
                          {stat.label}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Professional Bio & Profile Highlights Card */}
                <div className="bg-white border border-slate-100 rounded-2xl sm:rounded-3xl lg:rounded-[36px] p-5 sm:p-7 lg:p-9 shadow-lg shadow-slate-200/40 animate-in fade-in slide-in-from-right-6 duration-700">
                  <div className="flex items-center gap-2.5 mb-4 sm:mb-6">
                    <div className="p-2 sm:p-2.5 bg-pink-50 rounded-xl text-[#D10043] shrink-0">
                      <Zap size={18} />
                    </div>
                    <div>
                      <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight">
                        {isCandidate ? 'Candidate Professional Overview' : isHR ? 'Talent Operations Focus' : 'System Governance & Platform Oversight'}
                      </h3>
                      <p className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider">
                        {isAdmin ? 'Administrative parameters, module authority & operational objectives' : 'Personal profile summary & credentials'}
                      </p>
                    </div>
                  </div>

                  <p className="text-slate-600 text-xs sm:text-sm lg:text-base leading-relaxed font-medium">
                    {profileData.bio}
                  </p>

                  {/* Role Specific Dynamic Highlights */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 sm:gap-3.5 mt-5 sm:mt-7">
                    {highlights.map((item, i) => (
                      <div key={i} className="bg-slate-50/80 p-3 sm:p-4 rounded-xl sm:rounded-2xl border border-slate-100 text-left">
                        <div className="text-[#D10043] mb-1.5">{item.icon}</div>
                        <p className="text-[9px] sm:text-[10px] font-black text-slate-400 uppercase tracking-wider truncate mb-0.5">{item.label}</p>
                        <p className="text-xs sm:text-sm font-black text-slate-900 truncate">{item.value}</p>
                      </div>
                    ))}
                  </div>

                  {/* Administrator Operational Pillars */}
                  {isAdmin && (
                    <div className="mt-5 sm:mt-7 pt-5 sm:pt-7 border-t border-slate-100">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-[10px] sm:text-xs font-black text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                          <ShieldCheck size={14} className="text-[#D10043]" />
                          System Governance Capabilities
                        </span>
                        <button
                          onClick={() => navigate(settingsPath)}
                          className="text-[10px] font-black text-[#D10043] hover:underline cursor-pointer"
                        >
                          + Update Authority
                        </button>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex items-start gap-2.5">
                          <div className="p-1.5 rounded-lg bg-pink-100/50 text-[#D10043] shrink-0 mt-0.5">
                            <Users size={14} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-black text-slate-800">RBAC User Directory</p>
                            <p className="text-[11px] text-slate-500 font-medium">HR and Candidate account privileges and status regulation</p>
                          </div>
                        </div>

                        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex items-start gap-2.5">
                          <div className="p-1.5 rounded-lg bg-indigo-100/50 text-indigo-600 shrink-0 mt-0.5">
                            <Zap size={14} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-black text-slate-800">AI Scoring Calibration</p>
                            <p className="text-[11px] text-slate-500 font-medium">Matching weights, qualification thresholds & parsing rules</p>
                          </div>
                        </div>

                        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex items-start gap-2.5">
                          <div className="p-1.5 rounded-lg bg-emerald-100/50 text-emerald-600 shrink-0 mt-0.5">
                            <Briefcase size={14} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-black text-slate-800">Job Requisitions</p>
                            <p className="text-[11px] text-slate-500 font-medium">Plant vacancy lifecycle, departmental requirements & salaries</p>
                          </div>
                        </div>

                        <div className="p-3 bg-slate-50 border border-slate-100 rounded-xl flex items-start gap-2.5">
                          <div className="p-1.5 rounded-lg bg-amber-100/50 text-amber-600 shrink-0 mt-0.5">
                            <TrendingUp size={14} />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-black text-slate-800">Security Audit Logs</p>
                            <p className="text-[11px] text-slate-500 font-medium">Real-time audit tracking, system events & worker tasks</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Application Feature Hub - Meaningful, functional connection to Mariwasa features */}
                <div className="bg-slate-900 rounded-2xl sm:rounded-3xl lg:rounded-[36px] p-5 sm:p-7 lg:p-9 text-white relative overflow-hidden group animate-in fade-in slide-in-from-right-6 duration-700 delay-100">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-[#D10043]/15 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none" />

                  <div className="relative z-10">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between mb-4 sm:mb-6 gap-2">
                      <div>
                        <h3 className="text-base sm:text-lg font-black tracking-tight">
                          {isCandidate ? "Candidate Portal Features" : isHR ? "Talent Operations Hub" : "Platform Governance & Security"}
                        </h3>
                        <p className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider mt-0.5">
                          Quick access to system workflows and modules
                        </p>
                      </div>
                      <Award className="text-[#D10043] shrink-0 hidden sm:block" size={24} />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">

                      {/* Candidate Feature 1: AI Resume Matching */}
                      {isCandidate && (
                        <>
                          <div 
                            onClick={() => navigate('/candidate/smart-matches')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <FileText size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                AI Resume Matching
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                {profile?.resume_url 
                                  ? "Resume file indexed. View match compatibility across all open requisitions."
                                  : "Upload your resume PDF to automatically extract qualifications and match jobs."}
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              Explore Smart Matches <ChevronRight size={11} />
                            </span>
                          </div>

                          <div 
                            onClick={() => navigate('/candidate/applications')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <Briefcase size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                Application Tracking
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Monitor your active submissions, screening scores, and interview schedules in real-time.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              View Submissions <ChevronRight size={11} />
                            </span>
                          </div>
                        </>
                      )}

                      {/* HR Features */}
                      {isHR && (
                        <>
                          <div 
                            onClick={() => navigate('/hr/dashboard')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <Users size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                Screening Portal
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Review applicants, analyze candidate skills breakdowns, and compare candidates side-by-side.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              Open Screening <ChevronRight size={11} />
                            </span>
                          </div>

                          <div 
                            onClick={() => navigate('/hr/scheduling')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <Calendar size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                Interview Schedules & Calendar
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Schedule candidate rounds, assign interviewers, and sync meetings directly with Google Calendar.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              Manage Schedules <ChevronRight size={11} />
                            </span>
                          </div>
                        </>
                      )}

                      {/* Admin Features */}
                      {isAdmin && (
                        <>
                          <div 
                            onClick={() => navigate('/admin/users')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <Users size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                User Management Directory
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Oversee candidates and HR personnel, manage active statuses, and configure access permissions.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              Manage Users <ChevronRight size={11} />
                            </span>
                          </div>

                          <div 
                            onClick={() => navigate('/admin/system-config')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <Zap size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                AI Screening Calibration
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Fine-tune AI resume scoring weights, matching thresholds, and automated evaluation criteria.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              Tune System Config <ChevronRight size={11} />
                            </span>
                          </div>

                          <div 
                            onClick={() => navigate('/admin/jobmanagement')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <Briefcase size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                Job Requisitions
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Create, configure, publish, and oversee open job descriptions across plant departments.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              Manage Openings <ChevronRight size={11} />
                            </span>
                          </div>

                          <div 
                            onClick={() => navigate('/admin/dashboard')}
                            className="p-4 sm:p-5 bg-white/5 border border-white/10 rounded-xl sm:rounded-2xl hover:bg-white/10 transition-all cursor-pointer group/item flex flex-col justify-between"
                          >
                            <div>
                              <div className="flex justify-between items-start mb-2.5">
                                <div className="w-8 h-8 sm:w-9 sm:h-9 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                                  <TrendingUp size={16} />
                                </div>
                                <ChevronRight size={15} className="text-white/30 group-hover/item:text-white transition-colors group-hover/item:translate-x-0.5" />
                              </div>
                              <h4 className="font-black text-xs sm:text-sm uppercase tracking-wider mb-1 text-white">
                                Platform Analytics & Logs
                              </h4>
                              <p className="text-[11px] sm:text-xs text-white/60 font-medium leading-relaxed">
                                Monitor system metrics, application submission rates, database activity, and audit logs.
                              </p>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] mt-3 inline-flex items-center gap-1">
                              View Admin Dashboard <ChevronRight size={11} />
                            </span>
                          </div>
                        </>
                      )}

                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default ViewProfile;
