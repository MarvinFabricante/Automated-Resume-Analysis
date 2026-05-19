import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Helmet } from 'react-helmet-async';
import {
  User,
  Mail,
  Lock,
  Bell,
  ShieldCheck,
  Camera,
  ChevronRight,
  Globe,
  MessageSquare,
  Trash2,
  Check,
  Save,
  Zap,
  Smartphone,
  Shield,
  Eye,
  EyeOff,
  Building2,
  Users,
  TrendingUp,
  Briefcase
} from 'lucide-react';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';

import { updateProfileImage } from '../../redux/slices/authSlice';
import { useDispatch } from 'react-redux';

const BRAND_RED = "#D10043";

const AccountSettings = () => {
  const dispatch = useDispatch();
  const [activeTab, setActiveTab] = useState('profile');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  const userRole = localStorage.getItem('role') || 'Guest';
  const userId = localStorage.getItem('user_id');
  const userEmail = localStorage.getItem('saved_email') || 'user@system.com';

  const [formData, setFormData] = useState({
    fullname: '',
    phone: '',
    location: '',
    current_job_title: '',
    current_company: '',
    bio: '',
    highest_degree: '',
    university: '',
    skills: [],
    profile_image_url: '',
    department: '',
    managed_region: '',
    position: ''
  });

  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      if (!userId) return;
      setFetching(true);
      try {
        let endpoint = `http://localhost:8000/candidate/profile/${userId}`;
        if (userRole === 'HR') endpoint = `http://localhost:8000/hr/profile/${userId}`;
        if (userRole === 'ADMIN') endpoint = `http://localhost:8000/admins/profile/${userId}`;

        const response = await axios.get(endpoint);
        const data = response.data;
        setFormData({
          fullname: data.fullname || '',
          email: data.email || '',
          phone: data.phone || '',
          location: data.location || '',
          current_job_title: data.current_job_title || data.position || '',
          current_company: data.current_company || data.company_name || '',
          bio: data.bio || '',
          highest_degree: data.highest_degree || '',
          university: data.university || '',
          skills: data.skills || [],
          profile_image_url: data.profile_image_url || '',
          department: data.department || '',
          managed_region: data.managed_region || '',
          position: data.position || ''
        });
      } catch (err) {
        console.error("Failed to fetch profile:", err);
      } finally {
        setFetching(false);
      }
    };
    fetchProfile();
  }, [userRole, userId]);

  useEffect(() => {
    if (formData.profile_image_url && !selectedImage) {
      setImagePreview(formData.profile_image_url);
    }
  }, [formData.profile_image_url, selectedImage]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };



  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    if (!userId) {
      alert("User ID not found. Please log in again.");
      return;
    }
    setLoading(true);
    try {
      let currentImageUrl = formData.profile_image_url;

      // 1. If an image is selected but not uploaded, upload it first
      if (selectedImage) {
        const formDataImage = new FormData();
        formDataImage.append('file', selectedImage);
        let uploadEndpoint = `http://localhost:8000/candidate/upload-profile-image/${userId}`;
        if (userRole === 'HR') uploadEndpoint = `http://localhost:8000/hr/upload-profile-image/${userId}`;
        if (userRole === 'ADMIN') uploadEndpoint = `http://localhost:8000/admins/upload-profile-image/${userId}`;

        const uploadResponse = await axios.post(uploadEndpoint, formDataImage);
        currentImageUrl = uploadResponse.data.image_url;
        setSelectedImage(null); // Clear selected image after successful upload
      }

      // 2. Update the rest of the profile
      let endpoint = `http://localhost:8000/candidate/profile/${userId}`;
      if (userRole === 'HR') endpoint = `http://localhost:8000/hr/profile/${userId}`;
      if (userRole === 'ADMIN') endpoint = `http://localhost:8000/admins/profile/${userId}`;

      const updateData = { ...formData, profile_image_url: currentImageUrl };
      if (userRole === 'HR') {
        updateData.company_name = formData.current_company;
        updateData.position = formData.current_job_title;
      }

      const response = await axios.put(endpoint, updateData);
      const updatedData = response.data;
      
      // Update local state with fresh data from server
      setFormData(prev => ({
        ...prev,
        ...updatedData,
        current_job_title: updatedData.current_job_title || updatedData.position || '',
        current_company: updatedData.current_company || updatedData.company_name || ''
      }));

      // Update Redux and LocalStorage for global consistency
      if (updatedData.profile_image_url) {
        dispatch(updateProfileImage(updatedData.profile_image_url));
        localStorage.setItem('profile_image_url', updatedData.profile_image_url);
      }
      
      alert("Profile updated successfully!");
    } catch (err) {
      console.error("Failed to update profile:", err);
      alert("Failed to update profile. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const TABS = [
    { id: 'profile', label: 'Identity & Profile', icon: <User size={18} /> },
    { id: 'security', label: 'Security', icon: <Lock size={18} /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell size={18} /> },
  ];

  if (userRole === 'CANDIDATE') {
    TABS.push({ id: 'applications', label: 'Applications', icon: <ShieldCheck size={18} /> });
  } else if (userRole === 'HR' || userRole === 'ADMIN') {
    TABS.push({ id: 'system', label: 'System Access', icon: <Shield size={18} /> });
  }

  return (
    <div className="bg-[#F8FAFC] text-slate-900 antialiased min-h-screen font-['Inter',_sans-serif] flex flex-col">
      <Helmet>
        <title>Mariwasa - {userRole.charAt(0) + userRole.slice(1).toLowerCase()} Settings</title>
      </Helmet>

      <Header />
      
      <div className="flex flex-1">
        <Sidebar />
        <main className="max-w-[1400px] mx-auto px-4 sm:px-6 md:px-10 py-6 md:py-8 w-full flex-grow">

        <div className="mb-12 animate-in fade-in slide-in-from-top-4 duration-700">
          <div className="flex items-center gap-2 bg-[#D10043]/5 text-[#D10043] px-3 py-1 rounded-md text-[10px] font-black uppercase tracking-[0.2em] mb-3 border border-[#D10043]/10 w-fit">
            <Zap size={12} className="animate-pulse" />
            {userRole} Preferences
          </div>
          <h2 className="text-4xl font-black tracking-tight text-slate-900 leading-none">
            {userRole === 'HR' ? 'HR' : userRole === 'ADMIN' ? 'Admin' : 'Account'} <span className="text-[#D10043]">Settings</span>
          </h2>
          <p className="text-slate-400 font-bold text-sm mt-2 uppercase tracking-widest">
            Manage your {userRole.toLowerCase()} credentials and system preferences.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-10">

          <div className="w-full lg:w-80 shrink-0 animate-in fade-in slide-in-from-left-6 duration-700">
            <div className="bg-white border border-slate-100 rounded-[40px] p-6 shadow-xl shadow-slate-200/40 sticky top-32">
              <div className="flex flex-col items-center mb-8 pb-8 border-b border-slate-50">
                <div className="w-24 h-24 rounded-[32px] bg-slate-50 border-4 border-white shadow-xl overflow-hidden mb-4 flex items-center justify-center text-slate-200">
                  {imagePreview ? (
                    <img 
                      src={imagePreview} 
                      alt="Profile" 
                      className="w-full h-full object-cover" 
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div className={`items-center justify-center w-full h-full ${imagePreview ? 'hidden' : 'flex'}`}>
                    {userRole === 'CANDIDATE' ? <User size={40} /> : <Shield size={40} />}
                  </div>
                </div>
                <h3 className="text-sm font-black text-slate-900 truncate w-full text-center px-4">{formData.fullname || 'Your Name'}</h3>
                <p className="text-[10px] font-black text-[#D10043] uppercase tracking-[0.2em] mt-1">{userRole}</p>
              </div>

              <div className="space-y-2">
                {TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-4 px-6 py-4 rounded-3xl transition-all duration-300 group ${activeTab === tab.id
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
                <p className="text-[11px] font-black text-slate-900 truncate mt-1">{userEmail}</p>
                <div className="mt-4 flex items-center justify-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Active Session</span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex-grow animate-in fade-in slide-in-from-right-6 duration-700">

            {activeTab === 'profile' && (
              <div className="space-y-10">
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <h3 className="text-xl font-black text-slate-900 tracking-tight mb-10 flex items-center gap-3">
                    {userRole === 'CANDIDATE' ? <User size={24} className="text-[#D10043]" /> : <Building2 size={24} className="text-[#D10043]" />}
                    {userRole === 'CANDIDATE' ? 'Public Profile' : 'Professional Identity'}
                  </h3>

                  <div className="space-y-10">
                    <div className="flex flex-col sm:flex-row items-center gap-8 pb-10 border-b border-slate-50">
                      <div className="relative group">
                        <div className="w-32 h-32 rounded-[40px] bg-slate-50 border-4 border-white shadow-2xl shadow-slate-200 overflow-hidden flex items-center justify-center text-slate-200">
                          {imagePreview ? (
                            <img 
                              src={imagePreview} 
                              alt="Profile" 
                              className="w-full h-full object-cover" 
                              onError={(e) => {
                                e.target.style.display = 'none';
                                e.target.nextSibling.style.display = 'flex';
                              }}
                            />
                          ) : null}
                          <div className={`items-center justify-center w-full h-full ${imagePreview ? 'hidden' : 'flex'}`}>
                            <User size={48} className="text-slate-200" />
                          </div>
                        </div>
                        <label className="absolute -bottom-2 -right-2 p-3 bg-slate-900 text-white rounded-2xl shadow-xl hover:bg-[#D10043] transition-colors group-hover:scale-110 duration-300 cursor-pointer">
                          <Camera size={18} />
                          <input type="file" className="hidden" accept="image/*" onChange={handleImageChange} />
                        </label>
                      </div>
                      <div className="text-center sm:text-left">
                        <h4 className="text-lg font-black text-slate-900 mb-1">{userRole === 'CANDIDATE' ? 'Profile Picture' : 'Enterprise Avatar'}</h4>
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-widest leading-relaxed mb-4">
                          JPG, GIF or PNG. Max size of 2MB.<br />
                          {userRole === 'CANDIDATE' ? 'Visible to HR and hiring managers.' : 'Used in internal communications and screening.'}
                        </p>
                        {selectedImage && (
                          <p className="text-[10px] text-[#D10043] font-black uppercase tracking-widest mt-2 animate-pulse">
                            Click "Save Changes" to upload image
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
                        <input
                          type="text"
                          name="fullname"
                          value={formData.fullname}
                          onChange={handleInputChange}
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                        />
                      </div>
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">{userRole === 'CANDIDATE' ? 'Professional Title' : userRole === 'HR' ? 'Position' : 'Admin Role'}</label>
                        <input
                          type="text"
                          name="current_job_title"
                          value={formData.current_job_title}
                          onChange={handleInputChange}
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          placeholder={userRole === 'HR' ? 'e.g. Talent Acquisition Manager' : 'e.g. System Administrator'}
                        />
                      </div>
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Phone Number</label>
                        <input
                          type="text"
                          name="phone"
                          value={formData.phone}
                          onChange={handleInputChange}
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                        />
                      </div>
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Location</label>
                        <input
                          type="text"
                          name="location"
                          value={formData.location}
                          onChange={handleInputChange}
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                        />
                      </div>
                      {userRole === 'HR' && (
                        <div className="space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Department</label>
                          <input
                            type="text"
                            name="department"
                            value={formData.department}
                            onChange={handleInputChange}
                            className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          />
                        </div>
                      )}
                      {userRole === 'ADMIN' && (
                        <div className="space-y-3">
                          <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Managed Region</label>
                          <input
                            type="text"
                            name="managed_region"
                            value={formData.managed_region}
                            onChange={handleInputChange}
                            className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          />
                        </div>
                      )}
                      {userRole === 'CANDIDATE' && (
                        <>
                          <div className="space-y-3">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Highest Degree</label>
                            <input
                              type="text"
                              name="highest_degree"
                              value={formData.highest_degree}
                              onChange={handleInputChange}
                              className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                            />
                          </div>
                          <div className="space-y-3">
                            <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">University</label>
                            <input
                              type="text"
                              name="university"
                              value={formData.university}
                              onChange={handleInputChange}
                              className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                            />
                          </div>
                        </>
                      )}
                      <div className="col-span-full space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">{userRole === 'CANDIDATE' ? 'Bio' : 'Operational Summary'}</label>
                        <textarea
                          rows="4"
                          name="bio"
                          value={formData.bio}
                          onChange={handleInputChange}
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[24px] text-sm font-medium text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all resize-none"
                        />
                      </div>
                    </div>

                    <div className="flex justify-end gap-4 pt-4">
                      <button className="px-8 py-4 bg-slate-50 text-slate-500 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-100 transition-all">Reset</button>
                      <button 
                        onClick={handleSave}
                        disabled={loading}
                        className="px-10 py-4 bg-[#D10043] text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-900 transition-all shadow-xl shadow-pink-100 flex items-center gap-3 disabled:opacity-50"
                      >
                        <Save size={16} /> {loading ? 'Saving...' : 'Save Changes'}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="space-y-10">
                {/* Password Management */}
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <h3 className="text-xl font-black text-slate-900 tracking-tight mb-10 flex items-center gap-3">
                    <Lock size={24} className="text-[#D10043]" />
                    Password & Authentication
                  </h3>

                  <div className="space-y-10">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Current Password</label>
                        <div className="relative group">
                          <input
                            type={showPassword ? 'text' : 'password'}
                            className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                            placeholder="••••••••••••"
                          />
                          <button
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-300 hover:text-slate-600 transition-colors"
                          >
                            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                          </button>
                        </div>
                      </div>
                      <div className="space-y-3 md:pt-8">
                        <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest leading-relaxed px-1">
                          Enterprise accounts require complex passwords (12+ characters, symbols).
                        </p>
                      </div>
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">New Password</label>
                        <input
                          type="password"
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          placeholder="••••••••••••"
                        />
                      </div>
                      <div className="space-y-3">
                        <label className="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Confirm New Password</label>
                        <input
                          type="password"
                          className="w-full px-6 py-4 bg-slate-50 border border-slate-100 rounded-[20px] text-sm font-bold text-slate-900 focus:outline-none focus:ring-4 focus:ring-[#D10043]/10 focus:border-[#D10043] transition-all"
                          placeholder="••••••••••••"
                        />
                      </div>
                    </div>
                    <div className="flex justify-end pt-4 border-t border-slate-50">
                      <button className="px-10 py-4 bg-slate-900 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-[#D10043] transition-all shadow-xl active:scale-[0.95] flex items-center gap-3">
                        <ShieldCheck size={16} /> Update Security Key
                      </button>
                    </div>
                  </div>
                </div>

                {/* MFA Section */}
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <h3 className="text-xl font-black text-slate-900 tracking-tight mb-10 flex items-center gap-3">
                    <Smartphone size={24} className="text-[#D10043]" />
                    Two-Factor Authentication
                  </h3>
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6 p-8 bg-slate-50/50 rounded-[32px] border border-slate-100">
                    <div className="flex gap-5">
                      <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-[#D10043] shadow-sm border border-slate-100">
                        <Globe size={22} />
                      </div>
                      <div>
                        <h4 className="text-lg font-black text-slate-900 leading-none mb-2">SMS Authentication</h4>
                        <p className="text-xs text-slate-400 font-bold uppercase tracking-widest">Receive security codes via your primary phone number.</p>
                      </div>
                    </div>
                    <label className="relative inline-flex items-center cursor-pointer">
                      <input type="checkbox" className="sr-only peer" defaultChecked />
                      <div className="w-14 h-7 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-7 after:transition-all peer-checked:bg-[#D10043]"></div>
                    </label>
                  </div>
                </div>

                {/* Login History */}
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <h3 className="text-xl font-black text-slate-900 tracking-tight mb-8">Login History</h3>
                  <div className="space-y-4">
                    {[
                      { device: 'MacBook Pro 16"', location: 'Sto. Tomas, Batangas', status: 'Active Now', icon: <Smartphone size={18} />, color: 'text-green-500 bg-green-50' },
                      { device: 'iPhone 15 Pro', location: 'Manila, Philippines', status: '2 hours ago', icon: <Smartphone size={18} />, color: 'text-slate-400 bg-slate-50' }
                    ].map((session, i) => (
                      <div key={i} className="flex items-center justify-between p-6 rounded-3xl border border-slate-50 hover:bg-slate-50/50 transition-all">
                        <div className="flex gap-4 items-center">
                          <div className="w-10 h-10 bg-slate-100 rounded-xl flex items-center justify-center text-slate-500">
                            {session.icon}
                          </div>
                          <div>
                            <p className="text-sm font-black text-slate-900">{session.device}</p>
                            <p className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">{session.location}</p>
                          </div>
                        </div>
                        <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-lg ${session.color}`}>
                          {session.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="space-y-10">
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <h3 className="text-xl font-black text-slate-900 tracking-tight mb-10 flex items-center gap-3">
                    <Bell size={24} className="text-[#D10043]" />
                    Channel Preferences
                  </h3>

                  <div className="space-y-6">
                    {[
                      { title: userRole === 'CANDIDATE' ? "Application Progress" : "Screening Alerts", desc: "Get notified when status changes occur.", icon: <TrendingUp size={18} /> },
                      { title: userRole === 'CANDIDATE' ? "Job Recommendations" : "System Health", desc: "Maintenance and performance updates.", icon: <Zap size={18} /> },
                      { title: "Twilio AI Caller", desc: "Automated phone reminders and notifications.", icon: <Smartphone size={18} /> },
                      { title: "Direct Internal Chat", desc: "Notifications for real-time internal messages.", icon: <MessageSquare size={18} /> }
                    ].map((item, i) => (
                      <div key={i} className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6 p-6 hover:bg-slate-50 rounded-[32px] transition-all border border-transparent hover:border-slate-100 group">
                        <div className="flex gap-5">
                          <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-slate-300 shadow-sm border border-slate-100 group-hover:text-[#D10043] transition-colors">
                            {item.icon}
                          </div>
                          <div>
                            <h4 className="text-base font-black text-slate-900 leading-none mb-2">{item.title}</h4>
                            <p className="text-[11px] text-slate-400 font-bold uppercase tracking-widest">{item.desc}</p>
                          </div>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input type="checkbox" className="sr-only peer" defaultChecked />
                          <div className="w-12 h-6 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[#D10043]"></div>
                        </label>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-end mt-10">
                    <button className="px-10 py-4 bg-[#D10043] text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-slate-900 transition-all shadow-xl shadow-pink-100 flex items-center gap-3">
                      <Save size={16} /> Save Settings
                    </button>
                  </div>
                </div>

                <div className="bg-slate-50 rounded-[48px] p-10 border border-slate-100">
                  <div className="flex items-center gap-4 mb-6">
                    <Mail className="text-[#D10043]" size={20} />
                    <h4 className="text-sm font-black text-slate-900 uppercase tracking-widest">Email Digest</h4>
                  </div>
                  <p className="text-xs text-slate-500 font-medium mb-8 max-w-lg">
                    Receive a weekly summary of your application activities, new job matches, and system updates directly in your inbox.
                  </p>
                  <button className="px-6 py-3 bg-white border border-slate-200 rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-[#D10043] hover:text-white hover:border-[#D10043] transition-all">Configure Digest</button>
                </div>
              </div>
            )}

            {activeTab === 'applications' && userRole === 'CANDIDATE' && (
              <div className="space-y-10 animate-in fade-in slide-in-from-right-6 duration-700">
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <div className="flex justify-between items-center mb-10">
                    <h3 className="text-xl font-black text-slate-900 tracking-tight flex items-center gap-3">
                      <Briefcase size={24} className="text-[#D10043]" />
                      Submitted Applications
                    </h3>
                    <span className="bg-slate-50 text-slate-400 text-[10px] font-black px-3 py-1 rounded-lg uppercase tracking-widest">3 Total</span>
                  </div>

                  <div className="space-y-6">
                    {[
                      { role: 'Senior Frontend Developer', status: 'Interview Stage', date: 'Oct 12, 2023', type: 'Full-time', color: 'text-blue-500 bg-blue-50' },
                      { role: 'UI/UX Designer', status: 'Under Review', date: 'Oct 08, 2023', type: 'Contract', color: 'text-orange-500 bg-orange-50' },
                      { role: 'Product Manager', status: 'Rejected', date: 'Sept 25, 2023', type: 'Full-time', color: 'text-red-500 bg-red-50' }
                    ].map((app, i) => (
                      <div key={i} className="group p-8 rounded-[32px] border border-slate-50 hover:border-[#D10043]/20 bg-slate-50/30 hover:bg-white transition-all duration-500">
                        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
                          <div className="flex gap-6">
                            <div className="w-14 h-14 bg-white rounded-2xl flex items-center justify-center text-slate-200 group-hover:text-[#D10043] border border-slate-100 transition-colors">
                              <Building2 size={24} />
                            </div>
                            <div>
                              <h4 className="text-lg font-black text-slate-900 mb-1 group-hover:text-[#D10043] transition-colors">{app.role}</h4>
                              <div className="flex items-center gap-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                                <span>Mariwasa Siam Ceramics</span>
                                <span className="w-1 h-1 bg-slate-200 rounded-full" />
                                <span>{app.type}</span>
                              </div>
                            </div>
                          </div>
                          <div className="flex flex-col items-end gap-3">
                            <span className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest ${app.color}`}>
                              {app.status}
                            </span>
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Applied on {app.date}</span>
                          </div>
                        </div>
                        <div className="mt-8 pt-8 border-t border-slate-50 flex justify-between items-center opacity-0 group-hover:opacity-100 transition-all translate-y-2 group-hover:translate-y-0">
                          <p className="text-xs text-slate-400 font-medium italic">Your profile was 92% match for this role.</p>
                          <button className="flex items-center gap-2 text-[10px] font-black text-[#D10043] uppercase tracking-widest hover:gap-4 transition-all">
                            View Details <ChevronRight size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="bg-slate-900 rounded-[48px] p-12 text-white relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-64 h-64 bg-[#D10043]/10 rounded-full blur-3xl -mr-32 -mt-32" />
                  <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-10">
                    <div className="max-w-md">
                      <h4 className="text-2xl font-black tracking-tight mb-4 leading-none">Ready for your next move?</h4>
                      <p className="text-slate-400 text-sm font-medium leading-relaxed">
                        Explore new opportunities that match your skills. Our AI-powered recommendations are updated daily.
                      </p>
                    </div>
                    <button onClick={() => navigate('/candidate/findjobs')} className="px-10 py-5 bg-[#D10043] text-white rounded-[20px] font-black text-xs uppercase tracking-widest hover:bg-white hover:text-slate-900 transition-all shadow-2xl shadow-pink-900/20">
                      Browse Jobs
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'system' && (userRole === 'HR' || userRole === 'ADMIN') && (
              <div className="space-y-10 animate-in fade-in slide-in-from-right-6 duration-700">
                <div className="bg-white border border-slate-100 rounded-[48px] p-10 shadow-xl shadow-slate-200/40">
                  <h3 className="text-xl font-black text-slate-900 tracking-tight mb-10 flex items-center gap-3">
                    <Shield size={24} className="text-[#D10043]" />
                    System Access Level
                  </h3>

                  <div className="p-8 bg-slate-900 rounded-[32px] text-white mb-10">
                    <div className="flex items-center gap-6 mb-8">
                      <div className="w-16 h-16 bg-[#D10043] rounded-2xl flex items-center justify-center shadow-xl shadow-pink-900/20">
                        <Users size={32} />
                      </div>
                      <div>
                        <h4 className="text-xl font-black tracking-tight leading-none mb-2">{userRole} Credentials</h4>
                        <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">Full Administrative Privileges</p>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {['Read', 'Write', 'Delete', 'Audit'].map((perm, i) => (
                        <div key={i} className="bg-white/5 border border-white/10 p-4 rounded-2xl flex items-center justify-center gap-2">
                          <Check size={14} className="text-green-500" />
                          <span className="text-[10px] font-black uppercase tracking-widest">{perm}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="space-y-6">
                    <h4 className="text-sm font-black text-slate-400 uppercase tracking-widest ml-1">Connected Systems</h4>
                    {[
                      { name: 'Twilio API', status: 'Connected', icon: <Smartphone size={18} /> },
                      { name: 'Siam Cloud', status: 'Syncing', icon: <Globe size={18} /> }
                    ].map((sys, i) => (
                      <div key={i} className="flex items-center justify-between p-6 bg-slate-50 rounded-3xl border border-slate-100">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-slate-400 border border-slate-100">
                            {sys.icon}
                          </div>
                          <span className="text-sm font-black text-slate-900">{sys.name}</span>
                        </div>
                        <span className="flex items-center gap-2 text-[9px] font-black text-green-500 uppercase tracking-widest">
                          <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
                          {sys.status}
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
