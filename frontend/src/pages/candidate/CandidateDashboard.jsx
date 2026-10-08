import React, { useState, useMemo } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import {
  Briefcase,
  Zap,
  ChevronRight,
  Calendar,
  Bookmark,
  TrendingUp,
  ShieldCheck,
  Search,
  ArrowRight,
  Clock,
  X,
  Sparkles,
  Layers
} from 'lucide-react';

import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import WelcomeHeader from '../../components/candidate/dashboard/WelcomeHeader';
import ApplicationList from '../../components/candidate/dashboard/ApplicationList';
import ProfileStrength from '../../components/candidate/dashboard/ProfileStrength';
import UpcomingInterviews from '../../components/candidate/dashboard/UpcomingInterviews';
import QuickActions from '../../components/candidate/dashboard/QuickActions';
import ChatWidget from '../../components/layout/ChatWidget';

import {
  useGetCandidateApplicationsQuery,
  useGetCandidateInterviewsQuery
} from '../../redux/api/apiSlice';

const CandidateDashboard = () => {
  const navigate = useNavigate();
  const { user: email } = useSelector((state) => state.auth);

  // Live queries
  const { data: applications = [], isLoading: isLoadingApps } = useGetCandidateApplicationsQuery(
    email,
    { skip: !email, pollingInterval: 10000 }
  );

  const { data: interviews = [], isLoading: isLoadingInterviews } = useGetCandidateInterviewsQuery(
    email,
    { skip: !email, pollingInterval: 10000 }
  );

  // Active Interviews calculation
  const activeInterviews = useMemo(() => {
    return interviews.filter((i) => i.status !== 'CANCELED' && i.status !== 'COMPLETED');
  }, [interviews]);

  // Bookmarked jobs count
  const bookmarkedCount = useMemo(() => {
    try {
      const saved = localStorage.getItem('candidate_bookmarked_jobs');
      return saved ? JSON.parse(saved).length : 0;
    } catch {
      return 0;
    }
  }, []);

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
        <title>Candidate Portal | Mariwasa Career Hub</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        
        <main className="flex-1 max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 w-full flex-grow min-w-0">
          
          {/* WELCOME BANNER */}
          <WelcomeHeader
            applicationCount={applications.length}
            interviewCount={activeInterviews.length}
          />

          {/* EXECUTIVE KPI STATS ROW */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5 mb-8 sm:mb-10">
            
            {/* KPI 1: Active Applications */}
            <div
              onClick={() => navigate('/candidate/applicationtracking')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xs hover:shadow-md hover:border-[#D10043]/30 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                  Applications
                </span>
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-slate-50 group-hover:bg-[#D10043]/10 text-slate-400 group-hover:text-[#D10043] flex items-center justify-center transition-colors">
                  <Briefcase size={18} />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {applications.length}
                </span>
                <span className="text-xs font-bold text-slate-400">Total</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                {applications.length > 0 ? 'Active in recruitment pipeline' : 'No submissions yet'}
              </p>
            </div>

            {/* KPI 2: Interview Schedules */}
            <div
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xs hover:shadow-md hover:border-purple-200 transition-all duration-200"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                  Interviews
                </span>
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
                  <Calendar size={18} />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {activeInterviews.length}
                </span>
                <span className="text-xs font-bold text-purple-600">Upcoming</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                {activeInterviews.length > 0 ? 'Sessions pending evaluation' : 'No sessions pending'}
              </p>
            </div>

            {/* KPI 3: Saved Roles */}
            <div
              onClick={() => navigate('/candidate/findjobs')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xs hover:shadow-md hover:border-amber-200 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                  Saved Jobs
                </span>
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-amber-50 group-hover:bg-amber-100 text-amber-600 flex items-center justify-center transition-colors">
                  <Bookmark size={18} className={bookmarkedCount > 0 ? "fill-amber-500" : ""} />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  {bookmarkedCount}
                </span>
                <span className="text-xs font-bold text-slate-400">Bookmarked</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                Saved for quick application
              </p>
            </div>

            {/* KPI 4: Profile Strength */}
            <div
              onClick={() => navigate('/candidate/settings')}
              className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xs hover:shadow-md hover:border-emerald-200 transition-all duration-200 cursor-pointer group"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                  Readiness
                </span>
                <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-emerald-50 group-hover:bg-emerald-100 text-emerald-600 flex items-center justify-center transition-colors">
                  <ShieldCheck size={18} />
                </div>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight font-mono">
                  85%
                </span>
                <span className="text-xs font-bold text-emerald-600">Strong</span>
              </div>
              <p className="text-[11px] text-slate-500 font-medium mt-1 truncate">
                Candidate ATS matching rating
              </p>
            </div>

          </div>

          {/* DRAFT APPLICATION NOTICE */}
          {hasDraft && draftJobId && (
            <div className="bg-white border border-rose-200/80 rounded-[28px] p-5 sm:p-7 shadow-sm mb-8 sm:mb-10 relative overflow-hidden">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
                
                <div className="flex items-start gap-4">
                  <div className="w-11 h-11 rounded-2xl bg-rose-50 text-[#D10043] flex items-center justify-center shrink-0 border border-rose-100">
                    <Zap size={20} className="animate-pulse" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#D10043]">
                        Application In Progress
                      </span>
                      <span className="text-slate-300">•</span>
                      <span className="text-xs font-semibold text-slate-400">
                        {draftProgress.text}
                      </span>
                    </div>
                    <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight mt-0.5">
                      {draftJobTitle}
                    </h3>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">
                      Mariwasa Siam Ceramics • Complete your submission to proceed to recruitment review
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
                  <button
                    type="button"
                    onClick={handleDismissDraft}
                    title="Dismiss Draft"
                    className="p-3 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition-colors"
                  >
                    <X size={18} />
                  </button>

                  <button
                    type="button"
                    onClick={() => navigate(getDraftRoute())}
                    className="px-6 py-3 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center gap-2 transition-all shadow-md shadow-[#D10043]/20 active:scale-[0.98]"
                  >
                    Continue Application
                    <ChevronRight size={14} />
                  </button>
                </div>

              </div>
            </div>
          )}

          {/* MAIN 2-COLUMN DASHBOARD GRID */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 sm:gap-10">

            {/* LEFT 2 COLUMNS: APPLICATIONS & OPPORTUNITIES */}
            <div className="lg:col-span-2 space-y-8 sm:space-y-10">
              
              {/* Application List Component */}
              {isLoadingApps ? (
                <div className="bg-white border border-slate-200/80 rounded-[32px] p-8 shadow-sm space-y-4 animate-pulse">
                  <div className="h-6 bg-slate-200 rounded w-1/4 mb-6" />
                  <div className="h-28 bg-slate-50 rounded-2xl" />
                  <div className="h-28 bg-slate-50 rounded-2xl" />
                </div>
              ) : applications.length > 0 ? (
                <ApplicationList applications={applications} />
              ) : (
                <div className="bg-white border border-slate-200/80 rounded-[32px] p-8 sm:p-12 shadow-sm text-center space-y-5">
                  <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto text-slate-300 border border-slate-100">
                    <Briefcase size={32} />
                  </div>
                  <div className="max-w-md mx-auto space-y-2">
                    <h3 className="text-xl font-black text-slate-900 tracking-tight">No Active Applications</h3>
                    <p className="text-slate-500 text-xs sm:text-sm font-medium leading-relaxed">
                      You haven't submitted any job applications yet. Browse open positions across Mariwasa to jumpstart your career.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate('/candidate/findjobs')}
                    className="inline-flex items-center gap-2 px-7 py-3.5 bg-[#D10043] hover:bg-slate-900 text-white rounded-2xl font-black text-xs uppercase tracking-wider transition-all shadow-lg shadow-[#D10043]/20 active:scale-95"
                  >
                    <Search size={15} />
                    Explore Open Opportunities
                  </button>
                </div>
              )}

              {/* RECOMMENDED OPPORTUNITIES PROMO BANNER */}
              <div className="bg-white border border-slate-200/80 rounded-[32px] p-6 sm:p-8 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 relative overflow-hidden">
                <div className="space-y-1.5 max-w-lg">
                  <span className="text-[10px] font-black uppercase tracking-[0.2em] text-[#D10043] flex items-center gap-1.5">
                    <Sparkles size={12} />
                    Talent Discovery
                  </span>
                  <h4 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                    Explore More Roles Matching Your Profile
                  </h4>
                  <p className="text-slate-500 text-xs sm:text-sm font-medium leading-relaxed">
                    Mariwasa is actively recruiting across Manufacturing, Engineering, Quality Assurance, and Administrative divisions.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={() => navigate('/candidate/findjobs')}
                  className="px-6 py-3.5 rounded-2xl bg-slate-900 hover:bg-[#D10043] text-white font-black text-xs uppercase tracking-wider flex items-center gap-2 transition-all shrink-0 active:scale-[0.98]"
                >
                  Find Jobs <ArrowRight size={14} />
                </button>
              </div>

            </div>

            {/* RIGHT COLUMN: INTERVIEWS, PROFILE STRENGTH, QUICK ACTIONS */}
            <div className="space-y-8 sm:space-y-10">
              
              {/* Upcoming Interviews Schedule */}
              <UpcomingInterviews />

              {/* Profile Strength & ATS Completeness */}
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