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
  Cpu,
  Zap
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import RecruitmentTermsModal from '../../components/modals/shared/RecruitmentTermsModal';

const CandidateSmartUpload = () => {
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
  const { jobId } = useParams();
  const fileInputRef = useRef(null);
  const navigate = useNavigate();
  const [jobTitle, setJobTitle] = useState('Position');

  useEffect(() => {
    const fetchJobDetails = async () => {
      try {
        const response = await jobService.getJobById(jobId);
        if (response.data?.job_title) {
          setJobTitle(response.data.job_title);
          // Store for dashboard "Continue Application" feature
          localStorage.setItem('draft_application_job_title', response.data.job_title);
          localStorage.setItem('draft_application_job_id', jobId);
          localStorage.setItem('draft_application_step', '1');
        }
      } catch (err) {
        console.error("Failed to fetch job title:", err);
      }
    };
    if (jobId) fetchJobDetails();
  }, [jobId]);

  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

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
    setUploadProgress(20);

    try {
      const response = await candidateService.parseResume(file, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(Math.max(20, Math.min(80, percentCompleted))); // Save last 20% for matching
        }
      });
      
      const extracted = response.data;
      setExtractedData(extracted);
      setUploadProgress(100);
      setIsUploading(false);
      setIsComplete(true);
      
      setIsMatching(true);
      try {
        let finalMatchData = null;
        if (jobId) {
          const matchRes = await candidateService.matchData(jobId, extracted);
          finalMatchData = matchRes.data;
        } else {
          const matchRes = await candidateService.matchData(null, extracted);
          finalMatchData = matchRes.data.results;
        }
        setMatchData(finalMatchData);
      } catch (matchErr) {
        console.error("Post-upload match analysis failed:", matchErr);
      } finally {
        setIsMatching(false);
      }
      
    } catch (error) {
      console.error("Error analyzing resume:", error);
      if (error.response?.status === 429) {
        alert("Too many requests! Please wait a moment before trying again.");
        setCooldown(30);
      } else {
        const detail = error.response?.data?.detail || "Failed to analyze resume. Please ensure you uploaded a valid PDF or Word document.";
        alert(detail);
      }
      setIsUploading(false);
      setCooldown(10);
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Apply for {jobTitle} | Candidate Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-7xl mx-auto px-6 py-12 flex-grow">
        <div className="bg-white rounded-[40px] shadow-xl shadow-slate-200/60 border border-slate-100 overflow-hidden relative">
          <div className="absolute top-0 right-0 w-80 h-80 bg-[#D60041]/5 rounded-bl-[300px] -mr-20 -mt-20 opacity-50"></div>

          <div className="p-8 md:p-16 border-b border-slate-50 bg-gradient-to-b from-slate-50/50 to-transparent relative z-10">
            <div className="flex flex-col md:flex-row md:items-center gap-8">
              <div className="w-20 h-20 bg-slate-900 rounded-[28px] flex items-center justify-center text-white shadow-2xl shadow-slate-200 shrink-0">
                <Cpu size={40} className="text-[#D60041]" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="px-3 py-1 bg-red-100 text-[#D60041] rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5">
                    <Zap size={10} fill="currentColor" />
                    Candidate Profile Update
                  </span>
                </div>
                <h1 className="text-3xl md:text-5xl font-black text-slate-900 tracking-tight mb-4">
                  {jobId ? (
                    <>Applying for <span className="text-[#D60041]">{jobTitle}</span></>
                  ) : (
                    <>Smart Match <span className="text-[#D60041]">Portal</span></>
                  )}
                </h1>
                <p className="text-lg text-slate-500 font-medium max-w-2xl leading-relaxed">
                  {jobId 
                    ? "Upload your latest resume to match your profile with this specific position and highlight your relevant skills."
                    : "Not sure which role fits? Upload your resume and our AI will analyze your skills to match you with the perfect career opportunities."
                  }
                </p>
              </div>
            </div>
          </div>

          <div className="p-8 md:p-16">
            {!file ? (
              <div
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current.click()}
                className={`group relative border-2 border-dashed rounded-[40px] p-16 text-center cursor-pointer transition-all duration-500 ${isDragging
                  ? "border-[#D60041] bg-pink-50/50 scale-[0.99] shadow-inner"
                  : "border-slate-200 hover:border-[#D60041]/30 hover:bg-slate-50/50 hover:shadow-lg hover:shadow-slate-100"
                  }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={(e) => validateAndSetFile(e.target.files[0])}
                  className="hidden"
                  accept=".pdf,.doc,.docx"
                />
                <div className="w-24 h-24 bg-slate-100 text-slate-400 group-hover:text-[#D60041] group-hover:bg-white group-hover:shadow-xl group-hover:shadow-pink-100/50 rounded-[32px] mb-8 flex items-center justify-center mx-auto transition-all duration-500 transform group-hover:rotate-6">
                  <FileUp size={48} />
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-2">Upload Latest Resume</h3>
                <p className="text-slate-400 text-base mb-10 font-medium">Drag and drop your file here or click to browse</p>
                <button className="inline-flex items-center bg-slate-900 text-white px-10 py-4 rounded-2xl font-bold text-base hover:bg-[#D60041] transition-all shadow-xl shadow-slate-200 hover:shadow-pink-200 hover:-translate-y-1 active:scale-95">
                  Select New Document
                </button>
                <p className="mt-8 text-xs text-slate-400 font-bold uppercase tracking-widest">Supported formats: PDF, DOCX (Max 10MB)</p>
              </div>
            ) : (
              <div className="max-w-3xl mx-auto space-y-8">
                <div className="flex items-center p-8 bg-slate-50 rounded-[32px] border border-slate-100 shadow-sm relative overflow-hidden group">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                  <div className="p-5 bg-white rounded-2xl text-[#D60041] shadow-md mr-6 relative z-10">
                    <FileText size={32} />
                  </div>
                  <div className="flex-1 min-w-0 relative z-10">
                    <h4 className="text-xl font-black text-slate-900 truncate mb-1">{file.name}</h4>
                    <p className="text-sm text-slate-500 font-bold uppercase tracking-wider">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB • Analysis Ready
                    </p>
                  </div>
                  {!isUploading && !isComplete && (
                    <button
                      onClick={() => setFile(null)}
                      className="p-3 hover:bg-red-50 hover:text-red-500 rounded-full transition-all text-slate-400 border border-transparent hover:border-red-100 relative z-10 active:scale-90"
                    >
                      <X size={24} />
                    </button>
                  )}
                </div>

                {isUploading && (
                  <div className="px-4 space-y-4">
                    <div className="flex justify-between items-end">
                      <div>
                        <span className="block text-[10px] font-black uppercase tracking-[0.2em] text-[#D60041] mb-1">Processing Profile</span>
                        <h4 className="text-lg font-black text-slate-900 flex items-center gap-3">
                          <span className="w-2.5 h-2.5 bg-[#D60041] rounded-full animate-ping" />
                          Extracting Resume Details...
                        </h4>
                      </div>
                      <span className="text-2xl font-black text-slate-900">{uploadProgress}%</span>
                    </div>
                    <div className="w-full bg-slate-100 h-4 rounded-full overflow-hidden p-1 shadow-inner">
                      <div
                        className="bg-gradient-to-r from-[#D60041] to-[#FF4D8D] h-full rounded-full transition-all duration-300 ease-out relative"
                        style={{ width: `${uploadProgress}%` }}
                      >
                        <div className="absolute inset-0 bg-[linear-gradient(45deg,rgba(255,255,255,0.2)_25%,transparent_25%,transparent_50%,rgba(255,255,255,0.2)_50%,rgba(255,255,255,0.2)_75%,transparent_75%,transparent)] bg-[length:20px_20px] animate-[progress-bar-stripes_1s_linear_infinite]"></div>
                      </div>
                    </div>
                  </div>
                )}

                {isComplete && (
                  <div className="space-y-8 animate-in fade-in zoom-in-95 duration-500">
                    <div className="bg-green-50 border border-green-100 p-8 rounded-[32px] flex items-center gap-6 shadow-sm">
                      <div className="bg-white text-green-500 p-4 rounded-2xl shadow-md border border-green-50">
                        <CheckCircle2 size={32} />
                      </div>
                      <div>
                        <h4 className="text-xl font-black text-slate-900">Resume Parsed</h4>
                        <p className="text-slate-600 font-medium">
                          Your credentials are ready to review for your <span className="font-bold text-slate-900">{jobTitle}</span> application.
                          {isMatching ? " Match analysis is running in the background." : ""}
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => navigate('/candidate/update-profile/smart', { 
                        state: { 
                          fileName: file.name, 
                          job: { title: jobTitle }, 
                          extractedData, 
                          matchData,
                          personal: {
                            name: extractedData?.fullname,
                            email: extractedData?.email,
                            phone: extractedData?.phone,
                            location: extractedData?.location
                          },
                          experience: {
                            title: extractedData?.experience ? extractedData.experience.split('|')[0]?.trim() : "",
                            company: extractedData?.experience ? extractedData.experience.split('|')[1]?.trim() : "",
                            relevance: extractedData?.years_experience ? `${extractedData.years_experience} years` : ""
                          },
                          education: {
                            degree: extractedData?.highest_degree,
                            college: extractedData?.education
                          },
                          skills: extractedData?.skills ? extractedData.skills.split(' | ') : [],
                          resumeUrl: extractedData?.file_url
                        } 
                      })}
                      className="w-full bg-slate-900 hover:bg-[#D60041] text-white py-6 rounded-[28px] font-black text-lg flex items-center justify-center gap-4 transition-all shadow-2xl shadow-slate-200 hover:shadow-pink-200 hover:-translate-y-1 active:scale-95 group"
                    >
                      <span>Proceed to Edit Information</span>
                      <ArrowRight size={24} className="group-hover:translate-x-2 transition-transform" />
                    </button>
                  </div>
                )}

                {!isUploading && !isComplete && (
                  <div className="space-y-8">
                    <div className="flex items-start gap-4 px-4">
                      <div className="flex items-center h-6">
                        <input
                          id="terms"
                          type="checkbox"
                          checked={isTermsAccepted}
                          onChange={(e) => setIsTermsAccepted(e.target.checked)}
                          className="w-6 h-6 text-[#D60041] border-slate-300 rounded-lg focus:ring-[#D60041] cursor-pointer transition-all"
                        />
                      </div>
                      <label htmlFor="terms" className="text-sm text-slate-500 font-bold leading-relaxed cursor-pointer select-none">
                        I confirm that this is my current resume and I authorize Mariwasa to update my profile. <button type="button" onClick={() => setShowTermsModal(true)} className="text-[#D60041] hover:underline">View Terms</button>.
                      </label>
                    </div>

                    <button
                      onClick={handleUpload}
                      disabled={!isTermsAccepted || cooldown > 0}
                      className={`w-full py-6 rounded-[28px] font-black text-lg flex items-center justify-center gap-4 transition-all transform shadow-2xl active:scale-95 ${isTermsAccepted && cooldown === 0
                        ? "bg-[#D60041] hover:bg-slate-900 text-white shadow-pink-200 hover:shadow-slate-200 hover:-translate-y-1"
                        : "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
                        }`}
                    >
                      <ShieldCheck size={26} />
                      <span>{cooldown > 0 ? `Wait ${cooldown}s` : 'Process Profile Update'}</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>

      <RecruitmentTermsModal
        isOpen={showTermsModal}
        onClose={() => setShowTermsModal(false)}
        onAccept={() => setIsTermsAccepted(true)}
      />

      </div>

      <style dangerouslySetInnerHTML={{
        __html: `
        @keyframes progress-bar-stripes {
          from { background-position: 20px 0; }
          to { background-position: 0 0; }
        }
      `}} />
    </div>
  );
};

export default CandidateSmartUpload;
