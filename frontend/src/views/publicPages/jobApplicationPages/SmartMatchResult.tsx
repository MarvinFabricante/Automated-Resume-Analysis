import React, { useEffect, useState, useRef } from 'react';
import { useLocation, useNavigate } from '@/utils/navigation';
import { Helmet } from 'react-helmet-async';
import {
  Briefcase,
  MapPin,
  Clock,
  ArrowRight,
  Target,
  Zap,
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import DetailedAnalysisDrawer, { formatSecondPersonText } from '../../../components/candidate/DetailedAnalysisDrawer';
import HelpTooltip from '../../../components/common/HelpTooltip';
import { isBelowAcceptedRequirements } from '../../../components/common/MinimumRequirementBlocker';

const SmartMatchResult: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { matches, extractedData, fileName } = location.state || {};
  const [selectedDrawerMatch, setSelectedDrawerMatch] = useState<any>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const drawerTriggerRef = useRef<HTMLButtonElement | null>(null);

  const candidateFullName = extractedData?.fullname || '';

  const hasMountedRef = useRef(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      if (!matches) {
        navigate('/smart-upload');
      }
    }
  }, [matches, navigate]);

  const sortedMatches = matches ? [...matches].sort((a: any, b: any) => b.match_percentage - a.match_percentage) : [];

  const getMatchColor = (pct: number) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const handleStartApplication = (match: any) => {
    if (isBelowAcceptedRequirements(match)) return;
    const effectiveJobId = match.job_id || match.id;
    if (typeof window !== 'undefined') {
      const draftData = {
        step: 2,
        jobId: effectiveJobId,
        jobTitle: match.job_title,
        fileName: fileName || extractedData?.filename || 'Uploaded_Resume.pdf',
        extractedData,
        matchData: match,
        savedAt: new Date().toISOString()
      };
      try {
        localStorage.setItem(`draft_application_${effectiveJobId}`, JSON.stringify(draftData));
        localStorage.setItem('draft_application_step', '2');
        localStorage.setItem('draft_application_job_id', String(effectiveJobId));
        localStorage.setItem('draft_application_job_title', match.job_title);
      } catch { }
    }

    navigate(`/applicationform/${effectiveJobId}`, {
      state: {
        job: {
          job_id: effectiveJobId,
          title: match.job_title,
          department: match.department,
          location: match.location,
          job_type: match.job_type
        },
        extractedData,
        matchData: match,
        matches,
        fileName,
        file: location.state?.file,
        resumeUrl: location.state?.resumeUrl || extractedData?.file_url || extractedData?.resume_url,
        rawText: location.state?.rawText || extractedData?.raw_text
      }
    });
  };

  const openDrawerForMatch = (match: any, buttonEl: HTMLButtonElement | null) => {
    drawerTriggerRef.current = buttonEl;
    setSelectedDrawerMatch(match);
    setIsDrawerOpen(true);
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Career Matches | Mariwasa</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">
        <div className="text-center mb-16 relative">
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
            We've matched your profile against all our current job openings. Here are the positions where your background connects best.
          </p>
        </div>

        {/* Top Match Hero */}
        {sortedMatches.length > 0 && (
          <div className="bg-white p-8 md:p-10 rounded-[32px] border border-slate-100 shadow-sm mb-12 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
                <Zap className="text-[#D60041]" size={24} />
                Your Top Match: {sortedMatches[0].job_title} ({Math.round(sortedMatches[0].match_percentage)}%)
              </h2>
              {sortedMatches[0].ai_powered && (
                <span className="px-3 py-1 rounded-full text-[11px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Hybrid NLP + Gemini AI
                </span>
              )}
            </div>
            <p className="text-slate-600 leading-relaxed text-sm">
              {formatSecondPersonText(sortedMatches[0].ai_summary, candidateFullName) || "Your background and skills closely match what this role asks for."}
            </p>
            {Array.isArray(sortedMatches[0].why_this_score) && sortedMatches[0].why_this_score.length > 0 && (
              <div className="p-4 bg-rose-50/40 rounded-2xl border border-rose-100 space-y-1.5">
                <p className="text-[11px] font-black uppercase tracking-wider text-slate-900">
                  Why you got this match result
                </p>
                <ul className="space-y-1">
                  {sortedMatches[0].why_this_score.slice(0, 4).map((reason: string, idx: number) => (
                    <li key={idx} className="text-xs text-slate-700 leading-relaxed flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#D60041] shrink-0 mt-1.5" />
                      <span>{formatSecondPersonText(reason, candidateFullName)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-stretch">
          {sortedMatches.length > 0 ? (
            sortedMatches.map((match: any, index: number) => {
              const summaryText = formatSecondPersonText(
                match.ai_summary || match.experience_reason || "Good fit based on your background and skills.",
                candidateFullName
              );

              return (
                <div
                  key={index}
                  className="bg-white rounded-[32px] p-6 sm:p-8 border border-slate-100 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between h-full relative"
                >
                  <div className="flex-1 flex flex-col">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-4 mb-6">
                      <div className="min-w-0 pr-2">
                        <span className="px-3 py-1 bg-red-50 text-[#D60041] rounded-full text-[10px] font-black uppercase tracking-widest inline-block mb-3">
                          {match.department || "General"}
                        </span>
                        <h3 className="text-xl font-black text-slate-900 tracking-tight leading-snug">
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
                          <div className="absolute inset-0 flex flex-col items-center justify-center pt-1">
                            <span className="text-sm font-black text-slate-900 leading-none tracking-tight text-center">
                              {Math.round(match.match_percentage)}%
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 mt-1">
                          <span className="text-[9px] font-black uppercase tracking-wider text-[#D60041]">Fit Score</span>
                          <HelpTooltip content="Shows how closely your skills and background match what this job asks for." />
                        </div>
                      </div>
                    </div>

                    {/* Summary with 3-line clamp */}
                    <div className="mb-6 p-4 bg-slate-50 rounded-2xl border border-slate-100/80 relative z-10">
                      <p className="text-xs text-slate-700 leading-relaxed font-medium mb-3 line-clamp-3">
                        {summaryText}
                      </p>
                      {match.matched_skills && match.matched_skills.length > 0 && (
                        <div className="flex flex-wrap items-center gap-1.5 pt-1">
                          <span className="text-[10px] font-bold text-emerald-700 mr-1">Skills you have:</span>
                          {match.matched_skills.slice(0, 3).map((sk: string, i: number) => (
                            <span key={i} className="text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-md">
                              {sk}
                            </span>
                          ))}
                          {match.matched_skills.length > 3 && (
                            <span className="text-[10px] text-slate-400 font-medium">+{match.matched_skills.length - 3} more</span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Details card */}
                    <div className="bg-slate-50/50 rounded-2xl p-4 sm:p-5 mb-6 relative z-10 border border-slate-100">
                      <div className="flex flex-wrap items-center gap-5">
                        <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                          <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center shadow-sm">
                            <MapPin size={12} className="text-slate-400" />
                          </div>
                          <span>{match.location || "Sto. Tomas, Batangas"}</span>
                        </div>
                        <div className="flex items-center gap-2 text-xs font-bold text-slate-600">
                          <div className="w-6 h-6 rounded-full bg-white flex items-center justify-center shadow-sm">
                            <Clock size={12} className="text-slate-400" />
                          </div>
                          <span>{match.job_type || "Full-time"}</span>
                        </div>
                      </div>
                    </div>

                    {/* Drawer Button */}
                    <div className="mb-6 relative z-10">
                      <button
                        type="button"
                        onClick={(e) => openDrawerForMatch(match, e.currentTarget)}
                        className="w-full flex items-center justify-between p-3.5 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 border border-slate-200 rounded-2xl transition-all font-bold text-xs sm:text-sm text-slate-700 cursor-pointer"
                      >
                        <span className="flex items-center gap-2">
                          <Target size={15} className="text-[#D60041]" />
                          <span>View Detailed Analysis</span>
                        </span>
                        <ArrowRight size={15} className="text-slate-400" />
                      </button>
                    </div>
                  </div>

                  {/* Bottom Actions */}
                  <div className="flex gap-3 relative z-10 mt-auto pt-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/job-details/${match.job_id || match.id}`);
                      }}
                      className="flex-1 py-3.5 px-3 rounded-full border border-slate-200 font-bold text-xs sm:text-sm text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95 text-center cursor-pointer"
                    >
                      View Role
                    </button>
                    <button
                      type="button"
                      disabled={isBelowAcceptedRequirements(match)}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleStartApplication(match);
                      }}
                      className={`flex-[1.5] sm:flex-[2] py-3.5 px-4 rounded-full font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition-colors group/btn ${
                        isBelowAcceptedRequirements(match)
                          ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                          : 'bg-slate-900 text-white hover:bg-[#D60041] shadow-lg active:scale-95 cursor-pointer'
                      }`}
                    >
                      <span>{isBelowAcceptedRequirements(match) ? 'Below Requirements' : 'Start Application'}</span>
                      {!isBelowAcceptedRequirements(match) && (
                        <ArrowRight size={16} className="group-hover/btn:translate-x-1 transition-transform" />
                      )}
                    </button>
                  </div>
                </div>
              );
            })
          ) : (
            <div className="col-span-full py-24 text-center bg-white rounded-[32px] border border-slate-100 shadow-sm">
              <h3 className="text-slate-900 font-black text-xl mb-2">No strong matches found</h3>
              <p className="text-slate-500 font-medium max-w-sm mx-auto">
                We couldn't find any roles that strongly match your profile at the moment. You can still browse all our open positions.
              </p>
              <button
                type="button"
                onClick={() => navigate('/careerspage')}
                className="mt-6 px-8 py-4 rounded-full bg-slate-900 text-white font-bold text-sm hover:bg-[#D60041] transition-all shadow-lg active:scale-95 cursor-pointer"
              >
                Browse All Jobs
              </button>
            </div>
          )}
        </div>
      </main>

      {/* Accessible Slide-over Drawer / Bottom Sheet */}
      <DetailedAnalysisDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        match={selectedDrawerMatch}
        candidateName={candidateFullName}
        triggerRef={drawerTriggerRef}
        onViewDescription={() => {
          if (selectedDrawerMatch) {
            navigate(`/job-details/${selectedDrawerMatch.job_id || selectedDrawerMatch.id}`);
          }
        }}
        onStartApplication={() => {
          if (selectedDrawerMatch) handleStartApplication(selectedDrawerMatch);
        }}
      />

      <Footer />
    </div>
  );
};

export default SmartMatchResult;
