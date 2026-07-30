import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Users, Database, Building2, User, Settings, Search, FileText, Info, Briefcase,
  HelpCircle, BookOpen, ChevronRight, X, MessageSquare, Menu, ChevronLeft, Scale,
  Sliders, Activity
} from 'lucide-react';
import { useSelector, useDispatch } from 'react-redux';
import { toggleSidebar, closeSidebar } from '../../redux/slices/uiSlice';

const Sidebar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const dispatch = useDispatch();
  const { role: userRole } = useSelector(state => state.auth);
  const { isSidebarOpen } = useSelector(state => state.ui);

  const isAdminRole = userRole === 'ADMIN';
  const isHRRole = userRole === 'HR';
  const isCandidateRole = userRole === 'CANDIDATE';

  const getNavItems = () => {
    const items = [];
    if (isAdminRole) {
      items.push(
        { label: 'Dashboard', path: '/admin/dashboard', icon: <LayoutDashboard size={22} /> },
        { label: 'Performance', path: '/admin/performance', icon: <Activity size={22} /> },
        { label: 'User Management', path: '/admin/users', icon: <Users size={22} /> },
        { label: 'Jobs', path: '/admin/jobmanagement', icon: <Briefcase size={22} /> },
        { label: 'System Config', path: '/admin/system-config', icon: <Sliders size={22} /> },
        { label: 'Messages', path: '/admin/messages', icon: <MessageSquare size={22} /> },
        { label: 'Audit Logs', path: '/admin/auditlog', icon: <Database size={22} /> }
      );
    } else if (isHRRole) {
      items.push(
        { label: 'Dashboard', path: '/hr/dashboard', icon: <Building2 size={22} /> },
        { label: 'Screening', path: '/hr/screeningportal', icon: <User size={22} /> },
        { label: 'Compare Candidates', path: '/hr/comparecandidates', icon: <Scale size={22} /> },
        { label: 'Messages', path: '/hr/messages', icon: <MessageSquare size={22} /> }
      );
    } else if (isCandidateRole) {
      items.push(
        { label: 'Dashboard', path: '/candidate/dashboard', icon: <LayoutDashboard size={22} /> },
        { label: 'Find Jobs', path: '/candidate/findjobs', icon: <Search size={22} /> },

        { label: 'Messages', path: '/candidate/messages', icon: <MessageSquare size={22} /> }
      );
    } else {
      items.push(
        { label: 'About', path: '/aboutpage', icon: <Info size={22} /> },
        { label: 'Careers', path: '/careerspage', icon: <Briefcase size={22} /> }
      );
    }
    return items;
  };

  const navItems = getNavItems();

  return (
    <>
      {/* Mobile Backdrop - Adjusted top to start below header */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 top-[81px] bg-gray-900/40 backdrop-blur-sm z-[35] lg:hidden transition-opacity duration-300"
          onClick={() => dispatch(closeSidebar())}
        />
      )}

      <aside
        className={`
          fixed top-[81px] left-0 
          bg-white border-r border-gray-100 
          h-[calc(100vh-81px)] 
          z-[40] flex flex-col transition-all duration-300 ease-in-out
          ${isSidebarOpen ? 'w-64' : 'w-20 lg:translate-x-0 -translate-x-full'}
        `}
      >
        {/* SIDEBAR TOGGLE AREA */}
        <div className={`p-4 flex items-center shrink-0 ${isSidebarOpen ? 'justify-end' : 'justify-center'}`}>
          <button
            onClick={() => dispatch(toggleSidebar())}
            className="p-2.5 hover:bg-red-50 hover:text-[#D60041] rounded-xl text-gray-500 transition-all active:scale-95 bg-gray-50 border border-gray-100 shadow-sm"
          >
            {isSidebarOpen ? <ChevronLeft size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* NAVIGATION ITEMS */}
        <div className="flex-grow overflow-y-auto scrollbar-hide px-3 py-2">
          {isSidebarOpen && (
            <div className="mb-4 px-4">
              <p className="text-[10px] font-black uppercase tracking-widest text-gray-400">
                Menu
              </p>
            </div>
          )}

          <nav className="space-y-1.5">
            {navItems.map((item, index) => {
              const isActive = location.pathname === item.path;
              return (
                <button
                  key={index}
                  onClick={() => {
                    navigate(item.path);
                    if (window.innerWidth < 1024) dispatch(closeSidebar());
                  }}
                  className={`w-full flex items-center rounded-2xl transition-all duration-300 group relative ${isSidebarOpen ? 'px-4 py-3.5 space-x-3.5' : 'p-3.5 justify-center'
                    } ${isActive
                      ? 'bg-red-50 text-[#D60041] shadow-sm'
                      : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'
                    }`}
                  title={!isSidebarOpen ? item.label : ""}
                >
                  <span className={`transition-all duration-300 shrink-0 ${isActive ? 'text-[#D60041] scale-110' : 'text-gray-400 group-hover:text-gray-600 group-hover:scale-110'
                    }`}>
                    {item.icon}
                  </span>

                  {isSidebarOpen && (
                    <span className="text-sm font-bold tracking-tight whitespace-nowrap overflow-hidden animate-in fade-in duration-300">
                      {item.label}
                    </span>
                  )}

                  {/* Indicators */}
                  {isActive && (
                    <div className={`absolute left-0 bg-[#D60041] rounded-r-full transition-all ${isSidebarOpen ? 'w-1 h-6' : 'w-1.5 h-8'
                      }`} />
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        {/* FOOTER SECTION */}
        <div className="p-4 border-t border-gray-50 bg-gray-50/30">
          {isSidebarOpen ? (
            <div className="bg-white border border-gray-100 rounded-[24px] p-4 shadow-sm">
              <div className="space-y-3">
                <button className="w-full flex items-center space-x-3 text-[11px] font-bold text-gray-600 hover:text-[#D60041] group transition-colors">
                  <div className="p-1.5 bg-blue-50 rounded-lg text-blue-500 group-hover:bg-[#D60041] group-hover:text-white transition-all">
                    <HelpCircle size={14} />
                  </div>
                  <span>Help Center</span>
                </button>
                <button className="w-full flex items-center space-x-3 text-[11px] font-bold text-gray-600 hover:text-[#D60041] group transition-colors">
                  <div className="p-1.5 bg-orange-50 rounded-lg text-orange-500 group-hover:bg-[#D60041] group-hover:text-white transition-all">
                    <BookOpen size={14} />
                  </div>
                  <span>Docs</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center space-y-4 py-2">
              <HelpCircle size={20} className="text-blue-400 hover:text-[#D60041] cursor-pointer transition-colors" />
              <BookOpen size={20} className="text-orange-400 hover:text-[#D60041] cursor-pointer transition-colors" />
            </div>
          )}
        </div>
      </aside>

      {/* Main Content Spacer */}
      <div className={`hidden lg:block transition-all duration-300 shrink-0 ${isSidebarOpen ? 'w-64' : 'w-20'}`} />
    </>
  );
};

export default Sidebar;