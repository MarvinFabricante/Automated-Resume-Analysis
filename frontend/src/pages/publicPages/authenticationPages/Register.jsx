import React, { useState } from 'react';
import axios from 'axios';
import { Users, Eye, EyeOff, Loader2, CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';
import { Helmet } from 'react-helmet-async';

const Register = () => {
  const [role] = useState('CANDIDATE');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
    confirmPassword: '',
    managedRegion: '',
  });

  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [showTermsModal, setShowTermsModal] = useState(false);

  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'success',
    title: '',
    message: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!agreedToTerms) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Registration Error',
        message: 'You must agree to the Terms and Conditions to register.'
      });
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Registration Error',
        message: 'Passwords do not match!'
      });
      return;
    }

    setLoading(true);

    let endpoint = 'http://localhost:8000/candidate/register';
    if (role === 'HR') {
      endpoint = 'http://localhost:8000/hr/register';
    } else if (role === 'ADMIN') {
      endpoint = 'http://localhost:8000/admins/register';
    }

    const payload = {
      fullname: formData.fullName,
      email: formData.email.trim().toLowerCase(),
      password: formData.password,
    };

    if (role === 'HR') {
      payload.company_name = "Mariwasa Siam Ceramics Inc.";
      payload.department = "General";
    } else if (role === 'ADMIN') {
      payload.managed_region = formData.managedRegion || "Main Headquarters";
    } else {
      payload.resume_url = null;
      payload.experience_years = 0;
    }

    try {
      const response = await axios.post(endpoint, payload);

      if (response.status === 200 || response.status === 201) {
        setModalState({
          isOpen: true,
          type: 'success',
          title: 'Account Created!',
          message: `Your ${role === 'HR' ? 'HR Staff' : role === 'ADMIN' ? 'Admin' : 'Candidate'} account has been registered successfully.`
        });
      }
    } catch (error) {
      const errorData = error.response?.data?.detail;
      let errorMessage = "Registration failed. Please try again.";

      if (typeof errorData === 'string') {
        errorMessage = errorData;
      } else if (Array.isArray(errorData)) {
        errorMessage = errorData[0]?.msg || errorMessage;
      }

      const isExistingAccount = errorMessage.toLowerCase().includes('already') ||
        errorMessage.toLowerCase().includes('exists') ||
        errorMessage.toLowerCase().includes('registered');

      if (isExistingAccount) {
        setModalState({
          isOpen: true,
          type: 'exists',
          title: 'Account Already Exists',
          message: 'It looks like an account with this email is already registered. Please sign in instead.'
        });
      } else {
        setModalState({
          isOpen: true,
          type: 'error',
          title: 'Registration Failed',
          message: errorMessage
        });
      }
      console.error("Registration Error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-8 bg-[#F0F4F9] font-sans antialiased text-gray-800 relative">
      <Helmet>
        <title>Create Account - Mariwasa Portal</title>
      </Helmet>

      <button 
        onClick={() => window.location.href = '/'}
        className="fixed top-8 left-8 flex items-center gap-2 text-gray-600 hover:text-[#D60041] transition-all group font-bold text-xs uppercase tracking-widest bg-white/50 backdrop-blur-sm py-3 px-5 rounded-2xl border border-gray-200 hover:border-pink-100 hover:shadow-lg active:scale-95 z-50"
      >
        <ArrowLeft size={16} className="group-hover:-translate-x-1 transition-transform" />
        Back to Home
      </button>

      {modalState.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-8 transform transition-all animate-in zoom-in-95 duration-200">
            <div className="flex flex-col items-center text-center">
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-5 ${modalState.type === 'success' ? 'bg-green-50' :
                  modalState.type === 'exists' ? 'bg-blue-50' : 'bg-red-50'
                }`}>
                {modalState.type === 'success' ? (
                  <CheckCircle2 className="w-8 h-8 text-green-500" />
                ) : modalState.type === 'exists' ? (
                  <Users className="w-8 h-8 text-blue-500" />
                ) : (
                  <XCircle className="w-8 h-8 text-red-500" />
                )}
              </div>
              <h3 className="text-xl font-normal text-gray-900 mb-2 tracking-tight">
                {modalState.title}
              </h3>
              <p className="text-sm text-gray-600 mb-8 px-2 leading-relaxed">
                {modalState.message}
              </p>
              <button
                onClick={() => {
                  if (modalState.type === 'success' || modalState.type === 'exists') {
                    window.location.href = '/login';
                  } else {
                    setModalState({ ...modalState, isOpen: false });
                  }
                }}
                className={`w-full font-medium py-2.5 px-4 rounded-full transition-all duration-200 text-sm ${modalState.type === 'success' ? 'bg-[#D60041] hover:bg-[#b50037] text-white' :
                    modalState.type === 'exists' ? 'bg-blue-600 hover:bg-blue-700 text-white' :
                      'bg-gray-100 hover:bg-gray-200 text-gray-800'
                  }`}
              >
                {modalState.type === 'success' ? 'Continue to Login' :
                  modalState.type === 'exists' ? 'Go to Login' : 'Try Again'}
              </button>
            </div>
          </div>
        </div>
      )}

      {showTermsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-[28px] shadow-2xl w-full max-w-lg p-8 transform transition-all animate-in zoom-in-95 duration-200 relative overflow-hidden flex flex-col max-h-[80vh]">
            <div className="flex justify-between items-center mb-6 shrink-0">
              <h3 className="text-2xl font-normal tracking-tight text-gray-900">Terms and Conditions</h3>
              <button onClick={() => setShowTermsModal(false)} className="text-gray-400 hover:bg-gray-100 p-2 rounded-full transition">
                <XCircle className="w-6 h-6" />
              </button>
            </div>
            <div className="overflow-y-auto pr-2 text-sm text-gray-700 space-y-4 mb-6 font-normal">
              <p>Welcome to Mariwasa Siam Ceramics Inc. Resume Analysis System. By registering an account, you agree to comply with our terms and conditions.</p>
              <h4 className="font-medium text-gray-900 mt-2">1. Data Privacy</h4>
              <p>We collect and process your personal and professional data strictly for recruitment and analytical purposes. We adhere to data protection regulations and ensure your data is kept secure.</p>
              <h4 className="font-medium text-gray-900 mt-2">2. Account Responsibilities</h4>
              <p>You are responsible for maintaining the confidentiality of your account credentials. Any activities that occur under your account are your responsibility.</p>
              <h4 className="font-medium text-gray-900 mt-2">3. System Usage</h4>
              <p>The system is to be used exclusively for applying to, or managing, job positions at Mariwasa. Any misuse, unauthorized access attempts, or submission of false information may result in account termination.</p>
            </div>
            <div className="mt-auto shrink-0 pt-6 border-t border-gray-100 flex justify-end gap-3">
              <button
                onClick={() => setShowTermsModal(false)}
                className="px-6 py-2.5 rounded-full font-medium text-sm text-gray-700 hover:bg-gray-100 transition"
              >
                Close
              </button>
              <button
                onClick={() => {
                  setAgreedToTerms(true);
                  setShowTermsModal(false);
                }}
                className="px-6 py-2.5 rounded-full font-medium text-sm bg-[#D60041] hover:bg-[#b50037] text-white transition shadow-sm"
              >
                I agree
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-[28px] shadow-sm w-full max-w-[1040px] flex flex-col md:flex-row overflow-hidden min-h-[500px]">

        <div className="w-full md:w-[45%] p-10 md:p-14 flex flex-col justify-start">
          <div className="mb-6">
            <img src="src/assets/logo.png" alt="Mariwasa Logo" className="h-10 w-10 object-contain" />
          </div>
          <h1 className="text-[36px] leading-[44px] font-normal tracking-normal text-gray-900 mb-4">
            Create a Mariwasa Account
          </h1>
          <p className="text-base font-normal text-gray-800 mb-8 md:mb-0">
            to access the Resume Analysis System. Set up your profile to continue.
          </p>
        </div>

        <div className="w-full md:w-[55%] p-10 md:p-14 flex flex-col justify-center">
          <form onSubmit={handleSubmit} className="w-full max-w-[420px] mx-auto md:mx-0 md:ml-auto">

            <div className="space-y-4 mb-6">

              <div className="relative">
                <input
                  type="text"
                  id="fullName"
                  name="fullName"
                  required
                  value={formData.fullName}
                  onChange={handleChange}
                  className="peer w-full px-4 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:px-[15px] transition-all placeholder-transparent bg-transparent"
                  placeholder="Full Name"
                />
                <label htmlFor="fullName" className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none">
                  Full name
                </label>
              </div>

              <div className="relative">
                <input
                  type="email"
                  id="email"
                  name="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  className="peer w-full px-4 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:px-[15px] transition-all placeholder-transparent bg-transparent"
                  placeholder="Email address"
                />
                <label htmlFor="email" className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none">
                  Email address
                </label>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    required
                    value={formData.password}
                    onChange={handleChange}
                    className="peer w-full pl-4 pr-10 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:pl-[15px] transition-all placeholder-transparent bg-transparent"
                    placeholder="Password"
                  />
                  <label htmlFor="password" className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none z-10">
                    Password
                  </label>
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-900 p-1 rounded-full hover:bg-gray-100 transition-colors z-20">
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>

                <div className="relative">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    id="confirmPassword"
                    name="confirmPassword"
                    required
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className="peer w-full pl-4 pr-10 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:pl-[15px] transition-all placeholder-transparent bg-transparent"
                    placeholder="Confirm"
                  />
                  <label htmlFor="confirmPassword" className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none z-10">
                    Confirm
                  </label>
                  <button type="button" onClick={() => setShowConfirmPassword(!showConfirmPassword)} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-900 p-1 rounded-full hover:bg-gray-100 transition-colors z-20">
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <p className="text-[11px] text-gray-600 ml-1 mt-1">Use 8 or more characters with a mix of letters & numbers</p>

              {role === 'ADMIN' && (
                <div className="relative mt-4 animate-in fade-in slide-in-from-top-2 duration-300">
                  <input
                    type="text"
                    id="managedRegion"
                    name="managedRegion"
                    value={formData.managedRegion}
                    onChange={handleChange}
                    className="peer w-full px-4 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:px-[15px] transition-all placeholder-transparent bg-transparent"
                    placeholder="Managed Region / Office"
                  />
                  <label htmlFor="managedRegion" className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none">
                    Managed Region (Optional)
                  </label>
                </div>
              )}
            </div>

            <div className="flex items-start gap-3 mt-8 mb-10">
              <div className="flex items-center h-5 mt-0.5">
                <input
                  id="terms"
                  type="checkbox"
                  checked={agreedToTerms}
                  onChange={(e) => setAgreedToTerms(e.target.checked)}
                  className="w-4 h-4 border-gray-400 rounded text-[#D60041] focus:ring-[#D60041] cursor-pointer"
                  required
                />
              </div>
              <div className="text-sm">
                <label htmlFor="terms" className="font-normal text-gray-700 cursor-pointer select-none">
                  I agree to the Mariwasa{' '}
                  <button
                    type="button"
                    onClick={(e) => { e.preventDefault(); setShowTermsModal(true); }}
                    className="text-[#D60041] font-medium hover:underline focus:outline-none inline-block"
                  >
                    Terms and Conditions
                  </button>
                </label>
              </div>
            </div>

            <div className="flex flex-col-reverse sm:flex-row justify-between items-center gap-4 sm:gap-0 mt-8">
              <a
                href="/login"
                className="text-sm font-medium text-[#D60041] hover:bg-red-50 px-3 py-2 rounded-md transition-colors w-full sm:w-auto text-center"
              >
                Sign in instead
              </a>
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-medium px-6 py-2.5 rounded-full transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center min-w-[100px]"
              >
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : "Next"}
              </button>
            </div>
          </form>
        </div>
      </div>

      <div className="w-full max-w-[1040px] mt-4 flex flex-col sm:flex-row justify-between items-center text-xs text-gray-600 px-2">
        <div className="mb-4 sm:mb-0">
          <select className="bg-transparent border-none focus:ring-0 cursor-pointer outline-none hover:bg-gray-200 py-1 px-2 rounded-md transition-colors">
            <option>English (United States)</option>
            <option>Filipino</option>
          </select>
        </div>
        <div className="flex space-x-6">
          <a href="#" className="hover:bg-gray-200 px-2 py-1 rounded-md transition-colors">Help</a>
          <a href="#" className="hover:bg-gray-200 px-2 py-1 rounded-md transition-colors">Privacy</a>
          <a href="#" className="hover:bg-gray-200 px-2 py-1 rounded-md transition-colors">Terms</a>
        </div>
      </div>
    </div>
  );
};

export default Register;