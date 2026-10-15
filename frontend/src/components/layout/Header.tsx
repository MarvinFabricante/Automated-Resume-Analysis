import React, { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from '@/utils/navigation';
import {
  ChevronDown, LayoutDashboard, Users, Database, ShieldCheck, LogOut,
  Settings, Menu, X, FileText, Search, User, Building2, Info, Briefcase, LogIn, UserPlus,
  Bell, Clock, CheckCircle2, AlertCircle, MessageSquare, ChevronRight,
  TrendingUp, Zap, Radio, Edit3, Calendar, Home, Scale, Lock,
  PanelLeft, PanelLeftClose
} from 'lucide-react';
import NotificationDropdown from './NotificationDropdown';
import notificationService from '../../services/notificationService';
import profileService from '../../services/profileService';
import { useSelector, useDispatch } from 'react-redux';
import { logout as logoutAction, updateProfileImage } from '../../redux/slices/authSlice';
import { setNotifications, addNotification, markAllRead as markAllReadAction } from '../../redux/slices/notificationSlice';
import { closeSidebar, toggleSidebar } from '../../redux/slices/uiSlice';
import { WS_BASE_URL } from '../../services/api';
import { formatNotificationTime } from '../../utils/notificationUtils';
import logo from '../../assets/logo.png';
import { RootState } from '../../redux/store';
import { clearAllAuthSessions } from '../../utils/token';

const BRAND_RED = "#D60041";

const Header: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isNotificationsOpen, setIsNotificationsOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobileNotifsOpen, setIsMobileNotifsOpen] = useState(false);
  const [pulse, setPulse] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const notificationsRef = useRef<HTMLDivElement>(null);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const hamburgerBtnRef = useRef<HTMLButtonElement>(null);

  const dispatch = useDispatch();
  const { user: userEmail, role: userRole, profileImageUrl } = useSelector((state: RootState) => state.auth);
  const { notifications, unreadCount } = useSelector((state: RootState) => state.notifications);
  const { isSidebarOpen } = useSelector((state: RootState) => state.ui);

  const normRole = (userRole || '').toUpperCase();
  const isCandidateRole = normRole === 'CANDIDATE';
  const isHRRole = normRole === 'HR';
  const isAdminRole = normRole === 'ADMIN';
  const isGuest = normRole === 'GUEST' || !userRole || userRole === 'Guest';

  useEffect(() => {
    if (window.innerWidth < 1024) {
      dispatch(closeSidebar());
    }
  }, [dispatch]);

  useEffect(() => {
    let ws: WebSocket | null = null;
    const fetchNotifications = async () => {
      if (isAdminRole || isHRRole) {
        try {
          const res = await notificationService.getNotifications(userRole, userEmail || '');
          const formatted = (res.data || []).map((n: any) => {
            let iconName = 'AlertCircle';
            let bgColor = 'bg-slate-50';
            let textColor = 'text-slate-600';
            let tag: string | null = null;
            let tagColor: string | null = null;

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

            const timeInfo = formatNotificationTime(n.created_at);

            return {
              id: n.id,
              title: n.title,
              desc: isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${n.message}` : n.message,
              time: timeInfo.relativeTime,
              relativeTime: timeInfo.relativeTime,
              timeStr: timeInfo.timeStr,
              dateStr: timeInfo.dateStr,
              displayDateTime: timeInfo.displayDateTime,
              fullDateTime: timeInfo.fullDateTime,
              createdAt: timeInfo.date,
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
          const res = await notificationService.getNotifications(userRole, userEmail || '');
          const formatted = (res.data || []).map((n: any) => {
            let iconName = 'Briefcase';
            let bgColor = 'bg-blue-50';
            let textColor = 'text-blue-600';
            let tag: string | null = 'Update';
            let tagColor: string | null = 'bg-blue-100 text-blue-700';

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
              if (n.title?.includes('Accepted') || n.title?.includes('🎉')) {
                bgColor = 'bg-emerald-50';
                textColor = 'text-emerald-600';
                tag = 'Accepted';
                tagColor = 'bg-emerald-100 text-emerald-700';
              } else if (n.title?.includes('Rejected') || n.message?.includes('regret') || n.message?.includes('other candidates') || n.desc?.includes('regret') || n.desc?.includes('other candidates')) {
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

            const timeInfo = formatNotificationTime(n.created_at);

            return {
              id: n.id,
              title: n.title,
              desc: isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${n.message}` : n.message,
              time: timeInfo.relativeTime,
              relativeTime: timeInfo.relativeTime,
              timeStr: timeInfo.timeStr,
              dateStr: timeInfo.dateStr,
              displayDateTime: timeInfo.displayDateTime,
              fullDateTime: timeInfo.fullDateTime,
              createdAt: timeInfo.date,
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
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
      const wsUrl = token
        ? `${WS_BASE_URL}/notifications/ws?token=${encodeURIComponent(token)}`
        : `${WS_BASE_URL}/notifications/ws?role=${userRole}&email=${userEmail}`;
      ws = new WebSocket(wsUrl);
      ws.onmessage = (event) => {
        try {
          const n = JSON.parse(event.data);
          let iconName = 'AlertCircle';
          let bgColor = 'bg-slate-50';
          let textColor = 'text-slate-600';
          let tag: string | null = null;
          let tagColor: string | null = null;

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
              if (n.title?.includes('Accepted') || n.title?.includes('🎉')) {
                bgColor = 'bg-emerald-50';
                textColor = 'text-emerald-600';
                tag = 'Accepted';
                tagColor = 'bg-emerald-100 text-emerald-700';
              } else if (n.title?.includes('Rejected') || n.message?.includes('regret') || n.message?.includes('other candidates')) {
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

          const timeInfo = formatNotificationTime(n.created_at || new Date());
          const desc = isAdminRole && n.sender_role ? `[Sender: ${n.sender_role}] ${n.message}` : n.message;
          const formattedNewNotif = {
            id: n.id,
            title: n.title,
            desc,
            time: timeInfo.relativeTime,
            relativeTime: timeInfo.relativeTime,
            timeStr: timeInfo.timeStr,
            dateStr: timeInfo.dateStr,
            displayDateTime: timeInfo.displayDateTime,
            fullDateTime: timeInfo.fullDateTime,
            createdAt: timeInfo.date,
            type: n.type,
            icon: iconName,
            bgColor,
            textColor,
            tag,
            tagColor,
            read: n.is_read
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
  }, [userRole, userEmail, dispatch, isAdminRole, isHRRole, isCandidateRole]);

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
  }, [isAdminRole, isHRRole, isGuest, userRole, profileImageUrl, dispatch]);

  const handleMarkAllRead = async () => {
    if (!isGuest && userEmail) {
      try { await notificationService.markAllRead(userRole, userEmail); }
      catch (err) { console.error("Failed to mark all read:", err); }
    }
    dispatch(markAllReadAction());
  };

  const isCandidateRoute = location.pathname.startsWith('/candidate');

  const isApplicationPage =
    !isCandidateRoute && (
      location.pathname.includes('/job-details/') ||
      location.pathname.includes('/apply/') ||
      location.pathname.includes('/smart-upload') ||
      location.pathname.includes('/preview-and-verify/') ||
      location.pathname.includes('/applicationform/') ||
      location.pathname.includes('/submissionsuccess/')
    );

  const isPublicSitePage =
    location.pathname === '/' ||
    location.pathname === '/aboutpage' ||
    location.pathname === '/aboutpage/' ||
    location.pathname === '/careerspage' ||
    location.pathname === '/careerspage/';

  const isHRPage = location.pathname.startsWith('/hr');
  const hasSidebar = !isGuest && !isPublicSitePage && !isApplicationPage;

  const handleLogout = () => {
    clearAllAuthSessions();
    dispatch(logoutAction());
    navigate('/');
    window.location.reload();
  };

  // Close menus on route navigation
  useEffect(() => {
    setIsMobileMenuOpen(false);
    setIsProfileOpen(false);
    setIsNotificationsOpen(false);
    setIsMobileNotifsOpen(false);
  }, [location.pathname]);

  // Handle escape key, shortcut Ctrl+B, and window resize
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle sidebar shortcut Ctrl+B / Cmd+B
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        if (hasSidebar) {
          e.preventDefault();
          dispatch(toggleSidebar());
        }
      }

      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false);
        setIsProfileOpen(false);
        setIsNotificationsOpen(false);
        setIsMobileNotifsOpen(false);
        if (window.innerWidth < 1024) {
          dispatch(closeSidebar());
        }
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
  }, [hasSidebar, dispatch]);

  // Handle click outside to close dropdowns and mobile menu
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (dropdownRef.current && !dropdownRef.current.contains(target)) setIsProfileOpen(false);
      if (notificationsRef.current && !notificationsRef.current.contains(target)) setIsNotificationsOpen(false);
      if (
        isMobileMenuOpen &&
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(target) &&
        hamburgerBtnRef.current &&
        !hamburgerBtnRef.current.contains(target)
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
    if (isHRRole || isHRPage) return [
      { label: 'Dashboard', path: '/hr/dashboard', icon: <Building2 size={18} /> },
      { label: 'Screening', path: '/hr/screeningportal', icon: <User size={18} /> },
      { label: 'Scheduling', path: '/hr/scheduling', icon: <Calendar size={18} /> },
      { label: 'Compare Candidates', path: '/hr/comparecandidates', icon: <Scale size={18} /> },
      { label: 'Messages', path: '/hr/messages', icon: <MessageSquare size={18} /> },
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
    <header className="main-header relative bg-white border-b border-gray-100 px-4 sm:px-6 md:px-10 py-3 sm:py-4 sticky top-0 z-50 font-sans shadow-sm transition-colors duration-200">
      <div className="max-w-[1400px] mx-auto flex items-center justify-between">

        <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
          {/* Mobile Drawer Trigger (Mobile & Tablet only < 1024px) */}
          {hasSidebar ? (
            <button
              type="button"
              onClick={() => dispatch(toggleSidebar())}
              className={`lg:hidden p-2 sm:p-2.5 rounded-xl transition-all duration-200 active:scale-95 border cursor-pointer ${
                isSidebarOpen
                  ? 'bg-rose-50 text-[#D60041] border-rose-200'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
              title="Toggle navigation"
              aria-label="Toggle navigation"
            >
              <Menu size={20} className="transition-transform duration-200" />
            </button>
          ) : (
            <button
              ref={hamburgerBtnRef}
              type="button"
              className={`lg:hidden relative p-2 sm:p-2.5 rounded-xl transition-all active:scale-95 -ml-1 cursor-pointer ${
                isMobileMenuOpen
                  ? 'bg-red-50 text-[#D60041]'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              aria-label={isMobileMenuOpen ? "Close navigation menu" : "Open navigation menu"}
              aria-expanded={isMobileMenuOpen}
            >
              {isMobileMenuOpen ? (
                <X size={22} className="transition-transform duration-200" />
              ) : (
                <Menu size={22} className="transition-transform duration-200" />
              )}
            </button>
          )}

          <div className="flex items-center space-x-2 sm:space-x-4 cursor-pointer group min-w-0" onClick={() => navigate(isGuest ? '/' : location.pathname)}>
            <div className={`w-8 h-8 sm:w-10 sm:h-10 rounded-xl flex items-center justify-center overflow-hidden transition-all duration-300 shrink-0 ${!isGuest && 'group-hover:shadow-[0_0_15px_rgba(209,0,67,0.3)]'}`}>
              <img src={(logo as any)?.src || logo} alt="logo" className="w-full h-full object-contain" />
            </div>
            <div className="min-w-0">
              <h1 className="text-sm sm:text-base font-black tracking-tight text-gray-900 leading-tight truncate">
                {isPublicSitePage ? "Mariwasa" : isAdminRole ? "Admin Portal" : isHRRole ? "HR Portal" : isCandidateRole ? "Candidate Portal" : "Mariwasa"}
              </h1>
              <p className={`text-[9px] sm:text-[10px] font-bold uppercase tracking-widest mt-0.5 truncate ${isGuest || isPublicSitePage ? 'text-gray-400' : 'text-[#D60041]'}`}>
                {isGuest || isPublicSitePage ? "Siam Ceramics Inc." : "Resume Analysis System"}
              </p>
            </div>
          </div>
        </div>

        <div className={`hidden lg:flex flex-1 items-center ${(isGuest || isPublicSitePage) || isApplicationPage ? 'justify-end pr-8' : 'justify-center'}`}>
          {!isApplicationPage && (isGuest || isPublicSitePage) && (
            <nav className="desktop-nav flex items-center space-x-1 bg-white p-1 rounded-2xl border border-gray-200/80 shadow-xs">
              {navItems.map((item, index) => {
                const isActive = location.pathname === item.path;
                return (
                  <button
                    key={index}
                    onClick={() => navigate(item.path)}
                    className={`desktop-nav-item px-5 py-2.5 rounded-xl flex items-center space-x-2.5 transition-all duration-300 group ${isActive
                        ? 'active-nav-item bg-red-50 text-[#D60041] shadow-xs font-bold ring-1 ring-red-100'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900 font-semibold'
                      }`}
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

        <div className="flex items-center space-x-1.5 sm:space-x-3 md:space-x-4 relative shrink-0" ref={dropdownRef}>

          {isGuest ? (
            <div className="hidden sm:block relative group">
              <button className="flex items-center space-x-2 bg-[#D60041] text-white px-4 sm:px-6 py-2.5 sm:py-3 rounded-full text-xs sm:text-sm font-bold hover:bg-[#b50037] transition-all shadow-md shadow-pink-200 cursor-pointer">
                <span>Access Portal</span>
                <ChevronDown size={16} className="group-hover:rotate-180 transition-transform duration-300" />
              </button>
              <div className="desktop-dropdown absolute right-0 mt-3 w-64 bg-white border border-gray-100 rounded-[24px] shadow-2xl py-3 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-[60]">
                <div className="px-5 py-2 mb-2 border-b border-gray-50">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Select Portal</p>
                </div>
                <button onClick={() => navigate('/login')} className="w-full flex items-center space-x-4 px-5 py-3.5 text-sm font-bold text-gray-700 hover:bg-pink-50 hover:text-[#D60041] transition-colors cursor-pointer"><LogIn size={18} className="text-gray-400" /> <span>Login to Account</span></button>
                <button onClick={() => navigate('/register')} className="w-full flex items-center space-x-4 px-5 py-3.5 text-sm font-bold text-gray-700 hover:bg-pink-50 hover:text-[#D60041] transition-colors cursor-pointer"><UserPlus size={18} className="text-gray-400" /> <span>Register Candidate</span></button>
              </div>
            </div>
          ) : (
            <>
              <div className="relative mr-0 sm:mr-1" ref={notificationsRef}>
                <button
                  type="button"
                  onClick={() => setIsNotificationsOpen(!isNotificationsOpen)}
                  className={`desktop-icon-btn w-9 h-9 sm:w-11 sm:h-11 rounded-xl sm:rounded-2xl flex items-center justify-center transition-all duration-300 border cursor-pointer ${pulse ? 'ring-4 ring-pink-100 scale-110' : ''} ${isNotificationsOpen
                      ? 'bg-slate-900 border-slate-900 shadow-xl'
                      : 'bg-white border-gray-200/80 hover:bg-gray-50 hover:border-pink-200 hover:shadow-md hover:scale-105 active:scale-95'
                    }`}
                  title="Notifications"
                  aria-label="Notifications"
                >
                  <Bell size={18} className={`${pulse ? 'animate-bounce text-[#D60041]' : ''} ${isNotificationsOpen ? 'text-white' : 'text-gray-600'}`} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 sm:w-5 sm:h-5 bg-[#D60041] text-white text-[8px] sm:text-[9px] font-black rounded-full border-2 border-white flex items-center justify-center shadow-lg animate-in zoom-in duration-300">
                      {unreadCount}
                    </span>
                  )}
                </button>
                {isNotificationsOpen && (
                  <NotificationDropdown 
                    userRole={userRole} 
                    notifications={notifications} 
                    onMarkAllRead={handleMarkAllRead} 
                    onClose={() => setIsNotificationsOpen(false)}
                  />
                )}
              </div>
              <div
                onClick={() => setIsProfileOpen(!isProfileOpen)}
                className={`desktop-profile-pill flex items-center sm:space-x-3 border p-1 sm:px-2 sm:py-2 sm:pr-4 rounded-full cursor-pointer transition-all duration-300 group ${isProfileOpen ? 'bg-gray-50 border-gray-200 shadow-inner' : 'hover:border-pink-200 border-gray-200/80 hover:shadow-md hover:bg-gray-50 bg-white'}`}
                title="Account menu"
                role="button"
                aria-label="Account menu"
              >
                <div className={`w-8 h-8 sm:w-9 sm:h-9 rounded-full flex items-center justify-center border transition-all duration-300 overflow-hidden shrink-0 ${isProfileOpen ? 'bg-[#D60041] border-[#D60041] shadow-md shadow-pink-200' : 'bg-white border-gray-200 group-hover:border-pink-200'}`}>
                  {profileImageUrl ? (
                    <img 
                      src={profileImageUrl} 
                      alt="Profile" 
                      className="w-full h-full object-cover" 
                      onError={(e) => { 
                        const img = e.currentTarget;
                        img.style.display = 'none'; 
                        if (img.nextElementSibling) {
                          (img.nextElementSibling as HTMLElement).style.display = 'flex';
                        }
                      }} 
                    />
                  ) : null}
                  <div className={`items-center justify-center w-full h-full ${profileImageUrl ? 'hidden' : 'flex'}`}>
                    {isAdminRole ? <ShieldCheck className={`h-4 w-4 ${isProfileOpen ? 'text-white' : 'text-gray-600 group-hover:text-[#D60041]'}`} /> : <User className={`h-4 w-4 ${isProfileOpen ? 'text-white' : 'text-gray-600 group-hover:text-[#D60041]'}`} />}
                  </div>
                </div>
                <div className="hidden sm:flex flex-col items-start overflow-hidden">
                  <span className="text-[10px] text-gray-400 font-bold uppercase tracking-widest leading-none mb-0.5">{userRole}</span>
                  <span className="text-xs font-bold text-gray-900 truncate max-w-[100px] md:max-w-[130px]">{userEmail}</span>
                </div>
                <ChevronDown size={14} className={`hidden sm:block text-gray-400 transition-transform duration-300 ml-1 ${isProfileOpen ? 'rotate-180 text-[#D60041]' : 'group-hover:text-gray-600'}`} />
              </div>
            </>
          )}

          {isProfileOpen && !isGuest && (
            <div className="desktop-dropdown absolute right-0 top-[calc(100%+12px)] w-[calc(100vw-2rem)] sm:w-72 max-w-[288px] bg-white border border-gray-100 rounded-[24px] shadow-2xl py-3 z-[60] animate-in fade-in slide-in-from-top-4 duration-200">
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
              <button onClick={() => { navigate(isAdminRole ? '/admin/profile' : isHRRole ? '/hr/profile' : '/candidate/profile'); setIsProfileOpen(false); }} className="w-full text-left px-4 sm:px-6 py-3 sm:py-3.5 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 flex items-center space-x-4 transition-all group cursor-pointer">
                <User size={18} className="text-gray-400 group-hover:text-gray-600" /> <span>View Profile</span>
              </button>
              <button onClick={() => { navigate(isAdminRole ? '/admin/settings' : isHRRole ? '/hr/settings' : '/candidate/settings'); setIsProfileOpen(false); }} className="w-full text-left px-4 sm:px-6 py-3 sm:py-3.5 text-sm font-bold text-gray-600 hover:bg-gray-50 hover:text-gray-900 flex items-center space-x-4 transition-all group cursor-pointer">
                <Settings size={18} className="text-gray-400 group-hover:text-gray-600" /> <span>Account Settings</span>
              </button>
              <button onClick={handleLogout} className="w-full text-left px-4 sm:px-6 py-3 sm:py-3.5 text-sm font-bold text-red-600 hover:bg-red-50 flex items-center space-x-4 transition-all cursor-pointer">
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
          className="lg:hidden absolute top-full left-0 w-full bg-white border-b border-gray-200/90 shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-200 max-h-[calc(100vh-70px)] overflow-y-auto"
        >
          <div className="flex flex-col py-3 divide-y divide-gray-100">
            {/* 1. Primary Navigation Links */}
            <div className="px-4 py-2">
              <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 px-2">
                {isHRRole || isHRPage ? "HR Management Menu" : "Navigation"}
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
                      className={`w-full flex items-center justify-between px-4 py-3 rounded-2xl transition-all duration-200 text-left ${isActive
                          ? 'bg-red-50 text-[#D60041] font-bold shadow-xs border border-red-100/70'
                          : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900 font-semibold'
                        }`}
                    >
                      <div className="flex items-center space-x-3.5">
                        <span className={`${isActive ? 'text-[#D60041]' : 'text-gray-400'}`}>
                          {item.icon}
                        </span>
                        <span className="text-sm tracking-tight">{item.label}</span>
                      </div>
                      {isActive && (
                        <span className="w-2 h-2 rounded-full bg-[#D60041]" />
                      )}
                    </button>
                  );
                })}
              </nav>
            </div>

            {/* 2. Notifications Section (Mobile) */}
            {!isGuest && (
              <div className="px-4 py-3">
                <div
                  onClick={() => setIsMobileNotifsOpen(!isMobileNotifsOpen)}
                  className="flex items-center justify-between cursor-pointer py-1 group select-none"
                >
                  <div className="flex items-center space-x-2.5">
                    <div className="relative">
                      <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600 group-hover:text-[#D60041] transition-colors">
                        <Bell size={16} />
                      </div>
                      {unreadCount > 0 && (
                        <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#D60041] text-white text-[8px] font-black rounded-full flex items-center justify-center shadow-xs">
                          {unreadCount}
                        </span>
                      )}
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-900 flex items-center gap-2 flex-wrap">
                        <span>{userRole === 'HR' ? 'Recruitment Alerts' : 'Notifications'}</span>
                        <span className="inline-flex items-center gap-1 text-[8px] font-black uppercase tracking-wider text-amber-700 bg-amber-50 border border-amber-200/80 px-1.5 py-0.5 rounded-full">
                          <Lock size={8} className="text-amber-600" /> Read-Only
                        </span>
                        {unreadCount > 0 ? (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-red-100 text-[#D60041]">
                            {unreadCount} new
                          </span>
                        ) : (
                          <span className="text-[10px] font-medium text-gray-400">
                            Up to date
                          </span>
                        )}
                      </p>
                      <p className="text-[10px] text-gray-400 font-medium">
                        {notifications.length} {notifications.length === 1 ? 'alert' : 'alerts'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    {unreadCount > 0 && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMarkAllRead();
                        }}
                        className="text-[10px] font-bold text-[#D60041] hover:underline px-1 py-0.5"
                      >
                        Mark all read
                      </button>
                    )}
                    <ChevronDown
                      size={16}
                      className={`text-gray-400 transition-transform duration-200 ${isMobileNotifsOpen ? 'rotate-180 text-[#D60041]' : ''}`}
                    />
                  </div>
                </div>

                {isMobileNotifsOpen && (
                  <div className="mt-3 pt-3 border-t border-gray-100 space-y-2 max-h-56 overflow-y-auto pr-1">
                    {notifications.length === 0 ? (
                      <div className="py-6 text-center">
                        <CheckCircle2 size={24} className="mx-auto text-emerald-500 mb-1.5 opacity-80" />
                        <p className="text-xs font-bold text-gray-700">All caught up!</p>
                        <p className="text-[11px] text-gray-400">No new notifications</p>
                      </div>
                    ) : (
                      notifications.slice(0, 8).map((n) => (
                        <div
                          key={n.id}
                          className={`p-3 rounded-xl border transition-all ${
                            !n.read
                              ? 'bg-rose-50/40 border-rose-100/90 shadow-2xs'
                              : 'bg-gray-50/70 border-gray-100'
                          }`}
                        >
                          <div className="flex items-start justify-between gap-1.5 mb-1">
                            <p className={`text-xs truncate ${!n.read ? 'font-black text-gray-900' : 'font-bold text-gray-700'}`}>
                              {n.title}
                            </p>
                            <div className="flex items-center gap-1.5 shrink-0">
                              {n.tag && (
                                <span className={`text-[8px] font-black px-1.5 py-0.5 rounded uppercase tracking-wider ${n.tagColor}`}>
                                  {n.tag}
                                </span>
                              )}
                              {!n.read && (
                                <span className="w-1.5 h-1.5 rounded-full bg-[#D60041] shrink-0" />
                              )}
                            </div>
                          </div>
                          <p className="text-[11px] text-gray-600 line-clamp-2 leading-relaxed mb-2">
                            {n.desc}
                          </p>
                          <div className="flex items-center justify-between gap-2 pt-1 border-t border-gray-100/80 text-[10px]">
                            <div className="flex items-center gap-1 text-gray-600 font-semibold truncate" title={`Created: ${n.fullDateTime || n.displayDateTime}`}>
                              <Clock size={10} className="text-[#D60041] shrink-0" />
                              <span className="truncate">{n.displayDateTime || n.time}</span>
                            </div>
                            <span className="text-[9px] font-bold text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded-full shrink-0">
                              {n.relativeTime || n.time}
                            </span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 3. Access Portal (Login Account, Register User) */}
            {isGuest ? (
              <div className="px-4 py-3 bg-gray-50/60">
                <div className="flex items-center space-x-2 mb-3 px-2">
                  <ShieldCheck size={15} className="text-[#D60041]" />
                  <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
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
                    className="w-full flex items-center justify-between px-4 py-3 rounded-2xl bg-white text-gray-800 border border-gray-200 text-sm font-bold transition-all hover:bg-gray-50 shadow-xs active:scale-[0.99] group"
                  >
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600">
                        <UserPlus size={18} />
                      </div>
                      <div className="text-left">
                        <p className="leading-tight">Register Candidate</p>
                        <p className="text-[11px] text-gray-500 font-normal">Create Candidate Account</p>
                      </div>
                    </div>
                    <ChevronRight size={18} className="text-gray-400 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="px-4 py-3 bg-gray-50/60">
                <div className="flex items-center space-x-2 mb-3 px-2">
                  <ShieldCheck size={15} className="text-[#D60041]" />
                  <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">
                    Active Portal Session
                  </p>
                </div>

                <div className="bg-white p-3 rounded-2xl border border-gray-200/80 mb-3 flex items-center space-x-3">
                  <div className="w-10 h-10 rounded-xl overflow-hidden bg-gray-100 flex items-center justify-center text-[#D60041] shrink-0 border border-gray-200">
                    {profileImageUrl ? (
                      <img src={profileImageUrl} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                      <User size={20} />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <span className="text-[10px] font-black uppercase tracking-wider text-[#D60041] block">{userRole} Portal</span>
                    <p className="text-xs font-bold text-gray-900 truncate">{userEmail}</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <button
                    onClick={() => {
                      navigate(isAdminRole ? '/admin/dashboard' : (isHRRole || isHRPage) ? '/hr/dashboard' : '/candidate/dashboard');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-[#D60041] hover:bg-[#b50037] text-white text-sm font-bold shadow-md shadow-pink-500/20 transition-all"
                  >
                    <LayoutDashboard size={18} /> <span>Open Portal Dashboard</span>
                  </button>
                  <button
                    onClick={() => {
                      navigate(isAdminRole ? '/admin/profile' : (isHRRole || isHRPage) ? '/hr/profile' : '/candidate/profile');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-white text-gray-700 border border-gray-200 text-sm font-bold hover:bg-gray-50 transition-all"
                  >
                    <User size={18} className="text-gray-400" /> <span>My Profile</span>
                  </button>
                  <button
                    onClick={() => {
                      navigate(isAdminRole ? '/admin/settings' : (isHRRole || isHRPage) ? '/hr/settings' : '/candidate/settings');
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-white text-gray-700 border border-gray-200 text-sm font-bold hover:bg-gray-50 transition-all"
                  >
                    <Settings size={18} className="text-gray-400" /> <span>Account Settings</span>
                  </button>
                  {(isHRRole || isHRPage) && (
                    <button
                      onClick={() => {
                        navigate('/careerspage');
                        setIsMobileMenuOpen(false);
                      }}
                      className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-white text-gray-700 border border-gray-200 text-sm font-bold hover:bg-gray-50 transition-all"
                    >
                      <Briefcase size={18} className="text-gray-400" /> <span>View Careers Portal</span>
                    </button>
                  )}
                  <button
                    onClick={() => {
                      handleLogout();
                      setIsMobileMenuOpen(false);
                    }}
                    className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-2xl bg-red-50 text-red-600 text-sm font-bold border border-red-100 hover:bg-red-100 transition-all"
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
