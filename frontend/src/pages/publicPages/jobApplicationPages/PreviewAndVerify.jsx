import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import candidateService from '../../../services/candidateService';
import {
  User, Mail, Phone, MapPin,
  Cpu, Briefcase, GraduationCap,
  CheckCircle, ArrowLeft, Edit3, Target,
  FileText
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import ApplicationProgressBar from '../../../components/common/ApplicationProgressBar';
import ApplicationSuccessModal from '../../../components/modals/shared/ApplicationSuccessModal';

const PreviewAndVerifyPage = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { jobId } = useParams();

  const data = state?.extractedData;
  const matchData = state?.matchData;
  const [smartMatches, setSmartMatches] = useState(state?.matches || null);
  const [isLoadingSmartMatches, setIsLoadingSmartMatches] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  useEffect(() => {
    if (jobId !== 'smart' || !data || smartMatches) return;

    let cancelled = false;
    const runPostParseAnalysis = async () => {
      setIsLoadingSmartMatches(true);
      try {
        const matchRes = await candidateService.matchData(null, data);
        if (!cancelled) {
          setSmartMatches(matchRes.data.results || []);
        }
      } catch (error) {
        console.error("Post-parse match analysis failed:", error);
        if (!cancelled) {
          setSmartMatches([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingSmartMatches(false);
        }
      }
    };

    runPostParseAnalysis();
    return () => {
      cancelled = true;
    };
  }, [jobId, data, smartMatches]);

  const extractedData = {
    personal: {
      name: data?.fullname || state?.formData?.fullName || "",
      email: data?.email || state?.formData?.email || "",
      phone: data?.phone || state?.formData?.phone || "",
      location: data?.location || state?.formData?.location || ""
    },
    skills: (Array.isArray(data?.skills_list) && data.skills_list.length > 0)
      ? data.skills_list
      : (data?.skills ? data.skills.split(' | ').filter(Boolean) : (state?.formData?.skills || ["Skills in review"])),
    experience: {
      title: data?.job_title || state?.formData?.jobTitle || (data?.experience ? data.experience.split('|')[0]?.trim() : ""),
      company: data?.company || state?.formData?.company || state?.job?.department || "Mariwasa Siam Ceramics",
      relevance: data?.relevance || state?.formData?.relevance || (data?.years_experience ? `${data.years_experience}+ years of experience` : "Experience provided")
    },
    education: {
      degree: data?.degree || data?.highest_degree || state?.formData?.degree || "",
      college: data?.institution || data?.college || state?.formData?.college || (data?.education ? data.education.split('|')[0]?.trim() : "")
    },
    profile_image_url: data?.profile_image_url || state?.profile_image_url || null
  };

  const getMatchTier = (pct) => {
    if (pct >= 70) return 'Strong Match';
    if (pct >= 40) return 'Good Match';
    return 'Potential Match';
  };

  const handleBackToEdit = () => {
    navigate(`/applicationform/${jobId}`, {
      state: {
        ...extractedData,
        formData: state?.formData,
        personal: {
          name: extractedData.personal.name,
          email: extractedData.personal.email,
          phone: extractedData.personal.phone,
          location: extractedData.personal.location
        },
        experience: extractedData.experience,
        education: extractedData.education,
        skills: extractedData.skills,
        job: state?.job,
        fileName: state?.fileName,
        matchData: state?.matchData,
        matchScore: state?.matchScore,
        profile_image_url: extractedData.profile_image_url
      }
    });
  };

  const handleFinalSubmit = async () => {
    if (jobId === 'smart') {
      navigate('/smart-matches', {
        state: {
          matches: smartMatches,
          extractedData: data,
          fileName: state?.fileName
        }
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        job_id: jobId,
        candidate_name: extractedData.personal.name,
        candidate_email: extractedData.personal.email,
        phone: extractedData.personal.phone,
        location: extractedData.personal.location,
        job_title: extractedData.experience.title || "Applicant",
        company: extractedData.experience.company || "General",
        relevance: extractedData.experience.relevance || "",
        degree: extractedData.education.degree || "",
        college: extractedData.education.college || "",
        skills: extractedData.skills,
        match_score: state?.matchScore || matchData?.match_percentage || 0,
        skills_score: matchData?.skills_score || 0,
        experience_score: matchData?.experience_score || 0,
        education_score: matchData?.education_score || 0,
        profile_image_url: extractedData.profile_image_url || null,
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
        ai_powered: Boolean(matchData?.ai_powered)
      };

      await candidateService.submitApplication(payload);
      setShowSuccessModal(true);
    } catch (error) {
      console.error("Failed to submit application:", error);
      const detail = error.response?.data?.detail || "Failed to submit application. Please check your network and try again.";
      alert(detail);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFinalRedirect = () => {
    navigate(`/submissionsuccess/${jobId}`, {
      state: {
        jobTitle: state?.job?.title || state?.jobTitle || "Position",
        fileName: state?.fileName,
        updatedData: extractedData
      }
    });
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Review & Verify Application | {state?.job?.title || 'Careers'}</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Reversal of action: Back to Application Details */}
        <button
          id="btn-back-to-edit"
          type="button"
          onClick={handleBackToEdit}
          className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-6 font-semibold text-sm group"
        >
          <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
          Back to Application Details
        </button>

        {/* Multi-step Application Progress Bar */}
        <ApplicationProgressBar currentStep={3} />

        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">Review Application</h1>
            <p className="text-slate-500 font-medium">
              Verify your information before finalizing submission for <span className="text-slate-900 font-bold">{state?.job?.title || "this position"}</span>.
            </p>
          </div>
          <button
            id="btn-edit-details"
            onClick={handleBackToEdit}
            className="flex items-center text-sm font-bold text-[#D60041] hover:underline bg-pink-50 px-5 py-2.5 rounded-xl transition-colors active:scale-95"
          >
            <Edit3 size={16} className="mr-2" /> Edit Details
          </button>
        </div>

        <div className="space-y-6">

          {/* AI Match Analysis Card if matchData available */}
          {matchData && (
            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3 text-[#D60041]">
                  <div className="p-2.5 bg-pink-50 rounded-xl">
                    <Target size={20} />
                  </div>
                  <h2 className="font-bold uppercase tracking-widest text-xs">AI Match Analysis</h2>
                </div>
                <div className="bg-[#D60041] text-white px-4 py-1.5 rounded-xl text-xs font-black shadow-sm">
                  {getMatchTier(matchData.match_percentage)} ({matchData.match_percentage}%)
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {[
                  { label: 'Skills Alignment', score: matchData.skills_score, icon: <Cpu size={16} /> },
                  { label: 'Experience Level', score: matchData.experience_score, icon: <Briefcase size={16} /> },
                  { label: 'Education Match', score: matchData.education_score, icon: <GraduationCap size={16} /> }
                ].map((item, idx) => (
                  <div key={idx} className="bg-slate-50/70 p-4 rounded-2xl border border-slate-100/70 flex flex-col items-center text-center">
                    <div className="text-[#D60041] mb-1.5">{item.icon}</div>
                    <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 mb-0.5">{item.label}</span>
                    <p className="text-base font-black uppercase text-slate-900">
                      {item.score >= 70 ? 'High Match' : item.score >= 40 ? 'Moderate' : 'Basic Match'}
                    </p>
                  </div>
                ))}
              </div>
            </section>
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
              {extractedData.profile_image_url && (
                <div className="shrink-0">
                  <img 
                    src={extractedData.profile_image_url} 
                    alt="Profile" 
                    className="w-32 h-32 rounded-2xl object-cover border-4 border-white shadow-lg"
                  />
                </div>
              )}
              <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-6 w-full">
                <InfoItem icon={<User size={16} />} label="Full Name" value={extractedData.personal.name} />
                <InfoItem icon={<Mail size={16} />} label="Email Address" value={extractedData.personal.email} />
                <InfoItem icon={<Phone size={16} />} label="Phone" value={extractedData.personal.phone || "Not specified"} />
                <InfoItem icon={<MapPin size={16} />} label="Location" value={extractedData.personal.location || "Not specified"} />
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
              <h4 className="font-black text-slate-900 mb-1">{extractedData.experience.title || "No Title Specified"}</h4>
              <p className="text-sm font-bold text-slate-500 mb-4">{extractedData.experience.company}</p>
              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100">
                <p className="text-sm text-slate-600 leading-relaxed font-medium">{extractedData.experience.relevance || "No additional description provided."}</p>
              </div>
            </section>

            <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-3 mb-6 text-[#D60041]">
                <div className="p-2.5 bg-pink-50 rounded-xl">
                  <GraduationCap size={20} />
                </div>
                <h2 className="font-bold uppercase tracking-widest text-xs">Education</h2>
              </div>
              <h4 className="font-black text-slate-900 mb-1">{extractedData.education.degree || "Degree Not Specified"}</h4>
              <p className="text-sm font-bold text-slate-500 bg-slate-50 inline-block px-3 py-1.5 rounded-lg border border-slate-100 mt-2">
                {extractedData.education.college || "Institution Not Specified"}
              </p>
            </section>
          </div>

          {/* Action Buttons: Reversal of Action (Back) + Final Submission */}
          <div className="flex flex-col sm:flex-row gap-4 pt-6 border-t border-slate-200">
            <button
              id="btn-back-edit"
              type="button"
              onClick={handleBackToEdit}
              className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95 flex items-center justify-center gap-2"
            >
              <ArrowLeft size={18} />
              <span>Back to Edit Details</span>
            </button>
            {jobId === 'smart' ? (
              <button
                disabled={isLoadingSmartMatches || !smartMatches}
                onClick={() => navigate(`/smart-matches`, { state: { matches: smartMatches, extractedData: data, fileName: state?.fileName } })}
                className={`flex-[2] py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl active:scale-95 ${
                  isLoadingSmartMatches || !smartMatches
                    ? "bg-slate-200 text-slate-400 cursor-not-allowed shadow-none"
                    : "bg-[#D60041] hover:bg-slate-900 text-white shadow-pink-100"
                }`}
              >
                <Target size={22} />
                {isLoadingSmartMatches ? "Analyzing Matches..." : "View Recommended Jobs"}
              </button>
            ) : (
              <button
                id="btn-confirm-submit"
                type="button"
                disabled={isSubmitting}
                onClick={handleFinalSubmit}
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

      <Footer />
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
      <p className="font-bold text-slate-800">{value || "Not specified"}</p>
    </div>
  </div>
);

export default PreviewAndVerifyPage;
