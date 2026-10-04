import React, { useState, useEffect } from 'react';
import authService from '../../../services/authService';
import { API_BASE_URL } from '../../../services/api';
import { useDispatch } from 'react-redux';
import { setCredentials } from '../../../redux/slices/authSlice';
import { Helmet } from 'react-helmet-async';
import {
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  User,
  Calendar,
  ShieldCheck,
  Sparkles
} from 'lucide-react';

const Login = () => {
  const [email, setEmail] = useState(() => {
    return localStorage.getItem('saved_email') || '';
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedRole, setSelectedRole] = useState('candidate'); // 'candidate' | 'hr' | 'admin'
  const [detectedRoleInfo, setDetectedRoleInfo] = useState(null);
  const [isDetectingRole, setIsDetectingRole] = useState(false);
  const dispatch = useDispatch();

  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'success',
    title: '',
    message: ''
  });
  const [verifiedUserRole, setVerifiedUserRole] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const errorParam = params.get('error');
    if (errorParam) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Authentication Error',
        message: decodeURIComponent(errorParam)
      });
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  useEffect(() => {
    const checkExistingSession = () => {
      const token = localStorage.getItem('token');
      const role = localStorage.getItem('role');
      if (token && role) {
        if (role.toUpperCase() === 'ADMIN') {
          window.location.href = '/admin/dashboard';
        } else if (role.toUpperCase() === 'HR') {
          window.location.href = '/hr/dashboard';
        } else {
          window.location.href = '/candidate/dashboard';
        }
      }
    };
    
    checkExistingSession();
    window.addEventListener('storage', checkExistingSession);
    return () => window.removeEventListener('storage', checkExistingSession);
  }, []);

  // Intelligent Role Auto-Detection from typed email
  useEffect(() => {
    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes('@') || cleanEmail.length < 5) {
      setDetectedRoleInfo(null);
      setIsDetectingRole(false);
      return;
    }

    setIsDetectingRole(true);
    const timer = setTimeout(async () => {
      try {
        const response = await authService.checkRole(cleanEmail);
        const data = response.data;
        if (data && data.role) {
          const roleKey = data.role.toLowerCase();
          setDetectedRoleInfo({
            role: roleKey,
            roleName: data.role,
            exists: data.exists,
            isAuthorizedStaff: data.is_authorized_staff
          });
          // Automatically synchronize role tab if recognized
          if (roleKey === 'hr' || roleKey === 'admin') {
            setSelectedRole(roleKey);
          } else if (roleKey === 'candidate') {
            setSelectedRole('candidate');
          }
        }
      } catch (err) {
        // Silently keep default
      } finally {
        setIsDetectingRole(false);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [email]);

  const handleGoogleLogin = () => {
    const existingToken = localStorage.getItem('token');
    const existingRole = localStorage.getItem('role');
    
    if (existingToken && existingRole) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Already Logged In',
        message: `An account (${existingRole.toLowerCase()}) is already logged in on this browser. Please log out first if you want to switch accounts.`
      });
      return;
    }

    // Role-specific Google login URL with separated scopes to avoid Google Console conflicts
    window.location.href = `${API_BASE_URL}/auth/google/login?role=${selectedRole}`;
  };

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    localStorage.setItem('saved_email', value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const existingToken = localStorage.getItem('token');
    const existingRole = localStorage.getItem('role');
    
    if (existingToken && existingRole) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Already Logged In',
        message: `An account (${existingRole.toLowerCase()}) is already logged in on this browser. Please log out first if you want to switch accounts.`
      });
      return;
    }

    setLoading(true);

    const normalizedEmail = email.trim().toLowerCase();

    try {
      const response = await authService.login(normalizedEmail, password);

      const { access_token, role: verifiedRole, fullname, user_id, profile_image_url } = response.data;

      // Update Redux state
      dispatch(setCredentials({
        user: normalizedEmail,
        role: verifiedRole,
        profileImageUrl: profile_image_url
      }));

      localStorage.setItem('token', access_token);
      localStorage.setItem('fullname', fullname);
      localStorage.setItem('user_id', user_id);

      setVerifiedUserRole(verifiedRole);
      setModalState({
        isOpen: true,
        type: 'success',
        title: 'Success!',
        message: `Authentication successful. Welcome back to the ${verifiedRole} portal.`
      });

    } catch (err) {
      const message = err.response?.data?.detail || "Invalid email or password";
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Login Failed',
        message: message
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRedirect = () => {
    if (verifiedUserRole.toUpperCase() === 'ADMIN') {
      window.location.href = '/admin/dashboard';
    } else if (verifiedUserRole.toUpperCase() === 'HR') {
      window.location.href = '/hr/dashboard';
    } else {
      window.location.href = '/candidate/dashboard';
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 pt-16 pb-8 sm:py-8 bg-[#F0F4F9] font-sans antialiased text-gray-800">
      <Helmet>
        <title>Sign in - Mariwasa Portal</title>
      </Helmet>

      <button
        onClick={() => window.location.href = '/'}
        className="fixed top-3 left-3 sm:top-8 sm:left-8 flex items-center gap-1.5 sm:gap-2 text-gray-600 hover:text-[#D60041] transition-all group font-bold text-[11px] sm:text-xs uppercase tracking-widest bg-white/70 backdrop-blur-sm py-2 px-3 sm:py-3 sm:px-5 rounded-xl sm:rounded-2xl border border-gray-200 hover:border-pink-100 hover:shadow-lg active:scale-95 z-50 shadow-sm"
      >
        <ArrowLeft size={14} className="group-hover:-translate-x-1 transition-transform sm:w-4 sm:h-4" />
        Back to Home
      </button>

      {modalState.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/40 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-6 sm:p-8 transform transition-all animate-in zoom-in-95 duration-200">
            <div className="flex flex-col items-center text-center">
              <div className={`w-14 h-14 sm:w-16 sm:h-16 rounded-full flex items-center justify-center mb-4 sm:mb-5 ${modalState.type === 'success' ? 'bg-green-50' : 'bg-red-50'}`}>
                {modalState.type === 'success' ? (
                  <CheckCircle2 className="w-7 h-7 sm:w-8 sm:h-8 text-green-500" />
                ) : (
                  <XCircle className="w-7 h-7 sm:w-8 sm:h-8 text-red-500" />
                )}
              </div>
              <h3 className="text-lg sm:text-xl font-normal text-gray-900 mb-2 tracking-tight">
                {modalState.title}
              </h3>
              <p className="text-xs sm:text-sm text-gray-600 mb-6 sm:mb-8 px-2 leading-relaxed">
                {modalState.message}
              </p>
              <button
                onClick={() => {
                  if (modalState.type === 'success') {
                    handleRedirect();
                  } else {
                    setModalState({ ...modalState, isOpen: false });
                  }
                }}
                className={`w-full font-medium py-2.5 px-4 rounded-full transition-all duration-200 text-xs sm:text-sm ${modalState.type === 'success'
                  ? 'bg-[#D60041] hover:bg-[#b50037] text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                  }`}
              >
                {modalState.type === 'success' ? 'Continue' : 'Try Again'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl sm:rounded-[28px] shadow-sm w-full max-w-[1060px] flex flex-col md:flex-row overflow-hidden min-h-[460px]">

        {/* Left Portal Info Banner */}
        <div className="w-full md:w-[42%] p-6 sm:p-10 md:p-12 flex flex-col justify-between border-b md:border-b-0 md:border-r border-gray-100 bg-gradient-to-b from-white to-gray-50/50">
          <div>
            <div className="mb-4 sm:mb-6 flex items-center gap-3">
              <img src="/assets/logo.png" alt="Mariwasa Logo" className="h-9 w-9 sm:h-10 sm:w-10 object-contain" />
              <span className="text-xs font-bold tracking-wider uppercase text-gray-400">Mariwasa Portal</span>
            </div>
            
            <h1 className="text-2xl sm:text-[34px] sm:leading-[42px] font-normal tracking-tight text-gray-900 mb-3 sm:mb-4">
              Sign in
            </h1>
            
            <p className="text-sm sm:text-base font-normal text-gray-600 leading-relaxed mb-6">
              {selectedRole === 'candidate' && "Sign in to view and track your job applications, assessments, and interview schedules."}
              {selectedRole === 'hr' && "Human Resources portal to manage job postings, evaluate candidate resumes, and sync interview calendars."}
              {selectedRole === 'admin' && "Administration console for system settings, user management, audit trails, and security."}
            </p>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            <div className="flex items-center gap-2 text-xs font-medium text-gray-500">
              <Sparkles size={14} className="text-[#D60041]" />
              <span>
                {selectedRole === 'candidate' && "Candidate Google accounts log in without Google Console restrictions."}
                {selectedRole === 'hr' && "HR Google accounts integrate directly with Google Calendar."}
                {selectedRole === 'admin' && "Authorized administrator authentication."}
              </span>
            </div>
          </div>
        </div>

        {/* Right Form Container */}
        <div className="w-full md:w-[58%] p-6 sm:p-10 md:p-12 flex flex-col justify-center">
          <div className="w-full max-w-[420px] mx-auto md:mx-0 md:ml-auto">
            
            {/* Role Selection Tabs */}
            <div className="mb-5">
              <div className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Select Login Role</span>
                {detectedRoleInfo && (
                  <span className="text-emerald-600 font-semibold normal-case tracking-normal flex items-center gap-1">
                    ✓ Recognized as {detectedRoleInfo.roleName}
                  </span>
                )}
              </div>
              <div className="grid grid-cols-3 gap-1.5 p-1 bg-gray-100 rounded-xl">
                <button
                  type="button"
                  onClick={() => setSelectedRole('candidate')}
                  className={`flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg text-xs font-bold transition-all ${
                    selectedRole === 'candidate'
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                  }`}
                >
                  <User size={13} className={selectedRole === 'candidate' ? 'text-[#D60041]' : 'text-gray-400'} />
                  <span>Candidate</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedRole('hr')}
                  className={`flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg text-xs font-bold transition-all ${
                    selectedRole === 'hr'
                      ? 'bg-white text-[#D60041] shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                  }`}
                >
                  <Calendar size={13} className={selectedRole === 'hr' ? 'text-[#D60041]' : 'text-gray-400'} />
                  <span>HR Staff</span>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedRole('admin')}
                  className={`flex items-center justify-center gap-1.5 py-2 px-2.5 rounded-lg text-xs font-bold transition-all ${
                    selectedRole === 'admin'
                      ? 'bg-white text-indigo-700 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                  }`}
                >
                  <ShieldCheck size={13} className={selectedRole === 'admin' ? 'text-indigo-600' : 'text-gray-400'} />
                  <span>Admin</span>
                </button>
              </div>
            </div>

            {/* Google OAuth Login Button */}
            <div className="mb-5">
              <button
                type="button"
                onClick={handleGoogleLogin}
                className="w-full flex items-center justify-center gap-3 bg-white border border-gray-300 hover:bg-gray-50 hover:border-gray-400 text-gray-800 text-sm font-semibold px-5 py-3 rounded-full transition-all shadow-sm hover:shadow active:scale-[0.99] group"
              >
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google Logo" className="w-5 h-5 group-hover:scale-105 transition-transform" />
                <span>
                  {selectedRole === 'candidate' && "Sign in with Google (Candidate)"}
                  {selectedRole === 'hr' && "Sign in with Google (HR Portal)"}
                  {selectedRole === 'admin' && "Sign in with Google (Admin Portal)"}
                </span>
              </button>
              
              <p className="text-center text-[11px] text-gray-500 mt-2 font-medium px-2 leading-tight">
                {selectedRole === 'candidate' && (
                  <span className="text-gray-500">
                    Candidate Portal: Log in with any Google account without Google Console conflicts.
                  </span>
                )}
                {selectedRole === 'hr' && (
                  <span className="text-amber-700 font-medium">
                    HR Portal: Connects Google Calendar for authorized HR personnel registered in Google Console.
                  </span>
                )}
                {selectedRole === 'admin' && (
                  <span className="text-gray-500">
                    Admin Portal: Dedicated sign-in for verified system administrators.
                  </span>
                )}
              </p>
            </div>

            {/* Divider */}
            <div className="relative flex items-center justify-center my-5">
              <div className="border-t border-gray-200 w-full"></div>
              <span className="bg-white px-3 text-xs text-gray-400 uppercase tracking-wider font-medium absolute">or sign in with password</span>
            </div>

            <form onSubmit={handleSubmit} className="w-full">
              <div className="space-y-4 mb-2">
                <div className="relative">
                  <input
                    type="email"
                    id="email"
                    required
                    value={email}
                    onChange={handleEmailChange}
                    className="peer w-full px-4 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:px-[15px] transition-all placeholder-transparent bg-transparent"
                    placeholder="Email address"
                  />
                  <label
                    htmlFor="email"
                    className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none flex items-center gap-1"
                  >
                    <span>Email address</span>
                    {isDetectingRole && <Loader2 size={10} className="animate-spin text-[#D60041]" />}
                  </label>
                </div>

                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="peer w-full pl-4 pr-12 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:pl-[15px] transition-all placeholder-transparent bg-transparent"
                    placeholder="Enter your password"
                  />
                  <label
                    htmlFor="password"
                    className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none"
                  >
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-900 p-1 rounded-full hover:bg-gray-100 transition-colors"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              <div className="mb-5 mt-2 flex items-center justify-between">
                <a href="/forgot-password" className="text-xs font-medium text-[#D60041] hover:underline transition-colors inline-block">
                  Forgot password?
                </a>
                <span className="text-[11px] text-gray-400 font-medium">
                  Signing in as: <strong className="uppercase text-gray-600">{selectedRole}</strong>
                </span>
              </div>

              <div className="flex flex-col-reverse sm:flex-row justify-between items-center gap-4 sm:gap-0 mt-6">
                <a
                  href="/register"
                  className="text-sm font-medium text-[#D60041] hover:bg-red-50 px-3 py-2 rounded-md transition-colors w-full sm:w-auto text-center"
                >
                  Create account
                </a>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full sm:w-auto bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-medium px-6 py-2.5 rounded-full transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center min-w-[100px] shadow-sm"
                >
                  {loading ? <Loader2 className="animate-spin h-5 w-5" /> : "Sign in"}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <div className="w-full max-w-[1060px] mt-4 flex flex-col sm:flex-row justify-between items-center text-xs text-gray-600 px-2">
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

export default Login;