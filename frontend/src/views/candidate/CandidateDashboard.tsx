import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import {
  Briefcase,
  Zap,
  ChevronRight,
  Calendar,
  Bookmark,
  TrendingUp,
  Search,
  X
} from 'lucide-react';

import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import WelcomeHeader from '../../components/candidate/dashboard/WelcomeHeader';
import ApplicationList from '../../components/candidate/dashboard/ApplicationList';
import RecommendedJobs from '../../components/candidate/dashboard/RecommendedJobs';
import ProfileStrength from '../../components/candidate/dashboard/ProfileStrength';
import UpcomingInterviews from '../../components/candidate/dashboard/UpcomingInterviews';
import QuickActions from '../../components/candidate/dashboard/QuickActions';
import ChatWidget from '../../components/layout/ChatWidget';
import HelpTooltip from '../../components/common/HelpTooltip';

import {
  useGetCandidateApplicationsQuery,
  useGetCandidateInterviewsQuery
} from '../../redux/api/apiSlice';
import { RootState } from '../../redux/store';

const CandidateDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user: email, userId } = useSelector((state: RootState) => state.auth);
  const candidateIdentifier = userId ? String(userId) : (typeof email === 'string' ? email : (email as any)?.email || '');

  // Live queries (linked by authenticated user_id first)
  const { data: applications = [], isLoading: isLoadingApps } = useGetCandidateApplicationsQuery(
    candidateIdentifier,
    { skip: !candidateIdentifier, pollingInterval: 10000 }
  );

  const { data: interviews = [] } = useGetCandidateInterviewsQuery(
    candidateIdentifier,
    { skip: !candidateIdentifier, pollingInterval: 10000 }
  );

  // Active Interviews calculation
  const activeInterviews = useMemo(() => {
    return interviews.filter((i: any) => i.status !== 'CANCELED' && i.status !== 'COMPLETED');
  }, [interviews]);

  // In Evaluation calculation
  const inReviewCount = useMemo(() => {
    return applications.filter((app: any) => {
      const s = (app.status || '').toUpperCase();
      return s !== 'REJECTED' && s !== 'ACCEPTED';
    }).length;
  }, [applications]);

  // Bookmarked jobs state & sync
  const [bookmarkTrigger, setBookmarkTrigger] = useState(0);
  const bookmarkedCount = useMemo(() => {
    try {
      const saved = localStorage.getItem('candidate_bookmarked_jobs');
      return saved ? JSON.parse(saved).length : 0;
    } catch {
      return 0;
    }
  }, [bookmarkTrigger]);

  // Draft Application State
  const [hasDraft, setHasDraft] = useState(() => {
    return Boolean(localStorage.getItem('draft_application_job_id'));
  });

  const draftJobTitle = localStorage.getItem('draft_application_job_title') || 'Position Application';
  const draftJobId = localStorage.getItem('draft_application_job_id');
  const draftStep = parseInt(localStorage.getItem('draft_application_step') || '1', 10);

  const getDraftProgress = () => {
    if (draftStep === 1) return { text: 'Step 1: Resume Upload', percent: 33 };
    if (draftStep === 2) return { text: 'Step 2: Profile Verification', percent: 66 };
    if (draftStep === 3) return { text: 'Step 3: Final Review', percent: 90 };
    return { text: 'In Progress', percent: 25 };
  };
  const draftProgress = getDraftProgress();

  const getDraftRoute = () => {
    if (draftStep === 2) return `/candidate/update-profile/${draftJobId}`;
    if (draftStep === 3) return `/candidate/preview-profile/${draftJobId}`;
    return `/candidate/upload-resume/${draftJobId}`;
  };

  const handleDismissDraft = () => {
    localStorage.removeItem('draft_application_job_id');
    localStorage.removeItem('draft_application_job_title');
    localStorage.removeItem('draft_application_step');
    setHasDraft(false);
  };

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Dashboard | Mariwasa Recruitment</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        
        <main className="flex-1 max-w-[1440px] mx-auto px-3.5 sm:px-6 lg:px-8 py-5 sm:py-8 w-full flex-grow min-w-0">
          
          {/* WELCOME BANNER */}
          <WelcomeHeader
            applicationCount={applications.length}
            interviewCount={activeInterviews.length}
          />

          {/* EXECUTIVE KPI STATS ROW */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4 mb-6 sm:mb-8">
            
            {/* KPI 1: Active Applications */}
            <div
              onClick={() => navigate('/candidate/applicationtracking')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-3.5 sm:p-5 shadow-2xs hover:shadow-md hover:border-[#D10043]/30 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    Applications
                  </span>
                  <HelpTooltip content="Total job applications you have submitted." />
                </div>
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-slate-50 group-hover:bg-[#D10043]/10 text-slate-400 group-hover:text-[#D10043] flex items-center justify-center transition-colors">
                  <Briefcase size={16} className="sm:w-[18px] sm:h-[18px]" />
                </div>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {applications.length}
                </span>
                <span className="text-[10px] sm:text-xs font-bold text-slate-400">Total</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                {applications.length > 0 ? 'Submitted applications' : 'No submissions yet'}
              </p>
            </div>

            {/* KPI 2: Interview Schedules */}
            <div
              onClick={() => navigate('/candidate/applicationtracking')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-3.5 sm:p-5 shadow-2xs hover:shadow-md hover:border-purple-200 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    Interviews
                  </span>
                  <HelpTooltip content="Upcoming phone, video, or in-person interview invitations." />
                </div>
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-purple-50 group-hover:bg-purple-100 text-purple-600 flex items-center justify-center transition-colors">
                  <Calendar size={16} className="sm:w-[18px] sm:h-[18px]" />
                </div>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {activeInterviews.length}
                </span>
                <span className="text-[10px] sm:text-xs font-bold text-purple-600">Upcoming</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                {activeInterviews.length > 0 ? 'Upcoming interviews' : 'No interviews scheduled'}
              </p>
            </div>

            {/* KPI 3: Saved Roles */}
            <div
              onClick={() => navigate('/candidate/findjobs')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-3.5 sm:p-5 shadow-2xs hover:shadow-md hover:border-amber-200 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    Saved Jobs
                  </span>
                  <HelpTooltip content="Jobs you bookmarked to look at or apply for later." />
                </div>
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-amber-50 group-hover:bg-amber-100 text-amber-600 flex items-center justify-center transition-colors">
                  <Bookmark size={16} className={`sm:w-[18px] sm:h-[18px] ${bookmarkedCount > 0 ? 'fill-amber-500' : ''}`} />
                </div>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {bookmarkedCount}
                </span>
                <span className="text-[10px] sm:text-xs font-bold text-slate-400">Bookmarked</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                Saved for later
              </p>
            </div>

            {/* KPI 4: Under Evaluation */}
            <div
              onClick={() => navigate('/candidate/applicationtracking')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-3.5 sm:p-5 shadow-2xs hover:shadow-md hover:border-emerald-200 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    Being Reviewed
                  </span>
                  <HelpTooltip content="Applications currently being reviewed by the hiring team." />
                </div>
                <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-emerald-50 group-hover:bg-emerald-100 text-emerald-600 flex items-center justify-center transition-colors">
                  <TrendingUp size={16} className="sm:w-[18px] sm:h-[18px]" />
                </div>
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {inReviewCount}
                </span>
                <span className="text-[10px] sm:text-xs font-bold text-emerald-600">Active</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                {inReviewCount > 0 ? 'Under review by hiring team' : 'No active reviews'}
              </p>
            </div>

          </div>

          {/* NEXT ACTION PROMINENT CARD */}
          {activeInterviews.length > 0 ? (
            <div className="bg-gradient-to-r from-purple-900 via-slate-900 to-slate-900 text-white rounded-2xl sm:rounded-3xl p-5 sm:p-6 shadow-md mb-6 sm:mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border border-purple-800/40">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-purple-500/20 text-purple-300 flex items-center justify-center shrink-0 border border-purple-400/30">
                  <Calendar size={24} />
                </div>
                <div>
                  <span className="text-[10px] font-black uppercase tracking-wider text-purple-300 bg-purple-500/20 px-2.5 py-0.5 rounded-full border border-purple-400/20">
                    Next Action
                  </span>
                  <h3 className="text-base sm:text-lg font-black tracking-tight mt-1">
                    Confirm your interview details
                  </h3>
                  <p className="text-xs text-slate-300 font-medium mt-0.5">
                    You have an upcoming interview scheduled. Check the date, time, and session coordinates.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => navigate('/candidate/applicationtracking')}
                className="px-5 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-400 text-white font-black text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-sm active:scale-[0.98] cursor-pointer shrink-0 self-end sm:self-auto"
              >
                <span>View Interview</span>
                <ChevronRight size={14} />
              </button>
            </div>
          ) : hasDraft && draftJobId ? (
            <div className="bg-white border border-rose-200/80 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-xs mb-6 sm:mb-8 relative overflow-hidden">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                <div className="flex items-start gap-3.5">
                  <div className="w-10 h-10 rounded-xl bg-rose-50 text-[#D10043] flex items-center justify-center shrink-0 border border-rose-100">
                    <Zap size={18} className="animate-pulse" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] bg-rose-50 px-2 py-0.5 rounded border border-rose-100">
                        Next Action: {draftStep === 3 ? 'Answer your questions' : draftStep === 2 ? 'Review your details' : 'Complete your application'}
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="text-xs font-semibold text-slate-500">
                        {draftProgress.text}
                      </span>
                    </div>
                    <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight mt-0.5">
                      {draftJobTitle}
                    </h3>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">
                      Mariwasa Siam Ceramics • Complete submission to proceed to recruitment review
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                  <button
                    type="button"
                    onClick={handleDismissDraft}
                    title="Dismiss Draft"
                    className="p-2.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
                  >
                    <X size={16} />
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate(getDraftRoute())}
                    className="px-5 py-2.5 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-sm shadow-[#D10043]/20 active:scale-[0.98] cursor-pointer"
                  >
                    <span>{draftStep === 3 ? 'Answer questions' : 'Continue'}</span>
                    <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            </div>
          ) : applications.length === 0 ? (
            <div className="bg-gradient-to-r from-slate-900 to-slate-800 text-white rounded-2xl sm:rounded-3xl p-5 sm:p-6 shadow-md mb-6 sm:mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-[#D10043]/20 text-[#D10043] flex items-center justify-center shrink-0 border border-[#D10043]/30">
                  <Briefcase size={24} />
                </div>
                <div>
                  <span className="text-[10px] font-black uppercase tracking-wider text-rose-300 bg-rose-500/20 px-2.5 py-0.5 rounded-full border border-rose-400/20">
                    Next Action
                  </span>
                  <h3 className="text-base sm:text-lg font-black tracking-tight mt-1">
                    Upload your resume to get started
                  </h3>
                  <p className="text-xs text-slate-300 font-medium mt-0.5">
                    We compare your resume with open positions at Mariwasa to show you the jobs that fit you best.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => navigate('/candidate/smart-upload')}
                className="px-5 py-2.5 rounded-xl bg-[#D10043] hover:bg-white hover:text-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center gap-1.5 transition-all shadow-sm active:scale-[0.98] cursor-pointer shrink-0 self-end sm:self-auto"
              >
                <span>Upload Resume</span>
                <ChevronRight size={14} />
              </button>
            </div>
          ) : null}

          {/* MAIN 2-COLUMN DASHBOARD GRID */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">

            {/* LEFT 2 COLUMNS: APPLICATIONS & RECOMMENDED JOBS */}
            <div className="lg:col-span-2 space-y-6 sm:space-y-8">
              
              {/* Application List Component */}
              {isLoadingApps ? (
                <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-6 shadow-xs space-y-4 animate-pulse">
                  <div className="h-6 bg-slate-200 rounded w-1/4 mb-4" />
                  <div className="h-24 bg-slate-50 rounded-2xl" />
                  <div className="h-24 bg-slate-50 rounded-2xl" />
                </div>
              ) : applications.length > 0 ? (
                <ApplicationList applications={applications} />
              ) : (
                <div className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-6 sm:p-10 shadow-xs text-center space-y-4">
                  <div className="w-14 h-14 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300 border border-slate-100">
                    <Briefcase size={28} />
                  </div>
                  <div className="max-w-md mx-auto space-y-1.5">
                    <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">No Active Applications</h3>
                    <p className="text-slate-500 text-xs sm:text-sm font-medium leading-relaxed">
                      You haven't submitted any job applications yet. Browse open positions across Mariwasa to jumpstart your career.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate('/candidate/findjobs')}
                    className="inline-flex items-center gap-2 px-6 py-3 bg-[#D10043] hover:bg-slate-900 text-white rounded-xl font-black text-xs uppercase tracking-wider transition-all shadow-sm shadow-[#D10043]/20 active:scale-95 cursor-pointer"
                  >
                    <Search size={14} />
                    <span>Explore Open Opportunities</span>
                  </button>
                </div>
              )}

              {/* RECOMMENDED OPENINGS COMPONENT */}
              <RecommendedJobs
                onBookmarkChange={() => setBookmarkTrigger((p) => p + 1)}
              />

            </div>

            {/* RIGHT COLUMN: INTERVIEWS, PROFILE READINESS, QUICK ACTIONS */}
            <div className="space-y-6 sm:space-y-8">
              
              {/* Upcoming Interviews Schedule */}
              <UpcomingInterviews />

              {/* Profile Strength */}
              <ProfileStrength />

              {/* Quick Actions Hub */}
              <QuickActions />

            </div>

          </div>

          <ChatWidget />
        </main>

      </div>
    </div>
  );
};

export default CandidateDashboard;
