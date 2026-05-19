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
import Footer from '../../../components/layout/Footer';
import Header from '../../../components/layout/Header';

const SmartMatchResult = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { matches, extractedData, fileName } = location.state || {};

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!matches) {
      navigate('/smart-upload');
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
        <title>Smart Matches | Mariwasa</title>
      </Helmet>
      <Header />

      <main className="flex-grow max-w-6xl mx-auto px-6 py-16 lg:py-24 w-full">
        <div className="text-center mb-16 relative">
          <div className="inline-block p-1.5 rounded-full bg-white shadow-sm border border-slate-100 mb-8">
            <div className="flex items-center gap-3 px-3 py-1 text-[#D60041]">
              <Target size={16} />
              <span className="text-xs font-semibold uppercase tracking-wider">AI Match Results</span>
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 mb-6">
            Your Best Career <span className="text-[#D60041]">Matches</span>
          </h1>
          <p className="text-slate-500 text-lg max-w-2xl mx-auto font-medium leading-relaxed">
            Based on your resume, our AI has identified the roles below as the best fit for your skills, experience, and education.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-12 items-stretch">
          {sortedMatches.length > 0 ? (
            sortedMatches.map((match) => (
              <div 
                key={match.job_id}
                onClick={() => navigate(`/preview-and-verify/${match.job_id}`, { state: { job: { job_id: match.job_id, title: match.job_title, department: match.department, location: match.location, job_type: match.job_type }, extractedData, matchData: match, fileName } })}
                className="bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm hover:shadow-xl hover:shadow-pink-100/50 transition-all duration-300 group flex flex-col relative overflow-hidden cursor-pointer active:scale-[0.99]"
              >
                <div className="absolute top-0 right-0 w-32 h-32 bg-red-50 rounded-bl-[100px] opacity-0 group-hover:opacity-50 transition-opacity duration-300"></div>

                <div className="flex justify-between items-start mb-6 relative z-10">
                  <div className="flex-1 pr-4">
                    <span className="inline-block px-3 py-1 rounded-full bg-red-50 text-[10px] font-bold uppercase tracking-wider text-[#D60041] mb-4">
                      {match.department}
                    </span>
                    <h3 className="text-2xl font-black text-slate-900 group-hover:text-[#D60041] transition-colors leading-tight tracking-tight">
                      {match.job_title}
                    </h3>
                  </div>
                  
                  {/* Gauge */}
                  <div className="flex flex-col items-center shrink-0">
                    <div className="relative w-16 h-16">
                      <svg className="w-16 h-16 -rotate-90" viewBox="0 0 100 100">
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
                        <span className="text-[9px] font-black text-slate-900 leading-none uppercase tracking-wider text-center">
                          {match.match_percentage >= 70 ? 'Strong' : match.match_percentage >= 40 ? 'Good' : 'Potential'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3 mb-8 relative z-10">
                  {[
                    { label: 'Skills', score: match.skills_score, icon: <Cpu size={12} />, reason: match.skills_reason },
                    { label: 'Experience', score: match.experience_score, icon: <Briefcase size={12} />, reason: match.experience_reason },
                    { label: 'Education', score: match.education_score, icon: <GraduationCap size={12} />, reason: match.education_reason }
                  ].map((item, idx) => (
                    <div key={idx} className="bg-slate-50 p-3 rounded-2xl flex flex-col items-center text-center group-hover:bg-pink-50/50 transition-colors">
                      <div className="text-slate-400 mb-1">{item.icon}</div>
                      <p className="text-xs font-black uppercase tracking-wider text-slate-800">
                        {item.score >= 70 ? 'High' : item.score >= 40 ? 'Medium' : 'Basic'}
                      </p>
                      <span className="text-[8px] font-black uppercase tracking-widest text-slate-400 mb-1">{item.label}</span>
                      <p className="text-[7px] font-medium leading-tight text-slate-500 mt-1 line-clamp-2">{item.reason}</p>
                    </div>
                  ))}
                </div>

                <div className="bg-slate-50/50 rounded-[24px] p-5 mb-8 mt-auto relative z-10 border border-slate-100">
                  <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                      <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center shadow-sm">
                        <MapPin size={12} className="text-slate-400" />
                      </div>
                      {match.location || "Philippines"}
                    </div>
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                      <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center shadow-sm">
                        <Clock size={12} className="text-slate-400" />
                      </div>
                      {match.job_type || "Full-time"}
                    </div>
                  </div>
                </div>

                <div className="flex gap-3 relative z-10 mt-auto">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/job-details/${match.job_id}`, { state: { job: { job_id: match.job_id, title: match.job_title, department: match.department, location: match.location, job_type: match.job_type } } });
                    }}
                    className="flex-1 py-4 rounded-full border border-slate-200 font-bold text-sm text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95"
                  >
                    View Role
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/preview-and-verify/${match.job_id}`, { state: { job: { job_id: match.job_id, title: match.job_title, department: match.department, location: match.location, job_type: match.job_type }, extractedData, matchData: match, fileName } });
                    }}
                    className="flex-[2] py-4 rounded-full bg-slate-900 text-white font-bold text-sm flex items-center justify-center gap-2 hover:bg-[#D60041] transition-colors shadow-lg active:scale-95 group/btn"
                  >
                    Apply Now
                    <ArrowRight size={16} className="group-hover/btn:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="col-span-full py-24 text-center bg-white rounded-[32px] border border-slate-100 shadow-sm">
              <h3 className="text-slate-900 font-black text-xl mb-2">No strong matches found</h3>
              <p className="text-slate-500 font-medium max-w-sm mx-auto">
                We couldn't find any roles that strongly match your profile at the moment. You can still browse all our open positions.
              </p>
              <button
                onClick={() => navigate('/careerspage')}
                className="mt-6 px-8 py-4 rounded-full bg-slate-900 text-white font-bold text-sm hover:bg-[#D60041] transition-all shadow-lg active:scale-95"
              >
                Browse All Jobs
              </button>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SmartMatchResult;
