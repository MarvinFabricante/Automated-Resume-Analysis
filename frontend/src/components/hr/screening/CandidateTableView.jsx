import React, { useState, useRef, useEffect } from 'react';
import { 
  Calendar, MapPin, ChevronDown, CheckCircle2, XCircle, Clock, Search, 
  Check, Archive, Trash2, RotateCcw, FileText, Download, Copy, Mail, Phone, Eye, Sparkles
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

const TableStatusDropdown = ({ status, candidateId, onUpdateStatus }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handleOutside = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  const getStatusInfo = (st) => {
    switch ((st || '').toLowerCase()) {
      case 'accepted': return { color: 'text-teal-700 bg-teal-50 border-teal-200', label: 'Accepted' };
      case 'rejected': return { color: 'text-rose-700 bg-rose-50 border-rose-200', label: 'Rejected' };
      case 'reviewed': return { color: 'text-blue-700 bg-blue-50 border-blue-200', label: 'Reviewed' };
      case 'technical interview': return { color: 'text-purple-700 bg-purple-50 border-purple-200', label: 'Tech Interview' };
      case 'final interview': return { color: 'text-indigo-700 bg-indigo-50 border-indigo-200', label: 'Final Interview' };
      case 'archived': return { color: 'text-gray-700 bg-gray-100 border-gray-200', label: 'Archived' };
      default: return { color: 'text-amber-700 bg-amber-50 border-amber-200', label: 'Pending' };
    }
  };

  const currentInfo = getStatusInfo(status);

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        disabled={isUpdating}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-bold uppercase tracking-wider transition-all cursor-pointer ${currentInfo.color} ${isUpdating ? 'opacity-50 animate-pulse' : 'hover:shadow-xs'}`}
      >
        <span className="truncate max-w-[100px]">{currentInfo.label}</span>
        <ChevronDown size={11} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-44 bg-white border border-gray-100 rounded-xl shadow-xl z-50 py-1 animate-in fade-in zoom-in-95 duration-150">
          {['Pending', 'Reviewed', 'Technical Interview', 'Final Interview', 'Accepted', 'Rejected'].map((s) => (
            <button
              key={s}
              type="button"
              onClick={async (e) => {
                e.stopPropagation();
                setIsOpen(false);
                setIsUpdating(true);
                await onUpdateStatus(candidateId, s);
                setTimeout(() => setIsUpdating(false), 500);
              }}
              className={`w-full flex items-center justify-between px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider transition-colors cursor-pointer ${
                (status || '').toLowerCase() === s.toLowerCase() 
                  ? 'bg-pink-50 text-[#D60041]' 
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span>{s}</span>
              {(status || '').toLowerCase() === s.toLowerCase() && <Check size={11} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const CandidateTableView = ({
  candidates,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onOpenDetails,
  onOpenInterview,
  onUpdateStatus,
  onArchiveApplication,
  onRestoreApplication,
  onDeleteApplication,
  onSkillClick
}) => {
  const [copiedId, setCopiedId] = useState(null);

  const handleCopy = (text, id) => {
    if (!text || text === 'N/A') return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const allSelected = candidates.length > 0 && candidates.every(c => selectedIds.includes(c.id));

  return (
    <div className="bg-white rounded-2xl sm:rounded-3xl border border-gray-200/80 shadow-sm overflow-hidden">
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full text-left border-collapse min-w-[760px]">
          <thead>
            <tr className="bg-gray-50/80 border-b border-gray-200/80 text-[10px] font-black uppercase tracking-wider text-gray-500">
              <th className="py-3.5 px-3.5 w-10 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onSelectAll}
                  className="w-4 h-4 rounded border-gray-300 text-[#D60041] focus:ring-[#D60041] cursor-pointer"
                  title="Select all"
                />
              </th>
              <th className="py-3.5 px-3">Candidate</th>
              <th className="py-3.5 px-3">Applied Role</th>
              <th className="py-3.5 px-3 text-center">AI Match</th>
              <th className="py-3.5 px-3">Skills</th>
              <th className="py-3.5 px-3">Applied Date</th>
              <th className="py-3.5 px-3">Status</th>
              <th className="py-3.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {candidates.map((c) => {
              const isSelected = selectedIds.includes(c.id);
              const isArchived = (c.status || '').toLowerCase() === 'archived';
              const match = Math.round(c.matchScore || 0);

              const avatarUrl = c.profileImage
                ? getAssetUrl(c.profileImage)
                : `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name || 'Candidate')}&background=fdf2f8&color=d81159&bold=true`;

              const matchColor = match >= 80 
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200 ring-1 ring-emerald-500/20' 
                : match >= 60 
                  ? 'text-amber-700 bg-amber-50 border-amber-200 ring-1 ring-amber-500/20' 
                  : 'text-rose-700 bg-rose-50 border-rose-200 ring-1 ring-rose-500/20';

              return (
                <tr 
                  key={c.id} 
                  className={`hover:bg-pink-50/25 transition-colors ${isSelected ? 'bg-pink-50/35' : ''}`}
                >
                  <td className="py-3 px-3.5 text-center">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(c.id)}
                      className="w-4 h-4 rounded border-gray-300 text-[#D60041] focus:ring-[#D60041] cursor-pointer"
                    />
                  </td>

                  <td className="py-3 px-3">
                    <div className="flex items-center gap-2.5">
                      <div className="w-9 h-9 rounded-xl overflow-hidden border border-gray-100 shrink-0 bg-pink-50">
                        <img 
                          src={avatarUrl} 
                          alt={c.name} 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name || 'Candidate')}&background=fdf2f8&color=d81159&bold=true`;
                          }}
                        />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => onOpenDetails(c)}
                            className="font-bold text-xs sm:text-sm text-gray-900 hover:text-[#D60041] transition-colors truncate text-left cursor-pointer"
                          >
                            {c.name}
                          </button>
                        </div>
                        <div className="flex items-center gap-1.5 text-[11px] text-gray-400 font-medium">
                          <span className="truncate max-w-[130px]">{c.email || 'N/A'}</span>
                          {c.email && c.email !== 'N/A' && (
                            <button
                              type="button"
                              onClick={() => handleCopy(c.email, `email-${c.id}`)}
                              title="Copy Email"
                              className="hover:text-gray-700 transition-colors cursor-pointer"
                            >
                              {copiedId === `email-${c.id}` ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-gray-800 truncate">{c.preferredJob}</p>
                      <p className="text-[10px] text-gray-400 font-medium flex items-center gap-1 mt-0.5">
                        <MapPin size={10} />
                        <span className="truncate">{c.location || "N/A"}</span>
                      </p>
                    </div>
                  </td>

                  <td className="py-3 px-3 text-center">
                    <span className={`inline-flex px-2 py-0.5 rounded-lg border text-xs font-black ${matchColor}`}>
                      {match}%
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <div className="flex flex-wrap gap-1 max-w-[180px]">
                      {(c.skills || []).slice(0, 3).map((skill, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => onSkillClick && onSkillClick(skill)}
                          title={`Filter by ${skill}`}
                          className="px-1.5 py-0.5 bg-gray-50 border border-gray-200/80 hover:border-pink-200 hover:text-[#D60041] text-gray-600 text-[10px] font-semibold rounded-md transition-colors truncate max-w-[85px] cursor-pointer"
                        >
                          {skill}
                        </button>
                      ))}
                      {(c.skills || []).length > 3 && (
                        <span className="px-1 py-0.5 bg-gray-50 text-gray-400 text-[10px] font-bold rounded-md border border-gray-100">
                          +{c.skills.length - 3}
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="py-3 px-3">
                    <span className="text-xs font-medium text-gray-500 whitespace-nowrap">
                      {formatDate(c.date)}
                    </span>
                  </td>

                  <td className="py-3 px-3">
                    <TableStatusDropdown 
                      status={c.status} 
                      candidateId={c.id} 
                      onUpdateStatus={onUpdateStatus} 
                    />
                  </td>

                  <td className="py-3 px-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {c.resumeUrl && (
                        <button
                          type="button"
                          onClick={() => {
                            const fullUrl = getAssetUrl(c.resumeUrl);
                            window.open(fullUrl, '_blank');
                          }}
                          title="View Resume"
                          className="p-1.5 hover:bg-pink-50 text-gray-500 hover:text-[#D60041] rounded-lg transition-colors cursor-pointer"
                        >
                          <FileText size={14} />
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => onOpenDetails(c)}
                        title="View Details"
                        className="p-1.5 hover:bg-pink-50 text-gray-500 hover:text-[#D60041] rounded-lg transition-colors cursor-pointer"
                      >
                        <Eye size={14} />
                      </button>

                      <button
                        type="button"
                        onClick={() => onOpenInterview(c)}
                        title="Schedule Interview"
                        className="p-1.5 hover:bg-pink-50 text-gray-500 hover:text-[#D60041] rounded-lg transition-colors cursor-pointer"
                      >
                        <Calendar size={14} />
                      </button>

                      {isArchived ? (
                        <button
                          type="button"
                          onClick={() => onRestoreApplication(c.id)}
                          title="Restore Application"
                          className="p-1.5 hover:bg-emerald-50 text-gray-400 hover:text-emerald-700 rounded-lg transition-colors cursor-pointer"
                        >
                          <RotateCcw size={14} />
                        </button>
                      ) : (
                        <button
                          type="button"
                          onClick={() => onArchiveApplication(c.id)}
                          title="Archive Application"
                          className="p-1.5 hover:bg-amber-50 text-gray-400 hover:text-amber-700 rounded-lg transition-colors cursor-pointer"
                        >
                          <Archive size={14} />
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => onDeleteApplication(c.id)}
                        title="Remove Application"
                        className="p-1.5 hover:bg-rose-50 text-gray-400 hover:text-rose-700 rounded-lg transition-colors cursor-pointer"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default CandidateTableView;
