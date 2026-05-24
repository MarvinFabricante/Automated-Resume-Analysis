import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import authService from '../../../services/authService';
import { Helmet } from 'react-helmet-async';
import {
  Lock,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  XCircle,
  ArrowLeft,
  KeyRound
} from 'lucide-react';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token');

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'success',
    title: '',
    message: ''
  });

  useEffect(() => {
    if (!token) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Invalid Link',
        message: 'The password reset link is invalid or has expired. Please request a new one.'
      });
    }
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Mismatch',
        message: 'Passwords do not match. Please try again.'
      });
      return;
    }

    setLoading(true);

    try {
      await authService.resetPassword(token, password);

      setModalState({
        isOpen: true,
        type: 'success',
        title: 'Password Updated',
        message: 'Your password has been reset successfully. You can now sign in with your new password.'
      });
    } catch (err) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Reset Failed',
        message: err.response?.data?.detail || "Could not reset password. The link may have expired."
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-8 bg-[#F0F4F9] font-sans antialiased text-gray-800">
      <Helmet>
        <title>Reset Password - Mariwasa Portal</title>
      </Helmet>

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
                  if (modalState.type === 'success' || modalState.title === 'Invalid Link') {
                    navigate('/login');
                  } else {
                    setModalState({ ...modalState, isOpen: false });
                  }
                }}
                className={`w-full font-medium py-2.5 px-4 rounded-full transition-all duration-200 text-sm ${modalState.type === 'success'
                  ? 'bg-[#D60041] hover:bg-[#b50037] text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
                  }`}
              >
                {modalState.type === 'success' ? 'Go to Login' : 'Try Again'}
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
            Reset password
          </h1>
          <p className="text-base font-normal text-gray-800 mb-8 md:mb-0 leading-relaxed">
            Create a new, strong password for your account. Make sure it's something you don't use elsewhere.
          </p>
        </div>

        <div className="w-full md:w-[55%] p-10 md:p-14 flex flex-col justify-center">
          <form onSubmit={handleSubmit} className="w-full max-w-[400px] mx-auto md:mx-0 md:ml-auto">
            
            <div className="space-y-6 mb-10">
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  id="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="peer w-full pl-4 pr-12 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:pl-[15px] transition-all placeholder-transparent bg-transparent"
                  placeholder="New password"
                />
                <label
                  htmlFor="password"
                  className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none"
                >
                  New password
                </label>
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600 hover:text-gray-900 p-1 rounded-full hover:bg-gray-100 transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>

              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  id="confirmPassword"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="peer w-full pl-4 pr-12 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:pl-[15px] transition-all placeholder-transparent bg-transparent"
                  placeholder="Confirm new password"
                />
                <label
                  htmlFor="confirmPassword"
                  className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none"
                >
                  Confirm new password
                </label>
              </div>
            </div>

            <div className="flex flex-col-reverse sm:flex-row justify-between items-center gap-4 sm:gap-0">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:bg-gray-100 px-3 py-2 rounded-md transition-colors w-full sm:w-auto justify-center sm:justify-start"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || !token}
                className="w-full sm:w-auto bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-medium px-10 py-2.5 rounded-full transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center min-w-[140px]"
              >
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : "Reset password"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ResetPassword;
