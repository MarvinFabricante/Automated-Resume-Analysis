import React, { useState, useEffect, useRef } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  CheckCircle,
  Target,
  Users,
  History,
  Globe,
  Cpu,
  ArrowRight,
  Search,
  Award
} from 'lucide-react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { useGSAP } from '@gsap/react';
import Header from '../../../components/layout/Header';
import Footer from '../../../components/layout/Footer';
import banner from '../../../assets/banner.jpg';
import banner2 from '../../../assets/banner2.jpg';
import banner3 from '../../../assets/banner3.jpg';
import subHeader from '../../../assets/sub header.jpg';

if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

const getAssetSrc = (asset: any): string => (asset && typeof asset === 'object' && asset.src ? asset.src : asset);

const BANNERS = [
  getAssetSrc(banner),
  getAssetSrc(banner2),
  getAssetSrc(banner3)
];

const AboutPage: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % BANNERS.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  useGSAP(
    () => {
      // 1. Hero Entrance & Subtle Parallax
      const heroTl = gsap.timeline({ defaults: { ease: 'power3.out' } });

      heroTl
        .fromTo(
          '.about-hero-title',
          { y: 40, opacity: 0 },
          { y: 0, opacity: 1, duration: 1, clearProps: 'all' }
        )
        .fromTo(
          '.about-hero-desc',
          { y: 25, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.85, clearProps: 'all' },
          '-=0.55'
        )
        .fromTo(
          '.about-hero-dots',
          { y: 15, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.7, clearProps: 'all' },
          '-=0.45'
        );

      // Hero banner parallax scrub on scroll
      gsap.to('.hero-bg-layer', {
        yPercent: 18,
        ease: 'none',
        scrollTrigger: {
          trigger: '.about-hero-section',
          start: 'top top',
          end: 'bottom top',
          scrub: true,
        },
      });

      // 2. Legacy Section Reveal
      gsap.fromTo(
        '.legacy-card',
        { y: 45, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.85,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.legacy-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.legacy-text-item',
        { x: -35, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.12,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.legacy-section',
            start: 'top 82%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.legacy-image',
        { scale: 0.94, y: 25, opacity: 0 },
        {
          scale: 1,
          y: 0,
          opacity: 1,
          duration: 0.85,
          delay: 0.1,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.legacy-section',
            start: 'top 82%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.to('.legacy-glow-orb', {
        y: 60,
        ease: 'none',
        scrollTrigger: {
          trigger: '.legacy-section',
          start: 'top bottom',
          end: 'bottom top',
          scrub: 1.2,
        },
      });

      // 3. 4-Step Process Section
      gsap.fromTo(
        '.process-header',
        { y: 30, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.8,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: '.process-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.process-step-card',
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.12,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.process-steps-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.process-step-icon',
        { scale: 0.6, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.6,
          stagger: 0.12,
          delay: 0.1,
          ease: 'back.out(2)',
          scrollTrigger: {
            trigger: '.process-steps-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      // 4. Mission & Vision Split Cards
      gsap.fromTo(
        '.mission-card',
        { x: -40, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.85,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.mission-vision-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.vision-card',
        { x: 40, opacity: 0 },
        {
          x: 0,
          opacity: 1,
          duration: 0.85,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.mission-vision-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.mission-vision-icon',
        { scale: 0.5, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.6,
          delay: 0.15,
          stagger: 0.12,
          ease: 'back.out(2)',
          scrollTrigger: {
            trigger: '.mission-vision-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      // 5. Core Values Stagger
      gsap.fromTo(
        '.values-header',
        { y: 25, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.75,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: '.values-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.value-card',
        { y: 40, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.8,
          stagger: 0.14,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.values-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.value-icon-box',
        { scale: 0.5, rotate: -12, opacity: 0 },
        {
          scale: 1,
          rotate: 0,
          opacity: 1,
          duration: 0.6,
          stagger: 0.14,
          delay: 0.1,
          ease: 'back.out(2)',
          scrollTrigger: {
            trigger: '.values-grid',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      // 6. Call to Action Banner
      gsap.fromTo(
        '.about-cta-card',
        { scale: 0.95, y: 35, opacity: 0 },
        {
          scale: 1,
          y: 0,
          opacity: 1,
          duration: 0.85,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: '.about-cta-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      gsap.fromTo(
        '.about-cta-btn',
        { scale: 0.85, opacity: 0 },
        {
          scale: 1,
          opacity: 1,
          duration: 0.6,
          delay: 0.2,
          ease: 'back.out(1.8)',
          scrollTrigger: {
            trigger: '.about-cta-section',
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
          clearProps: 'all',
        }
      );

      // Refresh ScrollTrigger after layout settles
      ScrollTrigger.refresh();
    },
    { scope: containerRef }
  );

  return (
    <div ref={containerRef} className="bg-[transparent] text-gray-800 antialiased font-sans min-h-screen flex flex-col">
      <Helmet>
        <title>About Us - Mariwasa Portal</title>
      </Helmet>
      <Header />

      <main className="flex-grow">
        {/* Hero Section with Parallax Background */}
        <section className="about-hero-section relative w-full h-[360px] sm:h-[450px] md:h-[650px] flex items-center justify-center overflow-hidden">
          {BANNERS.map((bg, index) => (
            <div
              key={index}
              className={`hero-bg-layer absolute -inset-y-12 inset-x-0 w-full h-[120%] bg-cover bg-center transition-opacity duration-1000 z-0 will-change-transform ${index === currentSlide ? 'opacity-100' : 'opacity-0'}`}
              style={{ backgroundImage: `url('${bg}')` }}
            ></div>
          ))}
          <div className="absolute inset-0 bg-gray-900/75 z-10"></div>
          <div className="relative z-20 text-center px-4 sm:px-6 max-w-4xl mx-auto">
            <h1 className="about-hero-title text-2xl sm:text-4xl md:text-6xl font-normal tracking-tight text-white mb-3 sm:mb-6 leading-tight will-change-transform">
              Empowering the Future of <span className="text-[#D60041] font-semibold">Manufacturing</span>
            </h1>
            <p className="about-hero-desc text-sm sm:text-lg md:text-xl text-gray-200 font-normal leading-relaxed max-w-2xl mx-auto will-change-transform">
              Merging decades of ceramic excellence with cutting-edge AI technology to build the workforce of tomorrow.
            </p>
          </div>

          <div className="about-hero-dots absolute bottom-4 sm:bottom-10 left-1/2 -translate-x-1/2 z-30 flex gap-2 will-change-transform">
            {BANNERS.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setCurrentSlide(i)}
                aria-label={`Slide ${i + 1}`}
                className={`h-2 rounded-full transition-all duration-300 ${i === currentSlide ? 'bg-[#D60041] w-6 sm:w-8' : 'w-2 bg-white/30 hover:bg-white/50'}`}
              />
            ))}
          </div>
        </section>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 sm:py-12 md:py-20">

          {/* Legacy Section */}
          <section className="legacy-section mb-10 sm:mb-16 md:mb-20">
            <div className="legacy-card bg-white rounded-3xl md:rounded-[32px] shadow-sm border border-gray-100 p-5 sm:p-8 md:p-16 relative overflow-hidden will-change-transform">
              <div className="legacy-glow-orb absolute top-0 right-0 w-64 h-64 bg-pink-100/60 rounded-full blur-3xl opacity-60 -translate-y-1/2 translate-x-1/2 pointer-events-none"></div>
              <div className="relative z-10 flex flex-col md:flex-row gap-8 md:gap-12 items-center">
                <div className="flex-1">
                  <div className="legacy-text-item inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 text-[#D60041] text-xs font-semibold uppercase tracking-wider mb-4 sm:mb-6">
                    <History size={14} /> Our Legacy
                  </div>
                  <h2 className="legacy-text-item text-2xl sm:text-3xl md:text-4xl font-normal tracking-tight text-gray-900 mb-4 sm:mb-6 leading-tight">
                    A History of <span className="font-semibold text-[#D60041]">Uncompromising Quality</span>
                  </h2>
                  <p className="legacy-text-item text-gray-600 text-sm sm:text-base leading-relaxed mb-4">
                    Founded in 1966, Mariwasa Siam Ceramics Inc. has grown from a visionary local enterprise into the Philippines' premier ceramic tile manufacturer. We revolutionized the industry by introducing European technology and design while maintaining the rich heritage of Filipino craftsmanship.
                  </p>
                  <p className="legacy-text-item text-gray-600 text-sm sm:text-base leading-relaxed">
                    Today, as a proud member of the SCG (Siam Cement Group), we continue to push boundaries. Our commitment to sustainable manufacturing, product innovation, and community development has solidified our position as a trusted household name for over five decades.
                  </p>
                </div>
                <div className="legacy-image flex-1 w-full will-change-transform">
                  <img
                    src={getAssetSrc(subHeader)}
                    alt="Corporate Office"
                    className="rounded-2xl sm:rounded-[24px] object-cover w-full h-[220px] sm:h-[280px] md:h-[300px] shadow-sm"
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Process Section */}
          <section className="process-section mb-10 sm:mb-16 md:mb-20">
            <div className="process-header text-center mb-8 sm:mb-14 will-change-transform">
              <h2 className="text-2xl sm:text-3xl md:text-4xl font-normal tracking-tight text-gray-900 mb-3 sm:mb-4 leading-tight">
                The Mariwasa <span className="font-semibold text-[#D60041]">Resume Analysis System</span>
              </h2>
              <p className="text-gray-600 text-sm sm:text-base max-w-2xl mx-auto px-2">
                We believe that great companies are built by great people. This portal utilizes advanced AI to ensure a fair, skill-based, and highly efficient hiring process, removing human bias from initial screenings.
              </p>
            </div>

            <div className="process-steps-grid grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
              {[
                {
                  icon: Users,
                  title: "1. Create Profile",
                  desc: "Candidates register and upload their resumes to our secure portal."
                },
                {
                  icon: Cpu,
                  title: "2. AI Analysis",
                  desc: "Our automated system extracts skills, experience, and key metrics without bias."
                },
                {
                  icon: Search,
                  title: "3. Smart Matching",
                  desc: "Candidates are instantly matched with job openings that fit their unique profile."
                },
                {
                  icon: Award,
                  title: "4. Get Hired",
                  desc: "HR seamlessly reviews top matches and schedules interviews efficiently."
                }
              ].map((step, idx) => (
                <div key={idx} className="process-step-card bg-white p-5 sm:p-6 md:p-8 rounded-2xl sm:rounded-[24px] border border-gray-100 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden group will-change-transform">
                  <div className="absolute top-0 left-0 w-1 h-full bg-gray-100 group-hover:bg-[#D60041] transition-colors"></div>
                  <div className="process-step-icon w-11 h-11 sm:w-12 sm:h-12 bg-gray-50 rounded-xl flex items-center justify-center mb-4 sm:mb-6 group-hover:scale-110 transition-transform">
                    <step.icon className="text-[#D60041]" size={22} />
                  </div>
                  <h3 className="text-base sm:text-lg font-semibold text-gray-900 mb-2 sm:mb-3">{step.title}</h3>
                  <p className="text-xs sm:text-sm text-gray-600 leading-relaxed">{step.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Mission & Vision */}
          <div className="mission-vision-grid grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 md:gap-8 mb-10 sm:mb-16 md:mb-20">
            <div className="mission-card bg-white p-6 sm:p-8 md:p-12 rounded-3xl md:rounded-[32px] border border-gray-100 shadow-sm flex flex-col items-center text-center will-change-transform">
              <div className="mission-vision-icon w-14 h-14 sm:w-16 sm:h-16 bg-red-50 text-[#D60041] rounded-2xl flex items-center justify-center mb-5 sm:mb-6">
                <Target size={28} />
              </div>
              <h3 className="text-xl sm:text-2xl font-semibold mb-3 sm:mb-4 text-gray-900">Our Mission</h3>
              <p className="text-gray-600 text-sm sm:text-base leading-relaxed">
                To provide world-class ceramic products that enhance the Filipino living space,
                driven by a passion for excellence, environmental sustainability, and
                technological advancement.
              </p>
            </div>

            <div className="vision-card bg-[#1A1A1A] p-6 sm:p-8 md:p-12 rounded-3xl md:rounded-[32px] shadow-sm flex flex-col items-center text-center will-change-transform">
              <div className="mission-vision-icon w-14 h-14 sm:w-16 sm:h-16 bg-white/10 text-white rounded-2xl flex items-center justify-center mb-5 sm:mb-6">
                <Globe size={28} />
              </div>
              <h3 className="text-xl sm:text-2xl font-semibold mb-3 sm:mb-4 text-white">Our Vision</h3>
              <p className="text-gray-400 text-sm sm:text-base leading-relaxed">
                To be the leading innovator in the ceramic industry across Southeast Asia,
                setting the standard for aesthetic beauty, durability, and customer satisfaction
                in every tile we produce.
              </p>
            </div>
          </div>

          {/* Core Values */}
          <section className="values-section mb-10 sm:mb-16 md:mb-20">
            <h3 className="values-header text-center text-xl sm:text-2xl font-semibold mb-6 sm:mb-10 text-gray-900 will-change-transform">Our Core Values</h3>
            <div className="values-grid grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 sm:gap-6">
              {[
                {
                  title: "Innovation",
                  desc: "Constantly evolving our processes and products to lead the market.",
                  icon: Cpu
                },
                {
                  title: "Quality",
                  desc: "Adhering to strict Siam-standards to ensure lifelong durability.",
                  icon: CheckCircle
                },
                {
                  title: "People-First",
                  desc: "Empowering our employees and candidates through fair technology.",
                  icon: Users
                }
              ].map((value, idx) => (
                <div key={idx} className="value-card bg-white p-5 sm:p-6 md:p-8 rounded-2xl sm:rounded-[24px] border border-gray-100 text-center flex flex-col items-center hover:shadow-md transition-shadow will-change-transform">
                  <div className="value-icon-box text-[#D60041] mb-4 bg-red-50 p-3 rounded-xl">
                    <value.icon size={22} />
                  </div>
                  <h4 className="font-semibold text-gray-900 text-base sm:text-lg mb-2">{value.title}</h4>
                  <p className="text-xs sm:text-sm text-gray-600 leading-relaxed">{value.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* CTA Section */}
          <section className="about-cta-section text-center py-8 sm:py-12 md:py-16 px-4 sm:px-6 bg-white rounded-3xl md:rounded-[32px] border border-gray-100 shadow-sm relative overflow-hidden">
            <div className="about-cta-card relative z-10 max-w-2xl mx-auto will-change-transform">
              <h2 className="text-2xl sm:text-3xl font-normal tracking-tight mb-3 sm:mb-4 text-gray-900 leading-tight">Ready to join our team?</h2>
              <p className="text-gray-600 text-sm sm:text-base mb-6 sm:mb-8">
                Take the next step in your career. Upload your resume and let our AI match you with your perfect role at Mariwasa.
              </p>
              <a
                href="/careerspage"
                className="about-cta-btn inline-flex items-center justify-center space-x-2 bg-[#D60041] text-white px-6 sm:px-8 py-3 rounded-full font-medium hover:bg-[#b50037] transition-all shadow-sm w-full sm:w-auto text-sm sm:text-base will-change-transform"
              >
                <span>View Openings</span>
                <ArrowRight size={18} />
              </a>
            </div>
          </section>

        </div>
      </main>

      <Footer />
    </div>
  );
};

export default AboutPage;
