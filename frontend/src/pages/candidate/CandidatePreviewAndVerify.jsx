import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  User, Mail, Phone, MapPin,
  Cpu, Briefcase, GraduationCap,
  CheckCircle, ArrowLeft, Edit3, Target
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ApplicationProgressBar from '../../components/common/ApplicationProgressBar';
import ApplicationSuccessModal from '../../components/modals/shared/ApplicationSuccessModal';
import { useSubmitApplicationMutation } from '../../redux/api/apiSlice';

const CandidatePreviewAndVerify = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { jobId } = useParams();

  const [submitApplication, { isLoading: isSubmitting }] = useSubmitApplicationMutation();
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  useEffect(() => {
    if (jobId) {
      localStorage.setItem('draft_application_step', '3');
      if (state?.job?.title) {
        localStorage.setItem('draft_application_job_title', state.job.title);
      }
      localStorage.setItem('draft_application_job_id', jobId);
    }
  }, [jobId, state]);

  const data = state?.extractedData;
  const matchData = state?.matchData;

  const extractedData = {
    personal: {
      name: data?.fullname || state?.personal?.name || "Candidate Name",
      email: data?.email || state?.personal?.email || "candidate@example.com",
      phone: data?.phone || state?.personal?.phone || "Not specified",
      location: data?.location || state?.personal?.location || "Not specified"
    },
    skills: data?.skills 
      ? (Array.isArray(data.skills) ? data.skills : data.skills.split(' | ').filter(Boolean)) 
      : (state?.skills || ["Process Optimization", "Team Leadership"]),
    experience: {
      title: data?.job_title || (data?.experience ? data.experience.split('|')[0]?.trim() : (state?.experience?.title || "Specialist")),
      company: state?.job?.title || state?.experience?.company || "Mariwasa Siam Ceramics",
      relevance: data?.years_experience ? `${data.years_experience}+ years of experience` : (state?.experience?.relevance || "Professional experience")
    },
    education: {
      degree: data?.highest_degree || data?.degree || state?.education?.degree || "Degree in Field",
      college: data?.education ? (data.education.split('|')[0]?.trim()) : (state?.education?.college || "Educational Institution")
    },
    resumeUrl: data?.file_url || data?.resumeUrl || state?.resumeUrl || null
  };

  const getMatchTier = (pct) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const handleBackToEdit = () => {
    navigate(jobId ? `/candidate/update-profile/${jobId}` : '/candidate/update-profile', {
      state: {
        ...extractedData,
        formData: state?.formData,
        fileName: state?.fileName,
        job: state?.job,
        matchData: state?.matchData,
        resumeUrl: extractedData.resumeUrl
      }
    });
  };

  const handleSubmitFinalApplication = async () => {
    if (!jobId || jobId === 'smart') {
      navigate('/candidate/smart-matches', {
        state: { matches: matchData, extractedData: data, fileName: state?.fileName }
      });
      return;
    }

    const payload = {
      job_id: jobId,
      candidate_name: extractedData.personal.name,
      candidate_email: extractedData.personal.email,
      phone: extractedData.personal.phone,
      location: extractedData.personal.location,
      job_title: extractedData.experience.title,
      company: extractedData.experience.company,
      relevance: extractedData.experience.relevance,
      degree: extractedData.education.degree,
      college: extractedData.education.college,
      skills: extractedData.skills,
      match_score: matchData?.match_percentage || state?.matchScore || 0,
      skills_score: matchData?.skills_score || 0,
      experience_score: matchData?.experience_score || 0,
      education_score: matchData?.education_score || 0,
      skills_reason: matchData?.skills_reason || "",
      experience_reason: matchData?.experience_reason || "",
      education_reason: matchData?.education_reason || "",
      matched_skills: matchData?.matched_skills || [],
      missing_skills: matchData?.missing_skills || [],
      relevant_experience: matchData?.relevant_experience || "",
      experience_gaps: matchData?.experience_gaps || "",
      required_degree: matchData?.required_degree || "",
      candidate_degree: matchData?.candidate_degree || "",
      recommendations: matchData?.recommendations || [],
      ai_summary: matchData?.ai_summary || "",
      strengths: matchData?.strengths || [],
      weaknesses: matchData?.weaknesses || [],
      ai_powered: Boolean(matchData?.ai_powered),
      profile_image_url: localStorage.getItem('profile_image_url'),
      resume_url: extractedData.resumeUrl,
    };

    try {
      await submitApplication(payload).unwrap();
      localStorage.removeItem('draft_application_job_title');
      localStorage.removeItem('draft_application_job_id');
      localStorage.removeItem('draft_application_step');
      setShowSuccessModal(true);
    } catch (err) {
      console.error("Failed to submit application:", err);
      alert("Failed to submit application. Please try again.");
    }
  };

  const handleFinalRedirect = () => {
    navigate('/candidate/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Verify Application | {state?.job?.title || 'Candidate Portal'}</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-7xl mx-auto px-6 py-12 flex-grow">
          {/* Reversal of action / Back to Edit */}
          <button
            onClick={handleBackToEdit}
            className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-4 font-semibold text-sm group"
          >
            <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
            Back to Edit Details
          </button>

          {jobId && <ApplicationProgressBar currentStep={3} />}

          <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
            <div>
              <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
                {jobId ? "Review Application" : "AI Profile Analysis"}
              </h1>
              <p className="text-slate-500 font-medium">
                {jobId 
                  ? `Verify your information before finalizing submission for ${state?.job?.title || 'this position'}.`
                  : "Verify the information our AI extracted from your resume before we find your matches."
                }
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                id="btn-edit-details"
                onClick={handleBackToEdit}
                className="flex items-center text-sm font-bold text-[#D60041] hover:underline bg-pink-50 px-4 py-2.5 rounded-xl transition-colors active:scale-95"
              >
                <Edit3 size={16} className="mr-2" /> Edit Details
              </button>
            </div>
          </div>

          <div className="space-y-6">

            {/* Match Analysis section */}
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
                    {getMatchTier(matchData.match_percentage)} ({matchData.match_percentage}%)
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

            {/* Personal Information */}
            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <User size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Personal Information</h2>
              </div>
              <div className="flex flex-col md:flex-row gap-8 items-start">
                <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                  <InfoItem icon={<User size={16} />} label="Full Name" value={extractedData.personal.name} />
                  <InfoItem icon={<Mail size={16} />} label="Email Address" value={extractedData.personal.email} />
                  <InfoItem icon={<Phone size={16} />} label="Phone" value={extractedData.personal.phone} />
                  <InfoItem icon={<MapPin size={16} />} label="Location" value={extractedData.personal.location} />
                </div>
              </div>

              <div className="mt-8 pt-8 border-t border-slate-50">
                <div className="flex items-center gap-3 mb-4 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Cpu size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">Skills</h2>
                </div>
                <div className="flex flex-wrap gap-2">
                  {extractedData.skills.map((skill, i) => (
                    <span key={i} className="px-4 py-2 bg-slate-50 text-slate-700 rounded-xl text-sm font-bold border border-slate-100 hover:border-slate-200 transition-colors cursor-default">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            </section>

            {/* Experience + Education */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
                <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Briefcase size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">Experience</h2>
                </div>
                <h4 className="font-black text-slate-900 mb-1">{extractedData.experience.title}</h4>
                <p className="text-sm font-bold text-slate-500 mb-4">{extractedData.experience.company}</p>
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                  <p className="text-sm text-slate-600 leading-relaxed font-medium">{extractedData.experience.relevance}</p>
                </div>
              </section>

              <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
                <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <GraduationCap size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">Education</h2>
                </div>
                <h4 className="font-black text-slate-900 mb-1">{extractedData.education.degree}</h4>
                <p className="text-sm font-bold text-slate-500 bg-slate-50 inline-block px-3 py-1.5 rounded-lg border border-slate-100 mt-2">{extractedData.education.college}</p>
              </section>
            </div>

            {/* Action Buttons: Reversal (Back to Edit) + Final Submission */}
            <div className="flex flex-col sm:flex-row gap-4 pt-6 border-t border-slate-200">
              <button
                type="button"
                onClick={handleBackToEdit}
                className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95 flex items-center justify-center gap-2"
              >
                <ArrowLeft size={18} />
                <span>Back to Edit Details</span>
              </button>
              {!jobId ? (
                <button
                  onClick={() => navigate('/candidate/smart-matches', { state: { matches: matchData, extractedData: data, fileName: state?.fileName } })}
                  className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95"
                >
                  <Target size={22} />
                  View Recommended Jobs
                </button>
              ) : (
                <button
                  type="button"
                  disabled={isSubmitting}
                  onClick={handleSubmitFinalApplication}
                  className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95 disabled:opacity-75 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <div className="flex items-center gap-2">
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Submitting Application...</span>
                    </div>
                  ) : (
                    <>
                      <CheckCircle size={22} />
                      <span>Confirm & Submit Final Application</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </div>

          <ApplicationSuccessModal 
            isOpen={showSuccessModal} 
            onConfirm={handleFinalRedirect} 
          />
        </main>
      </div>
    </div>
  );
};

const InfoItem = ({ icon, label, value }) => (
  <div className="flex items-start gap-3 bg-slate-50 p-4 rounded-2xl border border-transparent hover:border-slate-100 transition-colors">
    <div className="mt-0.5 text-slate-400 bg-white p-1.5 rounded-lg shadow-sm border border-slate-100">
      {icon}
    </div>
    <div>
      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider mb-0.5">{label}</p>
      <p className="font-bold text-slate-800">{value}</p>
    </div>
  </div>
);

export default CandidatePreviewAndVerify;
