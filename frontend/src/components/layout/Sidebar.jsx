import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Users, Building2, User, Settings, Search, Briefcase,
  HelpCircle, BookOpen, ChevronRight, MessageSquare, ChevronLeft, Scale,
  Sliders, Calendar, Sparkles, CheckCircle2, PanelLeftClose, PanelLeftOpen,
  PanelLeft, X
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import { toggleSidebar, closeSidebar } from '../../redux/slices/uiSlice';

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { role: userRole } = useSelector(state => state.auth);
  const { isSidebarOpen } = useSelector(state => state.ui);

  const normRole = (userRole || '').toUpperCase();
  const isAdminRole = normRole === 'ADMIN';
  const isHRRole = normRole === 'HR';
  const isCandidateRole = normRole === 'CANDIDATE';
  const isHRPage = location.pathname.startsWith('/hr');
  const isHR = isHRRole || isHRPage;

  // Grouped navigation structure for modern SaaS UX
  const getNavSections = () => {
    if (isAdminRole) {
      return [
        {
          title: 'ANALYTICS & METRICS',
          items: [
            { label: 'Dashboard', path: '/admin/dashboard', icon: <LayoutDashboard size={19} /> },
          ]
        },
        {
          title: 'MANAGEMENT',
          items: [
            { label: 'User Directory', path: '/admin/users', icon: <Users size={19} /> },
            { label: 'Job Postings', path: '/admin/jobmanagement', icon: <Briefcase size={19} /> },
            { label: 'System Config', path: '/admin/system-config', icon: <Sliders size={19} /> },
          ]
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/admin/messages', icon: <MessageSquare size={19} /> }
          ]
        }
      ];
    }

    if (isHR) {
      return [
        {
          title: 'TALENT PIPELINE',
          items: [
            { label: 'Dashboard', path: '/hr/dashboard', icon: <LayoutDashboard size={19} /> },
            { 
              label: 'AI Screening', 
              path: '/hr/screeningportal', 
              icon: <User size={19} />, 
              badge: 'AI', 
              badgeColor: 'bg-gradient-to-r from-[#D60041] to-pink-600 text-white shadow-2xs' 
            },
            { label: 'Interview Scheduling', path: '/hr/scheduling', icon: <Calendar size={19} /> },
            { label: 'Candidate Comparison', path: '/hr/comparecandidates', icon: <Scale size={19} /> },
          ]
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/hr/messages', icon: <MessageSquare size={19} /> }
          ]
        }
      ];
    }

    if (isCandidateRole) {
      return [
        {
          title: 'CAREER',
          items: [
            { label: 'Dashboard', path: '/candidate/dashboard', icon: <LayoutDashboard size={19} /> },
            { label: 'Find Jobs', path: '/candidate/findjobs', icon: <Search size={19} /> },
            { label: 'Smart Match', path: '/candidate/smart-upload', icon: <Sparkles size={19} />, badge: 'AI', badgeColor: 'bg-gradient-to-r from-[#D60041] to-pink-600 text-white shadow-2xs' },
          ]
        },
        {
          title: 'COMMUNICATION',
          items: [
            { label: 'Messages', path: '/candidate/messages', icon: <MessageSquare size={19} /> }
          ]
        }
      ];
    }

    return [
      {
        title: 'EXPLORE',
        items: [
          { label: 'About', path: '/aboutpage', icon: <BookOpen size={19} /> },
          { label: 'Careers', path: '/careerspage', icon: <Briefcase size={19} /> }
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
      {/* Mobile Drawer Backdrop (Active on mobile/tablet for all portals) */}
      <div 
        className={`lg:hidden fixed inset-0 bg-slate-950/60 backdrop-blur-xs z-[55] transition-opacity duration-300 ${
          isSidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => dispatch(closeSidebar())}
        aria-hidden="true"
      />

      <aside
        className={`
          fixed top-0 bottom-0 left-0 z-[60] flex flex-col bg-white/95 backdrop-blur-xl border-r border-slate-200/90
          transition-all duration-300 ease-in-out shadow-[1px_0_16px_rgba(0,0,0,0.03)]
          /* Mobile Drawer Sizing & Position */
          w-72 max-w-[85vw] h-full ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'}
          /* Desktop Docked Sidebar */
          lg:translate-x-0 lg:top-[73px] lg:bottom-auto lg:h-[calc(100vh-73px)] lg:z-[40]
          ${isSidebarOpen ? 'lg:w-64' : 'lg:w-20'}
        `}
      >
        {/* Floating Border Edge Toggle Button (Desktop Only) */}
        <button
          type="button"
          onClick={() => dispatch(toggleSidebar())}
          className="hidden lg:flex absolute -right-3.5 top-5 w-7 h-7 rounded-full bg-white border border-slate-200 shadow-md hover:shadow-lg items-center justify-center text-slate-400 hover:text-[#D60041] hover:scale-110 active:scale-95 transition-all cursor-pointer z-50 group hover:border-rose-200"
          title={isSidebarOpen ? "Collapse sidebar (Ctrl+B)" : "Expand sidebar (Ctrl+B)"}
          aria-label={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
        >
          {isSidebarOpen ? (
            <ChevronLeft size={14} className="group-hover:-translate-x-0.5 transition-transform text-slate-600 group-hover:text-[#D60041]" />
          ) : (
            <ChevronRight size={14} className="group-hover:translate-x-0.5 transition-transform text-slate-600 group-hover:text-[#D60041]" />
          )}
        </button>

        {/* WORKSPACE BRANDING HEADER */}
        <div className={`p-3.5 sm:p-4 border-b border-slate-100 flex items-center shrink-0 ${isSidebarOpen ? 'justify-between' : 'justify-center flex-col gap-2.5'}`}>
          {isSidebarOpen ? (
            <>
              <div className="flex items-center space-x-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#D60041] via-[#E11D48] to-[#FF4D6D] text-white flex items-center justify-center shadow-md shadow-[#D60041]/25 shrink-0 ring-2 ring-rose-50">
                  {isHR ? <Building2 size={18} /> : isAdminRole ? <Sliders size={18} /> : <Sparkles size={18} />}
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-black text-slate-900 tracking-tight leading-tight truncate">
                    {getWorkspaceTitle()}
                  </h3>
                  <div className="flex items-center space-x-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shadow-xs shadow-emerald-500/50" />
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider truncate">
                      {getWorkspaceSubtitle()} • Online
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {/* Mobile Close Button */}
                <button
                  type="button"
                  onClick={() => dispatch(closeSidebar())}
                  className="lg:hidden p-1.5 rounded-xl text-slate-400 hover:text-slate-800 hover:bg-slate-100 active:scale-95 transition-all cursor-pointer"
                  title="Close sidebar"
                  aria-label="Close sidebar"
                >
                  <X size={18} />
                </button>

                {/* Desktop Collapse Button */}
                <button
                  type="button"
                  onClick={() => dispatch(toggleSidebar())}
                  className="hidden lg:flex w-8 h-8 items-center justify-center rounded-xl text-slate-400 hover:text-slate-800 hover:bg-slate-100 active:scale-95 transition-all shadow-2xs border border-transparent hover:border-slate-200 cursor-pointer"
                  title="Collapse sidebar (Ctrl+B)"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeftClose size={18} />
                </button>
              </div>
            </>
          ) : (
            <>
              {/* Collapsed Workspace Icon with Tooltip */}
              <div className="relative group">
                <div 
                  onClick={() => dispatch(toggleSidebar())}
                  className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#D60041] via-[#E11D48] to-[#FF4D6D] text-white flex items-center justify-center shadow-md shadow-[#D60041]/25 cursor-pointer hover:scale-105 transition-all ring-2 ring-rose-50"
                  title="Click to expand sidebar"
                >
                  {isHR ? <Building2 size={19} /> : isAdminRole ? <Sliders size={19} /> : <Sparkles size={19} />}
                </div>
                <div className="absolute left-[calc(100%+14px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-950 text-white text-xs font-semibold rounded-lg shadow-2xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50 border border-slate-800 flex items-center gap-1.5">
                  <span>{getWorkspaceTitle()}</span>
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-950" />
                </div>
              </div>

              {/* Dedicated Expand Trigger Button */}
              <button
                type="button"
                onClick={() => dispatch(toggleSidebar())}
                className="w-8 h-8 flex items-center justify-center text-slate-400 hover:text-[#D60041] hover:bg-rose-50 rounded-lg transition-all active:scale-95 border border-slate-200/80 hover:border-rose-200 shadow-2xs cursor-pointer"
                title="Expand sidebar (Ctrl+B)"
                aria-label="Expand sidebar"
              >
                <PanelLeftOpen size={16} />
              </button>
            </>
          )}
        </div>

        {/* NAVIGATION ITEMS */}
        <div className="flex-grow overflow-y-auto overflow-x-hidden custom-scrollbar px-3 py-3 space-y-4">
          {navSections.map((section, sIdx) => (
            <div key={sIdx} className="space-y-1">
              {isSidebarOpen ? (
                <div className="px-3 pt-1 pb-1">
                  <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">
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
                        className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl transition-all duration-200 group relative cursor-pointer ${
                          isActive
                            ? 'bg-gradient-to-r from-rose-50/90 to-pink-50/40 text-[#D60041] font-bold border border-rose-100 shadow-2xs'
                            : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/70 font-semibold'
                        }`}
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          {isActive && (
                            <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#D60041] rounded-r-full shadow-xs" />
                          )}
                          <span className={`transition-all duration-200 shrink-0 ${
                            isActive ? 'text-[#D60041] scale-105' : 'text-slate-400 group-hover:text-slate-700 group-hover:scale-105'
                          }`}>
                            {item.icon}
                          </span>
                          <span className="text-[13px] tracking-tight truncate leading-tight">
                            {item.label}
                          </span>
                        </div>
                        {item.badge && (
                          <span className={`text-[9px] font-black uppercase tracking-wider px-1.5 py-0.5 rounded-md shrink-0 shadow-2xs ${
                            item.badgeColor || 'bg-gradient-to-r from-[#D60041] to-pink-600 text-white'
                          }`}>
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
                        className={`w-11 h-11 flex items-center justify-center rounded-xl transition-all duration-200 relative cursor-pointer ${
                          isActive
                            ? 'bg-rose-50 text-[#D60041] shadow-2xs border border-rose-200/80'
                            : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100/80'
                        }`}
                        aria-label={item.label}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-5 bg-[#D60041] rounded-r-full shadow-xs" />
                        )}
                        <span className={`transition-transform duration-200 ${
                          isActive ? 'text-[#D60041] scale-110' : 'text-slate-400 group-hover:text-slate-800 group-hover:scale-110'
                        }`}>
                          {item.icon}
                        </span>
                        {item.badge && (
                          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#D60041] rounded-full border-2 border-white animate-pulse" />
                        )}
                      </button>

                      {/* Modern floating tooltip */}
                      <div className="absolute left-[calc(100%+14px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-950 text-white text-xs font-semibold rounded-lg shadow-2xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50 flex items-center gap-2 border border-slate-800">
                        <span>{item.label}</span>
                        {item.badge && (
                          <span className="bg-[#D60041] text-white text-[9px] px-1 py-0.5 rounded font-black uppercase tracking-wider">
                            {item.badge}
                          </span>
                        )}
                        <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-950" />
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
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-xs shadow-emerald-500/50" />
                  <span className="text-[11px] font-bold text-slate-800">ARAS Engine</span>
                </div>
                <span className="text-[9px] font-black uppercase tracking-wider text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200/80">
                  v2.4 Online
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
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-2 py-1">
              {/* Collapsed Settings Shortcut with Tooltip */}
              <div className="relative group">
                <button 
                  onClick={() => navigate(settingsPath)}
                  className="p-2 text-slate-400 hover:text-[#D60041] hover:bg-rose-50 rounded-xl transition-all cursor-pointer"
                  aria-label="Settings"
                >
                  <Settings size={18} />
                </button>
                <div className="absolute left-[calc(100%+14px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-950 text-white text-xs font-semibold rounded-lg shadow-2xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50 border border-slate-800">
                  Settings
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-950" />
                </div>
              </div>

              {/* Collapsed Help Shortcut with Tooltip */}
              <div className="relative group">
                <button 
                  onClick={() => navigate('/aboutpage')}
                  className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all cursor-pointer"
                  aria-label="Help"
                >
                  <HelpCircle size={18} />
                </button>
                <div className="absolute left-[calc(100%+14px)] top-1/2 -translate-y-1/2 px-2.5 py-1.5 bg-slate-950 text-white text-xs font-semibold rounded-lg shadow-2xl whitespace-nowrap opacity-0 group-hover:opacity-100 transition-all duration-150 pointer-events-none z-50 border border-slate-800">
                  Help Center
                  <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-slate-950" />
                </div>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* Desktop Main Content Spacer (matches docked sidebar width) */}
      <div 
        className={`hidden lg:block transition-all duration-300 ease-in-out shrink-0 ${
          isSidebarOpen ? 'w-64' : 'w-20'
        }`} 
        aria-hidden="true"
      />
    </>
  );
};

export default Sidebar;