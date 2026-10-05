import React, { useState, useEffect } from 'react';
import profileService from '../../services/profileService';
import { Helmet } from 'react-helmet-async';
import { useNavigate } from 'react-router-dom';
import {
  User,
  Mail,
  MapPin,
  Briefcase,
  ShieldCheck,
  Edit3,
  ArrowLeft,
  Building2,
  Calendar,
  Zap,
  CheckCircle2,
  TrendingUp,
  Globe,
  Award,
  Link as LinkIcon,
  Clock,
  FileText,
  Users
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { useDispatch, useSelector } from 'react-redux';
import { updateProfileImage } from '../../redux/slices/authSlice';

const BRAND_RED = "#D10043";

const ViewProfile = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [, setLoading] = useState(true);

  const userEmail = localStorage.getItem('saved_email') || 'user@system.com';
  const userRole = localStorage.getItem('role') || 'Guest';
  const userId = localStorage.getItem('user_id');
  const dispatch = useDispatch();
  const { profileImageUrl } = useSelector(state => state.auth);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!userId) {
        setLoading(false);
        return;
      }
      try {
        const response = await profileService.getProfile(userRole, userId);
        const data = response.data;
        // If it's the current user, sync with Redux
        if (data.id === parseInt(userId) && data.profile_image_url) {
          dispatch(updateProfileImage(data.profile_image_url));
        }
        setProfile(data);
      } catch (err) {
        console.error("Failed to fetch profile:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [userRole, userId, dispatch]);

  const profileData = {
    name: profile?.fullname || (userRole === 'CANDIDATE' ? "Candidate User" : userRole === 'HR' ? "HR Official" : "Admin User"),
    title: profile?.current_job_title || profile?.position || (userRole === 'CANDIDATE' ? "Professional Title" : userRole === 'HR' ? "HR Professional" : "System Administrator"),
    location: profile?.location || "Location not set",
    bio: profile?.bio || (userRole === 'CANDIDATE'
      ? "No professional bio provided yet."
      : `Member of the Mariwasa ${userRole === 'HR' ? 'Human Resources' : 'Administration'} Team.`),
    since: userRole === 'CANDIDATE' ? "Joined Mariwasa" : "Member since 2024",
    stats: userRole === 'CANDIDATE' ? [
      { label: "Applications", value: profile?.applications_count ?? "0", icon: <FileText size={18} /> },
      { label: "Interviews", value: profile?.interviews_count ?? "0", icon: <Calendar size={18} /> },
      { label: "Offers", value: profile?.offers_count ?? "0", icon: <Award size={18} /> }
    ] : [
      { label: "Screened", value: profile?.screened_count ?? "0", icon: <Users size={18} /> },
      { label: "Job Posts", value: profile?.job_posts_count ?? "0", icon: <Briefcase size={18} /> },
      { label: "Reports", value: profile?.reports_count ?? "0", icon: <TrendingUp size={18} /> }
    ]
  };

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - {userRole.charAt(0) + userRole.slice(1).toLowerCase()} Profile</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-grow min-w-0 w-full overflow-hidden">

          {/* Hero Banner Header */}
          <div className="relative h-48 sm:h-60 md:h-72 lg:h-80 w-full bg-slate-900 overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-[#D10043]/40 to-slate-900 opacity-60" />
            <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10" />

            <div className="max-w-[1400px] mx-auto px-4 sm:px-6 md:px-8 h-full relative flex items-start pt-4 sm:pt-6 md:pt-8">
              <button
                onClick={() => navigate(-1)}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-xl sm:rounded-2xl bg-black/40 hover:bg-black/60 backdrop-blur-md border border-white/15 text-white/90 hover:text-white text-xs font-black uppercase tracking-wider transition-all shadow-md group active:scale-95"
              >
                <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
                <span>Back</span>
              </button>
            </div>
          </div>

          {/* Profile Body Container */}
          <div className="max-w-[1400px] mx-auto px-4 sm:px-6 md:px-8 -mt-16 sm:-mt-24 md:-mt-28 lg:-mt-32 relative z-10 pb-16 sm:pb-20">
            <div className="flex flex-col lg:flex-row gap-6 sm:gap-8 lg:gap-10">

              {/* Left Column: Avatar, Profile Details & Contact Info */}
              <div className="w-full lg:w-[380px] xl:w-[400px] shrink-0">
                <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] lg:rounded-[48px] p-6 sm:p-8 lg:p-10 shadow-xl shadow-slate-200/50 text-center animate-in fade-in slide-in-from-bottom-8 duration-700">

                  {/* Avatar */}
                  <div className="relative inline-block mb-6 sm:mb-8">
                    <div className="w-28 h-28 sm:w-36 sm:h-36 md:w-40 md:h-40 rounded-3xl sm:rounded-[40px] md:rounded-[48px] bg-slate-50 border-4 sm:border-8 border-white shadow-xl sm:shadow-2xl overflow-hidden flex items-center justify-center text-slate-200 mx-auto">
                      {profileImageUrl ? (
                        <img 
                          src={profileImageUrl} 
                          alt="Profile" 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            if (e.target.nextSibling) {
                              e.target.nextSibling.style.display = 'flex';
                            }
                          }}
                        />
                      ) : null}
                      <div className={`fallback-icon items-center justify-center w-full h-full ${profileImageUrl ? 'hidden' : 'flex'}`}>
                        {userRole === 'CANDIDATE' ? <User size={64} className="sm:w-20 sm:h-20" /> : <ShieldCheck size={64} className="sm:w-20 sm:h-20" />}
                      </div>
                    </div>
                    <div className="absolute -bottom-1 -right-1 sm:-bottom-2 sm:-right-2 w-8 h-8 sm:w-10 sm:h-10 bg-green-500 rounded-xl sm:rounded-2xl border-2 sm:border-4 border-white flex items-center justify-center shadow-md sm:shadow-lg">
                      <CheckCircle2 size={16} className="text-white" strokeWidth={3} />
                    </div>
                  </div>

                  {/* Name and Title */}
                  <h2 className="text-xl sm:text-2xl md:text-3xl font-black text-slate-900 tracking-tight mb-1.5 break-words">
                    {profileData.name}
                  </h2>
                  <p className="text-[#D10043] font-black text-xs uppercase tracking-[0.15em] sm:tracking-[0.2em] mb-4 sm:mb-6 break-words">
                    {profileData.title}
                  </p>

                  {/* Location Badge */}
                  <div className="flex items-center justify-center gap-2 mb-6 sm:mb-8 bg-slate-50 py-2 sm:py-2.5 px-3.5 sm:px-4 rounded-xl sm:rounded-2xl border border-slate-100 w-fit max-w-full mx-auto">
                    <MapPin size={14} className="text-slate-400 shrink-0" />
                    <span className="text-[10px] sm:text-[11px] font-black text-slate-500 uppercase tracking-widest truncate">
                      {profileData.location}
                    </span>
                  </div>

                  {/* Edit Profile CTA */}
                  <button
                    onClick={() => navigate(userRole === 'ADMIN' ? '/admin/settings' : userRole === 'HR' ? '/hr/settings' : '/candidate/settings')}
                    className="w-full py-3.5 sm:py-4 bg-slate-900 text-white rounded-xl sm:rounded-2xl lg:rounded-[24px] font-black uppercase tracking-widest text-[10px] sm:text-xs hover:bg-[#D10043] transition-all shadow-lg active:scale-[0.98] flex items-center justify-center gap-2 mb-4"
                  >
                    <Edit3 size={15} /> <span>Edit Profile</span>
                  </button>

                  {/* Quick Meta Details */}
                  <div className="pt-6 sm:pt-8 mt-6 sm:mt-8 border-t border-slate-100 space-y-3 sm:space-y-4">
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest">
                      <span>Member Type</span>
                      <span className="text-slate-900 font-extrabold">{userRole}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest">
                      <span>Account Status</span>
                      <span className="text-green-600 font-extrabold flex items-center gap-1">
                        <CheckCircle2 size={13} className="text-green-500" />
                        Verified
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest">
                      <span>Join Date</span>
                      <span className="text-slate-900 font-extrabold">{profileData.since}</span>
                    </div>
                  </div>
                </div>

                {/* Contact Information Card */}
                <div className="mt-6 sm:mt-8 bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] p-6 sm:p-8 lg:p-10 shadow-lg shadow-slate-200/40 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                  <h3 className="text-xs sm:text-sm font-black text-slate-900 tracking-widest uppercase mb-5 sm:mb-8 flex items-center gap-2">
                    <Mail size={16} className="text-[#D10043]" />
                    <span>Contact Information</span>
                  </h3>
                  <div className="space-y-4 sm:space-y-6">
                    <div className="flex items-center gap-3.5 sm:gap-4">
                      <div className="w-10 h-10 sm:w-11 sm:h-11 bg-slate-50 rounded-xl sm:rounded-2xl flex items-center justify-center text-[#D10043] shrink-0 border border-slate-100">
                        <Mail size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Email Address</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-900 truncate" title={userEmail}>
                          {userEmail}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3.5 sm:gap-4">
                      <div className="w-10 h-10 sm:w-11 sm:h-11 bg-slate-50 rounded-xl sm:rounded-2xl flex items-center justify-center text-[#D10043] shrink-0 border border-slate-100">
                        <Globe size={18} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Timezone</p>
                        <p className="text-xs sm:text-sm font-bold text-slate-900">GMT+8 (Manila)</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Key Metrics, Professional Bio & Highlights */}
              <div className="flex-grow space-y-6 sm:space-y-8 lg:space-y-10 min-w-0 w-full">

                {/* Role Key Metrics */}
                <div className="grid grid-cols-3 gap-2.5 sm:gap-4 lg:gap-6 animate-in fade-in slide-in-from-right-8 duration-700">
                  {profileData.stats.map((stat, idx) => (
                    <div
                      key={idx}
                      className="bg-white border border-slate-100 rounded-2xl sm:rounded-3xl p-3.5 sm:p-5 lg:p-6 shadow-md shadow-slate-200/30 flex flex-col sm:flex-row items-center sm:items-start text-center sm:text-left gap-2 sm:gap-4 transition-transform hover:-translate-y-0.5"
                    >
                      <div className="p-2 sm:p-2.5 lg:p-3 rounded-xl sm:rounded-2xl bg-pink-50 text-[#D10043] shrink-0">
                        {stat.icon}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-base sm:text-xl lg:text-2xl font-black text-slate-900 leading-tight truncate">
                          {stat.value}
                        </p>
                        <p className="text-[9px] sm:text-[10px] lg:text-xs font-bold text-slate-400 uppercase tracking-wider truncate">
                          {stat.label}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Professional Bio Card */}
                <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] lg:rounded-[48px] p-6 sm:p-8 lg:p-12 shadow-xl shadow-slate-200/40 animate-in fade-in slide-in-from-right-8 duration-700">
                  <div className="flex items-center gap-3 mb-6 sm:mb-8">
                    <div className="p-2.5 sm:p-3 bg-pink-50 rounded-xl sm:rounded-2xl shrink-0">
                      <Zap size={20} className="text-[#D10043]" />
                    </div>
                    <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight">
                      {userRole === 'CANDIDATE' ? 'Professional Bio' : 'Enterprise Focus'}
                    </h3>
                  </div>
                  <p className="text-slate-600 text-sm sm:text-base lg:text-lg leading-relaxed font-medium">
                    {profileData.bio}
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 lg:gap-6 mt-8 sm:mt-12">
                    {[
                      { label: "Expertise", value: "Modern Web", icon: <TrendingUp size={16} /> },
                      { label: "Availability", value: "Full-Time", icon: <Clock size={16} /> },
                      { label: "Languages", value: "EN, PH", icon: <Globe size={16} /> }
                    ].map((item, i) => (
                      <div key={i} className="bg-slate-50 p-4 sm:p-5 lg:p-6 rounded-2xl sm:rounded-3xl border border-slate-100">
                        <div className="text-[#D10043] mb-2 sm:mb-3">{item.icon}</div>
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{item.label}</p>
                        <p className="text-xs sm:text-sm font-black text-slate-900 truncate">{item.value}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Enterprise Standards / Contributions Card */}
                <div className="bg-slate-900 rounded-3xl sm:rounded-[40px] lg:rounded-[48px] p-6 sm:p-8 lg:p-12 text-white relative overflow-hidden group animate-in fade-in slide-in-from-right-8 duration-700 delay-100">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-[#D10043]/10 rounded-full blur-3xl -mr-32 -mt-32 group-hover:scale-150 transition-transform duration-1000 pointer-events-none" />

                  <div className="relative z-10">
                    <div className="flex justify-between items-center mb-6 sm:mb-10 gap-3">
                      <h3 className="text-lg sm:text-xl font-black tracking-tight">Legacy & Contributions</h3>
                      <Award className="text-[#D10043] shrink-0" size={28} />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6 lg:gap-8">
                      <div className="p-5 sm:p-6 bg-white/5 border border-white/10 rounded-2xl sm:rounded-3xl hover:bg-white/10 transition-all cursor-pointer group/item">
                        <div className="flex justify-between items-start mb-3 sm:mb-4">
                          <div className="w-10 h-10 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                            <Briefcase size={20} />
                          </div>
                          <LinkIcon size={16} className="text-white/20 group-hover/item:text-white transition-colors" />
                        </div>
                        <h4 className="font-black text-xs sm:text-sm uppercase tracking-widest mb-1.5 sm:mb-2 text-white">Internal Projects</h4>
                        <p className="text-xs text-white/50 font-medium leading-relaxed">
                          System-wide infrastructure updates and recruitment process automation.
                        </p>
                      </div>
                      <div className="p-5 sm:p-6 bg-white/5 border border-white/10 rounded-2xl sm:rounded-3xl hover:bg-white/10 transition-all cursor-pointer group/item">
                        <div className="flex justify-between items-start mb-3 sm:mb-4">
                          <div className="w-10 h-10 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                            <Award size={20} />
                          </div>
                          <LinkIcon size={16} className="text-white/20 group-hover/item:text-white transition-colors" />
                        </div>
                        <h4 className="font-black text-xs sm:text-sm uppercase tracking-widest mb-1.5 sm:mb-2 text-white">Certifications</h4>
                        <p className="text-xs text-white/50 font-medium leading-relaxed">
                          Verified by Mariwasa Enterprise Standards (MES) Level 4.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default ViewProfile;
