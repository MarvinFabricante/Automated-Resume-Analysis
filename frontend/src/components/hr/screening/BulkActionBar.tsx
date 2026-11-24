import React, { useState, useRef } from 'react';
import {
  Scale, Archive, Download, X, CheckSquare, Square,
  ChevronDown
} from 'lucide-react';
import PortalDropdown, { PortalDropdownItem } from '../../common/PortalDropdown';

interface BulkActionBarProps {
  selectedCount: number;
  totalFilteredCount: number;
  allSelected: boolean;
  onToggleSelectAll: () => void;
  onClearSelection: () => void;
  onCompare: () => void;
  onBatchStatusUpdate: (status: string) => void;
  onBatchArchive: () => void;
  onBatchDelete: () => void;
  onBatchExport: () => void;
}

const BulkActionBar: React.FC<BulkActionBarProps> = ({
  selectedCount,
  totalFilteredCount,
  allSelected,
  onToggleSelectAll,
  onClearSelection,
  onCompare,
  onBatchStatusUpdate,
  onBatchArchive,
  onBatchExport
}) => {
  const [statusMenuOpen, setStatusMenuOpen] = useState<boolean>(false);
  const statusButtonRef = useRef<HTMLButtonElement>(null);

  if (selectedCount === 0) return null;

  const bulkStatusItems: PortalDropdownItem[] = [
    'Submitted',
    'Under Review',
    'Shortlisted',
    'Interview Scheduled',
    'Interviewed',
    'Passed initial interview',
    'Not Selected',
  ].map((st) => ({
    id: st,
    label: st,
    onSelect: () => onBatchStatusUpdate(st),
  }));

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
      <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 w-full sm:w-auto">
        {/* Compare Candidates */}
        <button
          type="button"
          onClick={onCompare}
          disabled={selectedCount < 2}
          title={selectedCount < 2 ? "Select at least 2 candidates to compare" : "Compare selected candidates"}
          className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 px-3 py-1.5 sm:py-2 rounded-xl text-xs font-bold transition-all h-8.5 sm:h-9 ${selectedCount >= 2
              ? 'bg-[#D60041] text-white hover:bg-[#B50037] shadow-sm cursor-pointer'
              : 'bg-gray-800/60 text-gray-500 cursor-not-allowed border border-gray-700/60'
            }`}
        >
          <Scale size={13} />
          <span>Compare ({selectedCount})</span>
        </button>

        {/* Change Status Dropdown (Rendered in Portal) */}
        <div className="relative flex-1 sm:flex-none">
          <button
            ref={statusButtonRef}
            type="button"
            aria-haspopup="menu"
            aria-expanded={statusMenuOpen}
            onClick={() => setStatusMenuOpen((prev) => !prev)}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-xl text-xs font-bold transition-all cursor-pointer h-8.5 sm:h-9"
          >
            <span>Status</span>
            <ChevronDown size={12} className={`transition-transform duration-200 ${statusMenuOpen ? 'rotate-180' : ''}`} />
          </button>

          <PortalDropdown
            isOpen={statusMenuOpen}
            onClose={() => setStatusMenuOpen(false)}
            anchorRef={statusButtonRef}
            align="right"
            minWidth={210}
            items={bulkStatusItems}
            ariaLabel={`Set status for ${selectedCount} selected candidates`}
          />
        </div>

        {/* Export Selected to CSV */}
        <button
          type="button"
          onClick={onBatchExport}
          title="Export selected candidates to CSV"
          className="flex items-center justify-center gap-1.5 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 rounded-xl text-xs font-bold transition-all cursor-pointer h-8.5 sm:h-9"
        >
          <Download size={13} />
          <span>Export</span>
        </button>

        {/* Archive Selected */}
        <button
          type="button"
          onClick={onBatchArchive}
          title="Archive selected candidates"
          className="flex items-center justify-center gap-1.5 px-2.5 sm:px-3 py-1.5 sm:py-2 bg-gray-800 hover:bg-amber-950/40 text-amber-300 border border-gray-700 hover:border-amber-700/50 rounded-xl text-xs font-bold transition-all cursor-pointer h-8.5 sm:h-9"
        >
          <Archive size={13} />
          <span className="hidden sm:inline">Archive</span>
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
