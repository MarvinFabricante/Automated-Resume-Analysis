import React, { useState, useRef, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams } from 'react-router-dom';
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
  Sparkles,
  XCircle,
  Check,
  Layers
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import RecruitmentTermsModal from '../../components/modals/shared/RecruitmentTermsModal';
import ApplicationProgressBar from '../../components/common/ApplicationProgressBar';

const CandidateSmartUpload = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [job, setJob] = useState(null);
  const [jobTitle, setJobTitle] = useState('Position');
  const [isLoadingJob, setIsLoadingJob] = useState(true);

  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [progressStage, setProgressStage] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const [isTermsAccepted, setIsTermsAccepted] = useState(false);
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [matchData, setMatchData] = useState(null);
  const [isMatching, setIsMatching] = useState(false);
  const [cooldown, setCooldown] = useState(0);

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

  const validateAndSetFile = (selectedFile) => {
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
      setFile(selectedFile);
      setIsComplete(false);
      setUploadProgress(0);
      setExtractedData(null);
      setMatchData(null);
    } else {
      alert('Please upload a valid PDF or Microsoft Word document (.pdf, .docx, .doc).');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragover') setIsDragging(true);
    else setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file || !isTermsAccepted || cooldown > 0) return;
    setIsUploading(true);
    setUploadProgress(15);
    setProgressStage('Uploading and parsing resume document...');

    try {
      // 1. Parse Resume
      const response = await candidateService.parseResume(file, {
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
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
    } catch (error) {
      console.error('Error analyzing resume:', error);
      if (error.response?.status === 429) {
        alert('Server is experiencing high volume. Please wait 30 seconds before retrying.');
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

  const getMatchColor = (pct) => {
    if (pct >= 70) return '#10b981'; // emerald
    if (pct >= 40) return '#f59e0b'; // amber
    return '#ef4444'; // rose
  };

  const getMatchTier = (pct) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const handleProceedToDetails = () => {
    navigate(`/candidate/update-profile/${jobId}`, {
      state: {
        fileName: file.name,
        job: { title: jobTitle, job_id: jobId, ...job },
        extractedData,
        matchData,
        personal: {
          name: extractedData?.fullname,
          email: extractedData?.email,
          phone: extractedData?.phone,
          location: extractedData?.location
        },
        experience: {
          title: extractedData?.experience ? extractedData.experience.split('|')[0]?.trim() : '',
          company: extractedData?.experience ? extractedData.experience.split('|')[1]?.trim() : '',
          relevance: extractedData?.years_experience ? `${extractedData.years_experience} years` : ''
        },
        education: {
          degree: extractedData?.highest_degree || extractedData?.degree,
          college: extractedData?.education || extractedData?.institution
        },
        skills: Array.isArray(extractedData?.skills_list) && extractedData.skills_list.length > 0
          ? extractedData.skills_list
          : extractedData?.skills
          ? extractedData.skills.split(' | ').filter(Boolean)
          : [],
        resumeUrl: extractedData?.file_url
      }
    });
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Apply for {jobTitle} | Candidate Portal</title>
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

          {/* Exclusive Application Progress Bar (Step 1 of 3) */}
          <ApplicationProgressBar currentStep={1} />

          {/* MAIN UPLOAD CARD */}
          <div className="bg-white rounded-[32px] sm:rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden relative">
            
            {/* Ambient Background Glow */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-[#D10043]/10 via-rose-50/30 to-transparent rounded-bl-[300px] pointer-events-none" />

            {/* HEADER HERO */}
            <div className="p-6 sm:p-10 md:p-14 border-b border-slate-100 bg-gradient-to-b from-slate-50/60 to-transparent relative z-10">
              <div className="flex flex-col md:flex-row md:items-center gap-6 sm:gap-8">
                
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-slate-900 rounded-3xl flex items-center justify-center text-white shadow-xl shadow-slate-200 shrink-0">
                  <Cpu size={36} className="text-[#D10043]" />
                </div>

                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="px-3 py-1 bg-[#D10043]/10 text-[#D10043] rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 border border-[#D10043]/15">
                      <Zap size={10} fill="currentColor" />
                      Candidate Portal Job Application
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
                    Applying for <span className="text-[#D10043]">{jobTitle}</span>
                  </h1>

                  <p className="text-sm sm:text-base text-slate-500 font-medium max-w-3xl leading-relaxed">
                    Upload your resume to process your application exclusively through the candidate portal. 
                    Our AI parser will analyze your technical competencies and calculate your suitability for this role.
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
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={(e) => validateAndSetFile(e.target.files[0])}
                    className="hidden"
                    accept=".pdf,.doc,.docx"
                  />

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
                    <span>Max Size 10MB</span>
                  </div>
                </div>
              ) : (
                /* FILE PREVIEW & PROCESSING STATES */
                <div className="max-w-4xl mx-auto space-y-8">
                  
                  {/* Selected File Card */}
                  <div className="flex items-center p-6 sm:p-8 bg-slate-50 rounded-[28px] border border-slate-100 shadow-sm relative overflow-hidden group">
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

                    {!isUploading && !isComplete && (
                      <button
                        type="button"
                        onClick={() => {
                          setFile(null);
                          setExtractedData(null);
                          setMatchData(null);
                        }}
                        className="p-3 hover:bg-rose-50 hover:text-rose-600 rounded-2xl transition-colors text-slate-400 shrink-0"
                        title="Remove file"
                      >
                        <X size={20} />
                      </button>
                    )}
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

                  {/* COMPLETED STATE: AI MATCH ANALYSIS & RESUME SUMMARY */}
                  {isComplete && (
                    <div className="space-y-8 animate-in fade-in zoom-in-95 duration-500">
                      
                      {/* Success Banner */}
                      <div className="bg-emerald-50 border border-emerald-100 p-6 sm:p-8 rounded-[28px] flex items-center gap-5">
                        <div className="bg-white text-emerald-600 p-3.5 rounded-2xl shadow-sm shrink-0 border border-emerald-100">
                          <CheckCircle2 size={30} />
                        </div>
                        <div>
                          <h4 className="text-lg font-black text-slate-900">
                            Resume Parsed & Evaluated
                          </h4>
                          <p className="text-sm text-slate-600 font-medium">
                            Your credentials have been matched against <span className="font-bold text-slate-900">{jobTitle}</span>. Review your analysis below and proceed to complete your application.
                          </p>
                        </div>
                      </div>

                      {/* AI Match Breakdown Card */}
                      {matchData && (
                        <div className="bg-white border border-slate-100 rounded-[32px] p-6 sm:p-8 shadow-sm space-y-6">
                          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                            <div className="flex items-center gap-2.5 text-[#D10043]">
                              <Target size={20} />
                              <span className="text-xs font-black uppercase tracking-widest">
                                Role Fit Analysis
                              </span>
                            </div>
                            <span className="px-3 py-1 bg-slate-100 rounded-full text-xs font-bold text-slate-700">
                              {getMatchTier(matchData.match_percentage || 0)}
                            </span>
                          </div>

                          <div className="flex flex-col md:flex-row items-center gap-8">
                            
                            {/* Match Gauge */}
                            <div className="flex flex-col items-center shrink-0">
                              <div className="relative w-32 h-32">
                                <svg className="w-32 h-32 -rotate-90" viewBox="0 0 100 100">
                                  <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" strokeWidth="10" />
                                  <circle
                                    cx="50"
                                    cy="50"
                                    r="42"
                                    fill="none"
                                    stroke={getMatchColor(matchData.match_percentage || 0)}
                                    strokeWidth="10"
                                    strokeDasharray="264 264"
                                    strokeDashoffset={264 - (264 * (matchData.match_percentage || 0)) / 100}
                                    strokeLinecap="round"
                                    className="transition-all duration-1000 ease-out"
                                  />
                                </svg>
                                <div className="absolute inset-0 flex flex-col items-center justify-center pt-1">
                                  <span className="text-3xl font-black text-slate-900 leading-none tracking-tight">
                                    {Math.round(matchData.match_percentage || 0)}%
                                  </span>
                                  <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 mt-1">
                                    Match
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Sub Scores */}
                            <div className="flex-1 grid grid-cols-1 sm:grid-cols-3 gap-3 w-full">
                              <div className="p-4 rounded-2xl bg-blue-50/70 border border-blue-100 flex flex-col text-center">
                                <Cpu size={18} className="mx-auto text-blue-600 mb-1" />
                                <span className="text-xl font-black text-slate-900">
                                  {Math.round(matchData.skills_score || 0)}%
                                </span>
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-0.5">
                                  Skills Fit
                                </span>
                              </div>

                              <div className="p-4 rounded-2xl bg-purple-50/70 border border-purple-100 flex flex-col text-center">
                                <Briefcase size={18} className="mx-auto text-purple-600 mb-1" />
                                <span className="text-xl font-black text-slate-900">
                                  {Math.round(matchData.experience_score || 0)}%
                                </span>
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-0.5">
                                  Experience Fit
                                </span>
                              </div>

                              <div className="p-4 rounded-2xl bg-amber-50/70 border border-amber-100 flex flex-col text-center">
                                <GraduationCap size={18} className="mx-auto text-amber-600 mb-1" />
                                <span className="text-xl font-black text-slate-900">
                                  {Math.round(matchData.education_score || 0)}%
                                </span>
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-500 mt-0.5">
                                  Education Fit
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* AI Summary */}
                          {matchData.ai_summary && (
                            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 text-xs text-slate-600 font-medium leading-relaxed">
                              {matchData.ai_summary}
                            </div>
                          )}

                          {/* Matched & Missing Skills Badges */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                            {matchData.matched_skills?.length > 0 && (
                              <div className="p-4 rounded-2xl bg-emerald-50/50 border border-emerald-100">
                                <span className="block text-[10px] font-black uppercase tracking-widest text-emerald-700 mb-2.5 flex items-center gap-1.5">
                                  <Check size={12} />
                                  Matched Competencies ({matchData.matched_skills.length})
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {matchData.matched_skills.map((skill, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2.5 py-1 bg-white text-emerald-800 text-[11px] font-bold rounded-lg border border-emerald-200"
                                    >
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {matchData.missing_skills?.length > 0 && (
                              <div className="p-4 rounded-2xl bg-rose-50/50 border border-rose-100">
                                <span className="block text-[10px] font-black uppercase tracking-widest text-rose-700 mb-2.5 flex items-center gap-1.5">
                                  <XCircle size={12} />
                                  Additional Skills to Highlight ({matchData.missing_skills.length})
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {matchData.missing_skills.map((skill, idx) => (
                                    <span
                                      key={idx}
                                      className="px-2.5 py-1 bg-white text-rose-700 text-[11px] font-bold rounded-lg border border-rose-200"
                                    >
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Extracted Profile Credentials Preview */}
                      {extractedData && (
                        <div className="bg-slate-50 border border-slate-100 rounded-[32px] p-6 sm:p-8 space-y-4">
                          <h4 className="text-xs font-black uppercase tracking-widest text-slate-400 flex items-center gap-2">
                            <Layers size={14} className="text-[#D10043]" />
                            Parsed Candidate Information
                          </h4>

                          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                            <div className="bg-white p-3.5 rounded-2xl border border-slate-100">
                              <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">Full Name</span>
                              <p className="text-xs font-black text-slate-900 truncate mt-0.5">
                                {extractedData.fullname || 'Extracted Name'}
                              </p>
                            </div>

                            <div className="bg-white p-3.5 rounded-2xl border border-slate-100">
                              <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">Email</span>
                              <p className="text-xs font-black text-slate-900 truncate mt-0.5">
                                {extractedData.email || 'Extracted Email'}
                              </p>
                            </div>

                            <div className="bg-white p-3.5 rounded-2xl border border-slate-100">
                              <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">Experience</span>
                              <p className="text-xs font-black text-slate-900 truncate mt-0.5">
                                {extractedData.years_experience ? `${extractedData.years_experience} Years` : 'Recorded'}
                              </p>
                            </div>

                            <div className="bg-white p-3.5 rounded-2xl border border-slate-100">
                              <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">Education</span>
                              <p className="text-xs font-black text-slate-900 truncate mt-0.5">
                                {extractedData.highest_degree || extractedData.degree || 'Recorded'}
                              </p>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Primary Continue Button */}
                      <button
                        type="button"
                        onClick={handleProceedToDetails}
                        className="w-full bg-slate-900 hover:bg-[#D10043] text-white py-5 rounded-[24px] font-black text-base flex items-center justify-center gap-3 transition-all shadow-xl shadow-slate-200 hover:shadow-[#D10043]/20 hover:-translate-y-0.5 active:scale-[0.99] group"
                      >
                        <span>Proceed to Step 2: Application Details</span>
                        <ArrowRight size={20} className="group-hover:translate-x-1.5 transition-transform" />
                      </button>

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
                        onClick={handleUpload}
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
                            : 'Analyze & Process Application Resume'}
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

      <RecruitmentTermsModal
        isOpen={showTermsModal}
        onClose={() => setShowTermsModal(false)}
        onAccept={() => setIsTermsAccepted(true)}
      />
    </div>
  );
};

export default CandidateSmartUpload;
