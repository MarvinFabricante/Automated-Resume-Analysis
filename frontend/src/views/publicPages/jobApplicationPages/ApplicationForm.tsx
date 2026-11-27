import { collectClarificationResponses } from '../../../utils/clarificationQuestions';
import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, useParams } from '@/utils/navigation';
import { useSelector } from 'react-redux';
import { RootState } from '../../../redux/store';
import candidateService from '../../../services/candidateService';
import { Helmet } from 'react-helmet-async';
import {
  User, Mail, Phone, MapPin,
  Briefcase, GraduationCap, Building2,
  FileText, Code,
  ArrowLeft, ArrowRight, CheckCircle2
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import ApplicationProgressBar from '../../../components/common/ApplicationProgressBar';
import ClarificationQuestionsPanel, { ClarificationSubmitConfirmation } from '../../../components/common/ClarificationQuestionsPanel';
import ExperienceGapAlert from '../../../components/common/ExperienceGapAlert';
import MinimumRequirementBlocker, { isBelowAcceptedRequirements } from '../../../components/common/MinimumRequirementBlocker';
import { SelectWithOther, MultiSelectDropdownWithOther } from '../../../components/common/SelectWithOther';
import {
  PH_LOCATIONS,
  COMMON_JOB_TITLES,
  EXPERIENCE_LEVEL_OPTIONS,
  DEGREE_OPTIONS,
  PH_INSTITUTIONS,
  SKILL_OPTIONS,
} from '../../../data/formOptions';
import ResumeTipsPanel, {
  ResumeReadabilityBanner,
} from '../../../components/common/ResumeTipsPanel';
import { useJobClarifications } from '../../../hooks/useJobClarifications';
import {
  ClarificationQuestion,
  buildCandidateMatchPayload,
  finalizeFormWithClarifications,
  resolveClarifiedYears,
} from '../../../utils/clarificationQuestions';
import { isNoValueRequirement } from '../../../utils/criterionStatus';

interface InputFieldProps {
  icon: React.ReactNode;
  label: string;
  name: string;
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  placeholder?: string;
  type?: string;
  required?: boolean;
}

const InputField: React.FC<InputFieldProps> = ({ icon, label, name, value, onChange, placeholder, type = "text", required = false }) => (
  <div className="w-full">
    <label htmlFor={name} className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
      {label} {required && <span className="text-[#D10043] ml-1">*</span>}
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
        required={required}
        className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3 pl-12 pr-4 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all"
      />
    </div>
  </div>
);

const ApplicationForm: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId } = useParams<{ jobId: string }>();
  const loggedInUser = useSelector((state: RootState) => state.auth?.user);

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
      } catch {}
    }
    return 2;
  });

  useEffect(() => {
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
  const accountEmail =
    cleanField(typeof loggedInUser === 'string' ? loggedInUser : (loggedInUser as any)?.email) ||
    (typeof window !== 'undefined' && localStorage.getItem('token') ? cleanField(localStorage.getItem('saved_email')) : '') ||
    '';
  const resumeEmail = cleanField(location.state?.resumeEmail) || cleanField(ext?.email) || cleanField(savedDraft?.resumeEmail) || '';
  const hasEmailMismatch = Boolean(
    accountEmail &&
    resumeEmail &&
    accountEmail.toLowerCase() !== resumeEmail.toLowerCase()
  );
  const initialContactEmail =
    cleanField(location.state?.contactEmail) ||
    cleanField(savedDraft?.contactEmail) ||
    accountEmail ||
    cleanField(location.state?.personal?.email) ||
    resumeEmail ||
    cleanField(savedDraft?.formData?.email) ||
    '';

  const initialFormData = {
    fullName: cleanField(location.state?.personal?.name) || cleanField(ext?.fullname) || cleanField(savedDraft?.formData?.fullName),
    email: initialContactEmail,
    phone: cleanField(location.state?.personal?.phone) || cleanField(ext?.phone) || cleanField(savedDraft?.formData?.phone),
    location: cleanField(location.state?.personal?.location) || cleanField(ext?.location) || cleanField(savedDraft?.formData?.location),
    jobTitle: cleanField(location.state?.experience?.title) || cleanField(ext?.job_title) || cleanField(ext?.work_experiences?.[0]?.job_title) || cleanField(savedDraft?.formData?.jobTitle),
    company: cleanField(location.state?.experience?.company) || cleanField(ext?.company) || cleanField(ext?.work_experiences?.[0]?.company_name) || cleanField(savedDraft?.formData?.company),
    relevance: cleanField(location.state?.experience?.relevance) || cleanField(ext?.relevance) || cleanField(savedDraft?.formData?.relevance) || (ext?.years_experience ? `${ext.years_experience} years of experience` : ""),
    degree: cleanDegreeField(
      location.state?.education?.degree || ext?.degree,
      ext?.education_entries?.[0]?.degree_or_course || savedDraft?.formData?.degree,
      ext?.highest_degree
    ),
    college: cleanField(location.state?.education?.college) || cleanField(ext?.institution) || cleanField(ext?.college) || cleanField(ext?.education_entries?.[0]?.institution_name) || cleanField(savedDraft?.formData?.college),
    skills: Array.isArray(location.state?.skills) && location.state.skills.length > 0 && location.state.skills[0] !== "Extraction in progress"
      ? location.state.skills
      : Array.isArray(ext?.skills_list) && ext.skills_list.length > 0
      ? ext.skills_list
      : Array.isArray(savedDraft?.formData?.skills)
      ? savedDraft.formData.skills
      : [] as string[]
  };

  const displayFileName = location.state?.fileName || location.state?.extractedData?.filename || 'Uploaded_Resume.pdf';

  const [formData, setFormData] = useState(initialFormData);
  const [matchScore, setMatchScore] = useState(location.state?.matchData?.match_percentage || 0);
  const [matchData, setMatchData] = useState(location.state?.matchData || null);
  const [, setIsCalculating] = useState(false);
  const isBelowRequirements = Boolean(jobId && jobId !== 'smart' && isBelowAcceptedRequirements(matchData));

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

  useEffect(() => {
    const calculateMatchScore = async () => {
      if (!jobId || (!formData.skills.length && !formData.relevance && !formData.degree)) return;
      if (jobId === 'smart') return; // Do not calculate score for a specific job if it's a smart upload
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

  const handleBackToUpload = () => {
    if (currentStep === 3) {
      setCurrentStep(2);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    if (jobId && jobId !== 'smart') {
      navigate(`/apply/${jobId}`, {
        state: {
          job: location.state?.job,
          file: location.state?.file,
          fileName: location.state?.fileName,
          resumeUrl: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
          rawText: location.state?.rawText || location.state?.extractedData?.raw_text || null,
          extractedData: {
            ...location.state?.extractedData,
            fullname: formData.fullName,
            email: formData.email,
            phone: formData.phone,
            location: formData.location,
            job_title: formData.jobTitle,
            company: formData.company,
            relevance: formData.relevance,
            degree: formData.degree,
            college: formData.college,
            skills: formData.skills.join(' | '),
            skills_list: formData.skills,
            file_url: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
            raw_text: location.state?.rawText || location.state?.extractedData?.raw_text || null,
            profile_image_url: location.state?.profile_image_url || location.state?.extractedData?.profile_image_url
          },
          matchData
        }
      });

    } else {
      navigate('/smart-upload');
    }
  };

  const handleProceedToQuestions = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isBelowRequirements) {
      return;
    }
    if (!formData.fullName.trim() || !formData.email.trim()) {
      alert("Please provide at least your full name and email address.");
      return;
    }
    if (jobId && jobId !== 'smart') {
      try {
        localStorage.setItem(`draft_application_${jobId}`, JSON.stringify({
          jobId,
          step: 3,
          detailsConfirmed: true,
          formData,
          clarificationAnswers,
          resumeUrl: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
          fileName: location.state?.fileName || null,
          timestamp: Date.now()
        }));
      } catch {}
      setCurrentStep(3);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isBelowRequirements) {
      return;
    }
    
    if (currentStep === 2 && jobId !== 'smart') {
      handleProceedToQuestions(e);
      return;
    }

    if (!formData.fullName.trim() || !formData.email.trim()) {
      alert("Please provide at least your full name and email address.");
      return;
    }

    const finalForm = finalizeFormWithClarifications(clarificationQuestions, clarificationAnswers, formData);
    const clarifiedYears = resolveClarifiedYears(
      clarificationQuestions,
      clarificationAnswers,
      location.state?.extractedData?.years_experience,
      finalForm.relevance
    );

    if (jobId === 'smart') {
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
        highest_degree: finalForm.degree,
        degree: finalForm.degree,
        education: finalForm.college,
        college: finalForm.college,
        skills: finalForm.skills.join(' | '),
        skills_list: finalForm.skills,
        work_experiences: location.state?.extractedData?.work_experiences || [],
        education_entries: location.state?.extractedData?.education_entries || [],
        certifications: location.state?.extractedData?.certifications || [],
        clarification_questions: clarificationQuestions,
        clarification_answers: clarificationAnswers,
        clarification_responses: collectClarificationResponses(clarificationQuestions, clarificationAnswers),
        summary: location.state?.extractedData?.summary || "",
        file_url: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
        resume_url: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
        raw_text: location.state?.rawText || location.state?.extractedData?.raw_text || null,
        profile_image_url: location.state?.profile_image_url || null
      };

      const runSmartMatch = async () => {
        try {
          const payload = {
            clarification_responses: collectClarificationResponses(clarificationQuestions, clarificationAnswers),
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
          navigate(`/smart-matches`, {
            state: {
              matches,
              extractedData: updatedExtractedData,
              fileName: location.state?.fileName,
              file: location.state?.file,
              resumeUrl: location.state?.resumeUrl || updatedExtractedData.file_url,
              rawText: location.state?.rawText || updatedExtractedData.raw_text
            }
          });
        } catch (err) {
          console.error("Failed to fetch smart matches:", err);
          alert("Failed to fetch job matches. Please try again.");
        }
      };
      runSmartMatch();
      return;
    }

    // Step 2 Submission -> NEXT is Step 4 Review & Submit
    if (jobId && jobId !== 'smart') {
      try {
        localStorage.setItem(`draft_application_${jobId}`, JSON.stringify({
          jobId,
          step: 4,
          detailsConfirmed: true,
          questionsConfirmed: true,
          formData: finalForm,
          accountEmail,
          resumeEmail,
          contactEmail: finalForm.email || accountEmail,
          clarificationAnswers,
          resumeUrl: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
          fileName: location.state?.fileName || null,
          timestamp: Date.now()
        }));
      } catch {}
    }

    navigate(`/preview-and-verify/${jobId}`, {
      state: {
        job: activeJob || location.state?.job,
        jobTitle,
        file: location.state?.file,
        fileName: location.state?.fileName,
        resumeUrl: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
        rawText: location.state?.rawText || location.state?.extractedData?.raw_text || null,
        formData: finalForm,
        accountEmail,
        resumeEmail,
        contactEmail: finalForm.email || accountEmail,
        clarificationQuestions,
        clarificationAnswers,
        extractedData: {
          ...location.state?.extractedData,
          fullname: finalForm.fullName,
          email: finalForm.email,
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
        clarification_responses: collectClarificationResponses(clarificationQuestions, clarificationAnswers),
          file_url: location.state?.resumeUrl || location.state?.extractedData?.file_url || null,
          raw_text: location.state?.rawText || location.state?.extractedData?.raw_text || null,
          profile_image_url: location.state?.profile_image_url || location.state?.extractedData?.profile_image_url
        },
        matchData,
        matchScore
      }
    });

  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Application Details | {jobTitle}</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Reversal of action */}
        <button
          id="btn-back"
          type="button"
          onClick={handleBackToUpload}
          className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-6 font-semibold text-sm group"
        >
          <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
          <span>{currentStep === 3 ? 'Back to Review Details' : 'Back to Resume Upload'}</span>
        </button>

        {/* Multi-step Application Progress Bar */}
        <ApplicationProgressBar currentStep={currentStep} />

        {/* Shared ATS Resume Tips & Post-Upload Readability Check */}
        <div className="space-y-3 mb-6">
          {ext?.readability_check && (
            <ResumeReadabilityBanner readabilityCheck={ext.readability_check} />
          )}
          <ResumeTipsPanel />
        </div>

        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-10 gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 bg-[#D10043]/10 text-[#D10043] rounded-full text-[10px] font-black uppercase tracking-widest">
                Step {currentStep} of 4
              </span>
              <span className="text-xs font-bold text-slate-400">
                {currentStep === 2 ? 'Review your details' : 'Answer a few questions'}
              </span>
            </div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
              {currentStep === 2 ? 'Review Your Application Details' : 'A Few Follow-up Questions'}
            </h1>
            <p className="text-slate-500 font-medium">
              {currentStep === 2
                ? `Review the information below for ${jobTitle}. You can update any field before moving forward.`
                : `These short questions help the hiring team evaluate your experience for ${jobTitle}.`}
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">

          {/* STEP 3 CONTENT: FOLLOW-UP QUESTIONS ONLY */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <ExperienceGapAlert
                matchData={matchData}
                job={activeJob}
                yearsExperience={resolveClarifiedYears(
                  clarificationQuestions,
                  clarificationAnswers,
                  location.state?.extractedData?.years_experience,
                  formData.relevance
                )}
              />

              {clarificationQuestions && clarificationQuestions.length > 0 ? (
                <ClarificationQuestionsPanel
                  questions={clarificationQuestions}
                  answers={clarificationAnswers}
                  onAnswerChange={handleClarificationChange}
                  reasons={location.state?.extractedData?.clarification_reasons || location.state?.clarification_reasons}
                  jobTitle={jobTitle}
                />
              ) : (
                <div className="bg-white p-8 md:p-10 rounded-[32px] border border-slate-100 shadow-sm text-center">
                  <div className="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center text-emerald-600 mx-auto mb-4">
                    <CheckCircle2 size={32} />
                  </div>
                  <h3 className="text-xl font-bold text-slate-900 mb-2">No Additional Questions Required</h3>
                  <p className="text-slate-500 max-w-md mx-auto text-sm leading-relaxed">
                    Your background covers the key details for this role. You are ready to review and submit your application.
                  </p>
                </div>
              )}

              {clarificationQuestions && clarificationQuestions.length > 0 && (
                <ClarificationSubmitConfirmation />
              )}

              {isBelowRequirements && (
                <MinimumRequirementBlocker
                  matchData={matchData}
                  jobTitle={jobTitle}
                  onUploadDifferent={handleBackToUpload}
                  onBrowseJobs={() => navigate('/jobs')}
                />
              )}

              <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-6 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setCurrentStep(2);
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                  }}
                  className="w-full sm:w-auto px-8 py-4 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 rounded-[20px] font-bold transition-all flex items-center justify-center gap-2 active:scale-95"
                >
                  <ArrowLeft size={18} />
                  <span>Back: Review your details</span>
                </button>
                <button
                  id="btn-submit-to-review"
                  type="submit"
                  disabled={isBelowRequirements}
                  className={`w-full sm:w-auto px-10 py-4 rounded-[20px] font-bold flex items-center justify-center gap-3 transition-all ${
                    isBelowRequirements
                      ? 'bg-slate-200 text-slate-500 cursor-not-allowed shadow-none'
                      : 'bg-[#D10043] hover:bg-slate-900 text-white shadow-xl shadow-pink-100 active:scale-[0.98]'
                  }`}
                >
                  <span>{isBelowRequirements ? 'Below Accepted Requirements' : 'Next: Review & Submit'}</span>
                  {!isBelowRequirements && <ArrowRight size={20} />}
                </button>
              </div>
            </div>
          )}

          {/* STEP 2 CONTENT: DETAILS FORM */}
          {currentStep === 2 && (
            <div className="space-y-8">
              {/* STEP 1 DONE: RESUME UPLOADED BANNER */}
              <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-2xs">
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
                  onClick={handleBackToUpload}
                  className="px-3.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-2xs self-end sm:self-auto cursor-pointer"
                >
                  <FileText size={14} className="text-[#D10043]" />
                  <span>Change resume</span>
                </button>
              </div>

              {isBelowRequirements && (
                <MinimumRequirementBlocker
                  matchData={matchData}
                  jobTitle={jobTitle}
                  onUploadDifferent={handleBackToUpload}
                  onBrowseJobs={() => navigate('/jobs')}
                />
              )}

              <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100">
                <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <User size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-sm">Personal Information</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <InputField
                    icon={<User size={18} />}
                    label="Full Name"
                    name="fullName"
                    value={formData.fullName}
                    onChange={handleChange}
                    placeholder="e.g. John Doe"
                    required={true}
                  />
                  <div className="w-full space-y-2">
                    <InputField
                      icon={<Mail size={18} />}
                      label="Email Address"
                      name="email"
                      type="email"
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="john@example.com"
                      required={true}
                    />
                    {hasEmailMismatch && (
                      <div
                        data-testid="email-mismatch-note"
                        className="rounded-2xl border border-amber-200 bg-amber-50/80 p-3.5 text-xs text-amber-900 space-y-2.5"
                      >
                        <p className="font-semibold leading-relaxed">
                          The email on your resume is different from your account email. Notifications will be sent to your account email.
                        </p>
                        <div className="space-y-1.5">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-amber-800">
                            Which email should HR use for contact?
                          </p>
                          <div className="flex flex-col sm:flex-row gap-2">
                            <label className="flex items-center gap-2 px-3 py-2 rounded-xl border border-amber-200 bg-white cursor-pointer hover:border-[#D10043]/40 transition-colors">
                              <input
                                type="radio"
                                name="hrContactEmailChoice"
                                checked={formData.email.trim().toLowerCase() === accountEmail.trim().toLowerCase()}
                                onChange={() => setFormData((prev) => ({ ...prev, email: accountEmail }))}
                                className="accent-[#D10043]"
                              />
                              <span className="text-xs font-medium text-slate-800">
                                Account email (<span className="font-bold">{accountEmail}</span>)
                              </span>
                            </label>
                            <label className="flex items-center gap-2 px-3 py-2 rounded-xl border border-amber-200 bg-white cursor-pointer hover:border-[#D10043]/40 transition-colors">
                              <input
                                type="radio"
                                name="hrContactEmailChoice"
                                checked={formData.email.trim().toLowerCase() === resumeEmail.trim().toLowerCase()}
                                onChange={() => setFormData((prev) => ({ ...prev, email: resumeEmail }))}
                                className="accent-[#D10043]"
                              />
                              <span className="text-xs font-medium text-slate-800">
                                Resume email (<span className="font-bold">{resumeEmail}</span>)
                              </span>
                            </label>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  <InputField
                    icon={<Phone size={18} />}
                    label="Phone Number"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder="+1 (555) 000-0000"
                  />
                  <SelectWithOther
                    icon={<MapPin size={18} />}
                    label="Location"
                    name="location"
                    value={formData.location}
                    onChange={(val) => setFormData((prev) => ({ ...prev, location: val }))}
                    options={PH_LOCATIONS}
                    placeholder="Select city / province..."
                    otherPlaceholder="Enter city, province or country..."
                  />
                </div>
              </section>

              <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100">
                <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Briefcase size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-sm">Latest Experience</h2>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <SelectWithOther
                    icon={<Briefcase size={18} />}
                    label="Job Title"
                    name="jobTitle"
                    value={formData.jobTitle}
                    onChange={(val) => setFormData((prev) => ({ ...prev, jobTitle: val }))}
                    options={COMMON_JOB_TITLES}
                    placeholder="Select latest job title..."
                    otherPlaceholder="Enter your job title..."
                  />
                  <InputField
                    icon={<Building2 size={18} />}
                    label="Company"
                    name="company"
                    value={formData.company}
                    onChange={handleChange}
                    placeholder="e.g. Acme Corp"
                  />
                </div>

                <SelectWithOther
                  icon={<FileText size={18} />}
                  label="Experience Level / Summary"
                  name="relevance"
                  value={formData.relevance}
                  onChange={(val) => setFormData((prev) => ({ ...prev, relevance: val }))}
                  options={EXPERIENCE_LEVEL_OPTIONS}
                  placeholder="Select years of relevant experience..."
                  otherPlaceholder="Enter your experience level or brief summary..."
                />
              </section>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100">
                  <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                    <div className="p-2.5 bg-pink-50 rounded-xl">
                      <GraduationCap size={20} />
                    </div>
                    <h2 className="font-bold uppercase tracking-widest text-sm">Education</h2>
                  </div>

                  <div className="space-y-6">
                    <SelectWithOther
                      icon={<GraduationCap size={18} />}
                      label="Degree / Certification"
                      name="degree"
                      value={formData.degree}
                      onChange={(val) => setFormData((prev) => ({ ...prev, degree: val }))}
                      options={DEGREE_OPTIONS}
                      placeholder="Select degree or qualification..."
                      otherPlaceholder="Enter specific degree or qualification..."
                    />
                    <SelectWithOther
                      icon={<Building2 size={18} />}
                      label="Institution"
                      name="college"
                      value={formData.college}
                      onChange={(val) => setFormData((prev) => ({ ...prev, college: val }))}
                      options={PH_INSTITUTIONS}
                      placeholder="Select university or school..."
                      otherPlaceholder="Enter university or institution name..."
                    />
                  </div>
                </section>

                <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100 flex flex-col">
                  <div className="flex items-center gap-3 mb-8 text-[#D10043]">
                    <div className="p-2.5 bg-pink-50 rounded-xl">
                      <Code size={20} />
                    </div>
                    <h2 className="font-bold uppercase tracking-widest text-sm">Core Skills</h2>
                  </div>

                  <MultiSelectDropdownWithOther
                    id="input-skill"
                    selectedItems={formData.skills}
                    onChange={(items) =>
                      setFormData((prev) => ({
                        ...prev,
                        skills: items.filter((s) => !isNoValueRequirement(s)),
                      }))
                    }
                    options={SKILL_OPTIONS}
                    placeholder="Select skills from dropdown..."
                    otherPlaceholder="Enter a custom skill and click Add..."
                    emptyStateText="No skills selected yet. Choose from the dropdown above."
                  />
                </section>
              </div>

              <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pt-6 border-t border-slate-200">
                <button
                  id="btn-back-bottom"
                  type="button"
                  onClick={handleBackToUpload}
                  className="w-full sm:w-auto px-8 py-4 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 rounded-[20px] font-bold transition-all flex items-center justify-center gap-2 active:scale-95"
                >
                  <ArrowLeft size={18} />
                  <span>Back to Resume Upload</span>
                </button>
                {jobId === 'smart' ? (
                  <button
                    id="btn-submit-to-review"
                    type="submit"
                    className="w-full sm:w-auto px-10 py-4 bg-[#D10043] hover:bg-slate-900 text-white rounded-[20px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-[0.98]"
                  >
                    <span>Find Job Matches</span>
                    <ArrowRight size={20} />
                  </button>
                ) : (
                  <button
                    id="btn-proceed-to-questions"
                    type="button"
                    onClick={handleProceedToQuestions}
                    disabled={isBelowRequirements}
                    className={`w-full sm:w-auto px-10 py-4 rounded-[20px] font-bold flex items-center justify-center gap-3 transition-all ${
                      isBelowRequirements
                        ? 'bg-slate-200 text-slate-500 cursor-not-allowed shadow-none'
                        : 'bg-[#D10043] hover:bg-slate-900 text-white shadow-xl shadow-pink-100 active:scale-[0.98]'
                    }`}
                  >
                    <span>{isBelowRequirements ? 'Below Accepted Requirements' : 'Next: Answer a few questions'}</span>
                    {!isBelowRequirements && <ArrowRight size={20} />}
                  </button>
                )}
              </div>
            </div>
          )}

        </form>
      </main>

      <Footer />
    </div>
  );
};

export default ApplicationForm;
