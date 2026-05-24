import React, { useState } from 'react';
import authService from '../../../services/authService';
import { Helmet } from 'react-helmet-async';
import {
  Mail,
  Loader2,
  CheckCircle2,
  XCircle,
  ArrowLeft
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [modalState, setModalState] = useState({
    isOpen: false,
    type: 'success',
    title: '',
    message: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await authService.forgotPassword(email);

      setModalState({
        isOpen: true,
        type: 'success',
        title: 'Recovery Email Sent',
        message: `If an account exists for ${email}, a password reset link has been sent. Please check your inbox and spam folder.`
      });
    } catch (err) {
      setModalState({
        isOpen: true,
        type: 'error',
        title: 'Error',
        message: err.response?.data?.detail || "Could not send reset email. Please try again."
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-8 bg-[#F0F4F9] font-sans antialiased text-gray-800">
      <Helmet>
        <title>Account Recovery - Mariwasa Portal</title>
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
                  if (modalState.type === 'success') {
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
                {modalState.type === 'success' ? 'Back to Login' : 'Try Again'}
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
            Account recovery
          </h1>
          <p className="text-base font-normal text-gray-800 mb-8 md:mb-0 leading-relaxed">
            Enter the email address associated with your account and we'll send you a link to reset your password.
          </p>
        </div>

        <div className="w-full md:w-[55%] p-10 md:p-14 flex flex-col justify-center">
          <form onSubmit={handleSubmit} className="w-full max-w-[400px] mx-auto md:mx-0 md:ml-auto">

            <div className="mb-10">
              <div className="relative">
                <input
                  type="email"
                  id="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="peer w-full px-4 py-3.5 border border-gray-400 rounded-[4px] text-base text-gray-900 focus:outline-none focus:border-[#D60041] focus:border-2 focus:py-[13px] focus:px-[15px] transition-all placeholder-transparent bg-transparent"
                  placeholder="Email"
                />
                <label
                  htmlFor="email"
                  className="absolute left-3.5 -top-2.5 bg-white px-1 text-xs font-normal text-gray-600 peer-placeholder-shown:text-base peer-placeholder-shown:text-gray-600 peer-placeholder-shown:top-3.5 peer-focus:-top-2.5 peer-focus:text-xs peer-focus:text-[#D60041] transition-all cursor-text pointer-events-none"
                >
                  Email address
                </label>
              </div>
            </div>

            <p className="text-sm text-gray-600 mb-10 leading-relaxed pr-4">
              Make sure you have access to this email. If you've forgotten your email too, please contact support.
            </p>

            <div className="flex flex-col-reverse sm:flex-row justify-between items-center gap-4 sm:gap-0 mt-8">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="flex items-center gap-2 text-sm font-medium text-[#D60041] hover:bg-red-50 px-3 py-2 rounded-md transition-colors w-full sm:w-auto justify-center sm:justify-start"
              >
                <ArrowLeft size={16} />
                Back to sign in
              </button>
              <button
                type="submit"
                disabled={loading}
                className="w-full sm:w-auto bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-medium px-8 py-2.5 rounded-full transition-colors disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center min-w-[120px]"
              >
                {loading ? <Loader2 className="animate-spin h-5 w-5" /> : "Send link"}
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

export default ForgotPassword;
