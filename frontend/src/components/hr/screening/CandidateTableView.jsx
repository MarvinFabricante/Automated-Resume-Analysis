import React, { useState, useRef, useEffect } from 'react';
import { 
  Calendar, MapPin, ChevronDown, CheckCircle2, XCircle, Clock, Search, 
  Check, Archive, Trash2, RotateCcw, FileText, Download, Copy, Mail, Phone, Eye
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
      case 'accepted': return { color: 'text-emerald-700 bg-emerald-50 border-emerald-200', label: 'Accepted' };
      case 'rejected': return { color: 'text-rose-700 bg-rose-50 border-rose-200', label: 'Rejected' };
      case 'reviewed': return { color: 'text-blue-700 bg-blue-50 border-blue-200', label: 'Reviewed' };
      case 'technical interview': return { color: 'text-purple-700 bg-purple-50 border-purple-200', label: 'Technical Interview' };
      case 'final interview': return { color: 'text-indigo-700 bg-indigo-50 border-indigo-200', label: 'Final Interview' };
      case 'archived': return { color: 'text-gray-700 bg-gray-100 border-gray-200', label: 'Archived' };
      default: return { color: 'text-amber-700 bg-amber-50 border-amber-200', label: 'Pending' };
    }
  };

  const currentInfo = getStatusInfo(status);

  return (
    <div className="relative inline-block" ref={ref}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isUpdating}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-[11px] font-bold uppercase tracking-wider transition-all ${currentInfo.color} ${isUpdating ? 'opacity-50 animate-pulse' : 'hover:shadow-sm'}`}
      >
        <span className="truncate max-w-[110px]">{currentInfo.label}</span>
        <ChevronDown size={12} className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-44 bg-white border border-gray-100 rounded-xl shadow-xl z-50 py-1.5 animate-in fade-in zoom-in-95 duration-150">
          {['Pending', 'Reviewed', 'Technical Interview', 'Final Interview', 'Accepted', 'Rejected'].map((s) => (
            <button
              key={s}
              onClick={async () => {
                setIsOpen(false);
                setIsUpdating(true);
                await onUpdateStatus(candidateId, s);
                setTimeout(() => setIsUpdating(false), 600);
              }}
              className={`w-full flex items-center justify-between px-3 py-1.5 text-[11px] font-bold uppercase tracking-wider transition-colors ${
                (status || '').toLowerCase() === s.toLowerCase() 
                  ? 'bg-pink-50 text-[#D60041]' 
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              <span>{s}</span>
              {(status || '').toLowerCase() === s.toLowerCase() && <Check size={12} />}
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
    <div className="bg-white rounded-2xl sm:rounded-[32px] border border-gray-100 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50/70 border-b border-gray-100 text-[10px] font-bold uppercase tracking-wider text-gray-500">
              <th className="py-4 px-4 w-12 text-center">
                <input
                  type="checkbox"
                  checked={allSelected}
                  onChange={onSelectAll}
                  className="w-4 h-4 rounded border-gray-300 text-[#D60041] focus:ring-[#D60041] cursor-pointer"
                />
              </th>
              <th className="py-4 px-4">Candidate</th>
              <th className="py-4 px-4">Applied Role</th>
              <th className="py-4 px-4 text-center">Match</th>
              <th className="py-4 px-4">Skills</th>
              <th className="py-4 px-4">Applied Date</th>
              <th className="py-4 px-4">Status</th>
              <th className="py-4 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {candidates.map((c) => {
              const isSelected = selectedIds.includes(c.id);
              const isArchived = (c.status || '').toLowerCase() === 'archived';
              const match = Math.round(c.matchScore || 0);

              const avatarUrl = c.profileImage
                ? getAssetUrl(c.profileImage)
                : `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name)}&background=fdf2f8&color=d81159&bold=true`;

              const matchColor = match >= 80 
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200' 
                : match >= 60 
                  ? 'text-amber-700 bg-amber-50 border-amber-200' 
                  : 'text-rose-700 bg-rose-50 border-rose-200';

              return (
                <tr 
                  key={c.id} 
                  className={`hover:bg-pink-50/20 transition-colors ${isSelected ? 'bg-pink-50/30' : ''}`}
                >
                  <td className="py-3.5 px-4 text-center">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(c.id)}
                      className="w-4 h-4 rounded border-gray-300 text-[#D60041] focus:ring-[#D60041] cursor-pointer"
                    />
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl overflow-hidden border border-gray-100 shrink-0 bg-pink-50">
                        <img 
                          src={avatarUrl} 
                          alt={c.name} 
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name)}&background=fdf2f8&color=d81159&bold=true`;
                          }}
                        />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <button
                            onClick={() => onOpenDetails(c)}
                            className="font-bold text-sm text-gray-900 hover:text-[#D60041] transition-colors truncate text-left"
                          >
                            {c.name}
                          </button>
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-gray-400 font-medium">
                          <span className="truncate max-w-[150px]">{c.email || 'N/A'}</span>
                          {c.email && c.email !== 'N/A' && (
                            <button
                              onClick={() => handleCopy(c.email, `email-${c.id}`)}
                              title="Copy Email"
                              className="hover:text-gray-700 transition-colors"
                            >
                              {copiedId === `email-${c.id}` ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-gray-800 truncate">{c.preferredJob}</p>
                      <p className="text-[10px] text-gray-400 font-medium flex items-center gap-1 mt-0.5">
                        <MapPin size={10} />
                        <span className="truncate">{c.location}</span>
                      </p>
                    </div>
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    <div className="inline-flex flex-col items-center">
                      <span className={`px-2 py-0.5 rounded-lg border text-xs font-black ${matchColor}`}>
                        {match}%
                      </span>
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="flex flex-wrap gap-1 max-w-[200px]">
                      {(c.skills || []).slice(0, 3).map((skill, idx) => (
                        <button
                          key={idx}
                          onClick={() => onSkillClick && onSkillClick(skill)}
                          title={`Filter by ${skill}`}
                          className="px-2 py-0.5 bg-gray-50 border border-gray-100 hover:border-pink-200 hover:text-[#D60041] text-gray-500 text-[10px] font-semibold rounded-lg transition-colors truncate max-w-[100px]"
                        >
                          {skill}
                        </button>
                      ))}
                      {(c.skills || []).length > 3 && (
                        <span className="px-1.5 py-0.5 bg-gray-50 text-gray-400 text-[10px] font-bold rounded-lg">
                          +{c.skills.length - 3}
                        </span>
                      )}
                    </div>
                  </td>

                  <td className="py-3.5 px-4">
                    <span className="text-xs font-medium text-gray-500 whitespace-nowrap">
                      {formatDate(c.date)}
                    </span>
                  </td>

                  <td className="py-3.5 px-4">
                    <TableStatusDropdown 
                      status={c.status} 
                      candidateId={c.id} 
                      onUpdateStatus={onUpdateStatus} 
                    />
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {c.resumeUrl && (
                        <button
                          onClick={() => {
                            const fullUrl = getAssetUrl(c.resumeUrl);
                            window.open(fullUrl, '_blank');
                          }}
                          title="View / Download Resume"
                          className="p-2 hover:bg-gray-100 text-gray-500 hover:text-gray-900 rounded-lg transition-colors"
                        >
                          <FileText size={15} />
                        </button>
                      )}

                      <button
                        onClick={() => onOpenDetails(c)}
                        title="View Candidate Details"
                        className="p-2 hover:bg-pink-50 text-gray-500 hover:text-[#D60041] rounded-lg transition-colors"
                      >
                        <Eye size={15} />
                      </button>

                      <button
                        onClick={() => onOpenInterview(c)}
                        title="Schedule Interview"
                        className="p-2 hover:bg-pink-50 text-gray-500 hover:text-[#D60041] rounded-lg transition-colors"
                      >
                        <Calendar size={15} />
                      </button>

                      {isArchived ? (
                        <button
                          onClick={() => onRestoreApplication(c.id)}
                          title="Restore Application"
                          className="p-2 hover:bg-emerald-50 text-gray-400 hover:text-emerald-600 rounded-lg transition-colors"
                        >
                          <RotateCcw size={15} />
                        </button>
                      ) : (
                        <button
                          onClick={() => onArchiveApplication(c.id)}
                          title="Archive Application"
                          className="p-2 hover:bg-amber-50 text-gray-400 hover:text-amber-600 rounded-lg transition-colors"
                        >
                          <Archive size={15} />
                        </button>
                      )}

                      <button
                        onClick={() => onDeleteApplication(c.id)}
                        title="Delete Application"
                        className="p-2 hover:bg-rose-50 text-gray-400 hover:text-rose-600 rounded-lg transition-colors"
                      >
                        <Trash2 size={15} />
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
