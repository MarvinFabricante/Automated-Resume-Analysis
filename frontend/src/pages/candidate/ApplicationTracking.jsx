import React, { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { 
  ArrowLeft, 
  Briefcase, 
  MapPin, 
  Calendar, 
  CheckCircle2, 
  Circle,
  FileText,
  Download,
  ExternalLink,
  MessageSquare,
  AlertCircle,
  ChevronRight,
  Sparkles,
  ShieldCheck,
  Building2,
  Clock
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

const BRAND_RED = "#D10043";

const ApplicationTracking = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const application = state?.application;

  useEffect(() => {
    if (!application) {
      navigate('/candidate/dashboard');
    }
  }, [application, navigate]);

  if (!application) return null;

  const jobDetails = {
    role: application.role || application.originalData?.job_title || "Position",
    company: application.company || "Mariwasa Siam Ceramics",
    location: application.originalData?.location || "Sto. Tomas, Batangas",
    appliedDate: application.appliedDate || new Date().toLocaleDateString(),
    status: application.status || "Pending",
    statusColor: application.statusColor || "text-slate-600 bg-slate-50 border-slate-100",
  };

  const TIMELINE_STEPS = [
    {
      label: "Application Submitted",
      date: application.appliedDate,
      description: `Your application was successfully received by the recruitment team and assigned an ID #ARA-88${application.id}.`,
      status: "completed"
    },
    {
      label: "Initial Screening",
      date: application.step >= 2 ? "Completed" : "Pending",
      description: application.originalData?.match_score ? "Recruiter reviewed your profile and resume. Your skills were evaluated against our requirements." : "Recruiter is currently reviewing your profile and resume.",
      status: application.step >= 2 ? "completed" : (application.step === 1 ? "current" : "upcoming")
    },
    {
      label: "Technical Interview",
      date: application.step >= 3 ? "Completed" : "Pending",
      description: "Live coding and architectural discussion with the Engineering Lead.",
      status: application.step >= 3 ? "completed" : (application.step === 2 ? "current" : "upcoming")
    },
    {
      label: "Final Interview",
      date: application.step >= 4 ? "Completed" : "Pending",
      description: "Interview with the Head of Digital Transformation.",
      status: application.step >= 4 ? "completed" : (application.step === 3 ? "current" : "upcoming")
    },
    {
      label: "Job Offer",
      date: application.status === 'Accepted' ? "Completed" : application.status === 'Rejected' ? "Declined" : "Pending",
      description: application.status === 'Rejected' ? "We regret to inform you that we are not moving forward with your application at this time." : "Final decision and salary negotiation phase.",
      status: application.status === 'Accepted' ? "completed" : application.status === 'Rejected' ? "failed" : "upcoming"
    }
  ];

  const ATTACHMENTS = [
    { name: "Resume_Updated.pdf", size: "1.2 MB", date: application.appliedDate, type: "PDF" }
  ];

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - Application Tracking</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 max-w-[1400px] mx-auto px-6 py-12 w-full flex-grow">
        
        {/* Navigation & Header */}
        <div className="mb-12">
          <button onClick={() => navigate('/candidate/dashboard')} className="flex items-center text-xs font-black text-slate-400 uppercase tracking-widest hover:text-[#D10043] transition-colors mb-8 group">
            <ArrowLeft className="w-4 h-4 mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Dashboard
          </button>
          
          <div className="relative overflow-hidden bg-white border border-slate-100 p-10 rounded-[40px] shadow-2xl shadow-slate-200/50 animate-in fade-in slide-in-from-top-4 duration-700">
            <div className="absolute top-0 right-0 w-1/3 h-full bg-gradient-to-l from-pink-50/30 to-transparent pointer-events-none" />
            
            <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
              <div className="flex gap-8 items-center">
                <div className="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center border border-slate-100 shadow-sm group hover:bg-[#D10043]/5 transition-colors duration-500">
                  <Briefcase className="w-10 h-10 text-[#D10043]" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="bg-[#D10043]/10 text-[#D10043] text-[10px] font-black px-2 py-0.5 rounded-md uppercase tracking-wider">Active Process</span>
                    <span className="w-1 h-1 bg-slate-300 rounded-full" />
                    <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">ID: #ARA-88{application.id}</span>
                  </div>
                  <h1 className="text-3xl font-black text-slate-900 tracking-tight leading-none mb-4">{jobDetails.role}</h1>
                  <div className="flex flex-wrap gap-y-3 gap-x-6 text-xs text-slate-500 font-bold uppercase tracking-widest">
                    <span className="flex items-center"><Building2 className="w-4 h-4 mr-2 text-slate-300" /> {jobDetails.company}</span>
                    <span className="flex items-center"><MapPin className="w-4 h-4 mr-2 text-slate-300" /> {jobDetails.location}</span>
                    <span className="flex items-center"><Clock className="w-4 h-4 mr-2 text-slate-300" /> Applied {jobDetails.appliedDate}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center gap-4 bg-slate-50 p-4 rounded-3xl border border-slate-100">
                <div className="text-right mr-2 hidden sm:block">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Current Status</p>
                  <p className="text-sm font-black text-slate-900 tracking-tight">{jobDetails.status}</p>
                </div>
                <div className={`w-3 h-3 rounded-full ${
                  jobDetails.status === 'Accepted' ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)]' :
                  jobDetails.status === 'Rejected' ? 'bg-rose-500 shadow-[0_0_10px_rgba(244,63,94,0.5)]' :
                  jobDetails.status === 'Reviewed' ? 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]' :
                  'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.5)] animate-pulse'
                }`} />
                <button className="p-4 bg-white hover:bg-[#D10043] hover:text-white rounded-2xl shadow-sm border border-slate-100 transition-all active:scale-[0.95] text-slate-400">
                  <MessageSquare size={20} />
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          
          {/* Main Timeline Panel */}
          <div className="lg:col-span-2">
            <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40 animate-in fade-in slide-in-from-left-6 duration-700">
              <div className="flex items-center justify-between mb-12">
                <h3 className="text-xl font-black text-slate-900 tracking-tight">Application Journey</h3>
                <div className="flex items-center gap-2 bg-slate-50 px-4 py-2 rounded-xl text-[10px] font-black text-slate-500 uppercase tracking-widest border border-slate-100">
                  <Sparkles size={14} className="text-[#D10043]" />
                  AI Tracking Enabled
                </div>
              </div>
              
              <div className="relative ml-4">
                {TIMELINE_STEPS.map((step, index) => (
                  <div key={index} className="relative pl-14 pb-14 last:pb-0 group">
                    {/* Connection Line */}
                    {index !== TIMELINE_STEPS.length - 1 && (
                      <div className={`absolute left-[13px] top-8 bottom-0 w-0.5 ${step.status === 'completed' ? 'bg-[#D10043]/20' : 'bg-slate-100'} transition-colors duration-500`}></div>
                    )}
                    
                    {/* Status Indicator */}
                    <div className="absolute left-0 top-1 transition-transform duration-500 group-hover:scale-110">
                      {step.status === 'completed' ? (
                        <div className="bg-pink-50 w-7 h-7 rounded-full flex items-center justify-center border-4 border-white shadow-sm">
                          <CheckCircle2 className="w-4 h-4 text-[#D10043]" />
                        </div>
                      ) : step.status === 'failed' ? (
                        <div className="bg-rose-50 w-7 h-7 rounded-full flex items-center justify-center border-4 border-white shadow-sm">
                          <XCircle className="w-4 h-4 text-rose-500" />
                        </div>
                      ) : step.status === 'current' ? (
                        <div className="bg-white border-2 border-[#D10043] w-7 h-7 rounded-full flex items-center justify-center shadow-lg shadow-pink-100">
                          <div className="w-2.5 h-2.5 bg-[#D10043] rounded-full animate-ping"></div>
                        </div>
                      ) : (
                        <div className="bg-white border-2 border-slate-100 w-7 h-7 rounded-full flex items-center justify-center">
                          <div className="w-2 h-2 bg-slate-100 rounded-full"></div>
                        </div>
                      )}
                    </div>

                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
                      <div className="max-w-md">
                        <div className="flex items-center gap-3 mb-2">
                          <h4 className={`text-lg font-black tracking-tight ${step.status === 'upcoming' ? 'text-slate-300' : 'text-slate-900'}`}>
                            {step.label}
                          </h4>
                          {step.status === 'current' && (
                            <span className="bg-[#D10043] text-white text-[8px] font-black px-1.5 py-0.5 rounded-md uppercase tracking-widest">Active</span>
                          )}
                        </div>
                        <p className={`text-sm font-medium leading-relaxed ${step.status === 'upcoming' ? 'text-slate-300' : 'text-slate-500'}`}>
                          {step.description}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className={`text-[10px] font-black uppercase tracking-[0.2em] whitespace-nowrap px-3 py-1 rounded-lg ${step.status === 'upcoming' ? 'text-slate-200 bg-slate-50/50' : 'text-[#D10043] bg-pink-50/50'}`}>
                          {step.date}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar Section */}
          <div className="space-y-10 animate-in fade-in slide-in-from-right-6 duration-700">
            
            {/* Documents Card */}
            <div className="bg-white border border-slate-100 rounded-[40px] p-10 shadow-xl shadow-slate-200/40">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-lg font-black text-slate-900 tracking-tight">Documents</h3>
                <button className="text-[10px] font-black text-[#D10043] uppercase tracking-widest hover:underline decoration-2 underline-offset-4">Upload New</button>
              </div>
              <div className="space-y-4">
                {ATTACHMENTS.map((doc, idx) => (
                  <div key={idx} className="flex items-center justify-between p-5 rounded-3xl border border-slate-50 bg-slate-50/50 group hover:border-[#D10043]/20 hover:bg-white transition-all duration-300">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-slate-300 group-hover:text-[#D10043] border border-slate-100 transition-colors">
                        <FileText size={18} />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-black text-slate-800 truncate">{doc.name}</p>
                        <p className="text-[9px] text-slate-400 font-black uppercase tracking-widest mt-0.5">{doc.type} • {doc.size}</p>
                      </div>
                    </div>
                    <button className="p-2.5 hover:bg-slate-50 rounded-xl transition-all text-slate-300 hover:text-slate-900 border border-transparent hover:border-slate-100">
                      <Download size={16} />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Smart Reminder Card */}
            <div className="bg-slate-900 rounded-[40px] p-10 shadow-2xl shadow-slate-900/20 overflow-hidden relative group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#D10043]/10 rounded-full blur-3xl -mr-16 -mt-16 group-hover:scale-150 transition-transform duration-700" />
              
              <div className="relative z-10">
                <div className="flex items-center gap-3 mb-6">
                  <div className="p-3 bg-orange-500/10 rounded-2xl">
                    <AlertCircle className="w-5 h-5 text-orange-500" />
                  </div>
                  <h3 className="font-black text-white text-sm uppercase tracking-widest">Priority Task</h3>
                </div>
                
                <p className="text-sm text-slate-400 leading-relaxed font-bold mb-8">
                  {application.status === 'Rejected' ? (
                    <span>Thank you for applying. We appreciate the time you invested. While we cannot proceed at this time, we will keep your profile in our talent pool for <span className="text-white">future openings</span>.</span>
                  ) : application.status === 'Accepted' ? (
                    <span>Congratulations! You have been offered the position. Please review the <span className="text-white">Job Offer</span> details and reach out to the recruiter.</span>
                  ) : (
                    <>
                      {application.step === 1 && <span>Your application is currently <span className="text-white">under review</span>. Keep your profile updated to stand out.</span>}
                      {application.step === 2 && <span>Great news! You passed the initial screening. <span className="text-white">Next steps</span> will be communicated soon.</span>}
                      {application.step === 3 && <span>Your Technical Interview is confirmed. <span className="text-white">Please prepare</span> your environment for the session.</span>}
                      {application.step >= 4 && <span>Your final stages are complete. We will reach out with a <span className="text-white">final decision</span> shortly.</span>}
                    </>
                  )}
                </p>
                
                <div className="space-y-3">
                  <button className="w-full py-4 bg-[#D10043] hover:bg-white hover:text-slate-900 text-white rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-2 group/btn shadow-lg shadow-pink-900/20">
                    {application.step === 3 ? (
                      <>Check Environment <ExternalLink size={12} className="group-hover/btn:translate-x-1 group-hover/btn:-translate-y-1 transition-transform" /></>
                    ) : (
                      <>View Status Details <ChevronRight size={12} className="group-hover/btn:translate-x-1 transition-transform" /></>
                    )}
                  </button>
                  <div className="flex items-center justify-center gap-2 text-[9px] font-black text-slate-500 uppercase tracking-widest pt-2">
                    <ShieldCheck size={12} className="text-green-500" />
                    Twilio AI Confirmed
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

export default ApplicationTracking;