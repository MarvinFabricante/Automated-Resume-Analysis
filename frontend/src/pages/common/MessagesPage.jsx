import React from 'react';
import { Helmet } from 'react-helmet-async';
import Header from '../../components/layout/Header';
import Sidebar from '../../components/layout/Sidebar';
import ChatLayout from '../../components/chat/ChatLayout';
import { MessageSquare, Shield, Clock } from 'lucide-react';
import { useSelector } from 'react-redux';
import { useGetActiveUsersCountQuery } from '../../redux/api/apiSlice';

const MessagesPage = () => {
    const { role } = useSelector((state) => state.auth);
    const showActiveWidget = role === 'HR' || role === 'ADMIN';

    const { data: activeData } = useGetActiveUsersCountQuery(undefined, {
        skip: !showActiveWidget,
    });
    const activeCount = activeData?.count || 1;

    return (
        <div className="bg-[#FCFCFC] text-gray-800 antialiased min-h-screen font-['Inter'] flex flex-col">
            <Helmet>
                <title>Messages - System Chat</title>
            </Helmet>
            
            <Header />
            
            <div className="flex flex-1">
                <Sidebar />
                <main className="flex-1 w-full max-w-full px-4 sm:px-6 md:px-10 py-6 sm:py-10 flex flex-col animate-in fade-in duration-500">
                    
                    <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-8 gap-4">
                        <div>
                            <div className="flex items-center gap-2 text-[10px] font-black text-[#D60041] uppercase tracking-[0.2em] mb-2">
                                <Shield size={12} />
                                <span>End-to-End Encrypted</span>
                            </div>
                            <h1 className="text-3xl font-black text-gray-900 tracking-tight">Communication Center</h1>
                            <p className="text-gray-500 font-medium mt-1 flex items-center gap-2">
                                <Clock size={14} className="text-gray-400" />
                                Real-time messaging with candidates and team members.
                            </p>
                        </div>
                        
                        {showActiveWidget && (
                            <div className="hidden lg:flex items-center gap-6 px-6 py-3 bg-white border border-gray-100 rounded-2xl shadow-sm">
                                <div className="text-center">
                                    <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Active Users</p>
                                    <div className="flex items-center justify-center gap-1.5">
                                        <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                                        <span className="text-sm font-black text-gray-900">
                                            {activeCount} {activeCount === 1 ? 'User' : 'Users'} Online
                                        </span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="flex-1 min-h-[600px]">
                        <ChatLayout isFullPage={true} />
                    </div>
                </main>
            </div>
        </div>
    );
};

export default MessagesPage;
