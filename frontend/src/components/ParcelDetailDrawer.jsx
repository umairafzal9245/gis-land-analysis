import React, { useState, useMemo } from 'react';
import { 
  X, ArrowLeft, Calculator, Ruler, MapPin, 
  Users, Store, ChevronRight, Building2
} from 'lucide-react';

const CATEGORY_COLORS = {
  Mosque: '#3b82f6',
  Commercial: '#f59e0b',
  Residential: '#10b981',
  Park: '#22c55e',
  Educational: '#8b5cf6',
  Government: '#ef4444',
  Unknown: '#6b7280',
};

export default function ParcelDetailDrawer({
  isOpen,
  onClose,
  mode, // 'query' | 'detail' | 'calculator'
  queriedParcels = [],
  activeCategory,
  selectedParcel,
  onParcelSelect,
  onHighlightParcel,
  onBackToQuery,
}) {
  const [calculatorMode, setCalculatorMode] = useState(null); // 'religious' | 'commercial'
  const [shopSize, setShopSize] = useState(120);

  if (!isOpen) return null;

  const drawerTitle = useMemo(() => {
    if (calculatorMode === 'religious') return 'Religious Facility Capacity Calculator';
    if (calculatorMode === 'commercial') return 'Commercial Plot Capacity';
    if (mode === 'query') return `Query Results: ${activeCategory} (${queriedParcels.length})`;
    if (mode === 'detail') return 'Parcel Detail';
    return 'Parcel Details';
  }, [mode, activeCategory, queriedParcels.length, calculatorMode]);

  const handleParcelClick = (parcel) => {
    onHighlightParcel(parcel.OBJECTID);
  };

  const handleCalculateClick = (parcel) => {
    onParcelSelect(parcel);
    if (parcel.LANDUSE_CATEGORY === 'Religious') {
      setCalculatorMode('religious');
    } else if (parcel.LANDUSE_CATEGORY === 'Commercial') {
      setCalculatorMode('commercial');
    }
  };

  const handleBack = () => {
    if (calculatorMode) {
      setCalculatorMode(null);
    } else if (mode === 'detail' && onBackToQuery) {
      onBackToQuery();
    }
  };

  const showBackButton = calculatorMode || (mode === 'detail' && queriedParcels.length > 0);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          {showBackButton && (
            <button style={styles.backButton} onClick={handleBack}>
              <ArrowLeft size={18} />
            </button>
          )}
          <h2 style={styles.title}>{drawerTitle}</h2>
        </div>
        <button style={styles.closeButton} onClick={onClose}>
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div style={styles.content}>
        {calculatorMode === 'religious' && selectedParcel && (
          <MosqueCalculator parcel={selectedParcel} />
        )}
        
        {calculatorMode === 'commercial' && selectedParcel && (
          <CommercialCalculator 
            parcel={selectedParcel} 
            shopSize={shopSize}
            setShopSize={setShopSize}
          />
        )}
        
        {!calculatorMode && mode === 'query' && (
          <QueryResultsList
            parcels={queriedParcels}
            category={activeCategory}
            onParcelClick={handleParcelClick}
            onCalculateClick={handleCalculateClick}
            onViewDetail={(parcel) => {
              onParcelSelect(parcel);
            }}
          />
        )}
        
        {!calculatorMode && mode === 'detail' && selectedParcel && (
          <ParcelDetail 
            parcel={selectedParcel}
            onCalculate={() => {
              if (selectedParcel.LANDUSE_CATEGORY === 'Religious') {
                setCalculatorMode('religious');
              } else if (selectedParcel.LANDUSE_CATEGORY === 'Commercial') {
                setCalculatorMode('commercial');
              }
            }}
          />
        )}
      </div>
    </div>
  );
}

