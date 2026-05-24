import React, { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import jobService from '../../services/jobService';
import candidateService from '../../services/candidateService';
import { useSelector } from 'react-redux';
import { Helmet } from 'react-helmet-async';
import {
  User, Mail, Phone, MapPin,
  Briefcase, GraduationCap, Building2,
  FileText, Code, X, Plus,
  ArrowLeft, Save
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ApplicationSuccessModal from '../../components/modals/shared/ApplicationSuccessModal';
import { useSubmitApplicationMutation } from '../../redux/api/apiSlice';

const CandidateProfileForm = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { jobId } = useParams();
  const loggedInEmail = useSelector((state) => state.auth.user);
  const [jobTitle, setJobTitle] = React.useState(location.state?.job?.title || 'Position');

  React.useEffect(() => {
    const fetchJobTitle = async () => {
      if (location.state?.job?.title) return;
      try {
        const response = await jobService.getJobById(jobId);
        if (response.data?.job_title) {
          setJobTitle(response.data.job_title);
        }
      } catch (err) {
        console.error("Failed to fetch job title:", err);
      }
    };
    if (jobId) {
      fetchJobTitle();
      localStorage.setItem('draft_application_step', '3');
      localStorage.setItem('draft_application_job_id', jobId);
    }
  }, [jobId, location.state]);

  const [formData, setFormData] = useState({
    fullName: location.state?.personal?.name || "Alex Thompson",
    email: loggedInEmail || location.state?.personal?.email || "alex.t@example.com",
    phone: location.state?.personal?.phone || "+1 (555) 000-1234",
    location: location.state?.personal?.location || "Chicago, IL",
    jobTitle: location.state?.experience?.title || "Senior Operations Lead",
    company: location.state?.experience?.company || "Global Tech Manufacturing",
    relevance: location.state?.experience?.relevance || "7+ years in high-volume production environments",
    degree: location.state?.education?.degree || "B.S. in Industrial Engineering",
    college: location.state?.education?.college || "University of Illinois",
    skills: location.state?.skills || ["Process Optimization", "Team Leadership", "Lean Manufacturing", "Safety Compliance", "ERP Systems"]
  });

  const [currentSkill, setCurrentSkill] = useState("");
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [matchScore, setMatchScore] = useState(location.state?.matchData?.match_percentage || 0);
  const [skillsScore, setSkillsScore] = useState(location.state?.matchData?.skills_score || 0);
  const [experienceScore, setExperienceScore] = useState(location.state?.matchData?.experience_score || 0);
  const [educationScore, setEducationScore] = useState(location.state?.matchData?.education_score || 0);
  const [skillsReason, setSkillsReason] = useState(location.state?.matchData?.skills_reason || "");
  const [experienceReason, setExperienceReason] = useState(location.state?.matchData?.experience_reason || "");
  const [educationReason, setEducationReason] = useState(location.state?.matchData?.education_reason || "");
  const [matchData, setMatchData] = useState(location.state?.matchData || null);
  const [isCalculating, setIsCalculating] = useState(false);

  React.useEffect(() => {
    const calculateMatchScore = async () => {
      if (!jobId || (!formData.skills.length && !formData.relevance && !formData.degree)) return;
      setIsCalculating(true);
      try {
        const payload = {
          skills: formData.skills.join(', '),
          experience: formData.relevance,
          education: formData.degree,
          highest_degree: formData.degree,
          fullname: formData.fullName,
          location: formData.location
        };
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
  }, [formData.skills, formData.relevance, formData.degree, formData.fullName, formData.location, jobId]);

  const getMatchColor = (pct) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleAddSkill = (e) => {
    e.preventDefault();
    if (currentSkill.trim() && !formData.skills.includes(currentSkill.trim())) {
      setFormData(prev => ({
        ...prev,
        skills: [...prev.skills, currentSkill.trim()]
      }));
      setCurrentSkill("");
    }
  };

  const handleRemoveSkill = (skillToRemove) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(skill => skill !== skillToRemove)
    }));
  };

  const [submitApplication, { isLoading: isSubmitting }] = useSubmitApplicationMutation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const payload = {
      job_id: jobId,
      candidate_name: formData.fullName,
      candidate_email: loggedInEmail || formData.email,
      phone: formData.phone,
      location: formData.location,
      job_title: jobTitle,
      company: formData.company,
      relevance: formData.relevance,
      degree: formData.degree,
      college: formData.college,
      skills: formData.skills,
      match_score: matchScore,
      skills_score: skillsScore,
      experience_score: experienceScore,
      education_score: educationScore,
      skills_reason: skillsReason,
      experience_reason: experienceReason,
      education_reason: educationReason,
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
      resume_url: location.state?.resumeUrl || null,
    };

    try {
      await submitApplication(payload).unwrap();
      // Clear draft as it's now submitted
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
        <title>Edit Application | {jobTitle}</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-7xl mx-auto px-6 py-12 flex-grow">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-8 font-semibold text-sm group"
        >
          <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
          Back to Review
        </button>

        <div className="mb-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">Application Details</h1>
            <p className="text-slate-500 font-medium">
              Review and update your professional details for the <span className="font-bold text-slate-900">{jobTitle}</span> position.
            </p>
          </div>
          
          <div className="flex items-center gap-4 bg-white p-3 pr-6 rounded-2xl border border-slate-100 shadow-sm">
            <div className="w-16 h-16 rounded-xl bg-slate-50 border border-slate-100 overflow-hidden flex items-center justify-center text-slate-300">
              {localStorage.getItem('profile_image_url') ? (
                <img src={localStorage.getItem('profile_image_url')} alt="Profile" className="w-full h-full object-cover" />
              ) : (
                <User size={32} />
              )}
            </div>
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Application Identity</p>
              <p className="text-sm font-black text-slate-900">{formData.fullName}</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">

          <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100">
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

          <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100">
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
                  rows="3"
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-3 pl-12 pr-4 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all resize-none"
                  placeholder="Summarize your professional background..."
                ></textarea>
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100">
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

            <section className="bg-white p-8 md:p-10 rounded-[32px] shadow-sm border border-slate-100 flex flex-col">
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

          <div className="flex flex-col sm:flex-row justify-end gap-4 pt-6 border-t border-slate-200">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-8 py-4 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 rounded-[20px] font-bold transition-all"
            >
              Discard Changes
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-10 py-4 bg-[#D10043] hover:bg-slate-900 text-white rounded-[20px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <Save size={20} />
              )}
              {isSubmitting ? 'Submitting...' : 'Submit Final Application'}
            </button>
          </div>

        </form>

        <ApplicationSuccessModal 
          isOpen={showSuccessModal} 
          onConfirm={handleFinalRedirect}
          // We can pass different props here if we want to customize the modal text
        />
        </main>
      </div>
    </div>
  );
};

const InputField = ({ icon, label, name, value, onChange, placeholder, type = "text" }) => (
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
