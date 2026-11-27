import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useLocation } from '@/utils/navigation';
import { Helmet } from 'react-helmet-async';
import {
  Briefcase,
  MapPin,
  Clock,
  ArrowRight,
  Target,
  Zap,
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import CandidateJobDetailsModal from '../../components/modals/candidate/CandidateJobDetailsModal';
import DetailedAnalysisDrawer, { formatSecondPersonText } from '../../components/candidate/DetailedAnalysisDrawer';
import jobService from '../../services/jobService';
import HelpTooltip from '../../components/common/HelpTooltip';
import { isBelowAcceptedRequirements } from '../../components/common/MinimumRequirementBlocker';

const CandidateSmartMatchResult: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { matches, extractedData, fileName } = location.state || {};
  const [selectedDrawerMatch, setSelectedDrawerMatch] = useState<any>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const drawerTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [isDetailsOpen, setIsDetailsOpen] = useState<boolean>(false);
  const [selectedJobForModal, setSelectedJobForModal] = useState<any>(null);

  const candidateFullName = extractedData?.fullname || (typeof localStorage !== 'undefined' ? localStorage.getItem('fullname') : '') || '';

  const handleOpenDetails = async (match: any) => {
    try {
      const response = await jobService.getJobById(match.job_id);
      const data = response.data;
      if (data) {
        setSelectedJobForModal({
          id: data.job_id || data.id || match.job_id,
          job_id: data.job_id || match.job_id,
          title: data.job_title || data.title || match.job_title,
          department: data.department || match.department || 'General',
          location: data.location || match.location || 'Sto. Tomas, Batangas',
          job_type: data.job_type || match.job_type || 'Full-Time',
          salary_range: data.salary_range || 'Competitive',
          description: data.description || match.ai_summary || '',
          skills_requirements: data.skills_requirements || (match.matched_skills || []).join(', '),
          education_requirements: data.education_requirements || match.required_degree || '',
          certifications_requirements: data.certifications_requirements || '',
          experience_requirements: data.experience_requirements || match.relevant_experience || '',
          is_active: data.is_active ?? true
        });
      }
    } catch {
      setSelectedJobForModal({
        id: match.job_id,
        job_id: match.job_id,
        title: match.job_title,
        department: match.department || 'General',
        location: match.location || 'Sto. Tomas, Batangas',
        job_type: match.job_type || 'Full-Time',
        salary_range: 'Competitive',
        description: match.ai_summary || '',
        skills_requirements: (match.matched_skills || []).join(', '),
        education_requirements: match.required_degree || '',
        certifications_requirements: '',
        experience_requirements: match.relevant_experience || '',
        is_active: true
      });
    }
    setIsDetailsOpen(true);
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

    navigate(`/candidate/update-profile/${effectiveJobId}`, {
      state: {
        fileName: fileName || extractedData?.filename || 'Uploaded_Resume.pdf',
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
        personal: {
          name: extractedData?.fullname,
          email: extractedData?.email,
          phone: extractedData?.phone,
          location: extractedData?.location,
          location_details: extractedData?.location_details
        },
        experience: {
          title: extractedData?.job_title || (extractedData?.experience ? extractedData.experience.split('|')[0]?.trim() : ''),
          company: extractedData?.company || (extractedData?.experience ? extractedData.experience.split('|')[1]?.trim() : ''),
          relevance: extractedData?.years_experience ? `${extractedData.years_experience} years` : ''
        },
        education: {
          degree: extractedData?.highest_degree || extractedData?.degree,
          college: extractedData?.institution || extractedData?.college || ''
        },
        work_experiences: extractedData?.work_experiences || [],
        education_entries: extractedData?.education_entries || [],
        certifications: extractedData?.certifications_list || (extractedData?.certifications ? extractedData.certifications.split(' | ') : []),
        certifications_details: extractedData?.certifications_details,
        skills_details: extractedData?.skills_details,
        summary: extractedData?.summary,
        skills: Array.isArray(extractedData?.skills_list) && extractedData.skills_list.length > 0
          ? extractedData.skills_list
          : extractedData?.skills
            ? (typeof extractedData.skills === 'string' ? extractedData.skills.split(/[|,\n]+/).map((s: string) => s.trim()).filter(Boolean) : extractedData.skills)
            : [],
        resumeUrl: extractedData?.file_url || extractedData?.resume_url,
        rawText: extractedData?.raw_text || null
      }
    });
  };

  const handleApplyFromModal = (targetJobId: string | number) => {
    setIsDetailsOpen(false);
    const matchedJob = matches?.find((m: any) => String(m.job_id || m.id) === String(targetJobId));
    handleStartApplication(matchedJob || { job_id: targetJobId, job_title: selectedJobForModal?.title });
  };

  const hasMountedRef = useRef(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    if (!hasMountedRef.current) {
      hasMountedRef.current = true;
      if (!matches) {
        navigate('/candidate/smart-upload');
      }
    }
  }, [matches, navigate]);

  const sortedMatches = matches ? [...matches].sort((a: any, b: any) => b.match_percentage - a.match_percentage) : [];

  const getMatchColor = (pct: number) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const openDrawerForMatch = (match: any, buttonEl: HTMLButtonElement | null) => {
    drawerTriggerRef.current = buttonEl;
    setSelectedDrawerMatch(match);
    setIsDrawerOpen(true);
  };

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] min-h-screen flex flex-col">
      <Helmet>
        <title>Career Matches | Mariwasa Recruitment</title>
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
                Your Top Match
              </h2>
              <div className="text-slate-600 space-y-6 relative z-10">
                <p className="text-lg leading-relaxed">
                  <strong className="text-slate-900">Why "{sortedMatches[0].job_title}" is your top match ({Math.round(sortedMatches[0].match_percentage)}%):</strong>{' '}
                  {formatSecondPersonText(sortedMatches[0].ai_summary, candidateFullName) || "Your background and skills closely match what this role asks for."}
                </p>

                {sortedMatches.length > 1 && (
                  <p className="text-base leading-relaxed p-5 bg-slate-50 rounded-2xl border border-slate-100">
                    <strong className="text-slate-900">Comparing other roles:</strong> Other roles, such as <em className="font-semibold text-slate-800">{sortedMatches[1].job_title}</em> ({Math.round(sortedMatches[1].match_percentage)}%), ask for different skill sets or experience levels.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Clean Matching Cards Grid - Uniform Heights */}
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
                    className="bg-white rounded-[32px] sm:rounded-[40px] p-6 sm:p-8 md:p-10 border border-slate-100 shadow-xl shadow-slate-200/50 flex flex-col justify-between h-full relative overflow-hidden group hover:border-pink-100 transition-all duration-300"
                  >
                    <div className="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-pink-50/40 via-transparent to-transparent rounded-bl-[100px] pointer-events-none"></div>

                    <div className="flex-1 flex flex-col">
                      {/* Header */}
                      <div className="flex items-start justify-between gap-4 mb-6 relative z-10">
                        <div className="min-w-0 pr-2">
                          <span className="px-3 py-1 bg-red-50 text-[#D60041] rounded-full text-[10px] font-black uppercase tracking-widest inline-block mb-3">
                            {match.department || "General"}
                          </span>
                          <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-snug">
                            {match.job_title}
                          </h3>
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
                          <div className="flex items-center gap-1 mt-2">
                            <span className="text-[10px] font-black uppercase tracking-wider text-[#D60041]">Fit Score</span>
                            <HelpTooltip content="Shows how closely your skills and background match what this job asks for." />
                          </div>
                        </div>
                      </div>

                      {/* Summary with 3-line clamp for consistent card heights */}
                      <div className="mb-6 p-4 bg-slate-50 rounded-2xl border border-slate-100/80 relative z-10">
                        <p className="text-xs text-slate-700 leading-relaxed font-medium mb-3 line-clamp-3">
                          {summaryText}
                        </p>
                        {match.matched_skills && match.matched_skills.length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            <span className="text-[10px] font-bold text-emerald-700 mr-1">Skills you have:</span>
                            {match.matched_skills.slice(0, 4).map((sk: string, i: number) => (
                              <span key={i} className="text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-md">
                                {sk}
                              </span>
                            ))}
                            {match.matched_skills.length > 4 && (
                              <span className="text-[10px] text-slate-400 font-medium">+{match.matched_skills.length - 4} more</span>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Location & Job Type Details */}
                      <div className="bg-slate-50/50 rounded-2xl sm:rounded-3xl p-5 sm:p-6 mb-6 relative z-10 border border-slate-100">
                        <div className="flex flex-wrap items-center gap-5 sm:gap-6">
                          <div className="flex items-center gap-2.5 text-xs font-bold text-slate-600">
                            <div className="w-8 h-8 rounded-xl bg-white flex items-center justify-center shadow-sm border border-slate-50">
                              <MapPin size={14} className="text-slate-400" />
                            </div>
                            <span>{match.location || "Sto. Tomas, Batangas"}</span>
                          </div>
                          <div className="flex items-center gap-2.5 text-xs font-bold text-slate-600">
                            <div className="w-8 h-8 rounded-xl bg-white flex items-center justify-center shadow-sm border border-slate-50">
                              <Clock size={14} className="text-slate-400" />
                            </div>
                            <span>{match.job_type || "Full-time"}</span>
                          </div>
                        </div>
                      </div>

                      {/* Detailed Analysis Slide-over Trigger Button */}
                      <div className="mb-6 relative z-10">
                        <button
                          type="button"
                          onClick={(e) => openDrawerForMatch(match, e.currentTarget)}
                          className="w-full flex items-center justify-between p-3.5 sm:p-4 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 border border-slate-200 rounded-2xl transition-all font-bold text-xs sm:text-sm text-slate-700 cursor-pointer active:scale-[0.99]"
                        >
                          <span className="flex items-center gap-2">
                            <Target size={16} className="text-[#D60041]" />
                            <span>View Detailed Analysis</span>
                          </span>
                          <ArrowRight size={16} className="text-slate-400" />
                        </button>
                      </div>
                    </div>

                    {/* Actions Pinned at Card Bottom */}
                    <div className="flex gap-3 sm:gap-4 relative z-10 mt-auto pt-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleOpenDetails(match);
                        }}
                        className="flex-1 py-3.5 sm:py-4 px-3 rounded-2xl border border-slate-200 font-bold text-xs sm:text-sm text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all active:scale-95 cursor-pointer text-center"
                      >
                        View Full Description
                      </button>
                      <button
                        type="button"
                        disabled={isBelowAcceptedRequirements(match)}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleStartApplication(match);
                        }}
                        className={`flex-[1.5] sm:flex-[2] py-3.5 sm:py-4 px-4 rounded-2xl font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition-all group/btn ${
                          isBelowAcceptedRequirements(match)
                            ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                            : 'bg-slate-900 text-white hover:bg-[#D60041] shadow-xl shadow-slate-200 hover:shadow-pink-200 active:scale-95 cursor-pointer'
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
                  className="px-10 py-4 rounded-2xl bg-slate-900 text-white font-bold text-sm hover:bg-[#D60041] transition-all shadow-xl shadow-slate-200 hover:shadow-pink-200 active:scale-95 cursor-pointer"
                >
                  Explore All Jobs
                </button>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Accessible Slide-over Drawer / Bottom Sheet */}
      <DetailedAnalysisDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        match={selectedDrawerMatch}
        candidateName={candidateFullName}
        triggerRef={drawerTriggerRef}
        onViewDescription={() => {
          if (selectedDrawerMatch) handleOpenDetails(selectedDrawerMatch);
        }}
        onStartApplication={() => {
          if (selectedDrawerMatch) handleStartApplication(selectedDrawerMatch);
        }}
      />

      {selectedJobForModal && (
        <CandidateJobDetailsModal
          isOpen={isDetailsOpen}
          onClose={() => setIsDetailsOpen(false)}
          job={selectedJobForModal}
          onApply={handleApplyFromModal}
        />
      )}
    </div>
  );
};

export default CandidateSmartMatchResult;
