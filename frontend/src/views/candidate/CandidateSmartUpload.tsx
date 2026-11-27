import React, { useState, useRef, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams } from '@/utils/navigation';
import jobService from '../../services/jobService';
import candidateService from '../../services/candidateService';
import {
  FileUp,
  X,
  FileText,
  CheckCircle2,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  Cpu,
  Zap,
  Briefcase,
  GraduationCap,
  MapPin,
  Clock,
  Target,
  XCircle,
  Check,
  Layers,
  Award,
  BookOpen,
  Phone,
  Mail,
  User,
  Sparkles,
  Building2,
  BadgeCheck,
  Eye,
  AlertTriangle
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import RecruitmentTermsModal from '../../components/modals/shared/RecruitmentTermsModal';
import ResumePreviewModal from '../../components/modals/shared/ResumePreviewModal';
import ApplicationProgressBar from '../../components/common/ApplicationProgressBar';
import ExperienceGapAlert from '../../components/common/ExperienceGapAlert';
import MinimumRequirementBlocker, { isBelowAcceptedRequirements } from '../../components/common/MinimumRequirementBlocker';
import ResumeTipsPanel, {
  ResumeReadabilityBanner,
  ApplySkillsReminder,
} from '../../components/common/ResumeTipsPanel';
import { formatUploadOrParseError } from '../../utils/errorUtils';


const CandidateSmartUpload: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [job, setJob] = useState<any>(null);
  const [jobTitle, setJobTitle] = useState<string>('Position');
  const [isLoadingJob, setIsLoadingJob] = useState<boolean>(true);

  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [progressStage, setProgressStage] = useState<string>('');
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [isTermsAccepted, setIsTermsAccepted] = useState<boolean>(false);
  const [showTermsModal, setShowTermsModal] = useState<boolean>(false);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [extractedData, setExtractedData] = useState<any>(null);
  const [matchData, setMatchData] = useState<any>(null);
  const [isMatching, setIsMatching] = useState<boolean>(false);
  const belowRequirements = isBelowAcceptedRequirements(matchData);
  const [cooldown, setCooldown] = useState<number>(0);
  const [savedDraft, setSavedDraft] = useState<any>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [replaceNotice, setReplaceNotice] = useState<string | null>(null);
  const wasReplacingCompletedRef = useRef<boolean>(false);

  // Check for saved draft progress
  useEffect(() => {
    if (jobId) {
      try {
        const raw = localStorage.getItem(`draft_application_${jobId}`);
        if (raw) {
          const parsed = JSON.parse(raw);
          if (parsed?.extractedData || parsed?.step >= 2) {
            setSavedDraft(parsed);
          }
        }
      } catch {
        // ignore parse error
      }
    }
  }, [jobId]);

  const handleResumeSavedDraft = () => {
    if (!savedDraft) return;
    const targetStep = savedDraft.step || 2;
    if (targetStep === 3) {
      navigate(`/candidate/update-profile/${jobId}?step=3`, {
        state: {
          ...savedDraft,
          job: { title: jobTitle, job_id: jobId, ...job }
        }
      });
    } else if (targetStep >= 4) {
      navigate(`/candidate/preview-profile/${jobId}`, {
        state: {
          ...savedDraft,
          job: { title: jobTitle, job_id: jobId, ...job }
        }
      });
    } else {
      navigate(`/candidate/update-profile/${jobId}`, {
        state: {
          ...savedDraft,
          job: { title: jobTitle, job_id: jobId, ...job }
        }
      });
    }
  };


  // Fetch job details for this specific application
  useEffect(() => {
    if (!jobId) {
      navigate('/candidate/findjobs', { replace: true });
      return;
    }

    const fetchJobDetails = async () => {
      try {
        setIsLoadingJob(true);
        const response = await jobService.getJobById(jobId);
        const data = response.data;
        if (data) {
          const title = data.job_title || data.title || 'Target Position';
          setJobTitle(title);
          setJob({
            id: data.job_id || data.id || jobId,
            job_id: data.job_id || data.id || jobId,
            title,
            department: data.department || 'General Operations',
            location: data.location || 'Sto. Tomas, Batangas',
            job_type: data.job_type || 'Full-Time',
            salary_range: data.salary_range || 'Competitive',
            description: data.description || '',
            skills_requirements: data.skills_requirements || '',
            education_requirements: data.education_requirements || '',
            experience_requirements: data.experience_requirements || ''
          });

          // Store for dashboard "Continue Application" feature
          localStorage.setItem('draft_application_job_title', title);
          localStorage.setItem('draft_application_job_id', jobId);
          localStorage.setItem('draft_application_step', '1');
        }
      } catch (err) {
        console.error('Failed to fetch job details for upload:', err);
      } finally {
        setIsLoadingJob(false);
      }
    };

    fetchJobDetails();
  }, [jobId, navigate]);

  // Cooldown timer
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

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
          error: 'This file is not a supported document. Please upload a PDF or Word document.'
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
            error: 'We could not read this PDF. Please make sure the file is not damaged or empty.'
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
            error: 'We could not read this Word file. Please check that it is a valid .docx or .doc document.'
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
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'text/plain'
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
      if (selectedFile.size === 0) {
        const msg = 'This file is empty (0 bytes). Please upload a valid resume document.';
        setUploadError(msg);
        alert(msg);
        return;
      }

      if (selectedFile.size > 10 * 1024 * 1024) {
        const msg = 'This file is too large. Please upload a file smaller than 10MB.';
        setUploadError(msg);
        alert(msg);
        return;
      }

      // Deep content check: reject disguised executables (.exe renamed to .pdf, etc.)
      const contentCheck = await checkFileContent(selectedFile);
      if (!contentCheck.valid) {
        const msg = contentCheck.error || 'Invalid or corrupted file content.';
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
      const msg = 'Please upload a PDF, Word document, or text file (.pdf, .docx, .doc, .txt).';
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
    if (e.type === 'dragover') setIsDragging(true);
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
    if (!activeFile || !isTermsAccepted || cooldown > 0) return;
    setUploadError(null);
    setIsUploading(true);
    setUploadProgress(15);
    setProgressStage('Uploading and parsing resume document...');

    try {
      // 1. Parse Resume
      const response = await candidateService.parseResume(activeFile, {
        onUploadProgress: (progressEvent: any) => {
          const total = progressEvent.total || progressEvent.loaded || activeFile.size || 1;
          const percent = Math.round((progressEvent.loaded * 100) / total);
          setUploadProgress(Math.max(15, Math.min(60, Math.round(percent * 0.6))));
        }
      });

      const extracted = response.data;
      setExtractedData(extracted);
      setUploadProgress(70);
      setProgressStage(`Analyzing qualifications against ${jobTitle}...`);

      // 2. Match against this specific position
      setIsMatching(true);
      let calculatedMatch = null;
      try {
        const matchRes = await candidateService.matchData(jobId, extracted);
        calculatedMatch = matchRes.data;
        setMatchData(calculatedMatch);
      } catch (matchErr) {
        console.error('Job match scoring failed:', matchErr);
      } finally {
        setIsMatching(false);
      }

      setUploadProgress(100);
      setProgressStage('Analysis complete!');
      setIsComplete(true);

      if (jobId) {
        try {
          localStorage.setItem(`draft_application_${jobId}`, JSON.stringify({
            step: 2,
            jobId,
            jobTitle,
            fileName: activeFile.name,
            extractedData: extracted,
            matchData: calculatedMatch,
            savedAt: new Date().toISOString()
          }));
          localStorage.setItem('draft_application_step', '2');
        } catch {
          // ignore storage error
        }
      }
    } catch (error: any) {
      console.error('Error analyzing resume:', error);
      const formattedMsg = formatUploadOrParseError(
        error,
        'Only resume or CV documents are accepted. Please upload a valid resume file (PDF, DOCX, DOC, or TXT).'
      );
      setUploadError(formattedMsg);
      alert(formattedMsg);
      const status = error?.response?.status;
      if (status === 400 || status === 415 || status === 422) {
        setFile(null);
        setExtractedData(null);
        setMatchData(null);
        setIsComplete(false);
        setUploadProgress(0);
        setCooldown(0);
      } else if (status === 429) {
        setCooldown(30);
      } else {
        setCooldown(10);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const getMatchColor = (pct: number) => {
    if (pct >= 70) return '#10b981'; // emerald
    if (pct >= 40) return '#f59e0b'; // amber
    return '#ef4444'; // rose
  };

  const getMatchTier = (pct: number) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const handleProceedToDetails = () => {
    if (!file || isMatching || belowRequirements) return;
    navigate(`/candidate/update-profile/${jobId}`, {
      state: {
        fileName: file.name,
        file: file,
        job: { title: jobTitle, job_id: jobId, ...job },
        extractedData,
        matchData,
        personal: {
          name: extractedData?.fullname,
          email: extractedData?.email,
          phone: extractedData?.phone,
          location: extractedData?.location,
          location_details: extractedData?.location_details
        },
        experience: {
          title: extractedData?.job_title || extractedData?.work_experiences?.[0]?.job_title || '',
          company: extractedData?.company || extractedData?.work_experiences?.[0]?.company_name || '',
          relevance: extractedData?.relevance || (extractedData?.years_experience ? `${extractedData.years_experience} years` : '')
        },
        education: {
          degree: extractedData?.degree || extractedData?.education_entries?.[0]?.degree_or_course || extractedData?.highest_degree || '',
          college: extractedData?.institution || extractedData?.college || extractedData?.education_entries?.[0]?.institution_name || ''
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
          ? extractedData.skills.split(' | ').filter(Boolean)
          : [],
        resumeUrl: extractedData?.file_url,
        rawText: extractedData?.raw_text || null
      }
    });

  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Apply for {jobTitle} | Mariwasa Recruitment</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 w-full min-w-0">
          
          {/* Back Button */}
          <button
            type="button"
            onClick={() => navigate('/candidate/findjobs')}
            className="flex items-center text-xs font-black uppercase tracking-wider text-slate-400 hover:text-[#D10043] transition-colors mb-6 group"
          >
            <ArrowLeft size={16} className="mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Available Positions
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
                    localStorage.removeItem(`draft_application_${jobId}`);
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

          {/* Application Progress Bar (Step 1 of 4) */}
          <ApplicationProgressBar currentStep={1} />

          {/* ATS-Friendly Resume Tips, Job Skills Reminder & Post-Upload Readability Check */}
          <div className="space-y-3 mb-5">
            <ApplySkillsReminder
              requiredSkills={job?.skills_requirements}
              jobTitle={jobTitle}
            />
            <ResumeTipsPanel isNewUploadStep uploadResetKey={file?.name || ''} />
            {extractedData?.readability_check && (
              <ResumeReadabilityBanner readabilityCheck={extractedData.readability_check} />
            )}
          </div>

          {/* MAIN UPLOAD CARD */}
          <div className="bg-white rounded-[32px] sm:rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden relative">
            
            {/* Ambient Background Glow */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-[#D10043]/10 via-rose-50/30 to-transparent rounded-bl-[300px] pointer-events-none" />

            {/* HEADER HERO */}
            <div className="p-6 sm:p-10 md:p-14 border-b border-slate-100 bg-gradient-to-b from-slate-50/60 to-transparent relative z-10">
              <div className="flex flex-col md:flex-row md:items-center gap-6 sm:gap-8">
                
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-slate-900 rounded-3xl flex items-center justify-center text-white shadow-xl shadow-slate-200 shrink-0">
                  <Briefcase size={36} className="text-[#D10043]" />
                </div>

                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-3 py-1 bg-[#D10043]/10 text-[#D10043] rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 border border-[#D10043]/15">
                      <Zap size={10} fill="currentColor" />
                      Apply for a Job
                    </span>
                    {job?.department && (
                      <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-[10px] font-bold uppercase tracking-wider">
                        {job.department}
                      </span>
                    )}
                    {job?.job_type && (
                      <span className="px-3 py-1 bg-slate-100 text-slate-600 rounded-full text-[10px] font-bold uppercase tracking-wider">
                        {job.job_type}
                      </span>
                    )}
                  </div>

                  <h1 className="text-2xl sm:text-3xl md:text-5xl font-black text-slate-900 tracking-tight">
                    Apply for <span className="text-[#D10043]">{jobTitle}</span>
                  </h1>

                  <p className="text-sm sm:text-base text-slate-500 font-medium max-w-3xl leading-relaxed">
                    Upload your resume to begin. We'll automatically fill in your experience, education, and skills in the next step so you can review them.
                  </p>
                </div>
              </div>

              {/* Job Highlights Quick Strip */}
              {job && (
                <div className="mt-8 pt-6 border-t border-slate-100 flex flex-wrap items-center gap-6 text-xs text-slate-600 font-bold">
                  <div className="flex items-center gap-2">
                    <MapPin size={15} className="text-[#D10043]" />
                    <span>{job.location}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock size={15} className="text-[#D10043]" />
                    <span>{job.job_type}</span>
                  </div>
                  {job.experience_requirements && (
                    <div className="flex items-center gap-2">
                      <Briefcase size={15} className="text-[#D10043]" />
                      <span>{job.experience_requirements}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* BODY SECTION */}
            <div className="p-6 sm:p-10 md:p-14">
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
                  className="max-w-4xl mx-auto mb-6 p-4 sm:p-5 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start justify-between gap-3 text-emerald-800 shadow-2xs animate-in fade-in duration-200"
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
                  className="max-w-4xl mx-auto mb-6 p-4 sm:p-5 bg-rose-50 border border-rose-200 rounded-2xl flex items-start justify-between gap-3 text-rose-800 shadow-2xs animate-in fade-in duration-200"
                >
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={20} className="text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs sm:text-sm font-black text-rose-900">
                        {/wrong document detected/i.test(uploadError) ? 'Wrong Document Detected' : 'Resume Upload Error'}
                      </h4>
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

              {!file ? (
                /* DROPZONE */
                <div
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`group relative border-2 border-dashed rounded-[32px] p-8 sm:p-16 text-center cursor-pointer transition-all duration-300 ${
                    isDragging
                      ? 'border-[#D10043] bg-[#D10043]/5 scale-[0.99] shadow-inner'
                      : 'border-slate-200 hover:border-[#D10043]/40 hover:bg-slate-50/70 hover:shadow-lg hover:shadow-slate-100'
                  }`}
                >
                  <div className="w-20 h-20 sm:w-24 sm:h-24 bg-slate-100 text-slate-400 group-hover:text-[#D10043] group-hover:bg-white group-hover:shadow-xl group-hover:shadow-[#D10043]/10 rounded-[28px] mb-6 flex items-center justify-center mx-auto transition-all duration-300 transform group-hover:scale-110">
                    <FileUp size={44} />
                  </div>

                  <h3 className="text-xl sm:text-2xl font-black text-slate-900 mb-2">
                    Upload Your Resume
                  </h3>
                  <p className="text-slate-400 text-sm sm:text-base mb-8 max-w-md mx-auto font-medium">
                    Drag and drop your document here, or browse your files to apply directly for {jobTitle}
                  </p>

                  <button
                    type="button"
                    className="inline-flex items-center gap-2 bg-slate-900 text-white px-8 sm:px-10 py-3.5 sm:py-4 rounded-2xl font-bold text-sm sm:text-base hover:bg-[#D10043] transition-all shadow-xl shadow-slate-200 active:scale-95"
                  >
                    <FileUp size={18} />
                    Choose Resume Document
                  </button>

                  <div className="mt-8 flex flex-wrap items-center justify-center gap-4 text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <span>PDF (.pdf)</span>
                    <span>•</span>
                    <span>Word (.docx, .doc)</span>
                    <span>•</span>
                    <span>Text (.txt)</span>
                    <span>•</span>
                    <span>Max Size 10MB</span>
                  </div>
                </div>
              ) : (
                /* FILE PREVIEW & PROCESSING STATES */
                <div className="max-w-4xl mx-auto space-y-8">
                  
                  {/* Selected File Card */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 sm:p-8 bg-slate-50 rounded-[28px] border border-slate-100 shadow-sm relative overflow-hidden group gap-4">
                    <div className="flex items-center min-w-0">
                      <div className="p-4 sm:p-5 bg-white rounded-2xl text-[#D10043] shadow-md mr-5 shrink-0">
                        <FileText size={32} />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <h4 className="text-base sm:text-lg font-black text-slate-900 truncate mb-1">
                          {file.name}
                        </h4>
                        <p className="text-xs text-slate-500 font-bold uppercase tracking-wider flex items-center gap-2">
                          <span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                          <span>•</span>
                          <span className="text-emerald-600 font-black">Document Ready</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                      <button
                        id="btn-candidate-preview-resume"
                        data-testid="preview-resume-btn"
                        type="button"
                        onClick={() => setShowPreviewModal(true)}
                        className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 hover:text-[#D10043] border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                        title="Preview Resume"
                      >
                        <Eye size={15} className="text-[#D10043]" />
                        <span>Preview</span>
                      </button>

                      {!isUploading && (
                        <button
                          id="btn-candidate-replace-resume"
                          data-testid="replace-resume-btn"
                          type="button"
                          onClick={handleReplaceResumeClick}
                          className="px-4 py-2 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                          title="Replace Resume"
                        >
                          <FileUp size={15} />
                          <span>Replace</span>
                        </button>
                      )}

                      {!isUploading && !isComplete && (
                        <button
                          type="button"
                          onClick={() => {
                            setFile(null);
                            setExtractedData(null);
                            setMatchData(null);
                          }}
                          className="p-2.5 hover:bg-rose-50 hover:text-rose-600 rounded-xl transition-colors text-slate-400 shrink-0 cursor-pointer"
                          title="Remove file"
                        >
                          <X size={18} />
                        </button>
                      )}
                    </div>
                  </div>


                  {/* UPLOADING / PROCESSING INDICATOR */}
                  {isUploading && (
                    <div className="p-6 bg-slate-50 rounded-[28px] border border-slate-100 space-y-4">
                      <div className="flex justify-between items-end">
                        <div>
                          <span className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#D10043] mb-1">
                            Processing Application Resume
                          </span>
                          <h4 className="text-base sm:text-lg font-black text-slate-900 flex items-center gap-2.5">
                            <span className="w-2.5 h-2.5 bg-[#D10043] rounded-full animate-ping" />
                            {progressStage || 'Extracting Resume Details...'}
                          </h4>
                        </div>
                        <span className="text-2xl font-black text-slate-900">{uploadProgress}%</span>
                      </div>

                      <div className="w-full bg-slate-200 h-3.5 rounded-full overflow-hidden p-0.5">
                        <div
                          className="bg-gradient-to-r from-[#D10043] to-[#FF4D8D] h-full rounded-full transition-all duration-300 ease-out"
                          style={{ width: `${uploadProgress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* COMPLETED STATE: RESUME READY TO PROCEED OR BLOCKED BELOW REQUIREMENTS */}
                  {isComplete && (
                    <div className="space-y-6 animate-in fade-in zoom-in-95 duration-300">
                      {belowRequirements ? (
                        <MinimumRequirementBlocker
                          matchData={matchData}
                          jobTitle={jobTitle}
                          onUploadDifferent={handleReplaceResumeClick}
                          onBrowseJobs={() => navigate('/candidate/findjobs')}
                        />
                      ) : (
                        /* Success Banner */
                        <div className="bg-emerald-50/80 border border-emerald-200 p-6 sm:p-8 rounded-[28px] flex items-center gap-5">
                          <div className="bg-white text-emerald-600 p-3.5 rounded-2xl shadow-xs shrink-0 border border-emerald-100">
                            <CheckCircle2 size={32} />
                          </div>
                          <div className="flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <h4 className="text-lg font-black text-slate-900">
                                Resume Attached Successfully
                              </h4>
                              {matchData?.match_percentage !== undefined && (
                                <span className="px-2.5 py-0.5 rounded-full bg-emerald-600 text-white text-[11px] font-black">
                                  {Math.round(matchData.match_percentage)}% Match
                                </span>
                              )}
                              {extractedData?.page_count > 1 && (
                                <span className="px-2.5 py-0.5 rounded-full bg-white text-emerald-700 border border-emerald-200 text-[11px] font-bold">
                                  {extractedData.page_count} Pages Parsed
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-slate-600 font-medium mt-0.5">
                              {isMatching
                                ? `Evaluating your qualifications against ${jobTitle}...`
                                : `We've processed your resume for ${jobTitle}. Click the button below to review your auto-filled details.`}
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Action Buttons */}
                      <div className="flex flex-col sm:flex-row gap-3 pt-2">
                        <button
                          type="button"
                          onClick={handleReplaceResumeClick}
                          className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-4 rounded-2xl font-bold transition-all active:scale-95 flex items-center justify-center gap-2 text-sm cursor-pointer shadow-2xs"
                        >
                          <FileUp size={18} />
                          <span>Choose a Different File</span>
                        </button>

                        <button
                          type="button"
                          onClick={handleProceedToDetails}
                          disabled={isMatching || belowRequirements}
                          className={`flex-[2] py-4 px-6 rounded-2xl font-black text-sm flex items-center justify-center gap-2.5 transition-all group ${
                            isMatching || belowRequirements
                              ? 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                              : 'bg-[#D10043] hover:bg-slate-900 text-white shadow-xl shadow-[#D10043]/20 active:scale-[0.99] cursor-pointer'
                          }`}
                        >
                          <span>
                            {isMatching
                              ? 'Evaluating Requirements...'
                              : belowRequirements
                              ? 'Below Accepted Requirements'
                              : 'Next: Review your details'}
                          </span>
                          {!isMatching && !belowRequirements && (
                            <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
                          )}
                        </button>
                      </div>
                    </div>
                  )}

                  {/* PRE-UPLOAD TERMS & SUBMIT BUTTON */}
                  {!isUploading && !isComplete && (
                    <div className="space-y-6 pt-2">
                      <div className="flex items-start gap-3.5 p-4 bg-slate-50 rounded-2xl border border-slate-100">
                        <input
                          id="terms"
                          type="checkbox"
                          checked={isTermsAccepted}
                          onChange={(e) => setIsTermsAccepted(e.target.checked)}
                          className="w-5 h-5 mt-0.5 text-[#D10043] border-slate-300 rounded focus:ring-[#D10043] cursor-pointer"
                        />
                        <label htmlFor="terms" className="text-xs text-slate-600 font-medium leading-relaxed select-none cursor-pointer">
                          I confirm that this is my authentic resume and authorize Mariwasa to process my credentials for the <span className="font-bold text-slate-900">{jobTitle}</span> position.{' '}
                          <button
                            type="button"
                            onClick={() => setShowTermsModal(true)}
                            className="text-[#D10043] font-bold hover:underline ml-1"
                          >
                            View Recruitment Terms
                          </button>
                        </label>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleUpload()}
                        disabled={!isTermsAccepted || cooldown > 0}
                        className={`w-full py-5 rounded-[24px] font-black text-base flex items-center justify-center gap-3 transition-all ${
                          isTermsAccepted && cooldown === 0
                            ? 'bg-[#D10043] hover:bg-slate-900 text-white shadow-xl shadow-[#D10043]/20 active:scale-[0.99]'
                            : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                        }`}
                      >
                        <ShieldCheck size={22} />
                        <span>
                          {cooldown > 0
                            ? `Please wait ${cooldown}s`
                            : 'Upload Resume and Continue'}
                        </span>
                      </button>
                    </div>
                  )}

                </div>
              )}

            </div>
          </div>

        </main>
      </div>

      <ResumePreviewModal
        isOpen={showPreviewModal}
        onClose={() => setShowPreviewModal(false)}
        file={file}
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

    </div>
  );
};

export default CandidateSmartUpload;
