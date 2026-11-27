import React, { useState, useMemo, useCallback } from 'react';
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
  X,
  Layers,
  Search,
  Laptop,
  Award,
  RotateCcw,
  Ban,
  MinusCircle,
} from 'lucide-react';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import {
  useGetCandidateApplicationsQuery,
  useGetApplicationInterviewsQuery,
  useGetApplicationHistoryQuery,
  useWithdrawApplicationMutation,
} from '../../redux/api/apiSlice';
import { getAssetUrl } from '../../services/api';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import HelpTooltip from '../../components/common/HelpTooltip';
import CandidateRescheduleModal, { isInterviewMissed } from '../../components/modals/candidate/CandidateRescheduleModal';
import ApplicationThreadPanel from '../../components/chat/ApplicationThreadPanel';
import { getJoinButtonLabel, resolveMeetingPlatform } from '../../utils/meetingPlatform';
import { ApplicationThreadItem } from '../../services/chatService';
import { computeApplicationTracker } from '../../utils/applicationTracker';

const ApplicationTracking: React.FC = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const params = useParams<{ id?: string }>();
  const [searchParams] = useSearchParams();

  const [selectedId, setSelectedId] = useState<number | string | null>(null);
  const [isEnvModalOpen, setIsEnvModalOpen] = useState(false);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isRescheduleModalOpen, setIsRescheduleModalOpen] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [withdrawReason, setWithdrawReason] = useState('');
  const [withdrawFeedback, setWithdrawFeedback] = useState<string | null>(null);
  const [withdrawApplication, { isLoading: isWithdrawing }] = useWithdrawApplicationMutation();
  const [activeAppThread, setActiveAppThread] = useState<ApplicationThreadItem | null>(null);

  const { user, userId } = useSelector((state: RootState) => state.auth);
  const email = typeof user === 'string' ? user : (user as any)?.email;
  const candidateIdentifier = userId ? String(userId) : (email || '');

  // Stable callback for ApplicationThreadPanel so parent re-renders NEVER trigger reload loops
  const handleThreadUpdated = useCallback((thr: ApplicationThreadItem | null) => {
    setActiveAppThread((prev) => {
      if (!prev && !thr) return prev;
      if (
        prev &&
        thr &&
        prev.id === thr.id &&
        prev.unread_count === thr.unread_count &&
        prev.is_closed === thr.is_closed &&
        prev.last_message_time === thr.last_message_time
      ) {
        return prev;
      }
      return thr;
    });
  }, []);

  const handleOpenFullInbox = useCallback(
    (threadId?: number) => {
      navigate(threadId ? `/candidate/messages?thread=${threadId}` : '/candidate/messages');
    },
    [navigate]
  );

  // Real-time polling of candidate applications (linked by authenticated user_id first)
  const {
    data: applications = [],
    isLoading: isLoadingApps,
    refetch: refetchApplications,
  } = useGetCandidateApplicationsQuery(
    candidateIdentifier,
    {
      skip: !candidateIdentifier,
      pollingInterval: 10000,
    }
  );

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

  // Fetch interviews and status history for active application
  const { data: interviews = [], refetch: refetchInterviews } = useGetApplicationInterviewsQuery(
    activeApplication?.id,
    {
      skip: !activeApplication?.id,
      pollingInterval: 15000,
    }
  );

  const { data: statusHistory = [], refetch: refetchHistory } = useGetApplicationHistoryQuery(
    activeApplication?.id,
    {
      skip: !activeApplication?.id,
      pollingInterval: 15000,
    }
  );

  // Compute canonical 5-stage tracker from status history + interviews (fixes skipped stages on display!)
  const tracker = useMemo(() => {
    if (!activeApplication) return null;
    return computeApplicationTracker({
      status: activeApplication.rawStatus || activeApplication.originalData?.status || activeApplication.status,
      statusHistory: statusHistory || [],
      interviews: interviews || [],
      createdAt: activeApplication.originalData?.created_at || null,
      resolvedAt: activeApplication.originalData?.resolved_at || activeApplication.resolvedAt || null,
      updatedAt: activeApplication.originalData?.updated_at || null,
    });
  }, [activeApplication, statusHistory, interviews]);

  // Pick the latest non-canceled interview (if any) for active applications
  const activeInterviewList = useMemo(
    () =>
      (interviews || []).filter((iv: any) => {
        const st = String(iv?.status || '').toUpperCase();
        return st !== 'CANCELED' && st !== 'CANCELLED';
      }),
    [interviews]
  );
  const latestInterview =
    activeInterviewList.length > 0
      ? activeInterviewList[activeInterviewList.length - 1]
      : interviews.length > 0
        ? interviews[interviews.length - 1]
        : null;
  const interviewStatusUpper = String(latestInterview?.status || '').toUpperCase();
  const isInterviewCompleted = interviewStatusUpper === 'COMPLETED';
  const isInterviewCanceled = interviewStatusUpper === 'CANCELED' || interviewStatusUpper === 'CANCELLED';
  const interviewMissed =
    !tracker?.isWithdrawn &&
    !tracker?.isResolved &&
    !isInterviewCanceled &&
    isInterviewMissed(latestInterview);

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
    } else if (!tracker?.isWithdrawn) {
      navigate('/candidate/settings');
    }
  };

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

  if (!activeApplication || !tracker) {
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

            <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-12 shadow-sm text-center max-w-4xl mx-auto space-y-6">
              <div className="w-16 h-16 bg-rose-50 text-[#D10043] rounded-2xl flex items-center justify-center mx-auto border border-rose-100 shadow-xs">
                <Briefcase size={32} />
              </div>

              <div className="space-y-2">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-black uppercase tracking-wider bg-rose-50 text-[#D10043] border border-rose-100">
                  <Sparkles size={13} />
                  Application Progress
                </span>
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  No Active Applications Found
                </h1>
                <p className="text-sm text-slate-500 font-medium leading-relaxed max-w-lg mx-auto">
                  You have not submitted an application yet. When you apply for a position at Mariwasa Siam Ceramics, you can track every step of your application here.
                </p>
              </div>

              {/* 5 Pipeline Stages Preview */}
              <div className="pt-4 border-t border-slate-100 text-left">
                <h3 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-4 text-center">
                  How Your Application Progresses
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                  {[
                    { step: 1, title: 'Submitted', desc: 'Your resume is received and saved in our system' },
                    { step: 2, title: 'Under Review', desc: 'The hiring team reviews your resume and qualifications' },
                    { step: 3, title: 'Shortlisted', desc: 'Your profile matches our requirements for the role' },
                    { step: 4, title: 'Interview Scheduled', desc: 'Meet with the hiring team for an initial discussion' },
                    { step: 5, title: 'Initial Interview Result', desc: 'HR records whether you are endorsed for the next stage' },
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

  const isWithdrawn = tracker.isWithdrawn;
  const isPassed = tracker.isPassed;
  const isNotSelected = tracker.isNotSelected;
  const isOnHold = tracker.isOnHold;
  const isReadOnly = tracker.isReadOnly;

  const jobDetails = {
    role:
      activeApplication.role ||
      activeApplication.job?.job_title ||
      activeApplication.originalData?.job?.job_title ||
      activeApplication.originalData?.job_title ||
      'Position',
    company: activeApplication.company || 'Mariwasa Siam Ceramics',
    location: activeApplication.originalData?.location || 'Sto. Tomas, Batangas',
    appliedDate: activeApplication.appliedDate || new Date().toLocaleDateString(),
    status: tracker.displayStatus,
    matchScore: activeApplication.originalData?.match_score
      ? Math.round(activeApplication.originalData.match_score)
      : null,
    matchedSkills: Array.isArray(activeApplication.originalData?.matched_skills)
      ? activeApplication.originalData.matched_skills
      : [],
    missingSkills: Array.isArray(activeApplication.originalData?.missing_skills)
      ? activeApplication.originalData.missing_skills
      : [],
    aiSummary: activeApplication.originalData?.ai_summary || null,
  };

  const heroBadgeLabel = isWithdrawn
    ? 'Withdrawn'
    : isPassed
      ? 'Endorsed for Next Stage'
      : isNotSelected
        ? 'Not Selected'
        : isOnHold
          ? 'On Hold'
          : 'Active Pipeline';

  const heroBadgeStyle = isWithdrawn
    ? 'bg-slate-200 text-slate-700'
    : isPassed
      ? 'bg-emerald-100 text-emerald-800'
      : isNotSelected
        ? 'bg-slate-200 text-slate-700'
        : isOnHold
          ? 'bg-amber-100 text-amber-800'
          : 'bg-[#D10043]/10 text-[#D10043]';

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Track Application | {jobDetails.role} - Mariwasa Recruitment</title>
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
              Mariwasa Recruitment
            </span>
          </div>

          {/* MULTI-APPLICATION SELECTOR TABS */}
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
                      onClick={() => {
                        setSelectedId(app.id);
                        setWithdrawFeedback(null);
                      }}
                      className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all shrink-0 flex items-center gap-2 cursor-pointer ${
                        isSelected
                          ? 'bg-[#D10043] text-white shadow-sm shadow-[#D10043]/20'
                          : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200/60'
                      }`}
                    >
                      <span className="truncate max-w-[180px]">{app.role}</span>
                      <span
                        className={`text-[10px] px-1.5 py-0.2 rounded font-mono font-black ${
                          isSelected ? 'bg-white/20 text-white' : 'bg-slate-200/80 text-slate-700'
                        }`}
                      >
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
            <div
              className={`absolute top-0 right-0 w-1/3 h-full pointer-events-none ${
                isWithdrawn
                  ? 'bg-gradient-to-l from-slate-100/70 to-transparent'
                  : 'bg-gradient-to-l from-rose-50/40 to-transparent'
              }`}
            />

            <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
              <div className="flex gap-4 sm:gap-6 items-start sm:items-center min-w-0">
                <div
                  className={`w-14 h-14 sm:w-20 sm:h-20 rounded-2xl sm:rounded-3xl flex items-center justify-center border shrink-0 shadow-xs ${
                    isWithdrawn
                      ? 'bg-slate-100 border-slate-200'
                      : 'bg-rose-50 border-rose-100'
                  }`}
                >
                  {isWithdrawn ? (
                    <Ban className="w-7 h-7 sm:w-10 sm:h-10 text-slate-500" />
                  ) : (
                    <Briefcase className="w-7 h-7 sm:w-10 sm:h-10 text-[#D10043]" />
                  )}
                </div>
                <div className="min-w-0 space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`${heroBadgeStyle} text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider`}>
                      {heroBadgeLabel}
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

              <div className="flex flex-wrap items-center gap-3 sm:gap-4 bg-slate-50/80 p-3 sm:p-4 rounded-2xl border border-slate-200/60 self-start lg:self-center shrink-0">
                <div className="text-right mr-1">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">
                    {isWithdrawn ? 'Application Status' : 'Current Stage'}
                  </p>
                  <p className="text-sm font-black text-slate-900 tracking-tight">
                    {isWithdrawn ? 'Withdrawn' : jobDetails.status}
                  </p>
                </div>

                {/* Hide Withdraw action button when withdrawn, passed, or not selected */}
                {tracker.isActive && !isReadOnly && (
                  <button
                    type="button"
                    onClick={() => setShowWithdrawModal(true)}
                    className="px-3.5 py-2 rounded-xl border border-rose-200 bg-white hover:bg-rose-50 text-rose-700 text-xs font-bold transition-colors cursor-pointer"
                  >
                    Withdraw Application
                  </button>
                )}

                <div
                  className={`w-3.5 h-3.5 rounded-full ${
                    isWithdrawn
                      ? 'bg-slate-400'
                      : isPassed
                        ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]'
                        : isNotSelected
                          ? 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]'
                          : 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)] animate-pulse'
                  }`}
                />

                {activeAppThread && !isWithdrawn && (
                  <button
                    type="button"
                    onClick={() => {
                      document
                        .getElementById('application-messages-section')
                        ?.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="inline-flex items-center gap-1.5 px-3 py-2 bg-rose-50 hover:bg-[#D10043] text-[#D10043] hover:text-white rounded-xl border border-rose-200 text-xs font-bold transition-all cursor-pointer"
                  >
                    <MessageSquare size={14} />
                    <span>Message from HR</span>
                    {(activeAppThread.unread_count || 0) > 0 && (
                      <span className="px-1.5 py-0.2 rounded-full bg-[#D10043] text-white text-[10px] font-black">
                        {activeAppThread.unread_count}
                      </span>
                    )}
                  </button>
                )}
              </div>
            </div>

            {/* End-State & Hold Callout Banners (excluding Withdrawn which replaces the tracker below) */}
            {isPassed && (
              <div className="mt-5 p-4 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-start gap-3">
                <Award size={20} className="text-emerald-600 shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                  <p className="font-black text-emerald-900 text-sm">
                    Passed Initial Interview – Endorsed for next stage
                  </p>
                  <p className="text-emerald-800 leading-relaxed">
                    Congratulations! Our HR team will contact you outside the system regarding the next steps. This application is now read-only, while your history and messages remain viewable and you can still apply to other open positions.
                  </p>
                </div>
              </div>
            )}

            {isNotSelected && (
              <div className="mt-5 p-4 rounded-2xl bg-slate-50 border border-slate-200 flex items-start gap-3">
                <AlertCircle size={20} className="text-slate-500 shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                  <p className="font-black text-slate-900 text-sm">Not selected</p>
                  <p className="text-slate-600 leading-relaxed">
                    Thank you for applying. Your feedback report remains viewable, this application no longer counts toward your 3-active-application limit, and your account stays active to apply for other open roles.
                  </p>
                </div>
              </div>
            )}

            {isOnHold && (
              <div className="mt-5 p-4 rounded-2xl bg-amber-50 border border-amber-200 flex items-start gap-3">
                <Clock size={20} className="text-amber-600 shrink-0 mt-0.5" />
                <div className="space-y-1 text-xs">
                  <p className="font-black text-amber-900 text-sm">Application On Hold</p>
                  <p className="text-amber-800 leading-relaxed">
                    {activeApplication?.originalData?.hold_reason ||
                      'HR has placed this application on hold while you progress with another opportunity. HR can resume it anytime, or you may withdraw it whenever you choose.'}
                  </p>
                </div>
              </div>
            )}

            {withdrawFeedback && (
              <div className="mt-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800">
                {withdrawFeedback}
              </div>
            )}

            {/* Withdraw Single Application Confirmation Modal */}
            {showWithdrawModal && (
              <div className="fixed inset-0 z-50 bg-slate-950/60 backdrop-blur-xs flex items-center justify-center p-4">
                <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-200 space-y-4">
                  <h3 className="text-lg font-black text-slate-900">Withdraw Application?</h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    Are you sure you want to withdraw your application for <strong>{jobDetails.role}</strong>?
                    Any scheduled interviews for this role will be cancelled, the conversation will become read-only, and your active application slot will be freed immediately.
                  </p>
                  <textarea
                    value={withdrawReason}
                    onChange={(e) => setWithdrawReason(e.target.value)}
                    placeholder="Optional reason for withdrawing..."
                    rows={2}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-800 outline-none focus:border-[#D10043]"
                  />
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowWithdrawModal(false)}
                      className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 cursor-pointer"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={isWithdrawing}
                      onClick={async () => {
                        try {
                          const res = await withdrawApplication({
                            applicationId: activeApplication.id,
                            reason: withdrawReason.trim() || undefined,
                          }).unwrap();
                          setWithdrawFeedback(res?.message || 'Application withdrawn and slot freed.');
                          setShowWithdrawModal(false);
                          setWithdrawReason('');
                          refetchApplications();
                          refetchInterviews();
                          refetchHistory();
                        } catch (err: any) {
                          setWithdrawFeedback(err?.data?.detail || 'Could not withdraw application.');
                          setShowWithdrawModal(false);
                        }
                      }}
                      className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold disabled:opacity-50 cursor-pointer"
                    >
                      {isWithdrawing ? 'Withdrawing...' : 'Confirm Withdrawal'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">

            {/* Main Recruitment Journey + Messages Panel */}
            <div className="lg:col-span-2 space-y-6 sm:space-y-8">
              <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-10 shadow-sm space-y-8">
                <div className="flex items-center justify-between gap-3 flex-wrap pb-4 border-b border-slate-100">
                  <div>
                    <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                      {isWithdrawn ? 'Withdrawal Record & History' : 'Recruitment Journey'}
                    </h3>
                    <p className="text-xs text-slate-400 font-medium">
                      {isWithdrawn
                        ? 'Read-only record of stages reached prior to withdrawal'
                        : 'Step-by-step progress through Mariwasa hiring pipeline'}
                    </p>
                  </div>

                  {/* Journey Status Pill (NEVER shows Active when Withdrawn or Resolved!) */}
                  <div
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest border ${
                      isWithdrawn
                        ? 'bg-slate-100 text-slate-700 border-slate-300'
                        : isPassed
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : isNotSelected
                            ? 'bg-slate-100 text-slate-600 border-slate-200'
                            : tracker.resultOutcome === 'awaiting'
                              ? 'bg-amber-50 text-amber-800 border-amber-200'
                              : interviewMissed
                                ? 'bg-amber-50 text-amber-800 border-amber-200'
                                : 'bg-emerald-50/70 text-emerald-700 border-emerald-200/70'
                    }`}
                  >
                    {isWithdrawn ? (
                      <>
                        <Ban size={13} className="text-slate-600" />
                        Withdrawn
                      </>
                    ) : isPassed ? (
                      <>
                        <Award size={13} className="text-emerald-600" />
                        Passed Initial Interview
                      </>
                    ) : isNotSelected ? (
                      <>
                        <XCircle size={13} className="text-slate-500" />
                        Not Selected
                      </>
                    ) : tracker.resultOutcome === 'awaiting' ? (
                      <>
                        <Clock size={13} className="text-amber-600" />
                        Awaiting Result
                      </>
                    ) : interviewMissed ? (
                      <>
                        <AlertCircle size={13} className="text-amber-600" />
                        Interview Missed
                      </>
                    ) : (
                      <>
                        <CheckCircle2 size={13} className="text-emerald-500" />
                        Application Active
                      </>
                    )}
                  </div>
                </div>

                {/* WITHDRAWN BANNER REPLACING ACTIVE STAGE TRACKER */}
                {isWithdrawn && tracker.withdrawalInfo && (
                  <div
                    data-testid="withdrawn-banner"
                    className="rounded-2xl border border-slate-300 bg-slate-50 p-5 sm:p-6 space-y-2"
                  >
                    <div className="flex items-start gap-3.5">
                      <div className="w-10 h-10 rounded-xl bg-slate-200 text-slate-700 flex items-center justify-center shrink-0">
                        <Ban size={20} />
                      </div>
                      <div className="space-y-1">
                        <h4 className="text-sm sm:text-base font-black text-slate-900">
                          {tracker.withdrawalInfo.withdrawnDateLabel
                            ? `This application was withdrawn on ${tracker.withdrawalInfo.withdrawnDateLabel}`
                            : 'This application was withdrawn'}
                        </h4>
                        <p className="text-xs sm:text-sm font-semibold text-slate-700">
                          Reason: <span className="font-black text-slate-900">{tracker.withdrawalInfo.reasonCategory}</span>
                          {tracker.withdrawalInfo.detailNote
                            ? ` (${tracker.withdrawalInfo.detailNote})`
                            : ''}
                        </p>
                        <p className="text-xs text-slate-500 leading-relaxed">
                          Any scheduled interview was cancelled, your application slot has been released, and no stage is active. Stages completed prior to withdrawal are shown below as read-only history.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                {/* 5-Stage Computed Timeline (Done / Active / Upcoming / Not applicable) */}
                <div className="relative pl-2 sm:pl-4">
                  {tracker.stages.map((stage, index) => {
                    const isDone = stage.state === 'done';
                    const isActive = stage.state === 'active';
                    const isNA = stage.state === 'not_applicable';
                    const isUpcoming = stage.state === 'upcoming';
                    const isInterviewStage = stage.key === 'interview_scheduled';
                    const isResultStage = stage.key === 'initial_interview_result';
                    const showInterviewCard =
                      !isWithdrawn &&
                      isInterviewStage &&
                      latestInterview &&
                      !isInterviewCanceled;

                    return (
                      <div
                        key={stage.key}
                        className={`relative pl-12 sm:pl-14 pb-9 sm:pb-11 last:pb-0 group ${
                          isNA ? 'opacity-65' : ''
                        }`}
                      >
                        {/* Connection Line */}
                        {index !== tracker.stages.length - 1 && (
                          <div
                            className={`absolute left-[13px] top-8 bottom-0 w-0.5 transition-colors duration-500 ${
                              isDone ? 'bg-emerald-300' : 'bg-slate-200'
                            }`}
                          />
                        )}

                        {/* Status Indicator Icon */}
                        <div className="absolute left-0 top-1">
                          {isDone ? (
                            stage.outcome === 'not_selected' ? (
                              <div className="bg-rose-50 w-7 h-7 rounded-full flex items-center justify-center border-2 border-rose-500 shadow-xs">
                                <XCircle className="w-4 h-4 text-rose-500" />
                              </div>
                            ) : stage.outcome === 'passed' ? (
                              <div className="bg-emerald-600 w-7 h-7 rounded-full flex items-center justify-center border-2 border-emerald-600 shadow-xs">
                                <Award className="w-4 h-4 text-white" />
                              </div>
                            ) : (
                              <div className="bg-emerald-50 w-7 h-7 rounded-full flex items-center justify-center border-2 border-emerald-500 shadow-xs">
                                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              </div>
                            )
                          ) : isActive ? (
                            stage.outcome === 'awaiting' || isOnHold ? (
                              <div className="bg-amber-50 border-2 border-amber-500 w-7 h-7 rounded-full flex items-center justify-center shadow-xs">
                                <Clock className="w-4 h-4 text-amber-600" />
                              </div>
                            ) : (
                              <div className="bg-white border-2 border-[#D10043] w-7 h-7 rounded-full flex items-center justify-center shadow-md shadow-[#D10043]/20">
                                <div className="w-2.5 h-2.5 bg-[#D10043] rounded-full animate-ping" />
                              </div>
                            )
                          ) : isNA ? (
                            <div className="bg-slate-100 border-2 border-slate-200 w-7 h-7 rounded-full flex items-center justify-center">
                              <MinusCircle className="w-3.5 h-3.5 text-slate-400" />
                            </div>
                          ) : (
                            <div className="bg-white border-2 border-slate-200 w-7 h-7 rounded-full flex items-center justify-center">
                              <div className="w-2 h-2 bg-slate-200 rounded-full" />
                            </div>
                          )}
                        </div>

                        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2 sm:gap-4">
                          <div className="max-w-xl space-y-1.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4
                                className={`text-base sm:text-lg font-black tracking-tight ${
                                  isUpcoming || isNA ? 'text-slate-400' : 'text-slate-900'
                                }`}
                              >
                                {stage.label}
                              </h4>

                              {isDone && stage.outcome !== 'not_selected' && stage.outcome !== 'passed' && (
                                <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-[9px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider">
                                  Done
                                </span>
                              )}

                              {stage.skipped && stage.skippedNote && (
                                <span className="bg-emerald-50/80 text-emerald-700 border border-emerald-200/80 text-[9px] font-bold px-2 py-0.5 rounded-md">
                                  {stage.skippedNote}
                                </span>
                              )}

                              {isActive && (
                                <span
                                  className={`text-[9px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider ${
                                    stage.outcome === 'awaiting' || isOnHold
                                      ? 'bg-amber-500 text-white'
                                      : 'bg-[#D10043] text-white'
                                  }`}
                                >
                                  {stage.badgeText || 'Active'}
                                </span>
                              )}

                              {isNA && (
                                <span className="bg-slate-100 text-slate-500 border border-slate-200 text-[9px] font-bold px-2 py-0.5 rounded-md uppercase tracking-wider">
                                  Not applicable
                                </span>
                              )}

                              {isResultStage && stage.outcome === 'passed' && (
                                <span className="bg-emerald-600 text-white text-[9px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider">
                                  Passed
                                </span>
                              )}

                              {isResultStage && stage.outcome === 'not_selected' && (
                                <span className="bg-rose-100 text-rose-700 border border-rose-200 text-[9px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider">
                                  Not selected
                                </span>
                              )}
                            </div>

                            <p
                              className={`text-xs sm:text-sm font-medium leading-relaxed ${
                                isUpcoming || isNA ? 'text-slate-400' : 'text-slate-600'
                              }`}
                            >
                              {stage.key === 'submitted'
                                ? `Your application was received for ${jobDetails.role} with reference #ARA-88${activeApplication.id}.`
                                : stage.key === 'under_review' && jobDetails.matchScore && !isUpcoming && !isNA && !stage.skipped
                                  ? `The hiring team reviewed your resume with a fit score of ${jobDetails.matchScore}%.`
                                  : stage.subtitle}
                            </p>

                            {/* Verified skills on Under Review stage */}
                            {stage.key === 'under_review' && !isUpcoming && !isNA && jobDetails.matchedSkills.length > 0 && (
                              <div className="pt-1.5 flex flex-wrap gap-1.5 items-center">
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                                  Verified Skills:
                                </span>
                                {jobDetails.matchedSkills.slice(0, 5).map((sk: string, i: number) => (
                                  <span
                                    key={i}
                                    className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200/60 px-2 py-0.5 rounded-md"
                                  >
                                    {sk}
                                  </span>
                                ))}
                                {jobDetails.matchedSkills.length > 5 && (
                                  <span className="text-[10px] text-slate-400 font-bold">
                                    +{jobDetails.matchedSkills.length - 5} more
                                  </span>
                                )}
                              </div>
                            )}

                            {/* Scheduled / Completed Interview Card (hidden when withdrawn) */}
                            {showInterviewCard && latestInterview && (
                              <div
                                className={`mt-3 rounded-2xl p-4 sm:p-5 flex flex-col gap-3 border ${
                                  interviewMissed
                                    ? 'bg-amber-50/60 border-amber-200'
                                    : 'bg-purple-50/50 border-purple-100'
                                }`}
                              >
                                <div className="flex items-center justify-between flex-wrap gap-2">
                                  <span
                                    className={`flex items-center text-xs font-black uppercase tracking-wider ${
                                      interviewMissed ? 'text-amber-900' : 'text-purple-900'
                                    }`}
                                  >
                                    <Calendar className={`w-4 h-4 mr-1.5 ${interviewMissed ? 'text-amber-600' : 'text-purple-600'}`} />
                                    {interviewMissed
                                      ? 'Missed Interview Session'
                                      : isInterviewCompleted
                                        ? 'Completed Interview Session'
                                        : 'Live Interview Session'}
                                  </span>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    {interviewMissed ? (
                                      <span className="bg-amber-100 text-amber-800 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider inline-flex items-center gap-1">
                                        <AlertCircle size={10} className="text-amber-700" /> Past Schedule
                                      </span>
                                    ) : isInterviewCompleted ? (
                                      <span className="bg-emerald-100 text-emerald-800 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                                        Completed
                                      </span>
                                    ) : (
                                      <span className="bg-purple-100 text-purple-700 text-[10px] font-black px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                                        Google Calendar Confirmed
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="space-y-1">
                                  <span className="text-sm font-black text-slate-900 block">{latestInterview.title}</span>
                                  <span className="text-xs font-medium text-slate-600 flex items-center gap-1.5">
                                    <Clock size={13} className={`${interviewMissed ? 'text-amber-600' : 'text-purple-600'} shrink-0`} />
                                    <span>
                                      {new Date(latestInterview.start_time).toLocaleString()} –{' '}
                                      {new Date(latestInterview.end_time).toLocaleTimeString([], {
                                        hour: 'numeric',
                                        minute: '2-digit',
                                        hour12: true,
                                      })}
                                    </span>
                                  </span>
                                  {latestInterview.interviewer_name && (
                                    <span className="text-xs text-slate-700 font-bold block pt-0.5">
                                      Panelist: <span className="text-[#D10043]">{latestInterview.interviewer_name}</span>
                                    </span>
                                  )}
                                </div>

                                <div className="text-xs text-slate-700 space-y-1">
                                  <p>Interview type: {latestInterview.interview_type || 'Not specified'}</p>
                                  {(() => {
                                    const ivPlatform = resolveMeetingPlatform(latestInterview.meeting_link, latestInterview.platform);
                                    return ivPlatform ? <p>Platform: {ivPlatform}</p> : null;
                                  })()}
                                  {latestInterview.location && <p>Location: {latestInterview.location}</p>}
                                  {latestInterview.instructions && <p>{latestInterview.instructions}</p>}
                                  <p>All interview times are Philippine time.</p>
                                </div>

                                {/* Hide action buttons when application is read-only / resolved / withdrawn */}
                                {!isReadOnly && !tracker.isResolved && (
                                  <div className="pt-2 flex flex-wrap items-center gap-2">
                                    {interviewMissed ? (
                                      <button
                                        type="button"
                                        onClick={() => setIsRescheduleModalOpen(true)}
                                        className="px-4 py-2 bg-[#D10043] hover:bg-[#b00038] text-white rounded-xl text-xs font-black flex items-center gap-1.5 transition-colors shadow-sm cursor-pointer"
                                      >
                                        <RotateCcw size={13} />
                                        <span>Reschedule with Interviewer Availability</span>
                                      </button>
                                    ) : (
                                      <>
                                        {latestInterview.meeting_link ? (
                                          <a
                                            href={latestInterview.meeting_link}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            className="px-3.5 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs"
                                          >
                                            <Video size={13} />
                                            <span>{getJoinButtonLabel(latestInterview.meeting_link, latestInterview.platform)}</span>
                                            <ExternalLink size={12} />
                                          </a>
                                        ) : (
                                          <div className="flex items-center gap-1.5 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200/60">
                                            <Mail size={13} className="text-emerald-600 shrink-0" />
                                            <span>See the interview location above</span>
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
                                      </>
                                    )}
                                  </div>
                                )}
                              </div>
                            )}

                            {/* Initial Interview Result Stage Detail Note */}
                            {isResultStage && !isWithdrawn && tracker.resultOutcome === 'awaiting' && (
                              <div className="mt-2 p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 font-medium flex items-center gap-2">
                                <Clock size={14} className="text-amber-600 shrink-0" />
                                <span>
                                  Your interview date has passed. This stage stays &ldquo;Awaiting result&rdquo; until HR records your outcome.
                                </span>
                              </div>
                            )}
                          </div>

                          <div className="text-left sm:text-right shrink-0 mt-1 sm:mt-0">
                            <span
                              className={`text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-lg inline-block ${
                                isNA
                                  ? 'text-slate-400 bg-slate-100'
                                  : isUpcoming
                                    ? 'text-slate-400 bg-slate-100'
                                    : isDone
                                      ? 'text-emerald-700 bg-emerald-50 border border-emerald-100'
                                      : 'text-[#D10043] bg-rose-50 border border-rose-100'
                              }`}
                            >
                              {isNA
                                ? 'Not applicable'
                                : stage.dateLabel || stage.badgeText || (isUpcoming ? 'Upcoming' : 'Active')}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Per-Application Two-Way Thread (HR-initiated only; read-only when withdrawn) */}
              {activeApplication?.id && (
                <ApplicationThreadPanel
                  applicationId={activeApplication.id}
                  jobTitle={jobDetails.role}
                  viewerRole="CANDIDATE"
                  readOnly={isWithdrawn}
                  readOnlyReason={
                    isWithdrawn
                      ? 'This application was withdrawn. Messaging is closed.'
                      : undefined
                  }
                  onThreadUpdated={handleThreadUpdated}
                  onOpenFullInbox={handleOpenFullInbox}
                />
              )}
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
                  {!isWithdrawn && !isReadOnly && (
                    <button
                      type="button"
                      onClick={() => navigate('/candidate/settings')}
                      className="text-[10px] font-black text-[#D10043] uppercase tracking-wider hover:underline cursor-pointer"
                    >
                      Update Profile
                    </button>
                  )}
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
                  {isWithdrawn
                    ? 'This document is preserved for your historical application record.'
                    : 'Recruiters evaluate your qualifications using the document attached during submission. Keep your profile updated for future matching.'}
                </p>
              </div>

              {/* Feedback Report / Next Priority Card */}
              <div className="bg-slate-900 rounded-3xl p-6 sm:p-8 shadow-xl shadow-slate-900/10 text-white relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-36 h-36 bg-[#D10043]/15 rounded-full blur-3xl pointer-events-none" />

                <div className="relative z-10 space-y-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 bg-rose-500/10 border border-rose-500/20 rounded-xl text-[#D10043]">
                      {isWithdrawn ? <Ban size={18} /> : <AlertCircle size={18} />}
                    </div>
                    <div>
                      <h4 className="font-black text-xs uppercase tracking-wider text-rose-400">
                        {isWithdrawn ? 'Application Closed' : isNotSelected ? 'Feedback Report' : 'Next Priority'}
                      </h4>
                      <p className="text-xs font-semibold text-slate-300">
                        {isWithdrawn ? 'Read-Only Record' : 'Actionable Candidate Guidance'}
                      </p>
                    </div>
                  </div>

                  <div className="text-xs text-slate-300 leading-relaxed font-medium">
                    {isWithdrawn ? (
                      <span>
                        This application was withdrawn ({tracker.withdrawalInfo?.reasonCategory || 'Withdrawn by applicant'}). Your application slot is free and you may browse other open positions anytime.
                      </span>
                    ) : isPassed ? (
                      <span>
                        Congratulations on passing your initial interview! HR will contact you outside the system regarding the next steps.
                      </span>
                    ) : isNotSelected ? (
                      <span>
                        Thank you for considering Mariwasa Siam Ceramics. Your resume feedback report remains viewable below.
                      </span>
                    ) : tracker.resultOutcome === 'awaiting' ? (
                      <span>
                        Your initial interview date has passed. Please wait while HR records your Initial Interview Result.
                      </span>
                    ) : tracker.currentStageIndex >= 3 ? (
                      <span>
                        Your initial interview is scheduled. Review your meeting coordinates and verify your environment ahead of time.
                      </span>
                    ) : (
                      <span>
                        Your application is being reviewed by our recruitment team. Keep your profile details and contact number up to date.
                      </span>
                    )}
                  </div>

                  {/* Action Buttons (Hidden for Withdrawn; Feedback Report stays viewable for Not Selected!) */}
                  {!isWithdrawn && (
                    <div className="pt-2 space-y-2">
                      {!isPassed && !isNotSelected && tracker.currentStageIndex === 3 ? (
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
                          <span>{isNotSelected ? 'View Feedback Report' : 'View Details'}</span>
                          <ChevronRight size={13} />
                        </button>
                      )}

                      {activeAppThread && (
                        <button
                          type="button"
                          onClick={() =>
                            document
                              .getElementById('application-messages-section')
                              ?.scrollIntoView({ behavior: 'smooth' })
                          }
                          className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-bold text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 cursor-pointer"
                        >
                          <MessageSquare size={13} />
                          <span>View Message from HR</span>
                        </button>
                      )}
                    </div>
                  )}

                  <div className="flex items-center justify-center gap-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider pt-1">
                    <ShieldCheck size={13} className="text-emerald-400" />
                    Mariwasa Recruitment Portal
                  </div>
                </div>
              </div>

            </div>
          </div>

        </main>
      </div>

      {/* MODAL 1: INTERVIEW PREPARATION & ENVIRONMENT CHECK */}
      {isEnvModalOpen && !isWithdrawn && (
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
                  <span className="font-bold text-slate-900 block">
                    {(() => {
                      const envPlatform = resolveMeetingPlatform(latestInterview?.meeting_link, latestInterview?.platform);
                      return `Network & ${envPlatform && envPlatform !== 'Other' ? envPlatform : 'Online Meeting'} Access`;
                    })()}
                  </span>
                  <span>A stable broadband connection (minimum 5 Mbps) is recommended. Coordinates were sent to your Gmail.</span>
                </div>
              </div>
            </div>

            {latestInterview?.meeting_link && (
              <div className="p-3 bg-purple-50 rounded-xl border border-purple-100 flex items-center justify-between text-xs font-bold text-purple-900">
                <span>Meeting link available:</span>
                <a
                  href={latestInterview.meeting_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-1"
                >
                  <span>{getJoinButtonLabel(latestInterview.meeting_link, latestInterview.platform)}</span>
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

      {/* MODAL 2: FEEDBACK REPORT & ATS BREAKDOWN MODAL */}
      {isDetailsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-white border border-slate-200 rounded-3xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2.5">
                <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#D10043] flex items-center justify-center border border-rose-100">
                  <Award size={20} />
                </div>
                <div>
                  <h3 className="text-base font-black text-slate-900 tracking-tight">How You Fit This Role</h3>
                  <p className="text-xs text-slate-400 font-medium">Based on your submitted application</p>
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
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] block">How well you fit this job</span>
                      <HelpTooltip text="This score compares the skills and experience on your resume with the job requirements." />
                    </div>
                    <span className="text-2xl font-black text-slate-900 font-mono">{jobDetails.matchScore}%</span>
                  </div>
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                    {jobDetails.matchScore >= 70 ? 'Strong match' : 'Evaluated'}
                  </span>
                </div>
              ) : (
                <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 text-center">
                  <span className="text-xs font-bold text-slate-700">Currently being reviewed by the hiring team</span>
                </div>
              )}

              {jobDetails.matchedSkills.length > 0 && (
                <div>
                  <div className="flex items-center gap-1 mb-2">
                    <h5 className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                      Skills you have
                    </h5>
                    <HelpTooltip text="Skills found on your resume that match what this job is looking for." />
                  </div>
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
                  <div className="flex items-center gap-1 mb-2">
                    <h5 className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                      Skills you can add
                    </h5>
                    <HelpTooltip text="Skills mentioned in the job description that were not detected on your resume." />
                  </div>
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
                  <span className="font-black text-slate-900 block mb-1">Feedback Summary:</span>
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

      {/* CANDIDATE RESCHEDULE INTERVIEW MODAL (disabled for withdrawn / resolved) */}
      {!isWithdrawn && !tracker.isResolved && (
        <CandidateRescheduleModal
          isOpen={isRescheduleModalOpen}
          onClose={() => setIsRescheduleModalOpen(false)}
          interview={latestInterview}
          onSuccess={() => {
            refetchInterviews();
            refetchApplications();
          }}
        />
      )}

    </div>
  );
};

export default ApplicationTracking;
