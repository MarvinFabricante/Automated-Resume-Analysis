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
  GraduationCap,
  Zap,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  XCircle
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

const CandidateSmartMatchResult = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { matches, extractedData, fileName } = location.state || {};
  const [expandedJobId, setExpandedJobId] = React.useState(null);

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

  const toggleAnalysis = (jobId, e) => {
    e.stopPropagation();
    setExpandedJobId(expandedJobId === jobId ? null : jobId);
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

          {sortedMatches.length > 0 && (
            <div className="bg-white p-8 md:p-10 rounded-[40px] border border-slate-100 shadow-xl shadow-slate-200/40 mb-12 relative overflow-hidden group animate-in fade-in slide-in-from-bottom-4 duration-700 delay-100">
              <div className="absolute top-0 right-0 w-64 h-64 bg-red-50 rounded-bl-[200px] opacity-20 group-hover:opacity-40 transition-opacity duration-700 pointer-events-none"></div>
              <h2 className="text-2xl font-black text-slate-900 mb-6 flex items-center gap-3 relative z-10">
                <Zap className="text-[#D60041] p-2 bg-pink-50 rounded-xl" size={40} />
                Top Match Analysis
              </h2>
              <div className="text-slate-600 space-y-6 relative z-10">
                <p className="text-lg leading-relaxed">
                  <strong className="text-slate-900">Why "{sortedMatches[0].job_title}" is your top match ({Math.round(sortedMatches[0].match_percentage)}%):</strong>{' '}
                  {sortedMatches[0].ai_summary || `Your profile strongly aligns with the core requirements of this role. Your skills score of ${Math.round(sortedMatches[0].skills_score)}% and experience score of ${Math.round(sortedMatches[0].experience_score)}% were the highest among all available positions.`}
                </p>
                
                {sortedMatches.length > 1 && (
                  <p className="text-base leading-relaxed p-5 bg-slate-50 rounded-2xl border border-slate-100">
                    <strong className="text-slate-900">Why other roles scored lower:</strong> Other recommended positions, such as <em className="font-semibold text-slate-800">{sortedMatches[1].job_title}</em> ({Math.round(sortedMatches[1].match_percentage)}%), had more gaps in required skills or mismatched experience levels compared to your current resume.
                  </p>
                )}

                {sortedMatches[0].recommendations?.length > 0 && (
                  <div className="p-6 bg-gradient-to-br from-pink-50 to-white rounded-2xl border border-pink-100 shadow-sm">
                    <h4 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-3">Recommendation to Improve Your Fit</h4>
                    <p className="text-slate-700 font-medium">{sortedMatches[0].recommendations[0]}</p>
                  </div>
                )}
              </div>
            </div>
          )}

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
                        <div className="absolute inset-0 flex flex-col items-center justify-center pt-1">
                          <span className="text-lg font-black text-slate-900 leading-none tracking-tight text-center">
                            {Math.round(match.match_percentage)}%
                          </span>
                        </div>
                      </div>
                      <span className="text-[8px] font-black uppercase tracking-widest text-[#D60041] mt-2">Job Fit Score</span>
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

                  {/* Detailed Analysis Toggle */}
                  <div className="mb-8 relative z-10">
                    <button 
                      onClick={(e) => toggleAnalysis(match.job_id, e)}
                      className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-2xl transition-colors font-bold text-sm text-slate-700"
                    >
                      <span>View Detailed Analysis</span>
                      {expandedJobId === match.job_id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                    </button>
                    
                    {expandedJobId === match.job_id && (
                      <div className="mt-4 p-6 bg-white border border-slate-200 rounded-3xl shadow-sm space-y-6 animate-in slide-in-from-top-2 duration-300" onClick={(e) => e.stopPropagation()}>
                        
                        {/* Detailed Score Breakdown */}
                        <div>
                          <h4 className="text-[10px] font-black uppercase tracking-widest text-[#D60041] mb-4 flex items-center gap-2"><Target size={14}/> Score Breakdown</h4>
                          <div className="space-y-4">
                            <div className="bg-slate-50 p-4 rounded-xl">
                              <p className="text-sm font-bold text-slate-900 flex justify-between">Skills Match <span className="text-[#D60041]">{Math.round(match.skills_score)}%</span></p>
                              <p className="text-xs text-slate-500 mt-1">{match.skills_reason}</p>
                            </div>
                            <div className="bg-slate-50 p-4 rounded-xl">
                              <p className="text-sm font-bold text-slate-900 flex justify-between">Experience Match <span className="text-[#D60041]">{Math.round(match.experience_score)}%</span></p>
                              <p className="text-xs text-slate-500 mt-1">{match.experience_reason}</p>
                            </div>
                            <div className="bg-slate-50 p-4 rounded-xl">
                              <p className="text-sm font-bold text-slate-900 flex justify-between">Education Match <span className="text-[#D60041]">{Math.round(match.education_score)}%</span></p>
                              <p className="text-xs text-slate-500 mt-1">{match.education_reason}</p>
                            </div>
                          </div>
                        </div>

                        {/* Missing / Matched Skills */}
                        <div>
                          <h4 className="text-[10px] font-black uppercase tracking-widest text-[#D60041] mb-4 flex items-center gap-2"><Cpu size={14}/> Skills Gap Analysis</h4>
                          {match.matched_skills?.length > 0 && (
                            <div className="mb-4">
                              <p className="text-xs font-bold text-green-600 mb-2 flex items-center gap-1"><CheckCircle2 size={12}/> Matched Skills</p>
                              <div className="flex flex-wrap gap-1.5">
                                {match.matched_skills.map((s, i) => (
                                  <span key={i} className="px-2 py-1 bg-green-50 text-green-700 border border-green-100 rounded-md text-[10px] font-bold">{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {match.missing_skills?.length > 0 && (
                            <div>
                              <p className="text-xs font-bold text-red-500 mb-2 flex items-center gap-1"><XCircle size={12}/> Missing Skills</p>
                              <div className="flex flex-wrap gap-1.5">
                                {match.missing_skills.map((s, i) => (
                                  <span key={i} className="px-2 py-1 bg-red-50 text-red-600 border border-red-100 rounded-md text-[10px] font-bold">{s}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>

                        {/* Experience Relevance Breakdown */}
                        {match.experience_explanation && (
                          <div>
                            <h4 className="text-[10px] font-black uppercase tracking-widest text-[#D60041] mb-4 flex items-center gap-2"><Briefcase size={14}/> Experience Relevance</h4>
                            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 text-xs text-slate-600 whitespace-pre-wrap font-medium font-mono leading-relaxed overflow-x-auto max-h-60 overflow-y-auto">
                              {match.experience_explanation}
                            </div>
                          </div>
                        )}

                      </div>
                    )}
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
