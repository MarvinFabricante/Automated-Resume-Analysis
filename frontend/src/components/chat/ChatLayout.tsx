import React, { useState, useEffect, useRef } from 'react';
import { 
    Search, Send, ArrowLeft, X, Lock, CheckCheck, Clock, 
    MessageSquare, Archive, ArchiveRestore, Trash2, AlertTriangle 
} from 'lucide-react';
import toast from 'react-hot-toast';
import chatService from '../../services/chatService';
import { useSelector } from 'react-redux';
import { WS_BASE_URL } from '../../services/api';
import { RootState } from '../../redux/store';
import { ChatContactItem, ChatMessageItem } from '../layout/ChatWidget';
import { decodeToken } from '../../utils/token';

interface ChatLayoutProps {
  isFullPage?: boolean;
}

const formatMessageTime = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return '';
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
        return '';
    }
};

const formatContactDate = (dateStr?: string) => {
    if (!dateStr) return '';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return '';
        const now = new Date();
        if (d.toDateString() === now.toDateString()) {
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        const yesterday = new Date(now);
        yesterday.setDate(now.getDate() - 1);
        if (d.toDateString() === yesterday.toDateString()) {
            return 'Yesterday';
        }
        return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
        return '';
    }
};

const getMessageDateGroup = (dateStr?: string) => {
    if (!dateStr) return 'Today';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return 'Today';
        const now = new Date();
        if (d.toDateString() === now.toDateString()) return 'Today';
        const yesterday = new Date(now);
        yesterday.setDate(now.getDate() - 1);
        if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
        return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
        return 'Today';
    }
};

