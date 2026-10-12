import React, { ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Users, Building2, User, Settings, Search, Briefcase,
  HelpCircle, BookOpen, MessageSquare, Scale, Sliders, Calendar, Sparkles,
  PanelLeftClose, PanelLeftOpen, X, LogOut
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import { toggleSidebar, closeSidebar } from '../../redux/slices/uiSlice';
import { logout as logoutAction } from '../../redux/slices/authSlice';
import { RootState } from '../../redux/store';

export interface NavItem {
  label: string;
  path: string;
  icon: ReactNode;
  badge?: string;
  badgeColor?: string;
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

  const handleLogout = () => {
    dispatch(logoutAction());
    navigate('/');
    window.location.reload();
  };

  const normRole = (userRole || '').toUpperCase();
  const isAdminRole = normRole === 'ADMIN';
  const isHRRole = normRole === 'HR';
  const isCandidateRole = normRole === 'CANDIDATE';
  const isHRPage = location.pathname.startsWith('/hr');
  const isHR = isHRRole || isHRPage;

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
            { label: 'Messages', path: '/admin/messages', icon: <MessageSquare size={18} /> },
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
            {
              label: 'AI Screening',
              path: '/hr/screeningportal',
              icon: <User size={18} />,
              badge: 'AI',
              badgeColor: 'bg-[#D60041] text-white',
            },
            { label: 'Interview Scheduling', path: '/hr/scheduling', icon: <Calendar size={18} /> },
            { label: 'Candidate Comparison', path: '/hr/comparecandidates', icon: <Scale size={18} /> },
          ],
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/hr/messages', icon: <MessageSquare size={18} /> },
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
            { label: 'Find Jobs', path: '/candidate/findjobs', icon: <Search size={18} /> },
            {
              label: 'Smart Match',
              path: '/candidate/smart-upload',
              icon: <Sparkles size={18} />,
              badge: 'AI',
              badgeColor: 'bg-[#D60041] text-white',
            },
          ],
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/candidate/messages', icon: <MessageSquare size={18} /> },
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
    if (isCandidateRole) return 'Career Portal';
    return 'Mariwasa ARAS';
  };

  const getWorkspaceSubtitle = () => {
    if (isHR) return 'Talent Operations';
    if (isAdminRole) return 'System Control';
    if (isCandidateRole) return 'Candidate Hub';
    return 'Resume Analysis';
  };

  const settingsPath = isHR ? '/hr/settings' : isAdminRole ? '/admin/settings' : '/accountsettings';

  return (
    <>
      {/* Mobile Drawer Backdrop (Active on mobile/tablet < 1024px) */}
      <div
        className={`lg:hidden fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-[55] transition-opacity duration-300 ${
          isSidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => dispatch(closeSidebar())}
        aria-hidden="true"
      />

      <aside
        className={`
          fixed top-0 bottom-0 left-0 z-[60] flex flex-col bg-white border-r border-slate-200/90
          transition-all duration-200 ease-in-out shadow-[1px_0_12px_rgba(0,0,0,0.03)]
          /* Mobile Drawer */
          w-72 max-w-[85vw] h-full ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          /* Desktop Docked Sidebar */
          lg:translate-x-0 lg:top-[73px] lg:bottom-auto lg:h-[calc(100vh-73px)] lg:z-[40]
          ${isSidebarOpen ? 'lg:w-64' : 'lg:w-20'}
        `}
      >
        {/* WORKSPACE HEADER */}
        <div className={`p-4 border-b border-slate-100 flex items-center shrink-0 ${isSidebarOpen ? 'justify-between' : 'justify-center'}`}>
          {isSidebarOpen ? (
            <>
              {/* Workspace Identity */}
              <div className="flex items-center space-x-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#D60041] to-[#B50037] text-white flex items-center justify-center shadow-xs shadow-[#D60041]/25 shrink-0">
                  {isHR ? <Building2 size={18} /> : isAdminRole ? <Sliders size={18} /> : <Sparkles size={18} />}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-black text-slate-900 tracking-tight leading-tight truncate">
                    {getWorkspaceTitle()}
                  </h3>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-xs" />
                    <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider truncate">
                      {getWorkspaceSubtitle()} • Online
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
                  className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 active:scale-95 transition-colors cursor-pointer"
                  title="Close sidebar"
                  aria-label="Close sidebar"
                >
                  <X size={18} />
                </button>

                {/* Desktop: Collapse Sidebar Button */}
                <button
                  type="button"
                  onClick={() => dispatch(toggleSidebar())}
                  className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-800 hover:bg-slate-100 active:scale-95 transition-colors cursor-pointer"
                  title="Collapse sidebar (Ctrl+B)"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeftClose size={18} />
                </button>
              </div>
            </>
          ) : (
            /* Collapsed Mode: Single Expand Sidebar Button */
            <div className="relative group flex justify-center py-0.5">
              <button
                type="button"
                onClick={() => dispatch(toggleSidebar())}
                className="w-10 h-10 rounded-xl bg-slate-50 hover:bg-rose-50 text-slate-600 hover:text-[#D60041] border border-slate-200/80 hover:border-rose-200 flex items-center justify-center transition-all cursor-pointer active:scale-95 shadow-2xs group"
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
        <div className="flex-grow overflow-y-auto overflow-x-hidden custom-scrollbar px-3 py-3 space-y-4">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              {isSidebarOpen ? (
                <div className="px-3 pt-1 pb-1">
                  <p className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                    {section.title}
                  </p>
                </div>
              ) : (
                <div className="w-full flex justify-center py-1">
                  <div className="w-5 border-t border-slate-200" />
                </div>
              )}

              <nav className="space-y-1">
                {section.items.map((item, index) => {
                  const isActive = location.pathname === item.path;

                  if (isSidebarOpen) {
                    return (
                      <button
                        key={index}
                        onClick={() => {
                          navigate(item.path);
                          if (window.innerWidth < 1024) dispatch(closeSidebar());
                        }}
                        className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl transition-all duration-150 group relative cursor-pointer ${
                          isActive
                            ? 'bg-rose-50/90 text-[#D60041] font-bold border border-rose-100 shadow-2xs'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50 font-medium'
                        }`}
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          {isActive && (
                            <span className="w-1 h-4 bg-[#D60041] rounded-full shrink-0 -ml-1 mr-0.5" />
                          )}
                          <span
                            className={`transition-colors shrink-0 ${
                              isActive
                                ? 'text-[#D60041]'
                                : 'text-slate-400 group-hover:text-slate-700'
                            }`}
                          >
                            {item.icon}
                          </span>
                          <span className="text-[13px] tracking-tight truncate leading-tight">
                            {item.label}
                          </span>
                        </div>
                        {item.badge && (
                          <span
                            className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md shrink-0 shadow-2xs ${
                              item.badgeColor || 'bg-[#D60041] text-white'
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </button>
                    );
                  }

                  // Collapsed View with Tooltip
                  return (
                    <div key={index} className="relative group flex justify-center w-full py-0.5">
                      <button
                        onClick={() => {
                          navigate(item.path);
                          if (window.innerWidth < 1024) dispatch(closeSidebar());
                        }}
                        className={`w-10 h-10 flex items-center justify-center rounded-xl transition-all duration-150 relative cursor-pointer ${
                          isActive
                            ? 'bg-rose-50 text-[#D60041] shadow-2xs border border-rose-200/80 font-bold'
                            : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100/80'
                        }`}
                        aria-label={item.label}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-[#D60041] rounded-r-full" />
                        )}
                        <span
                          className={`transition-colors ${
                            isActive ? 'text-[#D60041]' : 'text-slate-400 group-hover:text-slate-800'
                          }`}
                        >
                          {item.icon}
                        </span>
                        {item.badge && (
                          <span className="absolute top-1 right-1 w-2 h-2 bg-[#D60041] rounded-full border-2 border-white animate-pulse" />
                        )}
                      </button>

                      {/* Tooltip */}
                      <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 flex items-center gap-2 border border-slate-800">
                        <span>{item.label}</span>
                        {item.badge && (
                          <span className="bg-[#D60041] text-white text-[9px] px-1 py-0.5 rounded font-black uppercase tracking-wider">
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
        <div className="p-3 border-t border-slate-100 bg-slate-50/50 shrink-0">
          {isSidebarOpen ? (
            <div className="bg-white border border-slate-200/80 rounded-2xl p-3 shadow-2xs space-y-2.5">
              <div className="flex items-center justify-between px-0.5">
                <div className="flex items-center space-x-1.5">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-xs" />
                  <span className="text-[11px] font-bold text-slate-800">ARAS Engine</span>
                </div>
                <span className="text-[9px] font-black uppercase tracking-wider text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200/80">
                  Online
                </span>
              </div>
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-slate-500">
                <button
                  onClick={() => {
                    navigate(settingsPath);
                    if (window.innerWidth < 1024) dispatch(closeSidebar());
                  }}
                  className="flex items-center space-x-1.5 text-[11px] font-bold hover:text-[#D60041] transition-colors py-1 px-1.5 rounded-lg hover:bg-slate-50 cursor-pointer"
                  title="Account Settings"
                >
                  <Settings size={13} />
                  <span>Settings</span>
                </button>
                <button
                  onClick={() => {
                    navigate('/aboutpage');
                    if (window.innerWidth < 1024) dispatch(closeSidebar());
                  }}
                  className="flex items-center space-x-1.5 text-[11px] font-bold hover:text-[#D60041] transition-colors py-1 px-1.5 rounded-lg hover:bg-slate-50 cursor-pointer"
                  title="Documentation & Help"
                >
                  <HelpCircle size={13} />
                  <span>Help</span>
                </button>
              </div>

              {/* Sign Out Action */}
              <div className="pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-xl text-xs font-bold text-rose-600 bg-rose-50/70 hover:bg-rose-100 hover:text-rose-700 transition-colors border border-rose-100 cursor-pointer active:scale-95"
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
                  onClick={() => navigate(settingsPath)}
                  className="p-2 text-slate-400 hover:text-[#D60041] hover:bg-rose-50 rounded-xl transition-all cursor-pointer"
                  aria-label="Settings"
                >
                  <Settings size={18} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 border border-slate-800">
                  Settings
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                </div>
              </div>

              {/* Collapsed Help Shortcut */}
              <div className="relative group">
                <button
                  onClick={() => navigate('/aboutpage')}
                  className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all cursor-pointer"
                  aria-label="Help"
                >
                  <HelpCircle size={18} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 border border-slate-800">
                  Help Center
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                </div>
              </div>

              {/* Collapsed Sign Out Shortcut */}
              <div className="relative group">
                <button
                  type="button"
                  onClick={handleLogout}
                  className="p-2 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-xl transition-all cursor-pointer"
                  aria-label="Sign Out"
                >
                  <LogOut size={18} />
                </button>
                <div className="absolute left-[calc(100%+12px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-900 text-white text-xs font-semibold rounded-lg shadow-xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-150 pointer-events-none z-50 border border-slate-800">
                  Sign Out
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-900" />
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Desktop Main Content Spacer (matches docked sidebar width) */}
      <div
        className={`hidden lg:block transition-all duration-200 ease-in-out shrink-0 ${
          isSidebarOpen ? 'w-64' : 'w-20'
        }`}
        aria-hidden="true"
      />
    </>
  );
};

export default Sidebar;