// Query Results List Component
function QueryResultsList({ parcels, category, onParcelClick, onCalculateClick, onViewDetail }) {
  const categoryColor = CATEGORY_COLORS[category] || CATEGORY_COLORS.Unknown;

  return (
    <div style={styles.queryResults}>
      <div style={styles.resultsSummary}>
        <div style={{ ...styles.categoryDot, background: categoryColor }} />
        <span>{parcels.length} parcels found</span>
      </div>

      <div style={styles.parcelList}>
        {parcels.map((parcel) => {
          const isVacant = (parcel.PARCEL_STATUS_LABEL || parcel.PARCEL_STATUS_LABEL_EN || '').toLowerCase().includes('vacant');
          const canCalculate = parcel.LANDUSE_CATEGORY === 'Religious' || parcel.LANDUSE_CATEGORY === 'Commercial';

          return (
            <div
              key={parcel.OBJECTID}
              style={styles.parcelCard}
              onClick={() => onParcelClick(parcel)}
            >
              <div style={styles.parcelHeader}>
                <span style={styles.parcelLabel}>
                  {parcel.SUBTYPE_LABEL_EN || 'Unnamed'}
                </span>
                <span style={{
                  ...styles.statusBadge,
                  background: isVacant ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                  color: isVacant ? '#f59e0b' : '#10b981',
                }}>
                  {isVacant ? 'Vacant' : 'Developed'}
                </span>
              </div>
              
              {parcel.SUBTYPE_LABEL_AR && (
                <div style={styles.parcelLabelAr}>{parcel.SUBTYPE_LABEL_AR}</div>
              )}
              
              <div style={styles.parcelMeta}>
                <span style={styles.metaItem}>
                  <Ruler size={12} />
                  {Number(parcel.AREA_M2 || 0).toLocaleString()} m²
                </span>
              </div>

              <div style={styles.cardActions}>
                <button 
                  style={styles.viewButton}
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewDetail(parcel);
                  }}
                >
                  View Details
                  <ChevronRight size={14} />
                </button>
                {canCalculate && (
                  <button 
                    style={styles.calculateButton}
                    onClick={(e) => {
                      e.stopPropagation();
                      onCalculateClick(parcel);
                    }}
                  >
                    <Calculator size={14} />
                    Calculate
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Parcel Detail Component
function ParcelDetail({ parcel, onCalculate }) {
  const categoryColor = CATEGORY_COLORS[parcel.LANDUSE_CATEGORY] || CATEGORY_COLORS.Unknown;
  const canCalculate = parcel.LANDUSE_CATEGORY === 'Mosque' || parcel.LANDUSE_CATEGORY === 'Commercial';
  const isVacant = (parcel.PARCEL_STATUS_LABEL || parcel.PARCEL_STATUS_LABEL_EN || '').toLowerCase().includes('vacant');

  const fields = [
    { label: 'Object ID', value: parcel.OBJECTID },
    { label: 'Subtype (EN)', value: parcel.SUBTYPE_LABEL_EN },
    { label: 'Subtype (AR)', value: parcel.SUBTYPE_LABEL_AR },
    { label: 'Category', value: parcel.LANDUSE_CATEGORY, color: categoryColor },
    { label: 'Area (m²)', value: parcel.AREA_M2 ? Number(parcel.AREA_M2).toLocaleString() : 'N/A' },
    { label: 'Status', value: parcel.PARCEL_STATUS_LABEL || parcel.PARCEL_STATUS_LABEL_EN },
    { label: 'Block ID', value: parcel.BLOCK_NO || parcel.BLOCK_ID },
    { label: 'Municipality', value: parcel.MUNICIPALITY_LABEL_EN || parcel.MUNICIPALITY_LABEL_AR },
  ];

  return (
    <div style={styles.parcelDetails}>
      <div style={styles.detailHeader}>
        <div style={{ ...styles.categoryBadge, background: categoryColor }}>
          {parcel.LANDUSE_CATEGORY || 'Unknown'}
        </div>
        <span style={{
          ...styles.statusBadge,
          background: isVacant ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
          color: isVacant ? '#f59e0b' : '#10b981',
        }}>
          {isVacant ? 'Vacant' : 'Developed'}
        </span>
      </div>

      <div style={styles.detailsGrid}>
        {fields.map(({ label, value, color }) => value && (
          <div key={label} style={styles.detailField}>
            <div style={styles.fieldLabel}>{label}</div>
            <div style={{ ...styles.fieldValue, color: color || 'var(--text-primary)' }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {canCalculate && (
        <button style={styles.calculateCapacityButton} onClick={onCalculate}>
          <Calculator size={18} />
          Calculate Capacity
        </button>
      )}
    </div>
  );
}

// Religious Facility Calculator Component
function MosqueCalculator({ parcel }) {
  const area = Number(parcel.AREA_M2) || 0;
  // Use pre-calculated estimate from ETL if available, else derive from area
  const capacity = Number(parcel.CAPACITY_ESTIMATED) > 0
    ? Number(parcel.CAPACITY_ESTIMATED)
    : Math.floor(area / 1);
  const isVacant = (parcel.PARCEL_STATUS_LABEL || parcel.PARCEL_STATUS_LABEL_EN || '').toLowerCase().includes('vacant');

  return (
    <div style={styles.calculator}>
      <div style={styles.calcHeader}>
        <Church size={24} color="#3b82f6" />
        <div>
          <div style={styles.calcLabel}>{parcel.SUBTYPE_LABEL_EN || 'Religious Facility'}</div>
          <div style={styles.calcArea}>{area.toLocaleString()} m²</div>
        </div>
      </div>

      <div style={styles.formulaBox}>
        <div style={styles.formulaTitle}>Capacity Formula</div>
        <div style={styles.formula}>
          <span>{area.toLocaleString()} m²</span>
          <span style={styles.formulaOperator}>÷</span>
          <span>1 m²/worshipper</span>
          <span style={styles.formulaOperator}>=</span>
          <span style={styles.formulaResult}>{capacity.toLocaleString()}</span>
        </div>
      </div>

      <div style={styles.resultBox}>
        <div style={styles.resultValue}>{capacity.toLocaleString()}</div>
        <div style={styles.resultLabel}>estimated worshippers</div>
      </div>

      <div style={styles.calcNote}>
        Based on mosque prayer density of 1 m² per worshipper
      </div>

      <div style={styles.statusNote}>
        <div style={{
          ...styles.statusIndicator,
          background: isVacant ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)',
        }}>
          <span style={{ color: isVacant ? '#f59e0b' : '#10b981', fontWeight: 600 }}>
            {isVacant ? 'Vacant Plot' : 'Developed'}
          </span>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
            {isVacant 
              ? 'Full capacity available for development'
              : 'Existing mosque with current capacity'
            }
          </span>
        </div>
      </div>

      {/* Comparison chart placeholder */}
      <div style={styles.comparisonSection}>
        <div style={styles.comparisonTitle}>Block Comparison</div>
        <div style={styles.comparisonChart}>
          <div style={styles.comparisonBar}>
            <div style={styles.comparisonLabel}>This Mosque</div>
            <div style={styles.barContainer}>
              <div style={{ ...styles.bar, width: '100%', background: '#3b82f6' }} />
            </div>
            <div style={styles.barValue}>{capacity.toLocaleString()}</div>
          </div>
          <div style={styles.comparisonBar}>
            <div style={styles.comparisonLabel}>Block Avg.</div>
            <div style={styles.barContainer}>
              <div style={{ ...styles.bar, width: '60%', background: 'var(--panel-border)' }} />
            </div>
            <div style={styles.barValue}>~{Math.floor(capacity * 0.6).toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Church icon for mosque
function Church({ size, color }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m18 7 4 2v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9l4-2"/>
      <path d="M14 22v-4a2 2 0 0 0-2-2v0a2 2 0 0 0-2 2v4"/>
      <path d="M18 22V5l-6-3-6 3v17"/>
      <path d="M12 7v5"/>
      <path d="M10 9h4"/>
    </svg>
  );
}

// Commercial Calculator Component
function CommercialCalculator({ parcel, shopSize, setShopSize }) {
  const area = Number(parcel.AREA_M2) || 0;
  const estimatedShops = Math.floor(area / shopSize);
  
  // Preset calculations
  const at60 = Math.floor(area / 60);
  const at120 = Math.floor(area / 120);
  const at200 = Math.floor(area / 200);

  return (
    <div style={styles.calculator}>
      <div style={styles.calcHeader}>
        <Building2 size={24} color="#f59e0b" />
        <div>
          <div style={styles.calcLabel}>{parcel.SUBTYPE_LABEL_EN || 'Commercial'}</div>
          <div style={styles.calcArea}>{area.toLocaleString()} m²</div>
        </div>
      </div>

      <div style={styles.inputSection}>
        <label style={styles.inputLabel}>Shop Size (m²)</label>
        <input
          type="number"
          value={shopSize}
          onChange={(e) => setShopSize(Number(e.target.value) || 120)}
          style={styles.shopSizeInput}
          min={20}
          max={500}
        />
        <input
          type="range"
          value={shopSize}
          onChange={(e) => setShopSize(Number(e.target.value))}
          style={styles.slider}
          min={20}
          max={500}
          step={10}
        />
        <div style={styles.sliderLabels}>
          <span>20m² (kiosk)</span>
          <span>500m² (large store)</span>
        </div>
      </div>

      <div style={styles.resultBox}>
        <div style={styles.resultValue}>{estimatedShops.toLocaleString()}</div>
        <div style={styles.resultLabel}>shops estimated</div>
      </div>

      <div style={styles.presetComparisons}>
        <div style={styles.presetTitle}>Quick Comparisons</div>
        <div style={styles.presetGrid}>
          <div style={styles.presetItem} onClick={() => setShopSize(60)}>
            <div style={styles.presetValue}>{at60}</div>
            <div style={styles.presetLabel}>at 60m²</div>
          </div>
          <div style={styles.presetItem} onClick={() => setShopSize(120)}>
            <div style={styles.presetValue}>{at120}</div>
            <div style={styles.presetLabel}>at 120m²</div>
          </div>
          <div style={styles.presetItem} onClick={() => setShopSize(200)}>
            <div style={styles.presetValue}>{at200}</div>
            <div style={styles.presetLabel}>at 200m²</div>
          </div>
        </div>
      </div>

      <div style={styles.calcNote}>
        Adjust shop size to reflect local retail standards or your development brief
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'absolute',
    top: 'var(--topbar-height)',
    right: 0,
    bottom: 0,
    width: 'var(--drawer-width)',
    background: 'var(--panel-surface)',
    borderLeft: '1px solid var(--panel-border)',
    zIndex: 900,
    display: 'flex',
    flexDirection: 'column',
    boxShadow: 'var(--shadow-xl)',
    animation: 'slideInFromRight 0.25s ease',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 16px',
    borderBottom: '1px solid var(--panel-border)',
    background: 'var(--bg-deep-navy)',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  backButton: {
    width: 32,
    height: 32,
    borderRadius: 6,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-secondary)',
    background: 'var(--panel-border)',
    transition: 'all var(--transition-fast)',
  },
  title: {
    margin: 0,
    fontSize: '0.9rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'var(--text-secondary)',
    transition: 'all var(--transition-fast)',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px',
  },

  // Query Results
  queryResults: {},
  resultsSummary: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
    color: 'var(--text-secondary)',
    fontSize: '0.85rem',
  },
  categoryDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
  },
  parcelList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  parcelCard: {
    padding: '12px 14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 10,
    border: '1px solid var(--panel-border)',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  parcelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 4,
  },
  parcelLabel: {
    fontSize: '0.9rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  parcelLabelAr: {
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
    marginBottom: 6,
    direction: 'rtl',
  },
  statusBadge: {
    padding: '2px 8px',
    borderRadius: 4,
    fontSize: '0.7rem',
    fontWeight: 600,
  },
  parcelMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  metaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
  },
  cardActions: {
    display: 'flex',
    gap: 8,
  },
  viewButton: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    padding: '6px 10px',
    borderRadius: 6,
    background: 'var(--panel-border)',
    color: 'var(--text-primary)',
    fontSize: '0.75rem',
    fontWeight: 500,
    transition: 'all var(--transition-fast)',
  },
  calculateButton: {
    display: 'flex',
    alignItems: 'center',
    gap: 4,
    padding: '6px 12px',
    borderRadius: 6,
    background: 'var(--accent-blue)',
    color: 'white',
    fontSize: '0.75rem',
    fontWeight: 500,
    transition: 'all var(--transition-fast)',
  },

  // Parcel Details
  parcelDetails: {},
  detailHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 16,
  },
  categoryBadge: {
    padding: '4px 12px',
    borderRadius: 6,
    color: 'white',
    fontWeight: 600,
    fontSize: '0.8rem',
  },
  detailsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    marginBottom: 16,
  },
  detailField: {
    padding: '8px 12px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 6,
    border: '1px solid var(--panel-border)',
  },
  fieldLabel: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
    marginBottom: 2,
  },
  fieldValue: {
    fontSize: '0.85rem',
    fontWeight: 500,
  },
  calculateCapacityButton: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '12px',
    borderRadius: 8,
    background: 'var(--accent-blue)',
    color: 'white',
    fontSize: '0.9rem',
    fontWeight: 600,
    transition: 'all var(--transition-fast)',
  },

  // Calculator
  calculator: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  calcHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '12px 14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 10,
    border: '1px solid var(--panel-border)',
  },
  calcLabel: {
    fontSize: '0.9rem',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  calcArea: {
    fontSize: '0.8rem',
    color: 'var(--text-secondary)',
  },
  formulaBox: {
    padding: '14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 10,
    border: '1px solid var(--panel-border)',
  },
  formulaTitle: {
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    marginBottom: 8,
  },
  formula: {
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    fontSize: '0.9rem',
    color: 'var(--text-primary)',
    fontFamily: 'var(--font-mono)',
  },
  formulaOperator: {
    color: 'var(--text-secondary)',
  },
  formulaResult: {
    fontWeight: 700,
    color: 'var(--accent-blue)',
  },
  resultBox: {
    padding: '20px',
    background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05))',
    borderRadius: 12,
    border: '1px solid var(--accent-blue)',
    textAlign: 'center',
  },
  resultValue: {
    fontSize: '2.5rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
    lineHeight: 1,
    marginBottom: 4,
  },
  resultLabel: {
    fontSize: '0.85rem',
    color: 'var(--text-secondary)',
  },
  calcNote: {
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
    textAlign: 'center',
    padding: '0 10px',
  },
  statusNote: {
    padding: '12px',
  },
  statusIndicator: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    padding: '10px 14px',
    borderRadius: 8,
  },
  comparisonSection: {
    padding: '14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 10,
    border: '1px solid var(--panel-border)',
  },
  comparisonTitle: {
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    marginBottom: 12,
  },
  comparisonChart: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  comparisonBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  comparisonLabel: {
    width: 80,
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
  },
  barContainer: {
    flex: 1,
    height: 8,
    background: 'var(--panel-border)',
    borderRadius: 4,
    overflow: 'hidden',
  },
  bar: {
    height: '100%',
    borderRadius: 4,
  },
  barValue: {
    width: 60,
    fontSize: '0.75rem',
    color: 'var(--text-primary)',
    textAlign: 'right',
  },

  // Commercial Calculator
  inputSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  inputLabel: {
    fontSize: '0.8rem',
    fontWeight: 500,
    color: 'var(--text-primary)',
  },
  shopSizeInput: {
    width: '100%',
    padding: '12px 14px',
    borderRadius: 8,
    border: '2px solid var(--panel-border)',
    background: 'var(--bg-deep-navy)',
    color: 'var(--text-primary)',
    fontSize: '1.25rem',
    fontWeight: 600,
    textAlign: 'center',
  },
  slider: {
    width: '100%',
    height: 6,
    borderRadius: 3,
    background: 'var(--panel-border)',
    cursor: 'pointer',
    appearance: 'none',
  },
  sliderLabels: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
  },
  presetComparisons: {
    padding: '14px',
    background: 'var(--bg-deep-navy)',
    borderRadius: 10,
    border: '1px solid var(--panel-border)',
  },
  presetTitle: {
    fontSize: '0.75rem',
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    marginBottom: 10,
  },
  presetGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 8,
  },
  presetItem: {
    padding: '10px',
    background: 'var(--panel-border)',
    borderRadius: 6,
    textAlign: 'center',
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  presetValue: {
    fontSize: '1.1rem',
    fontWeight: 700,
    color: 'var(--text-primary)',
  },
  presetLabel: {
    fontSize: '0.7rem',
    color: 'var(--text-secondary)',
  },
};
