import React from 'react';
import { Helmet } from 'react-helmet-async';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ChatLayout from '../../components/chat/ChatLayout';
import { Shield, Clock } from 'lucide-react';
import { useSelector } from 'react-redux';
import { RootState } from '../../redux/store';
import { useGetActiveUsersCountQuery } from '../../redux/api/apiSlice';

const MessagesPage: React.FC = () => {
    const { role } = useSelector((state: RootState) => state.auth);
    const showActiveWidget = role === 'HR' || role === 'ADMIN';

    const { data: activeData } = useGetActiveUsersCountQuery(undefined, {
        skip: !showActiveWidget,
    }) as { data: { count?: number } | undefined };
    const activeCount = activeData?.count || 1;

    return (
        <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
            <Helmet>
                <title>Messages - System Chat</title>
            </Helmet>
            
            <Header />
            
            <div className="flex flex-1 min-h-0">
                <Sidebar />
                <main className="flex-1 min-w-0 w-full max-w-full px-3 sm:px-6 md:px-10 py-3 sm:py-6 md:py-8 flex flex-col animate-in fade-in duration-300">
                    
                    {/* Page Header */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-3 sm:mb-6 gap-3">
                        <div>
                            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-pink-50 border border-pink-100/80 text-[11px] font-bold text-[#D60041] uppercase tracking-wider mb-1 sm:mb-1.5">
                                <Shield size={12} className="shrink-0" />
                                <span>End-to-End Encrypted</span>
                            </div>
                            <h1 className="text-xl sm:text-2xl md:text-3xl font-black text-gray-900 tracking-tight leading-tight">
                                Communication Center
                            </h1>
                            <p className="text-xs sm:text-sm text-gray-500 font-medium mt-0.5 sm:mt-1 flex items-center gap-1.5">
                                <Clock size={13} className="text-gray-400 shrink-0" />
                                <span>Real-time messaging with candidates and team members</span>
                            </p>
                        </div>
                        
                        {showActiveWidget && (
                            <div className="flex items-center gap-2.5 px-3 py-1.5 sm:px-5 sm:py-2.5 bg-white border border-gray-100 rounded-full sm:rounded-2xl shadow-xs self-start sm:self-auto">
                                <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse shrink-0"></div>
                                <div className="flex items-baseline gap-1.5">
                                    <span className="text-xs sm:text-sm font-black text-gray-900">{activeCount}</span>
                                    <span className="text-[11px] sm:text-xs font-semibold text-gray-500">
                                        {activeCount === 1 ? 'User Online' : 'Users Online'}
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Chat Module Container */}
                    <div className="flex-1 min-h-0 flex flex-col">
                        <ChatLayout isFullPage={true} />
                    </div>
                </main>
            </div>
        </div>
    );
};

export default MessagesPage;
