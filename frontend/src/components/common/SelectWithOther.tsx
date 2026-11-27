'use client';

import React, { useMemo, useState } from 'react';
import { ChevronDown, Plus, X } from 'lucide-react';
import { OptionGroup } from '../../data/formOptions';

const OTHER_SENTINEL = '__OTHER__';

function flattenOptions(options: string[] | OptionGroup[]): string[] {
  if (!options.length) return [];
  if (typeof options[0] === 'string') return options as string[];
  return (options as OptionGroup[]).flatMap((g) => g.options);
}

interface SelectWithOtherProps {
  id?: string;
  name?: string;
  label?: React.ReactNode;
  icon?: React.ReactNode;
  value: string;
  onChange: (value: string) => void;
  options: string[] | OptionGroup[];
  placeholder?: string;
  otherPlaceholder?: string;
  required?: boolean;
  error?: string | null;
  className?: string;
  selectClassName?: string;
  labelClassName?: string;
  allowEmpty?: boolean;
  emptyLabel?: string;
  helperText?: string;
}

/**
 * Reusable Dropdown list (`<select>`) with built-in `"Other (Specify)"` support.
 * Auto-extracted or previously saved values that aren't in the preset list are
 * automatically shown as selectable options so nothing is ever lost.
 */
export const SelectWithOther: React.FC<SelectWithOtherProps> = ({
  id,
  name,
  label,
  icon,
  value,
  onChange,
  options,
  placeholder = 'Select an option...',
  otherPlaceholder = 'Specify custom entry...',
  required = false,
  error = null,
  className = '',
  selectClassName,
  labelClassName,
  allowEmpty = true,
  emptyLabel,
  helperText,
}) => {
  const flatOptions = useMemo(() => flattenOptions(options), [options]);
  const isGrouped = options.length > 0 && typeof options[0] !== 'string';

  const normalizedVal = (value || '').trim();
  const matchesPreset = useMemo(
    () => flatOptions.some((opt) => opt.toLowerCase() === normalizedVal.toLowerCase()),
    [flatOptions, normalizedVal]
  );
  const canonicalPreset = useMemo(() => {
    const found = flatOptions.find((opt) => opt.toLowerCase() === normalizedVal.toLowerCase());
    return found || normalizedVal;
  }, [flatOptions, normalizedVal]);

  const [isCustomMode, setIsCustomMode] = useState<boolean>(false);

  const effectiveSelectValue = isCustomMode
    ? OTHER_SENTINEL
    : normalizedVal
    ? canonicalPreset
    : '';

  const showDynamicCurrentOption =
    !isCustomMode && Boolean(normalizedVal) && !matchesPreset;

  const baseSelectClasses =
    selectClassName ||
    `w-full appearance-none bg-slate-50 border ${
      error ? 'border-red-300 ring-1 ring-red-50' : 'border-slate-200'
    } rounded-2xl py-3 ${icon ? 'pl-12' : 'pl-4'} pr-10 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all cursor-pointer`;

  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={id || name}
          className={
            labelClassName ||
            'block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2'
          }
        >
          {label} {required && <span className="text-[#D10043] ml-1">*</span>}
        </label>
      )}

      <div className="relative group">
        {icon && (
          <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400 group-focus-within:text-[#D10043] transition-colors">
            {icon}
          </div>
        )}
        <select
          id={id || name}
          name={name}
          required={required && !isCustomMode}
          value={effectiveSelectValue}
          onChange={(e) => {
            const next = e.target.value;
            if (next === OTHER_SENTINEL) {
              setIsCustomMode(true);
            } else {
              setIsCustomMode(false);
              onChange(next);
            }
          }}
          className={baseSelectClasses}
        >
          {allowEmpty && <option value="">{emptyLabel || placeholder}</option>}

          {showDynamicCurrentOption && (
            <option value={normalizedVal}>{normalizedVal} (Current)</option>
          )}

          {isGrouped
            ? (options as OptionGroup[]).map((grp) => (
                <optgroup key={grp.group} label={grp.group}>
                  {grp.options.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </optgroup>
              ))
            : (options as string[]).map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}

          <option value={OTHER_SENTINEL}>Other (Specify custom entry)...</option>
        </select>
        <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-slate-400">
          <ChevronDown size={16} />
        </div>
      </div>

      {isCustomMode && (
        <div className="mt-2 flex items-center gap-2">
          <input
            type="text"
            value={value}
            required={required}
            autoFocus
            onChange={(e) => onChange(e.target.value)}
            placeholder={otherPlaceholder}
            className="flex-1 bg-white border border-[#D10043]/40 rounded-xl py-2.5 px-3.5 text-sm text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10"
          />
          <button
            type="button"
            onClick={() => setIsCustomMode(false)}
            className="px-3 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 text-xs font-bold transition-colors cursor-pointer shrink-0"
          >
            Done
          </button>
        </div>
      )}

      {helperText && !error && (
        <p className="mt-1.5 ml-1 text-[11px] text-slate-500">{helperText}</p>
      )}
      {error && (
        <p className="text-[10px] text-red-500 mt-1.5 ml-1 font-bold">{error}</p>
      )}
    </div>
  );
};

interface MultiSelectDropdownProps {
  id?: string;
  label?: React.ReactNode;
  selectedItems: string[];
  onChange: (items: string[]) => void;
  options: string[] | OptionGroup[];
  placeholder?: string;
  otherPlaceholder?: string;
  error?: string | null;
  helperText?: string;
  labelClassName?: string;
  selectClassName?: string;
  chipClassName?: string;
  emptyStateText?: string;
}

