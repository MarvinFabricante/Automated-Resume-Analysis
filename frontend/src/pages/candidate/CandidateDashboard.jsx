import React from 'react';
import { Helmet } from 'react-helmet-async';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

// Sub-components
import WelcomeHeader from '../../components/candidate/dashboard/WelcomeHeader';
import ApplicationList from '../../components/candidate/dashboard/ApplicationList';
import ProfileStrength from '../../components/candidate/dashboard/ProfileStrength';
import UpcomingInterviews from '../../components/candidate/dashboard/UpcomingInterviews';
import QuickActions from '../../components/candidate/dashboard/QuickActions';
import ChatWidget from '../../components/layout/ChatWidget';

import { Briefcase, Zap, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { useGetCandidateApplicationsQuery } from '../../redux/api/apiSlice';

const CandidateDashboard = () => {
  const navigate = useNavigate();
  const { user: email } = useSelector((state) => state.auth);
  const { data: applications = [], isLoading } = useGetCandidateApplicationsQuery(email, {
    skip: !email,
  });

  // Filter for active applications (optional, but requested "active applications")
  // For now, we'll show all and maybe limit to top 5 or something
  const activeApplications = applications.slice(0, 5);

  const draftStep = parseInt(localStorage.getItem('draft_application_step') || '1');
  const getDraftProgress = () => {
    if (draftStep === 1) return { text: "Upload Phase", width: "w-1/3" };
    if (draftStep === 2) return { text: "AI Verification", width: "w-2/3" };
    if (draftStep === 3) return { text: "Final Review", width: "w-[90%]" };
    return { text: "Incomplete", width: "w-1/4" };
  };
  const draftProgress = getDraftProgress();

  const getDraftRoute = () => {
    const jobId = localStorage.getItem('draft_application_job_id');
    if (draftStep === 2) return `/candidate/preview-profile/${jobId}`;
    if (draftStep === 3) return `/candidate/update-profile/${jobId}`;
    return `/candidate/upload-resume/${jobId}`;
  };

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - Candidate Dashboard</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-6 py-12 w-full flex-grow">

          <WelcomeHeader />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">

            <div className="lg:col-span-2 space-y-10 animate-in fade-in slide-in-from-left-6 duration-700">
              {isLoading ? (
                <div className="bg-white border border-slate-100 rounded-[40px] p-10 shadow-2xl shadow-slate-200/40 animate-pulse">
                  <div className="h-8 bg-slate-100 rounded-full w-48 mb-10"></div>
                  <div className="space-y-6">
                    <div className="h-32 bg-slate-50 rounded-[32px]"></div>
                    <div className="h-32 bg-slate-50 rounded-[32px]"></div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Draft Application / In Progress */}
                  {localStorage.getItem('draft_application_job_id') && (
                    <div className="bg-white border border-[#D10043]/20 rounded-[40px] p-8 shadow-xl shadow-pink-50 animate-in fade-in slide-in-from-bottom-4 duration-700">
                      <div className="flex items-center gap-4 mb-6">
                        <div className="p-3 bg-pink-50 text-[#D10043] rounded-2xl">
                          <Zap size={20} className="animate-pulse" />
                        </div>
                        <div>
                          <span className="text-[10px] font-black text-[#D10043] uppercase tracking-[0.2em] mb-1">Application In Progress</span>
                          <h3 className="text-xl font-black text-slate-900 tracking-tight">Finish your application</h3>
                        </div>
                      </div>

                      <div className="flex flex-col sm:flex-row justify-between items-center p-6 bg-slate-50 rounded-3xl border border-slate-100 gap-6">
                        <div>
                          <h4 className="text-lg font-black text-slate-900 leading-none mb-1">
                            {localStorage.getItem('draft_application_job_title')}
                          </h4>
                          <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Mariwasa Siam Ceramics</p>
                        </div>
                        <div className="flex-1 max-w-xs mx-4 hidden md:block">
                          <div className="flex justify-between text-[10px] font-black text-slate-400 uppercase tracking-[0.2em] mb-2">
                            <span>Process Stage</span>
                            <span className="text-[#D10043]">{draftProgress.text}</span>
                          </div>
                          <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                            <div className={`bg-[#D10043] ${draftProgress.width} h-full rounded-full animate-pulse transition-all duration-700`}></div>
                          </div>
                        </div>
                        <button
                          onClick={() => navigate(getDraftRoute())}
                          className="bg-[#D10043] whitespace-nowrap text-white px-6 py-3 rounded-xl font-black text-[10px] uppercase tracking-widest hover:bg-slate-900 transition-all flex items-center gap-2 group"
                        >
                          Continue Applying <ChevronRight size={14} className="group-hover:translate-x-1 transition-transform" />
                        </button>
                      </div>
                    </div>
                  )}

                  {activeApplications.length > 0 ? (
                    <ApplicationList applications={activeApplications} />
                  ) : (
                    <div className="bg-white border border-slate-100 rounded-[40px] p-10 shadow-2xl shadow-slate-200/40 text-center py-20">
                      <div className="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center mx-auto mb-6 text-slate-300">
                        <Briefcase size={40} />
                      </div>
                      <h3 className="text-xl font-black text-slate-900 mb-2">No Submitted Applications</h3>
                      <p className="text-slate-500 mb-8 max-w-sm mx-auto font-medium">
                        {localStorage.getItem('draft_application_job_id')
                          ? `You have one application in progress for ${localStorage.getItem('draft_application_job_title')}. Finish it to see it here.`
                          : "You haven't applied for any positions yet. Explore our career opportunities to get started."}
                      </p>
                      <button
                        onClick={() => navigate('/candidate/findjobs')}
                        className="bg-[#D10043] text-white px-8 py-3 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-slate-900 transition-all"
                      >
                        Find Jobs
                      </button>
                    </div>
                  )}
                </div>
              )}


            </div>

            <div className="space-y-10 animate-in fade-in slide-in-from-right-6 duration-700">
              <UpcomingInterviews />
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