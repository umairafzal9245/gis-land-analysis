import React, { useState } from 'react';
import { 
  ChevronUp, ChevronDown, MapPin, Ruler, Building2, Trees, 
  GraduationCap, Landmark, Church, HelpCircle, FileText,
  Users, Store, Construction, CheckCircle
} from 'lucide-react';
import AnalysisPanel from './AnalysisPanel';

const CATEGORY_COLORS = {
  Residential:  { color: '#10b981', icon: MapPin },
  Commercial:   { color: '#f59e0b', icon: Building2 },
  Religious:    { color: '#3b82f6', icon: Church },
  Educational:  { color: '#8b5cf6', icon: GraduationCap },
  Health:       { color: '#ec4899', icon: HelpCircle },
  Municipal:    { color: '#ef4444', icon: Landmark },
  Recreational: { color: '#22c55e', icon: Trees },
  Utilities:    { color: '#6366f1', icon: MapPin },
  Special:      { color: '#a855f7', icon: Landmark },
  Unknown:      { color: '#6b7280', icon: HelpCircle },
};

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
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'analysis'

  if (!selectionSummary) return null;

  const {
    total_parcels = 0,
    total_area_m2 = 0,
    category_breakdown = {},
    total_religious_capacity = 0,
    vacant_count = 0,
    developed_count = 0,
  } = selectionSummary;

  const categories = Object.entries(category_breakdown).sort((a, b) => b[1] - a[1]);
  
  // Calculate stats
  const religiousCount = category_breakdown['Religious'] || 0;
  const recreationalCount = category_breakdown['Recreational'] || 0;
  const educationalCount = category_breakdown['Educational'] || 0;
  const municipalCount = category_breakdown['Municipal'] || 0;
  const commercialCount = category_breakdown['Commercial'] || 0;
  const nonCommercialCount = total_parcels - commercialCount;
  const commercialPercent = total_parcels > 0 ? ((commercialCount / total_parcels) * 100).toFixed(0) : 0;
  
  // Estimate commercial capacity (at 120 m² per shop)
  const commercialArea = selectionSummary.commercial_total_area_m2 || 0;
  const estimatedShops = Math.floor(commercialArea / 120);

  return (
    <div
      style={{
        ...styles.container,
        height: isExpanded ? 'var(--bottom-panel-height)' : 'var(--bottom-handle-height)',
      }}
    >
      {/* Handle Bar */}
      <div style={styles.handleBar} onClick={onToggle}>
        <div style={styles.handleLine} />
        <div style={styles.handleContent}>
          <span style={styles.handleTitle}>Selection Summary</span>
          {isExpanded ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
        </div>
      </div>

      {/* Panel Content */}
      {isExpanded && (
        <div style={styles.content}>
          {/* Tab Bar */}
          <div style={styles.tabBar}>
            <button
              style={{
                ...styles.tab,
                ...(activeTab === 'summary' ? styles.tabActive : {}),
              }}
              onClick={() => setActiveTab('summary')}
            >
              Summary
            </button>
            <button
              style={{
                ...styles.tab,
                ...(activeTab === 'analysis' ? styles.tabActive : {}),
              }}
              onClick={() => setActiveTab('analysis')}
            >
              Block Analysis
            </button>
          </div>

          {activeTab === 'summary' ? (
            <>
              {/* Three Column Stats */}
              <div style={styles.statsGrid}>
                {/* Column 1 - Selection Overview */}
                <div style={styles.statsColumn}>
                  <h4 style={styles.columnTitle}>Selection Overview</h4>
                  <div style={styles.statCard}>
                    <div style={styles.statValue}>{total_parcels.toLocaleString()}</div>
                    <div style={styles.statLabel}>Total Parcels</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={styles.statValueSmall}>{total_area_m2.toLocaleString()}</div>
                    <div style={styles.statLabel}>Total Area (m²)</div>
                  </div>
                  <div style={styles.splitBar}>
                    <div style={styles.splitLabel}>
                      <span>Commercial</span>
                      <span>{commercialPercent}%</span>
                    </div>
                    <div style={styles.splitBarTrack}>
                      <div 
                        style={{
                          ...styles.splitBarFill,
                          width: `${commercialPercent}%`,
                        }}
                      />
                    </div>
                    <div style={styles.splitLabel}>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        {commercialCount} commercial / {nonCommercialCount} other
                      </span>
                    </div>
                  </div>
                </div>

                {/* Column 2 - Facility Breakdown */}
                <div style={styles.statsColumn}>
                  <h4 style={styles.columnTitle}>Facility Breakdown</h4>
                  <div style={styles.facilityGrid}>
                    <div style={styles.facilityItem}>
                      <div style={{ ...styles.facilityIcon, background: '#3b82f6' }}>
                        <Church size={14} color="white" />
                      </div>
                      <div style={styles.facilityInfo}>
                        <span style={styles.facilityCount}>{religiousCount}</span>
                        <span style={styles.facilityLabel}>Religious</span>
                      </div>
                    </div>
                    <div style={styles.facilityItem}>
                      <div style={{ ...styles.facilityIcon, background: '#22c55e' }}>
                        <Trees size={14} color="white" />
                      </div>
                      <div style={styles.facilityInfo}>
                        <span style={styles.facilityCount}>{recreationalCount}</span>
                        <span style={styles.facilityLabel}>Recreational</span>
                      </div>
                    </div>
                    <div style={styles.facilityItem}>
                      <div style={{ ...styles.facilityIcon, background: '#8b5cf6' }}>
                        <GraduationCap size={14} color="white" />
                      </div>
                      <div style={styles.facilityInfo}>
                        <span style={styles.facilityCount}>{educationalCount}</span>
                        <span style={styles.facilityLabel}>Educational</span>
                      </div>
                    </div>
                    <div style={styles.facilityItem}>
                      <div style={{ ...styles.facilityIcon, background: '#ef4444' }}>
                        <Landmark size={14} color="white" />
                      </div>
                      <div style={styles.facilityInfo}>
                        <span style={styles.facilityCount}>{municipalCount}</span>
                        <span style={styles.facilityLabel}>Municipal</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Column 3 - Capacity Summary */}
                <div style={styles.statsColumn}>
                  <h4 style={styles.columnTitle}>Capacity Summary</h4>
                  <div style={styles.capacityGrid}>
                    <div style={styles.capacityItem}>
                      <Users size={16} color="var(--accent-blue)" />
                      <div>
                        <div style={styles.capacityValue}>{(total_religious_capacity || 0).toLocaleString()}</div>
                        <div style={styles.capacityLabel}>Religious Capacity</div>
                      </div>
                    </div>
                    <div style={styles.capacityItem}>
                      <Store size={16} color="var(--warning-amber)" />
                      <div>
                        <div style={styles.capacityValue}>{estimatedShops.toLocaleString()}</div>
                        <div style={styles.capacityLabel}>Est. Shops (120m²)</div>
                      </div>
                    </div>
                    <div style={styles.capacityItem}>
                      <Construction size={16} color="var(--text-secondary)" />
                      <div>
                        <div style={styles.capacityValue}>{(vacant_count || 0).toLocaleString()}</div>
                        <div style={styles.capacityLabel}>Vacant Plots</div>
                      </div>
                    </div>
                    <div style={styles.capacityItem}>
                      <CheckCircle size={16} color="var(--success-emerald)" />
                      <div>
                        <div style={styles.capacityValue}>{(developed_count || 0).toLocaleString()}</div>
                        <div style={styles.capacityLabel}>Developed Plots</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Category Pills */}
              <div style={styles.categoryPills}>
                {categories.map(([name, count]) => {
                  const { color } = CATEGORY_COLORS[name] || CATEGORY_COLORS.Unknown;
                  const isActive = activeCategory === name;

                  return (
                    <button
                      key={name}
                      style={{
                        ...styles.pill,
                        ...(isActive ? { ...styles.pillActive, borderColor: color } : {}),
                      }}
                      onClick={() => onCategorySelect(name)}
                    >
                      <span style={{ ...styles.pillDot, background: color }} />
                      <span style={styles.pillName}>{name}</span>
                      <span style={styles.pillCount}>{count}</span>
                    </button>
                  );
                })}
              </div>
            </>
          ) : (
            <AnalysisPanel 
              selectionData={selectionData}
              onZoomToBlock={onZoomToBlock}
              onBlockReport={onBlockReport}
            />
          )}

          {/* Generate Report Button */}
          <button
            style={{
              ...styles.reportButton,
              ...(isGeneratingReport ? styles.reportButtonDisabled : {}),
            }}
            onClick={onGenerateReport}
            disabled={isGeneratingReport}
          >
            <FileText size={18} />
            {isGeneratingReport ? 'Generating...' : 'Generate Report'}
          </button>
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
    background: 'var(--panel-surface)',
    borderTop: '1px solid var(--panel-border)',
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    zIndex: 800,
    transition: 'height var(--transition-normal)',
    overflow: 'hidden',
    boxShadow: 'var(--shadow-xl)',
  },
  handleBar: {
    height: 'var(--bottom-handle-height)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    userSelect: 'none',
    gap: 8,
  },
  handleLine: {
    width: 40,
    height: 4,
    borderRadius: 2,
    background: 'var(--panel-border)',
  },
  handleContent: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'var(--text-secondary)',
  },
  handleTitle: {
    fontSize: '0.85rem',
    fontWeight: 500,
  },
  content: {
    padding: '0 24px 24px',
    overflowY: 'auto',
    height: 'calc(var(--bottom-panel-height) - var(--bottom-handle-height))',
    position: 'relative',
  },
  tabBar: {
    display: 'flex',
    gap: 8,
    marginBottom: 16,
    borderBottom: '1px solid var(--panel-border)',
    paddingBottom: 8,
  },
  tab: {
    padding: '6px 12px',
    borderRadius: 6,
    fontSize: '0.8rem',
    fontWeight: 500,
    color: 'var(--text-secondary)',
    transition: 'all var(--transition-fast)',
  },
  tabActive: {
    background: 'var(--accent-blue)',
    color: 'white',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 20,
    marginBottom: 16,
  },
  statsColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  columnTitle: {
    margin: 0,
    fontSize: '0.75rem',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: 4,
  },
  statCard: {
    padding: '10px 14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 8,
    border: '1px solid var(--panel-border)',
  },
  statValue: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  statValueSmall: {
    fontSize: '1.1rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  statLabel: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
  },
  splitBar: {
    padding: '8px 14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 8,
    border: '1px solid var(--panel-border)',
  },
  splitLabel: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.75rem',
    color: 'var(--text-primary)',
    marginBottom: 4,
  },
  splitBarTrack: {
    height: 6,
    background: 'var(--panel-border)',
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 4,
  },
  splitBarFill: {
    height: '100%',
    background: 'var(--warning-amber)',
    borderRadius: 3,
  },
  facilityGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
  },
  facilityItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 8,
    border: '1px solid var(--panel-border)',
  },
  facilityIcon: {
    width: 28,
    height: 28,
    borderRadius: 6,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  facilityInfo: {
    display: 'flex',
    flexDirection: 'column',
  },
  facilityCount: {
    fontSize: '1rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    lineHeight: 1,
  },
  facilityLabel: {
    fontSize: '0.65rem',
    color: 'var(--text-secondary)',
  },
  capacityGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  capacityItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '6px 10px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 6,
    border: '1px solid var(--panel-border)',
  },
  capacityValue: {
    fontSize: '0.95rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    lineHeight: 1,
  },
  capacityLabel: {
    fontSize: '0.65rem',
    color: 'var(--text-secondary)',
  },
  categoryPills: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  pill: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    borderRadius: 20,
    background: 'var(--bg-deep-navy)',
    border: '1px solid var(--panel-border)',
    color: 'var(--text-primary)',
    fontSize: '0.8rem',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  pillActive: {
    background: 'rgba(59, 130, 246, 0.15)',
    borderWidth: 2,
  },
  pillDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
  },
  pillName: {
    fontWeight: 500,
  },
  pillCount: {
    fontWeight: 600,
    color: 'var(--text-secondary)',
    fontSize: '0.75rem',
  },
  reportButton: {
    position: 'absolute',
    bottom: 16,
    right: 24,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 20px',
    background: 'var(--accent-blue)',
    color: 'white',
    borderRadius: 8,
    fontWeight: 600,
    fontSize: '0.875rem',
    boxShadow: 'var(--shadow-md)',
    transition: 'all var(--transition-fast)',
  },
  reportButtonDisabled: {
    background: 'var(--panel-border)',
    color: 'var(--text-secondary)',
    cursor: 'not-allowed',
  },
};
