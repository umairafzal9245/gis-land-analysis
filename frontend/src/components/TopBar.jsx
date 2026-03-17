import React, { useState } from 'react';
import { Layers, FileText, Loader2, Download } from 'lucide-react';
import { exportShapefile } from '../api/client';

export default function TopBar({ selectionSummary, onGenerateReport, isGeneratingReport, selectedObjectIds }) {
  const parcelCount = selectionSummary?.total_parcels || 0;
  const [exporting, setExporting] = useState(false);

  const handleExportShapefile = async () => {
    if (!selectedObjectIds?.length || exporting) return;
    setExporting(true);
    try {
      const blob = await exportShapefile(selectedObjectIds);
      const url = window.URL.createObjectURL(blob instanceof Blob ? blob : new Blob([blob], { type: 'application/zip' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `parcels_export_${Date.now()}.zip`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export shapefile', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={styles.wrapper}>
      <header style={styles.capsule}>
        {/* Brand */}
        <div style={styles.brand}>
          <div style={styles.logoIcon}>
            <Layers size={15} color="white" strokeWidth={2.5} />
          </div>
          <span style={styles.title}>GIS Analysis Platform</span>
        </div>

        <div style={styles.divider} />

        {/* Selection Badge */}
        <div style={{ ...styles.badge, ...(parcelCount > 0 ? styles.badgeActive : {}) }}>
          {parcelCount > 0 ? (
            <>
              <span style={styles.badgePulse} />
              <span style={styles.badgeCount}>{parcelCount.toLocaleString()}</span>
              <span style={styles.badgeText}>parcels selected</span>
            </>
          ) : (
            <span style={styles.badgeEmpty}>No Selection</span>
          )}
        </div>

        <div style={styles.divider} />

        {/* Report Button */}
        <button
          style={{
            ...styles.reportBtn,
            ...(parcelCount === 0 || isGeneratingReport ? styles.reportBtnDisabled : {}),
          }}
          onClick={onGenerateReport}
          disabled={parcelCount === 0 || isGeneratingReport}
        >
          {isGeneratingReport ? (
            <>
              <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
              <span>Generating…</span>
            </>
          ) : (
            <>
              <FileText size={13} />
              <span>Report</span>
            </>
          )}
        </button>

        {/* Export Shapefile Button */}
        <button
          style={{
            ...styles.exportBtn,
            ...(parcelCount === 0 || exporting ? styles.reportBtnDisabled : {}),
          }}
          onClick={handleExportShapefile}
          disabled={parcelCount === 0 || exporting}
          title="Export as Shapefile"
        >
          {exporting ? (
            <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
          ) : (
            <Download size={13} />
          )}
          <span>{exporting ? 'Exporting…' : 'Export'}</span>
        </button>
      </header>
    </div>
  );
}

const styles = {
  wrapper: {
    position: 'absolute',
    top: 14,
    left: 0,
    right: 0,
    display: 'flex',
    justifyContent: 'center',
    zIndex: 1000,
    pointerEvents: 'none',
  },
  capsule: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5,
    padding: '6px 6px',
    background: 'var(--glass-bg)',
    backdropFilter: 'blur(28px) saturate(200%)',
    WebkitBackdropFilter: 'blur(28px) saturate(200%)',
    border: '1px solid var(--glass-border)',
    borderRadius: 999,
    boxShadow: 'var(--shadow-topbar)',
    pointerEvents: 'auto',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: 9,
    padding: '0 10px 0 4px',
  },
  logoIcon: {
    width: 30,
    height: 30,
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 2px 10px rgba(59,130,246,0.50)',
    flexShrink: 0,
  },
  title: {
    fontSize: '0.87rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    letterSpacing: '-0.025em',
    whiteSpace: 'nowrap',
  },
  divider: {
    width: 1,
    height: 20,
    background: 'rgba(0,0,0,0.10)',
    flexShrink: 0,
    margin: '0 2px',
  },
  badge: {
    display: 'flex',
    alignItems: 'center',
    gap: 7,
    padding: '5px 14px',
    borderRadius: 999,
    background: 'rgba(0,0,0,0.04)',
    fontSize: '0.81rem',
    transition: 'all var(--transition-fast)',
    whiteSpace: 'nowrap',
    minWidth: 140,
    justifyContent: 'center',
  },
  badgeActive: {
    background: 'rgba(59,130,246,0.08)',
  },
  badgePulse: {
    width: 7,
    height: 7,
    borderRadius: '50%',
    background: '#3b82f6',
    boxShadow: '0 0 0 3px rgba(59,130,246,0.22)',
    flexShrink: 0,
  },
  badgeCount: {
    fontWeight: 700,
    color: '#2563eb',
    fontSize: '0.9rem',
  },
  badgeText: {
    color: 'var(--text-secondary)',
    fontWeight: 500,
  },
  badgeEmpty: {
    color: 'var(--text-tertiary)',
    fontStyle: 'italic',
    fontWeight: 400,
  },
  reportBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 17px',
    borderRadius: 999,
    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
    color: 'white',
    fontSize: '0.81rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    border: 'none',
    boxShadow: '0 2px 10px rgba(59,130,246,0.42)',
    whiteSpace: 'nowrap',
  },
  reportBtnDisabled: {
    background: 'rgba(0,0,0,0.07)',
    color: 'var(--text-tertiary)',
    boxShadow: 'none',
    cursor: 'not-allowed',
  },
  exportBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '8px 17px',
    borderRadius: 999,
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: 'white',
    fontSize: '0.81rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
    border: 'none',
    boxShadow: '0 2px 10px rgba(16,185,129,0.42)',
    whiteSpace: 'nowrap',
  },
  exportBtnDisabled: {
    background: 'rgba(0,0,0,0.07)',
    color: 'var(--text-tertiary)',
    boxShadow: 'none',
    cursor: 'not-allowed',
  },
};
