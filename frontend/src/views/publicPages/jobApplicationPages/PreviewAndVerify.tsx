import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, useParams } from '@/utils/navigation';
import { Helmet } from 'react-helmet-async';
import candidateService from '../../../services/candidateService';
import {
  User, Mail, Phone, MapPin,
  Cpu, Briefcase, GraduationCap,
  CheckCircle, ArrowLeft, Target,
  Award, Sparkles, Layers, Clock,
  Eye, FileUp, FileText
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import ResumePreviewModal from '../../../components/modals/shared/ResumePreviewModal';
import ApplicationProgressBar from '../../../components/common/ApplicationProgressBar';


interface InfoItemProps {
  icon: React.ReactNode;
  label: string;
  value: string;
}

const InfoItem: React.FC<InfoItemProps> = ({ icon, label, value }) => (
  <div className="flex items-start gap-3 bg-slate-50 p-4 rounded-2xl border border-transparent hover:border-slate-100 transition-colors">
    <div className="mt-0.5 text-slate-400 bg-white p-1.5 rounded-lg shadow-sm border border-slate-100">
      {icon}
    </div>
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider mb-0.5">{label}</p>
      <p className="font-bold text-slate-800">{value || "Not specified"}</p>
    </div>
  </div>
);

const PreviewAndVerifyPage: React.FC = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  const effectiveJobId = (jobId && jobId !== 'smart' && jobId !== 'undefined')
    ? jobId
    : (state?.job?.job_id || state?.job?.id || null);

  const data = state?.extractedData;
  const matchData = state?.matchData;
  const [smartMatches, setSmartMatches] = useState<any[] | null>(state?.matches || null);
  const [isLoadingSmartMatches, setIsLoadingSmartMatches] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Resume Document Preview & Replace State (REQ003 / TC-RES-009)
  const [showResumePreview, setShowResumePreview] = useState<boolean>(false);
  const [currentFile, setCurrentFile] = useState<File | null>(null);
  const [currentFileName, setCurrentFileName] = useState<string>(
    state?.fileName || data?.filename || "Uploaded_Resume.pdf"
  );
  const [currentResumeUrl, setCurrentResumeUrl] = useState<string | null>(
    state?.resumeUrl || data?.file_url || null
  );
  const [currentRawText, setCurrentRawText] = useState<string | null>(
    state?.rawText || data?.raw_text || null
  );
  const [dynamicExtractedData, setDynamicExtractedData] = useState<any>(data || null);
  const [dynamicMatchData, setDynamicMatchData] = useState<any>(matchData || null);
  const [isReplacingResume, setIsReplacingResume] = useState<boolean>(false);
  const replaceInputRef = useRef<HTMLInputElement>(null);

  const checkFileContent = async (file: File): Promise<{ valid: boolean; error?: string }> => {
    try {
      const slice = file.slice(0, 1024);
      const buffer = await slice.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      if (bytes.length >= 2 && bytes[0] === 0x4d && bytes[1] === 0x5a) {
        return { valid: false, error: 'File rejected by content check: Windows executable binary (.exe) is not accepted.' };
      }
      if (bytes.length >= 4 && bytes[0] === 0x7f && bytes[1] === 0x45 && bytes[2] === 0x4c && bytes[3] === 0x46) {
        return { valid: false, error: 'File rejected by content check: ELF binary executable is not accepted.' };
      }
      return { valid: true };
    } catch {
      return { valid: true };
    }
  };

  const handleReplaceResume = async (newFile: File) => {
    const contentCheck = await checkFileContent(newFile);
    if (!contentCheck.valid) {
      alert(contentCheck.error);
      return;
    }

    try {
      setIsReplacingResume(true);
      setCurrentFile(newFile);
      setCurrentFileName(newFile.name);

      const response = await candidateService.parseResume(newFile);
      if (response.data) {
        const parsed = response.data;
        setCurrentResumeUrl(parsed.file_url || null);
        setCurrentRawText(parsed.raw_text || null);
        setDynamicExtractedData(parsed);

        if (jobId && jobId !== 'smart') {
          try {
            const matchRes = await candidateService.matchData(jobId, parsed);
            if (matchRes.data) {
              setDynamicMatchData(matchRes.data);
            }
          } catch (mErr) {
            console.error("Match recalculation failed:", mErr);
          }
        }
      }
    } catch (err: any) {
      console.error("Failed to replace resume:", err);
      alert(err.response?.data?.detail || "Failed to parse new resume. Please ensure the file is valid.");
    } finally {
      setIsReplacingResume(false);
    }
  };

  useEffect(() => {
    if (jobId !== 'smart' || !data || smartMatches) return;

    let cancelled = false;
    const runPostParseAnalysis = async () => {
      setIsLoadingSmartMatches(true);
      try {
        const matchRes = await candidateService.matchData(null, data);
        if (!cancelled) {
          setSmartMatches(matchRes.data.results || []);
        }
      } catch (error) {
        console.error("Post-parse match analysis failed:", error);
        if (!cancelled) {
          setSmartMatches([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSmartMatches(false);
        }
      }
    };

    runPostParseAnalysis();
    return () => {
      cancelled = true;
    };
  }, [jobId, data, smartMatches]);

  const activeData = dynamicExtractedData || data;
  const activeMatch = dynamicMatchData || matchData;

  const extractedData = {
    personal: {
      name: activeData?.fullname || state?.formData?.fullName || "",
      email: activeData?.email || state?.formData?.email || "",
      phone: activeData?.phone || state?.formData?.phone || "",
      location: activeData?.location || state?.formData?.location || ""
    },
    skills: (Array.isArray(activeData?.skills_list) && activeData.skills_list.length > 0)
      ? activeData.skills_list
      : (activeData?.skills ? activeData.skills.split(' | ').filter(Boolean) : (state?.formData?.skills || ["Skills in review"])),
    experience: {
      title: activeData?.job_title || state?.formData?.jobTitle || (activeData?.experience ? activeData.experience.split('|')[0]?.trim() : ""),
      company: activeData?.company || state?.formData?.company || state?.job?.department || "Mariwasa Siam Ceramics",
      relevance: activeData?.relevance || state?.formData?.relevance || (activeData?.years_experience ? `${activeData.years_experience}+ years of experience` : "Experience provided")
    },
    education: {
      degree: activeData?.degree || activeData?.highest_degree || state?.formData?.degree || "",
      college: activeData?.institution || activeData?.college || state?.formData?.college || ""
    },
    years_experience: activeData?.years_experience || 0,
    summary: activeData?.summary || state?.summary || "",
    work_experiences: activeData?.work_experiences || state?.work_experiences || [],
    education_entries: activeData?.education_entries || state?.education_entries || [],
    certifications: (Array.isArray(activeData?.certifications_list) && activeData.certifications_list.length > 0)
      ? activeData.certifications_list
      : (activeData?.certifications
        ? (Array.isArray(activeData.certifications) ? activeData.certifications : String(activeData.certifications).split(' | ').map((s: string) => s.trim()).filter(Boolean))
        : (state?.certifications || [])),
    certifications_details: activeData?.certifications_details || state?.certifications_details || null,
    skills_details: activeData?.skills_details || state?.skills_details || null,
    profile_image_url: activeData?.profile_image_url || state?.profile_image_url || null
  };


  const getMatchTier = (pct: number) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const handleBackToEdit = () => {
    navigate(effectiveJobId ? `/applicationform/${effectiveJobId}` : `/applicationform/smart`, {
      state: {
        ...extractedData,
        extractedData: {
          ...(activeData || {}),
          fullname: extractedData.personal.name,
          email: extractedData.personal.email,
          phone: extractedData.personal.phone,
          location: extractedData.personal.location,
          job_title: extractedData.experience.title,
          company: extractedData.experience.company,
          relevance: extractedData.experience.relevance,
          degree: extractedData.education.degree,
          college: extractedData.education.college,
          skills: extractedData.skills.join(' | '),
          skills_list: extractedData.skills,
          certifications: Array.isArray(extractedData.certifications) ? extractedData.certifications.join(' | ') : (extractedData.certifications || ''),
          certifications_list: extractedData.certifications,
          certifications_details: extractedData.certifications_details,
          work_experiences: extractedData.work_experiences,
          education_entries: extractedData.education_entries
        },
        formData: state?.formData,
        personal: {
          name: extractedData.personal.name,
          email: extractedData.personal.email,
          phone: extractedData.personal.phone,
          location: extractedData.personal.location
        },
        experience: extractedData.experience,
        education: extractedData.education,
        skills: extractedData.skills,
        job: state?.job,
        fileName: state?.fileName,
        matchData: state?.matchData,
        matches: state?.matches || smartMatches,
        matchScore: state?.matchScore,
        profile_image_url: extractedData.profile_image_url
      }
    });
  };

  const handleFinalSubmit = async () => {
    if (!effectiveJobId || effectiveJobId === 'smart') {
      navigate('/smart-matches', {
        state: {
          matches: smartMatches || state?.matches,
          extractedData: data,
          fileName: state?.fileName
        }
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        job_id: effectiveJobId,
        candidate_name: extractedData.personal.name,
        candidate_email: extractedData.personal.email,
        phone: extractedData.personal.phone,
        location: extractedData.personal.location,
        job_title: state?.job?.title || state?.jobTitle || extractedData.experience.title || "Applicant",
        company: extractedData.experience.company || "General",
        relevance: extractedData.experience.relevance || "",
        degree: extractedData.education.degree || "",
        college: extractedData.education.college || "",
        skills: extractedData.skills,
        work_experiences: extractedData.work_experiences || data?.work_experiences || undefined,
        total_experience_months: data?.total_experience_months || undefined,
        education_entries: extractedData.education_entries || data?.education_entries || undefined,
        highest_educational_attainment: data?.highest_educational_attainment || undefined,
        certifications: Array.isArray(extractedData.certifications) ? extractedData.certifications.join(' | ') : (extractedData.certifications || data?.certifications || undefined),
        candidate_certifications: Array.isArray(extractedData.certifications) ? extractedData.certifications.join(' | ') : (extractedData.certifications || data?.candidate_certifications || undefined),
        match_score: state?.matchScore || matchData?.match_percentage || 0,
        skills_score: matchData?.skills_score || 0,
        experience_score: matchData?.experience_score || 0,
        education_score: matchData?.education_score || 0,
        certifications_score: matchData?.certifications_score || 0,
        profile_image_url: extractedData.profile_image_url || null,
        resume_url: currentResumeUrl || state?.resumeUrl || data?.file_url || null,
        skills_reason: matchData?.skills_reason || "",
        experience_reason: matchData?.experience_reason || "",
        education_reason: matchData?.education_reason || "",
        certifications_reason: matchData?.certifications_reason || "",
        matched_skills: matchData?.matched_skills || [],
        missing_skills: matchData?.missing_skills || [],
        relevant_experience: matchData?.relevant_experience || "",
        experience_gaps: matchData?.experience_gaps || "",
        required_degree: matchData?.required_degree || "",
        candidate_degree: matchData?.candidate_degree || "",
        recommendations: matchData?.recommendations || [],
        ai_summary: matchData?.ai_summary || extractedData.summary || "",
        strengths: matchData?.strengths || [],
        weaknesses: matchData?.weaknesses || [],
        ai_powered: Boolean(matchData?.ai_powered)
      };

      await candidateService.submitApplication(payload);
      navigate(`/submissionsuccess/${effectiveJobId}`, {
        state: {
          jobTitle: state?.job?.title || state?.jobTitle || "Position",
          fileName: state?.fileName,
          updatedData: extractedData
        }
      });
    } catch (error: any) {
      console.error("Failed to submit application:", error);
      const detail = error.response?.data?.detail || "Failed to submit application. Please check your network and try again.";
      alert(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Review & Verify Application | {state?.job?.title || 'Careers'}</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Reversal of action: Back to Application Details */}
        <button
          id="btn-back-to-edit"
          type="button"
          onClick={handleBackToEdit}
          className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-6 font-semibold text-sm group"
        >
          <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
          Back to Application Details
        </button>

        {/* Multi-step Application Progress Bar */}
        <ApplicationProgressBar currentStep={3} />

        <div className="mb-8">
          <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">Review Application</h1>
          <p className="text-slate-500 font-medium">
            Verify your information before finalizing submission for <span className="text-slate-900 font-bold">{state?.job?.title || "this position"}</span>.
          </p>
        </div>

        <div className="space-y-6">

          {/* Uploaded Resume Document Review Card (REQ003 / TC-RES-009) */}
          <section className="bg-white p-6 sm:p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5">
              <div className="flex items-center gap-4 min-w-0">
                <div className="w-14 h-14 bg-pink-50 text-[#D10043] rounded-2xl flex items-center justify-center shrink-0 border border-pink-100/80 shadow-2xs">
                  <FileText size={26} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] bg-pink-50 px-2 py-0.5 rounded-md border border-pink-100/60">
                      Uploaded Resume Document
                    </span>
                    <span className="text-xs text-emerald-600 font-bold flex items-center gap-1">
                      <CheckCircle size={13} /> Verified for submission
                    </span>
                  </div>
                  <h3 className="text-base sm:text-lg font-black text-slate-900 truncate mt-1">
                    {currentFileName}
                  </h3>
                  <p className="text-xs text-slate-400 font-medium mt-0.5">
                    Review your resume formatting and content, or replace it before submitting your application.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2.5 w-full sm:w-auto shrink-0">
                <button
                  id="btn-preview-resume"
                  data-testid="preview-resume-btn"
                  type="button"
                  onClick={() => setShowResumePreview(true)}
                  className="flex-1 sm:flex-none px-5 py-3 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md active:scale-95 cursor-pointer"
                >
                  <Eye size={16} />
                  <span>Preview Resume</span>
                </button>
                <button
                  id="btn-replace-resume"
                  data-testid="replace-resume-btn"
                  type="button"
                  onClick={() => replaceInputRef.current?.click()}
                  disabled={isReplacingResume}
                  className="flex-1 sm:flex-none px-5 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-95 cursor-pointer shadow-2xs disabled:opacity-60"
                >
                  {isReplacingResume ? (
                    <>
                      <div className="w-4 h-4 border-2 border-slate-600 border-t-transparent rounded-full animate-spin" />
                      <span>Replacing...</span>
                    </>
                  ) : (
                    <>
                      <FileUp size={16} />
                      <span>Replace Resume</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </section>

          {/* AI Match Analysis Card if activeMatch available */}
          {activeMatch && (
            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Target size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">AI Match Analysis</h2>
                </div>
                <div className="bg-[#D60041] text-white px-4 py-1.5 rounded-xl text-xs font-black shadow-sm">
                  {getMatchTier(activeMatch.match_percentage)} ({activeMatch.match_percentage}%)
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: 'Skills Alignment', score: activeMatch.skills_score, icon: <Cpu size={16} /> },
                  { label: 'Experience Level', score: activeMatch.experience_score, icon: <Briefcase size={16} /> },
                  { label: 'Education Match', score: activeMatch.education_score, icon: <GraduationCap size={16} /> }
                ].map((item, idx) => (
                  <div key={idx} className="bg-slate-50/70 p-4 rounded-2xl border border-slate-100/70 flex flex-col items-center text-center">
                    <div className="text-[#D60041] mb-1.5">{item.icon}</div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-0.5">{item.label}</span>
                    <p className="text-base font-black uppercase text-slate-900">
                      {item.score >= 70 ? 'High Match' : item.score >= 40 ? 'Moderate' : 'Basic Match'}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}


          {/* Personal Information */}
          <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-6 text-[#D60041]">
              <div className="p-2.5 bg-pink-50 rounded-xl">
                <User size={20} />
              </div>
              <h2 className="font-bold uppercase tracking-widest text-xs">Personal Information</h2>
            </div>
            <div className="flex flex-col md:flex-row gap-8 items-start">
              {extractedData.profile_image_url && (
                <div className="shrink-0">
                  <img 
                    src={extractedData.profile_image_url} 
                    alt="Profile" 
                    className="w-32 h-32 rounded-2xl object-cover border-4 border-white shadow-lg"
                  />
                </div>
              )}
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                <InfoItem icon={<User size={16} />} label="Full Name" value={extractedData.personal.name} />
                <InfoItem icon={<Mail size={16} />} label="Email Address" value={extractedData.personal.email} />
                <InfoItem icon={<Phone size={16} />} label="Phone" value={extractedData.personal.phone || "Not specified"} />
                <InfoItem icon={<MapPin size={16} />} label="Location" value={extractedData.personal.location || "Not specified"} />
              </div>
            </div>

            {/* Executive Profile Summary */}
            {extractedData.summary && (
              <div className="mt-8 pt-6 border-t border-slate-50">
                <div className="flex items-center gap-3 mb-3 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Sparkles size={18} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">Executive Profile Summary</h2>
                </div>
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                  <p className="text-sm text-slate-700 leading-relaxed font-medium">
                    {extractedData.summary}
                  </p>
                </div>
              </div>
            )}

            {/* Skills & Competencies */}
            <div className="mt-8 pt-8 border-t border-slate-50">
              <div className="flex items-center gap-3 mb-4 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <Cpu size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Skills & Competencies</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                {extractedData.skills.map((skill: string, i: number) => (
                  <span key={i} className="px-3.5 py-1.5 bg-slate-50 text-slate-700 rounded-xl text-xs font-bold border border-slate-100 hover:border-slate-200 transition-colors cursor-default">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            {/* Certifications & Licenses */}
            {((extractedData.certifications_details?.certifications && extractedData.certifications_details.certifications.length > 0) ||
              (extractedData.certifications && extractedData.certifications.length > 0)) && (
              <div className="mt-8 pt-8 border-t border-slate-50">
                <div className="flex items-center gap-3 mb-4 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Award size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">Licenses, Eligibility & Certifications</h2>
                </div>
                {extractedData.certifications_details?.certifications?.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {extractedData.certifications_details.certifications.map((cert: any, cIdx: number) => (
                      <div key={cIdx} className="p-3.5 bg-rose-50/40 rounded-2xl border border-rose-100/70 text-xs">
                        <div className="flex items-start justify-between gap-1 mb-1">
                          <span className="font-bold text-slate-900 leading-snug">
                            {cert.canonical_name}
                          </span>
                          {cert.category && (
                            <span className="shrink-0 px-2 py-0.5 rounded-md bg-white text-rose-700 border border-rose-200 text-[10px] font-bold">
                              {cert.category}
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-600 flex flex-wrap gap-x-2 gap-y-0.5">
                          {cert.issuing_organization && (
                            <span>Issuer: <strong className="text-slate-800">{cert.issuing_organization}</strong></span>
                          )}
                          {cert.expiration_or_status && (
                            <span className="text-emerald-700 font-semibold">• {cert.expiration_or_status}</span>
                          )}
                          {cert.credential_id_or_details && (
                            <span className="text-slate-500">• {cert.credential_id_or_details}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {extractedData.certifications.map((cert: string, cIdx: number) => (
                      <span key={cIdx} className="px-3.5 py-1.5 bg-rose-50 text-rose-800 rounded-xl text-xs font-bold border border-rose-100">
                        {cert}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Experience + Education */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <Briefcase size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Experience</h2>
              </div>
              <h4 className="font-black text-slate-900 mb-1">{extractedData.experience.title || "No Title Specified"}</h4>
              <p className="text-sm font-bold text-slate-500 mb-4">{extractedData.experience.company}</p>
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                <p className="text-sm text-slate-600 leading-relaxed font-medium">{extractedData.experience.relevance || "No additional description provided."}</p>
              </div>

              {extractedData.work_experiences && extractedData.work_experiences.length > 0 && (
                <div className="mt-4 space-y-2 pt-3 border-t border-slate-100">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-1">
                    Granular Positions ({extractedData.work_experiences.length})
                  </span>
                  {extractedData.work_experiences.map((exp: any, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs">
                      <div className="font-bold text-slate-900">{exp.job_title || exp.role}</div>
                      <div className="text-slate-500 text-[11px] mt-0.5">
                        {exp.company_name || exp.company}
                        {[exp.start_date, exp.end_date].filter(Boolean).length > 0 && (
                          <span className="ml-1 text-slate-400">• {[exp.start_date, exp.end_date].filter(Boolean).join(' - ')}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <GraduationCap size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Education</h2>
              </div>
              <h4 className="font-black text-slate-900 mb-1">{extractedData.education.degree || "Degree Not Specified"}</h4>
              <p className="text-sm font-bold text-slate-500 bg-slate-50 inline-block px-3 py-1.5 rounded-lg border border-slate-100 mt-2">
                {extractedData.education.college || "Institution Not Specified"}
              </p>

              {extractedData.education_entries && extractedData.education_entries.length > 0 && (
                <div className="mt-4 space-y-2 pt-3 border-t border-slate-100">
                  <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-1">
                    Education History ({extractedData.education_entries.length})
                  </span>
                  {extractedData.education_entries.map((edu: any, idx: number) => (
                    <div key={idx} className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs">
                      <div className="font-bold text-slate-900">{edu.degree_or_course || edu.degree}</div>
                      <div className="text-slate-500 text-[11px] mt-0.5">
                        {edu.institution_name || edu.institution}
                        {edu.year && <span className="ml-1 text-slate-400">• {edu.year}</span>}
                        {edu.honors && <span className="ml-1 text-emerald-700 font-bold">• {edu.honors}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </section>
          </div>

          {/* Action Buttons: Reversal of Action (Back) + Resume Preview + Final Submission */}
          <div className="flex flex-col sm:flex-row gap-3 pt-6 border-t border-slate-200">
            <button
              id="btn-back-edit"
              type="button"
              onClick={handleBackToEdit}
              className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95 flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
            >
              <ArrowLeft size={18} />
              <span>Back to Edit Details</span>
            </button>

            <button
              id="btn-preview-resume-footer"
              data-testid="preview-resume-footer-btn"
              type="button"
              onClick={() => setShowResumePreview(true)}
              className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95 flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
            >
              <Eye size={18} className="text-[#D60041]" />
              <span>Preview Resume</span>
            </button>

            {(!effectiveJobId || effectiveJobId === 'smart') ? (
              <button
                disabled={isLoadingSmartMatches || !smartMatches}
                onClick={() => navigate(`/smart-matches`, { state: { matches: smartMatches || state?.matches, extractedData: activeData, fileName: currentFileName } })}
                className={`flex-[2] py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl active:scale-95 cursor-pointer ${
                  isLoadingSmartMatches || !smartMatches
                    ? "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
                    : "bg-[#D60041] hover:bg-slate-900 text-white shadow-pink-100"
                }`}
              >
                <Target size={22} />
                {isLoadingSmartMatches ? "Analyzing Matches..." : "View Recommended Jobs"}
              </button>
            ) : (
              <button
                id="btn-confirm-submit"
                type="button"
                disabled={isSubmitting}
                onClick={handleFinalSubmit}
                className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95 disabled:opacity-75 disabled:cursor-not-allowed cursor-pointer"
              >
                {isSubmitting ? (
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Submitting Application...</span>
                  </div>
                ) : (
                  <>
                    <CheckCircle size={22} />
                    <span>Confirm & Submit Final Application</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </main>

      <ResumePreviewModal
        isOpen={showResumePreview}
        onClose={() => setShowResumePreview(false)}
        file={currentFile}
        fileName={currentFileName}
        fileUrl={currentResumeUrl}
        rawText={currentRawText}
        extractedData={activeData}
        onReplaceFile={handleReplaceResume}
      />

      <input
        ref={replaceInputRef}
        type="file"
        accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
        onChange={(e) => e.target.files?.[0] && handleReplaceResume(e.target.files[0])}
        className="hidden"
      />

      <Footer />
    </div>

  );
};

export default PreviewAndVerifyPage;
