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
  ChevronRight
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

const DIVISIONS = [
  { id: 'ALL', label: 'All Divisions' },
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

  // Cooldown countdown
  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  const validateAndSetFile = (selectedFile: File) => {
    const validTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];

    if (
      selectedFile &&
      (validTypes.includes(selectedFile.type) ||
        selectedFile.name.endsWith('.pdf') ||
        selectedFile.name.endsWith('.docx') ||
        selectedFile.name.endsWith('.doc'))
    ) {
      if (selectedFile.size > 10 * 1024 * 1024) {
        alert('File size exceeds 10MB limit. Please upload a smaller document.');
        return;
      }
      setFile(selectedFile);
      setIsComplete(false);
      setUploadProgress(0);
      setExtractedData(null);
      setMatchResults([]);
    } else {
      alert('Please upload a valid PDF or Microsoft Word document (.pdf, .docx, .doc).');
    }
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

  const handleUploadAndMatch = async () => {
    if (!file || !isTermsAccepted || cooldown > 0) return;

    setIsUploading(true);
    setUploadProgress(15);
    setProgressStage('Ingesting document into candidate ATS sandbox...');

    try {
      // Step 1: Parse Resume
      const parseResponse = await candidateService.parseResume(file, {
        onUploadProgress: (progressEvent: any) => {
          const total = progressEvent.total || progressEvent.loaded;
          const percent = Math.round((progressEvent.loaded * 100) / total);
          setUploadProgress(Math.max(15, Math.min(50, Math.round(percent * 0.5))));
        }
      });

      const extracted = parseResponse.data;
      setExtractedData(extracted);
      setUploadProgress(65);
      setProgressStage('Extracting competencies, tenure & academic degrees...');

      // Small delay for smooth visual transition
      await new Promise((resolve) => setTimeout(resolve, 600));

      setUploadProgress(80);
      setProgressStage('Evaluating compatibility across all open Mariwasa requisitions...');

      // Step 2: Match Resume against ALL active jobs
      let matches: any[] = [];
      try {
        const payload = {
          skills: Array.isArray(extracted?.skills_list)
            ? extracted.skills_list.join(', ')
            : extracted?.skills || '',
          experience: extracted?.relevance || extracted?.experience || '',
          education: extracted?.degree || extracted?.highest_degree || '',
          highest_degree: extracted?.highest_degree || extracted?.degree || '',
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
      if (error.response?.status === 429) {
        alert('Server processing limit reached. Please wait 30 seconds before another scan.');
        setCooldown(30);
      } else {
        const detail =
          error.response?.data?.detail ||
          'Failed to analyze resume. Please ensure your document contains readable text.';
        alert(detail);
      }
      setCooldown(10);
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
        <title>AI Smart Match Upload | Candidate Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 max-w-[1360px] mx-auto px-3.5 sm:px-6 lg:px-8 py-5 sm:py-8 w-full min-w-0">
          
          {/* TOP BREADCRUMB & CANDIDATE CONTEXT */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-400">
              <button
                type="button"
                onClick={() => navigate('/candidate/dashboard')}
                className="hover:text-slate-800 transition-colors cursor-pointer"
              >
                Dashboard
              </button>
              <span>/</span>
              <span className="text-[#D10043]">AI Smart Match</span>
            </div>

            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold text-slate-600 bg-white border border-slate-200/80 shadow-2xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Candidate Session: <strong className="text-slate-900">{email || fullname}</strong>
              </span>
            </div>
          </div>

          {/* MAIN DEDICATED CANDIDATE SMART UPLOAD CONTAINER */}
          <div className="bg-white rounded-2xl sm:rounded-3xl shadow-xs border border-slate-200/80 overflow-hidden relative space-y-6 sm:space-y-8 p-5 sm:p-8 md:p-10">
            
            {/* Ambient Background Accent */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-[#D10043]/5 via-rose-50/30 to-transparent rounded-full blur-3xl pointer-events-none" />

            {/* HERO BANNER */}
            <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-100">
              <div className="flex items-start sm:items-center gap-4">
                <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white flex items-center justify-center shrink-0 shadow-sm shadow-slate-900/10">
                  <Cpu size={28} className="text-[#D10043] sm:w-8 sm:h-8" />
                </div>

                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-[#D10043]/10 text-[#D10043] border border-[#D10043]/15 flex items-center gap-1">
                      <Sparkles size={11} className="animate-pulse" />
                      Candidate AI Matching Engine
                    </span>
                    <span className="text-xs font-semibold text-slate-400 hidden sm:inline">
                      • Automated ATS Alignment
                    </span>
                  </div>

                  <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight leading-tight">
                    Smart Match <span className="text-[#D10043]">Upload</span>
                  </h1>

                  <p className="text-xs sm:text-sm text-slate-500 font-medium max-w-2xl leading-relaxed">
                    Upload your latest resume to automatically evaluate your competencies, work experience, and educational background across all open career requisitions at Mariwasa Siam Ceramics.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0 self-start md:self-center">
                <button
                  type="button"
                  onClick={() => navigate('/candidate/findjobs')}
                  className="px-4 py-2.5 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Briefcase size={14} className="text-slate-400" />
                  <span>Browse Jobs</span>
                </button>
              </div>
            </div>

            {/* CANDIDATE DIVISION FOCUS SELECTOR */}
            {!isComplete && !isUploading && (
              <div className="space-y-2.5 bg-slate-50/50 p-4 rounded-2xl border border-slate-100">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                    <Compass size={14} className="text-[#D10043]" />
                    Target Career Division (Optional):
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium hidden sm:inline">
                    Prioritizes roles in this operational area
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {DIVISIONS.map((div) => (
                    <button
                      key={div.id}
                      type="button"
                      onClick={() => setSelectedDivision(div.id)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        selectedDivision === div.id
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

            {/* ATS SCORING WEIGHTS CARD */}
            {!isComplete && !isUploading && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/70 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-pink-50 text-[#D10043] flex items-center justify-center shrink-0 border border-pink-100">
                    <Target size={16} />
                  </div>
                  <div>
                    <h5 className="text-xs font-black text-slate-900">Skill Alignment (40%)</h5>
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                      Matches technical competencies and industry certifications.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/70 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 border border-blue-100">
                    <Briefcase size={16} />
                  </div>
                  <div>
                    <h5 className="text-xs font-black text-slate-900">Experience & Tenure (40%)</h5>
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                      Evaluates years of service and role relevance.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/70 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0 border border-emerald-100">
                    <GraduationCap size={16} />
                  </div>
                  <div>
                    <h5 className="text-xs font-black text-slate-900">Education Level (20%)</h5>
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">
                      Checks degree requirements and academic discipline.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* UPLOAD WORKSPACE */}
            <div>
              {!file ? (
                /* DRAG AND DROP ZONE */
                <div
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl sm:rounded-3xl p-8 sm:p-12 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[260px] sm:min-h-[320px] ${
                    isDragging
                      ? 'border-[#D10043] bg-pink-50/40 scale-[0.99]'
                      : 'border-slate-200 hover:border-[#D10043]/50 hover:bg-slate-50/50'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        validateAndSetFile(e.target.files[0]);
                      }
                    }}
                  />

                  <div className="w-16 h-16 rounded-2xl bg-rose-50 text-[#D10043] flex items-center justify-center mb-4 shadow-2xs border border-rose-100">
                    <FileUp size={30} />
                  </div>

                  <h3 className="text-lg sm:text-xl font-black text-slate-900 mb-1.5 tracking-tight">
                    Select your resume file, or <span className="text-[#D10043] underline underline-offset-4">browse files</span>
                  </h3>
                  
                  <p className="text-xs text-slate-400 font-medium max-w-md mx-auto mb-5">
                    Supports PDF and Microsoft Word documents (.pdf, .docx, .doc) up to 10MB.
                  </p>

                  <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-semibold text-slate-500">
                    <span className="flex items-center gap-1.5 bg-slate-100/90 px-3 py-1 rounded-xl">
                      <ShieldCheck size={14} className="text-emerald-500" />
                      Candidate Data Privacy Guarded
                    </span>
                    <span className="flex items-center gap-1.5 bg-slate-100/90 px-3 py-1 rounded-xl">
                      <Zap size={14} className="text-amber-500" />
                      Instant ARAS ATS Evaluation
                    </span>
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
                          {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for algorithmic matching
                        </p>
                      </div>
                    </div>

                    {!isUploading && !isComplete && (
                      <button
                        type="button"
                        onClick={handleReset}
                        className="px-3 py-1.5 text-xs font-bold text-slate-500 hover:text-rose-600 hover:bg-white rounded-lg transition-colors flex items-center gap-1 border border-transparent hover:border-rose-100 self-end sm:self-auto cursor-pointer"
                        title="Change file"
                      >
                        <X size={14} />
                        <span>Change File</span>
                      </button>
                    )}
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
                            <span className="text-[11px] font-bold text-slate-400">ATS Snapshot</span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
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
                                {extractedData.highest_degree || extractedData.degree || 'Degree Recorded'}
                              </p>
                            </div>
                          </div>

                          {/* Skills Preview */}
                          {extractedData.skills && (
                            <div className="pt-2">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-2">
                                Identified Skills & Competencies
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
                          I authorize Mariwasa ARAS AI to parse this document against all active job requisitions to calculate competency fit scores and recruitment rankings.
                        </label>
                      </div>

                      <button
                        type="button"
                        onClick={handleUploadAndMatch}
                        disabled={!isTermsAccepted || cooldown > 0}
                        className={`w-full py-4 rounded-xl font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-sm ${
                          isTermsAccepted && cooldown === 0
                            ? 'bg-[#D10043] hover:bg-slate-900 text-white shadow-[#D10043]/20 active:scale-[0.98] cursor-pointer'
                            : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                        }`}
                      >
                        <ShieldCheck size={18} />
                        <span>
                          {cooldown > 0
                            ? `Please wait ${cooldown}s`
                            : 'Run Candidate AI Smart Match'}
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
    </div>
  );
};

export default CandidateSmartUploadPage;
