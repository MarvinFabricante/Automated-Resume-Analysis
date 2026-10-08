import React, { useState, useEffect, useRef } from 'react';
import { MessageSquare, Send, Minus, Search, ArrowLeft, Circle, X } from 'lucide-react';
import chatService from '../../services/chatService';
import { useSelector } from 'react-redux';
import { WS_BASE_URL } from '../../services/api';

const ChatWidget = () => {
    const { profileImageUrl: myProfileImage } = useSelector(state => state.auth);
    const [isOpen, setIsOpen] = useState(false);
    const [view, setView] = useState('contacts'); // 'contacts' | 'chat'
    const [contacts, setContacts] = useState([]);
    const [search, setSearch] = useState('');
    const [activeContact, setActiveContact] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [isMobileScrolling, setIsMobileScrolling] = useState(false);
    const wsRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const messagesEndRef = useRef(null);
    const activeContactRef = useRef(null);

    // Auto-close on mobile scroll/touch and smooth hide floater during active scrolling
    useEffect(() => {
        let scrollTimeout = null;
        let lastScrollY = window.scrollY || window.pageYOffset || 0;
        let touchStartY = 0;

        const handleScroll = () => {
            const currentScrollY = window.scrollY || window.pageYOffset || 0;
            const diff = Math.abs(currentScrollY - lastScrollY);

            if (window.innerWidth < 768) {
                // If chat modal is open on mobile and user scrolls, close it immediately
                if (isOpen && diff > 5) {
                    setIsOpen(false);
                }

                // Smoothly tuck floater button away during active mobile scroll
                if (diff > 8) {
                    setIsMobileScrolling(true);
                    clearTimeout(scrollTimeout);
                    scrollTimeout = setTimeout(() => {
                        setIsMobileScrolling(false);
                    }, 800);
                }
            }
            lastScrollY = currentScrollY;
        };

        const handleTouchStart = (e) => {
            if (e.touches && e.touches[0]) {
                touchStartY = e.touches[0].clientY;
            }
        };

        const handleTouchMove = (e) => {
            if (window.innerWidth < 768 && isOpen) {
                const target = e.target;
                const isInsideChat = target && target.closest && target.closest('.chat-window-container');
                // Touching or swiping outside the chat window closes it immediately
                if (!isInsideChat) {
                    setIsOpen(false);
                } else if (e.touches && e.touches[0]) {
                    const currentY = e.touches[0].clientY;
                    const isDragHeader = target && target.closest && target.closest('.chat-drag-header');
                    // Swipe down gesture on drag header closes it
                    if (isDragHeader && (currentY - touchStartY > 35)) {
                        setIsOpen(false);
                    }
                }
            }
        };

        window.addEventListener('scroll', handleScroll, { passive: true });
        window.addEventListener('touchstart', handleTouchStart, { passive: true });
        window.addEventListener('touchmove', handleTouchMove, { passive: true });

        return () => {
            window.removeEventListener('scroll', handleScroll);
            window.removeEventListener('touchstart', handleTouchStart);
            window.removeEventListener('touchmove', handleTouchMove);
            if (scrollTimeout) clearTimeout(scrollTimeout);
        };
    }, [isOpen]);

    // Sync ref with state
    useEffect(() => {
        activeContactRef.current = activeContact;
    }, [activeContact]);

    const token = localStorage.getItem('token');
    const currentUserRole = localStorage.getItem('role') || 'Guest';
    const currentUserId = parseInt(localStorage.getItem('user_id'), 10);


    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // WebSocket Connection
    useEffect(() => {
        if (!token) return;

        let shouldReconnect = true;

        const connectWebSocket = () => {
            if (!shouldReconnect) return;


            const ws = new WebSocket(`${WS_BASE_URL}/chat/ws?token=${encodeURIComponent(token)}`);
            wsRef.current = ws;
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                
                if (data.type === 'new_message') {
                    setMessages(prev => {
                        if (data.client_id) {
                            const index = prev.findIndex(m => m.client_id === data.client_id);
                            if (index !== -1) {
                                const newMessages = [...prev];
                                newMessages[index] = { ...data, is_optimistic: false };
                                return newMessages;
                            }
                        }

                        if (prev.find(m => m.id === data.id)) return prev;
                        
                        const currentActive = activeContactRef.current;
                        const isRelevant = currentActive && (
                            data.sender_id === currentActive.id || 
                            data.receiver_id === currentActive.id ||
                            data.sender_id === currentUserId
                        );
                        
                        if (isRelevant) {
                            return [...prev, data];
                        }
                        return prev;
                    });
                    
                    fetchContacts();
                } else if (data.type === 'status') {
                    setContacts(prev => prev.map(c => 
                        c.id === data.user_id ? { ...c, is_online: data.is_online } : c
                    ));
                    const currentActive = activeContactRef.current;
                    if (currentActive && currentActive.id === data.user_id) {
                        setActiveContact(prev => ({ ...prev, is_online: data.is_online }));
                    }
                }
            };

            ws.onclose = () => {
                if (shouldReconnect) {
                    reconnectTimeoutRef.current = setTimeout(connectWebSocket, 5000);
                }
            };
        };

        connectWebSocket();

        return () => {
            shouldReconnect = false;
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
                reconnectTimeoutRef.current = null;
            }
            if (wsRef.current) {
                const socket = wsRef.current;
                socket.onmessage = null;
                socket.onclose = null;
                socket.onerror = null;

                if (socket.readyState === WebSocket.CONNECTING) {
                    socket.onopen = () => socket.close();
                } else if (socket.readyState === WebSocket.OPEN) {
                    socket.close();
                }
            }
            wsRef.current = null;
        };
    }, [token, currentUserId]);

    const fetchContacts = async () => {
        try {
            const res = await chatService.getContacts(token, search);
            setContacts(res.data.users || []);
        } catch (error) {
            console.error("Failed to fetch contacts", error);
        }
    };

     
    useEffect(() => {
        if (isOpen) {
            fetchContacts();
        }
    }, [isOpen, search]);

    const openChat = async (contact) => {
        setActiveContact(contact);
        setView('chat');
        setLoading(true);
        try {
            const res = await chatService.getMessages(contact.id, token);
            setMessages(res.data);
            
            // Mark as read locally in contacts list
            setContacts(prev => prev.map(c => 
                c.id === contact.id ? { ...c, unread_count: 0 } : c
            ));
        } catch (error) {
            console.error("Failed to fetch messages", error);
        } finally {
            setLoading(false);
        }
    };

    const sendMessage = async () => {
        if (!inputMessage.trim() || !activeContact) return;
        
        const content = inputMessage;
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        // Clear input immediately for "smooth" feel
        setInputMessage('');

        const optimisticMessage = {
            sender_id: currentUserId,
            receiver_id: activeContact.id,
            content: content,
            timestamp: new Date().toISOString(),
            is_optimistic: true,
            client_id: clientId
        };

        // Add to messages state immediately (Optimistic Update)
        setMessages(prev => [...prev, optimisticMessage]);

        const messageData = {
            type: 'send_message',
            receiver_id: activeContact.id,
            content: content,
            client_id: clientId
        };

        // Try sending via WebSocket
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(messageData));
        } else {
            // Fallback to HTTP if WebSocket is not connected
            try {
                const res = await chatService.sendMessage(activeContact.id, content, token);
                
                // Replace optimistic message with real one
                setMessages(prev => prev.map(m => 
                    m.client_id === clientId ? { ...res.data, is_optimistic: false } : m
                ));
                fetchContacts();
            } catch (error) {
                console.error("Failed to send message via HTTP", error);
                // Optionally remove the optimistic message if it failed
                setMessages(prev => prev.filter(m => m.client_id !== clientId));
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    // Don't render chat for guests
    if (!token || currentUserRole.toUpperCase() === 'GUEST') {
        return null;
    }

    return (
        <>
            {/* Mobile Backdrop Overlay - closes modal when tapped or scrolled outside */}
            {isOpen && (
                <div 
                    className="md:hidden fixed inset-0 bg-black/40 backdrop-blur-[2px] z-[998] transition-opacity animate-in fade-in duration-200"
                    onClick={() => setIsOpen(false)}
                    onTouchMove={() => setIsOpen(false)}
                    onTouchStart={() => setIsOpen(false)}
                    aria-label="Close messaging overlay"
                />
            )}

            <div className="fixed bottom-3 right-3 sm:bottom-6 sm:right-6 z-[999] font-['Inter'] pointer-events-auto">
                {/* Chat Window */}
                {isOpen && (
                    <div className="chat-window-container bg-white w-[calc(100vw-1.5rem)] sm:w-[360px] h-[75vh] sm:h-[520px] max-h-[560px] rounded-[24px] shadow-2xl border border-gray-100 flex flex-col overflow-hidden mb-3 sm:mb-4 animate-in slide-in-from-bottom-5 duration-300">
                        {/* Mobile Pull / Swipe Indicator */}
                        <div 
                            className="chat-drag-header md:hidden bg-gray-50 hover:bg-gray-100 py-1.5 flex justify-center cursor-pointer border-b border-gray-100 transition-colors"
                            onClick={() => setIsOpen(false)}
                            title="Tap to close"
                        >
                            <div className="w-10 h-1 bg-gray-300 rounded-full" />
                        </div>
                        
                        {view === 'contacts' ? (
                            <>
                                {/* Contacts Header */}
                                <div className="bg-gradient-to-r from-[#B50037] to-[#D60041] p-3.5 sm:p-4 flex justify-between items-center shadow-sm text-white">
                                    <div className="flex items-center gap-2.5">
                                        <div className="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center shadow-xs">
                                            <MessageSquare className="h-4 w-4 text-white" />
                                        </div>
                                        <div>
                                            <h3 className="text-white font-bold text-sm tracking-tight leading-none">Messages</h3>
                                            <span className="text-[10px] text-pink-100 font-medium">Recruiter Inbox</span>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <button 
                                            onClick={() => setIsOpen(false)} 
                                            className="p-1.5 hover:bg-white/20 active:scale-95 rounded-xl text-white transition-all"
                                            title="Close messages"
                                            aria-label="Close messages"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>
                                
                                {/* Search */}
                                <div className="p-3 bg-gray-50 border-b border-gray-100">
                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4" />
                                        <input 
                                            type="text" 
                                            placeholder="Search contacts..." 
                                            value={search}
                                            onChange={(e) => setSearch(e.target.value)}
                                            className="w-full bg-white border border-gray-200 rounded-full py-2 pl-9 pr-4 text-sm focus:outline-none focus:border-[#D60041] focus:ring-1 focus:ring-[#D60041] transition-all"
                                        />
                                    </div>
                                </div>

                                {/* Contacts List */}
                                <div className="flex-1 overflow-y-auto">
                                    {contacts.length > 0 ? (
                                        contacts.map(contact => (
                                            <div 
                                                key={contact.id} 
                                                onClick={() => openChat(contact)}
                                                className="p-3 border-b border-gray-50 flex items-center gap-3 hover:bg-gray-50 cursor-pointer transition-colors relative"
                                            >
                                                <div className="relative shrink-0">
                                                    {contact.profile_image_url ? (
                                                        <img src={contact.profile_image_url} alt={contact.fullname} className="w-12 h-12 rounded-full object-cover border border-gray-100" />
                                                    ) : (
                                                        <div className="w-12 h-12 bg-pink-50 rounded-full flex items-center justify-center text-[#D60041] font-bold text-lg">
                                                            {contact.fullname.charAt(0).toUpperCase()}
                                                        </div>
                                                    )}
                                                    <div className={`absolute bottom-0 right-0 w-3 h-3 border-2 border-white rounded-full ${contact.is_online ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                                                </div>
                                                <div className="flex-1 min-w-0">
                                                    <div className="flex justify-between items-baseline mb-0.5">
                                                        <h4 className="text-sm font-bold text-gray-900 truncate">{contact.fullname}</h4>
                                                        {contact.last_message_time && (
                                                            <span className="text-[10px] text-gray-400 font-medium">
                                                                {new Date(contact.last_message_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-gray-500 truncate">{contact.last_message || `Role: ${contact.role}`}</p>
                                                </div>
                                                {contact.unread_count > 0 && (
                                                    <div className="w-5 h-5 bg-[#D60041] rounded-full flex items-center justify-center text-[10px] text-white font-bold shadow-sm">
                                                        {contact.unread_count}
                                                    </div>
                                                )}
                                            </div>
                                        ))
                                    ) : (
                                        <div className="p-8 text-center text-gray-500 text-sm">
                                            No contacts found.
                                        </div>
                                    )}
                                </div>
                            </>
                        ) : (
                            <>
                                {/* Chat Header */}
                                <div className="bg-white border-b border-gray-100 p-3.5 sm:p-4 flex justify-between items-center shadow-xs">
                                    <div className="flex items-center gap-2.5 min-w-0">
                                        <button 
                                            onClick={() => setView('contacts')} 
                                            className="p-1.5 hover:bg-gray-100 active:scale-95 rounded-xl text-gray-500 transition-colors shrink-0"
                                            title="Back to contacts"
                                        >
                                            <ArrowLeft className="h-4 w-4" />
                                        </button>
                                        <div className="relative shrink-0">
                                            {activeContact?.profile_image_url ? (
                                                <img src={activeContact.profile_image_url} alt={activeContact.fullname} className="w-8 h-8 rounded-full object-cover border border-gray-100" />
                                            ) : (
                                                <div className="w-8 h-8 bg-pink-50 rounded-full flex items-center justify-center text-[#D60041] font-bold text-xs">
                                                    {activeContact?.fullname?.charAt(0).toUpperCase()}
                                                </div>
                                            )}
                                            <div className={`absolute bottom-0 right-0 w-2.5 h-2.5 border-2 border-white rounded-full ${activeContact?.is_online ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                                        </div>
                                        <div className="min-w-0">
                                            <h4 className="text-sm font-bold text-gray-900 leading-tight truncate">{activeContact?.fullname}</h4>
                                            <p className={`text-[10px] font-semibold uppercase tracking-wider ${activeContact?.is_online ? 'text-green-600' : 'text-gray-400'}`}>
                                                {activeContact?.is_online ? 'Active Now' : 'Offline'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-1">
                                        <button 
                                            onClick={() => setIsOpen(false)} 
                                            className="p-1.5 hover:bg-gray-100 active:scale-95 rounded-xl text-gray-400 hover:text-gray-600 transition-colors"
                                            title="Close chat"
                                            aria-label="Close chat"
                                        >
                                            <X className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>

                                {/* Messages Area */}
                                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F8F9FA]">
                                    {loading ? (
                                        <div className="text-center text-gray-400 text-xs mt-4">Loading messages...</div>
                                    ) : messages.length === 0 ? (
                                        <div className="text-center text-gray-400 text-xs mt-4">No messages yet. Send a message to start the conversation!</div>
                                    ) : (
                                        messages.map((msg, idx) => {
                                            const isMe = msg.sender_id === currentUserId;
                                            const showAvatar = idx === 0 || messages[idx - 1].sender_id !== msg.sender_id;

                                            return (
                                                <div key={idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'} ${showAvatar ? 'mt-4' : 'mt-1'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                                                    <div className={`flex items-end gap-1.5 max-w-[90%] ${isMe ? 'flex-row-reverse' : 'flex-row'}`}>
                                                        {/* Avatar */}
                                                        <div className={`w-6 h-6 rounded-lg overflow-hidden shrink-0 shadow-sm border border-gray-100 flex items-center justify-center bg-gray-50 ${!showAvatar ? 'opacity-0' : 'opacity-100'}`}>
                                                            {isMe ? (
                                                                myProfileImage ? <img src={myProfileImage} className="w-full h-full object-cover" /> : <div className="text-[8px] font-bold text-[#D60041]">{localStorage.getItem('fullname')?.charAt(0) || 'M'}</div>
                                                            ) : (
                                                                activeContact.profile_image_url ? <img src={activeContact.profile_image_url} className="w-full h-full object-cover" /> : <div className="text-[8px] font-bold text-gray-400">{activeContact.fullname?.charAt(0)}</div>
                                                            )}
                                                        </div>

                                                        <div className="group flex flex-col">
                                                            <div className={`px-4 py-2 rounded-[18px] text-[13px] font-semibold shadow-sm transition-all hover:shadow-md ${isMe
                                                                    ? 'bg-[#D60041] text-white rounded-tr-none'
                                                                    : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                                                                }`}>
                                                                {msg.content}
                                                            </div>
                                                            {showAvatar && (
                                                                <p className={`text-[8px] mt-1 font-bold uppercase tracking-widest text-gray-400 ${isMe ? 'text-right' : 'text-left'}`}>
                                                                    {msg.is_optimistic ? 'Sending...' : new Date(msg.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                                                </p>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                    <div ref={messagesEndRef} />
                                </div>

                                {/* Input Area */}
                                {currentUserRole.toUpperCase() !== 'CANDIDATE' ? (
                                    <div className="p-4 bg-white border-t border-gray-100">
                                        <div className="relative flex items-center gap-2">
                                            <input
                                                type="text"
                                                value={inputMessage}
                                                onChange={(e) => setInputMessage(e.target.value)}
                                                onKeyDown={handleKeyDown}
                                                placeholder="Type a message..."
                                                className="w-full bg-gray-100 border-none rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-pink-100 transition-all outline-none font-medium placeholder:text-gray-400"
                                            />
                                            <button 
                                                onClick={sendMessage}
                                                disabled={!inputMessage.trim()}
                                                className="p-2.5 bg-[#D60041] hover:bg-[#b50037] text-white rounded-xl transition-all shadow-md shadow-pink-100 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                <Send className="h-4 w-4" />
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="p-4 bg-white border-t border-gray-100 flex items-center justify-center">
                                        <p className="text-xs font-bold text-gray-400">Read-only conversation. Only HR can message.</p>
                                    </div>
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* Toggle Button */}
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    aria-label="Open messaging"
                    className={`${isOpen ? 'scale-0 opacity-0 pointer-events-none' : 'scale-100 opacity-100'} 
                        ${isMobileScrolling ? 'translate-y-24 opacity-0 pointer-events-none' : 'translate-y-0'}
                        fixed bottom-5 right-5 sm:bottom-6 sm:right-6 transition-all duration-300 ease-out bg-gradient-to-tr from-[#B50037] via-[#D60041] to-[#FF2E63] text-white p-3.5 sm:p-4 rounded-2xl shadow-xl shadow-[#D60041]/25 flex items-center justify-center group z-[999] active:scale-95 hover:shadow-2xl hover:shadow-[#D60041]/35`}
                >
                    <MessageSquare className="h-6 w-6 group-hover:rotate-6 transition-transform" />
                    {contacts.some(c => c.unread_count > 0) && (
                        <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 border-2 border-white rounded-full animate-pulse"></span>
                    )}
                </button>
            </div>
        </>
    );
};

export default ChatWidget;
