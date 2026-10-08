import React, { useState, useRef, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
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
  Search,
  Check,
  AlertCircle
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import RecruitmentTermsModal from '../../components/modals/shared/RecruitmentTermsModal';

const CandidateSmartUploadPage = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [file, setFile] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [progressStage, setProgressStage] = useState('');
  const [isComplete, setIsComplete] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [isTermsAccepted, setIsTermsAccepted] = useState(false);
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [matchResults, setMatchResults] = useState([]);

  // Cooldown countdown
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

    if (selectedFile && (validTypes.includes(selectedFile.type) || selectedFile.name.endsWith('.pdf') || selectedFile.name.endsWith('.docx') || selectedFile.name.endsWith('.doc'))) {
      setFile(selectedFile);
      setIsComplete(false);
      setUploadProgress(0);
      setExtractedData(null);
      setMatchResults([]);
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

  const handleUploadAndMatch = async () => {
    if (!file || !isTermsAccepted || cooldown > 0) return;

    setIsUploading(true);
    setUploadProgress(15);
    setProgressStage('Uploading and parsing resume document...');

    try {
      // Step 1: Parse Resume
      const parseResponse = await candidateService.parseResume(file, {
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(Math.max(15, Math.min(50, Math.round(percent * 0.5))));
        }
      });

      const extracted = parseResponse.data;
      setExtractedData(extracted);
      setUploadProgress(65);
      setProgressStage('Extracting technical competencies & work history...');

      // Small delay for smooth visual transition
      await new Promise(resolve => setTimeout(resolve, 600));

      setUploadProgress(80);
      setProgressStage('Evaluating compatibility across all open Mariwasa positions...');

      // Step 2: Match Resume against ALL active jobs
      let matches = [];
      try {
        const payload = {
          skills: Array.isArray(extracted?.skills_list)
            ? extracted.skills_list.join(', ')
            : extracted?.skills || '',
          experience: extracted?.relevance || extracted?.experience || '',
          education: extracted?.degree || extracted?.highest_degree || '',
          highest_degree: extracted?.highest_degree || extracted?.degree || '',
          fullname: extracted?.fullname || '',
          location: extracted?.location || ''
        };

        const matchResponse = await candidateService.matchData(null, payload);
        matches = matchResponse.data?.results || matchResponse.data || [];
        setMatchResults(matches);
      } catch (matchErr) {
        console.error('Job matching error:', matchErr);
      }

      setUploadProgress(100);
      setProgressStage('AI matching complete!');
      setIsComplete(true);

    } catch (error) {
      console.error('Smart Upload error:', error);
      if (error.response?.status === 429) {
        alert('High server volume! Please wait 30 seconds before attempting another scan.');
        setCooldown(30);
      } else {
        const detail = error.response?.data?.detail || 'Failed to analyze resume. Please ensure your document contains readable text.';
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

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif] min-h-screen flex flex-col">
      <Helmet>
        <title>AI Smart Match Upload | Candidate Portal</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 max-w-[1360px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 w-full min-w-0">
          
          {/* Back to Find Jobs */}
          <button
            type="button"
            onClick={() => navigate('/candidate/findjobs')}
            className="flex items-center text-xs font-black uppercase tracking-wider text-slate-400 hover:text-[#D10043] transition-colors mb-6 group"
          >
            <ArrowLeft size={16} className="mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Find Jobs
          </button>

          {/* MAIN SMART UPLOAD CONTAINER */}
          <div className="bg-white rounded-[32px] sm:rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden relative">
            
            {/* Ambient Graphic Accent */}
            <div className="absolute top-0 right-0 w-80 h-80 bg-gradient-to-bl from-[#D10043]/10 via-rose-50/40 to-transparent rounded-bl-[300px] pointer-events-none" />

            {/* HEADER HERO */}
            <div className="p-6 sm:p-10 md:p-14 border-b border-slate-100 bg-gradient-to-b from-slate-50/50 to-transparent relative z-10">
              <div className="flex flex-col md:flex-row md:items-center gap-6 sm:gap-8">
                
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-slate-900 rounded-3xl flex items-center justify-center text-white shadow-xl shadow-slate-200 shrink-0">
                  <Cpu size={36} className="text-[#D10043]" />
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 bg-[#D10043]/10 text-[#D10043] rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 border border-[#D10043]/15">
                      <Sparkles size={11} className="animate-pulse" />
                      Candidate AI Matching
                    </span>
                  </div>

                  <h1 className="text-2xl sm:text-4xl md:text-5xl font-black text-slate-900 tracking-tight leading-tight">
                    Smart Match <span className="text-[#D10043]">Upload</span>
                  </h1>

                  <p className="text-xs sm:text-sm md:text-base text-slate-500 font-medium max-w-2xl leading-relaxed">
                    Unsure which job opening fits your background best? Upload your resume and let Mariwasa's automated AI engine parse your skillset, experience, and education to match you with top-ranking career opportunities.
                  </p>
                </div>

              </div>
            </div>

            {/* BODY CONTENT */}
            <div className="p-6 sm:p-10 md:p-14">
              
              {!file ? (
                /* DRAG AND DROP ZONE */
                <div
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-[32px] p-8 sm:p-14 text-center cursor-pointer transition-all duration-300 flex flex-col items-center justify-center min-h-[300px] sm:min-h-[380px] ${
                    isDragging
                      ? 'border-[#D10043] bg-pink-50/40 scale-[0.99]'
                      : 'border-slate-200 hover:border-[#D10043]/50 hover:bg-slate-50/60'
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

                  <div className="w-20 h-20 rounded-3xl bg-slate-50 text-[#D10043] flex items-center justify-center mb-6 shadow-sm border border-slate-100 group-hover:scale-105 transition-transform">
                    <FileUp size={36} />
                  </div>

                  <h3 className="text-xl sm:text-2xl font-black text-slate-900 mb-2 tracking-tight">
                    Drop your resume here, or <span className="text-[#D10043] underline underline-offset-4">browse files</span>
                  </h3>
                  
                  <p className="text-xs sm:text-sm text-slate-400 font-medium max-w-md mx-auto mb-6">
                    Supports PDF and Word documents (.pdf, .docx, .doc) up to 10MB.
                  </p>

                  <div className="flex flex-wrap items-center justify-center gap-4 text-xs font-bold text-slate-500">
                    <span className="flex items-center gap-1.5 bg-slate-100/80 px-3 py-1.5 rounded-full">
                      <ShieldCheck size={14} className="text-emerald-500" />
                      GDPR & Data Privacy Compliant
                    </span>
                    <span className="flex items-center gap-1.5 bg-slate-100/80 px-3 py-1.5 rounded-full">
                      <Zap size={14} className="text-amber-500" />
                      Instant ATS Parsing
                    </span>
                  </div>
                </div>

              ) : (

                /* FILE SELECTED STATE */
                <div className="space-y-8">
                  
                  {/* Selected File Card */}
                  <div className="bg-slate-50 border border-slate-200/80 rounded-3xl p-5 sm:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-[#D10043] shadow-xs border border-slate-100 shrink-0">
                        <FileText size={24} />
                      </div>
                      <div className="min-w-0">
                        <h4 className="text-sm sm:text-base font-black text-slate-900 truncate">
                          {file.name}
                        </h4>
                        <p className="text-xs text-slate-400 font-semibold mt-0.5">
                          {(file.size / (1024 * 1024)).toFixed(2)} MB • Ready for AI matching
                        </p>
                      </div>
                    </div>

                    {!isUploading && !isComplete && (
                      <button
                        type="button"
                        onClick={() => setFile(null)}
                        className="p-2 text-slate-400 hover:text-rose-500 rounded-xl hover:bg-white transition-all self-end sm:self-auto"
                        title="Remove file"
                      >
                        <X size={18} />
                      </button>
                    )}
                  </div>

                  {/* UPLOADING & PROCESSING PROGRESS */}
                  {isUploading && (
                    <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 space-y-4 shadow-sm animate-in fade-in duration-300">
                      <div className="flex items-center justify-between text-xs sm:text-sm font-black">
                        <span className="text-slate-900 flex items-center gap-2">
                          <Cpu size={16} className="text-[#D10043] animate-spin" />
                          {progressStage}
                        </span>
                        <span className="text-[#D10043] font-mono">{uploadProgress}%</span>
                      </div>

                      <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden p-0.5">
                        <div
                          style={{ width: `${uploadProgress}%` }}
                          className="bg-gradient-to-r from-rose-500 to-[#D10043] h-full rounded-full transition-all duration-500"
                        />
                      </div>

                      <p className="text-[11px] text-slate-400 font-medium text-center">
                        Please do not navigate away while our AI calculates role compatibility.
                      </p>
                    </div>
                  )}

                  {/* MATCH COMPLETED SUCCESS CARD */}
                  {isComplete && (
                    <div className="space-y-6 animate-in fade-in zoom-in-95 duration-500">
                      
                      <div className="bg-emerald-50/70 border border-emerald-200 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 shadow-xs">
                        <div className="flex items-center gap-4">
                          <div className="w-14 h-14 bg-white rounded-2xl flex items-center justify-center text-emerald-600 shadow-md shrink-0">
                            <CheckCircle2 size={30} />
                          </div>
                          <div>
                            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-emerald-700">
                              Analysis Complete
                            </span>
                            <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
                              {matchResults.length > 0
                                ? `Discovered ${matchResults.length} Career Matches!`
                                : 'Resume Parsed Successfully'}
                            </h3>
                            <p className="text-xs sm:text-sm text-slate-600 font-medium mt-0.5">
                              {matchResults.length > 0
                                ? `Top match scored at ${Math.round(matchResults[0].match_percentage)}% fit for ${matchResults[0].job_title}.`
                                : 'Your credentials have been extracted and processed.'}
                            </p>
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={handleProceedToMatches}
                          className="w-full sm:w-auto px-8 py-4 rounded-2xl bg-[#D10043] hover:bg-slate-900 text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-xl shadow-[#D10043]/20 active:scale-[0.98] shrink-0"
                        >
                          View Matching Roles ({matchResults.length})
                          <ArrowRight size={16} />
                        </button>
                      </div>

                      {/* Extracted Profile Preview */}
                      {extractedData && (
                        <div className="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 space-y-5">
                          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
                            <h4 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
                              <Sparkles size={16} className="text-[#D10043]" />
                              Extracted Profile Credentials
                            </h4>
                            <span className="text-xs font-bold text-slate-400">AI Summary</span>
                          </div>

                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-1">Full Name</span>
                              <p className="text-sm font-bold text-slate-900 truncate">{extractedData.fullname || 'Candidate'}</p>
                            </div>
                            <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-1">Email</span>
                              <p className="text-sm font-bold text-slate-900 truncate">{extractedData.email || 'N/A'}</p>
                            </div>
                            <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-1">Experience</span>
                              <p className="text-sm font-bold text-slate-900 truncate">{extractedData.years_experience ? `${extractedData.years_experience} Years` : 'Relevant Experience'}</p>
                            </div>
                            <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-1">Highest Degree</span>
                              <p className="text-sm font-bold text-slate-900 truncate">{extractedData.highest_degree || extractedData.degree || 'Degree'}</p>
                            </div>
                          </div>

                          {/* Skills Preview */}
                          {extractedData.skills && (
                            <div className="pt-2">
                              <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-2">Identified Skills</span>
                              <div className="flex flex-wrap gap-1.5">
                                {(typeof extractedData.skills === 'string'
                                  ? extractedData.skills.split(/[|,\n]+/)
                                  : Array.isArray(extractedData.skills)
                                  ? extractedData.skills
                                  : []
                                ).slice(0, 8).map((skill, sIdx) => (
                                  <span
                                    key={sIdx}
                                    className="px-2.5 py-1 rounded-lg text-xs font-bold bg-slate-100 text-slate-700"
                                  >
                                    {skill.trim()}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          <button
                            type="button"
                            onClick={handleProceedToMatches}
                            className="w-full py-4 rounded-2xl bg-slate-900 hover:bg-[#D10043] text-white font-black text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all"
                          >
                            Proceed to Career Match Results
                            <ArrowRight size={16} />
                          </button>
                        </div>
                      )}

                    </div>
                  )}

                  {/* TERMS & AUTHORIZATION (Before upload) */}
                  {!isUploading && !isComplete && (
                    <div className="space-y-6 pt-2">
                      <div className="flex items-start gap-3.5 p-4 bg-slate-50/80 rounded-2xl border border-slate-200/60">
                        <input
                          id="candidate-terms"
                          type="checkbox"
                          checked={isTermsAccepted}
                          onChange={(e) => setIsTermsAccepted(e.target.checked)}
                          className="w-5 h-5 mt-0.5 text-[#D10043] border-slate-300 rounded focus:ring-[#D10043] cursor-pointer"
                        />
                        <label htmlFor="candidate-terms" className="text-xs sm:text-sm text-slate-600 font-medium leading-relaxed cursor-pointer select-none">
                          I confirm that this document represents my authentic credentials and authorize Mariwasa AI to analyze my resume to calculate position fit.{' '}
                          <button
                            type="button"
                            onClick={() => setShowTermsModal(true)}
                            className="text-[#D10043] hover:underline font-bold"
                          >
                            View Recruitment Terms
                          </button>
                          .
                        </label>
                      </div>

                      <button
                        type="button"
                        onClick={handleUploadAndMatch}
                        disabled={!isTermsAccepted || cooldown > 0}
                        className={`w-full py-5 rounded-2xl font-black text-sm uppercase tracking-wider flex items-center justify-center gap-3 transition-all shadow-xl ${
                          isTermsAccepted && cooldown === 0
                            ? 'bg-[#D10043] hover:bg-slate-900 text-white shadow-[#D10043]/20 active:scale-[0.98]'
                            : 'bg-slate-200 text-slate-400 cursor-not-allowed shadow-none'
                        }`}
                      >
                        <ShieldCheck size={20} />
                        <span>{cooldown > 0 ? `Please wait ${cooldown}s` : 'Start Smart Match Analysis'}</span>
                      </button>
                    </div>
                  )}

                </div>
              )}

              {/* Informative Stats Callout */}
              <div className="mt-12 sm:mt-16 grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 pt-8 border-t border-slate-100">
                <div className="p-4 rounded-2xl bg-slate-50/60 border border-slate-100 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <h5 className="text-xs font-black text-slate-900 uppercase tracking-wide">Multi-Factor Scoring</h5>
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">Evaluates skills, tenure, degree relevance, and certifications.</p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-50/60 border border-slate-100 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
                    <Briefcase size={16} />
                  </div>
                  <div>
                    <h5 className="text-xs font-black text-slate-900 uppercase tracking-wide">Direct Applications</h5>
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">Apply with one click to high-match positions directly from results.</p>
                  </div>
                </div>

                <div className="p-4 rounded-2xl bg-slate-50/60 border border-slate-100 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
                    <ShieldCheck size={16} />
                  </div>
                  <div>
                    <h5 className="text-xs font-black text-slate-900 uppercase tracking-wide">Encrypted & Secure</h5>
                    <p className="text-[11px] text-slate-500 font-medium mt-0.5">Your resume data is stored confidentially and protected by privacy protocols.</p>
                  </div>
                </div>
              </div>

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

export default CandidateSmartUploadPage;
