import React, { useState } from 'react';
import authService from '../../../services/authService';
import { useDispatch } from 'react-redux';
import { setCredentials } from '../../../redux/slices/authSlice';
import { Helmet } from 'react-helmet-async';
import {
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  ArrowLeft
} from 'lucide-react';

const Login = () => {
  const [email, setEmail] = useState(() => {
    return localStorage.getItem('saved_email') || '';
  });
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const dispatch = useDispatch();

  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'success',
    title: '',
    message: ''
  });
  const [verifiedUserRole, setVerifiedUserRole] = useState('');

  const handleEmailChange = (e) => {
    const value = e.target.value;
    setEmail(value);
    localStorage.setItem('saved_email', value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-8 bg-[#F0F4F9] font-sans antialiased text-gray-800">
      <Helmet>
        <title>Sign in - Mariwasa Portal</title>
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
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-5 ${modalState.type === 'success' ? 'bg-green-50' : 'bg-red-50'}`}>
                {modalState.type === 'success' ? (
                  <CheckCircle2 className="w-8 h-8 text-green-500" />
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
                  if (modalState.type === 'success') {
                    handleRedirect();
                  } else {
                    setModalState({ ...modalState, isOpen: false });
                  }
                }}
                className={`w-full font-medium py-2.5 px-4 rounded-full transition-all duration-200 text-sm ${modalState.type === 'success'
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

      <div className="bg-white rounded-[28px] shadow-sm w-full max-w-[1040px] flex flex-col md:flex-row overflow-hidden min-h-[400px]">

        <div className="w-full md:w-[45%] p-10 md:p-14 flex flex-col justify-start">
          <div className="mb-6">
            <img src="src/assets/logo.png" alt="Mariwasa Logo" className="h-10 w-10 object-contain" />
          </div>
          <h1 className="text-[36px] leading-[44px] font-normal tracking-normal text-gray-900 mb-4">
            Sign in
          </h1>
          <p className="text-base font-normal text-gray-800 mb-8 md:mb-0">
            to Mariwasa Resume Analysis System. Please enter your credentials to continue.
          </p>
        </div>

        <div className="w-full md:w-[55%] p-10 md:p-14 flex flex-col justify-center">
          <form onSubmit={handleSubmit} className="w-full max-w-[400px] mx-auto md:mx-0 md:ml-auto">

            <div className="space-y-4 mb-2">
              <div className="relative">
                <input
                  type="email"
                  id="email"
                  required
                  value={email}
                  onChange={handleEmailChange}
                  className="peer w-full px-4 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:px-[15px] transition-all placeholder-transparent bg-transparent"
                  placeholder="Email or phone"
                />
                <label
                  htmlFor="email"
                  className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none"
                >
                  Email address
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
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div className="mb-10 mt-2">
              <a href="/forgot-password" className="text-sm font-medium text-[#D60041] hover:bg-red-50 px-2 py-1.5 -ml-2 rounded-md transition-colors inline-block">
                Forgot password?
              </a>
            </div>

            <p className="text-sm text-gray-600 mb-10 leading-relaxed pr-4">
              Not your computer? Use a private browsing window to sign in. <a href="#" className="text-[#D60041] font-medium hover:underline">Learn more</a>
            </p>

            <div className="flex flex-col gap-4 mt-8">
              <button
                type="button"
                onClick={() => window.location.href = 'http://localhost:8000/auth/google/login'}
                className="w-full flex items-center justify-center gap-2 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 text-sm font-medium px-6 py-2.5 rounded-full transition-colors"
              >
                <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" alt="Google Logo" className="w-5 h-5" />
                Sign in with Google
              </button>

              <div className="flex flex-col-reverse sm:flex-row justify-between items-center gap-4 sm:gap-0">
                <a
                  href="/register"
                  className="text-sm font-medium text-[#D60041] hover:bg-red-50 px-3 py-2 rounded-md transition-colors w-full sm:w-auto text-center"
                >
                  Create account
                </a>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full sm:w-auto bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-medium px-6 py-2.5 rounded-full transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center min-w-[100px]"
                >
                  {loading ? <Loader2 className="animate-spin h-5 w-5" /> : "Next"}
                </button>
              </div>
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

export default Login;