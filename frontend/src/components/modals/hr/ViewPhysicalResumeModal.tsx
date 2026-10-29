import React, { useState } from 'react';
import {
  X,
  Download,
  Printer,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Maximize2,
  Minimize2,
  FileText,
  Building2,
  Calendar,
  Mail,
  Phone,
  FolderArchive,
  Copy,
  Check,
  User,
  ExternalLink,
  Sparkles,
  Info,
  Clock,
  Briefcase,
  Layers
} from 'lucide-react';
import { API_BASE_URL, getAssetUrl } from '../../../services/api';

interface ViewPhysicalResumeModalProps {
  isOpen: boolean;
  onClose: () => void;
  resume: any;
  onEdit?: (resume: any) => void;
}

const ViewPhysicalResumeModal: React.FC<ViewPhysicalResumeModalProps> = ({
  isOpen,
  onClose,
  resume,
  onEdit,
}) => {
  const [zoom, setZoom] = useState<number>(100);
  const [rotation, setRotation] = useState<number>(0);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [showDetails, setShowDetails] = useState<boolean>(true);
  const [copiedLocation, setCopiedLocation] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'document' | 'parsed' | 'info'>('document');

  if (!isOpen || !resume) return null;

  // Determine file type
  const filename = resume.filename || 'resume_document.pdf';
  const ext = (filename.split('.').pop() || '').toLowerCase();
  const isPdf = ext === 'pdf' || (resume.file_type && resume.file_type.includes('pdf'));
  const isImage = ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext) || (resume.file_type && resume.file_type.includes('image'));

  // Build inline view URL and direct download URL
  const inlineViewUrl = `${API_BASE_URL}/hr/physical-resumes/${resume.id}/view`;
  const downloadUrl = `${API_BASE_URL}/hr/physical-resumes/${resume.id}/download`;

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: '2-digit',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 25, 250));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 25, 50));
  const handleResetZoom = () => {
    setZoom(100);
    setRotation(0);
  };
  const handleRotate = () => setRotation((prev) => (prev + 90) % 360);

  const handleCopyLocation = () => {
    if (resume.physical_location) {
      navigator.clipboard.writeText(resume.physical_location);
      setCopiedLocation(true);
      setTimeout(() => setCopiedLocation(false), 2000);
    }
  };

  const handlePrint = () => {
    if (isPdf) {
      const printWin = window.open(inlineViewUrl, '_blank');
      if (printWin) {
        printWin.focus();
      }
    } else {
      window.print();
    }
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.setAttribute('download', resume.filename || `${(resume.candidate_name || 'Resume').replace(/\s+/g, '_')}_Physical_Resume`);
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const statusBadgeColor = (status: string) => {
    switch ((status || '').toUpperCase()) {
      case 'RECEIVED':
        return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'UNDER_REVIEW':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'SHORTLISTED':
        return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'HIRED':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'ARCHIVED':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-slate-50 text-slate-600 border-slate-200';
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-950/75 backdrop-blur-xs flex items-center justify-center p-1.5 sm:p-4 animate-in fade-in duration-200">
      <div
        className={`bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-200 border border-slate-200 ${
          isFullscreen ? 'w-full h-full rounded-none' : 'w-full max-w-7xl h-[95vh] sm:h-[94vh]'
        }`}
      >
        {/* TOP TOOLBAR */}
        <header className="px-3 sm:px-6 py-2.5 sm:py-3.5 bg-white border-b border-slate-200 flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center space-x-2.5 sm:space-x-3 min-w-0">
            <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-xl bg-gradient-to-br from-[#D60041] to-[#B50037] text-white flex items-center justify-center shadow-xs shrink-0">
              <FolderArchive size={18} className="sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-1.5 sm:space-x-2">
                <h2 className="text-xs sm:text-base font-black text-slate-900 truncate">
                  {resume.candidate_name || 'Physical Resume'}
                </h2>
                <span
                  className={`text-[9px] sm:text-[10px] font-black uppercase tracking-wider px-1.5 sm:px-2 py-0.5 rounded-full border shrink-0 ${statusBadgeColor(
                    resume.status
                  )}`}
                >
                  {resume.status || 'RECEIVED'}
                </span>
              </div>
              <p className="text-[10px] sm:text-[11px] text-slate-500 font-medium truncate flex items-center gap-1 sm:gap-1.5 mt-0.5">
                <span className="font-semibold text-slate-700 truncate max-w-[120px] sm:max-w-none">{resume.filename}</span>
                <span>•</span>
                <span className="shrink-0">{resume.formatted_file_size || 'Doc'}</span>
                <span className="hidden sm:inline">•</span>
                <span className="hidden sm:inline text-[#D60041] font-semibold truncate">{resume.target_job_title || 'General Applicant'}</span>
              </p>
            </div>
          </div>

          {/* Controls & Actions */}
          <div className="flex items-center space-x-1 sm:space-x-2 shrink-0">
            {/* Desktop Tabs (lg+) */}
            {resume.parsed_data && (
              <div className="hidden lg:flex bg-slate-100 p-0.5 rounded-lg border border-slate-200 mr-1">
                <button
                  type="button"
                  onClick={() => setActiveTab('document')}
                  className={`px-3 py-1 rounded-md text-xs font-bold transition-all cursor-pointer ${
                    activeTab === 'document' || activeTab === 'info' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Document View
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab('parsed')}
                  className={`px-3 py-1 rounded-md text-xs font-bold transition-all flex items-center gap-1 cursor-pointer ${
                    activeTab === 'parsed' ? 'bg-white text-[#D60041] shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  <Sparkles size={12} />
                  <span>AI Extracted</span>
                </button>
              </div>
            )}

            {/* Desktop Image Zoom / Rotate Controls (active when image) */}
            {isImage && (
              <div className="hidden md:flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 space-x-0.5">
                <button
                  type="button"
                  onClick={handleZoomOut}
                  title="Zoom Out"
                  className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors cursor-pointer"
                >
                  <ZoomOut size={15} />
                </button>
                <span className="text-[11px] font-bold text-slate-700 px-1.5 select-none">{zoom}%</span>
                <button
                  type="button"
                  onClick={handleZoomIn}
                  title="Zoom In"
                  className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors cursor-pointer"
                >
                  <ZoomIn size={15} />
                </button>
                <button
                  type="button"
                  onClick={handleRotate}
                  title="Rotate 90°"
                  className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-white rounded transition-colors cursor-pointer"
                >
                  <RotateCw size={15} />
                </button>
                <button
                  type="button"
                  onClick={handleResetZoom}
                  title="Reset"
                  className="text-[10px] font-black text-slate-500 hover:text-slate-800 px-1.5 hover:bg-white rounded transition-colors cursor-pointer"
                >
                  Reset
                </button>
              </div>
            )}

            {/* Desktop Toggle Details Panel */}
            <button
              type="button"
              onClick={() => setShowDetails(!showDetails)}
              title={showDetails ? 'Hide filing details panel' : 'Show filing details panel'}
              className={`hidden lg:flex p-2 rounded-xl text-xs font-bold border transition-colors items-center gap-1.5 cursor-pointer ${
                showDetails
                  ? 'bg-slate-100 border-slate-300 text-slate-800'
                  : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Info size={16} />
              <span>{showDetails ? 'Hide Info' : 'Show Info'}</span>
            </button>

            {/* Print Button */}
            <button
              type="button"
              onClick={handlePrint}
              title="Print document"
              className="p-1.5 sm:p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors cursor-pointer"
            >
              <Printer size={16} />
            </button>

            {/* Fullscreen Toggle */}
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
              className="hidden sm:flex p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-xl border border-slate-200 transition-colors cursor-pointer"
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>

            {/* DOWNLOAD BUTTON */}
            <button
              type="button"
              onClick={handleDownload}
              title="Download file"
              className="px-2.5 sm:px-3.5 py-1.5 sm:py-2 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold shadow-xs hover:shadow-md hover:shadow-pink-500/25 active:scale-95 transition-all flex items-center gap-1.5 cursor-pointer"
            >
              <Download size={14} className="sm:w-[15px] sm:h-[15px]" />
              <span className="hidden sm:inline">Download</span>
            </button>

            {/* Close Button */}
            <button
              type="button"
              onClick={onClose}
              title="Close viewer"
              aria-label="Close viewer"
              className="p-1.5 sm:p-2 text-slate-400 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
            >
              <X size={18} />
            </button>
          </div>
        </header>

        {/* MOBILE SUB-NAVIGATION BAR (< lg) */}
        <div className="lg:hidden flex items-center justify-between px-3 py-1.5 bg-slate-50 border-b border-slate-200 text-xs shrink-0">
          <div className="flex items-center space-x-1 bg-slate-200/70 p-0.5 rounded-lg w-full max-w-sm">
            <button
              type="button"
              onClick={() => setActiveTab('document')}
              className={`flex-1 py-1 px-2 rounded-md font-bold text-center transition-all cursor-pointer text-[11px] ${
                activeTab === 'document' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Document
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('info')}
              className={`flex-1 py-1 px-2 rounded-md font-bold text-center transition-all cursor-pointer text-[11px] ${
                activeTab === 'info' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Filing Info
            </button>
            {resume.parsed_data && (
              <button
                type="button"
                onClick={() => setActiveTab('parsed')}
                className={`flex-1 py-1 px-2 rounded-md font-bold text-center transition-all cursor-pointer text-[11px] flex items-center justify-center gap-1 ${
                  activeTab === 'parsed' ? 'bg-white text-[#D60041] shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Sparkles size={11} />
                <span>AI Data</span>
              </button>
            )}
          </div>
          {isImage && activeTab === 'document' && (
            <div className="flex items-center space-x-1 pl-2">
              <button
                type="button"
                onClick={handleZoomOut}
                className="p-1 text-slate-600 hover:text-slate-900 bg-white rounded border border-slate-200"
              >
                <ZoomOut size={13} />
              </button>
              <span className="text-[10px] font-bold text-slate-600 px-1">{zoom}%</span>
              <button
                type="button"
                onClick={handleZoomIn}
                className="p-1 text-slate-600 hover:text-slate-900 bg-white rounded border border-slate-200"
              >
                <ZoomIn size={13} />
              </button>
              <button
                type="button"
                onClick={handleRotate}
                className="p-1 text-slate-600 hover:text-slate-900 bg-white rounded border border-slate-200"
              >
                <RotateCw size={13} />
              </button>
            </div>
          )}
        </div>

        {/* MAIN BODY AREA */}
        <div className="flex-1 flex flex-col lg:flex-row min-h-0 overflow-hidden bg-slate-100">
          {/* DOCUMENT VIEWER CANVAS */}
          <section
            className={`flex-1 flex flex-col min-w-0 bg-slate-900/5 relative overflow-hidden ${
              activeTab === 'info' ? 'hidden lg:flex' : 'flex'
            }`}
          >
            {activeTab === 'parsed' ? (
              /* AI PARSED DATA TAB */
              <div className="w-full h-full overflow-y-auto p-4 sm:p-6 custom-scrollbar bg-white">
                <div className="max-w-3xl mx-auto space-y-5 sm:space-y-6">
                  <div className="p-3.5 sm:p-4 bg-gradient-to-r from-pink-50 to-rose-50 border border-pink-100 rounded-2xl flex items-start gap-3">
                    <div className="p-2 rounded-xl bg-[#D60041] text-white shrink-0 mt-0.5">
                      <Sparkles size={18} />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-900">Extracted Resume Intelligence</h4>
                      <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
                        Data automatically scanned and indexed from the hard-copy physical document.
                      </p>
                    </div>
                  </div>

                  {/* Skills Grid */}
                  {resume.parsed_data?.skills && (
                    <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200">
                      <h5 className="text-xs font-black uppercase tracking-wider text-slate-500 mb-2.5">
                        Identified Skills & Competencies
                      </h5>
                      <div className="flex flex-wrap gap-1.5">
                        {Array.isArray(resume.parsed_data.skills) ? (
                          resume.parsed_data.skills.map((s: string, idx: number) => (
                            <span
                              key={idx}
                              className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-xs font-semibold text-slate-800 shadow-2xs"
                            >
                              {s}
                            </span>
                          ))
                        ) : (
                          <p className="text-xs text-slate-600">{String(resume.parsed_data.skills)}</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Full Parsed Text Dump */}
                  <div className="bg-slate-50 p-4 rounded-2xl border border-slate-200">
                    <h5 className="text-xs font-black uppercase tracking-wider text-slate-500 mb-2">
                      Extracted Text Snippet
                    </h5>
                    <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap break-words leading-relaxed max-h-96 overflow-y-auto custom-scrollbar p-3 bg-white rounded-xl border border-slate-200">
                      {JSON.stringify(resume.parsed_data, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ) : isPdf ? (
              /* PDF VIEWER: In-browser embedded view with native scroll and zoom */
              <div className="w-full h-full flex flex-col p-1.5 sm:p-3 relative">
                <iframe
                  src={`${inlineViewUrl}#toolbar=1&navpanes=0&scrollbar=1&view=FitH`}
                  className="w-full h-full rounded-xl border border-slate-200 bg-white shadow-xs"
                  title={`Physical Resume - ${resume.candidate_name}`}
                />
              </div>
            ) : isImage ? (
              /* IMAGE VIEWER: For scanned photos and camera scans */
              <div className="w-full h-full overflow-auto flex items-center justify-center p-3 sm:p-4 custom-scrollbar select-none">
                <div
                  style={{
                    transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                    transformOrigin: 'center center',
                    transition: 'transform 0.15s ease-out',
                  }}
                  className="max-w-full max-h-full flex items-center justify-center"
                >
                  <img
                    src={inlineViewUrl}
                    alt={`Physical Resume of ${resume.candidate_name}`}
                    className="max-w-none rounded-lg shadow-xl border border-slate-200 bg-white"
                    style={{ maxHeight: isFullscreen ? '90vh' : '80vh' }}
                  />
                </div>
              </div>
            ) : (
              /* FALLBACK VIEWER FOR DOCX OR OTHER FORMATS */
              <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center">
                <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-white border border-slate-200 shadow-xs flex items-center justify-center text-[#D60041] mb-4">
                  <FileText size={32} className="sm:w-9 sm:h-9" />
                </div>
                <h3 className="text-base sm:text-lg font-black text-slate-900 mb-1">{resume.filename}</h3>
                <p className="text-xs text-slate-500 max-w-md mb-6 leading-relaxed">
                  This document format ({ext.toUpperCase()}) is stored in the physical resume vault. You can download the file to inspect full formatting, or read the AI extracted contents below.
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2.5 sm:gap-3">
                  <button
                    type="button"
                    onClick={handleDownload}
                    className="px-4 py-2.5 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold shadow-xs hover:shadow-md transition-all flex items-center gap-2 cursor-pointer"
                  >
                    <Download size={16} />
                    <span>Download {ext.toUpperCase()} File</span>
                  </button>
                  {resume.parsed_data && (
                    <button
                      type="button"
                      onClick={() => setActiveTab('parsed')}
                      className="px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer"
                    >
                      <Sparkles size={16} className="text-[#D60041]" />
                      <span>View AI Extracted Data</span>
                    </button>
                  )}
                </div>
              </div>
            )}
          </section>

          {/* RIGHT SIDE PANEL: FILING & CANDIDATE DETAILS */}
          <aside
            className={`w-full lg:w-96 bg-white border-t lg:border-t-0 lg:border-l border-slate-200 flex flex-col shrink-0 overflow-y-auto custom-scrollbar ${
              activeTab === 'info'
                ? 'flex flex-1 lg:flex-none'
                : showDetails
                ? 'hidden lg:flex'
                : 'hidden'
            }`}
          >
            <div className="p-4 sm:p-6 space-y-5 sm:space-y-6">
              {/* Physical Filing Vault Reference Card */}
              <div className="p-4 rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white shadow-md relative overflow-hidden">
                <div className="absolute top-0 right-0 w-32 h-32 bg-[#D60041]/15 rounded-full blur-2xl -mr-16 -mt-16 pointer-events-none" />
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-wider text-pink-400 flex items-center gap-1">
                      <FolderArchive size={12} />
                      Physical Storage Location
                    </span>
                    <button
                      type="button"
                      onClick={handleCopyLocation}
                      className="text-[10px] font-bold text-white/70 hover:text-white flex items-center gap-1 cursor-pointer transition-colors"
                      title="Copy filing location to clipboard"
                    >
                      {copiedLocation ? (
                        <>
                          <Check size={12} className="text-emerald-400" />
                          <span className="text-emerald-400 font-bold">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy size={12} />
                          <span>Copy Ref</span>
                        </>
                      )}
                    </button>
                  </div>

                  <p className="text-base font-black tracking-tight text-white mt-1 break-words">
                    {resume.physical_location || 'General HR Archive'}
                  </p>

                  <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] text-white/70">
                    <span>Submitted:</span>
                    <span className="font-semibold text-white">
                      {formatDate(resume.submission_date)}
                    </span>
                  </div>

                  {resume.hr_name && (
                    <div className="mt-1 flex items-center justify-between text-[11px] text-white/70">
                      <span>Stored by:</span>
                      <span className="font-semibold text-white">{resume.hr_name}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Candidate Info */}
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-2.5 sm:mb-3 flex items-center gap-1.5">
                  <User size={14} className="text-[#D60041]" />
                  Candidate Credentials
                </h4>
                <div className="space-y-2 sm:space-y-2.5">
                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Full Name</span>
                    <span className="text-xs font-black text-slate-900">{resume.candidate_name}</span>
                  </div>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Target Requisition</span>
                      <span className="text-xs font-black text-slate-900">{resume.target_job_title || 'Unassigned / Open'}</span>
                    </div>
                    <Briefcase size={16} className="text-slate-400 shrink-0" />
                  </div>

                  {resume.candidate_email && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                      <div className="min-w-0 pr-2">
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Email Address</span>
                        <a
                          href={`mailto:${resume.candidate_email}`}
                          className="text-xs font-bold text-[#D60041] hover:underline truncate block"
                        >
                          {resume.candidate_email}
                        </a>
                      </div>
                      <Mail size={16} className="text-slate-400 shrink-0" />
                    </div>
                  )}

                  {resume.candidate_phone && (
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Contact Number</span>
                        <a href={`tel:${resume.candidate_phone}`} className="text-xs font-bold text-slate-800 hover:text-[#D60041]">
                          {resume.candidate_phone}
                        </a>
                      </div>
                      <Phone size={16} className="text-slate-400 shrink-0" />
                    </div>
                  )}
                </div>
              </div>

              {/* HR Notes / Submission Context */}
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                  <Info size={14} className="text-[#D60041]" />
                  HR Notes & Context
                </h4>
                <div className="p-3.5 bg-slate-50 rounded-xl border border-slate-100 text-xs text-slate-700 leading-relaxed font-medium">
                  {resume.notes || (
                    <span className="text-slate-400 italic">No notes recorded for this physical submission.</span>
                  )}
                </div>
              </div>

              {/* Edit & Download Actions */}
              <div className="pt-2 border-t border-slate-100 space-y-2">
                <button
                  type="button"
                  onClick={handleDownload}
                  className="w-full py-2.5 px-4 bg-[#D60041] hover:bg-[#B50037] text-white rounded-xl text-xs font-bold transition-all shadow-xs hover:shadow-md flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Download size={14} />
                  <span>Download Physical Resume File</span>
                </button>

                {onEdit && (
                  <button
                    type="button"
                    onClick={() => {
                      onEdit(resume);
                    }}
                    className="w-full py-2 px-4 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <span>Edit Filing Details & Notes</span>
                  </button>
                )}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
};

export default ViewPhysicalResumeModal;
