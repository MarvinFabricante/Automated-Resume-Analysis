import React from 'react';
import { useNavigate, useParams, useLocation } from '@/utils/navigation';
import jobService from '../../../services/jobService';
import { Helmet } from 'react-helmet-async';
import {
  CheckCircle,
  Home,
  Search,
  BellRing
} from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import ApplicationProgressBar from '../../../components/common/ApplicationProgressBar';

interface StepItemProps {
  number: string;
  title: string;
  desc: string;
}

const StepItem: React.FC<StepItemProps> = ({ number, title, desc }) => (
  <div className="flex flex-col gap-3">
    <span className="text-3xl font-black text-rose-200">{number}</span>
    <div>
      <h3 className="font-bold text-slate-900 mb-1">{title}</h3>
      <p className="text-sm text-slate-500 font-medium leading-relaxed">{desc}</p>
    </div>
  </div>
);

const SubmissionSuccessPage: React.FC = () => {
  const navigate = useNavigate();
  const { state } = useLocation();
  const { jobId } = useParams<{ jobId: string }>();
  const [jobTitle, setJobTitle] = React.useState(state?.jobTitle || "Success");
  const [appId] = React.useState(() => Math.floor(Math.random() * 900000 + 100000));

  React.useEffect(() => {
    const fetchJobTitle = async () => {
      if (state?.jobTitle || !jobId) return;
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

      <main className="max-w-7xl mx-auto px-6 py-12 flex flex-col items-center">
        {/* Progress Bar (Step 4 completed) */}
        <div className="w-full max-w-4xl mb-4">
          <ApplicationProgressBar currentStep={4} />
        </div>
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

        <div className="w-full bg-white rounded-[40px] shadow-xl shadow-slate-200/50 border border-slate-100 overflow-hidden mb-8">
          <div className="p-8 md:p-10">
            <h2 className="text-sm font-black uppercase tracking-widest text-[#D60041] mb-6 flex items-center gap-2">
              <BellRing size={16} />
              What Happens Next?
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <StepItem
                number="01"
                title="Hiring Team Review"
                desc="Our recruitment team will review your resume and qualifications within 2-3 business days."
              />
              <StepItem
                number="02"
                title="Status Updates"
                desc="You can monitor your application's progress anytime from your tracking page."
              />
              <StepItem
                number="03"
                title="Interview Invitation"
                desc="If your qualifications match the position, a recruiter will reach out with interview details."
              />
            </div>

            {/* Feedback Report Status Section */}
            <div className="mt-8 pt-8 border-t border-slate-100 bg-slate-50/60 -mx-8 -mb-10 p-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="space-y-1">
                <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block">
                  Feedback & Match Report
                </span>
                <p className="text-sm font-black text-slate-800">
                  Report is being prepared by our hiring team
                </p>
                <p className="text-xs text-slate-500 font-medium leading-relaxed">
                  Your feedback report will appear on your tracking page once the initial evaluation is complete.
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/candidate/applicationtracking')}
                className="px-5 py-2.5 rounded-xl bg-slate-900 hover:bg-[#D60041] text-white text-xs font-bold uppercase tracking-wider transition-colors shrink-0 cursor-pointer"
              >
                Track Application
              </button>
            </div>
          </div>

          <div className="bg-slate-50 p-6 border-t border-slate-100 flex items-center justify-center gap-2 text-slate-400 font-bold text-xs mt-4">
            <p>Application Tracking ID: #ARA-88{appId}</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md">
          <button
            onClick={() => navigate('/candidate/applicationtracking')}
            className="flex-1 bg-[#D60041] hover:bg-slate-900 text-white py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all shadow-lg shadow-pink-100 active:scale-[0.98] text-sm cursor-pointer"
          >
            <Search size={18} />
            Track Status
          </button>
          <button
            onClick={() => navigate('/candidate/dashboard')}
            className="flex-1 bg-white border border-slate-200 hover:border-slate-300 text-slate-700 py-4 rounded-2xl font-bold flex items-center justify-center gap-2 transition-all shadow-xs active:scale-[0.98] text-sm cursor-pointer"
          >
            <Home size={18} />
            Go to Dashboard
          </button>
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default SubmissionSuccessPage;
