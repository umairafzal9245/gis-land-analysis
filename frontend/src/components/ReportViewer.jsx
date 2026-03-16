import React, { useState } from 'react';
import { X, Download, FileText, Loader, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react';
import { generatePdfReport } from '../api/client';

const CATEGORY_COLORS = {
  Residential:  '#10b981',
  Commercial:   '#f59e0b',
  Religious:    '#3b82f6',
  Educational:  '#8b5cf6',
  Health:       '#ec4899',
  Municipal:    '#ef4444',
  Recreational: '#22c55e',
  Utilities:    '#6366f1',
  Special:      '#a855f7',
  Unknown:      '#6b7280',
};

export default function ReportViewer({ 
  isOpen, 
  onClose, 
  reportData,
  selectionData,
  isLoading,
  error
}) {
  const [expandedSections, setExpandedSections] = useState({
    overview: true,
    landUse: true,
    capacity: true,
    insights: true,
  });
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  if (!isOpen) return null;

  const toggleSection = (section) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  const handleDownloadPdf = async () => {
    if (!selectionData) return;
    setDownloadingPdf(true);
    try {
      const response = await generatePdfReport(selectionData);
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `land_analysis_report_${Date.now()}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF', err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  // Parse statistics from selection data
  const stats = selectionData ? {
    totalParcels: selectionData.parcels?.length || 0,
    totalArea: selectionData.parcels?.reduce((s, p) => s + (Number(p.AREA_M2) || 0), 0) || 0,
    vacantCount: selectionData.parcels?.filter(p => (p.PARCEL_STATUS_LABEL || p.PARCEL_STATUS_LABEL_EN || '').toLowerCase().includes('vacant')).length || 0,
    categories: {},
  } : null;

  if (stats && selectionData?.parcels) {
    selectionData.parcels.forEach(p => {
      const cat = p.LANDUSE_CATEGORY || 'Unknown';
      stats.categories[cat] = (stats.categories[cat] || 0) + 1;
    });
  }

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerLeft}>
            <FileText size={24} color="var(--accent-blue)" />
            <div>
              <h1 style={styles.title}>Land Analysis Report</h1>
              <span style={styles.subtitle}>AI-Generated Insights</span>
            </div>
          </div>
          <div style={styles.headerActions}>
            <button 
              style={styles.downloadButton}
              onClick={handleDownloadPdf}
              disabled={downloadingPdf || isLoading}
            >
              {downloadingPdf ? (
                <Loader size={16} className="animate-spin" />
              ) : (
                <Download size={16} />
              )}
              Download PDF
            </button>
            <button style={styles.closeButton} onClick={onClose}>
              <X size={22} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div style={styles.content}>
          {isLoading && (
            <div style={styles.loadingState}>
              <Loader size={48} style={{ animation: 'spin 1s linear infinite' }} />
              <p>Generating AI report...</p>
              <span style={styles.loadingHint}>This may take 15-30 seconds</span>
            </div>
          )}

          {error && (
            <div style={styles.errorState}>
              <AlertCircle size={48} color="#ef4444" />
              <p>Failed to generate report</p>
              <span style={styles.errorDetail}>{error}</span>
            </div>
          )}

          {!isLoading && !error && stats && (
            <>
              {/* Statistics Table */}
              <Section 
                title="Selection Overview" 
                expanded={expandedSections.overview}
                onToggle={() => toggleSection('overview')}
              >
                <div style={styles.statsGrid}>
                  <div style={styles.statCard}>
                    <div style={styles.statValue}>{stats.totalParcels.toLocaleString()}</div>
                    <div style={styles.statLabel}>Total Parcels</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={styles.statValue}>{(stats.totalArea / 10000).toFixed(2)}</div>
                    <div style={styles.statLabel}>Total Area (ha)</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={{ ...styles.statValue, color: '#f59e0b' }}>{stats.vacantCount}</div>
                    <div style={styles.statLabel}>Vacant Parcels</div>
                  </div>
                  <div style={styles.statCard}>
                    <div style={{ ...styles.statValue, color: '#10b981' }}>{stats.totalParcels - stats.vacantCount}</div>
                    <div style={styles.statLabel}>Developed</div>
                  </div>
                </div>
              </Section>

              {/* Land Use Categories */}
              <Section 
                title="Land Use Breakdown" 
                expanded={expandedSections.landUse}
                onToggle={() => toggleSection('landUse')}
              >
                <div style={styles.categoryTable}>
                  <div style={styles.categoryHeader}>
                    <span>Category</span>
                    <span>Count</span>
                    <span>Percentage</span>
                  </div>
                  {Object.entries(stats.categories)
                    .sort((a, b) => b[1] - a[1])
                    .map(([cat, count]) => (
                    <div key={cat} style={styles.categoryRow}>
                      <div style={styles.categoryName}>
                        <span 
                          style={{ 
                            ...styles.categoryDot, 
                            background: CATEGORY_COLORS[cat] || '#6b7280' 
                          }} 
                        />
                        {cat}
                      </div>
                      <span style={styles.categoryCount}>{count}</span>
                      <span style={styles.categoryPct}>
                        {((count / stats.totalParcels) * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </Section>

              {/* Capacity Estimates */}
              <Section 
                title="Capacity Estimates" 
                expanded={expandedSections.capacity}
                onToggle={() => toggleSection('capacity')}
              >
                <div style={styles.capacityGrid}>
                  <div style={styles.capacityCard}>
                    <div style={styles.capacityIcon}>🕌</div>
                    <div style={styles.capacityInfo}>
                      <div style={styles.capacityValue}>
                        {Math.floor(
                          selectionData.parcels
                            .filter(p => p.LANDUSE_CATEGORY === 'Religious')
                            .reduce((s, p) => s + (Number(p.AREA_M2) || 0), 0) / 8
                        ).toLocaleString()}
                      </div>
                      <div style={styles.capacityLabel}>Mosque Capacity (worshippers)</div>
                    </div>
                  </div>
                  <div style={styles.capacityCard}>
                    <div style={styles.capacityIcon}>🏪</div>
                    <div style={styles.capacityInfo}>
                      <div style={styles.capacityValue}>
                        {Math.floor(
                          selectionData.parcels
                            .filter(p => p.LANDUSE_CATEGORY === 'Commercial')
                            .reduce((s, p) => s + (Number(p.AREA_M2) || 0), 0) / 120
                        ).toLocaleString()}
                      </div>
                      <div style={styles.capacityLabel}>Shops Estimate (at 120m²)</div>
                    </div>
                  </div>
                </div>
              </Section>

              {/* LLM Report */}
              <Section 
                title="AI Analysis & Insights" 
                expanded={expandedSections.insights}
                onToggle={() => toggleSection('insights')}
              >
                {reportData?.report ? (
                  <div style={styles.reportText}>
                    {reportData.report}
                  </div>
                ) : (
                  <div style={styles.noReport}>
                    <p>No AI insights available for this selection.</p>
                  </div>
                )}
              </Section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Section({ title, expanded, onToggle, children }) {
  return (
    <div style={styles.section}>
      <button style={styles.sectionHeader} onClick={onToggle}>
        <span style={styles.sectionTitle}>{title}</span>
        {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
      </button>
      {expanded && <div style={styles.sectionContent}>{children}</div>}
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.85)',
    zIndex: 2000,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    animation: 'fadeIn 0.2s ease',
  },
  modal: {
    width: '90vw',
    maxWidth: 900,
    height: '90vh',
    maxHeight: 800,
    background: 'var(--panel-surface)',
    borderRadius: 16,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: 'var(--shadow-xl)',
    animation: 'slideUp 0.25s ease',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 24px',
    borderBottom: '1px solid var(--panel-border)',
    background: 'var(--bg-deep-navy)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
  },
  title: {
    margin: 0,
    fontSize: '1.25rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  subtitle: {
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
  },
  headerActions: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
  },
  downloadButton: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 18px',
    borderRadius: 8,
    background: 'var(--accent-blue)',
    color: 'white',
    fontWeight: 600,
    fontSize: '0.85rem',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  closeButton: {
    width: 40,
    height: 40,
    borderRadius: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--panel-border)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '24px',
  },
  loadingState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 16,
    color: 'var(--text-secondary)',
  },
  loadingHint: {
    fontSize: '0.8rem',
    opacity: 0.6,
  },
  errorState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    gap: 12,
    color: 'var(--text-primary)',
  },
  errorDetail: {
    fontSize: '0.85rem',
    color: '#ef4444',
  },
  section: {
    marginBottom: 20,
    background: 'var(--bg-deep-navy)',
    borderRadius: 12,
    border: '1px solid var(--panel-border)',
    overflow: 'hidden',
  },
  sectionHeader: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    background: 'none',
    border: 'none',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    transition: 'background var(--transition-fast)',
  },
  sectionTitle: {
    fontSize: '1rem',
    fontWeight: 600,
  },
  sectionContent: {
    padding: '0 20px 20px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 12,
  },
  statCard: {
    padding: '16px',
    background: 'var(--panel-surface)',
    borderRadius: 10,
    textAlign: 'center',
  },
  statValue: {
    fontSize: '1.75rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    marginBottom: 4,
  },
  statLabel: {
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
  },
  categoryTable: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },
  categoryHeader: {
    display: 'grid',
    gridTemplateColumns: '1fr 80px 80px',
    padding: '10px 14px',
    fontSize: '0.7rem',
    fontWeight: 600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
  },
  categoryRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 80px 80px',
    padding: '12px 14px',
    background: 'var(--panel-surface)',
    borderRadius: 6,
    alignItems: 'center',
  },
  categoryName: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  categoryDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
  },
  categoryCount: {
    fontWeight: 600,
    color: 'var(--text-primary)',
    textAlign: 'center',
  },
  categoryPct: {
    color: 'var(--text-secondary)',
    textAlign: 'right',
  },
  capacityGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 16,
  },
  capacityCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: '20px',
    background: 'var(--panel-surface)',
    borderRadius: 10,
  },
  capacityIcon: {
    fontSize: '2rem',
  },
  capacityInfo: {},
  capacityValue: {
    fontSize: '1.5rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    marginBottom: 2,
  },
  capacityLabel: {
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
  },
  reportText: {
    whiteSpace: 'pre-wrap',
    lineHeight: 1.7,
    fontSize: '0.9rem',
    color: 'var(--text-primary)',
    padding: '16px',
    background: 'var(--panel-surface)',
    borderRadius: 8,
  },
  noReport: {
    textAlign: 'center',
    padding: '40px',
    color: 'var(--text-secondary)',
    fontSize: '0.9rem',
  },
};
