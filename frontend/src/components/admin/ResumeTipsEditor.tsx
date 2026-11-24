import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, Plus, Trash2, Lightbulb } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import {
  DEFAULT_RESUME_TIPS,
  ResumeTipsConfig,
  clearResumeTipsCache,
} from '../common/ResumeTipsPanel';

const ResumeTipsEditor: React.FC = () => {
  const [tips, setTips] = useState<ResumeTipsConfig>(DEFAULT_RESUME_TIPS);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    api
      .get<ResumeTipsConfig>('/system-config/resume-tips')
      .then((res) => {
        if (active && res.data) {
          setTips({
            ...DEFAULT_RESUME_TIPS,
            ...res.data,
            bullets:
              Array.isArray(res.data.bullets) && res.data.bullets.length > 0
                ? res.data.bullets
                : [...DEFAULT_RESUME_TIPS.bullets],
          });
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleBulletChange = (index: number, value: string) => {
    setTips((prev) => {
      const next = [...prev.bullets];
      next[index] = value;
      return { ...prev, bullets: next };
    });
  };

  const handleAddBullet = () => {
    if (tips.bullets.length >= 10) return;
    setTips((prev) => ({ ...prev, bullets: [...prev.bullets, ''] }));
  };

  const handleRemoveBullet = (index: number) => {
    if (tips.bullets.length <= 1) return;
    setTips((prev) => ({
      ...prev,
      bullets: prev.bullets.filter((_, i) => i !== index),
    }));
  };

  const handleSave = async () => {
    const cleanedBullets = tips.bullets.map((b) => b.trim()).filter(Boolean);
    if (cleanedBullets.length === 0) {
      toast.error('Please keep at least one tip bullet.');
      return;
    }
    setSaving(true);
    try {
      const res = await api.put<ResumeTipsConfig>('/system-config/resume-tips', {
        title: tips.title.trim() || DEFAULT_RESUME_TIPS.title,
        tooltip: tips.tooltip.trim() || DEFAULT_RESUME_TIPS.tooltip,
        intro: tips.intro.trim() || DEFAULT_RESUME_TIPS.intro,
        bullets: cleanedBullets,
        honesty_reminder: tips.honesty_reminder.trim() || DEFAULT_RESUME_TIPS.honesty_reminder,
        apply_skills_reminder:
          tips.apply_skills_reminder.trim() || DEFAULT_RESUME_TIPS.apply_skills_reminder,
      });
      if (res.data) setTips(res.data);
      clearResumeTipsCache();
      toast.success('Applicant resume tips saved.');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to save resume tips.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset applicant resume tips back to the system defaults?')) return;
    setResetting(true);
    try {
      const res = await api.post<ResumeTipsConfig>('/system-config/resume-tips/reset');
      setTips(res.data || DEFAULT_RESUME_TIPS);
      clearResumeTipsCache();
      toast.success('Resume tips restored to defaults.');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Failed to reset resume tips.');
    } finally {
      setResetting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-6 text-xs text-slate-400">Loading applicant resume tips...</div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">Panel Heading</label>
          <input
            type="text"
            value={tips.title}
            onChange={(e) => setTips((prev) => ({ ...prev, title: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-900 focus:bg-white focus:border-[#D10043] outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-slate-700 mb-1">One-Line Honesty Reminder</label>
          <input
            type="text"
            value={tips.honesty_reminder}
            onChange={(e) => setTips((prev) => ({ ...prev, honesty_reminder: e.target.value }))}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-900 focus:bg-white focus:border-[#D10043] outline-none"
          />
        </div>
      </div>

      <div>
        <label className="block text-xs font-bold text-slate-700 mb-1">Help Tooltip (?) Text</label>
        <input
          type="text"
          value={tips.tooltip}
          onChange={(e) => setTips((prev) => ({ ...prev, tooltip: e.target.value }))}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-900 focus:bg-white focus:border-[#D10043] outline-none"
        />
      </div>

      <div>
        <label className="block text-xs font-bold text-slate-700 mb-1">Intro Line</label>
        <input
          type="text"
          value={tips.intro}
          onChange={(e) => setTips((prev) => ({ ...prev, intro: e.target.value }))}
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-900 focus:bg-white focus:border-[#D10043] outline-none"
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <label className="block text-xs font-bold text-slate-700">
            Bullet Tips ({tips.bullets.length})
          </label>
          {tips.bullets.length < 10 && (
            <button
              type="button"
              onClick={handleAddBullet}
              className="inline-flex items-center gap-1 text-[11px] font-bold text-[#D10043] hover:underline cursor-pointer"
            >
              <Plus size={12} /> Add bullet
            </button>
          )}
        </div>
        <div className="space-y-2">
          {tips.bullets.map((bullet, idx) => (
            <div key={idx} className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-slate-400 w-5 text-right shrink-0">
                {idx + 1}.
              </span>
              <input
                type="text"
                value={bullet}
                onChange={(e) => handleBulletChange(idx, e.target.value)}
                className="flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-900 focus:bg-white focus:border-[#D10043] outline-none"
              />
              {tips.bullets.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveBullet(idx)}
                  title="Remove bullet"
                  className="p-2 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 cursor-pointer"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-xs font-bold text-slate-700 mb-1">
          Job Apply Page Skills Reminder
        </label>
        <textarea
          rows={2}
          value={tips.apply_skills_reminder}
          onChange={(e) =>
            setTips((prev) => ({ ...prev, apply_skills_reminder: e.target.value }))
          }
          className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-medium text-slate-900 focus:bg-white focus:border-[#D10043] outline-none"
        />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100">
        <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
          <Lightbulb size={13} className="text-amber-500 shrink-0" />
          Keep wording plain and friendly. Do not mention weights, percentages, or the formula.
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={resetting}
            onClick={handleReset}
            className="px-3.5 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-bold inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <RotateCcw size={13} />
            <span>{resetting ? 'Resetting...' : 'Reset Defaults'}</span>
          </button>
          <button
            type="button"
            disabled={saving}
            onClick={handleSave}
            className="px-4 py-2 rounded-xl bg-[#D10043] hover:bg-[#b00038] text-white text-xs font-bold inline-flex items-center gap-1.5 shadow-sm cursor-pointer disabled:opacity-50"
          >
            <Save size={13} />
            <span>{saving ? 'Saving...' : 'Save Tips'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ResumeTipsEditor;
