import React, { useState, useRef, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams, useLocation } from '@/utils/navigation';
import jobService from '../../../services/jobService';
import candidateService from '../../../services/candidateService';
import {
  FileUp,
  X,
  FileText,
  CheckCircle2,
  ArrowLeft,
  ShieldCheck,
  Briefcase,
  ArrowRight,
  Target,
  GraduationCap,
  Cpu,
  Eye,
  AlertTriangle
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import RecruitmentTermsModal from '../../../components/modals/shared/RecruitmentTermsModal';
import ResumePreviewModal from '../../../components/modals/shared/ResumePreviewModal';
import ApplicationProgressBar from '../../../components/common/ApplicationProgressBar';
import ExperienceGapAlert from '../../../components/common/ExperienceGapAlert';
import { Job } from '../../../types';
import { formatUploadOrParseError } from '../../../utils/errorUtils';


const STATIC_JOBS = [
  {
    job_id: "1",
    title: "Production Supervisor",
    department: "Manufacturing",
    experience_requirements: "3+ years in manufacturing or production operations",
    skills_requirements: "Production Planning, Lean Manufacturing, Quality Control, Team Leadership",
  },
  {
    job_id: "2",
    title: "Quality Control Analyst",
    department: "Quality Assurance",
    experience_requirements: "2+ years in quality assurance or laboratory inspection",
    skills_requirements: "Quality Control, Inspection, Statistical Process Control, ISO 9001",
  },
  {
    job_id: "3",
    title: "HR Generalist",
    department: "Human Resources",
    experience_requirements: "2+ years in human resources and talent acquisition",
    skills_requirements: "Recruitment, Employee Relations, Payroll, HRIS, Onboarding",
  },
  {
    job_id: "4",
    title: "Maintenance Technician",
    department: "Engineering",
    experience_requirements: "2+ years in industrial equipment maintenance",
    skills_requirements: "Preventive Maintenance, Troubleshooting, PLC, Electrical Systems",
  },
];

const ApplyForJobPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<(Job & { [key: string]: any }) | null>(null);
  const [file, setFile] = useState<File | { name: string; size: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [isTermsAccepted, setIsTermsAccepted] = useState(false);
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [matchData, setMatchData] = useState<any>(null);
  const [, setIsMatching] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [savedDraft, setSavedDraft] = useState<any>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [replaceNotice, setReplaceNotice] = useState<string | null>(null);
  const hasRestoredFromLocationRef = useRef(false);
  const wasReplacingCompletedRef = useRef(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const location = useLocation();
  const [isLoadingJob, setIsLoadingJob] = useState(!location.state?.job);

  useEffect(() => {
    if (!jobId) return;
    try {
      const raw = localStorage.getItem(`draft_application_${jobId}`);
      if (raw) {
        const parsed = JSON.parse(raw);
        setSavedDraft(parsed);
      }
    } catch {}
  }, [jobId]);

  const handleResumeSavedDraft = () => {
    if (!savedDraft || !jobId) return;
    const targetStep = savedDraft.step || 2;
    if (targetStep >= 2) {
      navigate(`/applicationform/${jobId}?step=${targetStep}`, {
        state: {
          job,
          fileName: savedDraft.fileName || "Uploaded Resume",
          resumeUrl: savedDraft.resumeUrl || null,
          personal: savedDraft.formData ? {
            name: savedDraft.formData.fullName,
            email: savedDraft.formData.email,
            phone: savedDraft.formData.phone,
            location: savedDraft.formData.location
          } : undefined,
          experience: savedDraft.formData ? {
            title: savedDraft.formData.jobTitle,
            company: savedDraft.formData.company,
            relevance: savedDraft.formData.relevance
          } : undefined,
          education: savedDraft.formData ? {
            degree: savedDraft.formData.degree,
            college: savedDraft.formData.college
          } : undefined,
          skills: savedDraft.formData?.skills || [],
          clarificationAnswers: savedDraft.clarificationAnswers || {}
        }
      });
    }
  };

  useEffect(() => {
    const loadJobData = async () => {
      const stateJob = location.state?.job;
      if (stateJob) {
        setJob(stateJob);
        if (stateJob.skills_requirements || !jobId) {
          setIsLoadingJob(false);
          return;
        }
      }

      if (!jobId) {
        setIsLoadingJob(false);
        return;
      }

      // Fetch full requirements from API first; fall back to STATIC_JOBS only if unavailable
      try {
        if (!stateJob) {
          setIsLoadingJob(true);
        }
        const response = await jobService.getJobById(jobId);
        if (response.data) {
          const fetchedJob = response.data;
          setJob({
            ...(stateJob || {}),
            ...fetchedJob,
            title: fetchedJob.job_title || stateJob?.title || "Untitled Position",
            department: fetchedJob.department || stateJob?.department || "General"
          });
          return;
        }
      } catch (error) {
        console.error("Error fetching job details:", error);
      } finally {
        setIsLoadingJob(false);
      }

      const staticJob = STATIC_JOBS.find(j => j.job_id === jobId);
      if (staticJob) {
        setJob({
          ...(stateJob || {}),
          ...staticJob,
          title: stateJob?.title || staticJob.title,
          department: stateJob?.department || staticJob.department
        } as any);
      }
    };

    loadJobData();
  }, [jobId, location.state]);

  // Cooldown timer effect
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  // Restore previously extracted data once if navigated back (reversal of action)
  useEffect(() => {
    if (location.state?.extractedData && !extractedData && !hasRestoredFromLocationRef.current) {
      hasRestoredFromLocationRef.current = true;
      setExtractedData(location.state.extractedData);
      setIsComplete(true);
      if (location.state.fileName) {
        setFile({ name: location.state.fileName, size: 1024 * 1024 });
      }
      if (location.state.matchData) {
        setMatchData(location.state.matchData);
      }
    }
  }, [location.state, extractedData]);

  const handleProceedToForm = () => {
    if (!job?.job_id) return;
    navigate(`/applicationform/${job.job_id}`, {
      state: {
        job,
        fileName: file?.name || "Uploaded Resume",
        file: file,
        resumeUrl: extractedData?.file_url || null,
        rawText: extractedData?.raw_text || null,
        extractedData,
        matchData,
        personal: {
          name: extractedData?.fullname,
          email: extractedData?.email,
          phone: extractedData?.phone,
          location: extractedData?.location
        },
        experience: {
          title: extractedData?.job_title || extractedData?.work_experiences?.[0]?.job_title || "",
          company: extractedData?.company || extractedData?.work_experiences?.[0]?.company_name || "",
          relevance: extractedData?.relevance || (extractedData?.years_experience ? `${extractedData.years_experience} years of experience` : "")
        },
        education: {
          degree: extractedData?.degree || extractedData?.education_entries?.[0]?.degree_or_course || extractedData?.highest_degree || "",
          college: extractedData?.institution || extractedData?.college || extractedData?.education_entries?.[0]?.institution_name || ""
        },
        skills: (Array.isArray(extractedData?.skills_list) && extractedData.skills_list.length > 0)
          ? extractedData.skills_list
          : (extractedData?.skills ? extractedData.skills.split(' | ').filter(Boolean) : []),
        certifications: (Array.isArray(extractedData?.certifications_list) && extractedData.certifications_list.length > 0)
          ? extractedData.certifications_list
          : (extractedData?.certifications ? String(extractedData.certifications).split(' | ').filter(Boolean) : []),
        certifications_details: extractedData?.certifications_details || null,
        profile_image_url: extractedData?.profile_image_url || null
      }
    });

  };

  const getMatchTier = (pct: number) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const checkFileContent = async (file: File): Promise<{ valid: boolean; error?: string }> => {
    try {
      const slice = file.slice(0, 1024);
      const buffer = await slice.arrayBuffer();
      const bytes = new Uint8Array(buffer);

      // Windows PE Executable: 'M' (0x4D), 'Z' (0x5A)
      if (bytes.length >= 2 && bytes[0] === 0x4d && bytes[1] === 0x5a) {
        return {
          valid: false,
          error: 'This file is a computer program (.exe). Please upload your resume as a PDF or Word document.'
        };
      }

      // Linux ELF executable: 0x7F, 'E', 'L', 'F'
      if (bytes.length >= 4 && bytes[0] === 0x7f && bytes[1] === 0x45 && bytes[2] === 0x4c && bytes[3] === 0x46) {
        return {
          valid: false,
          error: 'This file is not a supported document format. Please upload your resume as a PDF or Word document.'
        };
      }

      // If claimed to be PDF, verify %PDF magic bytes
      if (/\.pdf$/i.test(file.name)) {
        let hasPdfHeader = false;
        for (let i = 0; i < Math.min(bytes.length - 4, 1020); i++) {
          if (bytes[i] === 0x25 && bytes[i + 1] === 0x50 && bytes[i + 2] === 0x44 && bytes[i + 3] === 0x46) {
            hasPdfHeader = true;
            break;
          }
        }
        if (!hasPdfHeader) {
          return {
            valid: false,
            error: 'We could not read this PDF. Please make sure the file is not damaged or corrupted.'
          };
        }
      }

      // If claimed to be DOCX or DOC, verify Word document signature (ZIP PK, OLE CFBF, RTF, or XML)
      if (/\.(docx|doc)$/i.test(file.name)) {
        const isZip = bytes.length >= 2 && bytes[0] === 0x50 && bytes[1] === 0x4b;
        const isCfbf = bytes.length >= 4 && bytes[0] === 0xd0 && bytes[1] === 0xcf && bytes[2] === 0x11 && bytes[3] === 0xe0;
        const isRtf = bytes.length >= 5 && bytes[0] === 0x7b && bytes[1] === 0x5c && bytes[2] === 0x72 && bytes[3] === 0x74 && bytes[4] === 0x66;
        let isXml = false;
        try {
          const sliceText = new TextDecoder().decode(bytes.slice(0, 80));
          isXml = sliceText.includes('<?xml') || sliceText.includes('<w:document');
        } catch {
          // ignore
        }

        if (!isZip && !isCfbf && !isRtf && !isXml) {
          return {
            valid: false,
            error: 'We could not read this Word file. Please make sure the document is not corrupted.'
          };
        }
      }

      return { valid: true };
    } catch {
      return { valid: true };
    }
  };

  const validateAndSetFile = async (selectedFile: File) => {
    setUploadError(null);
    const validTypes = [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain"
    ];

    if (
      selectedFile &&
      (validTypes.includes(selectedFile.type) ||
        selectedFile.type.startsWith('text/') ||
        selectedFile.type.includes('pdf') ||
        selectedFile.type.includes('word') ||
        selectedFile.type.includes('officedocument') ||
        /\.(pdf|docx|doc|txt|text)$/i.test(selectedFile.name) ||
        (!selectedFile.type && !/\.[a-zA-Z0-9]+$/i.test(selectedFile.name)))
    ) {
      if (selectedFile.size > 10 * 1024 * 1024) {
        const msg = "This file is too large. Resumes must be smaller than 10 MB.";
        setUploadError(msg);
        alert(msg);
        return;
      }

      if (selectedFile.size === 0) {
        const msg = "This file looks empty. Please upload a resume with your details.";
        setUploadError(msg);
        alert(msg);
        return;
      }

      // Deep content check: reject disguised executables (.exe renamed to .pdf, etc.)
      const contentCheck = await checkFileContent(selectedFile);
      if (!contentCheck.valid) {
        const msg = contentCheck.error || "Invalid or corrupted file content.";
        setUploadError(msg);
        alert(msg);
        return;
      }

      setFile(selectedFile);
      setIsComplete(false);
      setUploadProgress(0);
      setExtractedData(null);
      setMatchData(null);

      const shouldAutoAnalyze = wasReplacingCompletedRef.current && isTermsAccepted;
      if (wasReplacingCompletedRef.current || replaceNotice) {
        setReplaceNotice(`Resume replaced with "${selectedFile.name}".`);
      }
      wasReplacingCompletedRef.current = false;

      if (shouldAutoAnalyze) {
        await handleUpload(selectedFile);
      }
    } else {
      const msg = "Please upload your resume as a PDF, Word document, or text file (.pdf, .docx, .doc, .txt).";
      setUploadError(msg);
      alert(msg);
    }
  };

  const handleReplaceResumeClick = () => {
    wasReplacingCompletedRef.current = isComplete;
    setUploadError(null);
    setShowPreviewModal(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
      fileInputRef.current.click();
    }
    setFile(null);
    setIsComplete(false);
    setIsUploading(false);
    setUploadProgress(0);
    setExtractedData(null);
    setMatchData(null);
    setCooldown(0);
    setReplaceNotice('Previous resume cleared. Select a new resume file to replace it.');
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragover") setIsDragging(true);
    else setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async (overrideFile?: File) => {
    const activeFile = overrideFile instanceof File ? overrideFile : file;
    if (!activeFile || !(activeFile instanceof File) || !isTermsAccepted || cooldown > 0) return;
    setUploadError(null);
    setIsUploading(true);
    setUploadProgress(20); // Initial progress

    try {
      const response = await candidateService.parseResume(activeFile, {
        onUploadProgress: (progressEvent: any) => {
          const total = progressEvent.total || activeFile.size || 1;
          const percentCompleted = Math.round((progressEvent.loaded * 100) / total);
          setUploadProgress(Math.max(20, percentCompleted));
        }
      });
      
      setExtractedData(response.data);
      setIsComplete(true);

      // Save draft progress
      const targetId = job?.job_id || job?.id || jobId;
      if (targetId) {
        try {
          localStorage.setItem(`draft_application_${targetId}`, JSON.stringify({
            jobId: targetId,
            step: 2,
            savedAt: new Date().toISOString(),
            fileName: activeFile?.name || "Uploaded Resume",
            resumeUrl: response.data?.file_url || null,
            extractedData: response.data,
            formData: {
              fullName: response.data?.fullname || "",
              email: response.data?.email || "",
              phone: response.data?.phone || "",
              location: response.data?.location || "",
              jobTitle: response.data?.job_title || "",
              company: response.data?.company || "",
              relevance: response.data?.relevance || "",
              degree: response.data?.degree || response.data?.highest_degree || "",
              college: response.data?.institution || response.data?.college || "",
              skills: Array.isArray(response.data?.skills_list) ? response.data.skills_list : []
            }
          }));
          localStorage.setItem('draft_application_step', '2');
          localStorage.setItem('draft_application_job_id', String(targetId));
        } catch {}
      }

      // Fetch match score for this specific job
      if (job?.job_id) {
        setIsMatching(true);
        try {
          const matchRes = await candidateService.matchData(job.job_id, response.data);
          setMatchData(matchRes.data);
        } catch (matchErr) {
          console.error("Match scoring failed:", matchErr);
        } finally {
          setIsMatching(false);
        }
      }
    } catch (error: any) {
      console.error("Error parsing resume:", error);
      const formattedMsg = formatUploadOrParseError(
        error,
        "Failed to parse resume. Please ensure you uploaded a valid PDF, Word document, or text file."
      );
      setUploadError(formattedMsg);
      alert(formattedMsg);
      if (error?.response?.status === 429) {
        setCooldown(30); // Force a longer cooldown if backend rejected them
      } else {
        setCooldown(10); // 10s cooldown for retries
      }
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Apply | {job ? (job.title || job.job_title) : 'Careers'}</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Reversal of action: Back to Job Details */}
        <button
          onClick={() => {
            const targetJobId = job?.job_id || job?.id || jobId;
            navigate(targetJobId ? `/job-details/${targetJobId}` : '/careerspage', {
              state: job ? { job } : undefined,
              replace: true,
            });
          }}
          className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-6 font-semibold text-sm group"
        >
          <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
          Back to Job Details
        </button>

        {/* Saved Draft Resume Notification */}
        {savedDraft && !isComplete && (
          <div className="mb-6 p-4 sm:p-5 bg-amber-50/90 border border-amber-200/80 rounded-2xl sm:rounded-3xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm animate-in fade-in">
            <div className="flex items-start sm:items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 border border-amber-200">
                <FileText size={20} />
              </div>
              <div>
                <h4 className="text-xs sm:text-sm font-black text-amber-950">
                  You have an unfinished application for this job
                </h4>
                <p className="text-[11px] sm:text-xs text-amber-800 font-medium mt-0.5">
                  We saved your progress from {savedDraft.savedAt ? new Date(savedDraft.savedAt).toLocaleDateString() : 'a previous visit'}. You can continue or start over.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
              <button
                type="button"
                onClick={() => {
                  const targetId = job?.job_id || job?.id || jobId;
                  if (targetId) localStorage.removeItem(`draft_application_${targetId}`);
                  setSavedDraft(null);
                }}
                className="px-3.5 py-2 rounded-xl text-xs font-bold text-amber-900 hover:bg-amber-100/70 transition-colors"
              >
                Start Over
              </button>
              <button
                type="button"
                onClick={handleResumeSavedDraft}
                className="px-4 py-2 rounded-xl text-xs font-black bg-[#D10043] hover:bg-slate-900 text-white transition-colors flex items-center gap-1.5 shadow-sm"
              >
                <span>Continue Application</span>
                <ArrowRight size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Multi-step Application Progress Bar */}
        <ApplicationProgressBar currentStep={1} />

        <div className="bg-white rounded-[40px] shadow-xl shadow-slate-200/60 border border-slate-100 overflow-hidden relative">
          <div className="absolute top-0 right-0 w-64 h-64 bg-red-50 rounded-bl-[200px] -mr-20 -mt-20 opacity-50"></div>

          <div className="p-8 md:p-12 border-b border-slate-50 bg-gradient-to-b from-slate-50/50 to-transparent relative z-10">
            <div className="flex items-center gap-5 mb-6">
              <div className="w-14 h-14 bg-[#D60041] rounded-2xl flex items-center justify-center text-white shadow-lg shadow-pink-100">
                <Briefcase size={28} />
              </div>
              <div>
                <span className="text-[11px] font-bold uppercase tracking-widest text-[#D60041]">Application Portal</span>
                {isLoadingJob ? (
                  <div className="space-y-2 mt-1">
                    <div className="h-8 w-64 bg-slate-200 animate-pulse rounded-lg"></div>
                    <div className="h-4 w-32 bg-slate-100 animate-pulse rounded-md"></div>
                  </div>
                ) : (
                  <>
                    <h1 className="text-2xl md:text-3xl font-black text-slate-900 tracking-tight">
                      {job ? (job.title || job.job_title) : "Position Not Found"}
                    </h1>
                    <p className="text-sm text-slate-500 font-medium">{job?.department} Department</p>
                  </>
                )}
              </div>
            </div>
            <p className="text-slate-500 leading-relaxed">
              Complete your application by uploading your latest resume. Our system will automatically parse your experience for the hiring team.
            </p>
          </div>

          <div className="p-5 sm:p-8 md:p-12">
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                const selected = e.target.files?.[0];
                if (selected) {
                  validateAndSetFile(selected);
                }
                e.target.value = '';
              }}
              className="sr-only"
              accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            />

            {replaceNotice && !uploadError && (
              <div
                role="status"
                data-testid="replace-status-banner"
                className="mb-6 p-4 sm:p-5 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start justify-between gap-3 text-emerald-800 shadow-xs animate-in fade-in duration-200"
              >
                <div className="flex items-start gap-3">
                  <CheckCircle2 size={20} className="text-emerald-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs sm:text-sm font-black text-emerald-900">Resume Management</h4>
                    <p className="text-xs sm:text-sm font-medium text-emerald-700 mt-0.5">{replaceNotice}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setReplaceNotice(null)}
                  className="p-1 text-emerald-400 hover:text-emerald-700 rounded-lg transition-colors cursor-pointer"
                  aria-label="Dismiss notification"
                >
                  <X size={16} />
                </button>
              </div>
            )}

            {uploadError && (
              <div
                role="alert"
                data-testid="upload-error-banner"
                className="mb-6 p-4 sm:p-5 bg-rose-50 border border-rose-200 rounded-2xl flex items-start justify-between gap-3 text-rose-800 shadow-xs animate-in fade-in duration-200"
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle size={20} className="text-rose-600 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-xs sm:text-sm font-black text-rose-900">Resume Upload Error</h4>
                    <p className="text-xs sm:text-sm font-medium text-rose-700 mt-0.5">{uploadError}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setUploadError(null)}
                  className="p-1 text-rose-400 hover:text-rose-700 rounded-lg transition-colors cursor-pointer"
                  aria-label="Dismiss error"
                >
                  <X size={16} />
                </button>
              </div>
            )}

            {!isLoadingJob && job && job.is_active === false ? (
              <div className="text-center py-12 px-4 max-w-lg mx-auto">
                <div className="w-16 h-16 bg-slate-100 text-slate-500 rounded-2xl flex items-center justify-center mx-auto mb-5">
                  <Briefcase size={28} />
                </div>
                <h2 className="text-xl font-black text-slate-900 mb-2">Applications Closed</h2>
                <p className="text-sm text-slate-500 font-medium leading-relaxed mb-6">
                  This position has been archived and is no longer accepting new applications.
                </p>
                <button
                  type="button"
                  onClick={() => navigate('/careerspage')}
                  className="inline-flex items-center gap-2 px-6 py-3 bg-[#D60041] hover:bg-slate-900 text-white rounded-2xl text-sm font-bold transition-colors cursor-pointer"
                >
                  <span>Browse Open Positions</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            ) : !file ? (
              <div
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`group relative border-2 border-dashed rounded-2xl sm:rounded-[32px] p-6 sm:p-12 text-center cursor-pointer transition-all duration-300 ${isDragging
                  ? "border-[#D60041] bg-pink-50/50"
                  : "border-slate-200 hover:border-[#D60041]/30 hover:bg-slate-50"
                  }`}
              >
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-slate-100 text-slate-400 group-hover:text-[#D60041] group-hover:bg-pink-50 rounded-2xl sm:rounded-3xl mb-4 sm:mb-6 flex items-center justify-center mx-auto transition-all duration-300">
                  <FileUp size={32} />
                </div>
                <h3 className="text-base sm:text-lg font-bold mb-1">Upload Resume</h3>
                <p className="text-slate-400 text-xs sm:text-sm mb-6 sm:mb-8 font-medium">Drag and drop or click to browse (PDF, DOCX, or TXT)</p>
                <span className="inline-flex items-center bg-slate-900 text-white px-6 sm:px-8 py-3 sm:py-3.5 rounded-xl sm:rounded-2xl font-bold text-xs sm:text-sm hover:bg-[#D60041] transition-colors shadow-md">
                  Select Document
                </span>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 sm:p-6 bg-slate-50 rounded-2xl sm:rounded-[24px] border border-slate-100 gap-4">
                  <div className="flex items-center min-w-0">
                    <div className="p-3 sm:p-4 bg-white rounded-xl text-[#D60041] shadow-sm mr-3 sm:mr-5 shrink-0">
                      <FileText size={24} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-bold text-sm sm:text-base text-slate-900 truncate">{file.name}</h4>
                      <p className="text-[11px] sm:text-xs text-slate-500 font-medium">{(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to submit</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                    <button
                      id="btn-preview-resume"
                      data-testid="preview-resume-btn"
                      type="button"
                      onClick={() => setShowPreviewModal(true)}
                      className="px-3.5 py-2 bg-white hover:bg-slate-100 text-slate-700 hover:text-[#D60041] border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                      title="Preview Resume"
                    >
                      <Eye size={15} className="text-[#D60041]" />
                      <span>Preview</span>
                    </button>
                    {!isUploading && (
                      <button
                        id="btn-replace-resume"
                        data-testid="replace-resume-btn"
                        type="button"
                        onClick={handleReplaceResumeClick}
                        className="px-3.5 py-2 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                        title="Replace Resume"
                      >
                        <FileUp size={15} />
                        <span>Replace</span>
                      </button>
                    )}
                    {!isUploading && !isComplete && (
                      <button
                        type="button"
                        onClick={() => setFile(null)}
                        className="p-2 sm:p-2.5 hover:bg-white hover:text-red-500 rounded-full transition-all text-slate-400 border border-transparent hover:border-slate-100 shrink-0 cursor-pointer"
                        title="Remove Document"
                      >
                        <X size={18} />
                      </button>
                    )}
                  </div>
                </div>


                {isUploading && (
                  <div className="px-2">
                    <div className="flex justify-between text-xs sm:text-sm font-bold text-slate-700 mb-3">
                      <span className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-[#D60041] rounded-full animate-pulse" />
                        Extracting resume details...
                      </span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                      <div
                        className="bg-[#D60041] h-full transition-all duration-300 ease-out"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                  </div>
                )}
                {isComplete && (
                  <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">
                    <div className="bg-emerald-50/80 border border-emerald-200 p-6 sm:p-8 rounded-[28px] flex items-center gap-5">
                      <div className="bg-white text-emerald-600 p-3.5 rounded-2xl shadow-xs shrink-0 border border-emerald-100">
                        <CheckCircle2 size={32} />
                      </div>
                      <div>
                        <h4 className="text-lg font-black text-slate-900">
                          Resume Attached Successfully
                        </h4>
                        <p className="text-sm text-slate-600 font-medium mt-0.5">
                          We've read your resume for <span className="font-bold text-slate-900">{job ? (job.title || job.job_title) : 'this position'}</span>. Click the button below to review your details.
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3 pt-2">
                      <button
                        id="btn-preview-resume-complete"
                        data-testid="preview-resume-complete-btn"
                        type="button"
                        onClick={() => setShowPreviewModal(true)}
                        className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-4 rounded-2xl font-bold transition-all active:scale-95 flex items-center justify-center gap-2 text-sm cursor-pointer shadow-2xs"
                      >
                        <Eye size={18} className="text-[#D60041]" />
                        <span>Preview Resume</span>
                      </button>
                      <button
                        id="btn-upload-different"
                        data-testid="upload-different-resume-btn"
                        type="button"
                        onClick={handleReplaceResumeClick}
                        className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-4 rounded-2xl font-bold transition-all active:scale-95 flex items-center justify-center gap-2 text-sm cursor-pointer shadow-2xs"
                      >
                        <FileUp size={18} />
                        <span>Upload Different Resume</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleProceedToForm}
                        className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95 text-sm cursor-pointer"
                      >
                        <span>Next: Review your details</span>
                        <ArrowRight size={18} />
                      </button>
                    </div>
                  </div>
                )}

                {!isUploading && !isComplete && (
                  <div className="space-y-5">
                    <div className="flex items-start gap-3 px-2">
                      <div className="flex items-center h-5">
                        <input
                          id="terms"
                          type="checkbox"
                          checked={isTermsAccepted}
                          onChange={(e) => setIsTermsAccepted(e.target.checked)}
                          className="w-5 h-5 text-[#D60041] border-slate-300 rounded focus:ring-[#D60041] cursor-pointer"
                        />
                      </div>
                      <label htmlFor="terms" className="text-sm text-slate-600 font-medium cursor-pointer">
                        I agree to the <button type="button" onClick={() => setShowTermsModal(true)} className="text-[#D60041] hover:underline font-bold">Recruitment Terms & Conditions</button> and data processing policy.
                      </label>
                    </div>

                    <button
                      onClick={() => handleUpload()}
                      disabled={!isTermsAccepted || cooldown > 0}
                      className={`w-full py-4 sm:py-5 rounded-2xl font-bold flex items-center justify-center gap-3 transition-all transform active:scale-95 shadow-xl text-sm ${isTermsAccepted && cooldown === 0
                        ? "bg-[#D60041] hover:bg-slate-900 text-white shadow-pink-100 hover:shadow-none"
                        : "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
                        }`}
                    >
                      <ShieldCheck size={20} />
                      <span>{cooldown > 0 ? `Wait ${cooldown}s` : 'Process Resume & Continue'}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

      </main>

      <ResumePreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        file={file instanceof File ? file : null}
        fileName={file?.name}
        fileUrl={extractedData?.file_url}
        rawText={extractedData?.raw_text}
        extractedData={extractedData}
        onReplaceFile={(newFile) => {
          wasReplacingCompletedRef.current = isComplete;
          setShowPreviewModal(false);
          validateAndSetFile(newFile);
        }}
        onReplace={handleReplaceResumeClick}
      />

      <RecruitmentTermsModal 
        isOpen={showTermsModal} 
        onClose={() => setShowTermsModal(false)} 
        onAccept={() => setIsTermsAccepted(true)} 
      />

      <Footer />
    </div>

  );
};

export default ApplyForJobPage;
