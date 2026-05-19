import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Briefcase,
  MapPin,
  Clock,
  ArrowRight,
  CircleDot,
  Target,
  Cpu,
  GraduationCap
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

const CandidateSmartMatchResult = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { matches, extractedData, fileName } = location.state || {};

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!matches) {
      navigate('/candidate/upload-resume');
    }
  }, [matches, navigate]);

  const sortedMatches = matches ? [...matches].sort((a, b) => b.match_percentage - a.match_percentage) : [];

  const getMatchColor = (pct) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] min-h-screen flex flex-col">
      <Helmet>
        <title>Career Matches | Candidate Portal</title>
      </Helmet>
      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-grow max-w-[1400px] mx-auto px-6 py-12 w-full">
          <div className="text-center mb-16 relative animate-in fade-in slide-in-from-top-6 duration-700">
            <div className="inline-block p-1.5 rounded-full bg-white shadow-sm border border-slate-100 mb-8">
              <div className="flex items-center gap-3 px-3 py-1 text-[#D60041]">
                <Target size={16} />
                <span className="text-xs font-semibold uppercase tracking-wider">AI Analysis Result</span>
              </div>
            </div>
            <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 mb-6">
              Your Best Career <span className="text-[#D60041]">Matches</span>
            </h1>
            <p className="text-slate-500 text-lg max-w-2xl mx-auto font-medium leading-relaxed">
              We've analyzed your profile against our open positions. Here are the roles where your skills will shine the most.
            </p>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-12 items-stretch animate-in fade-in slide-in-from-bottom-6 duration-700 delay-200">
            {sortedMatches.length > 0 ? (
              sortedMatches.map((match) => (
                <div 
                  key={match.job_id}
                  onClick={() => navigate(`/candidate/preview-profile/${match.job_id}`, { state: { job: { job_id: match.job_id, title: match.job_title, department: match.department, location: match.location, job_type: match.job_type }, extractedData, matchData: match, fileName } })}
                  className="bg-white p-8 rounded-[40px] border border-slate-100 shadow-xl shadow-slate-200/40 hover:shadow-2xl hover:shadow-pink-100/50 transition-all duration-500 group flex flex-col relative overflow-hidden cursor-pointer active:scale-[0.99]"
                >
                  <div className="absolute top-0 right-0 w-48 h-48 bg-[#D60041]/5 rounded-bl-[100px] opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

                  <div className="flex justify-between items-start mb-8 relative z-10">
                    <div className="flex-1 pr-4">
                      <div className="flex items-center gap-2 mb-4">
                        <span className="inline-block px-3 py-1 rounded-full bg-slate-100 text-[9px] font-black uppercase tracking-widest text-slate-500 group-hover:bg-pink-50 group-hover:text-[#D60041] transition-colors">
                          {match.department}
                        </span>
                        <span className="inline-block px-3 py-1 rounded-full bg-green-50 text-[9px] font-black uppercase tracking-widest text-green-600">
                          Active Role
                        </span>
                      </div>
                      <h3 className="text-2xl font-black text-slate-900 group-hover:text-[#D60041] transition-colors leading-tight tracking-tight mb-2">
                        {match.job_title}
                      </h3>
                      <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Mariwasa Siam Ceramics</p>
                    </div>
                    
                    {/* Gauge */}
                    <div className="flex flex-col items-center shrink-0">
                      <div className="relative w-20 h-20">
                        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 100 100">
                          <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" strokeWidth="12" />
                          <circle
                            cx="50" cy="50" r="42" fill="none"
                            stroke={getMatchColor(match.match_percentage)}
                            strokeWidth="12"
                            strokeDasharray="264 264"
                            strokeLinecap="round"
                            className="transition-all duration-1000 ease-out"
                          />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                          <span className="text-[10px] font-black text-slate-900 leading-none uppercase tracking-wider text-center">
                            {match.match_percentage >= 70 ? 'Strong' : match.match_percentage >= 40 ? 'Good' : 'Potential'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-8 relative z-10">
                    {[
                      { label: 'Skills', score: match.skills_score, icon: <Cpu size={14} />, reason: match.skills_reason, color: 'text-blue-600', bg: 'bg-blue-50' },
                      { label: 'Experience', score: match.experience_score, icon: <Briefcase size={14} />, reason: match.experience_reason, color: 'text-purple-600', bg: 'bg-purple-50' },
                      { label: 'Education', score: match.education_score, icon: <GraduationCap size={14} />, reason: match.education_reason, color: 'text-amber-600', bg: 'bg-amber-50' }
                    ].map((item, idx) => (
                      <div key={idx} className={`${item.bg} p-4 rounded-2xl flex flex-col items-center text-center group-hover:shadow-inner transition-all`}>
                        <div className={`${item.color} mb-1.5`}>{item.icon}</div>
                        <p className={`text-xs font-black uppercase tracking-wider ${item.color}`}>
                          {item.score >= 70 ? 'High' : item.score >= 40 ? 'Medium' : 'Basic'}
                        </p>
                        <span className="text-[8px] font-black uppercase tracking-widest text-slate-400 mb-2">{item.label}</span>
                        <p className="text-[7px] font-semibold leading-relaxed text-slate-500 line-clamp-3">{item.reason}</p>
                      </div>
                    ))}
                  </div>

                  <div className="bg-slate-50/50 rounded-3xl p-6 mb-8 mt-auto relative z-10 border border-slate-100">
                    <div className="flex flex-wrap items-center gap-6">
                      <div className="flex items-center gap-2.5 text-xs font-bold text-slate-600">
                        <div className="w-8 h-8 rounded-xl bg-white flex items-center justify-center shadow-sm border border-slate-50">
                          <MapPin size={14} className="text-slate-400" />
                        </div>
                        {match.location || "Sto. Tomas, Batangas"}
                      </div>
                      <div className="flex items-center gap-2.5 text-xs font-bold text-slate-600">
                        <div className="w-8 h-8 rounded-xl bg-white flex items-center justify-center shadow-sm border border-slate-50">
                          <Clock size={14} className="text-slate-400" />
                        </div>
                        {match.job_type || "Full-time"}
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-4 relative z-10 mt-auto">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        // For candidates, we might want to stay in the dashboard context
                        navigate(`/candidate/findjobs`); 
                      }}
                      className="flex-1 py-4 rounded-2xl border border-slate-200 font-bold text-sm text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
                    >
                      Browse Jobs
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/candidate/preview-profile/${match.job_id}`, { state: { job: { job_id: match.job_id, title: match.job_title, department: match.department, location: match.location, job_type: match.job_type }, extractedData, matchData: match, fileName } });
                      }}
                      className="flex-[2] py-4 rounded-2xl bg-slate-900 text-white font-bold text-sm flex items-center justify-center gap-2 hover:bg-[#D60041] transition-all shadow-xl shadow-slate-200 hover:shadow-pink-200 active:scale-95 group/btn"
                    >
                      Start Application
                      <ArrowRight size={18} className="group-hover/btn:translate-x-1 transition-transform" />
                    </button>
                  </div>
                </div>
              ))
            ) : (
              <div className="col-span-full py-24 text-center bg-white rounded-[40px] border border-slate-100 shadow-xl shadow-slate-200/40">
                <div className="w-20 h-20 bg-slate-50 rounded-3xl flex items-center justify-center mx-auto mb-6 text-slate-300">
                  <Briefcase size={40} />
                </div>
                <h3 className="text-slate-900 font-black text-2xl mb-2">No direct matches found</h3>
                <p className="text-slate-500 font-medium max-w-sm mx-auto mb-8">
                  Your profile is unique! We couldn't find an exact AI match, but we have many other opportunities you might like.
                </p>
                <button
                  onClick={() => navigate('/candidate/findjobs')}
                  className="px-10 py-4 rounded-2xl bg-slate-900 text-white font-bold text-sm hover:bg-[#D60041] transition-all shadow-xl shadow-slate-200 hover:shadow-pink-200 active:scale-95"
                >
                  Explore All Jobs
                </button>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default CandidateSmartMatchResult;
