import React, { useState, useEffect, useRef } from 'react';
import { Search, Send, ArrowLeft, MoreVertical, Paperclip, Smile, Phone, Video } from 'lucide-react';
import chatService from '../../services/chatService';
import { useSelector } from 'react-redux';

const ChatLayout = ({ isFullPage = true }) => {
    const { profileImageUrl: myProfileImage } = useSelector(state => state.auth);
    const [view, setView] = useState('contacts'); // 'contacts' | 'chat'
    const [contacts, setContacts] = useState([]);
    const [search, setSearch] = useState('');
    const [activeContact, setActiveContact] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const wsRef = useRef(null);
    const messagesEndRef = useRef(null);
    const activeContactRef = useRef(null);

    const token = localStorage.getItem('token');
    const currentUserId = parseInt(localStorage.getItem('user_id'), 10);

    // Sync ref with state
    useEffect(() => {
        activeContactRef.current = activeContact;
    }, [activeContact]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // WebSocket Connection
    useEffect(() => {
        if (!token) return;

        const connectWebSocket = () => {
            const ws = new WebSocket(`ws://localhost:8000/chat/ws?token=${encodeURIComponent(token)}`);
            
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
                setTimeout(connectWebSocket, 5000);
            };

            wsRef.current = ws;
        };

        connectWebSocket();

        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
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
        fetchContacts();
    }, [search]);

    const openChat = async (contact) => {
        setActiveContact(contact);
        setView('chat');
        setLoading(true);
        try {
            const res = await chatService.getMessages(contact.id, token);
            setMessages(res.data);
            
            // Mark as read locally
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
        
        setInputMessage('');

        const optimisticMessage = {
            sender_id: currentUserId,
            receiver_id: activeContact.id,
            content: content,
            timestamp: new Date().toISOString(),
            is_optimistic: true,
            client_id: clientId
        };

        setMessages(prev => [...prev, optimisticMessage]);

        const messageData = {
            type: 'send_message',
            receiver_id: activeContact.id,
            content: content,
            client_id: clientId
        };

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(messageData));
        } else {
            try {
                const res = await chatService.sendMessage(activeContact.id, content, token);
                
                setMessages(prev => prev.map(m => 
                    m.client_id === clientId ? { ...res.data, is_optimistic: false } : m
                ));
                fetchContacts();
            } catch (error) {
                console.error("Failed to send message via HTTP", error);
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

    return (
        <div className={`flex bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden font-['Inter'] ${isFullPage ? 'h-[calc(100vh-180px)]' : 'h-[600px]'}`}>
            {/* Sidebar: Contacts List */}
            <div className={`w-full md:w-[350px] lg:w-[400px] flex flex-col border-r border-gray-50 transition-all duration-300 ${view === 'chat' ? 'hidden md:flex' : 'flex'}`}>
                <div className="p-6 border-b border-gray-50 bg-white">
                    <h3 className="text-xl font-black text-gray-900 mb-6">Messages</h3>
                    <div className="relative">
                        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4" />
                        <input 
                            type="text" 
                            placeholder="Search contacts..." 
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-gray-50 border-none rounded-2xl py-3 pl-11 pr-4 text-sm focus:ring-2 focus:ring-pink-100 transition-all outline-none font-medium placeholder:text-gray-400"
                        />
                    </div>
                </div>

                <div className="flex-1 overflow-y-auto bg-white">
                    {contacts.length > 0 ? (
                        contacts.map(contact => (
                            <div 
                                key={contact.id} 
                                onClick={() => openChat(contact)}
                                className={`p-4 border-b border-gray-50 flex items-center gap-4 cursor-pointer transition-all relative ${activeContact?.id === contact.id ? 'bg-pink-50/50' : 'hover:bg-gray-50'}`}
                            >
                                <div className="relative shrink-0">
                                    {contact.profile_image_url ? (
                                        <img src={contact.profile_image_url} alt={contact.fullname} className="w-14 h-14 rounded-[20px] object-cover border border-gray-100 shadow-sm" />
                                    ) : (
                                        <div className="w-14 h-14 bg-gradient-to-br from-pink-50 to-red-50 rounded-[20px] flex items-center justify-center text-[#D60041] font-black text-xl shadow-inner">
                                            {contact.fullname.charAt(0).toUpperCase()}
                                        </div>
                                    )}
                                    <div className={`absolute -bottom-1 -right-1 w-4 h-4 border-2 border-white rounded-full ${contact.is_online ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.4)]' : 'bg-gray-300'}`}></div>
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-baseline mb-1">
                                        <h4 className="text-sm font-bold text-gray-900 truncate tracking-tight">{contact.fullname}</h4>
                                        {contact.last_message_time && (
                                            <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">
                                                {new Date(contact.last_message_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center justify-between gap-2">
                                        <p className={`text-xs truncate ${contact.unread_count > 0 ? 'text-gray-900 font-bold' : 'text-gray-500 font-medium'}`}>
                                            {contact.last_message || contact.role}
                                        </p>
                                        {contact.unread_count > 0 && (
                                            <div className="shrink-0 min-w-[18px] h-[18px] bg-[#D60041] rounded-full flex items-center justify-center text-[10px] text-white font-black px-1.5 shadow-md shadow-pink-100">
                                                {contact.unread_count}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                {activeContact?.id === contact.id && (
                                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#D60041] rounded-r-full"></div>
                                )}
                            </div>
                        ))
                    ) : (
                        <div className="p-12 text-center">
                            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Search className="text-gray-300" size={24} />
                            </div>
                            <p className="text-sm text-gray-400 font-bold">No contacts found</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className={`flex-1 flex flex-col bg-[#FDFDFD] transition-all duration-300 ${view === 'contacts' ? 'hidden md:flex' : 'flex'}`}>
                {activeContact ? (
                    <>
                        {/* Chat Header */}
                        <div className="p-6 border-b border-gray-100 bg-white flex justify-between items-center shadow-sm z-10">
                            <div className="flex items-center gap-4">
                                <button onClick={() => setView('contacts')} className="md:hidden p-2 hover:bg-gray-100 rounded-xl text-gray-500 transition-colors">
                                    <ArrowLeft className="h-5 w-5" />
                                </button>
                                <div className="relative">
                                    {activeContact.profile_image_url ? (
                                        <img src={activeContact.profile_image_url} alt={activeContact.fullname} className="w-12 h-12 rounded-2xl object-cover border border-gray-100 shadow-sm" />
                                    ) : (
                                        <div className="w-12 h-12 bg-pink-50 rounded-2xl flex items-center justify-center text-[#D60041] font-black text-lg">
                                            {activeContact.fullname?.charAt(0).toUpperCase()}
                                        </div>
                                    )}
                                    <div className={`absolute -bottom-1 -right-1 w-3.5 h-3.5 border-2 border-white rounded-full ${activeContact.is_online ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                                </div>
                                <div>
                                    <h4 className="text-base font-black text-gray-900 leading-tight tracking-tight">{activeContact.fullname}</h4>
                                    <div className="flex items-center gap-1.5">
                                        <div className={`w-1.5 h-1.5 rounded-full ${activeContact.is_online ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`}></div>
                                        <p className={`text-[10px] font-black uppercase tracking-widest ${activeContact.is_online ? 'text-green-600' : 'text-gray-400'}`}>
                                            {activeContact.is_online ? 'Active Now' : 'Offline'}
                                        </p>
                                    </div>
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <button className="p-2.5 hover:bg-gray-50 rounded-xl text-gray-400 transition-all hidden sm:block"><Phone size={20} /></button>
                                <button className="p-2.5 hover:bg-gray-50 rounded-xl text-gray-400 transition-all hidden sm:block"><Video size={20} /></button>
                                <button className="p-2.5 hover:bg-gray-50 rounded-xl text-gray-400 transition-all"><MoreVertical size={20} /></button>
                            </div>
                        </div>

                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-gray-50/50">
                            {loading ? (
                                <div className="flex flex-col items-center justify-center h-full">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D60041] mb-2"></div>
                                    <p className="text-xs text-gray-400 font-bold">Syncing messages...</p>
                                </div>
                            ) : messages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-center">
                                    <div className="w-16 h-16 bg-white rounded-[24px] flex items-center justify-center shadow-sm border border-gray-100 mb-4 text-[#D60041]">
                                        <Send size={24} />
                                    </div>
                                    <p className="text-sm text-gray-900 font-bold mb-1">Start a conversation</p>
                                    <p className="text-xs text-gray-400 font-medium max-w-[200px]">Send your first message to {activeContact.fullname}</p>
                                </div>
                            ) : (
                                messages.map((msg, idx) => {
                                    const isMe = msg.sender_id === currentUserId;
                                    const showAvatar = idx === 0 || messages[idx - 1].sender_id !== msg.sender_id;
                                    
                                    return (
                                        <div key={idx} className={`flex ${isMe ? 'justify-end' : 'justify-start'} ${showAvatar ? 'mt-6' : 'mt-1'} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                                            <div className={`flex items-end gap-2 max-w-[85%] lg:max-w-[70%] ${isMe ? 'flex-row-reverse' : 'flex-row'}`}>
                                                {/* Avatar */}
                                                <div className={`w-8 h-8 rounded-xl overflow-hidden shrink-0 shadow-sm border border-gray-100 flex items-center justify-center bg-gray-50 ${!showAvatar ? 'opacity-0' : 'opacity-100'}`}>
                                                    {isMe ? (
                                                        myProfileImage ? <img src={myProfileImage} className="w-full h-full object-cover" /> : <div className="text-[10px] font-bold text-[#D60041]">{localStorage.getItem('fullname')?.charAt(0) || 'M'}</div>
                                                    ) : (
                                                        activeContact.profile_image_url ? <img src={activeContact.profile_image_url} className="w-full h-full object-cover" /> : <div className="text-[10px] font-bold text-gray-400">{activeContact.fullname?.charAt(0)}</div>
                                                    )}
                                                </div>

                                                <div className="group flex flex-col">
                                                    <div className={`px-5 py-3 rounded-[22px] text-sm font-semibold shadow-sm transition-all hover:shadow-md ${isMe
                                                            ? 'bg-[#D60041] text-white rounded-tr-none'
                                                            : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none'
                                                        }`}>
                                                        {msg.content}
                                                    </div>
                                                    {showAvatar && (
                                                        <p className={`text-[9px] mt-1.5 font-bold uppercase tracking-widest text-gray-400 ${isMe ? 'text-right' : 'text-left'}`}>
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
                        <div className="p-6 bg-white border-t border-gray-50">
                            <div className="max-w-[1000px] mx-auto bg-gray-50 rounded-[24px] p-2 flex items-center gap-2 border border-gray-100 transition-all focus-within:bg-white focus-within:shadow-xl focus-within:shadow-pink-100/50 focus-within:border-pink-100">
                                <button className="p-3 text-gray-400 hover:text-[#D60041] transition-colors"><Smile size={20} /></button>
                                <button className="p-3 text-gray-400 hover:text-[#D60041] transition-colors"><Paperclip size={20} /></button>
                                <input
                                    type="text"
                                    value={inputMessage}
                                    onChange={(e) => setInputMessage(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Write your message..."
                                    className="flex-1 bg-transparent border-none py-3 px-1 text-sm focus:ring-0 outline-none font-bold text-gray-900 placeholder:text-gray-400"
                                />
                                <button 
                                    onClick={sendMessage}
                                    disabled={!inputMessage.trim()}
                                    className="p-4 bg-[#D60041] hover:bg-[#b50037] text-white rounded-2xl transition-all shadow-lg shadow-pink-100 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed group"
                                >
                                    <Send className="h-5 w-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
                                </button>
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
                        <div className="w-24 h-24 bg-white rounded-[40px] flex items-center justify-center shadow-xl shadow-red-50 border border-gray-50 mb-8 animate-bounce duration-[3000ms]">
                             <div className="w-12 h-12 bg-[#D60041] rounded-2xl flex items-center justify-center text-white">
                                <Search size={32} />
                             </div>
                        </div>
                        <h3 className="text-2xl font-black text-gray-900 mb-3 tracking-tight">Select a conversation</h3>
                        <p className="text-sm text-gray-400 font-bold max-w-xs leading-relaxed uppercase tracking-widest">
                            Choose someone from your contacts list to start messaging.
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ChatLayout;
