import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const Pagination = ({
  currentPage,
  totalItems,
  itemsPerPage,
  onPageChange,
  onItemsPerPageChange
}) => {
  if (totalItems === 0) return null;

  const totalPages = itemsPerPage === 'all' ? 1 : Math.ceil(totalItems / itemsPerPage);
  const startItem = itemsPerPage === 'all' ? 1 : (currentPage - 1) * itemsPerPage + 1;
  const endItem = itemsPerPage === 'all' ? totalItems : Math.min(currentPage * itemsPerPage, totalItems);

  // Generate page numbers
  const getPageNumbers = () => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    const pages = [1];
    if (currentPage > 3) pages.push('...');
    const start = Math.max(2, currentPage - 1);
    const end = Math.min(totalPages - 1, currentPage + 1);
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    if (currentPage < totalPages - 2) pages.push('...');
    pages.push(totalPages);
    return pages;
  };

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4 mt-6 sm:mt-8 pt-4 sm:pt-6 border-t border-gray-200/80 text-xs text-gray-500 font-medium">
      
      {/* Left: Summary and Page Size */}
      <div className="flex items-center gap-2.5 sm:gap-3 flex-wrap justify-center sm:justify-start">
        <span>
          Showing <span className="font-bold text-gray-900">{startItem}</span>–<span className="font-bold text-gray-900">{endItem}</span> of <span className="font-bold text-gray-900">{totalItems}</span>
        </span>

        <span className="text-gray-300">•</span>

        <div className="flex items-center gap-1.5">
          <span className="text-gray-400">Rows:</span>
          <select
            value={itemsPerPage}
            onChange={(e) => onItemsPerPageChange(e.target.value === 'all' ? 'all' : parseInt(e.target.value, 10))}
            className="bg-gray-50 border border-gray-200 rounded-lg px-2 py-1 text-xs font-bold text-gray-700 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 cursor-pointer"
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value="all">All</option>
          </select>
        </div>
      </div>

      {/* Right: Page Buttons */}
      {totalPages > 1 && (
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => onPageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer disabled:cursor-not-allowed"
            title="Previous page"
          >
            <ChevronLeft size={16} />
          </button>

          {/* Desktop full numbered page list */}
          <div className="hidden sm:flex items-center gap-1">
            {getPageNumbers().map((p, idx) => {
              if (p === '...') {
                return <span key={idx} className="px-1.5 py-1 text-gray-400 font-bold">...</span>;
              }
              const isCurrent = p === currentPage;
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => onPageChange(p)}
                  className={`min-w-[32px] h-8 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    isCurrent 
                      ? 'bg-[#D60041] text-white shadow-xs' 
                      : 'border border-gray-200 text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {p}
                </button>
              );
            })}
          </div>

          {/* Mobile compact indicator */}
          <span className="sm:hidden px-3 py-1 text-xs font-bold text-gray-700 bg-gray-50 border border-gray-200 rounded-lg">
            Page {currentPage} / {totalPages}
          </span>

          <button
            type="button"
            onClick={() => onPageChange(currentPage + 1)}
            disabled={currentPage === totalPages}
            className="p-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer disabled:cursor-not-allowed"
            title="Next page"
          >
            <ChevronRight size={16} />
          </button>
        </div>
      )}

    </div>
  );
};

export default Pagination;
