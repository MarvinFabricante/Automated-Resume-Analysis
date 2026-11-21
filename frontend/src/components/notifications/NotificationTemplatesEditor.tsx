import React, { useEffect, useMemo, useState } from 'react';
import {
  Mail,
  MessageSquare,
  RotateCcw,
  Save,
  Sparkles,
  Eye,
  CheckCircle2,
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  useGetNotificationTemplatesQuery,
  useUpdateNotificationTemplatesMutation,
  useResetNotificationTemplatesMutation,
} from '../../redux/api/apiSlice';
import {
  DEFAULT_NOTIFICATION_TEMPLATES,
  NotificationTemplateItem,
  renderNotificationTemplate,
} from '../../utils/notificationTemplates';

const SAMPLE_CONTEXT: Record<string, string> = {
  candidate_name: 'Juan Dela Cruz',
  candidate_email: 'juan.delacruz@gmail.com',
  job_title: 'Quality Control Engineer',
  interview_title: 'Technical Interview',
  date: 'Tuesday, Nov 24, 2026',
  start_time: '10:00 AM',
  end_time: '11:00 AM',
  time_range: '10:00 AM - 11:00 AM',
  interviewer_name: 'Maria Santos (HR)',
  interviewer_email: 'maria.hr@mariwasa.com',
  location: 'Mariwasa HR Office, Sta. Maria, Bulacan',
  meeting_link: 'https://meet.google.com/abc-defg-hij',
  location_line: ' Venue: Mariwasa HR Office, Sta. Maria, Bulacan | Meeting Link: https://meet.google.com/abc-defg-hij.',
  notes: 'Please bring an updated copy of your resume and portfolio.',
  notes_line: ' Notes: Please bring an updated copy of your resume and portfolio.',
  reason: 'Panelist requested a schedule adjustment.',
  reason_line: ' Reason: Panelist requested a schedule adjustment.',
  email_note: ' Full details sent to juan.delacruz@gmail.com.',
  status: 'Shortlisted',
  company_name: 'Mariwasa Siam Ceramics, Inc.',
};

interface NotificationTemplatesEditorProps {
  compact?: boolean;
}