/**
 * Multi-select Dropdown tag picker with `"Other (Specify)"` support.
 * Selecting any item from the dropdown immediately adds it as a removable chip.
 */
export const MultiSelectDropdownWithOther: React.FC<MultiSelectDropdownProps> = ({
  id,
  label,
  selectedItems,
  onChange,
  options,
  placeholder = 'Select from dropdown to add...',
  otherPlaceholder = 'Enter custom item and click Add...',
  error = null,
  helperText,
  labelClassName,
  selectClassName,
  chipClassName,
  emptyStateText = 'No items selected yet.',
}) => {
  const [selectedChoice, setSelectedChoice] = useState<string>('');
  const [customEntry, setCustomEntry] = useState<string>('');
  const [showCustomInput, setShowCustomInput] = useState<boolean>(false);

  const isGrouped = options.length > 0 && typeof options[0] !== 'string';
  const selectedLower = useMemo(
    () => new Set(selectedItems.map((s) => s.trim().toLowerCase())),
    [selectedItems]
  );

  const addItem = (raw: string) => {
    const clean = raw.trim();
    if (!clean) return;
    if (!selectedLower.has(clean.toLowerCase())) {
      onChange([...selectedItems, clean]);
    }
  };

  const removeItem = (target: string) => {
    onChange(selectedItems.filter((item) => item !== target));
  };

  const baseSelectClasses =
    selectClassName ||
    `w-full appearance-none bg-slate-50 border ${
      error ? 'border-red-300 ring-1 ring-red-50' : 'border-slate-200'
    } rounded-2xl py-3 pl-4 pr-10 text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10 transition-all cursor-pointer`;

  return (
    <div className="w-full space-y-2.5">
      {label && (
        <label
          htmlFor={id}
          className={
            labelClassName ||
            'block text-xs font-bold text-slate-500 uppercase tracking-wider'
          }
        >
          {label}
        </label>
      )}

      <div className="relative">
        <select
          id={id}
          value={selectedChoice}
          onChange={(e) => {
            const val = e.target.value;
            if (!val) return;
            if (val === OTHER_SENTINEL) {
              setShowCustomInput(true);
              setSelectedChoice('');
              return;
            }
            addItem(val);
            setSelectedChoice('');
          }}
          className={baseSelectClasses}
        >
          <option value="">{placeholder}</option>
          {isGrouped
            ? (options as OptionGroup[]).map((grp) => (
                <optgroup key={grp.group} label={grp.group}>
                  {grp.options.map((opt) => (
                    <option
                      key={opt}
                      value={opt}
                      disabled={selectedLower.has(opt.toLowerCase())}
                    >
                      {opt}
                      {selectedLower.has(opt.toLowerCase()) ? ' ✓' : ''}
                    </option>
                  ))}
                </optgroup>
              ))
            : (options as string[]).map((opt) => (
                <option
                  key={opt}
                  value={opt}
                  disabled={selectedLower.has(opt.toLowerCase())}
                >
                  {opt}
                  {selectedLower.has(opt.toLowerCase()) ? ' ✓' : ''}
                </option>
              ))}
          <option value={OTHER_SENTINEL}>+ Other (Specify custom entry)...</option>
        </select>
        <div className="absolute inset-y-0 right-0 pr-3.5 flex items-center pointer-events-none text-slate-400">
          <ChevronDown size={16} />
        </div>
      </div>

      {showCustomInput && (
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={customEntry}
            autoFocus
            onChange={(e) => setCustomEntry(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                if (customEntry.trim()) {
                  addItem(customEntry);
                  setCustomEntry('');
                  setShowCustomInput(false);
                }
              }
            }}
            placeholder={otherPlaceholder}
            className="flex-1 bg-white border border-[#D10043]/40 rounded-xl py-2.5 px-3.5 text-sm text-slate-900 font-medium focus:outline-none focus:border-[#D10043] focus:ring-4 focus:ring-[#D10043]/10"
          />
          <button
            type="button"
            onClick={() => {
              if (customEntry.trim()) {
                addItem(customEntry);
                setCustomEntry('');
              }
              setShowCustomInput(false);
            }}
            className="px-3.5 py-2.5 rounded-xl bg-[#D10043] hover:bg-slate-900 text-white text-xs font-bold flex items-center gap-1 transition-colors cursor-pointer shrink-0"
          >
            <Plus size={14} />
            <span>Add</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setCustomEntry('');
              setShowCustomInput(false);
            }}
            className="p-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-500 transition-colors cursor-pointer shrink-0"
            aria-label="Cancel custom entry"
          >
            <X size={14} />
          </button>
        </div>
      )}

      <div className="bg-slate-50 border border-slate-100 rounded-2xl p-3.5 overflow-y-auto max-h-[160px]">
        {selectedItems.length === 0 ? (
          <p className="text-slate-400 text-xs font-medium text-center py-2">
            {emptyStateText}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {selectedItems.map((item, idx) => (
              <span
                key={`${item}-${idx}`}
                className={
                  chipClassName ||
                  'inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 text-slate-700 rounded-lg text-xs font-bold shadow-2xs'
                }
              >
                {item}
                <button
                  type="button"
                  onClick={() => removeItem(item)}
                  className="text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full p-0.5 transition-colors cursor-pointer"
                  aria-label={`Remove ${item}`}
                >
                  <X size={13} />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {helperText && !error && (
        <p className="ml-1 text-[11px] text-slate-500">{helperText}</p>
      )}
      {error && (
        <p className="text-[10px] text-red-500 ml-1 font-bold">{error}</p>
      )}
    </div>
  );
};

export default SelectWithOther;
