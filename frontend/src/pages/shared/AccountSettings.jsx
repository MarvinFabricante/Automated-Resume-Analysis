import React, { useState, useEffect } from 'react';
import profileService from '../../services/profileService';
import authService from '../../services/authService';
import { API_BASE_URL } from '../../services/api';
import { Helmet } from 'react-helmet-async';
import {
  User,
  Mail,
  Lock,
  Bell,
  Camera,
  ChevronRight,
  Globe,
  Trash2,
  Check,
  Save,
  Zap,
  Shield,
  ShieldCheck,
  Eye,
  EyeOff,
  Building2,
  Briefcase,
  Info,
  Plus,
  X,
  RefreshCw,
  Laptop,
  KeyRound,
  Sparkles,
  Smartphone
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import { updateProfileImage } from '../../redux/slices/authSlice';
import { useDispatch } from 'react-redux';
import { useLocation } from 'react-router-dom';

const POPULAR_SKILLS = [
  'React', 'JavaScript', 'TypeScript', 'Node.js', 'Python',
  'FastAPI', 'PostgreSQL', 'SQL', 'Docker', 'Git',
  'Tailwind CSS', 'HTML5/CSS3', 'REST APIs', 'UI/UX Design', 'Agile'
];

const getDeviceAndBrowser = () => {
  if (typeof window === 'undefined' || !navigator.userAgent) {
    return { device: 'Desktop Computer', browser: 'Web Browser' };
  }
  const ua = navigator.userAgent;
  let browser = 'Web Browser';
  let device = 'Desktop Device';

  if (ua.includes('Firefox/')) {
    browser = 'Mozilla Firefox';
  } else if (ua.includes('Edg/')) {
    browser = 'Microsoft Edge';
  } else if (ua.includes('Chrome/')) {
    browser = 'Google Chrome';
  } else if (ua.includes('Safari/') && !ua.includes('Chrome/')) {
    browser = 'Apple Safari';
  }

  if (ua.includes('iPhone')) {
    device = 'Apple iPhone';
  } else if (ua.includes('iPad')) {
    device = 'Apple iPad';
  } else if (ua.includes('Android')) {
    device = 'Android Device';
  } else if (ua.includes('Macintosh') || ua.includes('Mac OS')) {
    device = 'Apple Mac';
  } else if (ua.includes('Windows')) {
    device = 'Windows PC';
  } else if (ua.includes('Linux')) {
    device = 'Linux PC';
  }

  return { device, browser };
};

const AccountSettings = () => {
  const dispatch = useDispatch();
  const location = useLocation();

  const [activeTab, setActiveTab] = useState('profile');

  // Password state
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  // Security / Google status state
  const [securityStatus, setSecurityStatus] = useState({
    is_google_linked: false,
    google_email: null,
    has_calendar_sync: false,
    last_active: null
  });
  const [googleLoading, setGoogleLoading] = useState(false);

  const userRole = (localStorage.getItem('role') || 'CANDIDATE').toUpperCase();
  const userId = localStorage.getItem('user_id');
  const userEmail = localStorage.getItem('saved_email') || 'user@system.com';

  const [formData, setFormData] = useState({
    fullname: '',
    email: '',
    phone: '',
    location: '',
    current_job_title: '',
    current_company: '',
    bio: '',
    highest_degree: '',
    university: '',
    experience_years: 0,
    skills: [],
    profile_image_url: '',
    department: '',
    managed_region: '',
    position: '',
    company_name: ''
  });

  const [initialData, setInitialData] = useState(null);
  const [newSkillInput, setNewSkillInput] = useState('');
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  // Read URL query params on mount
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const tabParam = params.get('tab');
    if (tabParam && ['profile', 'security', 'notifications'].includes(tabParam)) {
      setActiveTab(tabParam);
    }
    const googleLinked = params.get('google_linked');
    if (googleLinked === 'success') {
      setStatusMessage({
        type: 'success',
        text: 'Google account has been successfully connected to your profile!'
      });
      setActiveTab('security');
      // Clean up URL parameter
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (googleLinked === 'error' || googleLinked === 'not_found') {
      setStatusMessage({
        type: 'error',
        text: 'Failed to link Google account. Please ensure your account credentials match.'
      });
      setActiveTab('security');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [location.search]);

  // Fetch Profile data
  const fetchProfile = async () => {
    if (!userId) return;
    try {
      const response = await profileService.getProfile(userRole, userId);
      const data = response.data;
      const normalized = {
        fullname: data.fullname || '',
        email: data.email || userEmail || '',
        phone: data.phone || '',
        location: data.location || '',
        current_job_title: data.current_job_title || data.position || '',
        current_company: data.current_company || data.company_name || '',
        bio: data.bio || '',
        highest_degree: data.highest_degree || '',
        university: data.university || '',
        experience_years: data.experience_years !== undefined ? data.experience_years : 0,
        skills: Array.isArray(data.skills) ? data.skills : [],
        profile_image_url: data.profile_image_url || '',
        department: data.department || '',
        managed_region: data.managed_region || '',
        position: data.position || data.current_job_title || '',
        company_name: data.company_name || data.current_company || ''
      };
      setFormData(normalized);
      setInitialData(normalized);
      if (normalized.profile_image_url) {
        setImagePreview(normalized.profile_image_url);
      }
    } catch (err) {
      console.error("Failed to fetch profile:", err);
    }
  };

  // Fetch Security status
  const fetchSecurityStatus = async () => {
    try {
      const res = await authService.getSecurityStatus(userId);
      if (res.data) {
        setSecurityStatus({
          is_google_linked: !!res.data.is_google_linked,
          google_email: res.data.google_email || null,
          has_calendar_sync: !!res.data.has_calendar_sync,
          last_active: res.data.last_active || null
        });
      }
    } catch (err) {
      console.error("Failed to fetch security status:", err);
    }
  };

  useEffect(() => {
    fetchProfile();
    fetchSecurityStatus();
  }, [userRole, userId]);

  useEffect(() => {
    if (formData.profile_image_url && !selectedImage) {
      setImagePreview(formData.profile_image_url);
    }
  }, [formData.profile_image_url, selectedImage]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 2 * 1024 * 1024) {
        alert("Image file size exceeds 2MB limit. Please choose a smaller image.");
        return;
      }
      setSelectedImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleAddSkill = (skillToAdd) => {
    const skill = (skillToAdd || newSkillInput).trim();
    if (!skill) return;
    if (formData.skills.includes(skill)) {
      setNewSkillInput('');
      return;
    }
    setFormData(prev => ({
      ...prev,
      skills: [...prev.skills, skill]
    }));
    setNewSkillInput('');
  };

  const handleRemoveSkill = (skillToRemove) => {
    setFormData(prev => ({
      ...prev,
      skills: prev.skills.filter(s => s !== skillToRemove)
    }));
  };

  const handleReset = () => {
    if (initialData) {
      setFormData({ ...initialData });
      setSelectedImage(null);
      setImagePreview(initialData.profile_image_url || null);
    }
  };

  const handleSave = async () => {
    if (!userId) {
      alert("User ID not found. Please log in again.");
      return;
    }

    if (!formData.fullname.trim()) {
      alert("Full Name is required.");
      return;
    }

    setLoading(true);
    setStatusMessage(null);

    try {
      let currentImageUrl = formData.profile_image_url;

      // 1. If an image is selected, upload it first
      if (selectedImage) {
        const uploadResponse = await profileService.uploadProfileImage(userRole, userId, selectedImage);
        currentImageUrl = uploadResponse.data.image_url;
        setSelectedImage(null);
      }

      // 2. Prepare payload tailored for role
      let updatePayload = {
        fullname: formData.fullname.trim(),
        email: formData.email.trim(),
        phone: formData.phone.trim(),
        location: formData.location.trim(),
        bio: formData.bio.trim(),
        profile_image_url: currentImageUrl
      };

      if (userRole === 'CANDIDATE') {
        updatePayload = {
          ...updatePayload,
          current_job_title: formData.current_job_title.trim(),
          current_company: formData.current_company.trim(),
          highest_degree: formData.highest_degree.trim(),
          university: formData.university.trim(),
          experience_years: parseInt(formData.experience_years, 10) || 0,
          skills: formData.skills
        };
      } else if (userRole === 'HR') {
        updatePayload = {
          ...updatePayload,
          company_name: (formData.company_name || formData.current_company).trim() || 'Mariwasa Siam Ceramics, Inc.',
          department: formData.department.trim(),
          position: (formData.position || formData.current_job_title).trim()
        };
      } else if (userRole === 'ADMIN') {
        updatePayload = {
          ...updatePayload,
          managed_region: formData.managed_region.trim()
        };
      }

      const response = await profileService.updateProfile(userRole, userId, updatePayload);
      const updatedData = response.data;

      // Synchronize state with response
      const refreshed = {
        ...formData,
        ...updatedData,
        current_job_title: updatedData.current_job_title || updatedData.position || formData.current_job_title,
        current_company: updatedData.current_company || updatedData.company_name || formData.current_company,
        position: updatedData.position || formData.position,
        company_name: updatedData.company_name || formData.company_name,
        profile_image_url: updatedData.profile_image_url || currentImageUrl
      };

      setFormData(refreshed);
      setInitialData(refreshed);

      // Update Redux and LocalStorage for global header / sidebar consistency
      if (refreshed.profile_image_url) {
        dispatch(updateProfileImage(refreshed.profile_image_url));
        localStorage.setItem('profile_image_url', refreshed.profile_image_url);
      }
      if (refreshed.fullname) {
        localStorage.setItem('fullname', refreshed.fullname);
      }
      if (refreshed.email) {
        localStorage.setItem('saved_email', refreshed.email);
      }

      setStatusMessage({
        type: 'success',
        text: 'Profile details successfully updated!'
      });
    } catch (err) {
      console.error("Failed to update profile:", err);
      const errDetail = err.response?.data?.detail || "Failed to update profile. Please check the fields and try again.";
      setStatusMessage({
        type: 'error',
        text: errDetail
      });
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({ ...prev, [name]: value }));
  };

  const handleUpdatePassword = async () => {
    if (!passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword) {
      setStatusMessage({
        type: 'error',
        text: "All password fields are required."
      });
      return;
    }
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setStatusMessage({
        type: 'error',
        text: "New password and confirm password do not match."
      });
      return;
    }
    if (passwordData.newPassword.length < 8) {
      setStatusMessage({
        type: 'error',
        text: "New password must be at least 8 characters long."
      });
      return;
    }

    setPasswordLoading(true);
    setStatusMessage(null);

    try {
      await authService.changePassword(passwordData.currentPassword, passwordData.newPassword);
      setStatusMessage({
        type: 'success',
        text: "Password successfully updated! Use your new password on your next login."
      });
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err) {
      console.error("Failed to update password:", err);
      const errorMessage = err.response?.data?.detail || "Failed to update password. Please check your current password.";
      setStatusMessage({
        type: 'error',
        text: errorMessage
      });
    } finally {
      setPasswordLoading(false);
    }
  };

  const handleConnectGoogle = () => {
    const clientOrigin = typeof window !== 'undefined' ? window.location.origin : '';
    const flowRole = userRole.toLowerCase();
    window.location.href = `${API_BASE_URL}/auth/google/login?origin=${encodeURIComponent(clientOrigin)}&flow=link_account&user_id=${userId}&role=${flowRole}`;
  };

  const handleDisconnectGoogle = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to disconnect your Google account? You will need to use your email and password to log in."
    );
    if (!confirmed) return;

    setGoogleLoading(true);
    setStatusMessage(null);
    try {
      await authService.disconnectGoogle(userId);
      setSecurityStatus(prev => ({
        ...prev,
        is_google_linked: false,
        google_email: null,
        has_calendar_sync: false
      }));
      setStatusMessage({
        type: 'success',
        text: 'Google account disconnected successfully.'
      });
    } catch (err) {
      console.error("Failed to disconnect Google account:", err);
      setStatusMessage({
        type: 'error',
        text: 'Failed to disconnect Google account. Please try again.'
      });
    } finally {
      setGoogleLoading(false);
    }
  };

  const clientSession = getDeviceAndBrowser();

  const TABS = [
    { id: 'profile', label: 'Identity & Profile', icon: <User size={18} /> },
    { id: 'security', label: 'Security & Credentials', icon: <Lock size={18} /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell size={18} /> },
  ];

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - {userRole.charAt(0) + userRole.slice(1).toLowerCase()} Settings</title>
      </Helmet>

      <Header />

      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-[1400px] mx-auto px-3.5 sm:px-6 md:px-10 py-5 sm:py-6 md:py-8 w-full flex-grow">

          {/* Page Header */}
          <div className="mb-6 sm:mb-10 animate-in fade-in slide-in-from-top-4 duration-700">
            <div className="flex items-center gap-2 bg-[#D10043]/5 text-[#D10043] px-2.5 sm:px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-[0.2em] mb-2 sm:mb-3 border border-[#D10043]/10 w-fit">
              <Zap size={12} className="animate-pulse" />
              {userRole} Account Center
            </div>
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-black tracking-tight text-slate-900 leading-tight">
              {userRole === 'HR' ? 'HR' : userRole === 'ADMIN' ? 'Admin' : 'Candidate'} <span className="text-[#D10043]">Settings</span>
            </h2>
            <p className="text-slate-400 font-bold text-xs sm:text-sm mt-1.5 sm:mt-2 uppercase tracking-wider sm:tracking-widest">
              Manage your personal credentials, identity profile, and security preferences.
            </p>
          </div>

          {/* Status Message Banner */}
          {statusMessage && (
            <div
              className={`mb-6 sm:mb-8 p-3.5 sm:p-4 rounded-xl sm:rounded-2xl flex items-center justify-between gap-3 text-xs sm:text-sm font-semibold transition-all shadow-sm ${
                statusMessage.type === 'success'
                  ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                  : 'bg-red-50 text-red-800 border border-red-200'
              }`}
            >
              <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
                {statusMessage.type === 'success' ? (
                  <Check size={18} className="text-emerald-600 shrink-0" />
                ) : (
                  <Info size={18} className="text-red-600 shrink-0" />
                )}
                <span className="truncate">{statusMessage.text}</span>
              </div>
              <button
                onClick={() => setStatusMessage(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg transition-colors shrink-0"
              >
                <X size={16} />
              </button>
            </div>
          )}

          {/* Mobile Profile Summary & Horizontal Scrollable Tabs (Visible on < lg screens) */}
          <div className="lg:hidden w-full mb-6 space-y-3">
            <div className="bg-white border border-slate-100 rounded-2xl sm:rounded-3xl p-3.5 sm:p-4 shadow-sm flex items-center justify-between">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl bg-slate-50 border border-slate-200 overflow-hidden flex items-center justify-center shrink-0">
                  {imagePreview ? (
                    <img
                      src={imagePreview}
                      alt="Profile"
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        if (e.target.nextSibling) e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div className={`items-center justify-center w-full h-full ${imagePreview ? 'hidden' : 'flex'}`}>
                    {userRole === 'CANDIDATE' ? <User size={20} className="text-slate-400" /> : <Shield size={20} className="text-slate-400" />}
                  </div>
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs sm:text-sm font-black text-slate-900 truncate">
                    {formData.fullname || 'Your Name'}
                  </h3>
                  <p className="text-[10px] font-black text-[#D10043] uppercase tracking-wider">
                    {userRole} • Active
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider shrink-0 border border-emerald-200">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>Online</span>
              </div>
            </div>

            {/* Horizontal Tabs */}
            <div className="flex overflow-x-auto no-scrollbar gap-2 pb-1">
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setStatusMessage(null);
                  }}
                  className={`flex items-center gap-2 px-3.5 sm:px-4 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider shrink-0 transition-all ${
                    activeTab === tab.id
                      ? 'bg-slate-900 text-white shadow-md'
                      : 'bg-white text-slate-600 border border-slate-100 hover:bg-slate-50'
                  }`}
                >
                  <div className={activeTab === tab.id ? 'text-[#D10043]' : 'text-slate-400'}>
                    {tab.icon}
                  </div>
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col lg:flex-row gap-6 lg:gap-10">

            {/* Desktop Left Sidebar Navigation Card (Visible on lg+ screens) */}
            <div className="hidden lg:block w-80 shrink-0 animate-in fade-in slide-in-from-left-6 duration-700">
              <div className="bg-white border border-slate-100 rounded-[40px] p-6 shadow-xl shadow-slate-200/40 sticky top-32">
                <div className="flex flex-col items-center mb-8 pb-8 border-b border-slate-50">
                  <div className="w-24 h-24 rounded-[32px] bg-slate-50 border-4 border-white shadow-xl overflow-hidden mb-4 flex items-center justify-center text-slate-200 relative group">
                    {imagePreview ? (
                      <img
                        src={imagePreview}
                        alt="Profile"
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          if (e.target.nextSibling) e.target.nextSibling.style.display = 'flex';
                        }}
                      />
                    ) : null}
                    <div className={`items-center justify-center w-full h-full ${imagePreview ? 'hidden' : 'flex'}`}>
                      {userRole === 'CANDIDATE' ? <User size={40} /> : <Shield size={40} />}
                    </div>
                  </div>
                  <h3 className="text-sm font-black text-slate-900 truncate w-full text-center px-4">
                    {formData.fullname || 'Your Name'}
                  </h3>
                  <p className="text-[10px] font-black text-[#D10043] uppercase tracking-[0.2em] mt-1">
                    {userRole}
                  </p>
                </div>

                <div className="space-y-2">
                  {TABS.map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => {
                        setActiveTab(tab.id);
                        setStatusMessage(null);
                      }}
                      className={`w-full flex items-center gap-4 px-6 py-4 rounded-3xl transition-all duration-300 group ${
                        activeTab === tab.id
                          ? 'bg-slate-900 text-white shadow-xl shadow-slate-900/20'
                          : 'bg-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                      }`}
                    >
                      <div className={`${activeTab === tab.id ? 'text-[#D10043]' : 'text-slate-300 group-hover:text-slate-500'} transition-colors`}>
                        {tab.icon}
                      </div>
                      <span className="text-xs font-black uppercase tracking-widest">{tab.label}</span>
                      {activeTab === tab.id && <ChevronRight size={14} className="ml-auto text-[#D10043]" />}
                    </button>
                  ))}
                </div>

                <div className="mt-10 pt-10 border-t border-slate-50 px-2 text-center">
                  <p className="text-[10px] font-black text-slate-300 uppercase tracking-widest">Signed in as</p>
                  <p className="text-[11px] font-black text-slate-900 truncate mt-1">
                    {formData.email || userEmail}
                  </p>
                  <div className="mt-4 flex items-center justify-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">
                      Active Session
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Content Area */}
            <div className="flex-grow min-w-0 animate-in fade-in slide-in-from-right-6 duration-700">

              {/* TAB 1: IDENTITY & PROFILE */}
              {activeTab === 'profile' && (
                <div className="space-y-10">
                  <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] md:rounded-[48px] p-5 sm:p-8 md:p-10 shadow-xl shadow-slate-200/40">
                    <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight mb-6 sm:mb-8 flex items-center gap-3">
                      {userRole === 'CANDIDATE' ? <User size={22} className="text-[#D10043]" /> : <Building2 size={22} className="text-[#D10043]" />}
                      {userRole === 'CANDIDATE' ? 'Candidate Profile & Details' : userRole === 'HR' ? 'HR Staff Identity' : 'Administrator Identity'}
                    </h3>

                    <div className="space-y-6 sm:space-y-10">
                      {/* Avatar Upload */}
                      <div className="flex flex-col sm:flex-row items-center gap-5 sm:gap-8 pb-6 sm:pb-10 border-b border-slate-50 text-center sm:text-left">
                        <div className="relative group shrink-0">
                          <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-3xl sm:rounded-[40px] bg-slate-50 border-4 border-white shadow-xl shadow-slate-200 overflow-hidden flex items-center justify-center text-slate-200 mx-auto">
                            {imagePreview ? (
                              <img
                                src={imagePreview}
                                alt="Profile Preview"
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                  if (e.target.nextSibling) e.target.nextSibling.style.display = 'flex';
                                }}
                              />
                            ) : null}
                            <div className={`items-center justify-center w-full h-full ${imagePreview ? 'hidden' : 'flex'}`}>
                              <User size={40} className="sm:w-12 sm:h-12 text-slate-200" />
                            </div>
                          </div>
                          <label className="absolute -bottom-1 -right-1 sm:-bottom-2 sm:-right-2 p-2.5 sm:p-3 bg-slate-900 text-white rounded-xl sm:rounded-2xl shadow-xl hover:bg-[#D10043] transition-colors group-hover:scale-110 duration-300 cursor-pointer">
                            <Camera size={16} className="sm:w-[18px] sm:h-[18px]" />
                            <input type="file" className="hidden" accept="image/*" onChange={handleImageChange} />
                          </label>
                        </div>
                        <div className="text-center sm:text-left min-w-0">
                          <h4 className="text-base sm:text-lg font-black text-slate-900 mb-1">
                            {userRole === 'CANDIDATE' ? 'Profile Picture' : 'Enterprise Avatar'}
                          </h4>
                          <p className="text-[11px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider sm:tracking-widest leading-relaxed mb-3 sm:mb-4">
                            JPG, PNG or GIF. Max file size: 2MB.<br className="hidden sm:inline" />
                            {userRole === 'CANDIDATE' ? ' Visible to hiring managers and recruiters.' : ' Displayed across internal screening notifications.'}
                          </p>
                          {selectedImage && (
                            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-pink-50 border border-pink-200 rounded-lg text-[10px] text-[#D10043] font-black uppercase tracking-wider animate-pulse">
                              <Sparkles size={12} /> New photo selected. Save Changes to apply.
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Profile Inputs Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-8">
                        {/* Full Name */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            Full Name <span className="text-[#D10043]">*</span>
                          </label>
                          <input
                            type="text"
                            name="fullname"
                            value={formData.fullname}
                            onChange={handleInputChange}
                            placeholder="Enter your full name"
                            className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          />
                        </div>

                        {/* Email Address */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            Email Address <span className="text-[#D10043]">*</span>
                          </label>
                          <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleInputChange}
                            placeholder="user@example.com"
                            className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          />
                        </div>

                        {/* Phone Number */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            Phone Number
                          </label>
                          <input
                            type="tel"
                            name="phone"
                            value={formData.phone}
                            onChange={handleInputChange}
                            placeholder="+63 912 345 6789"
                            className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          />
                        </div>

                        {/* Location */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            Location / Address
                          </label>
                          <input
                            type="text"
                            name="location"
                            value={formData.location}
                            onChange={handleInputChange}
                            placeholder="e.g. Batangas, Philippines"
                            className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          />
                        </div>

                        {/* ROLE-SPECIFIC FIELDS: CANDIDATE */}
                        {userRole === 'CANDIDATE' && (
                          <>
                            <div className="space-y-2 sm:space-y-3">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Professional Title
                              </label>
                              <input
                                type="text"
                                name="current_job_title"
                                value={formData.current_job_title}
                                onChange={handleInputChange}
                                placeholder="e.g. Senior Frontend Developer"
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            <div className="space-y-2 sm:space-y-3">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Current / Previous Company
                              </label>
                              <input
                                type="text"
                                name="current_company"
                                value={formData.current_company}
                                onChange={handleInputChange}
                                placeholder="e.g. Tech Solutions Inc."
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            <div className="space-y-2 sm:space-y-3">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Years of Experience
                              </label>
                              <input
                                type="number"
                                name="experience_years"
                                min="0"
                                max="50"
                                value={formData.experience_years}
                                onChange={handleInputChange}
                                placeholder="0"
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            <div className="space-y-2 sm:space-y-3">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Highest Educational Degree
                              </label>
                              <input
                                type="text"
                                name="highest_degree"
                                value={formData.highest_degree}
                                onChange={handleInputChange}
                                placeholder="e.g. Bachelor of Science in Computer Science"
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            <div className="space-y-2 sm:space-y-3 md:col-span-2">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                University / School
                              </label>
                              <input
                                type="text"
                                name="university"
                                value={formData.university}
                                onChange={handleInputChange}
                                placeholder="e.g. University of the Philippines"
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            {/* Skills Interactive Manager */}
                            <div className="col-span-full space-y-3 pt-2">
                              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
                                <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1 flex items-center gap-2">
                                  <Sparkles size={14} className="text-[#D10043]" />
                                  Core Skills & Technologies ({formData.skills.length})
                                </label>
                                <span className="text-[10px] font-bold text-slate-400">
                                  Press Enter or click Add to insert skill
                                </span>
                              </div>

                              {/* Skill input */}
                              <div className="flex flex-col sm:flex-row gap-2">
                                <input
                                  type="text"
                                  value={newSkillInput}
                                  onChange={(e) => setNewSkillInput(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      e.preventDefault();
                                      handleAddSkill();
                                    }
                                  }}
                                  placeholder="Type a skill (e.g. Python, React, Communication)..."
                                  className="flex-grow px-4 sm:px-6 py-3 sm:py-3.5 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[18px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                                />
                                <button
                                  type="button"
                                  onClick={() => handleAddSkill()}
                                  className="px-5 sm:px-6 py-3 sm:py-3.5 bg-slate-900 hover:bg-[#D10043] text-white rounded-xl sm:rounded-[18px] text-xs font-black uppercase tracking-wider transition-all flex items-center justify-center gap-2 shrink-0 shadow-md min-h-[44px]"
                                >
                                  <Plus size={16} /> Add Skill
                                </button>
                              </div>

                              {/* Current Skills list */}
                              <div className="flex flex-wrap gap-2 min-h-[44px] p-3 sm:p-4 bg-slate-50/60 rounded-xl sm:rounded-[22px] border border-slate-100">
                                {formData.skills.length === 0 ? (
                                  <p className="text-xs text-slate-400 italic py-1">
                                    No skills added yet. Add your key skills above to improve job matching accuracy.
                                  </p>
                                ) : (
                                  formData.skills.map((skill, index) => (
                                    <span
                                      key={index}
                                      className="inline-flex items-center gap-2 px-3 py-1 sm:px-3.5 sm:py-1.5 bg-white border border-slate-200/80 rounded-full text-xs font-bold text-slate-800 shadow-sm group hover:border-[#D10043]/40 transition-colors"
                                    >
                                      <span>{skill}</span>
                                      <button
                                        type="button"
                                        onClick={() => handleRemoveSkill(skill)}
                                        className="text-slate-300 hover:text-[#D10043] transition-colors p-0.5 rounded-full"
                                        title={`Remove ${skill}`}
                                      >
                                        <X size={14} />
                                      </button>
                                    </span>
                                  ))
                                )}
                              </div>

                              {/* Popular suggestions */}
                              <div className="pt-2">
                                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">
                                  Quick Suggestions:
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                  {POPULAR_SKILLS.filter(s => !formData.skills.includes(s)).slice(0, 8).map((s) => (
                                    <button
                                      key={s}
                                      type="button"
                                      onClick={() => handleAddSkill(s)}
                                      className="text-[10px] sm:text-[11px] font-bold px-2.5 sm:px-3 py-1 bg-white hover:bg-[#D10043] hover:text-white text-slate-600 rounded-lg border border-slate-200 transition-all"
                                    >
                                      + {s}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </>
                        )}

                        {/* ROLE-SPECIFIC FIELDS: HR */}
                        {userRole === 'HR' && (
                          <>
                            <div className="space-y-2 sm:space-y-3">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Position / Title
                              </label>
                              <input
                                type="text"
                                name="position"
                                value={formData.position}
                                onChange={handleInputChange}
                                placeholder="e.g. Talent Acquisition Specialist"
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            <div className="space-y-2 sm:space-y-3">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Company Name
                              </label>
                              <input
                                type="text"
                                name="company_name"
                                value={formData.company_name}
                                onChange={handleInputChange}
                                placeholder="Mariwasa Siam Ceramics, Inc."
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>

                            <div className="space-y-2 sm:space-y-3 md:col-span-2">
                              <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                                Department / Division
                              </label>
                              <input
                                type="text"
                                name="department"
                                value={formData.department}
                                onChange={handleInputChange}
                                placeholder="e.g. Human Resources & Talent Management"
                                className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                              />
                            </div>
                          </>
                        )}

                        {/* ROLE-SPECIFIC FIELDS: ADMIN */}
                        {userRole === 'ADMIN' && (
                          <div className="space-y-2 sm:space-y-3 md:col-span-2">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                              Managed Region / Headquarters
                            </label>
                            <input
                              type="text"
                              name="managed_region"
                              value={formData.managed_region}
                              onChange={handleInputChange}
                              placeholder="e.g. Main Headquarters - Sto. Tomas, Batangas"
                              className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                            />
                          </div>
                        )}

                        {/* Bio / Operational Summary */}
                        <div className="col-span-full space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            {userRole === 'CANDIDATE' ? 'Professional Bio / Summary' : userRole === 'HR' ? 'Operational Focus' : 'System Administration Summary'}
                          </label>
                          <textarea
                            rows="4"
                            name="bio"
                            value={formData.bio}
                            onChange={handleInputChange}
                            placeholder={
                              userRole === 'CANDIDATE'
                                ? "Describe your background, expertise, and what roles you are seeking..."
                                : "Describe your role, responsibilities, and team oversight..."
                            }
                            className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[24px] text-xs sm:text-sm font-medium text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all resize-none"
                          />
                        </div>
                      </div>

                      {/* Action Buttons */}
                      <div className="flex flex-col-reverse sm:flex-row justify-end gap-2.5 sm:gap-4 pt-4 border-t border-slate-50">
                        <button
                          type="button"
                          onClick={handleReset}
                          className="w-full sm:w-auto px-6 sm:px-8 py-3.5 sm:py-4 bg-slate-50 text-slate-500 rounded-xl sm:rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all text-center min-h-[44px]"
                        >
                          Reset
                        </button>
                        <button
                          type="button"
                          onClick={handleSave}
                          disabled={loading}
                          className="w-full sm:w-auto px-8 sm:px-10 py-3.5 sm:py-4 bg-[#D10043] text-white rounded-xl sm:rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-900 transition-all shadow-xl shadow-pink-100 flex items-center justify-center gap-3 disabled:opacity-50 text-center min-h-[44px]"
                        >
                          <Save size={16} /> {loading ? 'Saving Changes...' : 'Save Changes'}
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: SECURITY & CREDENTIALS */}
              {activeTab === 'security' && (
                <div className="space-y-10">

                  {/* GOOGLE ACCOUNT INTEGRATION CARD */}
                  <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] md:rounded-[48px] p-5 sm:p-8 md:p-10 shadow-xl shadow-slate-200/40">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 sm:mb-8">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-slate-50 flex items-center justify-center border border-slate-100 shadow-sm shrink-0">
                          {/* Official Google 'G' icon */}
                          <svg className="w-5 h-5 sm:w-6 sm:h-6" viewBox="0 0 24 24">
                            <path
                              fill="#4285F4"
                              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            />
                            <path
                              fill="#34A853"
                              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            />
                            <path
                              fill="#FBBC05"
                              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                            />
                            <path
                              fill="#EA4335"
                              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                            />
                          </svg>
                        </div>
                        <div>
                          <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight leading-tight">
                            Google Account Integration
                          </h3>
                          <p className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider sm:tracking-widest mt-0.5">
                            Single Sign-On & Cloud Authentication
                          </p>
                        </div>
                      </div>

                      <span
                        className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 sm:px-3.5 sm:py-1.5 rounded-full border w-fit ${
                          securityStatus.is_google_linked
                            ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                            : 'bg-slate-50 text-slate-500 border-slate-200'
                        }`}
                      >
                        {securityStatus.is_google_linked ? '● Google Connected' : '○ Not Linked'}
                      </span>
                    </div>

                    <div className="p-4 sm:p-6 md:p-8 bg-slate-50/70 rounded-2xl sm:rounded-[32px] border border-slate-100 mb-6">
                      {securityStatus.is_google_linked ? (
                        <div className="space-y-4">
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
                            <div>
                              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">
                                Connected Google Account
                              </p>
                              <p className="text-sm sm:text-base font-black text-slate-900 mt-0.5 sm:mt-1 truncate">
                                {securityStatus.google_email || formData.email || userEmail}
                              </p>
                            </div>
                            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-100/60 text-emerald-800 rounded-xl text-xs font-bold w-fit">
                              <Check size={16} className="text-emerald-600" />
                              SSO Login Active
                            </div>
                          </div>

                          <div className="pt-3 sm:pt-4 border-t border-slate-200/60 text-xs text-slate-500 font-medium space-y-1">
                            <p>• You can log in instantly with 1-click using "Sign in with Google".</p>
                            {userRole === 'HR' && (
                              <p>• Google Calendar scheduling integration enabled for automated candidate interviews.</p>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <p className="text-xs sm:text-sm font-bold text-slate-800">
                            Connect your Google Account for fast, password-free Single Sign-On.
                          </p>
                          <p className="text-xs text-slate-500 font-medium">
                            Linking your Google account enables 1-click authentication and synchronizes your profile avatar across the platform.
                            {userRole === 'HR' && ' For HR staff, connecting your Google account enables automatic Google Calendar event creation for candidate interviews.'}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Google Action Buttons */}
                    <div className="flex flex-col sm:flex-row flex-wrap items-stretch sm:items-center justify-end gap-2.5 sm:gap-4">
                      {securityStatus.is_google_linked ? (
                        <>
                          <button
                            type="button"
                            onClick={handleConnectGoogle}
                            className="w-full sm:w-auto px-5 sm:px-6 py-3 sm:py-3.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl sm:rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 min-h-[44px]"
                          >
                            <RefreshCw size={14} /> Reconnect / Sync
                          </button>
                          <button
                            type="button"
                            onClick={handleDisconnectGoogle}
                            disabled={googleLoading}
                            className="w-full sm:w-auto px-5 sm:px-6 py-3 sm:py-3.5 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl sm:rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center gap-2 disabled:opacity-50 min-h-[44px]"
                          >
                            <Trash2 size={14} /> {googleLoading ? 'Disconnecting...' : 'Disconnect Google'}
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={handleConnectGoogle}
                          className="w-full sm:w-auto px-6 sm:px-8 py-3.5 sm:py-4 bg-slate-900 hover:bg-[#D10043] text-white rounded-xl sm:rounded-2xl text-xs font-black uppercase tracking-wider transition-all shadow-xl shadow-slate-900/20 flex items-center justify-center gap-3 min-h-[44px]"
                        >
                          <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
                            <path
                              fill="#4285F4"
                              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                            />
                            <path
                              fill="#34A853"
                              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                            />
                            <path
                              fill="#FBBC05"
                              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                            />
                            <path
                              fill="#EA4335"
                              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                            />
                          </svg>
                          Connect Google Account
                        </button>
                      )}
                    </div>
                  </div>

                  {/* PASSWORD MANAGEMENT CARD */}
                  <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] md:rounded-[48px] p-5 sm:p-8 md:p-10 shadow-xl shadow-slate-200/40">
                    <div className="flex items-center gap-3 mb-6 sm:mb-8">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-pink-50 flex items-center justify-center text-[#D10043] border border-pink-100 shadow-sm shrink-0">
                        <KeyRound size={20} className="sm:w-[22px] sm:h-[22px]" />
                      </div>
                      <div>
                        <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight leading-tight">
                          Password & Credentials
                        </h3>
                        <p className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider sm:tracking-widest mt-0.5">
                          Change your secret authentication key
                        </p>
                      </div>
                    </div>

                    <div className="space-y-6 sm:space-y-8">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-8">
                        {/* Current Password */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            Current Password <span className="text-[#D10043]">*</span>
                          </label>
                          <div className="relative group">
                            <input
                              type={showCurrentPassword ? 'text' : 'password'}
                              name="currentPassword"
                              value={passwordData.currentPassword}
                              onChange={handlePasswordChange}
                              className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all pr-12 sm:pr-14"
                              placeholder="••••••••••••"
                            />
                            <button
                              type="button"
                              onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                              className="absolute right-4 sm:right-5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors p-1"
                            >
                              {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                          </div>
                        </div>

                        {/* Password Note */}
                        <div className="space-y-2 sm:space-y-3 md:pt-6">
                          <div className="p-3.5 sm:p-4 bg-slate-50 rounded-xl sm:rounded-2xl border border-slate-100 text-xs text-slate-500 font-medium">
                            <p className="font-bold text-slate-700 mb-1">Password Requirements:</p>
                            <p>• At least 8 characters long</p>
                            <p className="mt-1 text-[11px] text-slate-400">
                              * If you initially registered via Google, your starting password is <code>password</code>.
                            </p>
                          </div>
                        </div>

                        {/* New Password */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            New Password <span className="text-[#D10043]">*</span>
                          </label>
                          <div className="relative group">
                            <input
                              type={showNewPassword ? 'text' : 'password'}
                              name="newPassword"
                              value={passwordData.newPassword}
                              onChange={handlePasswordChange}
                              className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all pr-12 sm:pr-14"
                              placeholder="At least 8 characters"
                            />
                            <button
                              type="button"
                              onClick={() => setShowNewPassword(!showNewPassword)}
                              className="absolute right-4 sm:right-5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors p-1"
                            >
                              {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                          </div>
                        </div>

                        {/* Confirm New Password */}
                        <div className="space-y-2 sm:space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">
                            Confirm New Password <span className="text-[#D10043]">*</span>
                          </label>
                          <div className="relative group">
                            <input
                              type={showConfirmPassword ? 'text' : 'password'}
                              name="confirmPassword"
                              value={passwordData.confirmPassword}
                              onChange={handlePasswordChange}
                              className="w-full px-4 sm:px-6 py-3 sm:py-4 bg-slate-50 border border-slate-100 rounded-xl sm:rounded-[20px] text-xs sm:text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all pr-12 sm:pr-14"
                              placeholder="Confirm new password"
                            />
                            <button
                              type="button"
                              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                              className="absolute right-4 sm:right-5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-700 transition-colors p-1"
                            >
                              {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-end pt-4 border-t border-slate-50">
                        <button
                          type="button"
                          onClick={handleUpdatePassword}
                          disabled={passwordLoading}
                          className="w-full sm:w-auto px-8 sm:px-10 py-3.5 sm:py-4 bg-slate-900 text-white rounded-xl sm:rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-[#D10043] transition-all shadow-xl active:scale-[0.98] flex items-center justify-center gap-3 disabled:opacity-50 min-h-[44px]"
                        >
                          <ShieldCheck size={16} /> {passwordLoading ? 'Updating Password...' : 'Update Password'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* ACTIVE SESSION & DEVICE CARD (Real Device Information) */}
                  <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] md:rounded-[48px] p-5 sm:p-8 md:p-10 shadow-xl shadow-slate-200/40">
                    <div className="flex items-center gap-3 mb-6 sm:mb-8">
                      <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl bg-emerald-50 flex items-center justify-center text-emerald-600 border border-emerald-100 shadow-sm shrink-0">
                        <Laptop size={20} className="sm:w-[22px] sm:h-[22px]" />
                      </div>
                      <div>
                        <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight leading-tight">
                          Active Session & Device
                        </h3>
                        <p className="text-[10px] sm:text-xs text-slate-400 font-bold uppercase tracking-wider sm:tracking-widest mt-0.5">
                          Current verified browser environment
                        </p>
                      </div>
                    </div>

                    <div className="p-4 sm:p-6 md:p-8 rounded-2xl sm:rounded-[32px] border border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 sm:gap-6">
                      <div className="flex items-center gap-3.5 sm:gap-5 min-w-0">
                        <div className="w-11 h-11 sm:w-14 sm:h-14 bg-white rounded-xl sm:rounded-2xl flex items-center justify-center text-slate-600 shadow-sm border border-slate-100 shrink-0">
                          <Laptop size={22} className="sm:w-[26px] sm:h-[26px]" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                            <h4 className="text-sm sm:text-base font-black text-slate-900 truncate">
                              {clientSession.device}
                            </h4>
                            <span className="inline-flex items-center gap-1.5 text-[9px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-100/70 text-emerald-800 border border-emerald-200">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Active Now
                            </span>
                          </div>
                          <p className="text-xs text-slate-500 font-bold mt-1 truncate">
                            {clientSession.browser} • Authenticated as {formData.email || userEmail}
                          </p>
                        </div>
                      </div>

                      <div className="text-left sm:text-right shrink-0">
                        <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">
                          Session Type
                        </p>
                        <p className="text-xs font-black text-slate-700 mt-0.5">
                          Bearer JWT Verified
                        </p>
                      </div>
                    </div>
                  </div>

                </div>
              )}

              {/* TAB 3: NOTIFICATIONS */}
              {activeTab === 'notifications' && (
                <div className="space-y-6 sm:space-y-10">
                  <div className="bg-white border border-slate-100 rounded-3xl sm:rounded-[40px] md:rounded-[48px] p-5 sm:p-8 md:p-10 shadow-xl shadow-slate-200/40">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                      <h3 className="text-lg sm:text-xl font-black text-slate-900 tracking-tight flex items-center gap-3">
                        <Bell size={22} className="text-[#D10043]" />
                        System Notification Preferences
                      </h3>
                      <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-[10px] font-black uppercase tracking-widest w-fit">
                        <Info size={12} className="text-slate-500" />
                        Managed by System
                      </div>
                    </div>

                    <div className="p-3.5 sm:p-4 mb-6 sm:mb-8 rounded-xl sm:rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center gap-3 text-slate-700">
                      <Info size={18} className="text-slate-500 shrink-0" />
                      <p className="text-xs font-semibold leading-relaxed">
                        System notifications and alerts are delivered directly to your application dashboard header and associated email address.
                      </p>
                    </div>

                    <div className="space-y-3 sm:space-y-4">
                      {[
                        {
                          title: userRole === 'CANDIDATE' ? "Application Progress & Status" : "Applicant Screening Alerts",
                          desc: userRole === 'CANDIDATE'
                            ? "Get notified when recruiters review or update your submitted job applications."
                            : "Instant notifications when new candidates apply or complete screening.",
                          active: true
                        },
                        {
                          title: "Interview Schedules & Calendars",
                          desc: "Real-time alerts for scheduled interviews and calendar meeting bookings.",
                          active: true
                        },
                        {
                          title: "System Alerts & Security Notices",
                          desc: "Security notifications when password changes or logins from new sessions occur.",
                          active: true
                        }
                      ].map((item, i) => (
                        <div
                          key={i}
                          className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 sm:gap-6 p-4 sm:p-6 bg-slate-50/70 hover:bg-slate-50 rounded-2xl sm:rounded-[28px] transition-all border border-slate-100"
                        >
                          <div>
                            <h4 className="text-xs sm:text-sm font-black text-slate-900 leading-none">
                              {item.title}
                            </h4>
                            <p className="text-xs text-slate-500 font-medium mt-1.5 leading-relaxed">
                              {item.desc}
                            </p>
                          </div>
                          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-[10px] font-black uppercase tracking-widest shrink-0">
                            <Check size={12} /> Enabled
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AccountSettings;
