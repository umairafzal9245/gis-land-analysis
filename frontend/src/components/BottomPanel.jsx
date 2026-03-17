import React, { useState } from 'react';
import {
  ChevronUp, ChevronDown, Home, Building2, Zap, Users, Store,
  GraduationCap, Landmark, Trees, HelpCircle, Heart, Shield,
  Construction, CheckCircle, BarChart2, Maximize2, TrendingUp, Grid3X3
} from 'lucide-react';
import AnalysisPanel from './AnalysisPanel';

// All 10 categories — always shown, 0 if missing
const ALL_CATEGORIES = [
  { name: 'Residential',  color: '#10b981', icon: Home       },
  { name: 'Special',      color: '#a855f7', icon: Shield      },
  { name: 'Utilities',    color: '#6366f1', icon: Zap         },
  { name: 'Religious',    color: '#3b82f6', icon: Landmark    },
  { name: 'Municipal',    color: '#ef4444', icon: Building2   },
  { name: 'Educational',  color: '#8b5cf6', icon: GraduationCap },
  { name: 'Recreational', color: '#22c55e', icon: Trees       },
  { name: 'Commercial',   color: '#f59e0b', icon: Store       },
  { name: 'Unknown',      color: '#94a3b8', icon: HelpCircle  },
  { name: 'Health',       color: '#ec4899', icon: Heart       },
];

