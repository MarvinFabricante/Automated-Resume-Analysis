import React, { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate, useParams } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import { Helmet } from 'react-helmet-async';
import candidateService from '../../services/candidateService';
import {
  User, Mail, Phone, MapPin,
  Cpu, Briefcase, GraduationCap,
  CheckCircle, ArrowLeft, Edit3, Target,
  Award, Sparkles, Eye, FileUp, FileText, Code,
  AlertTriangle, X
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ApplicationProgressBar from '../../components/common/ApplicationProgressBar';
import ApplicationSuccessModal from '../../components/modals/shared/ApplicationSuccessModal';
import ResumePreviewModal from '../../components/modals/shared/ResumePreviewModal';
import ExperienceGapAlert from '../../components/common/ExperienceGapAlert';
import MinimumRequirementBlocker, { isBelowAcceptedRequirements } from '../../components/common/MinimumRequirementBlocker';
import { ClarificationSubmitConfirmation } from '../../components/common/ClarificationQuestionsPanel';
import ResumeTipsPanel, {
  ResumeReadabilityBanner,
} from '../../components/common/ResumeTipsPanel';
import { useSubmitApplicationMutation } from '../../redux/api/apiSlice';
import { formatApiErrorDetail, formatUploadOrParseError, toPositiveIntOrUndefined, toStringArray } from '../../utils/errorUtils';
import {
  cleanRequirementInput,
  cleanRequirementList,
  resolveCriterionStatus,
  getCriterionStatusBadgeStyle,
  stripStatusPrefix,
} from '../../utils/criterionStatus';
import { formatSecondPersonText } from '../../components/candidate/DetailedAnalysisDrawer';


const CandidatePreviewAndVerify: React.FC = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();
  const { user: authUser, userId: authUserId } = useSelector((state: RootState) => state.auth);
  const accountEmail =
    state?.accountEmail ||
    (typeof authUser === 'string' ? authUser : (authUser as any)?.email) ||
    (typeof window !== 'undefined' ? localStorage.getItem('saved_email') : '') ||
    '';
  const effectiveUserId =
    authUserId ||
    (typeof window !== 'undefined' && localStorage.getItem('userId') ? Number(localStorage.getItem('userId')) : undefined);
  const effectiveJobId = (jobId && jobId !== 'smart' && jobId !== 'undefined')
    ? jobId
    : (state?.job?.job_id || state?.job?.id || (typeof window !== 'undefined' ? localStorage.getItem('draft_application_job_id') : null));

  const [submitApplication, { isLoading: isSubmitting }] = useSubmitApplicationMutation();
  const [showSuccessModal, setShowSuccessModal] = useState<boolean>(false);

  useEffect(() => {
    // Step Gating: Verify Step 2 (Details) and Step 3 (Questions) are confirmed before allowing Step 4 Submit
    let savedDraft: any = null;
    if (effectiveJobId) {
      try {
        const raw = localStorage.getItem(`draft_application_${effectiveJobId}`);
        if (raw) savedDraft = JSON.parse(raw);
      } catch {}
    }

    const hasResume = Boolean(
      state?.file || state?.fileName || state?.resumeUrl || state?.rawText ||
      savedDraft?.fileName || savedDraft?.extractedData
    );
    const hasDetails = Boolean(
      state?.formData || state?.personal?.name ||
      savedDraft?.detailsConfirmed || savedDraft?.formData
    );

    // If no resume uploaded, redirect back to Step 1 Upload
    if (!hasResume) {
      navigate(effectiveJobId ? `/candidate/upload-resume/${effectiveJobId}` : '/candidate/upload-resume', { replace: true });
      return;
    }

    // If details not reviewed/confirmed, redirect back to Step 2
    if (!hasDetails) {
      navigate(effectiveJobId ? `/candidate/update-profile/${effectiveJobId}` : '/candidate/upload-resume', { replace: true });
      return;
    }

    if (effectiveJobId) {
      localStorage.setItem('draft_application_step', '4');
      if (state?.job?.title) {
        localStorage.setItem('draft_application_job_title', state.job.title);
      }
      localStorage.setItem('draft_application_job_id', String(effectiveJobId));
    }
  }, [effectiveJobId, state, navigate]);

  const data = state?.extractedData;
  const matchData = state?.matchData;

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
  const [hasReplacedResume, setHasReplacedResume] = useState<boolean>(false);
  const [replaceError, setReplaceError] = useState<string | null>(null);
  const [replaceNotice, setReplaceNotice] = useState<string | null>(null);
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
      if (/\.pdf$/i.test(file.name)) {
        let hasPdfHeader = false;
        for (let i = 0; i < Math.min(bytes.length - 4, 1020); i++) {
          if (bytes[i] === 0x25 && bytes[i + 1] === 0x50 && bytes[i + 2] === 0x44 && bytes[i + 3] === 0x46) {
            hasPdfHeader = true;
            break;
          }
        }
        if (!hasPdfHeader) {
          return { valid: false, error: 'File rejected by content check: The file has a .pdf extension but does not contain valid PDF content.' };
        }
      }
      if (/\.(docx|doc)$/i.test(file.name)) {
        const isZip = bytes.length >= 2 && bytes[0] === 0x50 && bytes[1] === 0x4b;
        const isCfbf = bytes.length >= 4 && bytes[0] === 0xd0 && bytes[1] === 0xcf && bytes[2] === 0x11 && bytes[3] === 0xe0;
        const isRtf = bytes.length >= 5 && bytes[0] === 0x7b && bytes[1] === 0x5c && bytes[2] === 0x72 && bytes[3] === 0x74 && bytes[4] === 0x66;
        let isXml = false;
        try {
          const sliceText = new TextDecoder().decode(bytes.slice(0, 80));
          isXml = sliceText.includes('<?xml') || sliceText.includes('<w:document');
        } catch {}
        if (!isZip && !isCfbf && !isRtf && !isXml) {
          return { valid: false, error: 'File rejected by content check: The file has a Word extension (.docx/.doc) but does not contain valid Word document content.' };
        }
      }
      return { valid: true };
    } catch {
      return { valid: true };
    }
  };

  const handleReplaceResume = async (newFile: File) => {
    setReplaceError(null);
    setReplaceNotice(null);
    setShowResumePreview(false);
    const validTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
    ];
    const isValidType =
      newFile &&
      (validTypes.includes(newFile.type) ||
        newFile.type.startsWith('text/') ||
        newFile.type.includes('pdf') ||
        newFile.type.includes('word') ||
        newFile.type.includes('officedocument') ||
        /\.(pdf|docx|doc|txt|text)$/i.test(newFile.name) ||
        (!newFile.type && !/\.[a-zA-Z0-9]+$/i.test(newFile.name)));

    if (!isValidType) {
      const msg = 'Invalid file type. Please upload a PDF, Word document, or text file (.pdf, .docx, .doc, .txt).';
      setReplaceError(msg);
      alert(msg);
      return;
    }

    if (newFile.size === 0) {
      const msg = 'This file is empty (0 bytes). Please upload a valid resume document.';
      setReplaceError(msg);
      alert(msg);
      return;
    }

    if (newFile.size > 10 * 1024 * 1024) {
      const msg = 'File size exceeds 10MB limit. Please upload a smaller document.';
      setReplaceError(msg);
      alert(msg);
      return;
    }

    const contentCheck = await checkFileContent(newFile);
    if (!contentCheck.valid) {
      const msg = contentCheck.error || 'Invalid or corrupted file content.';
      setReplaceError(msg);
      alert(msg);
      return;
    }

    try {
      setIsReplacingResume(true);
      const response = await candidateService.parseResume(newFile);
      if (response.data) {
        const parsed = response.data;
        setCurrentFile(newFile);
        setCurrentFileName(newFile.name);
        setCurrentResumeUrl(parsed.file_url || null);
        setCurrentRawText(parsed.raw_text || null);
        setDynamicExtractedData(parsed);
        setHasReplacedResume(true);
        setReplaceNotice(`Resume successfully replaced with "${newFile.name}". Extracted profile fields have been updated.`);

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
      const msg = formatUploadOrParseError(err, "Failed to parse new resume. Please ensure the file is valid.");
      setReplaceError(msg);
      alert(msg);
    } finally {
      setIsReplacingResume(false);
    }
  };

  const activeData = dynamicExtractedData || data;
  const activeMatch = dynamicMatchData || matchData;
  const belowRequirements = Boolean(effectiveJobId && effectiveJobId !== 'smart' && isBelowAcceptedRequirements(activeMatch));

  const resumeEmail = state?.resumeEmail || activeData?.email || data?.email || "";
  const chosenContactEmail =
    state?.contactEmail ||
    state?.formData?.email ||
    state?.personal?.email ||
    accountEmail ||
    activeData?.email ||
    "candidate@example.com";

  const extractedData = {
    personal: {
      name: (hasReplacedResume ? activeData?.fullname : (state?.formData?.fullName || state?.personal?.name || activeData?.fullname)) || "Candidate Name",
      email: chosenContactEmail,
      phone: (hasReplacedResume ? activeData?.phone : (state?.formData?.phone || state?.personal?.phone || activeData?.phone)) || "Not specified",
      location: (hasReplacedResume ? activeData?.location : (state?.formData?.location || state?.personal?.location || activeData?.location)) || "Not specified"
    },
    skills: (!hasReplacedResume && Array.isArray(state?.formData?.skills) && state.formData.skills.length > 0)
      ? state.formData.skills
      : (!hasReplacedResume && Array.isArray(state?.skills) && state.skills.length > 0)
      ? state.skills
      : (Array.isArray(activeData?.skills_list) && activeData.skills_list.length > 0)
      ? activeData.skills_list
      : activeData?.skills
      ? (Array.isArray(activeData.skills) ? activeData.skills : String(activeData.skills).split(' | ').filter(Boolean))
      : [],
    experience: {
      title: (hasReplacedResume
        ? (activeData?.job_title || activeData?.work_experiences?.[0]?.job_title)
        : (state?.formData?.jobTitle || state?.experience?.title || activeData?.job_title || activeData?.work_experiences?.[0]?.job_title)) || "Not specified",
      company: (hasReplacedResume
        ? (activeData?.company || activeData?.work_experiences?.[0]?.company_name)
        : (state?.formData?.company || state?.experience?.company || activeData?.company || activeData?.work_experiences?.[0]?.company_name)) || "Not specified",
      relevance: (hasReplacedResume
        ? (activeData?.relevance || (activeData?.years_experience ? `${activeData.years_experience}+ years of experience` : "Professional experience"))
        : (state?.formData?.relevance || state?.experience?.relevance || activeData?.relevance || (activeData?.years_experience ? `${activeData.years_experience}+ years of experience` : "Professional experience")))
    },
    education: {
      degree: (hasReplacedResume
        ? (activeData?.degree || activeData?.education_entries?.[0]?.degree_or_course || activeData?.highest_degree)
        : ((state?.formData?.degree && !['BACHELOR', 'MASTER', 'DOCTORATE', 'ASSOCIATE', 'VOCATIONAL'].includes(String(state.formData.degree).toUpperCase()))
            ? state.formData.degree
            : (activeData?.degree || activeData?.education_entries?.[0]?.degree_or_course || state?.education?.degree || state?.formData?.degree || activeData?.highest_degree))) || "Not specified",
      college: (hasReplacedResume
        ? (activeData?.institution || activeData?.college || activeData?.education_entries?.[0]?.institution_name)
        : (state?.formData?.college || state?.education?.college || activeData?.institution || activeData?.college || activeData?.education_entries?.[0]?.institution_name)) || "Not specified"
    },
    years_experience: activeData?.years_experience || state?.years_experience || 0,
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
    resumeUrl: currentResumeUrl || activeData?.file_url || activeData?.resumeUrl || state?.resumeUrl || null
  };


  const getMatchTier = (pct: number) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const handleBackToEdit = () => {
    navigate(effectiveJobId ? `/candidate/update-profile/${effectiveJobId}?step=3` : '/candidate/update-profile?step=3', {
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
        clarificationQuestions: state?.clarificationQuestions || activeData?.clarification_questions,
        clarificationAnswers: state?.clarificationAnswers || activeData?.clarification_answers,
        fileName: state?.fileName,
        job: state?.job,
        matchData: state?.matchData,
        matches: state?.matches,
        resumeUrl: extractedData.resumeUrl
      }
    });
  };

  const handleSubmitFinalApplication = async () => {
    if (belowRequirements) {
      alert("You cannot submit this application because your qualifications fall below the accepted minimum requirements for this position.");
      return;
    }
    if (!effectiveJobId || effectiveJobId === 'smart') {
      navigate('/candidate/smart-matches', {
        state: { matches: state?.matches || matchData, extractedData: data, fileName: state?.fileName }
      });
      return;
    }

    const candidateName = String(extractedData.personal.name || "").trim();
    const candidateEmail = String(extractedData.personal.email || "").trim();
    if (!candidateName || !candidateEmail) {
      alert("Please provide your full name and a valid email address before submitting.");
      return;
    }

    const certString = Array.isArray(extractedData.certifications)
      ? extractedData.certifications.join(' | ')
      : String(extractedData.certifications || data?.certifications || "").trim();

    const rawStateJobTitle = state?.job?.title || state?.jobTitle || localStorage.getItem('draft_application_job_title') || "";
    const validStateJobTitle = (rawStateJobTitle && !['position', 'target position', 'not specified'].includes(String(rawStateJobTitle).trim().toLowerCase()))
      ? String(rawStateJobTitle).trim()
      : "";
    const validCandidateJobTitle = (extractedData.experience.title && extractedData.experience.title !== "Not specified")
      ? extractedData.experience.title
      : "";

    const validCandidateCompany = cleanRequirementInput(
      (extractedData.experience.company && extractedData.experience.company !== "Not specified")
        ? extractedData.experience.company
        : ""
    );
    const cleanedCerts = cleanRequirementInput(certString) || cleanRequirementInput(String(data?.candidate_certifications || ""));

    const confirmationTimestamp = new Date().toISOString();
    const rawClarificationResponses = activeData?.clarification_responses || data?.clarification_responses || [];
    const stampedClarificationResponses = Array.isArray(rawClarificationResponses)
      ? rawClarificationResponses.map((item: any) =>
          item && typeof item === 'object'
            ? { ...item, confirmed_at: item.confirmed_at || confirmationTimestamp }
            : item
        )
      : [];

    const payload = {
      clarification_responses: stampedClarificationResponses,
      job_id: String(effectiveJobId),
      user_id: effectiveUserId ? Number(effectiveUserId) : undefined,
      candidate_name: candidateName,
      candidate_email: candidateEmail,
      contact_email: candidateEmail,
      resume_email: resumeEmail || undefined,
      phone: extractedData.personal.phone,
      location: extractedData.personal.location,
      job_title: validCandidateJobTitle || validStateJobTitle || "Applicant",
      company: validCandidateCompany,
      relevance: cleanRequirementInput(extractedData.experience.relevance),
      degree: cleanRequirementInput(extractedData.education.degree),
      college: cleanRequirementInput(extractedData.education.college),
      skills: cleanRequirementList(toStringArray(extractedData.skills)),
      work_experiences: extractedData.work_experiences,
      total_experience_months: toPositiveIntOrUndefined(activeData?.total_experience_months ?? data?.total_experience_months),
      years_experience: toPositiveIntOrUndefined(extractedData.years_experience),
      education_entries: extractedData.education_entries,
      highest_educational_attainment: cleanRequirementInput(data?.highest_educational_attainment || state?.highest_educational_attainment || ""),
      certifications: cleanedCerts || undefined,
      candidate_certifications: cleanedCerts || undefined,
      match_score: activeMatch?.match_percentage || state?.matchScore || 0,
      skills_score: activeMatch?.skills_score || 0,
      experience_score: activeMatch?.experience_score || 0,
      education_score: activeMatch?.education_score || 0,
      certifications_score: activeMatch?.certifications_score || 0,
      completeness_score: activeMatch?.completeness_score ?? data?.completeness_score ?? undefined,
      applied_weights: activeMatch?.applied_weights ?? undefined,
      skills_reason: activeMatch?.skills_reason || "",
      experience_reason: activeMatch?.experience_reason || "",
      education_reason: activeMatch?.education_reason || "",
      certifications_reason: activeMatch?.certifications_reason || "",
      matched_skills: toStringArray(activeMatch?.matched_skills),
      missing_skills: toStringArray(activeMatch?.missing_skills),
      relevant_experience: activeMatch?.relevant_experience || "",
      experience_gaps: activeMatch?.experience_gaps || "",
      required_degree: activeMatch?.required_degree || "",
      candidate_degree: activeMatch?.candidate_degree || "",
      recommendations: toStringArray(activeMatch?.recommendations),
      ai_summary: activeMatch?.ai_summary || "",
      strengths: toStringArray(activeMatch?.strengths),
      weaknesses: toStringArray(activeMatch?.weaknesses),
      ai_powered: Boolean(activeMatch?.ai_powered),
      profile_image_url: localStorage.getItem('profile_image_url'),
      resume_url: extractedData.resumeUrl,
    };

    try {
      await submitApplication(payload).unwrap();
      localStorage.removeItem('draft_application_job_title');
      localStorage.removeItem('draft_application_job_id');
      localStorage.removeItem('draft_application_step');
      if (effectiveJobId) {
        localStorage.removeItem(`draft_application_${effectiveJobId}`);
      }
      navigate(`/submissionsuccess/${effectiveJobId}`, {
        state: {
          jobTitle: state?.job?.title || 'Applied Position',
          fileName: currentFileName,
          updatedData: extractedData
        }
      });
    } catch (err: any) {
      console.error("Failed to submit application:", err);
      const detail = formatApiErrorDetail(
        err?.data?.detail || err?.response?.data?.detail,
        "Failed to submit application. Please try again."
      );
      alert(detail);
    }
  };

  const handleFinalRedirect = () => {
    navigate('/candidate/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Review Application | {state?.job?.title || 'Mariwasa Recruitment'}</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-7xl mx-auto px-6 py-12 flex-grow">
          {/* Back button */}
          <button
            onClick={handleBackToEdit}
            className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-4 font-semibold text-sm group cursor-pointer"
          >
            <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Questions
          </button>

          {jobId && <ApplicationProgressBar currentStep={4} />}

          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-3 py-1 bg-[#D10043]/10 text-[#D10043] rounded-full text-[10px] font-black uppercase tracking-widest">
                  Step 4 of 4
                </span>
                <span className="text-xs font-bold text-slate-400">Final Step: Submit</span>
              </div>
              <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
                {jobId ? "Review & Submit Your Application" : "AI Profile Analysis"}
              </h1>
              <p className="text-slate-500 font-medium">
                {jobId
                  ? `Please do a quick final check of your application for ${state?.job?.title || 'this position'} before submitting.`
                  : "Verify the information extracted from your resume before we find your matches."
                }
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                id="btn-edit-details"
                onClick={handleBackToEdit}
                className="flex items-center text-sm font-bold text-[#D60041] hover:underline bg-pink-50 px-4 py-2.5 rounded-xl transition-colors active:scale-95"
              >
                <Edit3 size={16} className="mr-2" /> Edit Details
              </button>
            </div>
          </div>

          <div className="space-y-6">

            {/* Shared ATS Resume Tips & Non-Blocking Readability Check */}
            {activeData?.readability_check && (
              <ResumeReadabilityBanner readabilityCheck={activeData.readability_check} />
            )}
            <ResumeTipsPanel />

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
                        Candidate Document
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
                    id="btn-candidate-preview-resume"
                    data-testid="preview-resume-btn"
                    type="button"
                    onClick={() => setShowResumePreview(true)}
                    className="flex-1 sm:flex-none px-5 py-3 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-md active:scale-95 cursor-pointer"
                  >
                    <Eye size={16} />
                    <span>Preview Resume</span>
                  </button>
                  <button
                    id="btn-candidate-replace-resume"
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

              {replaceNotice && !replaceError && (
                <div
                  role="status"
                  data-testid="replace-status-banner"
                  className="mt-4 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start justify-between gap-3 text-emerald-800 animate-in fade-in duration-200"
                >
                  <div className="flex items-start gap-2.5">
                    <CheckCircle size={18} className="text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-black text-emerald-900">Resume Replaced</h4>
                      <p className="text-xs font-medium text-emerald-700 mt-0.5">{replaceNotice}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setReplaceNotice(null)}
                    className="p-1 text-emerald-400 hover:text-emerald-700 rounded-lg transition-colors cursor-pointer"
                    aria-label="Dismiss notification"
                  >
                    <X size={15} />
                  </button>
                </div>
              )}

              {replaceError && (
                <div
                  role="alert"
                  data-testid="upload-error-banner"
                  className="mt-4 p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start justify-between gap-3 text-rose-800 animate-in fade-in duration-200"
                >
                  <div className="flex items-start gap-2.5">
                    <AlertTriangle size={18} className="text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs font-black text-rose-900">Failed to Replace Resume</h4>
                      <p className="text-xs font-medium text-rose-700 mt-0.5">{replaceError}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setReplaceError(null)}
                    className="p-1 text-rose-400 hover:text-rose-700 rounded-lg transition-colors cursor-pointer"
                    aria-label="Dismiss error"
                  >
                    <X size={15} />
                  </button>
                </div>
              )}
            </section>

            {/* Match Analysis section */}
            {activeMatch && (
              <div className="bg-white border border-slate-100 rounded-[32px] p-8 shadow-sm space-y-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-[#D60041]">
                    <div className="p-2.5 bg-pink-50 rounded-xl">
                      <Target size={20} />
                    </div>
                    <h2 className="font-bold uppercase tracking-widest text-xs">Job Match Analysis</h2>
                  </div>
                  <div className="bg-[#D60041] text-white px-5 py-2 rounded-2xl text-sm font-black shadow-lg shadow-pink-100">
                    {getMatchTier(activeMatch.match_percentage)} ({activeMatch.match_percentage}%)
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    {
                      label: 'Skills',
                      status: resolveCriterionStatus({
                        explicitStatus: activeMatch.skills_status,
                        reason: activeMatch.skills_reason,
                        score: activeMatch.skills_score,
                      }),
                      reason: activeMatch.skills_reason,
                      icon: <Cpu size={16} />,
                    },
                    {
                      label: 'Experience',
                      status: resolveCriterionStatus({
                        explicitStatus: activeMatch.experience_status,
                        reason: activeMatch.experience_reason,
                        score: activeMatch.experience_score,
                        isBelowMinimum: Boolean(activeMatch.experience_below_minimum),
                      }),
                      reason: activeMatch.experience_reason,
                      icon: <Briefcase size={16} />,
                    },
                    {
                      label: 'Education',
                      status: resolveCriterionStatus({
                        explicitStatus: activeMatch.education_status,
                        reason: activeMatch.education_reason,
                        score: activeMatch.education_score,
                      }),
                      reason: activeMatch.education_reason,
                      icon: <GraduationCap size={16} />,
                    },
                    {
                      label: 'Certifications',
                      status: resolveCriterionStatus({
                        explicitStatus: activeMatch.certifications_status,
                        reason: activeMatch.certifications_reason,
                        score: activeMatch.certifications_score,
                      }),
                      reason: activeMatch.certifications_reason,
                      icon: <Award size={16} />,
                    },
                  ].map((item, idx) => {
                    const style = getCriterionStatusBadgeStyle(item.status);
                    const cleanReason = formatSecondPersonText(
                      stripStatusPrefix(item.reason),
                      state?.formData?.fullName || data?.fullname
                    );
                    return (
                      <div key={idx} className="bg-slate-50/50 p-5 rounded-[24px] border border-slate-100/50 flex flex-col items-center text-center">
                        <div className={`${style.textClass} mb-2`}>{item.icon}</div>
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-1">{item.label}</span>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${style.badgeClass}`}>
                          {item.status}
                        </span>
                        {cleanReason && (
                          <p className="text-[11px] text-slate-600 font-medium mt-2 leading-snug">
                            {cleanReason}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>

                <ExperienceGapAlert
                  matchData={activeMatch}
                  job={state?.job}
                  yearsExperience={extractedData.years_experience}
                />

                {belowRequirements && (
                  <MinimumRequirementBlocker
                    matchData={activeMatch}
                    jobTitle={state?.job?.title || state?.jobTitle}
                    onUploadDifferent={() => replaceInputRef.current?.click()}
                    onBrowseJobs={() => navigate('/candidate/findjobs')}
                    compact
                  />
                )}
              </div>
            )}

            {!activeMatch && (
              <ExperienceGapAlert
                matchData={activeMatch}
                job={state?.job}
                yearsExperience={extractedData.years_experience}
              />
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
                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                  <InfoItem icon={<User size={16} />} label="Full Name" value={extractedData.personal.name} />
                  <InfoItem icon={<Mail size={16} />} label="Email Address" value={extractedData.personal.email} />
                  <InfoItem icon={<Phone size={16} />} label="Phone" value={extractedData.personal.phone} />
                  <InfoItem icon={<MapPin size={16} />} label="Location" value={extractedData.personal.location} />
                </div>
              </div>

              {/* Executive Summary */}
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

              {/* Skills */}
              <div className="mt-8 pt-8 border-t border-slate-50">
                <div className="flex items-center gap-3 mb-4 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Code size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">Key Skills</h2>
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
                <h4 className="font-black text-slate-900 mb-1">{extractedData.experience.title}</h4>
                <p className="text-sm font-bold text-slate-500 mb-4">{extractedData.experience.company}</p>
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                  <p className="text-sm text-slate-600 leading-relaxed font-medium">{extractedData.experience.relevance}</p>
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
                <h4 className="font-black text-slate-900 mb-1">{extractedData.education.degree}</h4>
                <p className="text-sm font-bold text-slate-500 bg-slate-50 inline-block px-3 py-1.5 rounded-lg border border-slate-100 mt-2">{extractedData.education.college}</p>

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

            {/* Short honesty confirmation near the final Submit button */}
            {effectiveJobId && (
              <ClarificationSubmitConfirmation />
            )}

            {/* Action Buttons: Reversal (Back to Edit) + Resume Preview + Final Submission */}
            <div className="flex flex-col sm:flex-row gap-3 pt-6 border-t border-slate-200">
              <button
                type="button"
                onClick={handleBackToEdit}
                className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95 flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
              >
                <ArrowLeft size={18} />
                <span>Back to Edit Details</span>
              </button>

              <button
                id="btn-candidate-preview-resume-footer"
                data-testid="preview-resume-footer-btn"
                type="button"
                onClick={() => setShowResumePreview(true)}
                className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95 flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
              >
                <Eye size={18} className="text-[#D60041]" />
                <span>Preview Resume</span>
              </button>

              {!effectiveJobId ? (
                <button
                  onClick={() => navigate('/candidate/smart-matches', { state: { matches: state?.matches || activeMatch, extractedData: activeData, fileName: currentFileName } })}
                  className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95 cursor-pointer"
                >
                  <Target size={22} />
                  <span>View Recommended Jobs</span>
                </button>
              ) : (
                <button
                  id="btn-candidate-confirm-submit"
                  type="button"
                  disabled={isSubmitting || belowRequirements}
                  onClick={handleSubmitFinalApplication}
                  className={`flex-[2] py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all ${
                    belowRequirements
                      ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                      : 'bg-[#D60041] hover:bg-slate-900 text-white shadow-xl shadow-pink-100 active:scale-95 disabled:opacity-75 disabled:cursor-not-allowed cursor-pointer'
                  }`}
                >
                  {isSubmitting ? (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Submitting Application...</span>
                    </div>
                  ) : belowRequirements ? (
                    <span>Below Accepted Requirements</span>
                  ) : (
                    <>
                      <CheckCircle size={22} />
                      <span>Submit Application</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          <ResumePreviewModal
            isOpen={showResumePreview}
            onClose={() => setShowResumePreview(false)}
            file={currentFile}
            fileName={currentFileName}
            fileUrl={currentResumeUrl}
            rawText={currentRawText}
            extractedData={activeData}
            onReplaceFile={handleReplaceResume}
            onReplace={() => {
              setShowResumePreview(false);
              if (replaceInputRef.current) {
                replaceInputRef.current.value = '';
                replaceInputRef.current.click();
              }
            }}
          />

          <input
            ref={replaceInputRef}
            type="file"
            accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            onChange={(e) => {
              const selected = e.target.files?.[0];
              if (selected) {
                handleReplaceResume(selected);
              }
              e.target.value = '';
            }}
            className="sr-only"
          />

          <ApplicationSuccessModal

            isOpen={showSuccessModal}
            onConfirm={handleFinalRedirect}
          />
        </main>
      </div>
    </div>
  );
};

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
      <p className="font-bold text-slate-800">{value}</p>
    </div>
  </div>
);

export default CandidatePreviewAndVerify;
