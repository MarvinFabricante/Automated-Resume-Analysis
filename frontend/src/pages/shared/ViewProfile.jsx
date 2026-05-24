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
  const [loading, setLoading] = useState(true);

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
  }, [userRole, userId]);

  const profileData = {
    name: profile?.fullname || (userRole === 'CANDIDATE' ? "Candidate User" : userRole === 'HR' ? "HR Official" : "Admin User"),
    title: profile?.current_job_title || profile?.position || (userRole === 'CANDIDATE' ? "Professional Title" : userRole === 'HR' ? "HR Professional" : "System Administrator"),
    location: profile?.location || "Location not set",
    bio: profile?.bio || (userRole === 'CANDIDATE'
      ? "No professional bio provided yet."
      : `Member of the Mariwasa ${userRole === 'HR' ? 'Human Resources' : 'Administration'} Team.`),
    since: userRole === 'CANDIDATE' ? "Joined Mariwasa" : "Member since 2024",
    stats: userRole === 'CANDIDATE' ? [
      { label: "Applications", value: "0", icon: <FileText size={18} /> },
      { label: "Interviews", value: "0", icon: <Calendar size={18} /> },
      { label: "Offers", value: "0", icon: <Award size={18} /> }
    ] : [
      { label: "Screened", value: "0", icon: <Users size={18} /> },
      { label: "Job Posts", value: "0", icon: <Briefcase size={18} /> },
      { label: "Reports", value: "0", icon: <TrendingUp size={18} /> }
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
        <main className="flex-grow">

        <div className="relative h-64 md:h-80 w-full bg-slate-900 overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-[#D10043]/40 to-slate-900 opacity-60" />
          <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-10" />

          <div className="max-w-[1400px] mx-auto px-6 h-full relative">
            <button
              onClick={() => navigate(-1)}
              className="absolute top-10 left-6 flex items-center gap-2 text-white/70 hover:text-white text-xs font-black uppercase tracking-widest transition-all group"
            >
              <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
              Back
            </button>
          </div>
        </div>

        <div className="max-w-[1400px] mx-auto px-6 -mt-24 md:-mt-32 relative z-10 pb-20">
          <div className="flex flex-col lg:flex-row gap-10">

            <div className="w-full lg:w-[400px] shrink-0">
              <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-2xl shadow-slate-200/50 text-center animate-in fade-in slide-in-from-bottom-8 duration-700">

                <div className="relative inline-block mb-8">
                  <div className="w-32 h-32 md:w-40 md:h-40 rounded-[48px] bg-slate-50 border-8 border-white shadow-2xl overflow-hidden flex items-center justify-center text-slate-200 mx-auto">
                    {profileImageUrl ? (
                      <img 
                        src={profileImageUrl} 
                        alt="Profile" 
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                    ) : null}
                    <div className={`fallback-icon items-center justify-center w-full h-full ${profileImageUrl ? 'hidden' : 'flex'}`}>
                      {userRole === 'CANDIDATE' ? <User size={80} /> : <ShieldCheck size={80} />}
                    </div>
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-10 h-10 bg-green-500 rounded-2xl border-4 border-white flex items-center justify-center shadow-lg">
                    <CheckCircle2 size={16} className="text-white" strokeWidth={3} />
                  </div>
                </div>

                <h2 className="text-3xl font-black text-slate-900 tracking-tight mb-2">{profileData.name}</h2>
                <p className="text-[#D10043] font-black text-xs uppercase tracking-[0.2em] mb-6">{profileData.title}</p>

                <div className="flex items-center justify-center gap-2 mb-8 bg-slate-50 py-2.5 px-4 rounded-2xl border border-slate-100 w-fit mx-auto">
                  <MapPin size={14} className="text-slate-400" />
                  <span className="text-[11px] font-black text-slate-500 uppercase tracking-widest">{profileData.location}</span>
                </div>

                <button
                  onClick={() => navigate(userRole === 'ADMIN' ? '/admin/settings' : userRole === 'HR' ? '/hr/settings' : '/candidate/settings')}
                  className="w-full py-4 bg-slate-900 text-white rounded-[24px] font-black uppercase tracking-widest text-[10px] hover:bg-[#D10043] transition-all shadow-xl active:scale-[0.98] flex items-center justify-center gap-2 mb-4"
                >
                  <Edit3 size={14} /> Edit Profile
                </button>

                <div className="pt-8 mt-8 border-t border-slate-50 space-y-4">
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest">
                    <span>Member Type</span>
                    <span className="text-slate-900">{userRole}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest">
                    <span>Account Status</span>
                    <span className="text-green-500">Verified</span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-widest">
                    <span>Join Date</span>
                    <span className="text-slate-900">{profileData.since}</span>
                  </div>
                </div>
              </div>

              <div className="mt-8 bg-white border border-slate-100 rounded-[40px] p-10 shadow-xl shadow-slate-200/40 animate-in fade-in slide-in-from-bottom-8 duration-700 delay-100">
                <h3 className="text-sm font-black text-slate-900 tracking-widest uppercase mb-8">Contact Information</h3>
                <div className="space-y-6">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-50 rounded-xl flex items-center justify-center text-[#D10043]">
                      <Mail size={18} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Email Address</p>
                      <p className="text-sm font-bold text-slate-900 truncate">{userEmail}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-slate-50 rounded-xl flex items-center justify-center text-[#D10043]">
                      <Globe size={18} />
                    </div>
                    <div>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-0.5">Timezone</p>
                      <p className="text-sm font-bold text-slate-900">GMT+8 (Manila)</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex-grow space-y-10">

              <div className="bg-white border border-slate-100 rounded-[48px] p-12 shadow-xl shadow-slate-200/40 animate-in fade-in slide-in-from-right-8 duration-700">
                <div className="flex items-center gap-3 mb-8">
                  <div className="p-3 bg-pink-50 rounded-2xl">
                    <Zap size={20} className="text-[#D10043]" />
                  </div>
                  <h3 className="text-xl font-black text-slate-900 tracking-tight">
                    {userRole === 'CANDIDATE' ? 'Professional Bio' : 'Enterprise Focus'}
                  </h3>
                </div>
                <p className="text-slate-500 text-lg leading-relaxed font-medium">
                  {profileData.bio}
                </p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                  {[
                    { label: "Expertise", value: "Modern Web", icon: <TrendingUp size={16} /> },
                    { label: "Availability", value: "Full-Time", icon: <Clock size={16} /> },
                    { label: "Languages", value: "EN, PH", icon: <Globe size={16} /> }
                  ].map((item, i) => (
                    <div key={i} className="bg-slate-50 p-6 rounded-3xl border border-slate-100">
                      <div className="text-[#D10043] mb-3">{item.icon}</div>
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{item.label}</p>
                      <p className="text-sm font-black text-slate-900">{item.value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-900 rounded-[48px] p-12 text-white relative overflow-hidden group animate-in fade-in slide-in-from-right-8 duration-700 delay-100">
                <div className="absolute top-0 right-0 w-64 h-64 bg-[#D10043]/10 rounded-full blur-3xl -mr-32 -mt-32 group-hover:scale-150 transition-transform duration-1000" />

                <div className="relative z-10">
                  <div className="flex justify-between items-center mb-10">
                    <h3 className="text-xl font-black tracking-tight">Legacy & Contributions</h3>
                    <Award className="text-[#D10043]" size={32} />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="p-6 bg-white/5 border border-white/10 rounded-3xl hover:bg-white/10 transition-all cursor-pointer group/item">
                      <div className="flex justify-between items-start mb-4">
                        <div className="w-10 h-10 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                          <Briefcase size={20} />
                        </div>
                        <LinkIcon size={16} className="text-white/20 group-hover/item:text-white transition-colors" />
                      </div>
                      <h4 className="font-black text-sm uppercase tracking-widest mb-2">Internal Projects</h4>
                      <p className="text-xs text-white/40 font-bold leading-relaxed">System-wide infrastructure updates and recruitment process automation.</p>
                    </div>
                    <div className="p-6 bg-white/5 border border-white/10 rounded-3xl hover:bg-white/10 transition-all cursor-pointer group/item">
                      <div className="flex justify-between items-start mb-4">
                        <div className="w-10 h-10 bg-[#D10043]/20 rounded-xl flex items-center justify-center text-[#D10043]">
                          <Award size={20} />
                        </div>
                        <LinkIcon size={16} className="text-white/20 group-hover/item:text-white transition-colors" />
                      </div>
                      <h4 className="font-black text-sm uppercase tracking-widest mb-2">Certifications</h4>
                      <p className="text-xs text-white/40 font-bold leading-relaxed">Verified by Mariwasa Enterprise Standards (MES) Level 4.</p>
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