const NotificationTemplatesEditor: React.FC<NotificationTemplatesEditorProps> = ({ compact = false }) => {
  const { data: serverTemplates, isLoading } = useGetNotificationTemplatesQuery();
  const [updateTemplates, { isLoading: isSaving }] = useUpdateNotificationTemplatesMutation();
  const [resetTemplates, { isLoading: isResetting }] = useResetNotificationTemplatesMutation();

  const [drafts, setDrafts] = useState<Record<string, NotificationTemplateItem>>(
    () => ({ ...DEFAULT_NOTIFICATION_TEMPLATES })
  );
  const [activeKey, setActiveKey] = useState<string>('interview_scheduled');
  const [focusedField, setFocusedField] = useState<'email_subject' | 'email_message' | 'sms_message'>('sms_message');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);

  useEffect(() => {
    if (serverTemplates && Object.keys(serverTemplates).length > 0) {
      const merged: Record<string, NotificationTemplateItem> = {};
      for (const [k, def] of Object.entries(DEFAULT_NOTIFICATION_TEMPLATES)) {
        merged[k] = {
          ...def,
          ...(serverTemplates[k] || {}),
        };
      }
      setDrafts(merged);
      setHasUnsavedChanges(false);
    }
  }, [serverTemplates]);

  const activeTemplate = drafts[activeKey] || DEFAULT_NOTIFICATION_TEMPLATES.interview_scheduled;

  const handleFieldChange = (
    field: 'email_subject' | 'email_message' | 'sms_message',
    value: string
  ) => {
    setDrafts((prev) => ({
      ...prev,
      [activeKey]: {
        ...prev[activeKey],
        [field]: value,
      },
    }));
    setHasUnsavedChanges(true);
  };

  const handleInsertPlaceholder = (placeholder: string) => {
    const token = `{${placeholder}}`;
    if (focusedField === 'sms_message' && !activeTemplate.supports_sms) {
      handleFieldChange('email_message', `${activeTemplate.email_message}${activeTemplate.email_message ? ' ' : ''}${token}`);
      return;
    }
    const current = activeTemplate[focusedField] || '';
    handleFieldChange(focusedField, `${current}${current && !current.endsWith(' ') ? ' ' : ''}${token}`);
  };

  const handleSave = async () => {
    try {
      const payload: Record<string, { email_subject?: string; email_message?: string; sms_message?: string }> = {};
      for (const [k, item] of Object.entries(drafts)) {
        payload[k] = {
          email_subject: item.email_subject,
          email_message: item.email_message,
          sms_message: item.sms_message,
        };
      }
      await updateTemplates(payload).unwrap();
      setHasUnsavedChanges(false);
      toast.success('Email & SMS notification templates saved!');
    } catch (err: any) {
      toast.error(err?.data?.detail || 'Failed to save notification templates.');
    }
  };

  const handleResetCurrent = async () => {
    try {
      await resetTemplates({ template_key: activeKey }).unwrap();
      setHasUnsavedChanges(false);
      toast.success(`Reset "${activeTemplate.label}" template to default.`);
    } catch (err: any) {
      toast.error(err?.data?.detail || 'Failed to reset template.');
    }
  };

  const previewSubject = useMemo(
    () => renderNotificationTemplate(activeTemplate.email_subject, SAMPLE_CONTEXT),
    [activeTemplate.email_subject]
  );
  const previewEmail = useMemo(
    () => renderNotificationTemplate(activeTemplate.email_message, SAMPLE_CONTEXT),
    [activeTemplate.email_message]
  );
  const previewSms = useMemo(
    () => renderNotificationTemplate(activeTemplate.sms_message, SAMPLE_CONTEXT),
    [activeTemplate.sms_message]
  );

  if (isLoading) {
    return (
      <div className="py-12 text-center">
        <div className="w-8 h-8 border-2 border-[#D60041] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs font-semibold text-gray-500">Loading notification templates...</p>
      </div>
    );
  }

  return (
    <div className={`grid grid-cols-1 ${compact ? 'lg:grid-cols-12' : 'lg:grid-cols-12'} gap-5`}>
      {/* Template List Sidebar */}
      <div className="lg:col-span-4 space-y-2">
        <p className="text-[10px] font-black uppercase tracking-wider text-gray-400 px-1 mb-2">
          Select Notification Event
        </p>
        <div className="space-y-1.5">
          {Object.values(drafts).map((item) => {
            const isActive = item.key === activeKey;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => {
                  setActiveKey(item.key);
                  if (!item.supports_sms && focusedField === 'sms_message') {
                    setFocusedField('email_message');
                  }
                }}
                className={`w-full text-left p-3 rounded-2xl border transition-all cursor-pointer ${
                  isActive
                    ? 'bg-rose-50/80 border-[#D60041] shadow-xs'
                    : 'bg-gray-50/60 hover:bg-white border-gray-200/80'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className={`text-xs font-bold ${isActive ? 'text-[#D60041]' : 'text-gray-900'}`}>
                    {item.label}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[9px] font-black uppercase ${
                      item.supports_sms
                        ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                        : 'bg-sky-50 text-sky-700 border border-sky-200'
                    }`}
                  >
                    {item.supports_sms ? 'Email + SMS' : 'Email'}
                  </span>
                </div>
                <p className="text-[11px] text-gray-500 mt-1 line-clamp-2">{item.description}</p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Template Editor + Live Preview */}
      <div className="lg:col-span-8 space-y-5">
        <div className="bg-gray-50/60 border border-gray-200/80 rounded-2xl p-4 sm:p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-gray-200/80">
            <div>
              <h3 className="text-sm font-black text-gray-900">{activeTemplate.label}</h3>
              <p className="text-[11px] text-gray-500">{activeTemplate.description}</p>
            </div>
            <button
              type="button"
              onClick={handleResetCurrent}
              disabled={isResetting}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-gray-100 border border-gray-200 rounded-xl text-[11px] font-bold text-gray-700 transition-colors cursor-pointer disabled:opacity-50"
            >
              <RotateCcw size={12} />
              Reset to Default
            </button>
          </div>

          {/* Clickable Placeholders */}
          <div>
            <p className="text-[10px] font-black uppercase tracking-wider text-gray-500 mb-1.5 flex items-center gap-1">
              <Sparkles size={11} className="text-[#D60041]" />
              Click to Insert Variable into Active Field
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(activeTemplate.placeholders || []).map((ph) => (
                <button
                  key={ph}
                  type="button"
                  onClick={() => handleInsertPlaceholder(ph)}
                  className="px-2 py-0.5 rounded-lg bg-white hover:bg-rose-50 hover:text-[#D60041] hover:border-rose-200 border border-gray-200 text-[10px] font-mono font-bold text-gray-700 transition-colors cursor-pointer"
                >
                  {`{${ph}}`}
                </button>
              ))}
            </div>
          </div>

          {/* Email Subject */}
          <div>
            <label className="flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wider text-gray-700 mb-1.5">
              <Mail size={12} className="text-[#D60041]" />
              Email Subject Template
            </label>
            <input
              type="text"
              value={activeTemplate.email_subject}
              onFocus={() => setFocusedField('email_subject')}
              onChange={(e) => handleFieldChange('email_subject', e.target.value)}
              className="w-full px-3.5 py-2.5 bg-white border border-gray-200 rounded-xl text-xs font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
            />
          </div>

          {/* Email Intro / Body Message */}
          <div>
            <label className="flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wider text-gray-700 mb-1.5">
              <Mail size={12} className="text-[#D60041]" />
              Email Notification Message
            </label>
            <textarea
              rows={3}
              value={activeTemplate.email_message}
              onFocus={() => setFocusedField('email_message')}
              onChange={(e) => handleFieldChange('email_message', e.target.value)}
              className="w-full px-3.5 py-2.5 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] resize-y"
            />
            <p className="text-[10px] text-gray-400 mt-1">
              Structured schedule details (Date, Time Range, Panelist, Venue/Meeting Link, and Notes) are automatically included in the email card below this message.
            </p>
          </div>

          {/* SMS Template */}
          {activeTemplate.supports_sms && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="flex items-center gap-1.5 text-[11px] font-black uppercase tracking-wider text-gray-700">
                  <MessageSquare size={12} className="text-indigo-600" />
                  SMS Notification Template
                </label>
                <span className="text-[10px] font-bold text-gray-400">
                  Rendered sample: {previewSms.length} chars
                </span>
              </div>
              <textarea
                rows={3}
                value={activeTemplate.sms_message}
                onFocus={() => setFocusedField('sms_message')}
                onChange={(e) => handleFieldChange('sms_message', e.target.value)}
                className="w-full px-3.5 py-2.5 bg-white border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-y"
              />
            </div>
          )}
        </div>

        {/* Live Sample Preview */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 sm:p-5 space-y-3">
          <div className="flex items-center gap-2 text-xs font-black text-gray-800 uppercase tracking-wider">
            <Eye size={14} className="text-[#D60041]" />
            Live Sample Preview
          </div>
          <div className="p-3 bg-rose-50/40 border border-rose-100 rounded-xl space-y-1.5">
            <p className="text-[10px] font-black uppercase text-[#D60041]">Email Preview</p>
            <p className="text-xs font-bold text-gray-900">Subject: {previewSubject}</p>
            <p className="text-xs text-gray-700 leading-relaxed whitespace-pre-wrap">{previewEmail}</p>
          </div>
          {activeTemplate.supports_sms && (
            <div className="p-3 bg-indigo-50/40 border border-indigo-100 rounded-xl space-y-1.5">
              <p className="text-[10px] font-black uppercase text-indigo-700">SMS Preview</p>
              <p className="text-xs text-gray-800 leading-relaxed">{previewSms}</p>
            </div>
          )}
        </div>

        {/* Footer Save Bar */}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs font-semibold text-gray-500 flex items-center gap-1.5">
            {hasUnsavedChanges ? (
              <span className="text-amber-600 font-bold">Unsaved template changes</span>
            ) : (
              <>
                <CheckCircle2 size={14} className="text-emerald-600" />
                <span>Templates synchronized</span>
              </>
            )}
          </span>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[#D60041] hover:bg-rose-700 text-white rounded-xl text-xs font-bold shadow-sm transition-all cursor-pointer disabled:opacity-50"
          >
            <Save size={14} />
            {isSaving ? 'Saving...' : 'Save Templates'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationTemplatesEditor;