export default function BottomPanel({
  isExpanded,
  onToggle,
  selectionSummary,
  selectionData,
  activeCategory,
  onCategorySelect,
  onGenerateReport,
  isGeneratingReport,
  onZoomToBlock,
  onBlockReport,
}) {
  const [activeTab, setActiveTab] = useState('summary');

  if (!selectionSummary) return null;

  const {
    total_parcels = 0,
    total_area_m2 = 0,
    category_breakdown = {},
    vacant_count = 0,
    developed_count = 0,
    block_ids_covered = [],
  } = selectionSummary;

  const avgParcelSize = total_parcels > 0 ? (total_area_m2 / total_parcels).toFixed(0) : 0;
  const developmentRate = total_parcels > 0 ? ((developed_count / total_parcels) * 100).toFixed(1) : 0;
  const blocksCovered = block_ids_covered.length || 0;
  const activeLandUses = Object.values(category_breakdown).filter(c => c > 0).length;

  const kpiCards = [
    { value: total_parcels.toLocaleString(),                        label: 'Total Parcels',   color: '#3b82f6', bg: 'rgba(59,130,246,0.08)'  },
    { value: (total_area_m2 / 1000).toFixed(1) + 'K',              label: 'Area (m²)',        color: '#6366f1', bg: 'rgba(99,102,241,0.08)'  },
    { value: (vacant_count || 0).toLocaleString(),                  label: 'Vacant Plots',    color: '#d97706', bg: 'rgba(217,119,6,0.08)'   },
    { value: (developed_count || 0).toLocaleString(),               label: 'Developed',       color: '#059669', bg: 'rgba(5,150,105,0.08)'  },
  ];

  const capacityItems = [
    { value: `${Number(avgParcelSize).toLocaleString()} m²`, label: 'Avg. Parcel Size',  icon: Maximize2,   color: '#3b82f6' },
    { value: `${developmentRate}%`,                          label: 'Development Rate',  icon: TrendingUp,  color: '#059669' },
    { value: `${activeLandUses}`,                            label: 'Land Use Types',    icon: BarChart2,   color: '#8b5cf6' },
    { value: blocksCovered.toLocaleString(),                 label: 'Blocks Covered',    icon: Grid3X3,     color: '#d97706' },
  ];

  return (
    <div style={{ ...styles.container, height: isExpanded ? 'var(--bottom-panel-height)' : 'var(--bottom-handle-height)' }}>
      {/* Handle */}
      <div style={styles.handle} onClick={onToggle}>
        <div style={styles.handlePill} />
        <div style={styles.handleRow}>
          <span style={styles.handleLabel}>Selection Summary</span>
          {isExpanded ? <ChevronDown size={16} style={{ color: 'var(--text-tertiary)' }} /> : <ChevronUp size={16} style={{ color: 'var(--text-tertiary)' }} />}
        </div>
      </div>

      {isExpanded && (
        <div style={styles.body}>
          {/* Tabs */}
          <div style={styles.tabs}>
            {['summary', 'analysis'].map(tab => (
              <button
                key={tab}
                style={{ ...styles.tab, ...(activeTab === tab ? styles.tabActive : {}) }}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'summary' ? 'Summary' : 'Block Analysis'}
              </button>
            ))}
          </div>

          {activeTab === 'summary' ? (
            <>
              {/* KPI Row */}
              <div style={styles.kpiRow}>
                {kpiCards.map(({ value, label, color, bg }) => (
                  <div key={label} style={{ ...styles.kpiCard, background: bg }}>
                    <div style={{ ...styles.kpiValue, color }}>{value}</div>
                    <div style={styles.kpiLabel}>{label}</div>
                  </div>
                ))}
              </div>

              {/* Land Use Section */}
              <div style={styles.sectionLabel}>Land Use Breakdown</div>
              <div style={styles.categoryGrid}>
                {ALL_CATEGORIES.map(({ name, color, icon: Icon }) => {
                  const count = category_breakdown[name] || 0;
                  const isActive = activeCategory === name;
                  return (
                    <button
                      key={name}
                      style={{
                        ...styles.catChip,
                        ...(isActive ? { ...styles.catChipActive, borderColor: color, background: `${color}12` } : {}),
                        ...(count === 0 ? styles.catChipEmpty : {}),
                      }}
                      onClick={() => count > 0 && onCategorySelect(name)}
                    >
                      <span style={{ ...styles.catDot, background: color }} />
                      <span style={styles.catName}>{name}</span>
                      <span style={{ ...styles.catCount, color: isActive ? color : count > 0 ? '#0f172a' : 'var(--text-tertiary)', fontWeight: count > 0 ? 700 : 400 }}>
                        {count}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Spatial Insights Row */}
              <div style={styles.sectionLabel}>Spatial Insights</div>
              <div style={styles.capacityRow}>
                {capacityItems.map(({ value, label, icon: Icon, color }) => (
                  <div key={label} style={styles.capItem}>
                    <div style={{ ...styles.capIconBox, background: `${color}14` }}>
                      <Icon size={15} color={color} />
                    </div>
                    <div>
                      <div style={{ ...styles.capValue, color }}>{value}</div>
                      <div style={styles.capLabel}>{label}</div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <AnalysisPanel
              selectionData={selectionData}
              onZoomToBlock={onZoomToBlock}
              onBlockReport={onBlockReport}
            />
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    position: 'absolute',
    bottom: 0,
    left: 'var(--toolbar-width)',
    right: 0,
    background: 'var(--glass-bg-dense)',
    backdropFilter: 'blur(24px) saturate(180%)',
    WebkitBackdropFilter: 'blur(24px) saturate(180%)',
    borderTop: '1px solid var(--glass-border)',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    zIndex: 800,
    transition: 'height var(--transition-normal)',
    overflow: 'hidden',
    boxShadow: '0 -8px 40px rgba(0,0,0,0.10), 0 -2px 8px rgba(0,0,0,0.05)',
  },
  handle: {
    height: 'var(--bottom-handle-height)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    userSelect: 'none',
    gap: 6,
  },
  handlePill: {
    width: 36,
    height: 4,
    borderRadius: 2,
    background: 'rgba(0,0,0,0.12)',
  },
  handleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  handleLabel: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    letterSpacing: '-0.01em',
  },
  body: {
    padding: '0 20px 16px',
    height: 'calc(var(--bottom-panel-height) - var(--bottom-handle-height))',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  tabs: {
    display: 'flex',
    gap: 6,
    paddingBottom: 2,
  },
  tab: {
    padding: '5px 14px',
    borderRadius: 999,
    fontSize: '0.78rem',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    background: 'rgba(0,0,0,0.05)',
    border: '1px solid transparent',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  tabActive: {
    background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
    color: 'white',
    boxShadow: '0 2px 8px rgba(59,130,246,0.35)',
  },

  /* KPI */
  kpiRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 8,
  },
  kpiCard: {
    borderRadius: 12,
    padding: '10px 12px',
    border: '1px solid rgba(0,0,0,0.06)',
  },
  kpiValue: {
    fontSize: '1.3rem',
    fontWeight: 800,
    lineHeight: 1,
    letterSpacing: '-0.03em',
  },
  kpiLabel: {
    fontSize: '0.68rem',
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    marginTop: 3,
    fontWeight: 500,
  },

  /* Section label */
  sectionLabel: {
    fontSize: '0.7rem',
    fontWeight: 700,
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
  },

  /* Category grid — 5 per row × 2 rows */
  categoryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: 6,
  },
  catChip: {
    display: 'flex',
    alignItems: 'center',
    gap: 5,
    padding: '7px 10px',
    borderRadius: 10,
    background: 'rgba(0,0,0,0.04)',
    border: '1px solid transparent',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    textAlign: 'left',
    minWidth: 0,
  },
  catChipActive: {
    border: '1.5px solid',
  },
  catChipEmpty: {
    cursor: 'default',
    opacity: 0.6,
  },
  catDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    flexShrink: 0,
  },
  catName: {
    fontSize: '0.72rem',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    flex: 1,
    minWidth: 0,
  },
  catCount: {
    fontSize: '0.78rem',
    flexShrink: 0,
  },

  /* Capacity row */
  capacityRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 8,
  },
  capItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    background: 'rgba(0,0,0,0.04)',
    borderRadius: 12,
    border: '1px solid rgba(0,0,0,0.05)',
  },
  capIconBox: {
    width: 32,
    height: 32,
    borderRadius: 9,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  capValue: {
    fontSize: '1.05rem',
    fontWeight: 800,
    lineHeight: 1,
    letterSpacing: '-0.02em',
  },
  capLabel: {
    fontSize: '0.65rem',
    color: 'var(--text-tertiary)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    marginTop: 2,
    fontWeight: 500,
  },
};
