import { Routes, Route } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import { useSelector } from 'react-redux';
import { useEffect } from 'react';

import ProtectedRoute from './ProtectedRoutes';
import ScrollToTop from './components/layout/ScrollToTop';

import Login from './pages/publicPages/authenticationPages/Login';
import Register from './pages/publicPages/authenticationPages/Register';
import ForgotPassword from './pages/publicPages/authenticationPages/ForgotPassword';
import ResetPassword from './pages/publicPages/authenticationPages/ResetPassword';
import GoogleCallback from './pages/publicPages/authenticationPages/GoogleCallback';

import LandingPage from './pages/publicPages/site/LandingPage';
import AboutPage from './pages/publicPages/site/AboutPage';
import CareersPage from './pages/publicPages/site/CareersPage';

import SmartUploadPage from './pages/publicPages/jobApplicationPages/SmartUploadPage';
import ApplicationForm from './pages/publicPages/jobApplicationPages/ApplicationForm';
import ApplyForJobPage from './pages/publicPages/jobApplicationPages/ApplyForJobPage';
import PreviewAndVerifyPage from './pages/publicPages/jobApplicationPages/PreviewAndVerify';
import SubmissionSuccessPage from './pages/publicPages/jobApplicationPages/SubmissionSuccess';
import JobDetailsPage from './pages/publicPages/jobApplicationPages/JobDetailsPage';
import SmartMatchResult from './pages/publicPages/jobApplicationPages/SmartMatchResult';

import ApplicationTracking from './pages/candidate/ApplicationTracking';
import CandidateDashboard from './pages/candidate/CandidateDashboard';
import FindJob from './pages/candidate/FindJob';
import CandidateSmartUpload from './pages/candidate/CandidateSmartUpload';
import CandidatePreviewAndVerify from './pages/candidate/CandidatePreviewAndVerify';
import CandidateProfileForm from './pages/candidate/CandidateProfileForm';
import CandidateSmartMatchResult from './pages/candidate/CandidateSmartMatchResult';

import HRDashboard from './pages/hr/HRDashboard';

import ScreeningPortal from './pages/hr/ScreeningPortal';
import CompareCandidates from './pages/hr/CompareCandidates';

import AdminDashboard from './pages/admin/AdminDashboard';
import UsersPage from './pages/admin/Users';
import JobManagement from './pages/admin/JobManagement';
import SystemSettings from './pages/admin/SystemSettings';
import PerformanceStats from './pages/admin/PerformanceStats';

import AccountSettings from './pages/shared/AccountSettings';
import ViewProfile from './pages/shared/ViewProfile';
import MessagesPage from './pages/common/MessagesPage';

const App = () => {
  const theme = useSelector((state) => state.theme.theme);

  useEffect(() => {
    const applyTheme = (currentTheme) => {
      const root = window.document.documentElement;
      root.classList.remove('light', 'dark');

      if (currentTheme === 'system') {
        const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (systemPrefersDark) {
          root.classList.add('dark');
        } else {
          root.classList.add('light');
        }
      } else {
        root.classList.add(currentTheme);
      }
    };

    applyTheme(theme);

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => applyTheme('system');
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);

  return (
    <HelmetProvider>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/auth/callback" element={<GoogleCallback />} />
        <Route path="/" element={<LandingPage />} />
        <Route path="/careerspage" element={<CareersPage />} />
        <Route path="/aboutpage" element={<AboutPage />} />

        <Route path="/smart-upload" element={<SmartUploadPage />} />
        <Route path="/smart-matches" element={<SmartMatchResult />} />
        <Route path="/apply/:jobId" element={<ApplyForJobPage />} />
        <Route path="/job-details/:jobId" element={<JobDetailsPage />} />
        <Route path="/preview-and-verify/:jobId" element={<PreviewAndVerifyPage />} />
        <Route path="/applicationform/:jobId" element={<ApplicationForm />} />
        <Route path="/submissionsuccess/:jobId" element={<SubmissionSuccessPage />} />

        <Route element={<ProtectedRoute allowedRole="ADMIN" />}>
          <Route path="/admin">
            <Route path="dashboard" element={<AdminDashboard />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="jobmanagement" element={<JobManagement />} />
            <Route path="system-config" element={<SystemSettings />} />
            <Route path="performance" element={<PerformanceStats />} />
            <Route path="messages" element={<MessagesPage />} />
            <Route path="settings" element={<AccountSettings />} />
            <Route path="profile" element={<ViewProfile />} />
          </Route>
        </Route>

        <Route element={<ProtectedRoute allowedRole="HR" />}>
          <Route path="/hr">
            <Route path="dashboard" element={<HRDashboard />} />
            <Route path="screeningportal" element={<ScreeningPortal />} />
            <Route path="comparecandidates" element={<CompareCandidates />} />

            <Route path="messages" element={<MessagesPage />} />
            <Route path="settings" element={<AccountSettings />} />
            <Route path="profile" element={<ViewProfile />} />
          </Route>
        </Route>

        <Route element={<ProtectedRoute allowedRole="CANDIDATE" />}>
          <Route path="/candidate">
            <Route path="dashboard" element={<CandidateDashboard />} />
            <Route path="findjobs" element={<FindJob />} />
            <Route path="applicationtracking/:id" element={<ApplicationTracking />} />
            <Route path="applicationtracking" element={<ApplicationTracking />} />
            <Route path="messages" element={<MessagesPage />} />
            <Route path="settings" element={<AccountSettings />} />
            <Route path="profile" element={<ViewProfile />} />
            <Route path="upload-resume/:jobId" element={<CandidateSmartUpload />} />
            <Route path="upload-resume" element={<CandidateSmartUpload />} />
            <Route path="preview-profile/:jobId" element={<CandidatePreviewAndVerify />} />
            <Route path="preview-profile" element={<CandidatePreviewAndVerify />} />
            <Route path="update-profile/:jobId" element={<CandidateProfileForm />} />
            <Route path="update-profile" element={<CandidateProfileForm />} />
            <Route path="smart-matches" element={<CandidateSmartMatchResult />} />
          </Route>
        </Route>
      </Routes>
    </HelmetProvider>
  )
}

export default App;