import React from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  User, Mail, Phone, MapPin,
  Cpu, Briefcase, GraduationCap,
  CheckCircle, ArrowLeft, Edit3, Target
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

const CandidatePreviewAndVerify = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { jobId } = useParams();

  React.useEffect(() => {
    if (jobId) {
      localStorage.setItem('draft_application_step', '2');
      if (state?.job?.title) {
        localStorage.setItem('draft_application_job_title', state.job.title);
      }
      localStorage.setItem('draft_application_job_id', jobId);
    }
  }, [jobId, state]);

  const data = state?.extractedData;
  const matchData = state?.matchData;

  const extractedData = {
    personal: {
      name: data?.fullname || "Alex Thompson",
      email: data?.email || "alex.t@example.com",
      phone: data?.phone || "+1 (555) 000-1234",
      location: data?.location || "Chicago, IL"
    },
    skills: data?.skills ? data.skills.split(' | ').filter(Boolean) : ["Process Optimization", "Team Leadership", "Lean Manufacturing"],
    experience: {
      title: data?.experience ? data.experience.split('|')[0] : "Senior Operations Lead",
      company: state?.job?.title || "Global Tech Manufacturing",
      relevance: data?.years_experience ? `${data.years_experience}+ years of experience` : "7+ years in high-volume production environments"
    },
    education: {
      degree: data?.highest_degree || "B.S. in Industrial Engineering",
      college: data?.education ? data.education.split('|')[0] : "University of Illinois"
    },
    resumeUrl: data?.file_url
  };

  const getMatchColor = (pct) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const getMatchTier = (pct) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Verify Application | {state?.job?.title || 'Candidate Portal'}</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-7xl mx-auto px-6 py-12 flex-grow">

        <div className="flex justify-between items-end mb-8">
          <div>
            <button
              onClick={() => navigate(-1)}
              className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-4 font-semibold text-sm group"
            >
              <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
              Back to Upload
            </button>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
              {jobId ? "Review Profile Updates" : "AI Profile Analysis"}
            </h1>
            <p className="text-slate-500 font-medium">
              {jobId 
                ? `Verify the information extracted for your ${state?.job?.title || 'application'}.`
                : "Verify the information our AI extracted from your resume before we find your matches."
              }
            </p>
          </div>
          <div className="flex items-center gap-4 bg-white p-3 pr-6 rounded-2xl border border-slate-100 shadow-sm">
            <div className="w-16 h-16 rounded-xl bg-slate-50 border border-slate-100 overflow-hidden flex items-center justify-center text-slate-300">
              {localStorage.getItem('profile_image_url') ? (
                <img src={localStorage.getItem('profile_image_url')} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <User size={32} />
              )}
            </div>
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Application Identity</p>
              <p className="text-sm font-black text-slate-900">{extractedData.personal.name}</p>
            </div>
          </div>
          <button
            id="btn-edit-details"
            onClick={() => navigate(jobId ? `/candidate/update-profile/${jobId}` : '/candidate/update-profile', { state: { ...extractedData, fileName: state?.fileName, job: state?.job, matchData } })}
            className="flex items-center text-sm font-bold text-[#D60041] hover:underline bg-pink-50 px-4 py-2 rounded-xl transition-colors"
          >
            <Edit3 size={16} className="mr-2" /> Manual Edit
          </button>
        </div>

        <div className="space-y-6">

          {/* AI Match Analysis Section */}
          {matchData && (
            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow space-y-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Target size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">AI Match Analysis</h2>
                </div>
                <div className="bg-[#D60041] text-white px-5 py-2 rounded-2xl text-sm font-black shadow-lg shadow-pink-100">
                  {getMatchTier(matchData.match_percentage)}
                </div>
              </div>
              
              <div className="flex flex-col md:flex-row items-center gap-8">
                {/* Gauge */}
                <div className="flex flex-col items-center shrink-0">
                  <div className="relative w-32 h-32">
                    <svg className="w-32 h-32 -rotate-90" viewBox="0 0 100 100">
                      <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" strokeWidth="10" />
                      <circle
                        cx="50" cy="50" r="42" fill="none"
                        stroke={getMatchColor(matchData.match_percentage)}
                        strokeWidth="10"
                        strokeDasharray="264 264"
                        strokeLinecap="round"
                        className="transition-all duration-1000 ease-out"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-sm font-black text-slate-900 leading-none uppercase tracking-wider text-center px-2">Analyzed</span>
                    </div>
                  </div>
                  <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 mt-3">Overall Match</span>
                </div>

                {/* Sub-Scores */}
                <div className="flex-1 grid grid-cols-3 gap-3 w-full">
                  {[
                    { label: 'Skills', score: matchData.skills_score, color: 'text-blue-600', bgColor: 'bg-blue-50', icon: <Cpu size={14} /> },
                    { label: 'Experience', score: matchData.experience_score, color: 'text-purple-600', bgColor: 'bg-purple-50', icon: <Briefcase size={14} /> },
                    { label: 'Education', score: matchData.education_score, color: 'text-amber-600', bgColor: 'bg-amber-50', icon: <GraduationCap size={14} /> }
                  ].map((item, idx) => (
                    <div key={idx} className={`${item.bgColor} ${item.color} p-5 rounded-2xl border border-transparent hover:border-current/10 transition-all text-center group`}>
                      <div className="flex items-center justify-center mb-1 gap-1.5">
                        {item.icon}
                        <span className="text-[9px] font-black uppercase tracking-widest opacity-70 group-hover:opacity-100 transition-opacity">{item.label}</span>
                      </div>
                      <p className="text-lg font-black uppercase tracking-wider">
                        {item.score >= 70 ? 'High' : item.score >= 40 ? 'Medium' : 'Basic'}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Matched / Missing Skills */}
              {(matchData.matched_skills?.length > 0 || matchData.missing_skills?.length > 0) && (
                <div className="pt-6 border-t border-slate-50 space-y-4">
                  {matchData.matched_skills?.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[9px] font-black uppercase tracking-widest text-green-600 mr-2">Matched:</span>
                      {matchData.matched_skills.map((s, i) => (
                        <span key={i} className="px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-xs font-bold border border-green-100/50">{s}</span>
                      ))}
                    </div>
                  )}
                  {matchData.missing_skills?.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[9px] font-black uppercase tracking-widest text-red-500 mr-2">Missing:</span>
                      {matchData.missing_skills.map((s, i) => (
                        <span key={i} className="px-3 py-1.5 bg-red-50 text-red-600 rounded-lg text-xs font-bold border border-red-100/50">{s}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </section>
          )}

          <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-6 text-[#D60041]">
              <div className="p-2.5 bg-pink-50 rounded-xl">
                <User size={20} />
              </div>
              <h2 className="font-bold uppercase tracking-widest text-xs">Personal Information</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <InfoItem icon={<User size={16} />} label="Full Name" value={extractedData.personal.name} />
              <InfoItem icon={<Mail size={16} />} label="Email Address" value={extractedData.personal.email} />
              <InfoItem icon={<Phone size={16} />} label="Phone" value={extractedData.personal.phone} />
              <InfoItem icon={<MapPin size={16} />} label="Location" value={extractedData.personal.location} />
            </div>

            <div className="mt-8 pt-8 border-t border-slate-50">
              <div className="flex items-center gap-3 mb-4 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <Cpu size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Skills Found</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {extractedData.skills.map((skill, i) => (
                  <span key={i} className="px-4 py-2 bg-slate-50 text-slate-700 rounded-xl text-sm font-bold border border-slate-100 hover:border-slate-200 transition-colors cursor-default">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <Briefcase size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Latest Experience</h2>
              </div>
              <h4 className="font-black text-slate-900 mb-1">{extractedData.experience.title}</h4>
              <p className="text-sm font-bold text-slate-500 mb-4">{extractedData.experience.company}</p>
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                <p className="text-sm text-slate-600 leading-relaxed font-medium">{extractedData.experience.relevance}</p>
              </div>
            </section>

            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <GraduationCap size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Education</h2>
              </div>
              <h4 className="font-black text-slate-900 mb-1">{extractedData.education.degree}</h4>
              <p className="text-sm font-bold text-slate-500 bg-slate-50 inline-block px-3 py-1.5 rounded-lg border border-slate-100 mt-2">{extractedData.education.college}</p>
            </section>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 pt-6">
            <button
              onClick={() => navigate('/candidate/dashboard')}
              className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95"
            >
              Cancel Update
            </button>
            {!jobId ? (
              <button
                onClick={() => navigate('/candidate/smart-matches', { state: { matches: matchData, extractedData: data, fileName: state?.fileName } })}
                className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95"
              >
                <Target size={22} />
                View Recommended Jobs
              </button>
            ) : (
              <button
                onClick={() => navigate(`/candidate/update-profile/${jobId}`, { state: { ...extractedData, fileName: state?.fileName, job: state?.job, matchData } })}
                className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95"
              >
                <CheckCircle size={22} />
                Confirm & Save Profile Changes
              </button>
            )}
          </div>
        </div>
        </main>
      </div>
    </div>
  );
};

const InfoItem = ({ icon, label, value }) => (
  <div className="flex items-start gap-3 bg-slate-50 p-4 rounded-2xl border border-transparent hover:border-slate-100 transition-colors">
    <div className="mt-0.5 text-slate-400 bg-white p-1.5 rounded-lg shadow-sm border border-slate-100">
      {icon}
    </div>
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider mb-0.5">{label}</p>
      <p className="font-bold text-slate-800">{value}</p>
    </div>
  </div>
);

export default CandidatePreviewAndVerify;
