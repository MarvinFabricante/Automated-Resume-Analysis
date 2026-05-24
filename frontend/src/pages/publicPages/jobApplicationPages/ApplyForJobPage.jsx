import React, { useState, useRef, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
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
  Info,
  ArrowRight,
  Target,
  Zap,
  GraduationCap,
  Cpu
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import RecruitmentTermsModal from '../../../components/modals/shared/RecruitmentTermsModal';

const STATIC_JOBS = [
  { job_id: "1", title: "Production Supervisor", department: "Manufacturing" },
  { job_id: "2", title: "Quality Control Analyst", department: "Quality Assurance" },
  { job_id: "3", title: "HR Generalist", department: "Human Resources" },
  { job_id: "4", title: "Maintenance Technician", department: "Engineering" }
];


const ApplyForJobPage = () => {
  const { jobId } = useParams();
  const [job, setJob] = useState(null);
  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);
  const [isTermsAccepted, setIsTermsAccepted] = useState(false);
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [matchData, setMatchData] = useState(null);
  const [isMatching, setIsMatching] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const location = useLocation();
  const [isLoadingJob, setIsLoadingJob] = useState(!location.state?.job);

  useEffect(() => {
    const loadJobData = async () => {
      // 1. Check if job is in navigation state (Fastest)
      if (location.state?.job) {
        setJob(location.state.job);
        setIsLoadingJob(false);
        return;
      }

      // 2. Check static jobs (Fallback)
      const staticJob = STATIC_JOBS.find(j => j.job_id === jobId);
      if (staticJob) {
        setJob(staticJob);
        setIsLoadingJob(false);
        return;
      }

      // 3. Fetch from API (Direct access/Refresh)
      try {
        setIsLoadingJob(true);
        const response = await jobService.getJobById(jobId);
        if (response.data) {
          const fetchedJob = response.data;
          setJob({
            ...fetchedJob,
            title: fetchedJob.job_title || "Untitled Position",
            department: fetchedJob.department || "General"
          });
        }
      } catch (error) {
        console.error("Error fetching job details:", error);
      } finally {
        setIsLoadingJob(false);
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

  const getMatchTier = (pct) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const validateAndSetFile = (selectedFile) => {
    const validTypes = [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ];

    if (selectedFile && validTypes.includes(selectedFile.type)) {
      setFile(selectedFile);
      setIsComplete(false);
      setUploadProgress(0);
    } else {
      alert("Invalid file type. Please upload a PDF or Word document.");
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragover") setIsDragging(true);
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
    setUploadProgress(20); // Initial progress

    try {
      const response = await candidateService.parseResume(file, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(Math.max(20, percentCompleted));
        }
      });
      
      setExtractedData(response.data);
      setIsComplete(true);

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
    } catch (error) {
      console.error("Error parsing resume:", error);
      if (error.response?.status === 429) {
        alert("Too many requests! Please wait a moment before trying again.");
        setCooldown(30); // Force a longer cooldown if backend rejected them
      } else {
        const detail = error.response?.data?.detail || "Failed to parse resume. Please ensure you uploaded a valid PDF or Word document.";
        alert(detail);
      }
    } finally {
      setIsUploading(false);
      if (!isComplete) setCooldown(10); // 10s cooldown for retries
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Apply | {job ? job.title : 'Careers'}</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">

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
                      {job ? job.title : "Position Not Found"}
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

          <div className="p-8 md:p-12">
            {!file ? (
              <div
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current.click()}
                className={`group relative border-2 border-dashed rounded-[32px] p-12 text-center cursor-pointer transition-all duration-300 ${isDragging
                  ? "border-[#D60041] bg-pink-50/50"
                  : "border-slate-200 hover:border-[#D60041]/30 hover:bg-slate-50"
                  }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => validateAndSetFile(e.target.files[0])}
                  className="hidden"
                  accept=".pdf,.doc,.docx"
                />
                <div className="w-20 h-20 bg-slate-100 text-slate-400 group-hover:text-[#D60041] group-hover:bg-pink-50 rounded-3xl mb-6 flex items-center justify-center mx-auto transition-all duration-300">
                  <FileUp size={40} />
                </div>
                <h3 className="text-lg font-bold mb-1">Upload Resume</h3>
                <p className="text-slate-400 text-sm mb-8 font-medium">Drag and drop or click to browse (PDF or DOCX)</p>
                <span className="inline-flex items-center bg-slate-900 text-white px-8 py-3.5 rounded-2xl font-bold text-sm hover:bg-[#D60041] transition-colors shadow-md">
                  Select Document
                </span>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center p-6 bg-slate-50 rounded-[24px] border border-slate-100">
                  <div className="p-4 bg-white rounded-xl text-[#D60041] shadow-sm mr-5">
                    <FileText size={28} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-slate-900 truncate">{file.name}</h4>
                    <p className="text-xs text-slate-500 font-medium">{(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to submit</p>
                  </div>
                  {!isUploading && !isComplete && (
                    <button
                      onClick={() => setFile(null)}
                      className="p-2.5 hover:bg-white hover:text-red-500 rounded-full transition-all text-slate-400 border border-transparent hover:border-slate-100"
                    >
                      <X size={20} />
                    </button>
                  )}
                </div>

                {isUploading && (
                  <div className="px-2">
                    <div className="flex justify-between text-sm font-bold text-slate-700 mb-3">
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
                  <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    {/* Match Analysis Section */}
                    {matchData && (
                      <div className="bg-white border border-slate-100 rounded-[32px] p-8 shadow-sm space-y-8 animate-in fade-in slide-in-from-bottom-2 duration-700">
                        <div className="flex items-center gap-3 text-[#D60041]">
                          <div className="p-2.5 bg-pink-50 rounded-xl">
                            <Target size={20} />
                          </div>
                          <h2 className="font-bold uppercase tracking-widest text-xs">AI Match Analysis</h2>
                        </div>

                        <div className="flex flex-col md:flex-row items-center gap-8">
                          {/* Gauge */}
                          <div className="flex flex-col items-center shrink-0">
                            <div className="relative w-32 h-32">
                              <svg className="w-32 h-32 -rotate-90" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" strokeWidth="10" />
                                <circle
                                  cx="50" cy="50" r="42" fill="none"
                                  stroke={matchData.match_percentage >= 70 ? '#22c55e' : matchData.match_percentage >= 40 ? '#f59e0b' : '#ef4444'}
                                  strokeWidth="10"
                                  strokeDasharray="264 264"
                                  strokeLinecap="round"
                                  className="transition-all duration-1000 ease-out"
                                />
                              </svg>
                              <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <span className="text-sm font-black text-slate-900 leading-none uppercase tracking-wider text-center px-2">Analyzed</span>
                              </div>
                            </div>
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 mt-3">Overall Match</span>
                          </div>

                          {/* Sub-Scores */}
                          <div className="flex-1 grid grid-cols-3 gap-3 w-full">
                            {[
                              { label: 'Skills', score: matchData.skills_score, color: 'text-blue-600', bgColor: 'bg-blue-50', icon: <Cpu size={14} /> },
                              { label: 'Experience', score: matchData.experience_score, color: 'text-purple-600', bgColor: 'bg-purple-50', icon: <Briefcase size={14} /> },
                              { label: 'Education', score: matchData.education_score, color: 'text-amber-600', bgColor: 'bg-amber-50', icon: <GraduationCap size={14} /> }
                            ].map((item, idx) => (
                              <div key={idx} className={`${item.bgColor} ${item.color} p-4 rounded-2xl border border-transparent hover:border-current/10 transition-all text-center group`}>
                                <div className="flex items-center justify-center mb-1 gap-1">
                                  {item.icon}
                                  <span className="text-[9px] font-black uppercase tracking-widest opacity-70 group-hover:opacity-100 transition-opacity">{item.label}</span>
                                </div>
                                <p className="text-lg font-black uppercase tracking-wider">
                                  {item.score >= 70 ? 'High' : item.score >= 40 ? 'Medium' : 'Basic'}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Matched / Missing Skills */}
                        {(matchData.matched_skills?.length > 0 || matchData.missing_skills?.length > 0) && (
                          <div className="pt-6 border-t border-slate-50 space-y-4">
                            {matchData.matched_skills?.length > 0 && (
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-[9px] font-black uppercase tracking-widest text-green-600 mr-2">Matched:</span>
                                {matchData.matched_skills.map((s, i) => (
                                  <span key={i} className="px-3 py-1 bg-green-50 text-green-700 rounded-lg text-xs font-bold border border-green-100/50">{s}</span>
                                ))}
                              </div>
                            )}
                            {matchData.missing_skills?.length > 0 && (
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-[9px] font-black uppercase tracking-widest text-red-500 mr-2">Missing:</span>
                                {matchData.missing_skills.map((s, i) => (
                                  <span key={i} className="px-3 py-1 bg-red-50 text-red-600 rounded-lg text-xs font-bold border border-red-100/50">{s}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Styled Match Analysis Section (Original Design Consistent) */}
                    {matchData && (
                      <div className="bg-white border border-slate-100 rounded-[32px] p-8 shadow-sm space-y-6">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3 text-[#D60041]">
                            <div className="p-2.5 bg-pink-50 rounded-xl">
                              <Target size={20} />
                            </div>
                            <h2 className="font-bold uppercase tracking-widest text-xs">Job Match Analysis</h2>
                          </div>
                          <div className="bg-[#D60041] text-white px-5 py-2 rounded-2xl text-sm font-black shadow-lg shadow-pink-100">
                            {getMatchTier(matchData.match_percentage)}
                          </div>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                          {[
                            { label: 'Skills', score: matchData.skills_score, icon: <Cpu size={16} /> },
                            { label: 'Experience', score: matchData.experience_score, icon: <Briefcase size={16} /> },
                            { label: 'Education', score: matchData.education_score, icon: <GraduationCap size={16} /> }
                          ].map((item, idx) => (
                            <div key={idx} className="bg-slate-50/50 p-5 rounded-[24px] border border-slate-100/50 flex flex-col items-center">
                              <div className="text-slate-400 mb-2">{item.icon}</div>
                              <p className="text-lg font-black uppercase tracking-wider text-slate-900 mb-0.5">
                                {item.score >= 70 ? 'High' : item.score >= 40 ? 'Medium' : 'Basic'}
                              </p>
                              <span className="text-[9px] font-black uppercase tracking-widest text-slate-400">{item.label}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Extracted Data Display */}
                    <div className="bg-slate-50 border border-slate-100 rounded-[32px] p-8 space-y-6">
                      <div className="flex flex-col md:flex-row gap-8 items-start">
                        {extractedData?.profile_image_url && (
                          <div className="shrink-0">
                            <img 
                              src={extractedData.profile_image_url} 
                              alt="Profile" 
                              className="w-32 h-32 rounded-2xl object-cover border-4 border-white shadow-lg"
                            />
                          </div>
                        )}
                        <div className="flex-1">
                          <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-[#D60041] mb-4">Extracted Profile Data</h5>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-10 gap-y-6">
                            {[
                              { label: "Full Name", value: extractedData?.fullname },
                              { label: "Email Address", value: extractedData?.email },
                              { label: "Phone Number", value: extractedData?.phone },
                              { label: "Location", value: extractedData?.location },
                              { label: "Experience", value: extractedData?.experience },
                              { label: "Total Years", value: extractedData?.years_experience },
                              { label: "Education", value: extractedData?.education },
                              { label: "Highest Degree", value: extractedData?.highest_degree }
                            ].map((item, idx) => (
                              <div key={idx} className="space-y-1">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{item.label}</span>
                                <p className="text-sm font-bold text-slate-900 truncate">
                                  {item.value || "null"}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>

                    <button
                      onClick={() => navigate(`/preview-and-verify/${job.job_id}`, { 
                        state: { 
                          job, 
                          fileName: file.name,
                          extractedData,
                          matchData
                        } 
                      })}
                      className="w-full bg-slate-900 hover:bg-[#D60041] text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl hover:shadow-pink-100 active:scale-95"
                    >
                      <span>Proceed to Review Information</span>
                      <ArrowRight size={20} />
                    </button>
                  </div>
                )}

                {!isUploading && !isComplete && (
                  <div className="space-y-6">
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
                      onClick={handleUpload}
                      disabled={!isTermsAccepted}
                      className={`w-full py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all transform active:scale-95 shadow-xl ${isTermsAccepted && cooldown === 0
                        ? "bg-[#D60041] hover:bg-slate-900 text-white shadow-pink-100 hover:shadow-none"
                        : "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
                        }`}
                    >
                      <ShieldCheck size={22} />
                      <span>{cooldown > 0 ? `Wait ${cooldown}s` : 'Submit My Application'}</span>
                    </button>
                  </div>
                )}
              </div>
            )}

            <div className="mt-10 flex items-start p-5 bg-slate-50 rounded-2xl border border-slate-100">
              <Info size={18} className="text-slate-400 mr-4 mt-0.5 shrink-0" />
              <p className="text-[13px] text-slate-600 leading-relaxed font-medium">
                Your privacy matters. We use secure encryption to process your resume. By submitting, you agree to our <button type="button" onClick={() => setShowTermsModal(true)} className="text-[#D60041] hover:underline">recruitment terms</button> and data processing policy.
              </p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-16 border-t border-slate-200 pt-12">
          {[
            { label: "Smart Matching", desc: "AI-powered skill alignment" },
            { label: "Secure Data", desc: "Enterprise-grade encryption" },
            { label: "Direct Access", desc: "Sent straight to the hiring lead" }
          ].map((item, i) => (
            <div key={i} className="flex flex-col items-center text-center">
              <div className="w-10 h-10 bg-white shadow-sm border border-slate-100 rounded-full flex items-center justify-center mb-4 text-[#D60041]">
                <CheckCircle2 size={20} />
              </div>
              <h5 className="text-sm font-bold text-slate-900 mb-1">{item.label}</h5>
              <p className="text-xs text-slate-500 font-medium">{item.desc}</p>
            </div>
          ))}
        </div>

      </main>

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
