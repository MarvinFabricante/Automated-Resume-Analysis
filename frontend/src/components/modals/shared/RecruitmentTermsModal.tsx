import React from 'react';
import { FileText, X } from 'lucide-react';

interface RecruitmentTermsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAccept: () => void;
}

const RecruitmentTermsModal: React.FC<RecruitmentTermsModalProps> = ({ isOpen, onClose, onAccept }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-300">
      <div className="bg-white rounded-[40px] shadow-2xl w-full max-w-2xl max-h-[80vh] flex flex-col overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-8 duration-300">
        <div className="p-8 border-b border-slate-50 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-pink-50 text-[#D10043] rounded-xl flex items-center justify-center">
              <FileText size={20} />
            </div>
            <h3 className="text-xl font-black text-slate-900 tracking-tight">Recruitment Terms</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-white rounded-full transition-all text-slate-400 hover:text-slate-900 border border-transparent hover:border-slate-100"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-8 overflow-y-auto text-slate-600 space-y-6 leading-relaxed">
          <section>
            <h4 className="font-bold text-slate-900 mb-2">1. Data Collection</h4>
            <p className="text-sm">By submitting your resume, you authorize Mariwasa Siam Ceramics Inc. to collect, store, and process your personal and professional information for recruitment purposes. This includes data extraction using our AI-powered analysis system.</p>
          </section>
          <section>
            <h4 className="font-bold text-slate-900 mb-2">2. AI Analysis</h4>
            <p className="text-sm">Our system automatically parses resume data to match candidates with suitable job openings. This automated process is designed to ensure a fair, skill-based assessment. Final hiring decisions are always made by our human HR staff.</p>
          </section>
          <section>
            <h4 className="font-bold text-slate-900 mb-2">3. Data Retention</h4>
            <p className="text-sm">Your data will be kept in our secure talent pool for a period of 12 months, unless you request its removal earlier. This allows us to consider you for future opportunities that match your profile.</p>
          </section>
          <section>
            <h4 className="font-bold text-slate-900 mb-2">4. Accuracy of Information</h4>
            <p className="text-sm">You certify that all information provided in your resume and application form is true and correct. Provision of false information may lead to disqualification from the recruitment process.</p>
          </section>
        </div>

        <div className="p-8 border-t border-slate-50 bg-slate-50/50 flex justify-end">
          <button
            onClick={() => {
              onAccept();
              onClose();
            }}
            className="bg-[#D10043] hover:bg-slate-900 text-white px-10 py-4 rounded-2xl font-bold transition-all shadow-lg shadow-pink-100"
          >
            I Accept These Terms
          </button>
        </div>
      </div>
    </div>
  );
};

export default RecruitmentTermsModal;
