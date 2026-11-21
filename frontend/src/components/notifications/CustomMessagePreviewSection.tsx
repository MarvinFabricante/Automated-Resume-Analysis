import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Mail, MessageSquare, RotateCcw } from 'lucide-react';
import { useGetNotificationTemplatesQuery } from '../../redux/api/apiSlice';
import {
  buildInterviewTemplateContext,
  DEFAULT_NOTIFICATION_TEMPLATES,
  renderNotificationTemplate,
} from '../../utils/notificationTemplates';

export interface CustomMessageValues {
  customEmailSubject: string;
  customEmailMessage: string;
  customSmsMessage: string;
  isCustomized: boolean;
}

interface CustomMessagePreviewSectionProps {
  templateKey: 'interview_scheduled' | 'interview_rescheduled' | 'interview_canceled';
  candidateName?: string;
  candidateEmail?: string;
  jobTitle?: string;
  interviewTitle?: string;
  startTime?: string | Date;
  endTime?: string | Date;
  interviewerName?: string;
  interviewerEmail?: string;
  location?: string;
  meetingLink?: string;
  notes?: string;
  reason?: string;
  defaultExpanded?: boolean;
  onChange: (values: CustomMessageValues) => void;
}

const CustomMessagePreviewSection: React.FC<CustomMessagePreviewSectionProps> = ({
  templateKey,
  candidateName,
  candidateEmail,
  jobTitle,
  interviewTitle,
  startTime,
  endTime,
  interviewerName,
  interviewerEmail,
  location,
  meetingLink,
  notes,
  reason,
  defaultExpanded = false,
  onChange,
}) => {
  const { data: savedTemplates } = useGetNotificationTemplatesQuery();
  const [isExpanded, setIsExpanded] = useState<boolean>(defaultExpanded);
  const [isCustomized, setIsCustomized] = useState<boolean>(false);

  const templateDef = useMemo(() => {
    const def = DEFAULT_NOTIFICATION_TEMPLATES[templateKey];
    const saved = savedTemplates?.[templateKey];
    return {
      ...def,
      ...(saved || {}),
    };
  }, [savedTemplates, templateKey]);

  const renderedDefaults = useMemo(() => {
    const ctx = buildInterviewTemplateContext({
      candidateName,
      candidateEmail,
      jobTitle,
      interviewTitle,
      startTime,
      endTime,
      interviewerName,
      interviewerEmail,
      location,
      meetingLink,
      notes,
      reason,
    });
    return {
      subject: renderNotificationTemplate(templateDef.email_subject, ctx),
      email: renderNotificationTemplate(templateDef.email_message, ctx),
      sms: renderNotificationTemplate(templateDef.sms_message, ctx),
    };
  }, [
    templateDef,
    candidateName,
    candidateEmail,
    jobTitle,
    interviewTitle,
    startTime,
    endTime,
    interviewerName,
    interviewerEmail,
    location,
    meetingLink,
    notes,
    reason,
  ]);

  const [subject, setSubject] = useState<string>(renderedDefaults.subject);
  const [emailBody, setEmailBody] = useState<string>(renderedDefaults.email);
  const [smsBody, setSmsBody] = useState<string>(renderedDefaults.sms);

  useEffect(() => {
    if (!isCustomized) {
      setSubject(renderedDefaults.subject);
      setEmailBody(renderedDefaults.email);
      setSmsBody(renderedDefaults.sms);
      onChange({
        customEmailSubject: '',
        customEmailMessage: '',
        customSmsMessage: '',
        isCustomized: false,
      });
    }
  }, [renderedDefaults, isCustomized, onChange]);

  const handleEdit = (field: 'subject' | 'email' | 'sms', value: string) => {
    const nextSubject = field === 'subject' ? value : subject;
    const nextEmail = field === 'email' ? value : emailBody;
    const nextSms = field === 'sms' ? value : smsBody;

    if (field === 'subject') setSubject(value);
    if (field === 'email') setEmailBody(value);
    if (field === 'sms') setSmsBody(value);

    setIsCustomized(true);
    onChange({
      customEmailSubject: nextSubject,
      customEmailMessage: nextEmail,
      customSmsMessage: nextSms,
      isCustomized: true,
    });
  };

  const handleReset = () => {
    setIsCustomized(false);
    setSubject(renderedDefaults.subject);
    setEmailBody(renderedDefaults.email);
    setSmsBody(renderedDefaults.sms);
    onChange({
      customEmailSubject: '',
      customEmailMessage: '',
      customSmsMessage: '',
      isCustomized: false,
    });
  };

  return (
    <div className="border border-gray-200 rounded-2xl bg-gray-50/60 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-100/70 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-rose-50 text-[#D60041] flex items-center justify-center shrink-0">
            <MessageSquare size={14} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-black text-gray-800 flex items-center gap-2">
              <span>Editable Email & SMS Notification Message</span>
              {isCustomized && (
                <span className="px-2 py-0.5 rounded-full text-[9px] font-black uppercase bg-amber-100 text-amber-800 border border-amber-200">
                  Customized
                </span>
              )}
            </p>
            <p className="text-[10px] text-gray-500 truncate">
              Pre-filled with schedule details; click to review or edit before sending
            </p>
          </div>
        </div>
        {isExpanded ? (
          <ChevronUp size={16} className="text-gray-400 shrink-0" />
        ) : (
          <ChevronDown size={16} className="text-gray-400 shrink-0" />
        )}
      </button>

      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200/80 space-y-3 bg-white">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
              Message Content Preview & Override
            </span>
            {isCustomized && (
              <button
                type="button"
                onClick={handleReset}
                className="inline-flex items-center gap-1 text-[10px] font-bold text-[#D60041] hover:underline cursor-pointer"
              >
                <RotateCcw size={10} />
                Reset to Template
              </button>
            )}
          </div>

          <div>
            <label className="flex items-center gap-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
              <Mail size={11} className="text-[#D60041]" /> Email Subject
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => handleEdit('subject', e.target.value)}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-semibold text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041]"
            />
          </div>

          <div>
            <label className="flex items-center gap-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
              <Mail size={11} className="text-[#D60041]" /> Email Message
            </label>
            <textarea
              rows={2}
              value={emailBody}
              onChange={(e) => handleEdit('email', e.target.value)}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-[#D60041]/20 focus:border-[#D60041] resize-y"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="flex items-center gap-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                <MessageSquare size={11} className="text-indigo-600" /> SMS Message
              </label>
              <span className="text-[10px] font-semibold text-gray-400">
                {smsBody.length} chars
              </span>
            </div>
            <textarea
              rows={3}
              value={smsBody}
              onChange={(e) => handleEdit('sms', e.target.value)}
              className="w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-xs font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 resize-y"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomMessagePreviewSection;
