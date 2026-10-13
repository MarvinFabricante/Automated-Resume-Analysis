import React, { useState, useMemo } from 'react';
import { useLocation, useNavigate, useParams, useSearchParams } from '@/utils/navigation';
import { Helmet } from 'react-helmet-async';
import { 
  ArrowLeft, 
  Briefcase, 
  MapPin, 
  Calendar, 
  CheckCircle2, 
  FileText, 
  Download, 
  ExternalLink, 
  MessageSquare, 
  AlertCircle, 
  ChevronRight, 
  Sparkles, 
  ShieldCheck, 
  Building2, 
  Clock, 
  XCircle, 
  Mail,
  Video,
  Check,
  X,
  Layers,
  Search,
  Laptop,
  HelpCircle,
  Award
} from 'lucide-react';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import { useGetCandidateApplicationsQuery, useGetApplicationInterviewsQuery } from '../../redux/api/apiSlice';
import { getAssetUrl } from '../../services/api';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

interface TimelineStep {
  label: string;
  date: string;
  description: string;
  status: 'completed' | 'current' | 'upcoming' | 'failed';
  interviewInfo?: any;
  matchScore?: number;
  matchedSkills?: string[];
}

const ApplicationTracking: React.FC = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const params = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();

  const [selectedId, setSelectedId] = useState<number | string | null>(null);
  const [isEnvModalOpen, setIsEnvModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);

  const { user } = useSelector((state: RootState) => state.auth);
  const email = typeof user === 'string' ? user : (user as any)?.email;

  // Real-time polling of candidate applications
  const { data: applications = [], isLoading: isLoadingApps } = useGetCandidateApplicationsQuery(
    email || '',
    {
      skip: !email,
      pollingInterval: 5000,
    }
  );

  // Determine active application ID priority:
  // 1. User clicked tab `selectedId`
  // 2. URL route param `params.id`
  // 3. Query string `?id=...`
  // 4. Navigation state `state.application.id`
  // 5. First application in candidate list
  const activeApplication = useMemo(() => {
    if (!applications || applications.length === 0) {
      return state?.application || null;
    }

    if (selectedId) {
      const found = applications.find((a: any) => String(a.id) === String(selectedId));
      if (found) return found;
    }

    if (params?.id) {
      const found = applications.find((a: any) => String(a.id) === String(params.id));
      if (found) return found;
    }

    const queryId = searchParams.get('id');
    if (queryId) {
      const found = applications.find((a: any) => String(a.id) === String(queryId));
      if (found) return found;
    }

    if (state?.application?.id) {
      const found = applications.find((a: any) => String(a.id) === String(state.application.id));
      if (found) return found;
      return state.application;
    }

    return applications[0];
  }, [applications, selectedId, params?.id, searchParams, state?.application]);

  // Fetch interviews for active application
  const { data: interviews = [] } = useGetApplicationInterviewsQuery(
    activeApplication?.id,
    {
      skip: !activeApplication?.id,
      pollingInterval: 10000,
    }
  );

  const latestInterview = interviews.length > 0 ? interviews[interviews.length - 1] : null;

  // Real resume link resolution
  const resumeUrl = activeApplication?.originalData?.resume_url || activeApplication?.resumeUrl;
  const resumeFilename = useMemo(() => {
    if (resumeUrl) {
      const clean = resumeUrl.split('?')[0];
      const name = clean.split('/').pop()?.split('\\').pop();
      if (name) return name;
    }
    return activeApplication ? `${(activeApplication.role || 'Position').replace(/\s+/g, '_')}_Resume.pdf` : 'Candidate_Resume.pdf';
  }, [resumeUrl, activeApplication]);

  const handleDownloadResume = () => {
    if (resumeUrl) {
      const fullUrl = getAssetUrl(resumeUrl);
      window.open(fullUrl, '_blank');
    } else {
      navigate('/candidate/settings');
    }
  };

  // If loading and no cached application yet, show clean skeleton
  if (isLoadingApps && !activeApplication) {
    return (
      <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
        <Helmet>
          <title>Mariwasa - Application Pipeline</title>
        </Helmet>
        <Header />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 py-8 sm:py-12 w-full flex-grow">
            <div className="animate-pulse space-y-8">
              <div className="h-6 w-32 bg-slate-200 rounded-lg" />
              <div className="h-44 bg-white rounded-3xl border border-slate-100 p-8" />
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                <div className="lg:col-span-2 h-96 bg-white rounded-3xl border border-slate-100" />
                <div className="h-96 bg-white rounded-3xl border border-slate-100" />
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  // If candidate has no applications at all, show helpful pipeline introduction
  if (!activeApplication) {
    return (
      <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
        <Helmet>
          <title>Mariwasa - Application Pipeline</title>
        </Helmet>
        <Header />
        <div className="flex flex-1">
          <Sidebar />
          <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 py-8 sm:py-12 w-full flex-grow">
            <button
              onClick={() => navigate('/candidate/dashboard')}
              className="flex items-center text-xs font-black text-slate-400 uppercase tracking-widest hover:text-[#D10043] transition-colors mb-6 group cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
              Back to Dashboard
            </button>

            <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-12 shadow-sm text-center max-w-3xl mx-auto space-y-6">
              <div className="w-16 h-16 bg-rose-50 text-[#D10043] rounded-2xl flex items-center justify-center mx-auto border border-rose-100 shadow-xs">
                <Briefcase size={32} />
              </div>

              <div className="space-y-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-wider bg-rose-50 text-[#D10043] border border-rose-100">
                  <Sparkles size={13} />
                  Candidate Recruitment Pipeline
                </span>
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  No Active Applications Found
                </h1>
                <p className="text-sm text-slate-500 font-medium leading-relaxed max-w-lg mx-auto">
                  You have not submitted an application yet. When you apply for a position at Mariwasa Siam Ceramics, you can monitor every stage of your evaluation in real-time here.
                </p>
              </div>

              {/* 5 Pipeline Stages Preview */}
              <div className="pt-4 border-t border-slate-100 text-left">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-4 text-center">
                  How Mariwasa's Recruitment Pipeline Works
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                  {[
                    { step: 1, title: 'Submission', desc: 'Resume parsing & ATS profile matching' },
                    { step: 2, title: 'Screening', desc: 'HR recruiter qualification review' },
                    { step: 3, title: 'Technical', desc: 'Competency & panel interview session' },
                    { step: 4, title: 'Executive', desc: 'Department head & cultural fit review' },
                    { step: 5, title: 'Decision', desc: 'Official offer letter & onboarding' },
                  ].map((s) => (
                    <div key={s.step} className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60 flex flex-col justify-between">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="w-5 h-5 rounded-full bg-[#D10043] text-white text-[10px] font-black flex items-center justify-center">
                          {s.step}
                        </span>
                        <span className="text-[9px] font-mono font-bold text-slate-400">STAGE</span>
                      </div>
                      <p className="text-xs font-black text-slate-900">{s.title}</p>
                      <p className="text-[10px] text-slate-500 font-medium mt-0.5 leading-snug">{s.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => navigate('/candidate/findjobs')}
                  className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm shadow-[#D10043]/20 active:scale-95 cursor-pointer"
                >
                  <Search size={15} />
                  <span>Browse Open Opportunities</span>
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/candidate/dashboard')}
                  className="w-full sm:w-auto px-5 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs uppercase tracking-wider transition-colors cursor-pointer"
                >
                  Return to Dashboard
                </button>
              </div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  const jobDetails = {
    role: activeApplication.role || activeApplication.originalData?.job_title || "Position",
    company: activeApplication.company || "Mariwasa Siam Ceramics",
    location: activeApplication.originalData?.location || "Sto. Tomas, Batangas",
    appliedDate: activeApplication.appliedDate || new Date().toLocaleDateString(),
    status: activeApplication.status || "Pending",
    statusColor: activeApplication.statusColor || "text-slate-600 bg-slate-50 border-slate-100",
    step: activeApplication.step || 1,
    matchScore: activeApplication.originalData?.match_score ? Math.round(activeApplication.originalData.match_score) : null,
    matchedSkills: Array.isArray(activeApplication.originalData?.matched_skills) ? activeApplication.originalData.matched_skills : [],
    missingSkills: Array.isArray(activeApplication.originalData?.missing_skills) ? activeApplication.originalData.missing_skills : [],
    aiSummary: activeApplication.originalData?.ai_summary || null,
  };

  const TIMELINE_STEPS: TimelineStep[] = [
    {
      label: "Application Submitted",
      date: jobDetails.appliedDate,
      description: `Your application was successfully logged in the Mariwasa Talent Acquisition system with tracking ID #ARA-88${activeApplication.id}.`,
      status: "completed"
    },
    {
      label: "Initial Screening & AI Fit",
      date: jobDetails.step > 2 ? "Completed" : (jobDetails.step === 2 ? "In Review" : "Pending"),
      description: jobDetails.matchScore 
        ? `Recruiter reviewed your credentials with an automated ATS fit score of ${jobDetails.matchScore}%. Qualifications match target job specifications.`
        : "Recruitment team is evaluating your credentials against job competencies and departmental criteria.",
      status: jobDetails.step > 2 ? "completed" : (jobDetails.step === 2 ? "current" : "upcoming"),
      matchScore: jobDetails.matchScore || undefined,
      matchedSkills: jobDetails.matchedSkills
    },
    {
      label: "Technical Interview",
      date: jobDetails.step > 3 ? "Completed" : (latestInterview ? new Date(latestInterview.start_time).toLocaleString() : "Pending"),
      description: latestInterview
        ? `Evaluation session scheduled: ${latestInterview.title}. Live discussion covering core competencies and operational problem solving.`
        : "Technical assessment and panel discussion with the hiring department engineering/technical panel.",
      status: jobDetails.step > 3 ? "completed" : (latestInterview || jobDetails.step === 3 ? "current" : "upcoming"),
      interviewInfo: latestInterview || null
    },
    {
      label: "Final Interview",
      date: jobDetails.step > 4 ? "Completed" : (jobDetails.step === 4 && latestInterview ? new Date(latestInterview.start_time).toLocaleString() : "Pending"),
      description: "Leadership evaluation with the Head of Department discussing strategic vision, organizational culture, and career trajectory.",
      status: jobDetails.step > 4 ? "completed" : (jobDetails.step === 4 ? "current" : "upcoming"),
      interviewInfo: jobDetails.step === 4 && latestInterview ? latestInterview : null
    },
    {
      label: "Job Offer & Onboarding",
      date: jobDetails.status === 'Accepted' ? "Completed" : jobDetails.status === 'Rejected' ? "Concluded" : "Pending",
      description: jobDetails.status === 'Rejected' 
        ? "Thank you for participating in our evaluation process. While we are not moving forward for this opening, your profile remains in our candidate pool."
        : jobDetails.status === 'Accepted'
        ? "Congratulations! Mariwasa Siam Ceramics has extended an official offer of employment. Check your inbox for the formal offer package."
        : "Final decision phase and compensation alignment following completion of all interview rounds.",
      status: jobDetails.status === 'Accepted' ? "completed" : jobDetails.status === 'Rejected' ? "failed" : (jobDetails.step === 5 ? "current" : "upcoming")
    }
  ];

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - Track Pipeline | {jobDetails.role}</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-4 sm:px-6 py-8 sm:py-12 w-full flex-grow min-w-0">
        
          {/* Back Navigation */}
          <div className="flex items-center justify-between mb-6">
            <button 
              onClick={() => navigate('/candidate/dashboard')} 
              className="flex items-center text-xs font-black text-slate-400 uppercase tracking-widest hover:text-[#D10043] transition-colors group cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
              Back to Dashboard
            </button>

            <span className="text-xs font-bold text-slate-400">
              Candidate Pipeline Portal
            </span>
          </div>

          {/* MULTI-APPLICATION SELECTOR TABS (If candidate has > 1 application) */}
          {applications.length > 1 && (
            <div className="mb-6 bg-white p-3 rounded-2xl border border-slate-200/80 shadow-2xs">
              <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
                <span className="text-[11px] font-black uppercase tracking-wider text-slate-400 shrink-0 px-2 flex items-center gap-1.5">
                  <Layers size={14} className="text-[#D10043]" />
                  Switch Application:
                </span>
                {applications.map((app: any) => {
                  const isSelected = String(app.id) === String(activeApplication.id);
                  return (
                    <button
                      key={app.id}
                      type="button"
                      onClick={() => setSelectedId(app.id)}
                      className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-2 cursor-pointer ${
                        isSelected
                          ? 'bg-[#D10043] text-white shadow-sm shadow-[#D10043]/20'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200/60'
                      }`}
                    >
                      <span className="truncate max-w-[180px]">{app.role}</span>
                      <span className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-black ${
                        isSelected ? 'bg-white/20 text-white' : 'bg-slate-200/80 text-slate-700'
                      }`}>
                        {app.status}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          
          {/* Hero Application Header */}
          <div className="relative overflow-hidden bg-white border border-slate-200/80 p-6 sm:p-10 rounded-3xl sm:rounded-[36px] shadow-sm mb-8 sm:mb-10">
            <div className="absolute top-0 right-0 w-1/3 h-full bg-gradient-to-l from-rose-50/40 to-transparent pointer-events-none" />
            
            <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="flex gap-4 sm:gap-6 items-start sm:items-center min-w-0">
                <div className="w-14 h-14 sm:w-20 sm:h-20 bg-rose-50 rounded-2xl sm:rounded-3xl flex items-center justify-center border border-rose-100 shrink-0 shadow-xs">
                  <Briefcase className="w-7 h-7 sm:w-10 sm:h-10 text-[#D10043]" />
                </div>
                <div className="min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="bg-[#D10043]/10 text-[#D10043] text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                      Active Pipeline
                    </span>
                    <span className="text-slate-300">•</span>
                    <span className="text-[10px] font-black font-mono text-slate-500 uppercase tracking-widest bg-slate-100 px-2 py-0.5 rounded-md">
                      ID: #ARA-88{activeApplication.id}
                    </span>
                    {jobDetails.matchScore && (
                      <span className="bg-emerald-50 text-emerald-700 border border-emerald-200/60 text-[10px] font-black px-2 py-0.5 rounded-md flex items-center gap-1 font-mono">
                        <Sparkles size={11} /> {jobDetails.matchScore}% Match
                      </span>
                    )}
                  </div>

                  <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight truncate">
                    {jobDetails.role}
                  </h1>

                  <div className="flex flex-wrap gap-y-2 gap-x-4 text-xs text-slate-500 font-semibold">
                    <span className="flex items-center"><Building2 className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> {jobDetails.company}</span>
                    <span className="flex items-center"><MapPin className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> {jobDetails.location}</span>
                    <span className="flex items-center"><Clock className="w-3.5 h-3.5 mr-1.5 text-slate-400" /> Submitted {jobDetails.appliedDate}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-3 sm:gap-4 bg-slate-50/80 p-3 sm:p-4 rounded-2xl border border-slate-200/60 self-start lg:self-center shrink-0">
                <div className="text-right mr-1">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Current Stage</p>
                  <p className="text-sm font-black text-slate-900 tracking-tight">{jobDetails.status}</p>
                </div>
                <div className={`w-3.5 h-3.5 rounded-full ${
                  jobDetails.status === 'Accepted' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' :
                  jobDetails.status === 'Rejected' ? 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]' :
                  jobDetails.status === 'Reviewed' ? 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]' :
                  'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)] animate-pulse'
                }`} />
                <button 
                  type="button"
                  onClick={() => navigate('/candidate/messages')}
                  title="Message Talent Acquisition Coordinator"
                  className="p-3 bg-white hover:bg-[#D10043] hover:text-white rounded-xl shadow-2xs border border-slate-200 text-slate-600 transition-all active:scale-95 cursor-pointer"
                >
                  <MessageSquare size={18} />
                </button>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
            
            {/* Main Timeline Panel */}
            <div className="lg:col-span-2">
              <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-10 shadow-sm space-y-8">
                <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                  <div>
                    <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">Recruitment Journey</h3>
                    <p className="text-xs text-slate-400 font-medium">Step-by-step progress through Mariwasa hiring pipeline</p>
                  </div>
                  <div className="flex items-center gap-1.5 bg-slate-50 px-3 py-1.5 rounded-xl text-[10px] font-black text-slate-600 uppercase tracking-widest border border-slate-200/60">
                    <Sparkles size={13} className="text-[#D10043]" />
                    AI ATS Sync Active
                  </div>
                </div>
                
                <div className="relative pl-2 sm:pl-4">
                  {TIMELINE_STEPS.map((step, index) => (
                    <div key={index} className="relative pl-12 sm:pl-14 pb-10 sm:pb-12 last:pb-0 group">
                      {/* Connection Line */}
                      {index !== TIMELINE_STEPS.length - 1 && (
                        <div className={`absolute left-[13px] top-8 bottom-0 w-0.5 ${
                          step.status === 'completed' ? 'bg-[#D10043]/30' : 'bg-slate-200'
                        } transition-colors duration-500`} />
                      )}
                      
                      {/* Status Indicator Icon */}
                      <div className="absolute left-0 top-1 transition-transform duration-300 group-hover:scale-110">
                        {step.status === 'completed' ? (
                          <div className="bg-rose-50 w-7 h-7 rounded-full flex items-center justify-center border-2 border-[#D10043] shadow-xs">
                            <CheckCircle2 className="w-4 h-4 text-[#D10043]" />
                          </div>
                        ) : step.status === 'failed' ? (
                          <div className="bg-rose-50 w-7 h-7 rounded-full flex items-center justify-center border-2 border-rose-500 shadow-xs">
                            <XCircle className="w-4 h-4 text-rose-500" />
                          </div>
                        ) : step.status === 'current' ? (
                          <div className="bg-white border-2 border-[#D10043] w-7 h-7 rounded-full flex items-center justify-center shadow-md shadow-[#D10043]/20">
                            <div className="w-2.5 h-2.5 bg-[#D10043] rounded-full animate-ping" />
                          </div>
                        ) : (
                          <div className="bg-white border-2 border-slate-200 w-7 h-7 rounded-full flex items-center justify-center">
                            <div className="w-2 h-2 bg-slate-200 rounded-full" />
                          </div>
                        )}
                      </div>

                      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 sm:gap-4">
                        <div className="max-w-xl space-y-1.5">
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <h4 className={`text-base sm:text-lg font-black tracking-tight ${
                              step.status === 'upcoming' ? 'text-slate-400' : 'text-slate-900'
                            }`}>
                              {step.label}
                            </h4>
                            {step.status === 'current' && (
                              <span className="bg-[#D10043] text-white text-[9px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider">
                                Active Step
                              </span>
                            )}
                          </div>
                          
                          <p className={`text-xs sm:text-sm font-medium leading-relaxed ${
                            step.status === 'upcoming' ? 'text-slate-400' : 'text-slate-600'
                          }`}>
                            {step.description}
                          </p>

                          {/* Matched skills tags on screening stage */}
                          {step.matchedSkills && step.matchedSkills.length > 0 && (
                            <div className="pt-2 flex flex-wrap gap-1.5 items-center">
                              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                Verified Skills:
                              </span>
                              {step.matchedSkills.slice(0, 5).map((sk: string, i: number) => (
                                <span key={i} className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-2 py-0.5 rounded-md">
                                  {sk}
                                </span>
                              ))}
                              {step.matchedSkills.length > 5 && (
                                <span className="text-[10px] text-slate-400 font-bold">
                                  +{step.matchedSkills.length - 5} more
                                </span>
                              )}
                            </div>
                          )}
                          
                          {/* Scheduled Interview Card */}
                          {step.interviewInfo && (
                            <div className="mt-3 bg-purple-50/50 border border-purple-100 rounded-2xl p-4 sm:p-5 flex flex-col gap-3">
                              <div className="flex items-center justify-between flex-wrap gap-2">
                                <span className="flex items-center text-xs font-black text-purple-900 uppercase tracking-wider">
                                  <Calendar className="w-4 h-4 mr-1.5 text-purple-600" />
                                  Live Interview Session
                                </span>
                                <span className="bg-purple-100 text-purple-700 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                                  Google Calendar Confirmed
                                </span>
                              </div>
                              <div className="space-y-1">
                                <span className="text-sm font-black text-slate-900 block">{step.interviewInfo.title}</span>
                                <span className="text-xs font-medium text-slate-600 flex items-center gap-1.5">
                                  <Clock size={13} className="text-purple-600 shrink-0" />
                                  <span>{new Date(step.interviewInfo.start_time).toLocaleString()} – {new Date(step.interviewInfo.end_time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', hour12: true })}</span>
                                </span>
                                {step.interviewInfo.interviewer_name && (
                                  <span className="text-xs text-slate-700 font-bold block pt-0.5">
                                    Panelist: <span className="text-[#D10043]">{step.interviewInfo.interviewer_name}</span>
                                  </span>
                                )}
                              </div>

                              <div className="pt-2 flex flex-wrap items-center gap-2">
                                {step.interviewInfo.meeting_link ? (
                                  <a
                                    href={step.interviewInfo.meeting_link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs"
                                  >
                                    <Video size={13} />
                                    <span>Join Google Meet</span>
                                    <ExternalLink size={12} />
                                  </a>
                                ) : (
                                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200/60">
                                    <Mail size={13} className="text-emerald-600 shrink-0" />
                                    <span>Meeting link delivered to your registered email</span>
                                  </div>
                                )}

                                <button
                                  type="button"
                                  onClick={() => setIsEnvModalOpen(true)}
                                  className="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
                                >
                                  <Laptop size={13} />
                                  <span>Check Environment</span>
                                </button>
                              </div>
                            </div>
                          )}
                        </div>

                        <div className="text-left sm:text-right shrink-0 mt-1 sm:mt-0">
                          <span className={`text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-lg inline-block ${
                            step.status === 'upcoming' 
                              ? 'text-slate-300 bg-slate-100' 
                              : 'text-[#D10043] bg-rose-50 border border-rose-100'
                          }`}>
                            {step.date}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Sidebar Cards */}
            <div className="space-y-6 sm:space-y-8">
              
              {/* Submitted Documents Card */}
              <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
                <div className="flex justify-between items-center pb-3 border-b border-slate-100">
                  <div>
                    <h3 className="text-base font-black text-slate-900 tracking-tight">Application Documents</h3>
                    <p className="text-[11px] text-slate-400 font-medium">Uploaded resume & credentials</p>
                  </div>
                  <button 
                    type="button"
                    onClick={() => navigate('/candidate/settings')}
                    className="text-[10px] font-black text-[#D10043] uppercase tracking-wider hover:underline cursor-pointer"
                  >
                    Update Profile
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between p-4 rounded-2xl border border-slate-200/70 bg-slate-50/60 hover:bg-white hover:border-[#D10043]/30 transition-all duration-200 group">
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-slate-400 group-hover:text-[#D10043] border border-slate-200 transition-colors shrink-0 shadow-2xs">
                        <FileText size={18} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs sm:text-sm font-black text-slate-800 truncate">
                          {resumeFilename}
                        </p>
                        <p className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider mt-0.5">
                          PDF • Attached to #ARA-88{activeApplication.id}
                        </p>
                      </div>
                    </div>
                    
                    <button 
                      type="button"
                      onClick={handleDownloadResume}
                      title="View / Download Resume"
                      className="p-2 hover:bg-slate-100 rounded-xl transition-all text-slate-400 hover:text-slate-900 cursor-pointer shrink-0"
                    >
                      <Download size={16} />
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-slate-400 font-medium leading-relaxed">
                  Recruiters evaluate your qualifications using the document attached during submission. Keep your profile updated for future matching.
                </p>
              </div>

              {/* Priority Task & Next Steps Card */}
              <div className="bg-slate-900 rounded-3xl p-6 sm:p-8 shadow-xl shadow-slate-900/10 text-white relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-36 h-36 bg-[#D10043]/15 rounded-full blur-3xl pointer-events-none" />
                
                <div className="relative z-10 space-y-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 bg-rose-500/10 border border-rose-500/20 rounded-xl text-[#D10043]">
                      <AlertCircle size={18} />
                    </div>
                    <div>
                      <h4 className="font-black text-xs uppercase tracking-wider text-rose-400">Next Priority</h4>
                      <p className="text-xs font-semibold text-slate-300">Actionable Candidate Guidance</p>
                    </div>
                  </div>
                  
                  <div className="text-xs text-slate-300 leading-relaxed font-medium">
                    {activeApplication.status === 'Rejected' ? (
                      <span>Thank you for considering Mariwasa Siam Ceramics. While this position is filled, our Talent Acquisition team actively sources candidates for upcoming projects.</span>
                    ) : activeApplication.status === 'Accepted' ? (
                      <span>Congratulations on receiving an official offer! Review your compensation package and message the HR coordinator for any inquiries.</span>
                    ) : jobDetails.step === 3 || jobDetails.step === 4 ? (
                      <span>You have an active interview session pending. Test your audio/video setup and review the job requirements beforehand.</span>
                    ) : (
                      <span>Your application is actively under recruitment review. Keep your profile details and contact number verified in settings.</span>
                    )}
                  </div>
                  
                  <div className="pt-2 space-y-2">
                    {jobDetails.step === 3 || jobDetails.step === 4 ? (
                      <button 
                        type="button"
                        onClick={() => setIsEnvModalOpen(true)}
                        className="w-full py-3 px-4 bg-[#D10043] hover:bg-white hover:text-slate-900 text-white rounded-xl font-black text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-md shadow-[#D10043]/20 cursor-pointer"
                      >
                        <Laptop size={14} />
                        <span>Check Environment</span>
                        <ChevronRight size={13} />
                      </button>
                    ) : (
                      <button 
                        type="button"
                        onClick={() => setIsDetailsModalOpen(true)}
                        className="w-full py-3 px-4 bg-[#D10043] hover:bg-white hover:text-slate-900 text-white rounded-xl font-black text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-md shadow-[#D10043]/20 cursor-pointer"
                      >
                        <span>View Status & ATS Breakdown</span>
                        <ChevronRight size={13} />
                      </button>
                    )}

                    <button
                      type="button"
                      onClick={() => navigate('/candidate/messages')}
                      className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer"
                    >
                      <MessageSquare size={13} />
                      <span>Contact Recruiter</span>
                    </button>
                  </div>

                  <div className="flex items-center justify-center gap-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider pt-1">
                    <ShieldCheck size={13} className="text-emerald-400" />
                    Mariwasa Automated ATS Tracking
                  </div>
                </div>
              </div>

            </div>
          </div>

        </main>
      </div>

      {/* MODAL 1: INTERVIEW PREPARATION & ENVIRONMENT CHECK */}
      {isEnvModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-purple-50 text-purple-700 flex items-center justify-center border border-purple-100">
                  <Laptop size={20} />
                </div>
                <div>
                  <h3 className="text-base font-black text-slate-900 tracking-tight">Interview Readiness Check</h3>
                  <p className="text-xs text-slate-400 font-medium">Pre-session environment verification</p>
                </div>
              </div>
              <button 
                onClick={() => setIsEnvModalOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-3 text-xs text-slate-600">
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60 flex items-start gap-3">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-slate-900 block">Webcam & Lighting</span>
                  <span>Ensure your face is well-lit from the front and the camera is positioned at eye level.</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60 flex items-start gap-3">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-slate-900 block">Microphone & Quiet Room</span>
                  <span>Use headphones or a headset to prevent room echo and test voice clarity before logging in.</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/60 flex items-start gap-3">
                <CheckCircle2 size={16} className="text-emerald-600 shrink-0 mt-0.5" />
                <div>
                  <span className="font-bold text-slate-900 block">Network & Google Meet Access</span>
                  <span>A stable broadband connection (minimum 5 Mbps) is recommended. Coordinates were sent to your Gmail.</span>
                </div>
              </div>
            </div>

            {latestInterview?.meeting_link && (
              <div className="p-3 bg-purple-50 rounded-xl border border-purple-100 flex items-center justify-between text-xs font-bold text-purple-900">
                <span>Google Meet Link Available:</span>
                <a
                  href={latestInterview.meeting_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-1"
                >
                  <span>Open Meet</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            )}

            <div className="pt-2 flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setIsEnvModalOpen(false)}
                className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider transition-colors cursor-pointer"
              >
                I'm Ready
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: STATUS & ATS BREAKDOWN MODAL */}
      {isDetailsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#D10043] flex items-center justify-center border border-rose-100">
                  <Award size={20} />
                </div>
                <div>
                  <h3 className="text-base font-black text-slate-900 tracking-tight">Application Evaluation Scorecard</h3>
                  <p className="text-xs text-slate-400 font-medium">Automated ATS screening breakdown</p>
                </div>
              </div>
              <button 
                onClick={() => setIsDetailsModalOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-4">
              {jobDetails.matchScore ? (
                <div className="flex items-center justify-between p-4 bg-rose-50/60 rounded-2xl border border-rose-100">
                  <div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] block">Overall ATS Match</span>
                    <span className="text-2xl font-black text-slate-900 font-mono">{jobDetails.matchScore}%</span>
                  </div>
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                    High Relevance
                  </span>
                </div>
              ) : (
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 text-center">
                  <span className="text-xs font-bold text-slate-700">Screening in progress by Recruiter</span>
                </div>
              )}

              {jobDetails.matchedSkills.length > 0 && (
                <div>
                  <h5 className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2">
                    Verified Competencies
                  </h5>
                  <div className="flex flex-wrap gap-1.5">
                    {jobDetails.matchedSkills.map((sk: string, i: number) => (
                      <span key={i} className="text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-2.5 py-1 rounded-lg">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {jobDetails.missingSkills.length > 0 && (
                <div>
                  <h5 className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-2">
                    Recommended Complementary Skills
                  </h5>
                  <div className="flex flex-wrap gap-1.5">
                    {jobDetails.missingSkills.map((sk: string, i: number) => (
                      <span key={i} className="text-xs font-semibold text-slate-600 bg-slate-100 px-2.5 py-1 rounded-lg">
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {jobDetails.aiSummary && (
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 leading-relaxed">
                  <span className="font-black text-slate-900 block mb-1">ATS Evaluation Notes:</span>
                  {jobDetails.aiSummary}
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setIsDetailsModalOpen(false)}
                className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default ApplicationTracking;
