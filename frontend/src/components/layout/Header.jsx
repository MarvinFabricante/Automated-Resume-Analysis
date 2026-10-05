import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  ChevronDown, LayoutDashboard, Users, Database, ShieldCheck, LogOut,
  Settings, Menu, X, FileText, Search, User, Building2, Info, Briefcase, LogIn, UserPlus,
  Bell, Clock, CheckCircle2, AlertCircle, MessageSquare, ChevronRight,
  TrendingUp, Zap, Radio, Edit3, Sun, Moon, Monitor, Calendar, Home
} from 'lucide-react';
import NotificationDropdown from './NotificationDropdown';
import notificationService from '../../services/notificationService';
import profileService from '../../services/profileService';
import { useSelector, useDispatch } from 'react-redux';
import { logout as logoutAction, updateProfileImage } from '../../redux/slices/authSlice';
import { setNotifications, addNotification, markAllRead as markAllReadAction } from '../../redux/slices/notificationSlice';
import { closeSidebar, toggleSidebar } from '../../redux/slices/uiSlice';
import { setTheme } from '../../redux/slices/themeSlice';
import { WS_BASE_URL } from '../../services/api';
import logo from '../../assets/logo.png';

const BRAND_RED = "#D60041";

const Header = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isThemeOpen, setIsThemeOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  const dropdownRef = useRef(null);
  const notificationsRef = useRef(null);
  const themeRef = useRef(null);
  const mobileMenuRef = useRef(null);
  const hamburgerBtnRef = useRef(null);

  const dispatch = useDispatch();
  const { user: userEmail, role: userRole, profileImageUrl } = useSelector(state => state.auth);
  const { notifications, unreadCount } = useSelector(state => state.notifications);
  const { isSidebarOpen } = useSelector(state => state.ui);
  const currentTheme = useSelector(state => state.theme?.theme || 'system');

  const isCandidateRole = userRole === 'CANDIDATE';
  const isHRRole = userRole === 'HR';
  const isAdminRole = userRole === 'ADMIN';
  const isGuest = userRole === 'Guest';

  useEffect(() => {
    if (window.innerWidth < 1024) {
      dispatch(closeSidebar());
    }
  }, [dispatch]);

  useEffect(() => {
    let ws;
    const fetchNotifications = async () => {
      if (isAdminRole || isHRRole) {
        try {
          const res = await notificationService.getNotifications(userRole, userEmail);
          const formatted = res.data.map(n => {
            let iconName = 'AlertCircle';
            let bgColor = 'bg-slate-50';
            let textColor = 'text-slate-600';
            let tag = null;
            let tagColor = null;

            if (n.type === 'registration') {
              iconName = 'UserPlus';
              bgColor = 'bg-blue-50';
              textColor = 'text-blue-600';
            } else if (n.type === 'application' || n.type === 'application_update') {
              iconName = 'Briefcase';
              bgColor = 'bg-pink-50';
              textColor = 'text-[#D60041]';
              tag = 'Update';
              tagColor = 'bg-pink-100 text-[#D60041]';
            } else if (n.type === 'upload') {
              iconName = 'FileText';
              bgColor = 'bg-orange-50';
              textColor = 'text-orange-600';
            } else if (n.type === 'hr_registration') {
              iconName = 'ShieldCheck';
              bgColor = 'bg-indigo-50';
              textColor = 'text-indigo-600';
              tag = 'System';
              tagColor = 'bg-indigo-100 text-indigo-700';
            } else if (n.type === 'job_creation') {
              iconName = 'Zap';
              bgColor = 'bg-green-50';
              textColor = 'text-green-600';
            } else if (n.type === 'job_update') {
              iconName = 'Edit3';
              bgColor = 'bg-amber-50';
              textColor = 'text-amber-600';
            } else if (n.type === 'candidate_login') {
              iconName = 'Radio';
              bgColor = 'bg-green-50';
              textColor = 'text-green-600';
            } else if (n.type === 'hr_login') {
              iconName = 'Radio';
              bgColor = 'bg-purple-50';
              textColor = 'text-purple-600';
            }

            const created = new Date(n.created_at);
            const now = new Date();
            const diffMs = now - created;
            const diffMins = Math.floor(diffMs / 60000);
            let timeStr = 'just now';
            if (diffMins > 0 && diffMins < 60) timeStr = `${diffMins}m ago`;
            else if (diffMins >= 60 && diffMins < 1440) timeStr = `${Math.floor(diffMins / 60)}h ago`;
            else if (diffMins >= 1440) timeStr = `${Math.floor(diffMins / 1440)}d ago`;

            return {
              id: n.id,
              title: n.title,
              desc: isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${n.message}` : n.message,
              time: timeStr,
              type: n.type,
              icon: iconName,
              bgColor,
              textColor,
              tag,
              tagColor,
              read: n.is_read
            };
          });
          dispatch(setNotifications(formatted));
        } catch (err) {
          console.error("Failed to fetch notifications:", err);
        }
      }

      if (isCandidateRole) {
        try {
          const res = await notificationService.getNotifications(userRole, userEmail);
          const formatted = res.data.map(n => {
            let iconName = 'Briefcase';
            let bgColor = 'bg-blue-50';
            let textColor = 'text-blue-600';
            let tag = 'Update';
            let tagColor = 'bg-blue-100 text-blue-700';

            if (n.type === 'schedule') {
              iconName = 'MessageSquare';
              bgColor = 'bg-pink-50';
              textColor = 'text-[#D60041]';
              tag = 'Interview';
              tagColor = 'bg-pink-100 text-[#D60041]';
            } else if (n.type === 'job') {
              iconName = 'TrendingUp';
              bgColor = 'bg-green-50';
              textColor = 'text-green-600';
              tag = 'Match';
              tagColor = 'bg-green-100 text-green-700';
            } else if (n.type === 'application_update') {
              if (n.title.includes('Accepted') || n.title.includes('🎉')) {
                bgColor = 'bg-emerald-50';
                textColor = 'text-emerald-600';
                tag = 'Accepted';
                tagColor = 'bg-emerald-100 text-emerald-700';
              } else if (n.title.includes('Rejected') || n.message?.includes('regret') || n.message?.includes('other candidates') || n.desc?.includes('regret') || n.desc?.includes('other candidates')) {
                bgColor = 'bg-rose-50';
                textColor = 'text-rose-600';
                tag = 'Rejected';
                tagColor = 'bg-rose-100 text-rose-700';
              } else {
                bgColor = 'bg-pink-50';
                textColor = 'text-[#D60041]';
                tag = 'Update';
                tagColor = 'bg-pink-100 text-[#D60041]';
              }
            }

            const created = new Date(n.created_at);
            const now = new Date();
            const diffMs = now - created;
            const diffMins = Math.floor(diffMs / 60000);
            let timeStr = 'just now';
            if (diffMins > 0 && diffMins < 60) timeStr = `${diffMins}m ago`;
            else if (diffMins >= 60 && diffMins < 1440) timeStr = `${Math.floor(diffMins / 60)}h ago`;
            else if (diffMins >= 1440) timeStr = `${Math.floor(diffMins / 1440)}d ago`;

            return {
              id: n.id,
              title: n.title,
              desc: isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${n.message}` : n.message,
              time: timeStr,
              type: n.type,
              icon: iconName,
              bgColor,
              textColor,
              tag,
              tagColor,
              read: n.is_read
            };
          });

          dispatch(setNotifications(formatted));
        } catch (err) {
          console.error("Failed to fetch candidate notifications:", err);
        }
      }
    };

    fetchNotifications();

    if (isAdminRole || isHRRole || isCandidateRole) {
      ws = new WebSocket(`${WS_BASE_URL}/notifications/ws?role=${userRole}&email=${userEmail}`);
      ws.onmessage = (event) => {
        try {
          const n = JSON.parse(event.data);
          let iconName = 'AlertCircle';
          let bgColor = 'bg-slate-50';
          let textColor = 'text-slate-600';
          let tag = null;
          let tagColor = null;

          if (isCandidateRole) {
            iconName = 'Briefcase';
            bgColor = 'bg-blue-50';
            textColor = 'text-blue-600';
            tag = 'Update';
            tagColor = 'bg-blue-100 text-blue-700';

            if (n.type === 'schedule') {
              iconName = 'MessageSquare';
              bgColor = 'bg-pink-50';
              textColor = 'text-[#D60041]';
              tag = 'Interview';
              tagColor = 'bg-pink-100 text-[#D60041]';
            } else if (n.type === 'job') {
              iconName = 'TrendingUp';
              bgColor = 'bg-green-50';
              textColor = 'text-green-600';
              tag = 'Match';
              tagColor = 'bg-green-100 text-green-700';
            } else if (n.type === 'application_update') {
              if (n.title.includes('Accepted') || n.title.includes('🎉')) {
                bgColor = 'bg-emerald-50';
                textColor = 'text-emerald-600';
                tag = 'Accepted';
                tagColor = 'bg-emerald-100 text-emerald-700';
              } else if (n.title.includes('Rejected') || n.message?.includes('regret') || n.message?.includes('other candidates')) {
                bgColor = 'bg-rose-50';
                textColor = 'text-rose-600';
                tag = 'Rejected';
                tagColor = 'bg-rose-100 text-rose-700';
              } else {
                bgColor = 'bg-pink-50';
                textColor = 'text-[#D60041]';
                tag = 'Update';
                tagColor = 'bg-pink-100 text-[#D60041]';
              }
            }
          } else {
            // HR / Admin
            if (n.type === 'registration') { iconName = 'UserPlus'; bgColor = 'bg-blue-50'; textColor = 'text-blue-600'; }
            else if (n.type === 'application' || n.type === 'application_update') { iconName = 'Briefcase'; bgColor = 'bg-pink-50'; textColor = 'text-[#D60041]'; tag = 'Update'; tagColor = 'bg-pink-100 text-[#D60041]'; }
            else if (n.type === 'upload') { iconName = 'FileText'; bgColor = 'bg-orange-50'; textColor = 'text-orange-600'; }
            else if (n.type === 'hr_registration') { iconName = 'ShieldCheck'; bgColor = 'bg-indigo-50'; textColor = 'text-indigo-600'; tag = 'System'; tagColor = 'bg-indigo-100 text-indigo-700'; }
            else if (n.type === 'job_creation') { iconName = 'Zap'; bgColor = 'bg-green-50'; textColor = 'text-green-600'; }
            else if (n.type === 'job_update') { iconName = 'Edit3'; bgColor = 'bg-amber-50'; textColor = 'text-amber-600'; }
            else if (n.type === 'candidate_login') { iconName = 'Radio'; bgColor = 'bg-green-50'; textColor = 'text-green-600'; }
            else if (n.type === 'hr_login') { iconName = 'Radio'; bgColor = 'bg-purple-50'; textColor = 'text-purple-600'; }
          }

          const desc = isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${n.message}` : n.message;
          const formattedNewNotif = {
            id: n.id, title: n.title, desc, time: 'just now', type: n.type, icon: iconName, bgColor, textColor, tag, tagColor, read: n.is_read
          };

          dispatch(addNotification(formattedNewNotif));
          setPulse(true);
          setTimeout(() => setPulse(false), 2000);
        } catch (err) { console.error("Error processing websocket message:", err); }
      };
    }

    return () => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.close();
    };
  }, [userRole, dispatch]);

  // Sync profile image from database on mount
  useEffect(() => {
    const syncProfileImage = async () => {
      const userId = localStorage.getItem('user_id');
      if (!userId || isGuest) return;

      try {
        const response = await profileService.getProfile(userRole, userId);
        const data = response.data;
        if (data.profile_image_url && data.profile_image_url !== profileImageUrl) {
          dispatch(updateProfileImage(data.profile_image_url));
        }
      } catch (err) {
        console.error("Failed to sync profile image from database:", err);
      }
    };

    syncProfileImage();
  }, [isAdminRole, isHRRole, isGuest, dispatch]);

  const handleMarkAllRead = async () => {
    if (!isGuest) {
      try { await notificationService.markAllRead(userRole, userEmail); }
      catch (err) { console.error("Failed to mark all read:", err); }
    }
    dispatch(markAllReadAction());
  };

  const isApplicationPage =
    location.pathname.includes('/job-details/') ||
    location.pathname.includes('/apply/') ||
    location.pathname.includes('/smart-upload') ||
    location.pathname.includes('/preview-and-verify/') ||
    location.pathname.includes('/applicationform/') ||
    location.pathname.includes('/submissionsuccess/');

  const isPublicSitePage =
    location.pathname === '/' ||
    location.pathname === '/aboutpage' ||
    location.pathname === '/aboutpage/' ||
    location.pathname === '/careerspage' ||
    location.pathname === '/careerspage/';

  const handleLogout = () => {
    dispatch(logoutAction());
    navigate('/');
    window.location.reload();
  };

  // Close menus on route navigation
  useEffect(() => {
    setIsMobileMenuOpen(false);
    setIsProfileOpen(false);
    setIsNotificationsOpen(false);
    setIsThemeOpen(false);
  }, [location.pathname]);

  // Handle escape key and window resize
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false);
        setIsProfileOpen(false);
        setIsNotificationsOpen(false);
        setIsThemeOpen(false);
      }
    };
    const handleResize = () => {
      if (window.innerWidth >= 1024) {
        setIsMobileMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  // Handle click outside to close dropdowns and mobile menu
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) setIsProfileOpen(false);
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) setIsNotificationsOpen(false);
      if (themeRef.current && !themeRef.current.contains(event.target)) setIsThemeOpen(false);
      if (
        isMobileMenuOpen &&
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(event.target) &&
        hamburgerBtnRef.current &&
        !hamburgerBtnRef.current.contains(event.target)
      ) {
        setIsMobileMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isMobileMenuOpen]);

  const getNavItems = () => {
    if (isPublicSitePage) return [
      { label: 'Home', path: '/', icon: <Home size={18} /> },
      { label: 'About', path: '/aboutpage', icon: <Info size={18} /> },
      { label: 'Careers', path: '/careerspage', icon: <Briefcase size={18} /> },
    ];
    if (isAdminRole) return [
      { label: 'Dashboard', path: '/admin/dashboard', icon: <LayoutDashboard size={18} /> },
      { label: 'User Management', path: '/admin/users', icon: <Users size={18} /> },
      { label: 'Jobs', path: '/admin/jobmanagement', icon: <Settings size={18} /> },
    ];
    if (isHRRole) return [
      { label: 'Dashboard', path: '/hr/dashboard', icon: <Building2 size={18} /> },
      { label: 'Screening', path: '/hr/screeningportal', icon: <User size={18} /> },
      { label: 'Scheduling', path: '/hr/scheduling', icon: <Calendar size={18} /> },
    ];
    if (isCandidateRole) return [
      { label: 'Dashboard', path: '/candidate/dashboard', icon: <LayoutDashboard size={18} /> },
      { label: 'Find Jobs', path: '/candidate/findjobs', icon: <Search size={18} /> },
      { label: 'Applications', path: '/candidate/applicationtracking', icon: <FileText size={18} /> },
    ];
    return [
      { label: 'Home', path: '/', icon: <Home size={18} /> },
      { label: 'About', path: '/aboutpage', icon: <Info size={18} /> },
      { label: 'Careers', path: '/careerspage', icon: <Briefcase size={18} /> },
    ];
  };

  const navItems = getNavItems();

  return (
    <>
    <header className="relative bg-white dark:bg-slate-900 border-b border-gray-100 dark:border-slate-800 px-4 sm:px-6 md:px-10 py-3 sm:py-4 sticky top-0 z-50 font-sans shadow-sm transition-colors duration-200">
      <div className="max-w-[1400px] mx-auto flex items-center justify-between">

        <div className="flex items-center space-x-2 sm:space-x-4 shrink-0">
          <button
            ref={hamburgerBtnRef}
            className={`lg:hidden p-2 sm:p-2.5 rounded-xl transition-all active:scale-95 -ml-1 ${
              isMobileMenuOpen
                ? 'bg-red-50 text-[#D60041] dark:bg-pink-950/40 dark:text-[#ff386e]'
                : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white'
            }`}
            onClick={() => {
              if (!isGuest && !isPublicSitePage && !isApplicationPage) {
                dispatch(isSidebarOpen ? closeSidebar() : toggleSidebar());
              } else {
                setIsMobileMenuOpen(!isMobileMenuOpen);
              }
            }}
            aria-label={isMobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
            aria-expanded={isMobileMenuOpen}
          >
            {isMobileMenuOpen || (isSidebarOpen && !isGuest && !isPublicSitePage && !isApplicationPage) ? (
              <X size={22} className="transition-transform duration-200" />
            ) : (
              <Menu size={22} className="transition-transform duration-200" />
            )}
          </button>

          <div className="flex items-center space-x-2 sm:space-x-4 cursor-pointer group" onClick={() => navigate(isGuest ? '/' : location.pathname)}>
            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center overflow-hidden transition-all duration-300 ${!isGuest && 'group-hover:shadow-[0_0_15px_rgba(209,0,67,0.3)]'}`}>
              <img src={logo} alt="logo" className="w-full h-full object-contain" />
            </div>
            <div>
              <h1 className="text-sm sm:text-base font-black tracking-tight text-gray-900 leading-tight">
                {isPublicSitePage ? "Mariwasa" : isAdminRole ? "Admin Portal" : isHRRole ? "HR Portal" : isCandidateRole ? "Candidate Portal" : "Mariwasa"}
              </h1>
              <p className={`text-[9px] sm:text-[10px] font-bold uppercase tracking-widest mt-0.5 ${isGuest || isPublicSitePage ? 'text-gray-400' : 'text-[#D60041]'}`}>
                {isGuest || isPublicSitePage ? "Siam Ceramics Inc." : "Resume Analysis System"}
              </p>
            </div>
          </div>
        </div>

        <div className={`hidden lg:flex flex-1 items-center ${(isGuest || isPublicSitePage) || isApplicationPage ? 'justify-end pr-8' : 'justify-center'}`}>
          {!isApplicationPage && (isGuest || isPublicSitePage) && (
            <nav className="flex items-center space-x-1 bg-gray-50/50 p-1 rounded-2xl border border-gray-100">
              {navItems.map((item, index) => {
                const isActive = location.pathname === item.path;
                return (
                  <button
                    key={index}
                    onClick={() => navigate(item.path)}
                    className={`px-5 py-2.5 rounded-xl flex items-center space-x-2.5 transition-all duration-300 group ${isActive ? 'bg-white text-[#D60041] shadow-sm ring-1 ring-gray-200/50' : 'text-gray-500 hover:bg-gray-100/50 hover:text-gray-900'}`}
                  >
                    <span className={`transition-transform duration-300 ${isActive ? 'text-[#D60041]' : 'text-gray-400 group-hover:text-gray-600'} ${!isActive && 'group-hover:scale-110'}`}>
                      {item.icon}
                    </span>
                    <span className="text-sm font-bold tracking-tight">{item.label}</span>
                  </button>
                );
              })}
            </nav>
          )}
        </div>

        <div className="flex items-center space-x-1.5 sm:space-x-4 relative shrink-0" ref={dropdownRef}>
          {/* Theme Toggle - Always Visible */}
          <div className="relative mr-0 sm:mr-2" ref={themeRef}>
            <button
              onClick={() => setIsThemeOpen(!isThemeOpen)}
              className={`w-9 h-9 sm:w-11 sm:h-11 rounded-xl sm:rounded-2xl flex items-center justify-center transition-all duration-300 border ${isThemeOpen ? 'bg-slate-900 border-slate-900 shadow-xl' : 'bg-gray-50/50 border-gray-100 hover:bg-white hover:border-pink-100 hover:shadow-md hover:scale-105 active:scale-95'}`}
              aria-label="Toggle theme"
            >
              {currentTheme === 'light' ? (
                <Sun size={18} className={isThemeOpen ? 'text-white' : 'text-gray-500'} />
              ) : currentTheme === 'dark' ? (
                <Moon size={18} className={isThemeOpen ? 'text-white' : 'text-gray-500'} />
              ) : (
                <Monitor size={18} className={isThemeOpen ? 'text-white' : 'text-gray-500'} />
              )}
            </button>
            
            {isThemeOpen && (
              <div className="absolute right-0 mt-3 w-40 bg-white border border-gray-100 rounded-2xl shadow-xl py-2 z-[60] animate-in fade-in slide-in-from-top-2 duration-200">
                <button 
                  onClick={() => { dispatch(setTheme('light')); setIsThemeOpen(false); }}
                  className={`w-full flex items-center space-x-3 px-4 py-2 text-sm font-bold transition-colors ${currentTheme === 'light' ? 'text-[#D60041] bg-pink-50' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}
                >
                  <Sun size={16} /> <span>Light</span>
                </button>
                <button 
                  onClick={() => { dispatch(setTheme('dark')); setIsThemeOpen(false); }}
                  className={`w-full flex items-center space-x-3 px-4 py-2 text-sm font-bold transition-colors ${currentTheme === 'dark' ? 'text-[#D60041] bg-pink-50' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}
                >
                  <Moon size={16} /> <span>Dark</span>
                </button>
                <button 
                  onClick={() => { dispatch(setTheme('system')); setIsThemeOpen(false); }}
                  className={`w-full flex items-center space-x-3 px-4 py-2 text-sm font-bold transition-colors ${currentTheme === 'system' ? 'text-[#D60041] bg-pink-50' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}
                >
                  <Monitor size={16} /> <span>System</span>
                </button>
              </div>
            )}
          </div>

          {isApplicationPage ? (
            <button
              onClick={() => navigate('/careerspage')}
              className="hidden lg:flex items-center space-x-2 bg-white border border-gray-200 text-gray-600 px-6 py-2.5 rounded-full text-sm font-bold hover:bg-red-50 hover:text-[#D60041] hover:border-pink-200 transition-all shadow-sm active:scale-95"
            >
              <X size={18} />
              <span>Cancel Application</span>
            </button>
          ) : isGuest ? (
            <div className="hidden lg:block relative group">
              <button className="flex items-center space-x-2 bg-[#D60041] text-white px-6 py-3 rounded-full text-sm font-bold hover:bg-[#b50037] transition-all shadow-md shadow-pink-200">
                <span>Access Portal</span>
                <ChevronDown size={16} className="group-hover:rotate-180 transition-transform duration-300" />
              </button>
              <div className="absolute right-0 mt-3 w-64 bg-white border border-gray-100 rounded-[24px] shadow-2xl py-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[60]">
                <div className="px-5 py-2 mb-2 border-b border-gray-50">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Select Portal</p>
                </div>
                <button onClick={() => navigate('/login')} className="w-full flex items-center space-x-4 px-5 py-3.5 text-sm font-bold text-gray-700 hover:bg-pink-50 hover:text-[#D60041] transition-colors"><LogIn size={18} className="text-gray-400" /> <span>Login to Account</span></button>
                <button onClick={() => navigate('/register')} className="w-full flex items-center space-x-4 px-5 py-3.5 text-sm font-bold text-gray-700 hover:bg-pink-50 hover:text-[#D60041] transition-colors"><UserPlus size={18} className="text-gray-400" /> <span>Register New User</span></button>
              </div>
            </div>
          ) : (
            <>
              <div className="relative mr-0 sm:mr-2" ref={notificationsRef}>
                <button
                  onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                  className={`w-9 h-9 sm:w-11 sm:h-11 rounded-xl sm:rounded-2xl flex items-center justify-center transition-all duration-300 border ${pulse ? 'ring-4 ring-pink-100 scale-110' : ''} ${isNotificationsOpen ? 'bg-slate-900 border-slate-900 shadow-xl' : 'bg-gray-50/50 border-gray-100 hover:bg-white hover:border-pink-100 hover:shadow-md hover:scale-105 active:scale-95'}`}
                >
                  <Bell size={18} className={`${pulse ? 'animate-bounce text-[#D60041]' : ''} ${isNotificationsOpen ? 'text-white' : 'text-gray-500'}`} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 sm:w-5 sm:h-5 bg-[#D60041] text-white text-[8px] sm:text-[9px] font-black rounded-full border-2 border-white flex items-center justify-center shadow-lg animate-in zoom-in duration-300">
                      {unreadCount}
                    </span>
                  )}
                </button>
                {isNotificationsOpen && <NotificationDropdown userRole={userRole} notifications={notifications} onMarkAllRead={handleMarkAllRead} />}
              </div>
              <div onClick={() => setIsProfileOpen(!isProfileOpen)} className={`flex items-center sm:space-x-4 border p-1 sm:px-2 sm:py-2 sm:pr-5 rounded-full cursor-pointer transition-all duration-300 group ${isProfileOpen ? 'bg-gray-50 border-gray-200 shadow-inner' : 'hover:border-pink-200 border-gray-100 hover:shadow-md hover:bg-white bg-gray-50/50'}`}>
                <div className={`w-9 h-9 rounded-full flex items-center justify-center border transition-all duration-300 overflow-hidden ${isProfileOpen ? 'bg-[#D60041] border-[#D60041] shadow-md shadow-pink-200' : 'bg-white border-gray-200 group-hover:border-pink-200'}`}>
                  {profileImageUrl && <img src={profileImageUrl} alt="Profile" className="w-full h-full object-cover" onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />}
                  <div className={`items-center justify-center w-full h-full ${profileImageUrl ? 'hidden' : 'flex'}`}>
                    {isAdminRole ? <ShieldCheck className={`h-4 w-4 ${isProfileOpen ? 'text-white' : 'text-gray-600 group-hover:text-[#D60041]'}`} /> : <User className={`h-4 w-4 ${isProfileOpen ? 'text-white' : 'text-gray-600 group-hover:text-[#D60041]'}`} />}
                  </div>
                </div>
                <div className="hidden sm:flex flex-col items-start overflow-hidden">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest leading-none mb-0.5">{userRole}</span>
                  <span className="text-xs font-bold text-gray-900 truncate max-w-[130px]">{userEmail}</span>
                </div>
                <ChevronDown size={14} className={`hidden sm:block text-gray-400 transition-transform duration-300 ml-1 ${isProfileOpen ? 'rotate-180 text-[#D60041]' : 'group-hover:text-gray-600'}`} />
              </div>
            </>
          )}

          {isProfileOpen && !isGuest && (
            <div className="absolute right-0 top-[calc(100%+16px)] w-[calc(100vw-2rem)] sm:w-72 max-w-[288px] bg-white border border-gray-100 rounded-[24px] shadow-2xl py-3 z-[60] animate-in fade-in slide-in-from-top-4 duration-200">
              <div className="px-4 sm:px-6 py-4 sm:py-5 border-b border-gray-50 mb-2 flex items-center gap-3 sm:gap-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl overflow-hidden border border-gray-100 shrink-0 bg-gray-50 flex items-center justify-center">
                  {profileImageUrl ? (
                    <img src={profileImageUrl} alt="Profile" className="w-full h-full object-cover" />
                  ) : (
                    isAdminRole ? <ShieldCheck size={20} className="text-[#D60041]" /> : <User size={20} className="text-gray-400" />
                  )}
                </div>
                <div className="min-w-0">
                  <p className="text-[10px] text-gray-400 font-black uppercase tracking-widest mb-0.5">{isAdminRole ? "Admin Session" : "Active Account"}</p>
                  <p className="text-xs sm:text-sm font-bold text-gray-900 truncate">{userEmail}</p>
                </div>
              </div>
              <button onClick={() => { navigate(isAdminRole ? '/admin/profile' : isHRRole ? '/hr/profile' : '/candidate/profile'); setIsProfileOpen(false); }} className="w-full text-left px-4 sm:px-6 py-3 sm:py-3.5 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 flex items-center space-x-4 transition-all group">
                <User size={18} className="text-gray-400 group-hover:text-gray-600" /> <span>View Profile</span>
              </button>
              <button onClick={() => { navigate(isAdminRole ? '/admin/settings' : isHRRole ? '/hr/settings' : '/candidate/settings'); setIsProfileOpen(false); }} className="w-full text-left px-4 sm:px-6 py-3 sm:py-3.5 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 flex items-center space-x-4 transition-all group">
                <Settings size={18} className="text-gray-400 group-hover:text-gray-600" /> <span>Account Settings</span>
              </button>
              <button onClick={handleLogout} className="w-full text-left px-4 sm:px-6 py-3 sm:py-3.5 text-sm font-bold text-red-600 hover:bg-red-50 flex items-center space-x-4 transition-all">
                <LogOut size={18} /> <span>Secure Sign Out</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Navigation Dropdown Menu (Inside header for sticky attachment) */}
      {isMobileMenuOpen && (
        <div
          ref={mobileMenuRef}
          className="lg:hidden absolute top-full left-0 w-full bg-white dark:bg-slate-900 border-b border-gray-200/90 dark:border-slate-800 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-200 max-h-[calc(100vh-70px)] overflow-y-auto"
        >
          <div className="flex flex-col py-3 divide-y divide-gray-100 dark:divide-slate-800">
            {/* 1. Primary Navigation Links (Home, About, Careers) */}
            <div className="px-4 py-2">
              <p className="text-[10px] font-black text-gray-400 dark:text-slate-400 uppercase tracking-widest mb-2 px-2">
                Navigation
              </p>
              <nav className="space-y-1">
                {navItems.map((item, index) => {
                  const isActive = location.pathname === item.path;
                  return (
                    <button
                      key={index}
                      onClick={() => {
                        navigate(item.path);
                        setIsMobileMenuOpen(false);
                      }}
                      className={`w-full flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-200 text-left ${
                        isActive
                          ? 'bg-red-50 dark:bg-pink-950/40 text-[#D60041] dark:text-[#ff386e] font-bold shadow-xs border border-red-100/70 dark:border-pink-900/50'
                          : 'text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-800 hover:text-gray-900 dark:hover:text-white font-semibold'
                      }`}
                    >
                      <div className="flex items-center space-x-3.5">
                        <span className={`${isActive ? 'text-[#D60041] dark:text-[#ff386e]' : 'text-gray-400 dark:text-slate-400'}`}>
                          {item.icon}
                        </span>
                        <span className="text-sm tracking-tight">{item.label}</span>
                      </div>
                      {isActive && (
                        <span className="w-2 h-2 rounded-full bg-[#D60041] dark:bg-[#ff386e]" />
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* 2. Theme Selection (Light and Dark Mode) */}
            <div className="px-4 py-3">
              <div className="flex items-center justify-between mb-2.5 px-2">
                <p className="text-[10px] font-black text-gray-400 dark:text-slate-400 uppercase tracking-widest flex items-center gap-1.5">
                  <Sun size={13} className="text-[#D60041]" />
                  <span>Light and Dark Mode</span>
                </p>
                <span className="text-[11px] font-bold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  {currentTheme}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 bg-gray-50 dark:bg-slate-800/80 p-1.5 rounded-2xl border border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => dispatch(setTheme('light'))}
                  className={`flex items-center justify-center space-x-2 py-2.5 px-2 rounded-xl text-xs font-bold transition-all duration-200 ${
                    currentTheme === 'light'
                      ? 'bg-white text-[#D60041] shadow-sm border border-gray-200/80 font-black scale-[1.02]'
                      : 'text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Sun size={16} className={currentTheme === 'light' ? 'text-[#D60041]' : 'text-amber-500'} />
                  <span>Light</span>
                </button>

                <button
                  type="button"
                  onClick={() => dispatch(setTheme('dark'))}
                  className={`flex items-center justify-center space-x-2 py-2.5 px-2 rounded-xl text-xs font-bold transition-all duration-200 ${
                    currentTheme === 'dark'
                      ? 'bg-slate-900 text-white shadow-sm border border-slate-700 font-black scale-[1.02]'
                      : 'text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Moon size={16} className={currentTheme === 'dark' ? 'text-pink-400' : 'text-indigo-400'} />
                  <span>Dark</span>
                </button>

                <button
                  type="button"
                  onClick={() => dispatch(setTheme('system'))}
                  className={`flex items-center justify-center space-x-2 py-2.5 px-2 rounded-xl text-xs font-bold transition-all duration-200 ${
                    currentTheme === 'system'
                      ? 'bg-white dark:bg-slate-900 text-[#D60041] dark:text-pink-400 shadow-sm border border-gray-200/80 dark:border-slate-700 font-black scale-[1.02]'
                      : 'text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white'
                  }`}
                >
                  <Monitor size={16} className="text-gray-400" />
                  <span>System</span>
                </button>
              </div>
            </div>

            {/* 3. Application Cancel (if in application flow) */}
            {isApplicationPage && (
              <div className="px-4 py-3">
                <button
                  onClick={() => {
                    navigate('/careerspage');
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full flex items-center justify-center space-x-2 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 text-gray-700 dark:text-slate-200 px-4 py-3 rounded-2xl text-sm font-bold hover:bg-red-50 dark:hover:bg-rose-950/40 hover:text-[#D60041] transition-all shadow-xs"
                >
                  <X size={18} />
                  <span>Cancel Application</span>
                </button>
              </div>
            )}

            {/* 4. Access Portal (Login Account, Register User) */}
            {isGuest ? (
              <div className="px-4 py-3 bg-gray-50/60 dark:bg-slate-800/40">
                <div className="flex items-center space-x-2 mb-3 px-2">
                  <ShieldCheck size={15} className="text-[#D60041]" />
                  <p className="text-[10px] font-black text-gray-400 dark:text-slate-400 uppercase tracking-widest">
                    Access Portal
                  </p>
                </div>
                <div className="space-y-2.5">
                  <button
                    onClick={() => {
                      navigate('/login');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center justify-between px-4 py-3 rounded-2xl bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-bold transition-all shadow-md shadow-pink-500/20 active:scale-[0.99] group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center">
                        <LogIn size={18} className="text-white" />
                      </div>
                      <div className="text-left">
                        <p className="leading-tight">Login to Account</p>
                        <p className="text-[11px] text-pink-100 font-normal">Candidate & HR Login</p>
                      </div>
                    </div>
                    <ChevronRight size={18} className="text-white/80 group-hover:translate-x-1 transition-transform" />
                  </button>

                  <button
                    onClick={() => {
                      navigate('/register');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center justify-between px-4 py-3 rounded-2xl bg-white dark:bg-slate-800 text-gray-800 dark:text-white border border-gray-200 dark:border-slate-700 text-sm font-bold transition-all hover:bg-gray-50 dark:hover:bg-slate-700/60 shadow-xs active:scale-[0.99] group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-gray-100 dark:bg-slate-700 flex items-center justify-center text-gray-600 dark:text-gray-300">
                        <UserPlus size={18} />
                      </div>
                      <div className="text-left">
                        <p className="leading-tight">Register New User</p>
                        <p className="text-[11px] text-gray-500 dark:text-slate-400 font-normal">Create Candidate Account</p>
                      </div>
                    </div>
                    <ChevronRight size={18} className="text-gray-400 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="px-4 py-3 bg-gray-50/60 dark:bg-slate-800/40">
                <div className="flex items-center space-x-2 mb-3 px-2">
                  <ShieldCheck size={15} className="text-[#D60041]" />
                  <p className="text-[10px] font-black text-gray-400 dark:text-slate-400 uppercase tracking-widest">
                    Active Portal Session
                  </p>
                </div>

                <div className="bg-white dark:bg-slate-800 p-3 rounded-2xl border border-gray-200/80 dark:border-slate-700 mb-3 flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl overflow-hidden bg-gray-100 dark:bg-slate-700 flex items-center justify-center text-[#D60041] shrink-0 border border-gray-200 dark:border-slate-600">
                    {profileImageUrl ? (
                      <img src={profileImageUrl} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                      <User size={20} />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="text-[10px] font-black uppercase tracking-wider text-[#D60041] block">{userRole} Portal</span>
                    <p className="text-xs font-bold text-gray-900 dark:text-white truncate">{userEmail}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <button
                    onClick={() => {
                      navigate(isAdminRole ? '/admin/dashboard' : isHRRole ? '/hr/dashboard' : '/candidate/dashboard');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-3 rounded-2xl bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-bold shadow-md shadow-pink-500/20 transition-all"
                  >
                    <LayoutDashboard size={18} /> <span>Open Portal Dashboard</span>
                  </button>
                  <button
                    onClick={() => {
                      navigate(isAdminRole ? '/admin/profile' : isHRRole ? '/hr/profile' : '/candidate/profile');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-white dark:bg-slate-800 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-slate-700 text-sm font-bold hover:bg-gray-50 dark:hover:bg-slate-700/60 transition-all"
                  >
                    <User size={18} className="text-gray-400" /> <span>My Profile</span>
                  </button>
                  <button
                    onClick={() => {
                      handleLogout();
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-red-50 dark:bg-rose-950/40 text-red-600 dark:text-rose-400 text-sm font-bold border border-red-100 dark:border-rose-900/50 hover:bg-red-100 dark:hover:bg-rose-900/40 transition-all"
                  >
                    <LogOut size={18} /> <span>Sign Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </header>

    {/* Backdrop Blur Overlay for mobile drawer */}
    {isMobileMenuOpen && (
      <div
        className="fixed inset-0 bg-slate-950/40 backdrop-blur-xs z-40 lg:hidden animate-in fade-in duration-200"
        onClick={() => setIsMobileMenuOpen(false)}
        aria-hidden="true"
      />
    )}
    </>
  );
};

export default Header;
