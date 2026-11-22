import styles from './HRDashboard.module.css';
import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from '@/utils/navigation';
import {
  Download, FileText, AlertCircle, Briefcase, BarChart3, Calendar,
  Sparkles, CheckCircle2, FolderArchive, Plus
} from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import KeyMetrics from '../../components/hr/dashboard/KeyMetrics';
import ApplicationTrends from '../../components/hr/dashboard/ApplicationTrends';
import RecentSubmissions from '../../components/hr/dashboard/RecentSubmissions';
import UpcomingInterviews from '../../components/hr/dashboard/UpcomingInterviews';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ChatWidget from '../../components/layout/ChatWidget';
import NewScheduleModal from '../../components/modals/hr/NewScheduleModal';

import {
  useGetDashboardStatsQuery,
  useGetDashboardTrendsQuery,
  useGetCandidateCountQuery,
  useGetResumeCountQuery,
  useGetJobsQuery,
  useGetApplicationsSummaryQuery,
  useGetAllInterviewsQuery
} from '../../redux/api/apiSlice';
import {
  exportDashboardAnalyticsToCSV,
  exportDashboardPDFWithFallback,
} from '../../utils/exportUtils';

const HRDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState<boolean>(false);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // RTK Query hooks with real-time WebSocket invalidation + lightweight stats-driven sync
  const { data: appStatsData } = useGetDashboardStatsQuery(undefined, {
    pollingInterval: 4000,
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    refetchOnReconnect: true,
  });
  const appStats = appStatsData ?? { pending: 0, reviewed: 0, accepted: 0, rejected: 0 };
  const { data: candidateCountData } = useGetCandidateCountQuery(undefined, {
    pollingInterval: 10000,
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    refetchOnReconnect: true,
  });
  const { data: resumeCountData } = useGetResumeCountQuery(undefined, {
    pollingInterval: 10000,
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    refetchOnReconnect: true,
  });
  const { data: jobs = [] } = useGetJobsQuery(undefined, {
    pollingInterval: 15000,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });
  const {
    data: applications = [],
    refetch: refetchApplications,
  } = useGetApplicationsSummaryQuery(undefined, {
    pollingInterval: 15000,
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    refetchOnReconnect: true,
  });
  useGetAllInterviewsQuery(undefined, {
    pollingInterval: 15000,
    refetchOnFocus: true,
    refetchOnReconnect: true,
  });
  const {
    data: trendsData,
    refetch: refetchTrends,
  } = useGetDashboardTrendsQuery(undefined, {
    pollingInterval: 15000,
    refetchOnFocus: true,
    refetchOnMountOrArgChange: true,
    refetchOnReconnect: true,
  });

  const activeJobsCount = jobs.filter((j: any) => j.is_active).length;
  const totalCandidates = candidateCountData?.count || applications.length || 0;
  const totalResumes = resumeCountData?.count || 0;
  const seenAppIdsRef = useRef<Set<string> | null>(null);
  const prevStatsSigRef = useRef<string | null>(null);

  useEffect(() => {
    if (!appStatsData) return;
    const sig = `${appStatsData.total ?? ''}:${appStatsData.pending ?? 0}:${appStatsData.reviewed ?? 0}:${appStatsData.accepted ?? 0}:${appStatsData.rejected ?? 0}`;
    if (prevStatsSigRef.current === null) {
      prevStatsSigRef.current = sig;
      return;
    }
    if (prevStatsSigRef.current !== sig) {
      prevStatsSigRef.current = sig;
      refetchApplications();
      refetchTrends();
    }
  }, [appStatsData, refetchApplications, refetchTrends]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  useEffect(() => {
    if (!Array.isArray(applications)) return;
    const currentIds = new Set(applications.map((a: any) => String(a.id)));
    if (seenAppIdsRef.current === null) {
      if (applications.length > 0) {
        seenAppIdsRef.current = currentIds;
      }
      return;
    }
    const newlyArrived = applications.filter((a: any) => !seenAppIdsRef.current!.has(String(a.id)));
    if (newlyArrived.length > 0) {
      const latest = newlyArrived[0];
      showToast(
        newlyArrived.length === 1
          ? `New application received: ${latest.name || 'Candidate'} (${latest.preferredJob || 'Role'})`
          : `${newlyArrived.length} new applications received`
      );
      seenAppIdsRef.current = currentIds;
    } else if (currentIds.size !== seenAppIdsRef.current.size) {
      seenAppIdsRef.current = currentIds;
    }
  }, [applications]);

  const buildExportPayload = () => ({
    applications,
    appStats,
    activeJobsCount,
    totalCandidates,
    totalResumes,
    trendsData,
  });

  const handleExportFullReport = () => {
    const { rowCount } = exportDashboardAnalyticsToCSV(buildExportPayload());
    showToast(`Exported analytics and ${rowCount} candidate records to CSV`);
  };

  const handleExportPdfReport = async () => {
    if (isExportingPdf) return;
    setIsExportingPdf(true);
    try {
      const { rowCount } = await exportDashboardPDFWithFallback(buildExportPayload());
      showToast(`Exported analytics and ${rowCount} candidate records to PDF`);
    } finally {
      setIsExportingPdf(false);
    }
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
        <title>Dashboard | Mariwasa Recruitment HR Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <div className="flex-1 min-w-0 flex flex-col">
          {/* Toast Notification */}
          {toastMessage && (
            <div role="status" className="fixed bottom-8 right-8 bg-slate-900 text-white px-5 py-3.5 rounded-2xl shadow-2xl flex items-center gap-3 text-xs font-bold z-50 border border-slate-800 animate-in fade-in slide-in-from-bottom-4 duration-300">
              <CheckCircle2 size={16} className="text-emerald-400" />
              <span>{toastMessage}</span>
            </div>
          )}

          <main className={styles.dashboard}>

            <header className={styles.pageHeader}>
              <div>
                <p className={styles.eyebrow}>MARIWASA / TALENT ACQUISITION</p>
                <h1>Recruitment overview</h1>
                <p className={styles.intro}>A clear view of your people, pipeline, and next steps.</p>
              </div>
              <div className={styles.reportActions} aria-label="Export reports">
                <button type="button" data-testid="btn-export-csv" onClick={handleExportFullReport} className={styles.secondaryButton}>
                  <Download size={16} /> Export CSV
                </button>
                <button type="button" data-testid="btn-export-pdf" onClick={handleExportPdfReport} disabled={isExportingPdf} className={styles.secondaryButton}>
                  <FileText size={16} /> {isExportingPdf ? 'Exporting…' : 'Export PDF'}
                </button>
              </div>
            </header>

            <section className={styles.welcome} aria-label="Recruitment workspace">
              <div className={styles.artwork} aria-hidden="true"><span /><span /><span /><span /></div>
              <div className={styles.welcomeContent}>
                <p className={styles.welcomeDate}><Calendar size={15} /> {currentDateFormatted}</p>
                <h2>Welcome back,<br /><span>{userName}.</span></h2>
                <p>Great teams start with the right connections.<br className="hidden sm:block" /> Find your next great hire, right here.</p>
                <div className={styles.welcomeActions}>
                  <button type="button" onClick={() => navigate('/hr/screeningportal')} className={styles.primaryButton}>
                    <Sparkles size={17} /> Screen applicants
                  </button>
                  <button type="button" onClick={() => setIsScheduleModalOpen(true)} className={styles.lightButton}>
                    <Plus size={17} /> Schedule interview
                  </button>
                </div>
              </div>
              <div className={styles.focusCard}>
                <span className={styles.focusLabel}>YOUR NEXT STEP</span>
                <div className={styles.focusValue}>{(appStats.pending ?? 0).toLocaleString()}</div>
                <h3>applications awaiting review</h3>
                <p>Give every new possibility a closer look.</p>
                <button type="button" onClick={() => navigate('/hr/screeningportal?status=SUBMITTED')}>Open review queue</button>
              </div>
            </section>

            <div className={styles.workspaceBar}>
              <span><span className={styles.statusDot} /> Recruitment workspace</span>
              <button type="button" onClick={() => navigate('/hr/physical-resumes')}><FolderArchive size={16} /> Import resumes</button>
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

            {/* 4. Operations Stack: Recent Submissions & Upcoming Interviews as Full-Width Rows */}
            <div className="space-y-6 sm:space-y-8 mb-8">
              <RecentSubmissions candidates={applications} />
              <UpcomingInterviews onScheduleClick={() => setIsScheduleModalOpen(true)} />
            </div>

            <section className={styles.tools} aria-labelledby="recruitment-tools-heading">
              <div className={styles.sectionHeading}>
                <h2 id="recruitment-tools-heading">Your recruitment toolkit</h2>
                <p>Everything you need to keep hiring moving.</p>
              </div>
              <div className={styles.toolGrid}>
                {[
                  { icon: AlertCircle, title: 'Review applications', description: 'Explore new submissions and candidate matches.', detail: `${appStats.pending} awaiting review`, path: '/hr/screeningportal?status=SUBMITTED' },
                  { icon: Calendar, title: 'Interview calendar', description: 'Coordinate conversations with your next great hire.', detail: 'Manage your schedule', path: '/hr/scheduling' },
                  { icon: Briefcase, title: 'Active positions', description: 'Keep your open roles and requirements up to date.', detail: `${activeJobsCount} open positions`, path: '/admin/jobmanagement' },
                  { icon: BarChart3, title: 'Compare candidates', description: 'Review skills and experience side by side.', detail: 'Explore candidate matches', path: '/hr/comparecandidates' },
                ].map(({ icon: Icon, title, description, detail, path }) => (
                  <button key={title} type="button" onClick={() => navigate(path)} className={styles.toolCard}>
                    <span className={styles.toolIcon}><Icon size={21} /></span>
                    <h3>{title}</h3>
                    <p>{description}</p>
                    <span className={styles.toolDetail}>{detail}</span>
                  </button>
                ))}
              </div>
            </section>

            {/* Floating Chat Widget */}
            <ChatWidget />

            {/* Quick Schedule Interview Modal */}
            {isScheduleModalOpen && (
              <NewScheduleModal
                isOpen={isScheduleModalOpen}
                onClose={() => setIsScheduleModalOpen(false)}
                onScheduled={(data) => {
                  showToast(`Interview scheduled for ${data.candidateName}! Notification sent.`);
                }}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
};

export default HRDashboard;
