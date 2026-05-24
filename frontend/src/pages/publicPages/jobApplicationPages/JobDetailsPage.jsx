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
  Trophy
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

  useEffect(() => {
    const loadJobData = async () => {
      if (location.state?.job) {
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

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>{job ? `${job.title} | Careers` : 'Job Details'}</title>
      </Helmet>

      <Header />

      <main className="max-w-5xl mx-auto px-6 py-12">

        {isLoading ? (
          <div className="space-y-8 animate-pulse">
            <div className="h-40 bg-white rounded-[40px] border border-slate-100"></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="h-20 bg-white rounded-2xl"></div>
              <div className="h-20 bg-white rounded-2xl"></div>
              <div className="h-20 bg-white rounded-2xl"></div>
            </div>
            <div className="h-64 bg-white rounded-[40px]"></div>
          </div>
        ) : job ? (
          <div className="space-y-8">
            <div className="bg-white rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden relative">
              <div className="absolute top-0 right-0 w-64 h-64 bg-red-50 rounded-bl-[200px] -mr-20 -mt-20 opacity-50"></div>

              <div className="p-8 md:p-12 border-b border-slate-50 bg-gradient-to-b from-slate-50/50 to-transparent relative z-10">

                <div className="flex items-center gap-6 mb-6">
                  <div className="w-16 h-16 bg-[#D60041] rounded-2xl flex items-center justify-center text-white shadow-lg shadow-pink-100 shrink-0">
                    <Briefcase size={32} />
                  </div>
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-widest text-[#D60041]">Job Details</span>
                    <h1 className="text-3xl md:text-4xl font-black text-slate-900 tracking-tight leading-tight mt-1">
                      {job.title}
                    </h1>
                    <p className="text-sm text-slate-500 font-medium">{job.department} Department</p>
                  </div>
                </div>
                <p className="text-slate-500 leading-relaxed max-w-2xl">
                  Explore the full details of this position. If you're ready to take the next step in your career with Mariwasa, click the apply button below.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <DetailItem icon={MapPin} label="Location" value={job.location || 'Philippines'} />
              <DetailItem icon={Clock} label="Job Type" value={job.job_type || 'Full-time'} />
              <DetailItem icon={DollarSign} label="Salary Range" value={job.salary_range || 'Competitive'} />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="lg:col-span-2 space-y-8">
                <div className="bg-white p-8 md:p-12 rounded-[40px] border border-slate-100 shadow-sm">
                  <h3 className="flex items-center gap-3 text-lg font-black text-slate-900 mb-6">
                    <FileText size={22} className="text-[#D60041]" />
                    Position Overview
                  </h3>
                  <div className="prose prose-slate max-w-none">
                    <p className="text-slate-600 leading-relaxed whitespace-pre-line text-base">
                      {job.description || "We are looking for a talented individual to join our team. This role offers the opportunity to work on exciting projects in ceramic manufacturing."}
                    </p>
                  </div>

                  <div className="mt-12">
                    <h3 className="flex items-center gap-3 text-lg font-black text-slate-900 mb-6">
                      <ListChecks size={22} className="text-[#D60041]" />
                      Skills & Requirements
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
                {job.education_requirements && (
                  <div className="bg-white p-6 rounded-[24px] border border-slate-100 shadow-sm">
                    <div className="flex items-center gap-2.5 mb-2.5 text-blue-600">
                      <GraduationCap size={18} />
                      <span className="text-[10px] font-black uppercase tracking-widest">Education Needed</span>
                    </div>
                    <p className="text-sm text-slate-800 font-bold leading-normal">
                      {job.education_requirements}
                    </p>
                  </div>
                )}

                {job.experience_requirements && (
                  <div className="bg-white p-6 rounded-[24px] border border-slate-100 shadow-sm">
                    <div className="flex items-center gap-2.5 mb-2.5 text-orange-600">
                      <Trophy size={18} />
                      <span className="text-[10px] font-black uppercase tracking-widest">Experience Needed</span>
                    </div>
                    <p className="text-sm text-slate-800 font-bold leading-normal">
                      {job.experience_requirements}
                    </p>
                  </div>
                )}

                <div className="bg-slate-900 text-white p-8 rounded-[40px] shadow-xl overflow-hidden relative">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -mr-16 -mt-16"></div>
                  <h4 className="text-xl font-black mb-4 relative z-10">Join Mariwasa</h4>
                  <p className="text-slate-400 text-sm leading-relaxed mb-8 relative z-10">
                    Be part of the leading ceramic tiles manufacturer in the Philippines. We value innovation, quality, and our people.
                  </p>
                  <div className="space-y-4 relative z-10">
                    <div className="flex items-center gap-3 text-xs font-bold text-slate-300">
                      <CheckCircle2 size={16} className="text-[#D60041]" />
                      Competitive Benefits
                    </div>
                    <div className="flex items-center gap-3 text-xs font-bold text-slate-300">
                      <CheckCircle2 size={16} className="text-[#D60041]" />
                      Career Growth
                    </div>
                    <div className="flex items-center gap-3 text-xs font-bold text-slate-300">
                      <CheckCircle2 size={16} className="text-[#D60041]" />
                      Dynamic Culture
                    </div>
                  </div>

                  <button
                    onClick={() => navigate(`/apply/${job.job_id}`, { state: { job } })}
                    className="w-full mt-10 bg-[#D60041] text-white py-5 rounded-[24px] font-bold text-sm hover:bg-white hover:text-slate-900 transition-all shadow-xl flex items-center justify-center gap-3 active:scale-95 relative z-10"
                  >
                    Apply Now
                    <ArrowRight size={18} />
                  </button>
                </div>

                <div className="bg-white p-8 rounded-[40px] border border-slate-100 shadow-sm text-center">
                  <div className="w-12 h-12 bg-pink-50 text-[#D60041] rounded-full flex items-center justify-center mx-auto mb-4">
                    <Calendar size={24} />
                  </div>
                  <h5 className="font-bold text-slate-900 mb-1">Posted Recently</h5>
                  <p className="text-xs text-slate-400 font-medium uppercase tracking-widest">Ongoing Recruitment</p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-20 bg-white rounded-[40px] border border-dashed border-slate-200">
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
