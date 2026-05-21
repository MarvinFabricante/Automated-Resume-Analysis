import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Download, AlertCircle, Briefcase, BarChart3 } from 'lucide-react';
import { Helmet } from 'react-helmet-async';
import KeyMetrics from '../../components/hr/dashboard/KeyMetrics';
import ApplicationTrends from '../../components/hr/dashboard/ApplicationTrends';
import RecentSubmissions from '../../components/hr/dashboard/RecentSubmissions';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

import {
  useGetDashboardStatsQuery,
  useGetCandidateCountQuery,
  useGetResumeCountQuery,
  useGetJobsQuery,
  useGetApplicationsQuery
} from '../../redux/api/apiSlice';
import ChatWidget from '../../components/layout/ChatWidget';
import { exportToCSV } from '../../utils/exportUtils';

const HRDashboard = () => {
  const navigate = useNavigate();

  // Use RTK Query hooks instead of useEffect/axios
  const { data: appStats = { pending: 0, reviewed: 0, accepted: 0, rejected: 0 }, isLoading: isStatsLoading } = useGetDashboardStatsQuery();
  const { data: candidateCountData, isLoading: isCandidateLoading } = useGetCandidateCountQuery();
  const { data: resumeCountData, isLoading: isResumeLoading } = useGetResumeCountQuery();
  const { data: jobs = [], isLoading: isJobsLoading } = useGetJobsQuery();
  const { data: applications = [], isLoading: isAppsLoading } = useGetApplicationsQuery();

  const activeJobsCount = jobs.filter(j => j.is_active).length;
  const totalCandidates = candidateCountData?.count || 0;
  const totalResumes = resumeCountData?.count || 0;

  // Get the 5 most recent applications
  const recentCandidates = [...applications]
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 5);

  const isLoading = isStatsLoading || isCandidateLoading || isResumeLoading || isJobsLoading || isAppsLoading;

  return (
    <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
      <Helmet>
        <title>Dashboard | Mariwasa ARAS</title>
      </Helmet>
      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <div className="flex-1">
          {isLoading && (
            <div className="fixed inset-0 bg-white/60 backdrop-blur-sm z-[999] flex items-center justify-center">
              <div className="flex flex-col items-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#D60041] mb-4"></div>
                <p className="text-sm font-bold text-gray-600 animate-pulse">Syncing dashboard data...</p>
              </div>
            </div>
          )}

          <main className="w-full max-w-full px-4 sm:px-6 md:px-10 py-6 md:py-8">

            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 md:mb-10 gap-6">
              <div>
                <h2 className="text-2xl md:text-3xl font-black tracking-tight text-gray-900 leading-tight">
                  Dashboard Overview
                </h2>
                <p className="text-sm text-gray-500 font-medium tracking-wide mt-1">
                  Live recruitment analytics from database
                </p>
              </div>

              <div className="flex items-center gap-3 w-full sm:w-auto overflow-x-auto pb-2 sm:pb-0 scrollbar-hide">
                <button className="whitespace-nowrap bg-white border border-gray-200 px-4 py-2 rounded-xl hover:border-pink-100 hover:text-[#D60041] hover:bg-pink-50 transition-all duration-300 text-[11px] md:text-xs font-bold text-gray-700 flex items-center shadow-sm shrink-0">
                  Real-time
                  <div className="w-2 h-2 bg-green-500 rounded-full ml-2 animate-pulse"></div>
                </button>

                <button 
                  onClick={() => exportToCSV(applications, `Recruitment_Report_${new Date().toISOString().split('T')[0]}`)}
                  className="whitespace-nowrap bg-white border border-gray-200 px-4 py-2 rounded-xl hover:border-pink-100 hover:text-[#D60041] hover:bg-pink-50 transition-all duration-300 text-[11px] md:text-xs font-bold text-gray-700 flex items-center shadow-sm group shrink-0"
                >
                  <Download className="h-4 w-4 mr-2 text-gray-400 group-hover:text-[#D60041]" />
                  Export Report
                </button>
              </div>
            </div>

            <KeyMetrics
              activeJobsCount={activeJobsCount}
              totalCandidates={totalCandidates}
              totalResumes={totalResumes}
              appStats={appStats}
            />
            <ApplicationTrends />
            <RecentSubmissions candidates={recentCandidates} />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

              <div
                onClick={() => navigate('/screening')}
                className="bg-white border border-gray-100 rounded-[32px] p-8 lg:p-10 shadow-sm hover:-translate-y-1 hover:shadow-xl hover:border-orange-100 transition-all duration-300 cursor-pointer flex flex-col items-start gap-6 group"
              >
                <div className="w-14 h-14 bg-gradient-to-br from-orange-50 to-orange-100/50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                  <AlertCircle className="text-orange-500 h-6 w-6" />
                </div>
                <div>
                  <h4 className="text-xl font-bold tracking-tight text-gray-900 group-hover:text-orange-600 transition-colors">
                    Pending Reviews
                  </h4>
                  <p className="text-sm text-gray-500 font-bold mt-2">
                    {appStats.pending} applications waiting
                  </p>
                </div>
              </div>

              <div
                onClick={() => navigate('/jobs')}
                className="bg-white border border-gray-100 rounded-[32px] p-8 lg:p-10 shadow-sm hover:-translate-y-1 hover:shadow-xl hover:border-pink-100 transition-all duration-300 cursor-pointer flex flex-col items-start gap-6 group"
              >
                <div className="w-14 h-14 bg-gradient-to-br from-pink-50 to-red-50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                  <Briefcase className="text-[#D60041] h-6 w-6" />
                </div>
                <div>
                  <h4 className="text-xl font-bold tracking-tight text-gray-900 group-hover:text-[#D60041] transition-colors">
                    Active Positions
                  </h4>
                  <p className="text-sm text-gray-500 font-bold mt-2">
                    {activeJobsCount} roles currently open
                  </p>
                </div>
              </div>

              <div className="bg-white border border-gray-100 rounded-[32px] p-8 lg:p-10 shadow-sm hover:-translate-y-1 hover:shadow-xl hover:border-blue-100 transition-all duration-300 cursor-pointer flex flex-col items-start gap-6 group">
                <div className="w-14 h-14 bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300 shadow-inner">
                  <BarChart3 className="text-blue-500 h-6 w-6" />
                </div>
                <div>
                  <h4 className="text-xl font-bold tracking-tight text-gray-900 group-hover:text-blue-600 transition-colors">
                    Department Reports
                  </h4>
                  <p className="text-sm text-gray-500 font-bold mt-2">
                    Detailed analytics & history
                  </p>
                </div>
              </div>

            </div>
            <ChatWidget />
          </main>
        </div>
      </div>
    </div>
  );
};

export default HRDashboard;