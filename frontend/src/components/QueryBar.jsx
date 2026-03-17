import React, { useState, useMemo, useCallback } from 'react';
import { ChevronDown, X, Send, Loader, MessageCircle, Filter } from 'lucide-react';
import { queryNaturalLanguage } from '../api/client';

const CAT_COLORS = {
  Residential: '#10b981', Commercial: '#f59e0b', Religious: '#3b82f6',
  Educational: '#8b5cf6', Health: '#ec4899',     Municipal: '#ef4444',
  Recreational:'#22c55e', Utilities: '#6366f1',  Special: '#a855f7',
  Unknown: '#94a3b8',
};

const FILTER_FIELDS = [
  { key: 'SUBTYPE_LABEL_EN', label: 'Subtype' },
  { key: 'DETAIL_LABEL_EN', label: 'Detail' },
  { key: 'PARCEL_STATUS_LABEL', label: 'Status' },
  { key: 'NOOFFLOORS', label: 'Floors', format: v => v != null && v !== '' ? `${Math.floor(Number(v))}` : null },
];

export default function QueryBar({
  selectionSummary,
  activeCategory,
  onCategorySelect,
  selectedObjectIds,
  queriedParcels,
  onDropdownFilter,
}) {
  const [filters, setFilters] = useState({});
  const [openDropdown, setOpenDropdown] = useState(null);
  const [nlQuery, setNlQuery] = useState('');
  const [nlAnswer, setNlAnswer] = useState('');
  const [nlLoading, setNlLoading] = useState(false);
  const [showNlInput, setShowNlInput] = useState(false);

  const categories = useMemo(() => {
    if (!selectionSummary?.category_breakdown) return [];
    return Object.entries(selectionSummary.category_breakdown)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count }));
  }, [selectionSummary]);

  // Build unique values for each dropdown from all parcels in the selection
  const allParcels = selectionSummary?.parcels || [];
  const dropdownOptions = useMemo(() => {
    const opts = {};
    for (const field of FILTER_FIELDS) {
      const counts = {};
      for (const p of allParcels) {
        let val = p[field.key];
        if (field.format) val = field.format(val);
        else val = val || null;
        if (val == null || val === '' || val === 'Unknown') continue;
        counts[val] = (counts[val] || 0) + 1;
      }
      opts[field.key] = Object.entries(counts)
        .sort((a, b) => b[1] - a[1])
        .map(([value, count]) => ({ value, count }));
    }
    return opts;
  }, [allParcels]);

  const activeFilterCount = Object.keys(filters).length;

  const handleFilterChange = useCallback((fieldKey, value) => {
    const next = { ...filters };
    if (value === null) {
      delete next[fieldKey];
    } else {
      next[fieldKey] = value;
    }
    setFilters(next);
    setOpenDropdown(null);

    // Notify parent with filtered parcel OBJECTIDs
    if (onDropdownFilter) {
      if (Object.keys(next).length === 0) {
        onDropdownFilter(null); // clear filter
      } else {
        const filtered = allParcels.filter(p => {
          for (const [fk, fv] of Object.entries(next)) {
            const field = FILTER_FIELDS.find(f => f.key === fk);
            let pVal = p[fk];
            if (field?.format) pVal = field.format(pVal);
            else pVal = pVal || '';
            if (String(pVal) !== String(fv)) return false;
          }
          return true;
        });
        onDropdownFilter(filtered);
      }
    }
  }, [filters, allParcels, onDropdownFilter]);

  const clearAllFilters = useCallback(() => {
    setFilters({});
    if (onDropdownFilter) onDropdownFilter(null);
  }, [onDropdownFilter]);

  const handleNlSubmit = async () => {
    if (!nlQuery.trim() || !selectionSummary || nlLoading) return;
    setNlLoading(true);
    setNlAnswer('');
    try {
      const result = await queryNaturalLanguage(nlQuery.trim(), selectionSummary);
      setNlAnswer(result.answer || 'No answer received.');
    } catch (err) {
      setNlAnswer('Failed to get answer. Please try again.');
    } finally {
      setNlLoading(false);
    }
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.capsule}>
        {/* Category filter pills */}
        <div style={styles.pills}>
          {categories.map(({ name, count }) => {
            const color = CAT_COLORS[name] || '#94a3b8';
            const isActive = activeCategory === name;
            return (
              <button
                key={name}
                style={{
                  ...styles.pill,
                  ...(isActive ? { background: `${color}15`, borderColor: color, borderWidth: 1.5 } : {}),
                }}
                onClick={() => onCategorySelect(name)}
              >
                <span style={{ ...styles.dot, background: color }} />
                <span style={styles.pillName}>{name}</span>
                <span style={{ ...styles.pillCount, color: isActive ? color : 'var(--text-tertiary)' }}>{count}</span>
              </button>
            );
          })}
        </div>

        <div style={styles.divider} />

        {/* Dropdown filters */}
        <div style={styles.dropdowns}>
          {FILTER_FIELDS.map(field => {
            const opts = dropdownOptions[field.key] || [];
            if (opts.length === 0) return null;
            const selected = filters[field.key];
            const isOpen = openDropdown === field.key;
            return (
              <div key={field.key} style={styles.dropdownWrap}>
                <button
                  style={{
                    ...styles.dropdownBtn,
                    ...(selected ? styles.dropdownBtnActive : {}),
                  }}
                  onClick={() => setOpenDropdown(isOpen ? null : field.key)}
                >
                  <span style={styles.dropdownLabel}>
                    {selected || field.label}
                  </span>
                  <ChevronDown size={12} style={{
                    color: selected ? '#3b82f6' : 'var(--text-tertiary)',
                    transform: isOpen ? 'rotate(180deg)' : 'none',
                    transition: 'transform 0.2s',
                  }} />
                </button>
                {isOpen && (
                  <div style={styles.dropdownMenu}>
                    {selected && (
                      <button
                        style={{ ...styles.dropdownItem, color: '#ef4444', fontStyle: 'italic' }}
                        onClick={() => handleFilterChange(field.key, null)}
                      >
                        Clear
                      </button>
                    )}
                    {opts.map(({ value, count }) => (
                      <button
                        key={value}
                        style={{
                          ...styles.dropdownItem,
                          ...(selected === value ? styles.dropdownItemActive : {}),
                        }}
                        onClick={() => handleFilterChange(field.key, value)}
                      >
                        <span>{value}</span>
                        <span style={styles.dropdownItemCount}>{count}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          {activeFilterCount > 0 && (
            <button style={styles.clearAllBtn} onClick={clearAllFilters} title="Clear all filters">
              <X size={12} />
              <span>{activeFilterCount}</span>
            </button>
          )}
        </div>

        <div style={styles.divider} />

        {/* NL query toggle */}
        <button
          style={{
            ...styles.nlToggle,
            ...(showNlInput ? { background: 'rgba(59,130,246,0.12)', borderColor: '#3b82f6' } : {}),
          }}
          onClick={() => { setShowNlInput(!showNlInput); setNlAnswer(''); }}
          title="Ask AI a question"
        >
          <MessageCircle size={14} style={{ color: showNlInput ? '#3b82f6' : 'var(--text-tertiary)' }} />
        </button>
      </div>

      {/* NL query input row */}
      {showNlInput && (
        <div style={styles.nlRow}>
          <div style={styles.nlInputBox}>
            <MessageCircle size={14} style={{ color: '#3b82f6', flexShrink: 0 }} />
            <input
              type="text"
              value={nlQuery}
              onChange={e => setNlQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleNlSubmit()}
              placeholder="Ask about this area… e.g. How many mosques are here?"
              style={styles.nlInput}
              disabled={nlLoading}
            />
            <button
              style={{
                ...styles.nlSendBtn,
                opacity: nlQuery.trim() && !nlLoading ? 1 : 0.4,
              }}
              onClick={handleNlSubmit}
              disabled={!nlQuery.trim() || nlLoading}
            >
              {nlLoading ? <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={14} />}
            </button>
          </div>
          {nlAnswer && (
            <div style={styles.nlAnswer}>
              <span style={styles.nlAnswerLabel}>AI Answer</span>
              <p style={styles.nlAnswerText}>{nlAnswer}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    position: 'absolute',
    top: 'calc(var(--topbar-height) + 16px)',
    left: '50%',
    transform: 'translateX(-50%)',
    zIndex: 950,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 6,
  },
  capsule: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    padding: '7px 10px',
    background: 'var(--glass-bg)',
    backdropFilter: 'blur(24px) saturate(200%)',
    WebkitBackdropFilter: 'blur(24px) saturate(200%)',
    border: '1px solid var(--glass-border)',
    borderRadius: 999,
    boxShadow: 'var(--shadow-lg)',
    maxWidth: '90vw',
    flexWrap: 'nowrap',
    overflow: 'visible',
  },
  pills: {
    display: 'flex',
    gap: 5,
    overflowX: 'auto',
    flexShrink: 1,
    minWidth: 0,
  },
  pill: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '5px 11px',
    borderRadius: 999,
    background: 'rgba(0,0,0,0.04)',
    border: '1px solid transparent',
    color: 'var(--text-primary)',
    fontSize: '0.78rem',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    whiteSpace: 'nowrap',
    flexShrink: 0,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: '50%',
    flexShrink: 0,
  },
  pillName: {
    fontWeight: 500,
    color: 'var(--text-secondary)',
  },
  pillCount: {
    fontWeight: 700,
    fontSize: '0.72rem',
  },
  divider: {
    width: 1,
    height: 20,
    background: 'rgba(0,0,0,0.09)',
    flexShrink: 0,
  },
  dropdowns: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    flexShrink: 0,
  },
  dropdownWrap: {
    position: 'relative',
  },
  dropdownBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '5px 10px',
    borderRadius: 999,
    background: 'rgba(0,0,0,0.04)',
    border: '1px solid rgba(0,0,0,0.06)',
    fontSize: '0.76rem',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    maxWidth: 130,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  dropdownBtnActive: {
    background: 'rgba(59,130,246,0.08)',
    borderColor: 'rgba(59,130,246,0.3)',
    color: '#3b82f6',
    fontWeight: 600,
  },
  dropdownMenu: {
    position: 'absolute',
    top: 'calc(100% + 6px)',
    left: 0,
    minWidth: 180,
    maxHeight: 260,
    overflowY: 'auto',
    background: 'var(--glass-bg-dense, rgba(255,255,255,0.92))',
    backdropFilter: 'blur(24px) saturate(200%)',
    WebkitBackdropFilter: 'blur(24px) saturate(200%)',
    border: '1px solid var(--glass-border)',
    borderRadius: 14,
    boxShadow: 'var(--shadow-lg)',
    padding: 4,
    zIndex: 1000,
  },
  dropdownItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    padding: '7px 12px',
    border: 'none',
    background: 'transparent',
    fontSize: '0.78rem',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    borderRadius: 10,
    textAlign: 'left',
    gap: 8,
    transition: 'background 0.15s',
  },
  dropdownItemActive: {
    background: 'rgba(59,130,246,0.1)',
    color: '#3b82f6',
    fontWeight: 600,
  },
  dropdownItemCount: {
    fontSize: '0.7rem',
    fontWeight: 700,
    color: 'var(--text-tertiary)',
    flexShrink: 0,
  },
  clearAllBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 3,
    padding: '4px 8px',
    borderRadius: 999,
    background: 'rgba(239,68,68,0.08)',
    border: '1px solid rgba(239,68,68,0.2)',
    color: '#ef4444',
    fontSize: '0.7rem',
    fontWeight: 700,
    cursor: 'pointer',
    flexShrink: 0,
  },
  nlToggle: {
    width: 30,
    height: 30,
    borderRadius: 999,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'rgba(0,0,0,0.04)',
    border: '1px solid transparent',
    cursor: 'pointer',
    flexShrink: 0,
    transition: 'all var(--transition-fast)',
  },
  nlRow: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    width: '100%',
    maxWidth: 560,
  },
  nlInputBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 12px',
    background: 'var(--glass-bg)',
    backdropFilter: 'blur(20px) saturate(180%)',
    WebkitBackdropFilter: 'blur(20px) saturate(180%)',
    border: '1px solid var(--glass-border)',
    borderRadius: 16,
    boxShadow: 'var(--shadow-glass)',
  },
  nlInput: {
    flex: 1,
    fontSize: '0.82rem',
    color: 'var(--text-primary)',
    background: 'transparent',
    border: 'none',
    outline: 'none',
    minWidth: 0,
  },
  nlSendBtn: {
    width: 30,
    height: 30,
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
    border: 'none',
    color: 'white',
    cursor: 'pointer',
    flexShrink: 0,
    transition: 'opacity var(--transition-fast)',
  },
  nlAnswer: {
    padding: '10px 14px',
    background: 'var(--glass-bg-dense)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    border: '1px solid var(--glass-border)',
    borderRadius: 14,
    boxShadow: 'var(--shadow-glass)',
  },
  nlAnswerLabel: {
    fontSize: '0.68rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: '#3b82f6',
    marginBottom: 4,
    display: 'block',
  },
  nlAnswerText: {
    fontSize: '0.82rem',
    color: 'var(--text-primary)',
    lineHeight: 1.5,
    margin: 0,
    whiteSpace: 'pre-wrap',
  },
};

