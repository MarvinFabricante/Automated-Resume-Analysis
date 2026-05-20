import React from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import axios from 'axios';
import {
  User, Mail, Phone, MapPin,
  Cpu, Briefcase, GraduationCap,
  CheckCircle, ArrowLeft, Edit3, Target
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';

const PreviewAndVerifyPage = () => {
  const { state } = useLocation();
  const navigate = useNavigate();
  const { jobId } = useParams();

  const data = state?.extractedData;
  const matchData = state?.matchData;
  const [smartMatches, setSmartMatches] = React.useState(state?.matches || null);
  const [isLoadingSmartMatches, setIsLoadingSmartMatches] = React.useState(false);

  React.useEffect(() => {
    if (jobId !== 'smart' || !data || smartMatches) return;

    let cancelled = false;
    const runPostParseAnalysis = async () => {
      setIsLoadingSmartMatches(true);
      try {
        const matchRes = await axios.post('http://localhost:8000/matching/match-data', data);
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
      name: data?.fullname || "",
      email: data?.email || "",
      phone: data?.phone || "",
      location: data?.location || ""
    },
    skills: data?.skills ? data.skills.split(' | ').filter(Boolean) : ["Extraction in progress"],
    experience: {
      title: data?.experience ? data.experience.split('|')[0] : "",
      company: state?.job?.department || "Department Not Specified",
      relevance: data?.years_experience ? `${data.years_experience}+ years of experience` : "Experience not extracted"
    },
    education: {
      degree: data?.highest_degree || "",
      college: data?.education ? data.education.split('|')[0] : ""
    },
    profile_image_url: data?.profile_image_url || null
  };

  const getMatchColor = (pct) => {
    if (pct >= 70) return '#22c55e';
    if (pct >= 40) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Verify Information | {state?.job?.title || 'Careers'}</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-12">

        <div className="flex justify-between items-end mb-8">
          <div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">Review Application</h1>
            <p className="text-slate-500 font-medium">
              Verify the information extracted from <span className="text-slate-900 font-bold">{state?.fileName || "your resume"}</span>.
            </p>
          </div>
          {jobId !== 'smart' && (
            <button
              id="btn-edit-details"
              onClick={() => navigate(`/applicationform/${jobId}`, { state: { ...extractedData, fileName: state?.fileName } })}
              className="flex items-center text-sm font-bold text-[#D60041] hover:underline bg-pink-50 px-4 py-2 rounded-xl transition-colors"
            >
              <Edit3 size={16} className="mr-2" /> Edit Details
            </button>
          )}
        </div>

        <div className="space-y-6">


          <section className="bg-white p-8 rounded-[32px] shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <div className="flex items-center gap-3 mb-6 text-[#D60041]">
              <div className="p-2.5 bg-pink-50 rounded-xl">
                <User size={20} />
              </div>
              <h2 className="font-bold uppercase tracking-widest text-xs">Personal Information</h2>
            </div>
            <div className="flex flex-col md:flex-row gap-8 items-start">
              {data?.profile_image_url && (
                <div className="shrink-0">
                  <img 
                    src={data.profile_image_url} 
                    alt="Profile" 
                    className="w-32 h-32 rounded-2xl object-cover border-4 border-white shadow-lg"
                  />
                </div>
              )}
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

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 pt-6">
            <button
              id="btn-cancel"
              onClick={() => navigate(-1)}
              className="flex-1 bg-white border border-slate-200 hover:border-slate-300 hover:bg-slate-50 text-slate-700 py-5 rounded-[24px] font-bold transition-all active:scale-95"
            >
              Cancel
            </button>
            {jobId === 'smart' ? (
              <button
                disabled={isLoadingSmartMatches || !smartMatches}
                onClick={() => navigate(`/smart-matches`, { state: { matches: smartMatches, extractedData, fileName: state?.fileName } })}
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
                onClick={() => navigate(`/applicationform/${jobId}`, { state: { ...extractedData, fileName: state?.fileName, matchData } })}
                className="flex-[2] bg-[#D60041] hover:bg-slate-900 text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl shadow-pink-100 active:scale-95"
              >
                <CheckCircle size={22} />
                Confirm & Submit Final Application
              </button>
            )}
          </div>
        </div>
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
      <p className="font-bold text-slate-800">{value}</p>
    </div>
  </div>
);

export default PreviewAndVerifyPage;
