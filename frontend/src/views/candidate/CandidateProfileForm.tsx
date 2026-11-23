import React, { useState } from 'react';
import { useLocation, useNavigate, useParams } from '@/utils/navigation';
import candidateService from '../../services/candidateService';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import { Helmet } from 'react-helmet-async';
import {
  User, Mail, Phone, MapPin,
  Briefcase, GraduationCap, Building2,
  FileText, Code, X, Plus,
  ArrowLeft, ArrowRight, CheckCircle2
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ApplicationProgressBar from '../../components/common/ApplicationProgressBar';
import ApplicationSuccessModal from '../../components/modals/shared/ApplicationSuccessModal';
import ClarificationQuestionsPanel from '../../components/common/ClarificationQuestionsPanel';
import ExperienceGapAlert from '../../components/common/ExperienceGapAlert';
import { useJobClarifications } from '../../hooks/useJobClarifications';
import {
  ClarificationQuestion,
  buildCandidateMatchPayload,
  finalizeFormWithClarifications,
  resolveClarifiedYears,
} from '../../utils/clarificationQuestions';
import { isNoValueRequirement } from '../../utils/criterionStatus';
import { useSubmitApplicationMutation } from '../../redux/api/apiSlice';

interface ProfileFormData {
  fullName: string;
  email: string;
  phone: string;
  location: string;
  jobTitle: string;
  company: string;
  relevance: string;
  degree: string;
  college: string;
  skills: string[];
}

const CandidateProfileForm: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId } = useParams<{ jobId: string }>();
  const loggedInEmail = useSelector((state: RootState) => state.auth.user);

  const [currentStep, setCurrentStep] = useState<number>(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('step') === '3') return 3;
      try {
        const saved = localStorage.getItem(`draft_application_${jobId}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (parsed.step === 3) return 3;
        }
      } catch {
        // ignore
      }
    }
    return 2;
  });

  React.useEffect(() => {
    if (jobId) {
      localStorage.setItem('draft_application_step', String(currentStep));
      localStorage.setItem('draft_application_job_id', jobId);
    }
  }, [jobId, currentStep]);

  const savedDraft = typeof window !== 'undefined' && jobId ? (() => {
    try {
      const raw = localStorage.getItem(`draft_application_${jobId}`);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  })() : null;

  const displayFileName = location.state?.fileName || savedDraft?.fileName || location.state?.extractedData?.filename || savedDraft?.extractedData?.filename || 'Uploaded_Resume.pdf';

  const hasUploadContext = Boolean(
    location.state?.extractedData || location.state?.fileName || location.state?.rawText ||
    savedDraft?.extractedData || savedDraft?.fileName
  );
  const ext = location.state?.extractedData || savedDraft?.extractedData;
  const cleanField = (val: any) => {
    if (!val) return "";
    const str = String(val).trim();
    if (
      !str ||
      ["null", "undefined", "not specified", "candidate name", "firstname lastname", "first name last name", "experience not extracted", "position"].includes(str.toLowerCase())
    ) {
      return "";
    }
    return str;
  };
  const cleanDegreeField = (primary: any, fallbackSpecific: any, fallbackTier: any) => {
    const p = cleanField(primary);
    const s = cleanField(fallbackSpecific);
    const t = cleanField(fallbackTier);
    const genericTiers = ["BACHELOR", "MASTER", "DOCTORATE", "ASSOCIATE", "VOCATIONAL", "HIGH SCHOOL"];
    if (p && !genericTiers.includes(p.toUpperCase())) return p;
    if (s && !genericTiers.includes(s.toUpperCase())) return s;
    return p || s || t;
  };
  const accountEmail = typeof loggedInEmail === 'string' ? loggedInEmail : (loggedInEmail as any)?.email || "";
  const storedFullname = typeof window !== 'undefined' ? cleanField(localStorage.getItem('fullname')) : "";
  const initialFormData: ProfileFormData = {
    fullName: cleanField(location.state?.personal?.name) || cleanField(ext?.fullname) || cleanField(savedDraft?.formData?.fullName) || storedFullname || "",
    email: cleanField(location.state?.personal?.email) || cleanField(ext?.email) || cleanField(savedDraft?.formData?.email) || accountEmail || "",
    phone: cleanField(location.state?.personal?.phone) || cleanField(ext?.phone) || cleanField(savedDraft?.formData?.phone) || "",
    location: cleanField(location.state?.personal?.location) || cleanField(ext?.location) || cleanField(savedDraft?.formData?.location) || "",
    jobTitle: cleanField(location.state?.experience?.title) || cleanField(ext?.job_title) || cleanField(ext?.work_experiences?.[0]?.job_title) || cleanField(savedDraft?.formData?.jobTitle) || "",
    company: cleanField(location.state?.experience?.company) || cleanField(ext?.company) || cleanField(ext?.work_experiences?.[0]?.company_name) || cleanField(savedDraft?.formData?.company) || "",
    relevance: cleanField(location.state?.experience?.relevance) || cleanField(ext?.relevance) || cleanField(savedDraft?.formData?.relevance) || (ext?.years_experience ? `${ext.years_experience} years of experience` : ""),
    degree: cleanDegreeField(
      location.state?.education?.degree || ext?.degree,
      ext?.education_entries?.[0]?.degree_or_course || savedDraft?.formData?.degree,
      ext?.highest_degree
    ),
    college: cleanField(location.state?.education?.college) || cleanField(ext?.institution) || cleanField(ext?.college) || cleanField(ext?.education_entries?.[0]?.institution_name) || cleanField(savedDraft?.formData?.college) || "",
    skills: (Array.isArray(location.state?.skills) && location.state.skills.length > 0)
      ? location.state.skills
      : (Array.isArray(ext?.skills_list) && ext.skills_list.length > 0)
      ? ext.skills_list
      : (Array.isArray(savedDraft?.formData?.skills) && savedDraft.formData.skills.length > 0)
      ? savedDraft.formData.skills
      : []
  };

  const [formData, setFormData] = useState<ProfileFormData>(initialFormData);
  const [currentSkill, setCurrentSkill] = useState<string>("");
  const [showSuccessModal, setShowSuccessModal] = useState<boolean>(false);
  const [matchScore, setMatchScore] = useState<number>(location.state?.matchData?.match_percentage || 0);
  const [, setSkillsScore] = useState<number>(location.state?.matchData?.skills_score || 0);
  const [, setExperienceScore] = useState<number>(location.state?.matchData?.experience_score || 0);
  const [, setEducationScore] = useState<number>(location.state?.matchData?.education_score || 0);
  const [, setSkillsReason] = useState<string>(location.state?.matchData?.skills_reason || "");
  const [, setExperienceReason] = useState<string>(location.state?.matchData?.experience_reason || "");
  const [, setEducationReason] = useState<string>(location.state?.matchData?.education_reason || "");
  const [matchData, setMatchData] = useState<any>(location.state?.matchData || null);
  const [, setIsCalculating] = useState<boolean>(false);

  const {
    activeJob,
    jobTitle,
    clarificationQuestions,
    clarificationAnswers,
    setClarificationAnswers,
    recordInitialMatch,
  } = useJobClarifications({
    jobId,
    locationState: location.state,
    onJobChanged: (scopedMatch) => {
      setMatchScore(scopedMatch?.match_percentage || 0);
      setMatchData(scopedMatch);
    },
  });

  const handleClarificationChange = (question: ClarificationQuestion, value: string) => {
    setClarificationAnswers((prev) => ({ ...prev, [question.id]: value }));
  };

  React.useEffect(() => {
    const calculateMatchScore = async () => {
      if (!jobId || (!formData.skills.length && !formData.relevance && !formData.degree)) return;
      if (jobId === 'smart') return;
      setIsCalculating(true);
      try {
        const payload = buildCandidateMatchPayload(
          formData,
          clarificationQuestions,
          clarificationAnswers,
          location.state?.extractedData
        );
        const response = await candidateService.matchData(jobId, payload);
        if (response.data?.match_percentage !== undefined) {
          setMatchScore(response.data.match_percentage);
          setSkillsScore(response.data.skills_score);
          setExperienceScore(response.data.experience_score);
          setEducationScore(response.data.education_score);
          setSkillsReason(response.data.skills_reason);
          setExperienceReason(response.data.experience_reason);
          setEducationReason(response.data.education_reason);
          setMatchData(response.data);
          recordInitialMatch(response.data);
        }
      } catch (err) {
        console.error("Failed to recalculate match score:", err);
      } finally {
        setIsCalculating(false);
      }
    };

    const timeoutId = setTimeout(() => {
      calculateMatchScore();
    }, 800);

    return () => clearTimeout(timeoutId);
  }, [formData, clarificationAnswers, clarificationQuestions, jobId, location.state, recordInitialMatch]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleAddSkill = (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault();
    const trimmed = currentSkill.trim();
    if (trimmed && !isNoValueRequirement(trimmed) && !formData.skills.includes(trimmed)) {
      setFormData(prev => ({
        ...prev,
        skills: [...prev.skills, trimmed]
      }));
      setCurrentSkill("");
    } else if (trimmed && isNoValueRequirement(trimmed)) {
      setCurrentSkill("");
    }
  };

  const handleRemoveSkill = (skillToRemove: string) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(skill => skill !== skillToRemove)
    }));
  };

  const [submitApplication] = useSubmitApplicationMutation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const finalForm = finalizeFormWithClarifications(clarificationQuestions, clarificationAnswers, formData);
    const clarifiedYears = resolveClarifiedYears(
      clarificationQuestions,
      clarificationAnswers,
      location.state?.extractedData?.years_experience,
      finalForm.relevance
    );

    if (!jobId || jobId === 'smart') {
      const updatedExtractedData = {
        ...location.state?.extractedData,
        fullname: finalForm.fullName,
        email: finalForm.email,
        phone: finalForm.phone,
        location: finalForm.location,
        job_title: finalForm.jobTitle,
        company: finalForm.company,
        experience: finalForm.jobTitle + (finalForm.company ? " | " + finalForm.company : ""),
        years_experience: clarifiedYears,
        relevance: finalForm.relevance,
        degree: finalForm.degree,
        highest_degree: finalForm.degree,
        education: finalForm.college,
        college: finalForm.college,
        skills: finalForm.skills.join(' | '),
        skills_list: finalForm.skills,
        clarification_questions: clarificationQuestions,
        clarification_answers: clarificationAnswers,
        file_url: location.state?.resumeUrl || null
      };

      try {
        const payload = {
          skills: finalForm.skills.join(', '),
          skills_list: finalForm.skills,
          experience: finalForm.relevance,
          years_experience: clarifiedYears,
          work_experiences: location.state?.extractedData?.work_experiences || [],
          education: [finalForm.degree, finalForm.college].filter(Boolean).join(' - '),
          highest_degree: finalForm.degree,
          education_entries: location.state?.extractedData?.education_entries || [],
          certifications: location.state?.extractedData?.certifications || undefined,
          fullname: finalForm.fullName,
          location: finalForm.location
        };
        const matchRes = await candidateService.matchData(null, payload);
        const matches = matchRes.data.results || [];
        navigate(`/candidate/smart-matches`, {
          state: {
            matches,
            extractedData: updatedExtractedData,
            fileName: location.state?.fileName
          }
        });
      } catch (err) {
        console.error("Failed to fetch smart matches:", err);
        alert("Failed to fetch job matches. Please try again.");
      }
      return;
    }

    // Advance to Step 4: Submit & Review in Candidate Portal
    localStorage.setItem('draft_application_step', '4');
    try {
      const prev = JSON.parse(localStorage.getItem(`draft_application_${jobId}`) || '{}');
      localStorage.setItem(`draft_application_${jobId}`, JSON.stringify({
        ...prev,
        step: 4,
        detailsConfirmed: true,
        questionsConfirmed: true,
        formData: finalForm,
        clarificationAnswers,
        savedAt: new Date().toISOString()
      }));
    } catch { }
    navigate(`/candidate/preview-profile/${jobId}`, {
      state: {
        job: activeJob || { title: jobTitle, job_id: jobId },
        file: location.state?.file,
        fileName: location.state?.fileName,
        resumeUrl: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
        rawText: location.state?.rawText || location.state?.extractedData?.raw_text || null,
        formData: finalForm,
        clarificationQuestions,
        clarificationAnswers,
        extractedData: {
          ...location.state?.extractedData,
          fullname: finalForm.fullName,
          email: finalForm.email || accountEmail,
          phone: finalForm.phone,
          location: finalForm.location,
          job_title: finalForm.jobTitle,
          company: finalForm.company,
          relevance: finalForm.relevance,
          years_experience: clarifiedYears,
          degree: finalForm.degree,
          college: finalForm.college,
          skills: finalForm.skills.join(' | '),
          skills_list: finalForm.skills,
          clarification_questions: clarificationQuestions,
          clarification_answers: clarificationAnswers,
          resumeUrl: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
          raw_text: location.state?.rawText || location.state?.extractedData?.raw_text || null
        },
        personal: {
          name: finalForm.fullName,
          email: finalForm.email || accountEmail,
          phone: finalForm.phone,
          location: finalForm.location
        },
        experience: {
          title: finalForm.jobTitle,
          company: finalForm.company,
          relevance: finalForm.relevance
        },
        education: {
          degree: finalForm.degree,
          college: finalForm.college
        },
        skills: finalForm.skills,
        matchData,
        matchScore
      }
    });
  };

  const handleFinalRedirect = () => {
    setShowSuccessModal(false);
    navigate('/candidate/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Edit Application | {jobTitle}</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-12 flex-grow min-w-0 w-full overflow-hidden">
          {/* Back navigation */}
          <button
            onClick={() => {
              if (currentStep === 3) {
                setCurrentStep(2);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              } else {
                navigate(jobId ? `/candidate/upload-resume/${jobId}` : '/candidate/upload-resume', { state: location.state });
              }
            }}
            className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-6 font-semibold text-sm group cursor-pointer"
          >
            <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
            <span>{currentStep === 3 ? 'Back to Review Details' : 'Back to Resume Upload'}</span>
          </button>

          {jobId && <ApplicationProgressBar currentStep={currentStep} />}

          <div className="mb-8 sm:mb-10 flex flex-col md:flex-row md:items-center justify-between gap-4 sm:gap-6">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="px-3 py-1 bg-[#D10043]/10 text-[#D10043] rounded-full text-[10px] font-black uppercase tracking-widest">
                  Step {currentStep} of 4
                </span>
                <span className="text-xs font-bold text-slate-400">
                  {currentStep === 2 ? 'Review your details' : 'Answer a few questions'}
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight mb-2 break-words">
                {currentStep === 2 ? 'Review Your Application Details' : 'A Few Follow-up Questions'}
              </h1>
              <p className="text-slate-500 font-medium text-sm sm:text-base">
                {currentStep === 2
                  ? `Review the information below for ${jobTitle}. You can update any field before moving forward.`
                  : `These short questions help the hiring team evaluate your experience for ${jobTitle}.`}
              </p>
            </div>

            <div className="flex items-center gap-3 sm:gap-4 bg-white p-3 pr-4 sm:pr-6 rounded-2xl border border-slate-100 shadow-sm w-full md:w-auto">
              <div className="w-12 h-12 sm:w-16 sm:h-16 rounded-xl bg-slate-50 border border-slate-100 overflow-hidden flex items-center justify-center text-slate-300 shrink-0">
                {localStorage.getItem('profile_image_url') ? (
                  <img src={localStorage.getItem('profile_image_url')!} alt="Profile" className="w-full h-full object-cover" />
                ) : (
                  <User size={28} className="sm:w-8 sm:h-8" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Application Identity</p>
                <p className="text-xs sm:text-sm font-black text-slate-900 truncate">{formData.fullName}</p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6 sm:space-y-8">

            {/* STEP 3 CONTENT: FOLLOW-UP QUESTIONS ONLY */}
            {currentStep === 3 && (
              <div className="space-y-6">
                {clarificationQuestions && clarificationQuestions.length > 0 ? (
                  <ClarificationQuestionsPanel
                    questions={clarificationQuestions}
                    answers={clarificationAnswers}
                    onAnswerChange={handleClarificationChange}
                    reasons={location.state?.extractedData?.clarification_reasons || location.state?.clarification_reasons}
                    jobTitle={jobTitle}
                  />
                ) : (
                  <div className="bg-white p-8 sm:p-12 rounded-3xl border border-slate-200/80 text-center max-w-2xl mx-auto space-y-4 shadow-xs">
                    <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-100">
                      <CheckCircle2 size={32} />
                    </div>
                    <h3 className="text-xl font-black text-slate-900 tracking-tight">No Additional Questions Required</h3>
                    <p className="text-sm text-slate-500 font-medium leading-relaxed">
                      All necessary qualifications were detected from your resume. You're ready to review and submit your application.
                    </p>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-6 border-t border-slate-200">
                  <button
                    type="button"
                    onClick={() => {
                      setCurrentStep(2);
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }}
                    className="w-full sm:w-auto px-8 py-4 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 rounded-[20px] font-bold transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
                  >
                    <ArrowLeft size={18} />
                    <span>Back: Review your details</span>
                  </button>
                  <button
                    type="submit"
                    className="w-full sm:w-auto px-10 py-4 bg-[#D10043] hover:bg-slate-900 text-white rounded-[20px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-[0.98] cursor-pointer"
                  >
                    <span>Next: Review & Submit</span>
                    <ArrowRight size={20} />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2 CONTENT: DETAILS FORM ONLY */}
            {currentStep === 2 && (
              <>
                {/* STEP 1 DONE: RESUME UPLOADED BANNER */}
                <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 shadow-2xs">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                      <CheckCircle2 size={20} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-black uppercase tracking-wider text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          Step 1 Done
                        </span>
                        <span className="text-xs font-bold text-slate-700">Resume uploaded</span>
                      </div>
                      <p className="text-xs font-semibold text-slate-900 truncate mt-0.5 max-w-xs sm:max-w-md">
                        {displayFileName}
                      </p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => navigate(jobId ? `/candidate/upload-resume/${jobId}` : '/candidate/upload-resume')}
                    className="px-3.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs self-end sm:self-auto cursor-pointer"
                  >
                    <FileText size={14} className="text-[#D10043]" />
                    <span>Change resume</span>
                  </button>
                </div>

                <section className="bg-white p-5 sm:p-8 md:p-10 rounded-2xl sm:rounded-[32px] shadow-sm border border-slate-100">
                  <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                    <div className="p-2.5 bg-pink-50 rounded-xl">
                      <User size={20} />
                    </div>
                    <h2 className="font-bold uppercase tracking-widest text-sm">Personal Details</h2>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <InputField
                      icon={<User size={18} />}
                      label="Full Name"
                      name="fullName"
                      value={formData.fullName}
                      onChange={handleChange}
                      placeholder="e.g. John Doe"
                    />
                    <InputField
                      icon={<Mail size={18} />}
                      label="Email Address"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="john@example.com"
                    />
                    <InputField
                      icon={<Phone size={18} />}
                      label="Phone Number"
                      name="phone"
                      value={formData.phone}
                      onChange={handleChange}
                      placeholder="+1 (555) 000-0000"
                    />
                    <InputField
                      icon={<MapPin size={18} />}
                      label="Primary Location"
                      name="location"
                      value={formData.location}
                      onChange={handleChange}
                      placeholder="City, State/Country"
                    />
                  </div>
                </section>

                <section className="bg-white p-5 sm:p-8 md:p-10 rounded-2xl sm:rounded-[32px] shadow-sm border border-slate-100">
                  <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                    <div className="p-2.5 bg-pink-50 rounded-xl">
                      <Briefcase size={20} />
                    </div>
                    <h2 className="font-bold uppercase tracking-widest text-sm">Current/Latest Experience</h2>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                    <InputField
                      icon={<Briefcase size={18} />}
                      label="Job Title"
                      name="jobTitle"
                      value={formData.jobTitle}
                      onChange={handleChange}
                      placeholder="e.g. Software Engineer"
                    />
                    <InputField
                      icon={<Building2 size={18} />}
                      label="Company Name"
                      name="company"
                      value={formData.company}
                      onChange={handleChange}
                      placeholder="e.g. Acme Corp"
                    />
                  </div>

                  <div className="w-full">
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                      Professional Bio / Experience Summary
                    </label>
                    <div className="relative">
                      <div className="absolute top-4 left-4 text-slate-400">
                        <FileText size={18} />
                      </div>
                      <textarea
                        name="relevance"
                        value={formData.relevance}
                        onChange={handleChange}
                        rows={3}
                        className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3 pl-12 pr-4 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all resize-none"
                        placeholder="Summarize your professional background..."
                      ></textarea>
                    </div>
                  </div>
                </section>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8">
                  <section className="bg-white p-5 sm:p-8 md:p-10 rounded-2xl sm:rounded-[32px] shadow-sm border border-slate-100">
                    <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                      <div className="p-2.5 bg-pink-50 rounded-xl">
                        <GraduationCap size={20} />
                      </div>
                      <h2 className="font-bold uppercase tracking-widest text-sm">Highest Education</h2>
                    </div>

                    <div className="space-y-6">
                      <InputField
                        icon={<GraduationCap size={18} />}
                        label="Degree / Qualification"
                        name="degree"
                        value={formData.degree}
                        onChange={handleChange}
                        placeholder="e.g. B.S. Computer Science"
                      />
                      <InputField
                        icon={<Building2 size={18} />}
                        label="University / Institution"
                        name="college"
                        value={formData.college}
                        onChange={handleChange}
                        placeholder="e.g. University of Technology"
                      />
                    </div>
                  </section>

                  <section className="bg-white p-5 sm:p-8 md:p-10 rounded-2xl sm:rounded-[32px] shadow-sm border border-slate-100 flex flex-col">
                    <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                      <div className="p-2.5 bg-pink-50 rounded-xl">
                        <Code size={20} />
                      </div>
                      <h2 className="font-bold uppercase tracking-widest text-sm">Skills Portfolio</h2>
                    </div>

                    <div className="mb-4 relative">
                      <input
                        type="text"
                        value={currentSkill}
                        onChange={(e) => setCurrentSkill(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleAddSkill(e)}
                        placeholder="Add a skill and hit Enter..."
                        className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3 px-4 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all"
                      />
                      <button
                        type="button"
                        onClick={handleAddSkill}
                        className="absolute right-2 top-2 bottom-2 bg-slate-200 hover:bg-[#D10043] hover:text-white text-slate-600 rounded-xl px-3 transition-colors flex items-center justify-center"
                      >
                        <Plus size={18} />
                      </button>
                    </div>

                    <div className="flex-1 bg-slate-50 border border-slate-100 rounded-2xl p-4 overflow-y-auto max-h-[160px]">
                      {formData.skills.length === 0 ? (
                        <p className="text-slate-400 text-sm font-medium text-center mt-4">No skills added yet.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {formData.skills.map((skill, index) => (
                            <span
                              key={index}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-sm font-bold shadow-sm group"
                            >
                              {skill}
                              <button
                                type="button"
                                onClick={() => handleRemoveSkill(skill)}
                                className="text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full p-0.5 transition-colors"
                              >
                                <X size={14} />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </section>
                </div>

                <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-6 border-t border-slate-200">
                  <button
                    type="button"
                    onClick={() => navigate(jobId ? `/candidate/upload-resume/${jobId}` : '/candidate/upload-resume')}
                    className="w-full sm:w-auto px-8 py-4 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 rounded-[20px] font-bold transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
                  >
                    <ArrowLeft size={18} />
                    <span>Back: Upload resume</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!formData.fullName.trim()) {
                        alert('Please enter your full name before continuing.');
                        return;
                      }
                      if (jobId) {
                        try {
                          const prev = JSON.parse(localStorage.getItem(`draft_application_${jobId}`) || '{}');
                          localStorage.setItem(`draft_application_${jobId}`, JSON.stringify({
                            ...prev,
                            step: 3,
                            detailsConfirmed: true,
                            formData,
                            savedAt: new Date().toISOString()
                          }));
                          localStorage.setItem('draft_application_step', '3');
                        } catch { }
                      }
                      setCurrentStep(3);
                      if (typeof window !== 'undefined') {
                        window.history.pushState(null, '', `?step=3`);
                        window.scrollTo({ top: 0, behavior: 'smooth' });
                      }
                    }}
                    className="w-full sm:w-auto px-10 py-4 bg-[#D10043] hover:bg-slate-900 text-white rounded-[20px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-[0.98] cursor-pointer"
                  >
                    <span>Next: Answer a few questions</span>
                    <ArrowRight size={20} />
                  </button>
                </div>
              </>
            )}

          </form>

          <ApplicationSuccessModal
            isOpen={showSuccessModal}
            onConfirm={handleFinalRedirect}
          />
        </main>
      </div>
    </div>
  );
};

interface InputFieldProps {
  icon: React.ReactNode;
  label: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder: string;
  type?: string;
}

const InputField: React.FC<InputFieldProps> = ({ icon, label, name, value, onChange, placeholder, type = "text" }) => (
  <div className="w-full">
    <label htmlFor={name} className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
      {label}
    </label>
    <div className="relative group">
      <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-[#D10043] transition-colors">
        {icon}
      </div>
      <input
        id={name}
        type={type}
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3 pl-12 pr-4 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all"
      />
    </div>
  </div>
);

export default CandidateProfileForm;
