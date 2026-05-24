import React from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import jobService from '../../../services/jobService';
import { Helmet } from 'react-helmet-async';
import {
  CheckCircle,
  ArrowRight,
  Home,
  Search,
  BellRing,
  ExternalLink
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';

const SubmissionSuccessPage = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const { jobId } = useParams();
  const [jobTitle, setJobTitle] = React.useState(state?.jobTitle || "Success");

  React.useEffect(() => {
    const fetchJobTitle = async () => {
      if (state?.jobTitle) return;
      try {
        const response = await jobService.getJobById(jobId);
        if (response.data?.job_title) {
          setJobTitle(response.data.job_title);
        }
      } catch (err) {
        console.error("Failed to fetch job title:", err);
      }
    };
    fetchJobTitle();
  }, [jobId, state]);

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 antialiased font-['Inter',_sans-serif]">
      <Helmet>
        <title>Applied: {jobTitle} | Success</title>
      </Helmet>

      <Header />

      <main className="max-w-7xl mx-auto px-6 py-20 flex flex-col items-center">
        <div className="relative mb-10">
          <div className="absolute inset-0 bg-[#D60041] opacity-20 blur-3xl rounded-full animate-pulse"></div>
          <div className="relative w-24 h-24 bg-white rounded-[32px] shadow-2xl shadow-pink-100 border border-slate-50 flex items-center justify-center text-[#D60041] animate-in zoom-in duration-700">
            <CheckCircle size={48} strokeWidth={2.5} />
          </div>
        </div>

        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-black text-slate-900 tracking-tight mb-4">
            Application Received!
          </h1>
          <p className="text-lg text-slate-500 font-medium max-w-lg mx-auto leading-relaxed">
            Your application has been successfully transmitted to our hiring team. We're excited to review your profile!
          </p>
        </div>

        <div className="w-full bg-white rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden mb-12">
          <div className="p-8 md:p-10">
            <h2 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-6 flex items-center gap-2">
              <BellRing size={16} />
              What's Next?
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <StepItem
                number="01"
                title="Review"
                desc="Our team will evaluate your skills and experience."
              />
              <StepItem
                number="02"
                title="Notification"
                desc="You'll receive an email update within 3-5 business days."
              />
              <StepItem
                number="03"
                title="Interview"
                desc="If it's a match, we'll schedule a virtual call."
              />
            </div>
          </div>

          <div className="bg-slate-50 p-6 border-t border-slate-100 flex items-center justify-center gap-2 text-slate-400 font-bold text-xs">
            <p>Application ID: #APP-{Math.floor(Math.random() * 900000 + 100000)}</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md">
          <button
            onClick={() => navigate('/careerspage')}
            className="flex-1 bg-slate-900 hover:bg-black text-white py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-xl active:scale-[0.98]"
          >
            <Search size={20} />
            Explore More Jobs
          </button>
          <button
            onClick={() => navigate('/')}
            className="flex-1 bg-white border border-slate-200 hover:border-[#D60041] hover:text-[#D60041] text-slate-700 py-5 rounded-[24px] font-bold flex items-center justify-center gap-3 transition-all shadow-sm active:scale-[0.98]"
          >
            <Home size={20} />
            Back to Home
          </button>
        </div>

        <a
          href="#"
          className="mt-12 text-slate-400 hover:text-[#D60041] text-sm font-bold flex items-center gap-2 transition-colors group"
        >
          Follow us on LinkedIn for updates
          <ExternalLink size={14} className="group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
        </a>
      </main>

      <Footer />
    </div>
  );
};

const StepItem = ({ number, title, desc }) => (
  <div className="flex flex-col gap-3">
    <span className="text-3xl font-black text-slate-100">{number}</span>
    <div>
      <h3 className="font-bold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 font-medium leading-relaxed">{desc}</p>
    </div>
  </div>
);

export default SubmissionSuccessPage;
