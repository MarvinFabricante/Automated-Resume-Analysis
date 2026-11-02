import React, { useState, useEffect, useRef } from 'react';
import {
  FileText,
  X,
  FileUp,
  Download,
  ExternalLink,
  Maximize2,
  Minimize2,
  Eye,
  CheckCircle2,
  Layers,
  Sparkles,
  AlignLeft,
  Briefcase,
  GraduationCap,
  Cpu
} from 'lucide-react';
import { getAssetUrl } from '../../../services/api';

export interface ResumePreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  file?: File | { name: string; size: number } | null;
  fileUrl?: string | null;
  resumeUrl?: string | null;
  fileName?: string | null;
  rawText?: string | null;
  extractedData?: any;
  onReplaceFile?: (newFile: File) => void;
  onReplace?: () => void;
}

const ResumePreviewModal: React.FC<ResumePreviewModalProps> = ({
  isOpen,
  onClose,
  file,
  fileUrl,
  resumeUrl,
  fileName,
  rawText,
  extractedData,
  onReplaceFile,
  onReplace
}) => {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string>('');
  const [activeTab, setActiveTab] = useState<'document' | 'text'>('document');
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Compute effective filename and size
  const effectiveFileName =
    fileName ||
    (file && 'name' in file ? file.name : null) ||
    extractedData?.filename ||
    'Resume_Document.pdf';

  const effectiveFileSize =
    file && 'size' in file && file.size
      ? `${(file.size / (1024 * 1024)).toFixed(2)} MB`
      : null;

  const ext = (effectiveFileName.split('.').pop() || 'pdf').toLowerCase();
  const isPdf = ext === 'pdf';
  const isTxt = ext === 'txt';
  const isDocx = ext === 'docx' || ext === 'doc';

  // Manage Blob URL for client-side File objects
  useEffect(() => {
    if (file && file instanceof File) {
      const url = URL.createObjectURL(file);
      setBlobUrl(url);

      if (isTxt) {
        file.text().then(text => setTextContent(text)).catch(() => {});
      }

      return () => {
        URL.revokeObjectURL(url);
        setBlobUrl(null);
      };
    } else {
      setBlobUrl(null);
    }
  }, [file, isTxt]);

  // Load raw text fallback
  useEffect(() => {
    if (rawText) {
      setTextContent(rawText);
    } else if (extractedData?.raw_text) {
      setTextContent(extractedData.raw_text);
    }
  }, [rawText, extractedData]);

  if (!isOpen) return null;

  // Resolve best URL for viewing
  const activeUrl = fileUrl || resumeUrl || extractedData?.file_url;
  const resolvedUrl = blobUrl || (activeUrl ? getAssetUrl(activeUrl) : null);
  const hasReplace = Boolean(onReplaceFile || onReplace);

  const handleTriggerReplace = () => {
    if (onReplace) {
      onReplace();
    } else if (fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected && onReplaceFile) {
      onReplaceFile(selected);
    }
    // Reset file input value so selecting the same file triggers change
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDownload = () => {
    if (resolvedUrl) {
      const link = document.createElement('a');
      link.href = resolvedUrl;
      link.download = effectiveFileName;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  return (
    <div
      id="resume-preview-backdrop"
      data-testid="resume-preview-modal"
      className="fixed inset-0 z-[120] flex items-center justify-center p-2 sm:p-4 md:p-6 bg-slate-900/70 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div
        className={`bg-white rounded-3xl sm:rounded-[36px] shadow-2xl w-full flex flex-col overflow-hidden border border-slate-200 transition-all duration-300 ${
          isFullscreen
            ? 'w-full h-full max-w-none max-h-none rounded-none'
            : 'max-w-5xl max-h-[92vh] h-[850px]'
        }`}
      >
        {/* MODAL HEADER */}
        <div className="p-4 sm:p-6 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-slate-50/80 via-white to-slate-50/80 shrink-0">
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="w-11 h-11 bg-pink-50 text-[#D10043] rounded-2xl flex items-center justify-center shrink-0 border border-pink-100/80 shadow-2xs">
              <FileText size={22} />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base sm:text-lg font-black text-slate-900 tracking-tight truncate">
                  {effectiveFileName}
                </h3>
                <span className="px-2 py-0.5 rounded-md bg-[#D10043]/10 text-[#D10043] font-black text-[10px] uppercase tracking-wider border border-[#D10043]/20">
                  {ext.toUpperCase()}
                </span>
                {effectiveFileSize && (
                  <span className="text-[11px] text-slate-400 font-semibold hidden sm:inline">
                    • {effectiveFileSize}
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 font-medium mt-0.5 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                Applicant Resume Review & Verification
              </p>
            </div>
          </div>

          {/* HEADER CONTROLS */}
          <div className="flex items-center gap-2 shrink-0 ml-3">
            {/* Tab switch between Document Layout & Extracted ATS Content */}
            <div className="hidden md:flex items-center bg-slate-100/80 p-1 rounded-xl border border-slate-200/60">
              <button
                type="button"
                onClick={() => setActiveTab('document')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  activeTab === 'document'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <Eye size={13} />
                <span>Document View</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('text')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                  activeTab === 'text'
                    ? 'bg-white text-slate-900 shadow-2xs'
                    : 'text-slate-500 hover:text-slate-900'
                }`}
              >
                <AlignLeft size={13} />
                <span>Extracted Content</span>
              </button>
            </div>

            {/* Replace Resume Action */}
            {hasReplace && (
              <button
                id="modal-btn-replace-resume"
                data-testid="modal-replace-resume-btn"
                type="button"
                onClick={handleTriggerReplace}
                className="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-[#D10043] text-slate-700 hover:text-white border border-slate-200 hover:border-transparent text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs"
                title="Replace with another resume"
              >
                <FileUp size={14} />
                <span className="hidden sm:inline">Replace Resume</span>
              </button>
            )}

            {/* Download / Open New Tab */}
            {resolvedUrl && (
              <button
                id="modal-btn-download"
                type="button"
                onClick={handleDownload}
                className="p-2 sm:px-3 sm:py-2 rounded-xl bg-slate-100 hover:bg-slate-200/80 text-slate-700 text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer"
                title="Download or open original file"
              >
                <Download size={15} />
                <span className="hidden lg:inline">Download</span>
              </button>
            )}

            {/* Toggle Fullscreen */}
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="p-2 hover:bg-slate-100 rounded-xl transition-all text-slate-400 hover:text-slate-900 hidden sm:flex cursor-pointer"
              title={isFullscreen ? 'Exit full screen' : 'Full screen'}
            >
              {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
            </button>

            {/* Close Button */}
            <button
              id="modal-btn-close"
              data-testid="modal-close-btn"
              type="button"
              onClick={onClose}
              className="p-2 hover:bg-slate-100 text-slate-400 hover:text-slate-900 rounded-xl transition-all cursor-pointer"
              title="Close preview"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* MODAL BODY */}
        <div className="flex-1 overflow-hidden p-3 sm:p-5 bg-slate-100/50 flex flex-col">
          {activeTab === 'document' ? (
            /* DOCUMENT VIEW */
            <div className="w-full h-full flex flex-col bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden relative">
              {isPdf && resolvedUrl ? (
                /* PDF VIEWER */
                <iframe
                  id="resume-pdf-iframe"
                  src={`${resolvedUrl}#toolbar=1&navpanes=0&scrollbar=1&view=FitH`}
                  className="w-full h-full rounded-2xl bg-slate-50"
                  title={`Resume Document - ${effectiveFileName}`}
                />
              ) : isTxt ? (
                /* TXT VIEWER */
                <div className="w-full h-full flex flex-col overflow-hidden">
                  <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-500 font-semibold">
                    <span className="flex items-center gap-1.5">
                      <AlignLeft size={14} className="text-[#D10043]" />
                      Plain Text Document Reader
                    </span>
                    <span className="font-mono text-[11px]">
                      {textContent ? `${textContent.split('\n').length} lines • ${textContent.split(/\s+/).filter(Boolean).length} words` : 'Empty document'}
                    </span>
                  </div>
                  <div className="flex-1 p-6 sm:p-8 overflow-y-auto custom-scrollbar font-mono text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap select-text bg-white">
                    {textContent || (
                      <div className="text-slate-400 italic text-center py-12">
                        No plain text content could be read from this file.
                      </div>
                    )}
                  </div>
                </div>
              ) : isDocx ? (
                /* DOCX / WORD VIEWER */
                <div className="w-full h-full flex flex-col overflow-hidden">
                  <div className="p-4 bg-gradient-to-r from-blue-50/80 via-white to-blue-50/50 border-b border-blue-100/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-blue-600 text-white flex items-center justify-center font-black text-sm shadow-xs">
                        W
                      </div>
                      <div>
                        <h4 className="text-sm font-black text-slate-900">
                          Microsoft Word Document ({ext.toUpperCase()})
                        </h4>
                        <p className="text-xs text-slate-500 font-medium">
                          Parsed ATS content rendered below. You can also inspect or download the original file.
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {resolvedUrl && (
                        <a
                          href={`https://docs.google.com/viewer?url=${encodeURIComponent(resolvedUrl)}&embedded=true`}
                          target="_blank"
                          rel="noreferrer"
                          className="px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 text-xs font-bold flex items-center gap-1.5 transition-colors"
                        >
                          <ExternalLink size={13} />
                          <span>Google Viewer</span>
                        </a>
                      )}
                      {resolvedUrl && (
                        <button
                          type="button"
                          onClick={handleDownload}
                          className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center gap-1.5 transition-colors shadow-2xs"
                        >
                          <Download size={13} />
                          <span>Download Word Doc</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Render Extracted Text from DOCX */}
                  <div className="flex-1 p-6 sm:p-8 overflow-y-auto custom-scrollbar bg-slate-50/50 space-y-6">
                    {extractedData && (
                      <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs space-y-4">
                        <span className="text-[10px] font-black uppercase tracking-wider text-[#D10043] block">
                          Parsed Profile Credentials
                        </span>
                        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                          <div className="p-3 bg-slate-50 rounded-xl">
                            <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Name</span>
                            <span className="text-xs font-bold text-slate-900">{extractedData.fullname || 'Not detected'}</span>
                          </div>
                          <div className="p-3 bg-slate-50 rounded-xl">
                            <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Email</span>
                            <span className="text-xs font-bold text-slate-900">{extractedData.email || 'Not detected'}</span>
                          </div>
                          <div className="p-3 bg-slate-50 rounded-xl">
                            <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Role</span>
                            <span className="text-xs font-bold text-slate-900">{extractedData.job_title || 'Not detected'}</span>
                          </div>
                          <div className="p-3 bg-slate-50 rounded-xl">
                            <span className="text-[10px] text-slate-400 font-bold uppercase block mb-0.5">Education</span>
                            <span className="text-xs font-bold text-slate-900">{extractedData.highest_degree || extractedData.degree || 'Not detected'}</span>
                          </div>
                        </div>
                      </div>
                    )}

                    <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-2xs">
                      <span className="text-[10px] font-black uppercase tracking-wider text-slate-400 block mb-3">
                        Extracted Document Body
                      </span>
                      <pre className="font-mono text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap select-text">
                        {textContent || 'Extracting document text...'}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : (
                /* FALLBACK VIEWER */
                <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center bg-white">
                  <div className="w-16 h-16 rounded-2xl bg-rose-50 text-[#D10043] flex items-center justify-center mb-4 border border-rose-100 shadow-xs">
                    <FileText size={32} />
                  </div>
                  <h4 className="text-lg font-black text-slate-900 mb-1">{effectiveFileName}</h4>
                  <p className="text-xs text-slate-500 max-w-md mb-6 leading-relaxed">
                    This file format is ready for submission. You can inspect the extracted text below or replace this resume with another document.
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    {onReplaceFile && (
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="px-4 py-2.5 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer shadow-sm"
                      >
                        <FileUp size={15} />
                        <span>Upload Different File</span>
                      </button>
                    )}
                    {resolvedUrl && (
                      <button
                        type="button"
                        onClick={handleDownload}
                        className="px-4 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 font-bold text-xs uppercase tracking-wider flex items-center gap-2 transition-all cursor-pointer"
                      >
                        <Download size={15} />
                        <span>Download Document</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* EXTRACTED ATS TEXT VIEW */
            <div className="w-full h-full flex flex-col bg-white rounded-2xl border border-slate-200/80 shadow-xs overflow-hidden">
              <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs text-slate-500 font-semibold">
                <span className="flex items-center gap-1.5 text-[#D10043]">
                  <Sparkles size={14} />
                  Parsed Resume Content (ATS Representation)
                </span>
                <span className="text-[11px] text-slate-400">
                  Data processed by DeepSeek / Groq & Natural Language Engine
                </span>
              </div>
              <div className="flex-1 p-6 sm:p-8 overflow-y-auto custom-scrollbar font-mono text-xs sm:text-sm text-slate-800 leading-relaxed whitespace-pre-wrap select-text">
                {textContent || (extractedData ? JSON.stringify(extractedData, null, 2) : 'No extracted text available.')}
              </div>
            </div>
          )}
        </div>

        {/* MODAL FOOTER */}
        <div className="p-4 sm:p-5 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 bg-white shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium text-center sm:text-left">
            <CheckCircle2 size={16} className="text-emerald-500 shrink-0 hidden sm:inline" />
            <span>
              Review your resume to ensure all details and formatting are accurate before submitting.
            </span>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto justify-end">
            {hasReplace && (
              <button
                id="modal-footer-replace"
                data-testid="modal-footer-replace-btn"
                type="button"
                onClick={handleTriggerReplace}
                className="flex-1 sm:flex-none px-5 py-2.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 hover:border-slate-300 text-slate-700 font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-95 cursor-pointer"
              >
                <FileUp size={15} />
                <span>Replace Resume</span>
              </button>
            )}

            <button
              id="modal-footer-close"
              data-testid="modal-footer-close-btn"
              type="button"
              onClick={onClose}
              className="flex-1 sm:flex-none px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-[#D10043] text-white font-bold text-xs uppercase tracking-wider transition-all active:scale-95 cursor-pointer shadow-md shadow-slate-900/10"
            >
              Close Preview
            </button>
          </div>
        </div>

        {/* Hidden File Input for Replace functionality */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          onChange={handleFileChange}
          className="hidden"
        />
      </div>
    </div>
  );
};

export default ResumePreviewModal;
