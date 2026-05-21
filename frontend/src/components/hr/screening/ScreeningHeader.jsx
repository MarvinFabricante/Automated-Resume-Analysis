import React from 'react';
import { Download } from 'lucide-react';

const ScreeningHeader = ({ onExport }) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
      <div>
        <h1 className="text-3xl font-black text-gray-900 tracking-tight">Resume Screening</h1>
        <p className="text-gray-500 font-medium mt-1">Review and manage candidate applications</p>
      </div>

      <div className="flex items-center gap-2">
        <button 
          onClick={onExport}
          className="flex items-center gap-2 px-6 py-3.5 bg-white border border-gray-100 rounded-2xl text-sm font-bold text-gray-700 hover:border-pink-100 hover:text-[#D60041] hover:bg-pink-50 transition-all duration-300 shadow-sm hover:scale-[1.02] active:scale-[0.98] group"
        >
          <Download className="w-4 h-4 text-gray-400 group-hover:text-[#D60041] transition-colors" />
          Export List
        </button>
      </div>
    </div>
  );
};

export default ScreeningHeader;
