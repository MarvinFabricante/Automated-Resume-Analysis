import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import { setCredentials } from '../../../redux/slices/authSlice';

const GoogleCallback = () => {
  const [searchParams] = useSearchParams();
  const dispatch = useDispatch();

  useEffect(() => {
    const token = searchParams.get('token');
    const role = searchParams.get('role');
    const fullname = searchParams.get('fullname');
    const userId = searchParams.get('user_id');
    const picture = searchParams.get('picture');

    if (token && role) {
      // Store auth data
      localStorage.setItem('token', token);
      localStorage.setItem('fullname', fullname || '');
      localStorage.setItem('user_id', userId || '');

      dispatch(setCredentials({
        user: fullname || 'Google User',
        role: role,
        profileImageUrl: picture || null,
      }));

      // Redirect based on role
      if (role.toUpperCase() === 'ADMIN') {
        window.location.href = '/admin/dashboard';
      } else if (role.toUpperCase() === 'HR') {
        window.location.href = '/hr/dashboard';
      } else {
        window.location.href = '/candidate/dashboard';
      }
    } else {
      // If no token, redirect to login
      window.location.href = '/login';
    }
  }, [searchParams, dispatch]);

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
