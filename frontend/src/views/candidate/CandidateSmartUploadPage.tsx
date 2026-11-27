import React, { useState, useRef, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
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
  Sparkles,
  Zap,
  Briefcase,
  Layers,
  Award,
  GraduationCap,
  Target,
  RefreshCw,
  Compass,
  Building2,
  ChevronRight,
  Eye,
  AlertTriangle
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ResumePreviewModal from '../../components/modals/shared/ResumePreviewModal';
import HelpTooltip from '../../components/common/HelpTooltip';
import ResumeTipsPanel, {
  ResumeReadabilityBanner,
} from '../../components/common/ResumeTipsPanel';
import { formatUploadOrParseError } from '../../utils/errorUtils';

const DIVISIONS = [
  { id: 'ALL', label: 'All Departments' },
  { id: 'MANUFACTURING', label: 'Manufacturing & Operations' },
  { id: 'ENGINEERING', label: 'Engineering & Maintenance' },
  { id: 'QA', label: 'Quality Assurance' },
  { id: 'ADMIN', label: 'Supply Chain & Corporate' }
];

const CandidateSmartUploadPage: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Authenticated candidate state
  const { user: email } = useSelector((state: RootState) => state.auth);
  const fullname = typeof localStorage !== 'undefined' ? (localStorage.getItem('fullname') || 'Candidate') : 'Candidate';

  // Component state
  const [file, setFile] = useState<File | null>(null);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);
  const [selectedDivision, setSelectedDivision] = useState<string>('ALL');
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [progressStage, setProgressStage] = useState<string>('');
  const [isComplete, setIsComplete] = useState<boolean>(false);
  const [cooldown, setCooldown] = useState<number>(0);
  const [isTermsAccepted, setIsTermsAccepted] = useState<boolean>(true); // Pre-accepted for authenticated candidates
  const [extractedData, setExtractedData] = useState<any>(null);
  const [matchResults, setMatchResults] = useState<any[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [replaceNotice, setReplaceNotice] = useState<string | null>(null);
  const wasReplacingCompletedRef = useRef<boolean>(false);

  // Cooldown countdown
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
          error: 'File rejected by content check: The file content is a Windows executable binary (.exe), not a valid document.'
        };
      }

      // Linux ELF executable: 0x7F, 'E', 'L', 'F'
      if (bytes.length >= 4 && bytes[0] === 0x7f && bytes[1] === 0x45 && bytes[2] === 0x4c && bytes[3] === 0x46) {
        return {
          valid: false,
          error: 'File rejected by content check: The file content is an ELF binary executable, not a valid document.'
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
            error: 'File rejected by content check: The file has a .pdf extension but does not contain valid PDF content (disguised or corrupt file).'
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
            error: 'File rejected by content check: The file has a Word extension (.docx/.doc) but does not contain valid Word document content.'
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
        const msg = 'File size exceeds 10MB limit. Please upload a smaller document.';
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
      setMatchResults([]);

      const shouldAutoAnalyze = wasReplacingCompletedRef.current && isTermsAccepted;
      if (wasReplacingCompletedRef.current || replaceNotice) {
        setReplaceNotice(`Resume replaced with "${selectedFile.name}".`);
      }
      wasReplacingCompletedRef.current = false;

      if (shouldAutoAnalyze) {
        await handleUploadAndMatch(selectedFile);
      }
    } else {
      const msg = 'Please upload a valid PDF, Word document, or text file (.pdf, .docx, .doc, .txt).';
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
    setMatchResults([]);
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

  const handleUploadAndMatch = async (overrideFile?: File) => {
    const activeFile = overrideFile instanceof File ? overrideFile : file;
    if (!activeFile || !isTermsAccepted || cooldown > 0) return;

    setUploadError(null);
    setIsUploading(true);
    setUploadProgress(15);
    setProgressStage('Processing resume document...');

    try {
      // Step 1: Parse Resume
      const parseResponse = await candidateService.parseResume(activeFile, {
        onUploadProgress: (progressEvent: any) => {
          const total = progressEvent.total || progressEvent.loaded || activeFile.size || 1;
          const percent = Math.round((progressEvent.loaded * 100) / total);
          setUploadProgress(Math.max(15, Math.min(50, Math.round(percent * 0.5))));
        }
      });

      const extracted = parseResponse.data;
      setExtractedData(extracted);
      setUploadProgress(65);
      setProgressStage('Reading your experience and education...');

      // Small delay for smooth visual transition
      await new Promise((resolve) => setTimeout(resolve, 600));

      setUploadProgress(80);
      setProgressStage('Finding positions that fit you best...');

      // Step 2: Match Resume against ALL active jobs
      let matches: any[] = [];
      try {
        const payload = {
          skills: Array.isArray(extracted?.skills_list)
            ? extracted.skills_list.join(', ')
            : extracted?.skills || '',
          skills_list: extracted?.skills_list || [],
          job_title: extracted?.job_title || '',
          company: extracted?.company || '',
          experience: extracted?.experience || extracted?.relevance || '',
          relevance: extracted?.relevance || '',
          years_experience: extracted?.years_experience || 0,
          work_experiences: extracted?.work_experiences || [],
          education: [extracted?.degree || extracted?.highest_degree, extracted?.institution || extracted?.college].filter(Boolean).join(' - '),
          highest_degree: extracted?.highest_degree || extracted?.degree || '',
          education_entries: extracted?.education_entries || [],
          certifications: extracted?.certifications || undefined,
          completeness_score: extracted?.completeness_score,
          fullname: extracted?.fullname || fullname || '',
          location: extracted?.location || '',
          preferred_department: selectedDivision !== 'ALL' ? selectedDivision : undefined
        };

        const matchResponse = await candidateService.matchData(null, payload);
        matches = matchResponse.data?.results || matchResponse.data || [];
        setMatchResults(matches);
      } catch (matchErr) {
        console.error('Job matching error:', matchErr);
      }

      // Mark that candidate has an uploaded resume in local storage
      try {
        localStorage.setItem('candidate_resume_uploaded', 'true');
        if (extracted?.fullname) localStorage.setItem('fullname', extracted.fullname);
      } catch (storageErr) {
        console.error('Failed to update local storage:', storageErr);
      }

      setUploadProgress(100);
      setProgressStage('Candidate AI analysis complete!');
      setIsComplete(true);
    } catch (error: any) {
      console.error('Candidate Smart Upload error:', error);
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
        setMatchResults([]);
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

  const handleProceedToMatches = () => {
    navigate('/candidate/smart-matches', {
      state: {
        matches: matchResults,
        extractedData,
        fileName: file?.name
      }
    });
  };

  const handleReset = () => {
    setFile(null);
    setIsComplete(false);
    setUploadProgress(0);
    setExtractedData(null);
    setMatchResults([]);
  };

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] min-h-screen flex flex-col">
      <Helmet>
        <title>Upload Your Resume | Mariwasa Recruitment</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 max-w-[1360px] mx-auto px-3.5 sm:px-6 lg:px-8 py-5 sm:py-8 w-full min-w-0">

          {/* TOP BREADCRUMB */}
          <div className="flex items-center justify-between gap-3 mb-6">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
              <button
                type="button"
                onClick={() => navigate('/candidate/dashboard')}
                className="hover:text-slate-800 transition-colors cursor-pointer"
              >
                Dashboard
              </button>
              <span>/</span>
              <span className="text-[#D10043]">Upload Resume</span>
            </div>
          </div>

          {/* MAIN DEDICATED CANDIDATE UPLOAD CONTAINER */}
          <div className="bg-white rounded-2xl sm:rounded-3xl shadow-xs border border-slate-200/80 overflow-hidden relative space-y-6 sm:space-y-8 p-5 sm:p-8 md:p-10">

            {/* Ambient Background Accent */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-[#D10043]/5 via-rose-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

            {/* HERO BANNER */}
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-100">
              <div className="flex items-start sm:items-center gap-4">
                <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white flex items-center justify-center shrink-0 shadow-sm shadow-slate-900/10">
                  <Briefcase size={28} className="text-[#D10043] sm:w-8 sm:h-8" />
                </div>

                <div className="space-y-1 min-w-0">
                  <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight">
                    Upload Your <span className="text-[#D10043]">Resume</span>
                  </h1>

                  <p className="text-xs sm:text-sm text-slate-500 font-medium max-w-2xl leading-relaxed">
                    Upload your resume and we'll show you the jobs that fit you best.
                  </p>
                </div>
              </div>
            </div>

            {/* ATS-Friendly Resume Tips & Readability Check */}
            <div className="relative z-10 space-y-3">
              <ResumeTipsPanel isNewUploadStep uploadResetKey={file?.name || ''} />
              {extractedData?.readability_check && (
                <ResumeReadabilityBanner readabilityCheck={extractedData.readability_check} />
              )}
            </div>

            {/* CANDIDATE DEPARTMENT FILTER */}
            {!isComplete && !isUploading && (
              <div className="space-y-2.5 bg-slate-50/50 p-4 rounded-2xl border border-slate-100">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Compass size={14} className="text-[#D10043]" />
                    Choose a department (optional):
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {DIVISIONS.map((div) => (
                    <button
                      key={div.id}
                      type="button"
                      onClick={() => setSelectedDivision(div.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${selectedDivision === div.id
                          ? 'bg-[#D10043] text-white shadow-2xs'
                          : 'bg-white hover:bg-slate-100 text-slate-600 border border-slate-200/80'
                        }`}
                    >
                      {div.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* UPLOAD WORKSPACE */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                className="sr-only"
                onChange={(e) => {
                  const selected = e.target.files?.[0];
                  if (selected) {
                    validateAndSetFile(selected);
                  }
                  e.target.value = '';
                }}
              />

              {replaceNotice && !uploadError && (
                <div
                  role="status"
                  data-testid="replace-status-banner"
                  className="mb-5 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start justify-between gap-3 text-emerald-800 shadow-2xs animate-in fade-in duration-200"
                >
                  <div className="flex items-start gap-3">
                    <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs sm:text-sm font-black text-emerald-900">Resume Management</h4>
                      <p className="text-xs font-medium text-emerald-700 mt-0.5">{replaceNotice}</p>
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
                  className="mb-5 p-4 bg-rose-50 border border-rose-200 rounded-2xl flex items-start justify-between gap-3 text-rose-800 shadow-2xs animate-in fade-in duration-200"
                >
                  <div className="flex items-start gap-3">
                    <AlertTriangle size={18} className="text-rose-600 shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-xs sm:text-sm font-black text-rose-900">Resume Upload Error</h4>
                      <p className="text-xs font-medium text-rose-700 mt-0.5">{uploadError}</p>
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
                /* DRAG AND DROP ZONE */
                <div>
                  <div
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl sm:rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[260px] sm:min-h-[300px] ${isDragging
                        ? 'border-[#D10043] bg-pink-50/40 scale-[0.99]'
                        : 'border-slate-200 hover:border-[#D10043]/50 hover:bg-slate-50/50'
                      }`}
                  >
                    <div className="w-16 h-16 rounded-2xl bg-rose-50 text-[#D10043] flex items-center justify-center mb-4 shadow-2xs border border-rose-100">
                      <FileUp size={30} />
                    </div>

                    <h3 className="text-lg sm:text-xl font-black text-slate-900 mb-1.5 tracking-tight">
                      Select your resume file, or <span className="text-[#D10043] underline underline-offset-4">browse files</span>
                    </h3>

                    <p className="text-xs text-slate-400 font-medium max-w-md mx-auto mb-5">
                      Supports PDF, Word documents (.docx, .doc), and Text files (.txt) up to 10MB.
                    </p>

                    <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-semibold text-slate-500">
                      <span className="flex items-center gap-1.5 bg-slate-100/90 px-3 py-1 rounded-xl">
                        <ShieldCheck size={14} className="text-emerald-500" />
                        Your information is kept private
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-2 text-xs text-slate-500 font-medium mt-4">
                    <span>We compare your resume with open positions to find your best fit.</span>
                    <HelpTooltip text="Our system compares your skills and experience with open positions to find where you fit best." />
                  </div>
                </div>
              ) : (
                /* FILE SELECTED STATE */
                <div className="space-y-6">

                  {/* Selected File Card */}
                  <div className="bg-slate-50/80 border border-slate-200/80 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3.5 min-w-0">
                      <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center text-[#D10043] shadow-2xs border border-slate-200/60 shrink-0">
                        <FileText size={22} />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-sm sm:text-base font-black text-slate-900 truncate">
                          {file.name}
                        </h4>
                        <p className="text-xs text-slate-400 font-medium mt-0.5">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to find matches
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-auto">
                      <button
                        id="btn-candidate-preview-resume"
                        data-testid="preview-resume-btn"
                        type="button"
                        onClick={() => setShowPreviewModal(true)}
                        className="px-3.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
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
                          className="px-3.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 hover:text-slate-900 border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs cursor-pointer"
                          title="Replace Resume"
                        >
                          <FileUp size={15} />
                          <span>Replace</span>
                        </button>
                      )}
                      {!isUploading && !isComplete && (
                        <button
                          type="button"
                          onClick={handleReset}
                          className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-white rounded-lg transition-colors border border-transparent hover:border-rose-100 cursor-pointer"
                          title="Change file"
                        >
                          <X size={16} />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* UPLOADING & PROCESSING PROGRESS */}
                  {isUploading && (
                    <div className="bg-white border border-slate-200/80 rounded-2xl p-5 sm:p-7 space-y-4 shadow-2xs animate-in fade-in duration-300">
                      <div className="flex items-center justify-between text-xs sm:text-sm font-black">
                        <span className="text-slate-900 flex items-center gap-2">
                          <Cpu size={16} className="text-[#D10043] animate-spin" />
                          {progressStage}
                        </span>
                        <span className="text-[#D10043] font-mono">{uploadProgress}%</span>
                      </div>

                      <div className="w-full bg-slate-100 h-2.5 rounded-full overflow-hidden">
                        <div
                          style={{ width: `${uploadProgress}%` }}
                          className="bg-gradient-to-r from-rose-500 to-[#D10043] h-full rounded-full transition-all duration-500"
                        />
                      </div>

                      <p className="text-[11px] text-slate-400 font-medium text-center">
                        Processing your document in candidate secure memory. Please wait a moment.
                      </p>
                    </div>
                  )}

                  {/* MATCH COMPLETED SUCCESS CARD */}
                  {isComplete && (
                    <div className="space-y-6 animate-in fade-in zoom-in-95 duration-400">

                      <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-2xl p-5 sm:p-7 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-5 shadow-2xs">
                        <div className="flex items-start sm:items-center gap-4">
                          <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center text-emerald-600 shadow-sm border border-emerald-100 shrink-0">
                            <CheckCircle2 size={26} />
                          </div>
                          <div>
                            <span className="text-[10px] font-black uppercase tracking-wider text-emerald-700">
                              Candidate Analysis Complete
                            </span>
                            <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                              {matchResults.length > 0
                                ? `Discovered ${matchResults.length} Matching Positions!`
                                : 'Resume Credentials Extracted'}
                            </h3>
                            <p className="text-xs text-slate-600 font-medium mt-0.5">
                              {matchResults.length > 0
                                ? `Top match scored at ${Math.round(matchResults[0].match_percentage)}% fit for ${matchResults[0].job_title}.`
                                : 'Your profile skills and experience have been stored.'}
                            </p>
                          </div>
                        </div>

                        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 w-full sm:w-auto">
                          <button
                            id="btn-candidate-preview-resume-complete"
                            data-testid="preview-resume-complete-btn"
                            type="button"
                            onClick={() => setShowPreviewModal(true)}
                            className="px-4 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-800 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                          >
                            <Eye size={14} className="text-[#D10043]" />
                            <span>Preview Resume</span>
                          </button>

                          <button
                            type="button"
                            onClick={handleProceedToMatches}
                            className="px-6 py-3 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm shadow-[#D10043]/20 active:scale-[0.98] cursor-pointer"
                          >
                            <span>Review Match Rankings ({matchResults.length})</span>
                            <ArrowRight size={14} />
                          </button>

                          <button
                            type="button"
                            onClick={handleReset}
                            className="px-4 py-3 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                          >
                            <RefreshCw size={13} />
                            <span>Re-scan</span>
                          </button>
                        </div>
                      </div>

                      {/* Extracted Profile Preview */}
                      {extractedData && (
                        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 sm:p-7 space-y-4">
                          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                            <h4 className="text-sm sm:text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
                              <Sparkles size={16} className="text-[#D10043]" />
                              Extracted Candidate Profile Summary
                            </h4>
                            <div className="flex items-center gap-2">
                              {extractedData?.is_incomplete && (
                                <span className="text-[10px] font-black uppercase px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                                  Incomplete: Missing {extractedData.missing_sections?.join(', ') || 'Section'}
                                </span>
                              )}
                              <span className="text-[11px] font-bold text-slate-400">Application Snapshot</span>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-0.5">
                                Candidate Name
                              </span>
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {extractedData.fullname || fullname}
                              </p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-0.5">
                                Email
                              </span>
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {extractedData.email || email}
                              </p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-0.5">
                                Role / Title
                              </span>
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {extractedData.job_title || extractedData.candidate_job_title || 'Role Recorded'}
                              </p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-0.5">
                                Company
                              </span>
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {extractedData.company || extractedData.candidate_company || 'Company Recorded'}
                              </p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-0.5">
                                Experience
                              </span>
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {extractedData.years_experience
                                  ? `${extractedData.years_experience} Years`
                                  : 'Experience Recorded'}
                              </p>
                            </div>
                            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-0.5">
                                Degree
                              </span>
                              <p className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                                {extractedData.degree || extractedData.highest_degree || 'Degree Recorded'}
                              </p>
                            </div>
                          </div>

                          {/* Skills Preview */}
                          {extractedData.skills && (
                            <div className="pt-2">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-2">
                                Identified Skills
                              </span>
                              <div className="flex flex-wrap gap-1.5">
                                {(typeof extractedData.skills === 'string'
                                  ? extractedData.skills.split(/[|,\n]+/)
                                  : Array.isArray(extractedData.skills)
                                    ? extractedData.skills
                                    : []
                                )
                                  .filter(Boolean)
                                  .slice(0, 10)
                                  .map((skill: string, sIdx: number) => (
                                    <span
                                      key={sIdx}
                                      className="px-2.5 py-0.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200/50"
                                    >
                                      {skill.trim()}
                                    </span>
                                  ))}
                              </div>
                            </div>
                          )}

                          {/* Certifications Preview */}
                          {((Array.isArray(extractedData.certifications_list) && extractedData.certifications_list.length > 0) ||
                            extractedData.certifications) && (
                              <div className="pt-2">
                                <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-2">
                                  Certifications & Achievements
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {(Array.isArray(extractedData.certifications_list) && extractedData.certifications_list.length > 0
                                    ? extractedData.certifications_list
                                    : typeof extractedData.certifications === 'string'
                                      ? extractedData.certifications.split('|')
                                      : Array.isArray(extractedData.certifications)
                                        ? extractedData.certifications
                                        : []
                                  )
                                    .map((c: string) => c.trim())
                                    .filter(Boolean)
                                    .map((cert: string, cIdx: number) => (
                                      <span
                                        key={cIdx}
                                        className="px-2.5 py-0.5 rounded-lg text-xs font-semibold bg-rose-50 text-rose-800 border border-rose-200/70"
                                      >
                                        {cert}
                                      </span>
                                    ))}
                                </div>
                              </div>
                            )}

                          <div className="pt-2">
                            <button
                              type="button"
                              onClick={handleProceedToMatches}
                              className="w-full py-3.5 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer"
                            >
                              <span>Proceed to Full Ranked Matches</span>
                              <ArrowRight size={14} />
                            </button>
                          </div>
                        </div>
                      )}

                    </div>
                  )}

                  {/* START ANALYSIS ACTION (Before upload) */}
                  {!isUploading && !isComplete && (
                    <div className="space-y-4 pt-1">
                      <div className="flex items-start gap-2.5 p-3.5 bg-slate-50/70 rounded-xl border border-slate-200/60">
                        <input
                          id="candidate-confirm"
                          type="checkbox"
                          checked={isTermsAccepted}
                          onChange={(e) => setIsTermsAccepted(e.target.checked)}
                          className="w-4 h-4 mt-0.5 text-[#D10043] border-slate-300 rounded focus:ring-[#D10043] cursor-pointer"
                        />
                        <label
                          htmlFor="candidate-confirm"
                          className="text-xs text-slate-600 font-medium leading-relaxed cursor-pointer select-none"
                        >
                          I agree to submit my resume for job matching and recruitment consideration at Mariwasa.
                        </label>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleUploadAndMatch()}
                        disabled={!isTermsAccepted || cooldown > 0}
                        className={`w-full py-4 rounded-xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm ${isTermsAccepted && cooldown === 0
                            ? 'bg-[#D10043] hover:bg-slate-900 text-white shadow-[#D10043]/20 active:scale-[0.98] cursor-pointer'
                            : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                          }`}
                      >
                        <ShieldCheck size={18} />
                        <span>
                          {cooldown > 0
                            ? `Please wait ${cooldown}s`
                            : 'Find Matching Jobs'}
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
        resumeUrl={extractedData?.file_url}
        rawText={extractedData?.raw_text}
        extractedData={extractedData}
        onReplaceFile={(newFile) => {
          wasReplacingCompletedRef.current = isComplete;
          setShowPreviewModal(false);
          validateAndSetFile(newFile);
        }}
        onReplace={handleReplaceResumeClick}
      />
    </div>
  );
};

export default CandidateSmartUploadPage;
