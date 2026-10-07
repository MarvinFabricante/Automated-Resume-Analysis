import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { setCredentials } from '../../../redux/slices/authSlice';
import { XCircle, ArrowLeft } from 'lucide-react';

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const dispatch = useDispatch();
  const [error] = useState(() => {
    const err = searchParams.get('error');
    return err ? decodeURIComponent(err) : null;
  });

  useEffect(() => {
    if (error) return;

    const token = searchParams.get('token');
    const role = searchParams.get('role');
    const email = searchParams.get('email');
    const fullname = searchParams.get('fullname');
    const userId = searchParams.get('user_id');
    const picture = searchParams.get('picture');

    if (token && role) {
      // Store auth data (cleanly overwrite any previous session)
      localStorage.setItem('token', token);
      localStorage.setItem('role', role);
      localStorage.setItem('saved_email', email || '');
      localStorage.setItem('fullname', fullname || '');
      localStorage.setItem('user_id', userId || '');
      if (picture) {
        localStorage.setItem('profile_image_url', picture);
      }

      dispatch(setCredentials({
        user: email || fullname || 'Google User',
        role: role,
        profileImageUrl: picture || null,
      }));

      // Redirect based on role
      const normRole = (role || '').toUpperCase();
      if (normRole === 'ADMIN') {
        window.location.href = '/admin/dashboard';
      } else if (normRole === 'HR') {
        window.location.href = '/hr/dashboard';
      } else {
        window.location.href = '/candidate/dashboard';
      }
    } else {
      // Direct access with no token: if already authenticated, go to dashboard, else login
      const existingToken = localStorage.getItem('token');
      const existingRole = (localStorage.getItem('role') || '').toUpperCase();
      if (existingToken && existingRole) {
        if (existingRole === 'ADMIN') window.location.href = '/admin/dashboard';
        else if (existingRole === 'HR') window.location.href = '/hr/dashboard';
        else window.location.href = '/candidate/dashboard';
      } else {
        window.location.href = '/login';
      }
    }
  }, [searchParams, dispatch, error]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F0F4F9] px-4">
        <div className="bg-white rounded-3xl shadow-2xl w-full max-w-sm p-8 text-center animate-in zoom-in-95 duration-200">
          <div className="w-16 h-16 bg-red-50 rounded-full flex items-center justify-center mx-auto mb-5">
            <XCircle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-xl font-normal text-gray-900 mb-2 tracking-tight">Already Logged In</h3>
          <p className="text-sm text-gray-600 mb-8 px-2 leading-relaxed">
            {error}
          </p>
          <button
            onClick={() => window.location.href = '/'}
            className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium py-2.5 px-4 rounded-full transition-all duration-200 text-sm flex items-center justify-center gap-2"
          >
            <ArrowLeft size={16} />
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F0F4F9]">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-[#D60041] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-600 font-medium">Signing you in with Google...</p>
      </div>
    </div>
  );
};

export default GoogleCallback;
