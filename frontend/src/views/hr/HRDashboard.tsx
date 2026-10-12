import React, { useState } from 'react';
import { useNavigate } from '@/utils/navigation';
import { 
  Download, AlertCircle, Briefcase, BarChart3, Calendar, 
  RefreshCw, Sparkles, CheckCircle2, ChevronRight
} from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import KeyMetrics from '../../components/hr/dashboard/KeyMetrics';
import ApplicationTrends from '../../components/hr/dashboard/ApplicationTrends';
import RecentSubmissions from '../../components/hr/dashboard/RecentSubmissions';
import UpcomingInterviews from '../../components/hr/dashboard/UpcomingInterviews';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ChatWidget from '../../components/layout/ChatWidget';
import ScheduleInterviewModal from '../../components/modals/hr/ScheduleInterviewModal';

import {
  useGetDashboardStatsQuery,
  useGetCandidateCountQuery,
  useGetResumeCountQuery,
  useGetJobsQuery,
  useGetApplicationsQuery,
  useGetAllInterviewsQuery
} from '../../redux/api/apiSlice';
import { exportToCSV } from '../../utils/exportUtils';

const HRDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // RTK Query hooks
  const { data: appStats = { pending: 0, reviewed: 0, accepted: 0, rejected: 0 }, refetch: refetchStats } = useGetDashboardStatsQuery();
  const { data: candidateCountData, refetch: refetchCandidates } = useGetCandidateCountQuery();
  const { data: resumeCountData, refetch: refetchResumes } = useGetResumeCountQuery();
  const { data: jobs = [], refetch: refetchJobs } = useGetJobsQuery();
  const { data: applications = [], refetch: refetchApps } = useGetApplicationsQuery();
  const { refetch: refetchInterviews } = useGetAllInterviewsQuery();

  const activeJobsCount = jobs.filter((j: any) => j.is_active).length;
  const totalCandidates = candidateCountData?.count || applications.length || 0;
  const totalResumes = resumeCountData?.count || 0;

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handleRefreshAll = async () => {
    setIsRefreshing(true);
    try {
      await Promise.allSettled([
        refetchStats?.(),
        refetchCandidates?.(),
        refetchResumes?.(),
        refetchJobs?.(),
        refetchApps?.(),
        refetchInterviews?.()
      ]);
      showToast('Dashboard analytics synchronized with live database');
    } catch {
      showToast('Dashboard data updated');
    } finally {
      setTimeout(() => setIsRefreshing(false), 600);
    }
  };

  const handleExportFullReport = () => {
    if (!applications.length) {
      alert('No application data available to export.');
      return;
    }
    const reportData = applications.map((app: any) => ({
      ID: app.id,
      CandidateName: app.name,
      PreferredRole: app.preferredJob,
      Department: app.jobDepartment || 'General',
      Status: app.status,
      MatchScore: `${app.matchScore || 0}%`,
      SkillsScore: `${app.skillsScore || 0}%`,
      ExperienceScore: `${app.experienceScore || 0}%`,
      EducationScore: `${app.educationScore || 0}%`,
      ApplicationDate: app.date ? new Date(app.date).toISOString().split('T')[0] : 'N/A',
      Location: app.location || 'N/A'
    }));

    exportToCSV(reportData, `Mariwasa_HR_Recruitment_Report_${new Date().toISOString().split('T')[0]}`);
    showToast(`Exported ${reportData.length} candidate records to CSV`);
  };

  const userName = localStorage.getItem('fullname') || 'Recruitment Team';
  const currentDateFormatted = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  return (
    <div className="bg-[#F8FAFC] text-slate-800 antialiased min-h-screen font-sans flex flex-col selection:bg-rose-100 selection:text-[#D60041]">
      <Helmet>
        <title>HR Dashboard | Mariwasa ARAS</title>
      </Helmet>
      
      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <div className="flex-1 min-w-0 flex flex-col">
          {/* Toast Notification */}
          {toastMessage && (
            <div className="fixed bottom-8 right-8 bg-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-2xl flex items-center gap-3 text-xs font-bold z-50 border border-slate-800 animate-in fade-in slide-in-from-bottom-4 duration-300">
              <CheckCircle2 size={16} className="text-emerald-400" />
              <span>{toastMessage}</span>
            </div>
          )}

          {/* Sync Progress Bar */}
          {isRefreshing && (
            <div className="h-1 w-full bg-slate-100 overflow-hidden sticky top-0 z-40">
              <div className="h-full bg-gradient-to-r from-rose-500 to-[#D60041] animate-pulse w-full"></div>
            </div>
          )}

          <main className="w-full max-w-full px-3.5 sm:px-6 md:px-8 lg:px-10 py-4 sm:py-6 md:py-8">

            {/* 1. Executive Command Banner */}
            <div className="relative mb-6 sm:mb-8 p-4 sm:p-6 md:p-8 bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl shadow-xs overflow-hidden">
              {/* Subtle ambient brand mesh background */}
              <div className="absolute top-0 right-0 w-96 h-96 bg-gradient-to-bl from-rose-50/70 via-pink-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

              <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-5 sm:gap-6 relative z-10">
                <div>
                  <div className="flex items-center gap-2 sm:gap-3 mb-1.5 sm:mb-2 flex-wrap">
                    <span className="px-2.5 sm:px-3 py-1 rounded-full text-[10px] sm:text-[11px] font-black uppercase tracking-wider bg-rose-50 text-[#D60041] border border-rose-100/90 flex items-center gap-1.5 shadow-2xs shrink-0">
                      <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-[#D60041] animate-pulse" />
                      <span className="sm:hidden">ATS Engine Active</span>
                      <span className="hidden sm:inline">Mariwasa ATS Engine Active</span>
                    </span>
                    <span className="text-[11px] sm:text-xs text-slate-500 font-semibold flex items-center gap-1.5">
                      <span className="text-slate-300 font-bold">•</span>
                      <span>{currentDateFormatted}</span>
                    </span>
                  </div>

                  <h1 className="text-xl sm:text-2xl md:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
                    Welcome back, <span className="text-[#D60041]">{userName}</span>
                  </h1>
                  <p className="text-[11px] sm:text-xs md:text-sm text-slate-500 font-medium mt-1 max-w-2xl leading-relaxed">
                    Live recruitment analytics, automated resume parsing, and candidate evaluation pipeline.
                  </p>
                </div>

                {/* Command Actions Bar */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-2 w-full lg:w-auto">
                  {/* Primary Screening Action */}
                  <button
                    onClick={() => navigate('/hr/screeningportal')}
                    className="w-full sm:w-auto px-4 py-2.5 sm:py-2.5 bg-gradient-to-r from-rose-600 to-[#D60041] hover:from-rose-700 hover:to-[#b50037] text-white rounded-2xl text-xs font-black uppercase tracking-wider transition-all shadow-md shadow-pink-900/20 flex items-center justify-center gap-2 active:scale-95 sm:order-last min-h-[42px]"
                  >
                    <Sparkles size={15} />
                    <span>Screen Applicants</span>
                  </button>

                  {/* Secondary Action Row for Mobile / Inline on Desktop */}
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    {/* Quick Schedule Interview */}
                    <button
                      onClick={() => setIsScheduleModalOpen(true)}
                      className="flex-1 sm:flex-none px-3 sm:px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1.5 sm:gap-2 active:scale-95 min-h-[42px] truncate"
                    >
                      <Calendar size={15} className="shrink-0" />
                      <span className="truncate">Schedule</span>
                    </button>

                    {/* Export CSV Report */}
                    <button
                      onClick={handleExportFullReport}
                      className="flex-1 sm:flex-none px-3 sm:px-4 py-2.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200/90 rounded-2xl text-xs font-bold transition-all shadow-2xs flex items-center justify-center gap-1.5 sm:gap-2 group active:scale-95 min-h-[42px] truncate"
                    >
                      <Download size={15} className="text-slate-400 group-hover:text-[#D60041] transition-colors shrink-0" />
                      <span className="truncate">Export CSV</span>
                    </button>

                    {/* Refresh live sync button */}
                    <button
                      onClick={handleRefreshAll}
                      disabled={isRefreshing}
                      className="p-2.5 bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200/80 rounded-2xl transition-all shadow-2xs active:scale-95 disabled:opacity-50 shrink-0 min-h-[42px] min-w-[42px] flex items-center justify-center"
                      title="Refresh Live Data Feed"
                    >
                      <RefreshCw size={16} className={isRefreshing ? 'animate-spin text-[#D60041]' : ''} />
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* 2. Key Metrics Section */}
            <KeyMetrics
              activeJobsCount={activeJobsCount}
              totalCandidates={totalCandidates}
              totalResumes={totalResumes}
              appStats={appStats}
              applications={applications}
            />

            {/* 3. Application Trends & Pipeline Distribution Analytics */}
            <ApplicationTrends 
              applications={applications} 
              appStats={appStats} 
            />

            {/* 4. Split Operations Grid: Recent Submissions (2/3) + Upcoming Interviews (1/3) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8 mb-8">
              {/* Left 2 Cols: Interactive Recent Submissions Queue */}
              <div className="lg:col-span-2">
                <RecentSubmissions candidates={applications} />
              </div>

              {/* Right 1 Col: Live Upcoming Interviews Widget */}
              <div className="lg:col-span-1">
                <UpcomingInterviews onScheduleClick={() => navigate('/hr/scheduling')} />
              </div>
            </div>

            {/* 5. Executive Module Navigation Hub (Bento Grid) */}
            <div className="mb-8">
              <div className="mb-4">
                <h3 className="text-lg font-extrabold text-slate-900 tracking-tight">
                  Recruitment Operations & Tools
                </h3>
                <p className="text-xs text-slate-500 font-medium">
                  Direct shortcuts to candidate evaluation workflows and management modules
                </p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-5">
                {/* 1. Pending Reviews */}
                <div
                  onClick={() => navigate('/hr/screeningportal?status=PENDING')}
                  className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4.5 sm:p-5 lg:p-6 shadow-xs hover:-translate-y-1 hover:shadow-xl hover:border-amber-200 transition-all duration-300 cursor-pointer flex flex-col justify-between group"
                >
                  <div className="flex justify-between items-start mb-3 sm:mb-4">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-amber-50 rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                      <AlertCircle className="text-amber-500 h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200/60">
                      {appStats.pending} Waiting
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm sm:text-base lg:text-lg font-extrabold tracking-tight text-slate-900 group-hover:text-amber-600 transition-colors flex items-center justify-between">
                      <span>Pending Reviews</span>
                      <ChevronRight size={16} className="text-slate-400 group-hover:translate-x-1 group-hover:text-amber-600 transition-all" />
                    </h4>
                    <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-1 leading-relaxed">
                      Evaluate newly submitted resumes with automated ATS match analysis.
                    </p>
                  </div>
                </div>

                {/* 2. Interview Scheduling */}
                <div
                  onClick={() => navigate('/hr/scheduling')}
                  className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4.5 sm:p-5 lg:p-6 shadow-xs hover:-translate-y-1 hover:shadow-xl hover:border-pink-200 transition-all duration-300 cursor-pointer flex flex-col justify-between group"
                >
                  <div className="flex justify-between items-start mb-3 sm:mb-4">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-rose-50 rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                      <Calendar className="text-[#D60041] h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-rose-50 text-[#D60041] border border-rose-200/60">
                      Calendar Sync
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm sm:text-base lg:text-lg font-extrabold tracking-tight text-slate-900 group-hover:text-[#D60041] transition-colors flex items-center justify-between">
                      <span>Interview Scheduling</span>
                      <ChevronRight size={16} className="text-slate-400 group-hover:translate-x-1 group-hover:text-[#D60041] transition-all" />
                    </h4>
                    <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-1 leading-relaxed">
                      Google Calendar synchronized slots, panel interviewers, and invitations.
                    </p>
                  </div>
                </div>

                {/* 3. Active Positions */}
                <div
                  onClick={() => navigate('/admin/jobmanagement')}
                  className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4.5 sm:p-5 lg:p-6 shadow-xs hover:-translate-y-1 hover:shadow-xl hover:border-blue-200 transition-all duration-300 cursor-pointer flex flex-col justify-between group"
                >
                  <div className="flex justify-between items-start mb-3 sm:mb-4">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-blue-50 rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                      <Briefcase className="text-blue-600 h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200/60">
                      {activeJobsCount} Open
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm sm:text-base lg:text-lg font-extrabold tracking-tight text-slate-900 group-hover:text-blue-600 transition-colors flex items-center justify-between">
                      <span>Active Positions</span>
                      <ChevronRight size={16} className="text-slate-400 group-hover:translate-x-1 group-hover:text-blue-600 transition-all" />
                    </h4>
                    <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-1 leading-relaxed">
                      Manage job requisitions, requirements, and active hiring openings.
                    </p>
                  </div>
                </div>

                {/* 4. Compare Candidates */}
                <div
                  onClick={() => navigate('/hr/comparecandidates')}
                  className="bg-white border border-slate-200/80 rounded-2xl sm:rounded-3xl p-4.5 sm:p-5 lg:p-6 shadow-xs hover:-translate-y-1 hover:shadow-xl hover:border-purple-200 transition-all duration-300 cursor-pointer flex flex-col justify-between group"
                >
                  <div className="flex justify-between items-start mb-3 sm:mb-4">
                    <div className="w-10 h-10 sm:w-12 sm:h-12 bg-purple-50 rounded-xl sm:rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                      <BarChart3 className="text-purple-600 h-5 w-5 sm:h-6 sm:w-6" />
                    </div>
                    <span className="text-[9px] sm:text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 border border-purple-200/60">
                      Matrix
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm sm:text-base lg:text-lg font-extrabold tracking-tight text-slate-900 group-hover:text-purple-600 transition-colors flex items-center justify-between">
                      <span>Compare Candidates</span>
                      <ChevronRight size={16} className="text-slate-400 group-hover:translate-x-1 group-hover:text-purple-600 transition-all" />
                    </h4>
                    <p className="text-[11px] sm:text-xs text-slate-500 font-medium mt-1 leading-relaxed">
                      Side-by-side comparative analysis of skills, experience, and ATS matches.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Floating Chat Widget */}
            <ChatWidget />

            {/* Quick Schedule Interview Modal */}
            {isScheduleModalOpen && (
              <ScheduleInterviewModal
                isOpen={isScheduleModalOpen}
                onClose={() => setIsScheduleModalOpen(false)}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default HRDashboard;
