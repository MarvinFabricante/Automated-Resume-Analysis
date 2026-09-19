import React from 'react';
import { Helmet } from 'react-helmet-async';
import { ChevronDown, LogIn, UserPlus, Briefcase, Info, FileUp, CheckCircle, ShieldCheck, ArrowRight } from 'lucide-react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import logo from '../../../assets/logo.png';

const LandingPage = () => {
  return (
    <div className="bg-[transparent] text-gray-800 antialiased font-sans min-h-screen flex flex-col">
      <Helmet>
        <title>Mariwasa - Careers Portal</title>
      </Helmet>

      <Header />

      <main className="flex-grow pt-16">

        <section className="text-center px-6 max-w-7xl mx-auto mb-20 mt-10">
          <div className="inline-block p-1.5 rounded-full bg-white shadow-sm border border-gray-100 mb-8">
            <div className="flex items-center gap-3 px-3 py-1">
              <img src={logo} alt="Mariwasa Logo" className="h-6 w-6 object-contain" />
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-600">Careers Portal</span>
            </div>
          </div>
          <h1 className="text-5xl md:text-7xl font-normal tracking-tight text-gray-900 mb-6 leading-tight">
            Join <span className="font-semibold text-[#D60041]">Mariwasa Siam</span> Ceramics
          </h1>
          <p className="text-gray-600 text-lg md:text-xl font-normal max-w-2xl mx-auto leading-relaxed">
            Experience an AI-driven recruitment process designed to match your potential with our innovation.
          </p>
        </section>

        <div className="grid md:grid-cols-2 gap-6 mb-24 max-w-6xl mx-auto px-6">
          <div className="bg-white p-12 rounded-[32px] border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 group relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 w-32 h-32 bg-pink-50 rounded-bl-[100px] z-0 opacity-50 group-hover:scale-110 transition-transform"></div>
            <div className="relative z-10 flex-grow">
              <div className="w-16 h-16 bg-red-50 text-[#D60041] rounded-2xl mb-8 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Briefcase size={32} />
              </div>
              <h3 className="text-3xl font-semibold mb-4 text-gray-900 tracking-tight">Browse Openings</h3>
              <p className="text-gray-600 text-base mb-10 leading-relaxed">
                Explore our current job listings across various departments and apply directly to the role that fits your expertise.
              </p>
            </div>
            <a href="/careerspage" className="w-full bg-white border border-gray-200 hover:border-[#D60041] hover:text-[#D60041] text-gray-800 py-3.5 rounded-full font-medium flex items-center justify-center space-x-2 transition-all relative z-10">
              <span>View Positions</span>
              <ArrowRight size={18} />
            </a>
          </div>

          <div className="bg-[#1A1A1A] p-12 rounded-[32px] shadow-sm hover:shadow-xl hover:shadow-gray-900/20 transition-all duration-300 group relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-bl-[100px] z-0 opacity-50 group-hover:scale-110 transition-transform"></div>
            <div className="relative z-10 flex-grow">
              <div className="w-16 h-16 bg-white/10 text-white rounded-2xl mb-8 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FileUp size={32} />
              </div>
              <h3 className="text-3xl font-semibold mb-4 text-white tracking-tight">Smart Application</h3>
              <p className="text-gray-400 text-base mb-10 leading-relaxed">
                Not sure where you fit? Upload your resume and let our Automated AI Analysis System match you with future opportunities.
              </p>
            </div>
            <a href="/smart-upload" className="w-full bg-[#D60041] hover:bg-[#b50037] text-white py-3.5 rounded-full font-medium flex items-center justify-center space-x-2 transition-all relative z-10">
              <span>Upload Resume</span>
              <ArrowRight size={18} />
            </a>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-6xl mx-auto mb-24 px-6">
          {[
            { title: "AI Review", desc: "Automated analysis ensures your profile is accurately evaluated immediately by HR.", icon: <ShieldCheck /> },
            { title: "Perfect Match", desc: "We match your skills precisely with our technical requirements without human bias.", icon: <CheckCircle /> },
            { title: "Real-time Status", desc: "Track every stage of your application securely through your dashboard.", icon: <LogIn /> }
          ].map((feature, idx) => (
            <div key={idx} className="bg-white p-8 rounded-[24px] border border-gray-100 hover:border-gray-200 transition-colors">
              <div className="text-[#D60041] mb-5 flex justify-start">
                <div className="p-3 bg-red-50 rounded-xl">
                  {React.cloneElement(feature.icon, { size: 24 })}
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 text-lg mb-2">{feature.title}</h4>
              <p className="text-sm text-gray-600 leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>

        <section className="max-w-6xl mx-auto px-6 mb-24">
          <div className="bg-white rounded-[32px] border border-gray-100 shadow-sm p-10 md:p-16 flex flex-col md:flex-row items-center gap-12 relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-gray-50 rounded-full blur-3xl opacity-50 -translate-y-1/2 translate-x-1/2"></div>

            <div className="flex-1 relative z-10">
              <h2 className="text-3xl font-semibold mb-6 text-gray-900 tracking-tight">About Mariwasa Siam Ceramics</h2>
              <p className="text-gray-600 text-base mb-8 leading-relaxed">
                The Philippines' leading ceramic manufacturer. We combine traditional craftsmanship with Siam-standard technology to build the homes of tomorrow. Discover how we're modernizing the talent experience.
              </p>
              <a href="/aboutpage" className="inline-flex items-center space-x-2 text-[#D60041] font-medium hover:underline">
                <span>Learn more about our legacy</span>
                <ArrowRight size={16} />
              </a>
            </div>

            <div className="flex-1 relative z-10 w-full flex flex-col gap-4">
              <div className="bg-gray-50 p-6 rounded-[20px] border border-gray-100 flex items-start gap-4">
                <div className="w-10 h-10 bg-white shadow-sm rounded-lg flex items-center justify-center shrink-0 text-[#D60041]">
                  <CheckCircle size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Our Mission</h4>
                  <p className="text-sm text-gray-600">To revolutionize the ceramic industry through sustainable innovation.</p>
                </div>
              </div>
              <div className="bg-gray-50 p-6 rounded-[20px] border border-gray-100 flex items-start gap-4">
                <div className="w-10 h-10 bg-white shadow-sm rounded-lg flex items-center justify-center shrink-0 text-gray-800">
                  <Briefcase size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Why Choose Us</h4>
                  <p className="text-sm text-gray-600">Competitive compensation, growth paths, and global standards.</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default LandingPage;
