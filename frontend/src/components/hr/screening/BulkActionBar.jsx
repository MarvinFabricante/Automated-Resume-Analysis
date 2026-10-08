import React, { useState, useRef, useEffect } from 'react';
import { 
  Scale, Archive, Trash2, Download, X, CheckSquare, Square, 
  ChevronDown, CheckCircle2, Clock, Check
} from 'lucide-react';

const BulkActionBar = ({
  selectedCount,
  totalFilteredCount,
  allSelected,
  onToggleSelectAll,
  onClearSelection,
  onCompare,
  onBatchStatusUpdate,
  onBatchArchive,
  onBatchDelete,
  onBatchExport
}) => {
  const [statusMenuOpen, setStatusMenuOpen] = useState(false);
  const statusMenuRef = useRef(null);

  useEffect(() => {
    const handleOutside = (e) => {
      if (statusMenuRef.current && !statusMenuRef.current.contains(e.target)) {
        setStatusMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  if (selectedCount === 0) return null;

  return (
    <div className="sticky top-20 z-30 mb-5 bg-gray-900/95 backdrop-blur-md text-white px-3.5 sm:px-5 py-3 rounded-2xl shadow-xl flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 animate-in slide-in-from-top-3 duration-250 border border-gray-800">
      
      {/* Left: Selected count & Select all toggle */}
      <div className="flex items-center justify-between sm:justify-start gap-3">
        <button
          type="button"
          onClick={onToggleSelectAll}
          className="flex items-center gap-2 text-xs font-bold text-gray-300 hover:text-white transition-colors cursor-pointer"
        >
          {allSelected ? <CheckSquare size={16} className="text-[#D60041]" /> : <Square size={16} />}
          <span>{allSelected ? 'Deselect All' : `Select All (${totalFilteredCount})`}</span>
        </button>

        <span className="h-4 w-[1px] bg-gray-700 hidden sm:block"></span>

        <span className="text-xs font-bold text-white bg-gray-800/80 px-2.5 py-1 rounded-lg border border-gray-700">
          <span className="text-[#D60041] font-black">{selectedCount}</span> Selected
        </span>

        {/* Mobile close button */}
        <button
          type="button"
          onClick={onClearSelection}
          title="Clear Selection"
          className="sm:hidden p-1.5 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors ml-auto cursor-pointer"
        >
          <X size={15} />
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
        {/* Compare Candidates */}
        <button
          type="button"
          onClick={onCompare}
          disabled={selectedCount < 2}
          title={selectedCount < 2 ? "Select at least 2 candidates to compare" : "Compare selected candidates"}
          className={`flex items-center gap-1.5 px-3 py-1.5 sm:py-2 rounded-xl text-xs font-bold transition-all ${
            selectedCount >= 2
              ? 'bg-[#D60041] text-white hover:bg-[#B50037] shadow-sm cursor-pointer'
              : 'bg-gray-800/60 text-gray-500 cursor-not-allowed border border-gray-700/60'
          }`}
        >
          <Scale size={13} />
          <span>Compare ({selectedCount})</span>
        </button>

        {/* Change Status Dropdown */}
        <div className="relative" ref={statusMenuRef}>
          <button
            type="button"
            onClick={() => setStatusMenuOpen(!statusMenuOpen)}
            className="flex items-center gap-1.5 px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-xl text-xs font-bold transition-all cursor-pointer"
          >
            <span>Update Status</span>
            <ChevronDown size={12} className={`transition-transform duration-200 ${statusMenuOpen ? 'rotate-180' : ''}`} />
          </button>

          {statusMenuOpen && (
            <div className="absolute top-full right-0 mt-1.5 w-48 bg-white text-gray-800 border border-gray-100 rounded-2xl shadow-xl z-50 py-1.5 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-1 text-[10px] font-bold text-gray-400 uppercase tracking-widest border-b border-gray-100 mb-1">
                Set status for {selectedCount} candidates:
              </div>
              {['Pending', 'Reviewed', 'Technical Interview', 'Final Interview', 'Accepted', 'Rejected'].map((st) => (
                <button
                  key={st}
                  type="button"
                  onClick={() => {
                    setStatusMenuOpen(false);
                    onBatchStatusUpdate(st);
                  }}
                  className="w-full text-left px-3.5 py-1.5 text-xs font-bold hover:bg-pink-50 hover:text-[#D60041] transition-colors flex items-center justify-between cursor-pointer"
                >
                  <span>{st}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Export Selected to CSV */}
        <button
          type="button"
          onClick={onBatchExport}
          title="Export selected candidates to CSV"
          className="flex items-center gap-1.5 px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-xl text-xs font-bold transition-all cursor-pointer"
        >
          <Download size={13} />
          <span>Export</span>
        </button>

        {/* Archive Selected */}
        <button
          type="button"
          onClick={onBatchArchive}
          title="Archive selected candidates"
          className="flex items-center gap-1.5 px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-amber-950/40 text-amber-300 border border-gray-700 hover:border-amber-700/50 rounded-xl text-xs font-bold transition-all cursor-pointer"
        >
          <Archive size={13} />
          <span className="hidden sm:inline">Archive</span>
        </button>

        {/* Delete Selected */}
        <button
          type="button"
          onClick={onBatchDelete}
          title="Remove selected candidates"
          className="flex items-center gap-1.5 px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-rose-950/60 text-rose-300 border border-gray-700 hover:border-rose-800/50 rounded-xl text-xs font-bold transition-all cursor-pointer"
        >
          <Trash2 size={13} />
          <span className="hidden sm:inline">Remove</span>
        </button>

        {/* Desktop Deselect / Cancel */}
        <button
          type="button"
          onClick={onClearSelection}
          title="Clear Selection"
          className="hidden sm:block p-2 text-gray-400 hover:text-white rounded-lg hover:bg-gray-800 transition-colors cursor-pointer"
        >
          <X size={15} />
        </button>
      </div>
    </div>
  );
};

export default BulkActionBar;
