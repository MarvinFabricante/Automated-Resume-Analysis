import React, { useEffect, useRef, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { LogIn, LayoutDashboard, Briefcase, FileUp, CheckCircle, ShieldCheck, ArrowRight, FileText, CheckCircle2, Clock, Sparkles } from 'lucide-react';
import { useSelector } from 'react-redux';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import logo from '../../../assets/logo.png';
import { RootState } from '../../../redux/store';
import { isTokenExpired } from '../../../utils/token';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

const LandingPage: React.FC = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { role: reduxRole, isAuthenticated } = useSelector((state: RootState) => state.auth);
  const [activeRole, setActiveRole] = useState<string | null>(null);

  useEffect(() => {
    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const storedRole = typeof localStorage !== 'undefined' ? localStorage.getItem('role') : null;
    const hasSession = Boolean(token && !isTokenExpired(token)) || isAuthenticated;
    const resolved = hasSession ? (reduxRole || storedRole || '').toUpperCase() : '';
    setActiveRole(resolved && resolved !== 'GUEST' ? resolved : null);
  }, [reduxRole, isAuthenticated]);

  const dashboardHref =
    activeRole === 'ADMIN'
      ? '/admin/dashboard'
      : activeRole === 'HR'
        ? '/hr/dashboard'
        : activeRole === 'CANDIDATE'
          ? '/candidate/dashboard'
          : '/login';

  const positionsHref =
    activeRole === 'ADMIN'
      ? '/admin/jobmanagement'
      : activeRole === 'HR'
        ? '/hr/screeningportal'
        : activeRole === 'CANDIDATE'
          ? '/candidate/findjobs'
          : '/careerspage';

  const uploadHref =
    activeRole === 'CANDIDATE'
      ? '/candidate/smart-upload'
      : activeRole === 'HR'
        ? '/hr/physical-resumes'
        : activeRole === 'ADMIN'
          ? '/admin/dashboard'
          : '/smart-upload';

  useGSAP(
    () => {
      // 1. Hero Entrance Animation
      const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });

      heroTl
        .fromTo(
          '.hero-badge',
          { y: -24, opacity: 0, scale: 0.92 },
          { y: 0, opacity: 1, scale: 1, duration: 0.8, clearProps: 'transform' }
        )
        .fromTo(
          '.hero-title',
          { y: 35, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.9, clearProps: 'all' },
          '-=0.45'
        )
        .fromTo(
          '.hero-desc',
          { y: 25, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.8, clearProps: 'all' },
          '-=0.55'
        );

      // Subtle float animation for the hero badge
      gsap.to('.hero-badge', {
        y: -4,
        duration: 2.4,
        repeat: -1,
        yoyo: true,
        ease: 'sine.inOut',
        delay: 1.2,
      });

      // 2. Action Cards (Browse Openings & Smart Application)
      gsap.fromTo(
        '.action-card',
        { y: 50, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.85,
          stagger: 0.18,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.action-cards-container',
            start: 'top 88%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.action-card-icon',
        { scale: 0.6, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.65,
          stagger: 0.18,
          delay: 0.15,
          ease: 'back.out(1.8)',
          scrollTrigger: {
            trigger: '.action-cards-container',
            start: 'top 88%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      // 3. Feature Cards Stagger
      gsap.fromTo(
        '.feature-card',
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.14,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.features-container',
            start: 'top 88%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.feature-icon-box',
        { scale: 0.6, rotate: -10, opacity: 0 },
        {
          scale: 1,
          rotate: 0,
          opacity: 1,
          duration: 0.6,
          stagger: 0.14,
          delay: 0.1,
          ease: 'back.out(2)',
          scrollTrigger: {
            trigger: '.features-container',
            start: 'top 88%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      // 4. About Mariwasa Section Reveal & Ambient Parallax
      gsap.fromTo(
        '.about-preview-card',
        { y: 45, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.85,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.about-preview-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.about-preview-left',
        { x: -35, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.85,
          delay: 0.1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.about-preview-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.about-preview-pill',
        { x: 35, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.85,
          stagger: 0.16,
          delay: 0.2,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.about-preview-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.to('.about-blur-orb', {
        y: 50,
        ease: 'none',
        scrollTrigger: {
          trigger: '.about-preview-section',
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1.2,
        },
      });

      // Refresh ScrollTrigger after layout settles
      ScrollTrigger.refresh();
    },
    { scope: containerRef }
  );

  return (
    <div ref={containerRef} className="relative bg-[#FAFAFC] text-gray-800 antialiased font-sans min-h-screen supports-[min-height:100dvh]:min-h-[100dvh] flex flex-col overflow-x-clip">
      <Helmet>
        <title>Mariwasa Recruitment | Careers</title>
      </Helmet>

      {/* Subtle Ceramic Tile / Mosaic SVG Pattern Background */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden" aria-hidden="true">
        <svg className="absolute w-full h-full opacity-[0.035]" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="ceramic-tile-mosaic" width="80" height="80" patternUnits="userSpaceOnUse">
              {/* Ceramic tile borders */}
              <rect x="2" y="2" width="36" height="36" rx="4" fill="none" stroke="#D60041" strokeWidth="1.5" />
              <rect x="42" y="2" width="36" height="36" rx="4" fill="none" stroke="#334155" strokeWidth="1.5" />
              <rect x="2" y="42" width="36" height="36" rx="4" fill="none" stroke="#334155" strokeWidth="1.5" />
              <rect x="42" y="42" width="36" height="36" rx="4" fill="none" stroke="#D60041" strokeWidth="1.5" />
              {/* Inner geometric mosaic diamonds */}
              <path d="M20 12 L28 20 L20 28 L12 20 Z" fill="#D60041" opacity="0.4" />
              <path d="M60 52 L68 60 L60 68 L52 60 Z" fill="#D60041" opacity="0.4" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#ceramic-tile-mosaic)" />
        </svg>

        {/* Soft tile-like ambient gradient shapes (respects prefers-reduced-motion) */}
        <div className="absolute top-16 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-gradient-to-br from-rose-100/40 via-red-50/20 to-transparent rounded-[80px] blur-3xl -rotate-6 motion-safe:animate-pulse" style={{ animationDuration: '6s' }} />
        <div className="absolute top-96 right-10 w-80 h-80 bg-rose-50/40 rounded-[60px] blur-2xl rotate-12" />
        <div className="absolute top-[600px] left-10 w-96 h-96 bg-slate-100/60 rounded-[60px] blur-2xl -rotate-12" />
      </div>

      <Header />

      <main className="flex-grow pt-16 relative z-10">

        {/* Hero Section */}
        <section className="text-center px-4 sm:px-6 max-w-5xl mx-auto mb-16 sm:mb-20 mt-6 sm:mt-10 relative z-10">
          <div className="hero-badge inline-flex items-center gap-2 p-1.5 px-3.5 rounded-full bg-white/90 backdrop-blur-xs shadow-xs border border-slate-200/80 mb-6 sm:mb-8 will-change-transform">
            <img src={(logo as any)?.src || logo} alt="Mariwasa Logo" className="h-5 w-5 sm:h-6 sm:w-6 object-contain" />
            <span className="text-[11px] sm:text-xs font-bold uppercase tracking-wider text-slate-700">Mariwasa Recruitment • Careers</span>
          </div>

          <h1 className="hero-title text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-black tracking-tight text-slate-900 mb-4 sm:mb-6 leading-tight will-change-transform">
            Build your career with <span className="text-[#D60041]">Mariwasa</span>
          </h1>

          <p className="hero-desc text-slate-600 text-base sm:text-lg md:text-xl font-normal max-w-2xl mx-auto leading-relaxed mb-8 sm:mb-10 will-change-transform">
            Explore open positions across our manufacturing, engineering, and operations teams, and find the role that fits you best.
          </p>

          {/* Primary & Secondary Action Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3.5 sm:gap-4 max-w-xl mx-auto mb-10 sm:mb-12">
            <a
              href={positionsHref}
              className="w-full sm:w-auto min-h-[44px] px-8 py-3.5 rounded-2xl bg-[#D60041] hover:bg-slate-900 text-white font-black text-sm uppercase tracking-wider flex items-center justify-center gap-2.5 whitespace-nowrap transition-all shadow-md shadow-[#D60041]/20 active:scale-[0.98] cursor-pointer touch-manipulation"
            >
              <Briefcase size={18} />
              <span>View Open Positions</span>
              <ArrowRight size={16} />
            </a>

            <a
              href={dashboardHref}
              className="w-full sm:w-auto min-h-[44px] px-7 py-3.5 rounded-2xl bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 border border-slate-200 font-bold text-sm uppercase tracking-wider flex items-center justify-center gap-2 whitespace-nowrap transition-all shadow-2xs active:scale-[0.98] cursor-pointer touch-manipulation"
            >
              {activeRole ? (
                <>
                  <LayoutDashboard size={18} className="text-[#D60041]" />
                  <span>Go to Dashboard</span>
                </>
              ) : (
                <>
                  <LogIn size={18} className="text-slate-400" />
                  <span>Sign in</span>
                </>
              )}
            </a>
          </div>

          {/* Simple Decorative Job/Resume Mosaic Badges */}
          <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-bold text-slate-500">
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/80 border border-slate-200/60 shadow-2xs">
              <Briefcase size={14} className="text-[#D60041]" /> Manufacturing & Plant Careers
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/80 border border-slate-200/60 shadow-2xs">
              <FileText size={14} className="text-slate-600" /> Fast Resume Screening
            </span>
          </div>
        </section>

        {/* 3-STEP APPLICANT STRIP */}
        <section className="max-w-5xl mx-auto px-4 sm:px-6 mb-20 sm:mb-24 relative z-10">
          <div className="bg-white/90 backdrop-blur-xs rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-xs">
            <div className="text-center mb-6">
              <span className="text-[10px] font-black uppercase tracking-widest text-[#D60041] bg-rose-50 px-3 py-1 rounded-full border border-rose-100">
                How It Works
              </span>
              <h2 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight mt-2">
                Apply in 3 Simple Steps
              </h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50/70 border border-slate-100 flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-white shadow-2xs border border-slate-200 flex items-center justify-center text-[#D60041] font-black text-sm shrink-0">
                  1
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Upload resume</h4>
                  <p className="text-xs text-slate-500 font-medium mt-0.5 leading-relaxed">
                    Attach your PDF or Word document in seconds.
                  </p>
                </div>
              </div>

              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50/70 border border-slate-100 flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-white shadow-2xs border border-slate-200 flex items-center justify-center text-[#D60041] font-black text-sm shrink-0">
                  2
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Answer a few questions</h4>
                  <p className="text-xs text-slate-500 font-medium mt-0.5 leading-relaxed">
                    Review your auto-filled details and answer short questions.
                  </p>
                </div>
              </div>

              <div className="p-4 sm:p-5 rounded-2xl bg-slate-50/70 border border-slate-100 flex items-start gap-3.5">
                <div className="w-10 h-10 rounded-xl bg-white shadow-2xs border border-slate-200 flex items-center justify-center text-emerald-600 font-black text-sm shrink-0">
                  3
                </div>
                <div>
                  <h4 className="font-bold text-slate-900 text-sm">Get your results</h4>
                  <p className="text-xs text-slate-500 font-medium mt-0.5 leading-relaxed">
                    See how well you fit and track your status online.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Action Cards */}
        <div className="action-cards-container grid md:grid-cols-2 gap-6 mb-24 max-w-6xl mx-auto px-6">
          <div className="action-card bg-white p-8 md:p-12 rounded-[32px] border border-gray-100 shadow-sm hover:shadow-xl transition-all duration-300 group relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 w-32 h-32 bg-pink-50 rounded-bl-[100px] z-0 opacity-50 group-hover:scale-110 transition-transform pointer-events-none" aria-hidden="true"></div>
            <div className="relative z-10 flex-grow">
              <div className="action-card-icon w-16 h-16 bg-red-50 text-[#D60041] rounded-2xl mb-8 flex items-center justify-center group-hover:scale-110 transition-transform">
                <Briefcase size={32} />
              </div>
              <h3 className="text-3xl font-semibold mb-4 text-gray-900 tracking-tight">Browse Open Positions</h3>
              <p className="text-gray-600 text-base mb-10 leading-relaxed">
                Explore our current job openings across plant operations, maintenance, quality assurance, and supply chain.
              </p>
            </div>
            <a href={positionsHref} className="w-full min-h-[44px] bg-white border border-gray-200 hover:border-[#D60041] hover:text-[#D60041] text-gray-800 py-3.5 rounded-full font-medium flex items-center justify-center space-x-2 transition-all relative z-10 cursor-pointer touch-manipulation">
              <span>View Positions</span>
              <ArrowRight size={18} />
            </a>
          </div>

          <div className="action-card bg-[#1A1A1A] p-8 md:p-12 rounded-[32px] shadow-sm hover:shadow-xl hover:shadow-gray-900/20 transition-all duration-300 group relative overflow-hidden flex flex-col">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-bl-[100px] z-0 opacity-50 group-hover:scale-110 transition-transform pointer-events-none" aria-hidden="true"></div>
            <div className="relative z-10 flex-grow">
              <div className="action-card-icon w-16 h-16 bg-white/10 text-white rounded-2xl mb-8 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FileUp size={32} />
              </div>
              <h3 className="text-3xl font-semibold mb-4 text-white tracking-tight">Upload Your Resume</h3>
              <p className="text-gray-400 text-base mb-10 leading-relaxed">
                Upload your resume and we'll compare your background with our open positions to show you your best fit.
              </p>
            </div>
            <a href={uploadHref} className="w-full min-h-[44px] bg-[#D60041] hover:bg-[#b50037] text-white py-3.5 rounded-full font-medium flex items-center justify-center space-x-2 transition-all relative z-10 cursor-pointer touch-manipulation">
              <span>Upload Resume</span>
              <ArrowRight size={18} />
            </a>
          </div>
        </div>

        {/* Feature Cards */}
        <div className="features-container grid md:grid-cols-3 gap-6 max-w-6xl mx-auto mb-24 px-6">
          {[
            { title: "Quick Review", desc: "Our recruitment team evaluates your qualifications efficiently so you receive timely updates.", icon: <Clock /> },
            { title: "Skills Matching", desc: "We compare your experience with open positions to highlight opportunities where you can excel.", icon: <CheckCircle /> },
            { title: "Track Your Progress", desc: "Follow every step of your application from initial submission to interview scheduling.", icon: <CheckCircle2 /> }
          ].map((feature, idx) => (
            <div key={idx} className="feature-card bg-white p-6 md:p-8 rounded-[24px] border border-gray-100 hover:border-gray-200 hover:shadow-md transition-all duration-300 will-change-transform">
              <div className="text-[#D60041] mb-5 flex justify-start">
                <div className="feature-icon-box p-3 bg-red-50 rounded-xl">
                  {React.cloneElement(feature.icon, { size: 24 } as any)}
                </div>
              </div>
              <h4 className="font-semibold text-gray-900 text-lg mb-2">{feature.title}</h4>
              <p className="text-sm text-gray-600 leading-relaxed">{feature.desc}</p>
            </div>
          ))}
        </div>

        {/* About Preview Section */}
        <section className="about-preview-section max-w-6xl mx-auto px-6 mb-24">
          <div className="about-preview-card bg-white rounded-[32px] border border-gray-100 shadow-sm p-8 md:p-16 flex flex-col md:flex-row items-center gap-12 relative overflow-hidden">
            <div className="about-blur-orb absolute top-0 right-0 w-64 h-64 bg-pink-100/60 rounded-full blur-3xl pointer-events-none -translate-y-1/2 translate-x-1/2"></div>

            <div className="about-preview-left flex-1 relative z-10">
              <h2 className="text-3xl font-semibold mb-6 text-gray-900 tracking-tight">About Mariwasa Siam Ceramics</h2>
              <p className="text-gray-600 text-base mb-8 leading-relaxed">
                The Philippines' leading ceramic manufacturer. We combine traditional craftsmanship with Siam-standard technology to build the homes of tomorrow. Discover how we're modernizing the talent experience.
              </p>
              <a href="/aboutpage" className="inline-flex items-center space-x-2 min-h-[44px] py-2 text-[#D60041] font-medium hover:underline group cursor-pointer touch-manipulation">
                <span>Learn more about our legacy</span>
                <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
              </a>
            </div>

            <div className="flex-1 relative z-10 w-full flex flex-col gap-4">
              <div className="about-preview-pill bg-gray-50 hover:bg-gray-100/80 p-6 rounded-[20px] border border-gray-100 transition-colors flex items-start gap-4 will-change-transform">
                <div className="w-10 h-10 bg-white shadow-sm rounded-lg flex items-center justify-center shrink-0 text-[#D60041]">
                  <CheckCircle size={20} />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900 mb-1">Our Mission</h4>
                  <p className="text-sm text-gray-600">To revolutionize the ceramic industry through sustainable innovation.</p>
                </div>
              </div>
              <div className="about-preview-pill bg-gray-50 hover:bg-gray-100/80 p-6 rounded-[20px] border border-gray-100 transition-colors flex items-start gap-4 will-change-transform">
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