const getRoleBadge = (role?: string) => {
    if (!role) return null;
    const r = role.toUpperCase();
    if (r === 'HR') {
        return (
            <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider bg-rose-50 text-[#D60041] border border-rose-200/80">
                HR
            </span>
        );
    }
    if (r === 'ADMIN') {
        return (
            <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200/80">
                Admin
            </span>
        );
    }
    if (r === 'CANDIDATE') {
        return (
            <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200/80">
                Candidate
            </span>
        );
    }
    return (
        <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider bg-gray-100 text-gray-700 border border-gray-200/80">
            {role}
        </span>
    );
};

const ChatLayout: React.FC<ChatLayoutProps> = ({ isFullPage = true }) => {
    const { profileImageUrl: myProfileImage } = useSelector((state: RootState) => state.auth);
    const [view, setView] = useState<'contacts' | 'chat'>('contacts');
    const [contacts, setContacts] = useState<ChatContactItem[]>([]);
    const [search, setSearch] = useState('');
    const [activeContact, setActiveContact] = useState<ChatContactItem | null>(null);
    const [messages, setMessages] = useState<ChatMessageItem[]>([]);
    const [inputMessage, setInputMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState<'all' | 'archived'>('all');
    const [archivedContactIds, setArchivedContactIds] = useState<number[]>([]);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const wsRef = useRef<WebSocket | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const activeContactRef = useRef<ChatContactItem | null>(null);

    const token = typeof localStorage !== 'undefined' ? localStorage.getItem('token') : null;
    const decodedToken = decodeToken(token);
    const currentUserId = typeof localStorage !== 'undefined' 
        ? (parseInt(localStorage.getItem('user_id') || '0', 10) || decodedToken?.id || 0) 
        : (decodedToken?.id || 0);
    const currentUserRole = typeof localStorage !== 'undefined' ? (localStorage.getItem('role') || 'Guest') : 'Guest';

    // Load archived contact IDs from localStorage and backend
    useEffect(() => {
        if (currentUserId) {
            try {
                const saved = localStorage.getItem(`archived_contacts_${currentUserId}`);
                if (saved) {
                    setArchivedContactIds(JSON.parse(saved));
                }
            } catch (e) {
                console.error("Failed to load archived contacts from localStorage", e);
            }
        }

        if (token) {
            chatService.getArchivedConversations(token)
                .then(res => {
                    if (res?.data?.archived_contact_ids && Array.isArray(res.data.archived_contact_ids)) {
                        setArchivedContactIds(prev => {
                            const merged = Array.from(new Set([...prev, ...res.data.archived_contact_ids]));
                            if (currentUserId) {
                                try {
                                    localStorage.setItem(`archived_contacts_${currentUserId}`, JSON.stringify(merged));
                                } catch (err) {
                                    console.error("Failed to save to localStorage", err);
                                }
                            }
                            return merged;
                        });
                    }
                })
                .catch(err => {
                    console.error("Failed to load archived conversations from backend", err);
                });
        }
    }, [currentUserId, token]);

    const toggleArchiveContact = async (contactId: number, e?: React.MouseEvent) => {
        if (e) e.stopPropagation();
        const isArchived = archivedContactIds.includes(contactId);
        const next = isArchived ? archivedContactIds.filter(id => id !== contactId) : [...archivedContactIds, contactId];

        // Optimistic UI updates
        setArchivedContactIds(next);
        setContacts(prev => prev.map(c => c.id === contactId ? { ...c, is_archived: !isArchived } : c));
        if (currentUserId) {
            try {
                localStorage.setItem(`archived_contacts_${currentUserId}`, JSON.stringify(next));
            } catch (err) {
                console.error("Failed to save archived contacts", err);
            }
        }
        toast.success(isArchived ? "Conversation moved to active inbox" : "Conversation archived");

        // Persist to backend database
        try {
            if (isArchived) {
                await chatService.unarchiveConversation(contactId, token);
            } else {
                await chatService.archiveConversation(contactId, token);
            }
        } catch (err) {
            console.error("Failed to sync archive status with backend", err);
            toast.error("Could not sync archive status with server");
            // Revert state if backend call failed
            setArchivedContactIds(prev => isArchived ? [...prev, contactId] : prev.filter(id => id !== contactId));
            setContacts(prev => prev.map(c => c.id === contactId ? { ...c, is_archived: isArchived } : c));
            if (currentUserId) {
                try {
                    localStorage.setItem(`archived_contacts_${currentUserId}`, JSON.stringify(archivedContactIds));
                } catch (e) {
                    console.error("Failed to revert localStorage", e);
                }
            }
        }
    };

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
            const ws = new WebSocket(`${WS_BASE_URL}/chat/ws?token=${encodeURIComponent(token)}`);
            
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
                        setActiveContact(prev => prev ? ({ ...prev, is_online: data.is_online }) : null);
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
            const userList: ChatContactItem[] = res.data.users || [];
            setContacts(userList);

            // Synchronize archived contact IDs from backend contacts
            const backendArchivedIds = userList.filter(c => c.is_archived).map(c => c.id);
            setArchivedContactIds(prev => {
                const activeIds = userList.filter(c => c.is_archived === false).map(c => c.id);
                const nextList = Array.from(new Set([
                    ...prev.filter(id => !activeIds.includes(id)),
                    ...backendArchivedIds
                ]));
                if (currentUserId) {
                    try {
                        localStorage.setItem(`archived_contacts_${currentUserId}`, JSON.stringify(nextList));
                    } catch (e) {
                        console.error("Failed to sync archived contacts to localStorage", e);
                    }
                }
                return nextList;
            });
        } catch (error) {
            console.error("Failed to fetch contacts", error);
        }
    };

    useEffect(() => {
        fetchContacts();
    }, [search]);

    const openChat = async (contact: ChatContactItem) => {
        setActiveContact(contact);
        setView('chat');
        setLoading(true);
        try {
            const res = await chatService.getMessages(contact.id, token);
            setMessages(res.data || []);
            
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
        
        const content = inputMessage.trim();
        const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        
        setInputMessage('');

        const optimisticMessage: ChatMessageItem = {
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

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    const handleDeleteConversation = async () => {
        if (!activeContact) return;
        setIsDeleting(true);
        try {
            await chatService.deleteConversation(activeContact.id, token);
            setMessages([]);
            setContacts(prev => prev.map(c => 
                c.id === activeContact.id ? { ...c, last_message: undefined, last_message_time: undefined, unread_count: 0 } : c
            ));
            toast.success("Conversation deleted");
            setShowDeleteModal(false);
        } catch (error) {
            console.error("Failed to delete conversation", error);
            toast.error("Failed to delete conversation");
        } finally {
            setIsDeleting(false);
        }
    };

    const handleDeleteSingleMessage = async (messageId?: string | number) => {
        if (!messageId) return;
        try {
            await chatService.deleteMessage(messageId, token);
            setMessages(prev => prev.filter(m => m.id !== messageId));
            toast.success("Message deleted");
        } catch (error) {
            console.error("Failed to delete message", error);
            toast.error("Could not delete message");
        }
    };

    const filteredContacts = contacts.filter(contact => {
        const isArchived = archivedContactIds.includes(contact.id);
        return activeTab === 'archived' ? isArchived : !isArchived;
    });

    const activeCount = contacts.filter(c => !archivedContactIds.includes(c.id)).length;
    const archivedCount = contacts.filter(c => archivedContactIds.includes(c.id)).length;
    const totalUnread = contacts.reduce((sum, c) => sum + (c.unread_count || 0), 0);

    return (
        <div className={`flex bg-white rounded-2xl sm:rounded-3xl md:rounded-[32px] border border-gray-100 shadow-xs overflow-hidden font-['Inter'] w-full relative ${isFullPage ? 'h-[calc(100dvh-175px)] sm:h-[calc(100dvh-200px)] md:h-[calc(100vh-210px)] min-h-[460px] max-h-full' : 'h-[600px]'}`}>
            {/* Sidebar: Contacts List */}
            <div className={`w-full md:w-[340px] lg:w-[380px] flex flex-col border-r border-gray-100 shrink-0 bg-white transition-all duration-300 ${view === 'chat' ? 'hidden md:flex' : 'flex'}`}>
                {/* Contacts Header */}
                <div className="p-3.5 sm:p-5 border-b border-gray-100 bg-white">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <h3 className="text-lg sm:text-xl font-black text-gray-900 tracking-tight">Messages</h3>
                            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                                {contacts.length}
                            </span>
                        </div>
                        {totalUnread > 0 && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-[#D60041] border border-rose-100">
                                {totalUnread} unread
                            </span>
                        )}
                    </div>

                    {/* Search Bar */}
                    <div className="relative">
                        <label htmlFor="contact-search-input" className="sr-only">Search contacts</label>
                        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 h-4 w-4 pointer-events-none" />
                        <input 
                            id="contact-search-input"
                            type="text" 
                            placeholder="Search contacts..." 
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full bg-gray-50 border border-gray-100 rounded-xl sm:rounded-2xl py-2 pl-10 pr-9 text-xs sm:text-sm focus:bg-white focus:border-[#D60041] focus:ring-2 focus:ring-pink-100 transition-all outline-none font-medium placeholder:text-gray-400 text-gray-800"
                        />
                        {search && (
                            <button 
                                onClick={() => setSearch('')}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 p-0.5 rounded-full cursor-pointer"
                                aria-label="Clear search"
                            >
                                <X size={14} />
                            </button>
                        )}
                    </div>

                    {/* Filter Tabs: All vs Archived */}
                    <div className="flex items-center gap-1 p-1 bg-gray-100/80 rounded-xl mt-3">
                        <button
                            onClick={() => setActiveTab('all')}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                                activeTab === 'all'
                                    ? 'bg-white text-gray-900 shadow-2xs'
                                    : 'text-gray-500 hover:text-gray-800'
                            }`}
                        >
                            <span>Inbox</span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-gray-200/60 text-gray-600">
                                {activeCount}
                            </span>
                        </button>
                        <button
                            onClick={() => setActiveTab('archived')}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                                activeTab === 'archived'
                                    ? 'bg-white text-gray-900 shadow-2xs'
                                    : 'text-gray-500 hover:text-gray-800'
                            }`}
                        >
                            <Archive size={12} className={activeTab === 'archived' ? 'text-amber-600' : 'text-gray-400'} />
                            <span>Archived</span>
                            {archivedCount > 0 && (
                                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-100 text-amber-800 font-bold">
                                    {archivedCount}
                                </span>
                            )}
                        </button>
                    </div>
                </div>

                {/* Contacts Scrollable List */}
                <div className="flex-1 overflow-y-auto divide-y divide-gray-50 bg-white">
                    {filteredContacts.length > 0 ? (
                        filteredContacts.map(contact => {
                            const isArchived = archivedContactIds.includes(contact.id);
                            return (
                                <div 
                                    key={contact.id} 
                                    onClick={() => openChat(contact)}
                                    className={`p-3.5 sm:p-4 flex items-center gap-3 sm:gap-3.5 cursor-pointer transition-all relative group ${
                                        activeContact?.id === contact.id ? 'bg-pink-50/50' : 'hover:bg-gray-50/80 active:bg-gray-100/60'
                                    }`}
                                >
                                    <div className="relative shrink-0">
                                        {contact.profile_image_url ? (
                                            <img 
                                                src={contact.profile_image_url} 
                                                alt={contact.fullname} 
                                                className="w-11 h-11 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl object-cover border border-gray-100 shadow-2xs" 
                                            />
                                        ) : (
                                            <div className="w-11 h-11 sm:w-12 sm:h-12 bg-gradient-to-br from-pink-50 to-red-50 rounded-xl sm:rounded-2xl flex items-center justify-center text-[#D60041] font-black text-base sm:text-lg shadow-inner">
                                                {contact.fullname ? contact.fullname.charAt(0).toUpperCase() : 'U'}
                                            </div>
                                        )}
                                        <div 
                                            className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 sm:w-3.5 sm:h-3.5 border-2 border-white rounded-full ${
                                                contact.is_online ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-gray-300'
                                            }`}
                                            title={contact.is_online ? 'Online' : 'Offline'}
                                        />
                                    </div>

                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center justify-between gap-1.5 mb-1">
                                            <div className="flex items-center gap-1.5 min-w-0">
                                                <h4 className="text-xs sm:text-sm font-bold text-gray-900 truncate tracking-tight">
                                                    {contact.fullname}
                                                </h4>
                                                {getRoleBadge(contact.role)}
                                            </div>
                                            {contact.last_message_time && (
                                                <span className="text-[10px] sm:text-[11px] text-gray-400 font-semibold shrink-0 ml-1">
                                                    {formatContactDate(contact.last_message_time)}
                                                </span>
                                            )}
                                        </div>

                                        <div className="flex items-center justify-between gap-2">
                                            <p className={`text-xs truncate ${
                                                (contact.unread_count || 0) > 0 ? 'text-gray-900 font-bold' : 'text-gray-500 font-normal'
                                            }`}>
                                                {contact.last_message || (
                                                    <span className="italic text-gray-400">Tap to start chatting</span>
                                                )}
                                            </p>
                                            
                                            <div className="flex items-center gap-1.5 shrink-0">
                                                {/* Quick Archive / Unarchive Button */}
                                                <button
                                                    onClick={(e) => toggleArchiveContact(contact.id, e)}
                                                    className="opacity-0 group-hover:opacity-100 sm:opacity-0 focus:opacity-100 p-1 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-200/60 transition-all cursor-pointer"
                                                    title={isArchived ? "Unarchive" : "Archive"}
                                                    aria-label={isArchived ? "Unarchive" : "Archive"}
                                                >
                                                    {isArchived ? <ArchiveRestore size={13} /> : <Archive size={13} />}
                                                </button>

                                                {Boolean(contact.unread_count && contact.unread_count > 0) && (
                                                    <span className="min-w-[18px] h-[18px] bg-[#D60041] rounded-full flex items-center justify-center text-[10px] text-white font-black px-1.5 shadow-sm shadow-pink-200">
                                                        {contact.unread_count}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    {activeContact?.id === contact.id && (
                                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-[#D60041] rounded-r-full hidden md:block"></div>
                                    )}
                                </div>
                            );
                        })
                    ) : (
                        <div className="p-8 sm:p-12 text-center">
                            <div className="w-12 h-12 sm:w-14 sm:h-14 bg-gray-50 rounded-2xl flex items-center justify-center mx-auto mb-3 text-gray-300">
                                {activeTab === 'archived' ? <Archive size={22} /> : <Search size={22} />}
                            </div>
                            <p className="text-xs sm:text-sm text-gray-500 font-bold mb-1">
                                {activeTab === 'archived' ? 'No archived conversations' : 'No contacts found'}
                            </p>
                            <p className="text-[11px] text-gray-400 font-medium">
                                {activeTab === 'archived' ? 'Conversations you archive will appear here' : 'Try searching by name or role'}
                            </p>
                        </div>
                    )}
                </div>
            </div>

            {/* Main Chat Area */}
            <div className={`flex-1 flex flex-col bg-[#FDFDFD] transition-all duration-300 min-w-0 ${view === 'contacts' ? 'hidden md:flex' : 'flex'}`}>
                {activeContact ? (
                    <>
                        {/* Chat Header */}
                        <div className="p-3.5 sm:p-4 md:p-5 border-b border-gray-100 bg-white flex justify-between items-center shadow-2xs z-10">
                            <div className="flex items-center gap-2.5 sm:gap-3.5 min-w-0">
                                {/* Back to contacts list on mobile */}
                                <button 
                                    onClick={() => setView('contacts')} 
                                    className="md:hidden p-2 -ml-1 hover:bg-gray-100 active:scale-95 rounded-xl text-gray-600 transition-all cursor-pointer shrink-0"
                                    title="Back to contacts"
                                    aria-label="Back to contacts list"
                                >
                                    <ArrowLeft className="h-5 w-5" />
                                </button>

                                <div className="relative shrink-0">
                                    {activeContact.profile_image_url ? (
                                        <img 
                                            src={activeContact.profile_image_url} 
                                            alt={activeContact.fullname} 
                                            className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl sm:rounded-2xl object-cover border border-gray-100 shadow-2xs" 
                                        />
                                    ) : (
                                        <div className="w-10 h-10 sm:w-12 sm:h-12 bg-pink-50 rounded-xl sm:rounded-2xl flex items-center justify-center text-[#D60041] font-black text-base sm:text-lg border border-pink-100/50">
                                            {activeContact.fullname?.charAt(0).toUpperCase()}
                                        </div>
                                    )}
                                    <div 
                                        className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 sm:w-3.5 sm:h-3.5 border-2 border-white rounded-full ${
                                            activeContact.is_online ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.4)]' : 'bg-gray-300'
                                        }`}
                                        title={activeContact.is_online ? 'Online' : 'Offline'}
                                    />
                                </div>

                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        <h4 className="text-sm sm:text-base font-black text-gray-900 leading-tight tracking-tight truncate">
                                            {activeContact.fullname}
                                        </h4>
                                        {getRoleBadge(activeContact.role)}
                                        {archivedContactIds.includes(activeContact.id) && (
                                            <span className="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider bg-amber-50 text-amber-700 border border-amber-200">
                                                Archived
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-1.5 mt-0.5 sm:mt-1">
                                        <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${activeContact.is_online ? 'bg-emerald-500 animate-pulse' : 'bg-gray-300'}`}></div>
                                        <p className={`text-[11px] sm:text-xs font-semibold ${activeContact.is_online ? 'text-emerald-600' : 'text-gray-400'}`}>
                                            {activeContact.is_online ? 'Active Now' : 'Offline'}
                                        </p>
                                    </div>
                                </div>
                            </div>

                            {/* Header Actions: Archive & Delete (replaces call, video, 3-dots) */}
                            <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
                                {/* Archive / Unarchive Button */}
                                <button 
                                    onClick={(e) => toggleArchiveContact(activeContact.id, e)}
                                    className={`p-2 sm:p-2.5 rounded-xl transition-all cursor-pointer flex items-center gap-1.5 text-xs font-semibold ${
                                        archivedContactIds.includes(activeContact.id)
                                            ? 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200/80 shadow-2xs'
                                            : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                                    }`}
                                    title={archivedContactIds.includes(activeContact.id) ? "Unarchive conversation" : "Archive conversation"}
                                    aria-label={archivedContactIds.includes(activeContact.id) ? "Unarchive conversation" : "Archive conversation"}
                                >
                                    {archivedContactIds.includes(activeContact.id) ? (
                                        <>
                                            <ArchiveRestore size={17} className="shrink-0" />
                                            <span className="hidden sm:inline">Unarchive</span>
                                        </>
                                    ) : (
                                        <>
                                            <Archive size={17} className="shrink-0" />
                                            <span className="hidden sm:inline">Archive</span>
                                        </>
                                    )}
                                </button>

                                {/* Delete Conversation Button */}
                                <button 
                                    onClick={() => setShowDeleteModal(true)}
                                    className="p-2 sm:p-2.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-xl transition-all cursor-pointer flex items-center gap-1.5 text-xs font-semibold"
                                    title="Delete conversation"
                                    aria-label="Delete conversation"
                                >
                                    <Trash2 size={17} className="shrink-0" />
                                    <span className="hidden sm:inline">Delete</span>
                                </button>
                            </div>
                        </div>

                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto p-3.5 sm:p-5 md:p-6 space-y-3 sm:space-y-4 bg-gray-50/50">
                            {loading ? (
                                <div className="flex flex-col items-center justify-center h-full text-center">
                                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#D60041] mb-2"></div>
                                    <p className="text-xs text-gray-500 font-semibold">Syncing messages...</p>
                                </div>
                            ) : messages.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-center p-6">
                                    <div className="w-14 h-14 sm:w-16 sm:h-16 bg-white rounded-2xl sm:rounded-3xl flex items-center justify-center shadow-xs border border-gray-100 mb-3 text-[#D60041]">
                                        <MessageSquare size={24} />
                                    </div>
                                    <p className="text-sm sm:text-base text-gray-900 font-bold mb-1">Start a conversation</p>
                                    <p className="text-xs text-gray-500 font-medium max-w-[220px]">
                                        Send your first message to {activeContact.fullname}
                                    </p>
                                </div>
                            ) : (
                                messages.map((msg, idx) => {
                                    const isMe = msg.sender_id === currentUserId;
                                    const prevMsg = idx > 0 ? messages[idx - 1] : null;
                                    const isFirstInCluster = !prevMsg || prevMsg.sender_id !== msg.sender_id;
                                    const currentDateGroup = getMessageDateGroup(msg.timestamp);
                                    const prevDateGroup = prevMsg ? getMessageDateGroup(prevMsg.timestamp) : null;
                                    const showDateDivider = !prevMsg || currentDateGroup !== prevDateGroup;

                                    return (
                                        <React.Fragment key={msg.id || msg.client_id || idx}>
                                            {showDateDivider && (
                                                <div className="flex items-center justify-center my-3 sm:my-4">
                                                    <span className="px-3 py-1 bg-white border border-gray-200/80 rounded-full text-[11px] font-semibold text-gray-500 shadow-2xs tracking-wide">
                                                        {currentDateGroup}
                                                    </span>
                                                </div>
                                            )}

                                            <div className={`flex ${isMe ? 'justify-end' : 'justify-start'} ${isFirstInCluster ? 'mt-4' : 'mt-1'} animate-in fade-in duration-200 group`}>
                                                <div className={`flex items-end gap-2 max-w-[88%] sm:max-w-[75%] md:max-w-[70%] ${isMe ? 'flex-row-reverse' : 'flex-row'}`}>
                                                    {/* Avatar for other user */}
                                                    {!isMe && (
                                                        <div className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl overflow-hidden shrink-0 shadow-2xs border border-gray-100 flex items-center justify-center bg-gray-50 ${!isFirstInCluster ? 'invisible' : ''}`}>
                                                            {activeContact.profile_image_url ? (
                                                                <img src={activeContact.profile_image_url} alt={activeContact.fullname} className="w-full h-full object-cover" />
                                                            ) : (
                                                                <div className="text-[11px] font-black text-[#D60041]">
                                                                    {activeContact.fullname?.charAt(0) || 'U'}
                                                                </div>
                                                            )}
                                                        </div>
                                                    )}

                                                    <div className="flex flex-col min-w-0">
                                                        {/* Sender Label for received messages */}
                                                        {!isMe && isFirstInCluster && (
                                                            <div className="flex items-center gap-1.5 mb-1 px-1">
                                                                <span className="text-[11px] font-bold text-gray-700 truncate">
                                                                    {activeContact.fullname}
                                                                </span>
                                                                {activeContact.role && (
                                                                    <span className="text-[9px] font-bold uppercase tracking-wider text-gray-400">
                                                                        • {activeContact.role}
                                                                    </span>
                                                                )}
                                                            </div>
                                                        )}

                                                        {/* Bubble */}
                                                        <div className={`px-4 py-2.5 sm:px-5 sm:py-3 rounded-[20px] text-xs sm:text-sm font-medium shadow-2xs leading-relaxed break-words relative ${
                                                            isMe 
                                                                ? 'bg-[#D60041] text-white rounded-br-sm' 
                                                                : 'bg-white text-gray-800 border border-gray-100/90 rounded-bl-sm'
                                                        }`}>
                                                            {msg.content}
                                                        </div>

                                                        {/* Timestamp, Status & Delete Message Option */}
                                                        <div className={`flex items-center gap-1.5 mt-1 px-1 ${isMe ? 'justify-end' : 'justify-start'}`}>
                                                            <span className="text-[10px] sm:text-[11px] font-medium text-gray-400 tracking-tight">
                                                                {formatMessageTime(msg.timestamp)}
                                                            </span>
                                                            {isMe && (
                                                                msg.is_optimistic ? (
                                                                    <span className="text-[10px] font-semibold text-pink-600 flex items-center gap-0.5">
                                                                        <Clock size={10} className="animate-spin" />
                                                                        <span>Sending</span>
                                                                    </span>
                                                                ) : (
                                                                    <span title="Delivered" aria-label="Delivered">
                                                                        <CheckCheck size={12} className="text-[#D60041]" />
                                                                    </span>
                                                                )
                                                            )}
                                                            {/* Option to delete individual message */}
                                                            {msg.id && !msg.is_optimistic && (isMe || currentUserRole.toUpperCase() === 'ADMIN') && (
                                                                <button
                                                                    onClick={() => handleDeleteSingleMessage(msg.id)}
                                                                    className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 p-0.5 transition-opacity cursor-pointer ml-0.5"
                                                                    title="Delete message"
                                                                    aria-label="Delete message"
                                                                >
                                                                    <Trash2 size={11} />
                                                                </button>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </React.Fragment>
                                    );
                                })
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Input Area (Clean & focused: dummy emoji and paperclip removed) */}
                        {currentUserRole.toUpperCase() !== 'CANDIDATE' ? (
                            <div className="p-2.5 sm:p-4 md:p-5 bg-white border-t border-gray-100">
                                <div className="max-w-4xl mx-auto bg-gray-50 rounded-2xl sm:rounded-3xl p-1.5 sm:p-2 flex items-center gap-2 border border-gray-200/80 focus-within:bg-white focus-within:border-[#D60041] focus-within:ring-2 focus-within:ring-pink-100/50 transition-all">
                                    <input
                                        type="text"
                                        value={inputMessage}
                                        onChange={(e) => setInputMessage(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        placeholder="Write your message..."
                                        aria-label="Write your message"
                                        className="flex-1 bg-transparent border-none py-2 sm:py-2.5 px-3 text-xs sm:text-sm focus:ring-0 outline-none font-medium text-gray-900 placeholder:text-gray-400 min-w-0"
                                    />
                                    <button 
                                        onClick={sendMessage}
                                        disabled={!inputMessage.trim()}
                                        aria-label="Send message"
                                        title="Send message"
                                        className="p-2.5 sm:p-3 bg-[#D60041] hover:bg-[#b50037] text-white rounded-xl sm:rounded-2xl transition-all shadow-md shadow-pink-200 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shrink-0"
                                    >
                                        <Send size={16} className="sm:w-[18px] sm:h-[18px]" />
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <div className="p-3 sm:p-4 md:p-5 bg-gray-50/80 border-t border-gray-100 flex items-center justify-center">
                                <div className="inline-flex items-center gap-2 px-3.5 py-2 sm:px-4 sm:py-2.5 rounded-2xl bg-white border border-gray-200/80 shadow-2xs text-gray-600 max-w-md text-center">
                                    <Lock size={14} className="text-[#D60041] shrink-0" />
                                    <span className="text-xs sm:text-sm font-semibold text-gray-600">
                                        This conversation is read-only. Only HR team members can post messages.
                                    </span>
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center p-8 sm:p-12 text-center">
                        <div className="w-16 h-16 sm:w-20 sm:h-20 bg-pink-50 rounded-3xl flex items-center justify-center shadow-xs border border-pink-100/60 mb-5 text-[#D60041]">
                            <MessageSquare size={32} />
                        </div>
                        <h3 className="text-xl sm:text-2xl font-black text-gray-900 mb-2 tracking-tight">Select a conversation</h3>
                        <p className="text-xs sm:text-sm text-gray-400 font-medium max-w-xs leading-relaxed">
                            Choose someone from your contacts list to view the conversation or start messaging.
                        </p>
                    </div>
                )}
            </div>

            {/* Conversation Deletion Confirmation Modal */}
            {showDeleteModal && activeContact && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-200">
                    <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-gray-100 flex flex-col items-center text-center animate-in zoom-in-95 duration-200">
                        <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center text-red-600 mb-4 border border-red-100">
                            <AlertTriangle size={28} />
                        </div>
                        <h3 className="text-lg font-black text-gray-900 mb-1">Delete Conversation?</h3>
                        <p className="text-xs sm:text-sm text-gray-500 leading-relaxed mb-6">
                            This will permanently remove all messages with <span className="font-bold text-gray-800">{activeContact.fullname}</span>. This action cannot be undone.
                        </p>
                        <div className="flex items-center gap-3 w-full">
                            <button
                                onClick={() => setShowDeleteModal(false)}
                                disabled={isDeleting}
                                className="flex-1 py-2.5 px-4 rounded-xl border border-gray-200 text-xs sm:text-sm font-bold text-gray-700 hover:bg-gray-50 active:scale-95 transition-all cursor-pointer"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleDeleteConversation}
                                disabled={isDeleting}
                                className="flex-1 py-2.5 px-4 rounded-xl bg-red-600 hover:bg-red-700 text-white text-xs sm:text-sm font-bold shadow-md shadow-red-200 active:scale-95 transition-all cursor-pointer flex items-center justify-center gap-1.5 disabled:opacity-50"
                            >
                                <Trash2 size={15} />
                                <span>{isDeleting ? 'Deleting...' : 'Delete'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChatLayout;


