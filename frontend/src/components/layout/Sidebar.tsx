import React, { ReactNode, useMemo } from 'react';
import { useNavigate, useLocation } from '@/utils/navigation';
import {
  LayoutDashboard, Users, Building2, User, Settings, Search, Briefcase,
  BookOpen, MessageSquare, Scale, Sliders, Calendar, Sparkles,
  PanelLeftClose, PanelLeftOpen, X, LogOut, FolderArchive, FileText, FileUp
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import { toggleSidebar, closeSidebar } from '../../redux/slices/uiSlice';
import { logout as logoutAction } from '../../redux/slices/authSlice';
import { RootState } from '../../redux/store';
import { clearAllAuthSessions, performUserLogout } from '../../utils/token';
import { useGetJobsQuery } from '../../redux/api/apiSlice';
import styles from './Sidebar.module.css';

export interface NavItem {
  label: string;
  path: string;
  icon: ReactNode;
  badge?: string;
  badgeColor?: string;
  hasUnreadDot?: boolean;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

const Sidebar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { role: userRole } = useSelector((state: RootState) => state.auth);
  const { isSidebarOpen } = useSelector((state: RootState) => state.ui);
  const { unreadMessagesCount } = useSelector((state: RootState) => state.notifications);

  const normRole = (userRole || '').toUpperCase();
  const isAdminRole = normRole === 'ADMIN';
  const isHRRole = normRole === 'HR';
  const isCandidateRole = normRole === 'CANDIDATE';
  const isHRPage = location.pathname.startsWith('/hr');
  const isHR = isHRRole || isHRPage;

  // Active jobs count for candidate sidebar badge
  const { data: rawJobs = [] } = useGetJobsQuery(undefined, { skip: !isCandidateRole });
  const activeJobCount = useMemo(
    () => (Array.isArray(rawJobs) ? rawJobs.filter((j: any) => j.is_active !== false).length : 0),
    [rawJobs]
  );

  const handleLogout = () => {
    dispatch(logoutAction());
    performUserLogout();
  };

  // Grouped navigation structure for modern SaaS UX
  const getNavSections = (): NavSection[] => {
    if (isAdminRole) {
      return [
        {
          title: 'ANALYTICS & METRICS',
          items: [
            { label: 'Dashboard', path: '/admin/dashboard', icon: <LayoutDashboard size={18} /> },
          ],
        },
        {
          title: 'MANAGEMENT',
          items: [
            { label: 'User Directory', path: '/admin/users', icon: <Users size={18} /> },
            { label: 'Job Postings', path: '/admin/jobmanagement', icon: <Briefcase size={18} /> },
            { label: 'System Config', path: '/admin/system-config', icon: <Sliders size={18} /> },
          ],
        },
        {
          title: 'COMMUNICATION',
          items: [
            {
              label: 'Messages',
              path: '/admin/messages',
              icon: <MessageSquare size={18} />,
              badge: unreadMessagesCount > 0 ? String(unreadMessagesCount) : undefined,
              badgeColor: 'bg-[#D60041] text-white',
              hasUnreadDot: unreadMessagesCount > 0,
            },
          ],
        },
      ];
    }

    if (isHR) {
      return [
        {
          title: 'TALENT PIPELINE',
          items: [
            { label: 'Dashboard', path: '/hr/dashboard', icon: <LayoutDashboard size={18} /> },
            { label: 'Applicants', path: '/hr/applicants', icon: <Users size={18} /> },
            {
              label: 'Screening',
              path: '/hr/screeningportal',
              icon: <User size={18} />,
            },
            {
              label: 'Import Resumes',
              path: '/hr/physical-resumes',
              icon: <FolderArchive size={18} />,
            },
            { label: 'Interview Scheduling', path: '/hr/scheduling', icon: <Calendar size={18} /> },
            { label: 'Candidate Comparison', path: '/hr/comparecandidates', icon: <Scale size={18} /> },
          ],
        },
        {
          title: 'COMMUNICATION',
          items: [
            {
              label: 'Messages',
              path: '/hr/messages',
              icon: <MessageSquare size={18} />,
              badge: unreadMessagesCount > 0 ? String(unreadMessagesCount) : undefined,
              badgeColor: 'bg-[#D60041] text-white',
              hasUnreadDot: unreadMessagesCount > 0,
            },
          ],
        },
      ];
    }

    if (isCandidateRole) {
      return [
        {
          title: 'CAREER',
          items: [
            { label: 'Dashboard', path: '/candidate/dashboard', icon: <LayoutDashboard size={18} /> },
            {
              label: 'Open Positions',
              path: '/candidate/findjobs',
              icon: <Briefcase size={18} />,
              badge: activeJobCount > 0 ? String(activeJobCount) : undefined,
              badgeColor: 'bg-[#D60041] text-white',
            },
            {
              label: 'Upload Resume',
              path: '/candidate/smart-upload',
              icon: <FileUp size={18} />,
            },
            { label: 'My Applications', path: '/candidate/applicationtracking', icon: <FileText size={18} /> },
            {
              label: 'Messages',
              path: '/candidate/messages',
              icon: <MessageSquare size={18} />,
              badge: unreadMessagesCount > 0 ? String(unreadMessagesCount) : undefined,
              badgeColor: 'bg-[#D60041] text-white',
              hasUnreadDot: unreadMessagesCount > 0,
            },
          ],
        },
      ];
    }

    return [
      {
        title: 'EXPLORE',
        items: [
          { label: 'About', path: '/aboutpage', icon: <BookOpen size={18} /> },
          { label: 'Careers', path: '/careerspage', icon: <Briefcase size={18} /> },
        ]
      }
    ];
  };

  const navSections = getNavSections();

  const getWorkspaceTitle = () => {
    if (isHR) return 'Mariwasa HR';
    if (isAdminRole) return 'Admin Suite';
    if (isCandidateRole) return 'Mariwasa Recruitment';
    return 'Mariwasa Recruitment';
  };

  const getWorkspaceSubtitle = () => {
    if (isHR) return 'Talent Operations';
    if (isAdminRole) return 'System Control';
    if (isCandidateRole) return 'Careers';
    return 'Recruitment System';
  };

  const settingsPath = isHR ? '/hr/settings' : isAdminRole ? '/admin/settings' : '/candidate/settings';

  return (
    <>
      {/* Mobile Drawer Backdrop (Active on mobile < 768px) */}
      <div
        className={`md:hidden fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-[55] transition-opacity duration-300 ${isSidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
          }`}
        onClick={() => dispatch(closeSidebar())}
        aria-hidden="true"
      />

      <aside
        data-sidebar="true"
        data-hr-theme="true"
        data-role-theme={isAdminRole ? 'admin' : isHR ? 'hr' : isCandidateRole ? 'candidate' : 'guest'}
        className={`
          desktop-sidebar flex flex-col ${styles.sidebarRoot}
          transition-all duration-200 ease-in-out
          /* Mobile Drawer */
          fixed top-0 bottom-0 left-0 z-[60]
          w-72 max-w-[85vw] h-full ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          /* Tablet and Desktop Docked Sticky Sidebar */
          md:sticky md:top-[73px] md:bottom-auto md:left-auto md:self-start md:h-[calc(100vh-73px)] md:z-40
          md:translate-x-0 md:shrink-0
          ${isSidebarOpen ? 'md:w-64' : 'md:w-20'}
        `}
      >
        {/* WORKSPACE HEADER */}
        <div data-slot="workspace-header" className={`p-4 border-b border-slate-100 flex items-center shrink-0 ${isSidebarOpen ? 'justify-between' : 'justify-center'}`}>
          {isSidebarOpen ? (
            <>
              {/* Workspace Identity */}
              <div className="flex items-center space-x-3 min-w-0">
                <div data-slot="brand-icon" className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#D60041] to-[#B50037] text-white flex items-center justify-center shadow-xs shadow-[#D60041]/25 shrink-0">
                  {isHR ? <Building2 size={18} /> : isAdminRole ? <Sliders size={18} /> : <Sparkles size={18} />}
                </div>
                <div className="min-w-0">
                  <h3 data-slot="brand-title" className="text-sm font-black text-slate-900 tracking-tight leading-tight truncate">
                    {getWorkspaceTitle()}
                  </h3>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <span data-slot="brand-dot" className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-xs" />
                    <span data-slot="brand-subtitle" className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider truncate">
                      {getWorkspaceSubtitle()}
                    </span>
                  </div>
                </div>
              </div>

              {/* Single Open/Close Control */}
              <div className="flex items-center">
                {/* Mobile: Close Drawer Button */}
                <button
                  type="button"
                  onClick={() => dispatch(closeSidebar())}
                  data-slot="sidebar-control"
                  className="md:hidden w-8 h-8 rounded-xl flex items-center justify-center transition-all cursor-pointer"
                  title="Close sidebar"
                  aria-label="Close sidebar"
                >
                  <X size={17} />
                </button>

                {/* Tablet and Desktop: Collapse Sidebar Button */}
                <button
                  type="button"
                  onClick={() => dispatch(toggleSidebar())}
                  data-slot="sidebar-control"
                  className="hidden md:flex w-8 h-8 rounded-xl items-center justify-center transition-all cursor-pointer"
                  title="Collapse sidebar (Ctrl+B)"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeftClose size={17} />
                </button>
              </div>
            </>
          ) : (
            /* Collapsed Mode: Single Expand Sidebar Button */
            <div className="relative group flex justify-center py-0.5">
              <button
                type="button"
                onClick={() => dispatch(toggleSidebar())}
                data-slot="sidebar-control"
                className="w-10 h-10 rounded-xl flex items-center justify-center transition-all cursor-pointer group"
                title="Expand sidebar (Ctrl+B)"
                aria-label="Expand sidebar"
              >
                <PanelLeftOpen size={18} className="group-hover:scale-105 transition-transform" />
              </button>

              <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 flex items-center gap-1.5 border border-slate-800">
                <span>Expand sidebar (Ctrl+B)</span>
                <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
              </div>
            </div>
          )}
        </div>

        {/* NAVIGATION ITEMS */}
        <div data-slot="nav-body" className="flex-grow overflow-y-auto overflow-x-hidden custom-scrollbar px-3 py-3 space-y-5">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1.5">
              {isSidebarOpen ? (
                <div className="px-2.5 pt-1 pb-1">
                  <p data-slot="section-label" className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    {section.title}
                  </p>
                </div>
              ) : (
                <div className="w-full flex justify-center py-1">
                  <div data-slot="section-divider" className="w-6 border-t border-slate-200" />
                </div>
              )}

              <nav className="space-y-1.5">
                {section.items.map((item, index) => {
                  const isActive = location.pathname === item.path;

                  if (isSidebarOpen) {
                    return (
                      <button
                        key={index}
                        type="button"
                        onClick={() => {
                          navigate(item.path);
                          if (window.innerWidth < 768) dispatch(closeSidebar());
                        }}
                        data-slot="nav-item"
                        data-active={isActive ? 'true' : undefined}
                        aria-current={isActive ? 'page' : undefined}
                        className="w-full flex items-center justify-between px-2.5 py-2 rounded-xl transition-all duration-150 group relative cursor-pointer"
                      >
                        <div className="flex items-center space-x-2.5 min-w-0">
                          <span
                            data-slot="nav-icon"
                            className="shrink-0"
                          >
                            {item.icon}
                          </span>
                          <span data-slot="nav-label" className="text-[13.5px] tracking-tight truncate leading-tight">
                            {item.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          {item.hasUnreadDot && (
                            <span data-slot="unread-dot" className="w-2 h-2 rounded-full animate-pulse" aria-label="Unread messages" />
                          )}
                          {item.badge && (
                            <span
                              data-slot="nav-badge"
                              className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                            >
                              {item.badge}
                            </span>
                          )}
                          {isActive && !item.badge && (
                            <span data-slot="active-marker" className="w-1.5 h-1.5 rounded-full shrink-0 mr-1" />
                          )}
                        </div>
                      </button>
                    );
                  }

                  // Collapsed View with Tooltip
                  return (
                    <div key={index} className="relative group flex justify-center w-full py-0.5">
                      <button
                        type="button"
                        onClick={() => {
                          navigate(item.path);
                          if (window.innerWidth < 768) dispatch(closeSidebar());
                        }}
                        data-slot="nav-item"
                        data-active={isActive ? 'true' : undefined}
                        aria-current={isActive ? 'page' : undefined}
                        className="w-11 h-11 flex items-center justify-center rounded-xl transition-all duration-150 relative cursor-pointer"
                        aria-label={item.label}
                        title={item.label}
                      >
                        <span
                          data-slot="nav-icon"
                          className="!w-auto !h-auto !bg-transparent !border-0 !shadow-none"
                        >
                          {item.icon}
                        </span>
                        {item.badge && (
                          <span data-slot="unread-dot" className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#D60041] rounded-full border-2 border-[#162134] animate-pulse" />
                        )}
                      </button>

                      {/* Tooltip */}
                      <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-3 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-xl shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 flex items-center gap-2 border border-slate-700/80">
                        <span>{item.label}</span>
                        {item.badge && (
                          <span className="bg-[#D60041] text-white text-[9px] px-1.5 py-0.5 rounded-full font-black uppercase tracking-wider">
                            {item.badge}
                          </span>
                        )}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                      </div>
                    </div>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>

        {/* FOOTER SECTION */}
        <div data-slot="sidebar-footer" className="p-3 border-t border-slate-100 shrink-0">
          {isSidebarOpen ? (
            <div data-slot="footer-card" className="rounded-2xl p-3 space-y-2.5">
              <div className="flex items-center justify-between px-1">
                <div className="flex items-center space-x-2 min-w-0">
                  <div data-slot="footer-dot" className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0" />
                  <span data-slot="footer-title" className="text-[11px] font-bold truncate">
                    {isHR ? 'Recruitment Workspace' : isAdminRole ? 'Admin Control Center' : isCandidateRole ? 'Candidate Portal' : 'Recruitment System'}
                  </span>
                </div>
                <span data-slot="footer-badge" className="text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md border shrink-0">
                  {isHR ? 'HR' : isAdminRole ? 'ADMIN' : isCandidateRole ? 'CAREERS' : 'ONLINE'}
                </span>
              </div>
              <div data-slot="footer-separator" className="pt-2 border-t space-y-1.5">
                <button
                  type="button"
                  onClick={() => {
                    navigate(settingsPath);
                    if (window.innerWidth < 768) dispatch(closeSidebar());
                  }}
                  data-slot="footer-action"
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-semibold cursor-pointer group"
                  title="Account Settings"
                >
                  <span className="flex items-center space-x-2.5">
                    <Settings size={14} className="opacity-80 group-hover:rotate-45 transition-transform duration-300" />
                    <span>Account Settings</span>
                  </span>
                </button>

                <button
                  type="button"
                  onClick={handleLogout}
                  data-slot="sign-out"
                  className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-xl text-xs font-bold cursor-pointer active:scale-98"
                  title="Secure Sign Out"
                >
                  <LogOut size={14} />
                  <span>Sign Out</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-2 py-1">
              {/* Collapsed Settings Shortcut */}
              <div className="relative group">
                <button
                  type="button"
                  onClick={() => navigate(settingsPath)}
                  data-slot="footer-action"
                  className="w-10 h-10 flex items-center justify-center rounded-xl transition-all cursor-pointer"
                  aria-label="Settings"
                >
                  <Settings size={17} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 border border-slate-700/80">
                  Account Settings
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                </div>
              </div>

              {/* Collapsed Sign Out Shortcut */}
              <div className="relative group">
                <button
                  type="button"
                  onClick={handleLogout}
                  data-slot="sign-out"
                  className="w-10 h-10 flex items-center justify-center rounded-xl transition-all cursor-pointer"
                  aria-label="Sign Out"
                >
                  <LogOut size={17} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 border border-slate-700/80">
                  Sign Out
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
};

export default Sidebar;
