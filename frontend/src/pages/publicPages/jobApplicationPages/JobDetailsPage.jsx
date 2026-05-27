import React, { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import jobService from '../../../services/jobService';
import {
  ArrowLeft,
  X,
  Briefcase,
  MapPin,
  Clock,
  DollarSign,
  FileText,
  ListChecks,
  CheckCircle2,
  Calendar,
  Building2,
  ArrowRight,
  GraduationCap,
  Trophy,
  Target,
  Cpu,
  Zap,
  XCircle,
  Award,
  AlertCircle
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';

const STATIC_JOBS = [
  { id: 1, title: "Production Supervisor", department: "Manufacturing" },
  { id: 2, title: "Quality Control Analyst", department: "Quality Assurance" },
  { id: 3, title: "HR Generalist", department: "Human Resources" },
  { id: 4, title: "Maintenance Technician", department: "Engineering" }
];

const JobDetailsPage = () => {
  const { jobId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const matchData = location.state?.matchData;
  const extractedData = location.state?.extractedData;
  const fileName = location.state?.fileName;

  useEffect(() => {
    window.scrollTo(0, 0);
    const loadJobData = async () => {
      if (location.state?.job && !location.state?.job?.description) {
        // If we have partial job state but no description, we should fetch it.
        try {
          const response = await jobService.getJobById(jobId);
          if (response.data) {
            setJob(response.data);
            setIsLoading(false);
            return;
          }
        } catch(e) {}
      }

      if (location.state?.job?.description) {
        setJob(location.state.job);
        setIsLoading(false);
        return;
      }

      const staticJob = STATIC_JOBS.find(j => j.id === parseInt(jobId));
      if (staticJob) {
        setJob(staticJob);
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
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
        console.error("Error loading job details:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadJobData();
  }, [jobId, location.state]);

  const DetailItem = ({ icon: Icon, label, value }) => (
    <div className="flex items-center gap-4 p-4 bg-white rounded-2xl border border-slate-100 shadow-sm">
      <div className="w-10 h-10 bg-slate-50 rounded-xl flex items-center justify-center text-[#D60041]">
        <Icon size={20} />
      </div>
      <div>
        <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{label}</p>
        <p className="text-sm font-bold text-slate-900">{value || 'N/A'}</p>
      </div>
    </div>
  );

  const getMatchColor = (pct) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  const getExperienceLevel = (title, reqs) => {
    const t = (title + " " + reqs).toLowerCase();
    if (t.includes('senior') || t.includes('lead') || t.includes('manager')) return "Senior Level";
    if (t.includes('junior') || t.includes('entry') || t.includes('assistant')) return "Entry Level";
    return "Mid Level";
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>{job ? `${job.title || job.job_title} | Careers` : 'Job Details'}</title>
      </Helmet>

      <Header />

      <main className="max-w-6xl mx-auto px-6 py-12">

        {isLoading ? (
          <div className="space-y-8 animate-pulse">
            <div className="h-40 bg-white rounded-[40px] border border-slate-100"></div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="h-20 bg-white rounded-2xl"></div>
              <div className="h-20 bg-white rounded-2xl"></div>
              <div className="h-20 bg-white rounded-2xl"></div>
              <div className="h-20 bg-white rounded-2xl"></div>
            </div>
            <div className="h-64 bg-white rounded-[40px]"></div>
          </div>
        ) : job ? (
          <div className="space-y-8">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center text-slate-500 hover:text-[#D10043] transition-all mb-4 font-semibold text-sm group w-fit"
            >
              <ArrowLeft size={18} className="mr-2 group-hover:-translate-x-1 transition-transform" />
              Back
            </button>

            <div className="bg-white rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden relative">
              <div className="absolute top-0 right-0 w-64 h-64 bg-red-50 rounded-bl-[200px] -mr-20 -mt-20 opacity-50"></div>

              <div className="p-8 md:p-12 border-b border-slate-50 bg-gradient-to-b from-slate-50/50 to-transparent relative z-10">

                <div className="flex items-center gap-6 mb-6">
                  <div className="w-16 h-16 bg-[#D60041] rounded-2xl flex items-center justify-center text-white shadow-lg shadow-pink-100 shrink-0">
                    <Briefcase size={32} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-widest text-[#D60041]">Job Description Card</span>
                    <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-tight mt-1">
                      {job.title || job.job_title}
                    </h1>
                    <p className="text-sm text-slate-500 font-medium">{job.department} Department</p>
                  </div>
                </div>
                <p className="text-slate-500 leading-relaxed max-w-2xl font-medium">
                  Review the complete requirements and qualifications for this position.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <DetailItem icon={MapPin} label="Location" value={job.location || 'Philippines'} />
              <DetailItem icon={Clock} label="Employment Type" value={job.job_type || 'Full-time'} />
              <DetailItem icon={DollarSign} label="Salary Range" value={job.salary_range || 'Competitive'} />
              <DetailItem icon={Target} label="Experience Level" value={getExperienceLevel(job.title || job.job_title, job.experience_requirements)} />
            </div>

            {/* AI Resume Analysis Integration */}
            {matchData && (
              <div className="bg-white p-8 md:p-12 rounded-[40px] border-2 border-pink-100 shadow-2xl shadow-pink-100/50 relative overflow-hidden animate-in fade-in slide-in-from-bottom-6 duration-700">
                <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-pink-50 to-transparent rounded-bl-[200px] opacity-40"></div>
                
                <div className="flex flex-col md:flex-row gap-12 items-center relative z-10 mb-8 border-b border-slate-100 pb-8">
                  <div className="flex flex-col items-center shrink-0">
                    <div className="relative w-36 h-36">
                      <svg className="w-36 h-36 -rotate-90" viewBox="0 0 100 100">
                        <circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" strokeWidth="12" />
                        <circle
                          cx="50" cy="50" r="42" fill="none"
                          stroke={getMatchColor(matchData.match_percentage)}
                          strokeWidth="12"
                          strokeDasharray="264 264"
                          strokeDashoffset={264 - (264 * matchData.match_percentage) / 100}
                          strokeLinecap="round"
                          className="transition-all duration-1000 ease-out"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
                        <span className="text-3xl font-black text-slate-900 leading-none tracking-tight">
                          {Math.round(matchData.match_percentage)}%
                        </span>
                        <span className="text-[9px] font-black uppercase tracking-widest text-slate-400 mt-1">Overall Match</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex-1 w-full">
                    <h3 className="text-xl font-black text-slate-900 mb-2 flex items-center gap-3">
                      <Zap className="text-[#D60041]" size={24} />
                      Your Resume Analysis
                    </h3>
                    <p className="text-slate-600 font-medium leading-relaxed mb-6">
                      {matchData.ai_summary || "We analyzed your qualifications against this job description. Here is the detailed breakdown of your fit."}
                    </p>
                    
                    <div className="grid grid-cols-3 gap-4">
                      {[
                        { label: 'Skills Match', score: matchData.skills_score, icon: <Cpu size={16} />, color: 'text-blue-600', bg: 'bg-blue-50' },
                        { label: 'Experience Match', score: matchData.experience_score, icon: <Briefcase size={16} />, color: 'text-purple-600', bg: 'bg-purple-50' },
                        { label: 'Education Match', score: matchData.education_score, icon: <GraduationCap size={16} />, color: 'text-amber-600', bg: 'bg-amber-50' }
                      ].map((item, idx) => (
                        <div key={idx} className={`${item.bg} p-4 rounded-2xl flex flex-col text-center`}>
                          <div className={`mx-auto ${item.color} mb-2`}>{item.icon}</div>
                          <p className="text-lg font-black text-slate-900">{Math.round(item.score)}%</p>
                          <span className="text-[9px] font-black uppercase tracking-widest text-slate-500">{item.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
                  <div className="space-y-6">
                    <div>
                      <h4 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-3 flex items-center gap-2">
                        <CheckCircle2 size={16} /> Matching Skills
                      </h4>
                      {matchData.matched_skills?.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {matchData.matched_skills.map((s, i) => (
                            <span key={i} className="px-3 py-1.5 bg-green-50 text-green-700 border border-green-100 rounded-xl text-xs font-bold">{s}</span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500 font-medium">No direct skill matches found.</p>
                      )}
                    </div>

                    <div>
                      <h4 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-3 flex items-center gap-2">
                        <Briefcase size={16} /> Relevant Experience Found
                      </h4>
                      <p className="text-sm text-slate-700 font-medium leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100">
                        {matchData.experience_reason || "Experience level evaluated against job requirements."}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <div>
                      <h4 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-3 flex items-center gap-2">
                        <XCircle size={16} /> Missing Skills
                      </h4>
                      {matchData.missing_skills?.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                          {matchData.missing_skills.map((s, i) => (
                            <span key={i} className="px-3 py-1.5 bg-red-50 text-red-600 border border-red-100 rounded-xl text-xs font-bold">{s}</span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-slate-500 font-medium">You meet all the identified skill requirements!</p>
                      )}
                    </div>

                    <div>
                      <h4 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-3 flex items-center gap-2">
                        <GraduationCap size={16} /> Education Verification
                      </h4>
                      <p className="text-sm text-slate-700 font-medium leading-relaxed bg-slate-50 p-4 rounded-2xl border border-slate-100">
                        {matchData.education_reason || "Education level evaluated."}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-8">
                <div className="bg-white p-8 md:p-12 rounded-[40px] border border-slate-100 shadow-sm">
                  <h3 className="flex items-center gap-3 text-xl font-black text-slate-900 mb-6 pb-4 border-b border-slate-50">
                    <FileText size={24} className="text-[#D60041]" />
                    Job Description & Responsibilities
                  </h3>
                  <div className="prose prose-slate max-w-none">
                    <p className="text-slate-600 leading-relaxed whitespace-pre-line text-base">
                      {job.description || "We are looking for a talented individual to join our team. This role offers the opportunity to work on exciting projects in ceramic manufacturing."}
                    </p>
                  </div>

                  <div className="mt-12">
                    <h3 className="flex items-center gap-3 text-xl font-black text-slate-900 mb-6 pb-4 border-b border-slate-50">
                      <ListChecks size={24} className="text-[#D60041]" />
                      Required Skills
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {(typeof job.skills_requirements === 'string'
                        ? job.skills_requirements.split(',')
                        : (job.skills_requirements || ["General Proficiency", "Problem Solving", "Teamwork"])
                      ).map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-4 py-2 bg-slate-50 border border-slate-100 text-slate-700 text-sm font-semibold rounded-xl"
                        >
                          {skill.trim()}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-6">
                <div className="bg-white p-6 rounded-[24px] border border-slate-100 shadow-sm">
                  <div className="flex items-center gap-3 mb-4 text-blue-600">
                    <div className="p-2 bg-blue-50 rounded-lg"><GraduationCap size={20} /></div>
                    <span className="text-xs font-black uppercase tracking-widest">Required Education</span>
                  </div>
                  <p className="text-sm text-slate-700 font-bold leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
                    {job.education_requirements || "Bachelor's degree or equivalent experience"}
                  </p>
                </div>

                <div className="bg-white p-6 rounded-[24px] border border-slate-100 shadow-sm">
                  <div className="flex items-center gap-3 mb-4 text-orange-600">
                    <div className="p-2 bg-orange-50 rounded-lg"><Trophy size={20} /></div>
                    <span className="text-xs font-black uppercase tracking-widest">Required Experience</span>
                  </div>
                  <p className="text-sm text-slate-700 font-bold leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100">
                    {job.experience_requirements || "Relevant professional experience in a similar role."}
                  </p>
                </div>

                {(job.certifications_requirements || job.preferred_qualifications) && (
                  <div className="bg-white p-6 rounded-[24px] border border-slate-100 shadow-sm">
                    <div className="flex items-center gap-3 mb-4 text-purple-600">
                      <div className="p-2 bg-purple-50 rounded-lg"><Award size={20} /></div>
                      <span className="text-xs font-black uppercase tracking-widest">Certifications / Preferred</span>
                    </div>
                    <p className="text-sm text-slate-700 font-bold leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-100 whitespace-pre-line">
                      {job.certifications_requirements || "No specific certifications required."}
                    </p>
                  </div>
                )}

                <div className="bg-slate-900 text-white p-8 rounded-[40px] shadow-xl overflow-hidden relative mt-8">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-16 -mt-16"></div>
                  <h4 className="text-xl font-black mb-4 relative z-10">Ready to Join?</h4>
                  <p className="text-slate-400 text-sm leading-relaxed mb-8 relative z-10">
                    Take the next step in your career with Mariwasa. Apply now to this position.
                  </p>
                  
                  {matchData ? (
                    <button
                      onClick={() => navigate(`/candidate/preview-profile/${job.job_id || job.id}`, { state: { job, extractedData, matchData, fileName } })}
                      className="w-full bg-[#D60041] text-white py-5 rounded-[24px] font-bold text-sm hover:bg-white hover:text-slate-900 transition-all shadow-xl flex items-center justify-center gap-3 active:scale-95 relative z-10"
                    >
                      Start Application
                      <ArrowRight size={18} />
                    </button>
                  ) : (
                    <button
                      onClick={() => navigate(`/apply/${job.job_id || job.id}`, { state: { job } })}
                      className="w-full bg-[#D60041] text-white py-5 rounded-[24px] font-bold text-sm hover:bg-white hover:text-slate-900 transition-all shadow-xl flex items-center justify-center gap-3 active:scale-95 relative z-10"
                    >
                      Apply Now
                      <ArrowRight size={18} />
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-20 bg-white rounded-[40px] border border-dashed border-slate-200">
            <AlertCircle size={48} className="mx-auto text-slate-300 mb-4" />
            <h2 className="text-2xl font-bold text-slate-400">Position Not Found</h2>
            <p className="text-slate-500 mt-2">The job you are looking for might have been closed or removed.</p>
            <button
              onClick={() => navigate('/careerspage')}
              className="mt-8 px-8 py-3 bg-slate-900 text-white rounded-2xl font-bold text-sm"
            >
              Back to Careers
            </button>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
};

export default JobDetailsPage;
