import React, { useState, useCallback } from 'react';
import MapView from './components/MapView';
import TopBar from './components/TopBar';
import LeftToolbar from './components/LeftToolbar';
import BottomPanel from './components/BottomPanel';
import ParcelDetailDrawer from './components/ParcelDetailDrawer';
import ReportViewer from './components/ReportViewer';
import QueryBar from './components/QueryBar';
import { queryCategory, generateTextReport, getParcelDetail } from './api/client';
import './index.css';

export default function App() {
  // Selection state
  const [selectionSummary, setSelectionSummary] = useState(null);
  const [selectionData, setSelectionData] = useState(null); // Full parcel data
  const [selectedObjectIds, setSelectedObjectIds] = useState([]);
  
  // Query state
  const [highlightedObjectIds, setHighlightedObjectIds] = useState([]);
  const [queriedParcels, setQueriedParcels] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);

  // --- Session context tracking for accurate reports ---
  // Accumulate applied filter descriptions (reset on new selection)
  const [appliedFilters, setAppliedFilters] = useState([]);
  // Filtered/queried subset summary (counts, area breakdown for filtered parcels)
  const [filteredSummary, setFilteredSummary] = useState(null);
  // Individual capacity calculations performed by the user
  const [capacityCalculations, setCapacityCalculations] = useState([]);
  
  // UI state
  const [drawMode, setDrawMode] = useState(null); // 'polygon' | 'rectangle' | null
  const [isBottomPanelExpanded, setIsBottomPanelExpanded] = useState(true);
  const [activeTab, setActiveTab] = useState('summary'); // 'summary' | 'analysis'
  const [clearTrigger, setClearTrigger] = useState(0); // bumped to tell MapView to clear polygon
  
  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState('query'); // 'query' | 'detail' | 'calculator'
  const [selectedParcel, setSelectedParcel] = useState(null);
  
  // Report modal state
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [reportError, setReportError] = useState(null);

  // Map zoom target [lat, lng]
  const [zoomTarget, setZoomTarget] = useState(null);
  
  // Selection polygon coordinates for GDB export
  const [polygonCoordinates, setPolygonCoordinates] = useState(null);

  // Handle selection complete from MapView
  const handleSelectionComplete = useCallback((summary, objectIds, parcels, polygonCoords) => {
    setSelectionSummary(summary);
    setSelectedObjectIds(objectIds);
    setSelectionData({ parcels });
    setPolygonCoordinates(polygonCoords || null);
    setIsBottomPanelExpanded(true);
    // Reset ALL query + session context when a new area is drawn
    setHighlightedObjectIds([]);
    setQueriedParcels([]);
    setActiveCategory(null);
    setIsDrawerOpen(false);
    setAppliedFilters([]);
    setFilteredSummary(null);
    setCapacityCalculations([]);
  }, []);

  // Handle clear selection
  const handleClearSelection = useCallback(() => {
    setSelectionSummary(null);
    setSelectionData(null);
    setSelectedObjectIds([]);
    setPolygonCoordinates(null);
    setHighlightedObjectIds([]);
    setQueriedParcels([]);
    setActiveCategory(null);
    setIsBottomPanelExpanded(false);
    setIsDrawerOpen(false);
    setDrawMode(null);
    setClearTrigger(prev => prev + 1); // tell MapView to clear drawn polygon
    setAppliedFilters([]);
    setFilteredSummary(null);
    setCapacityCalculations([]);
  }, []);

  // Handle category query from QueryBar or BottomPanel
  const handleCategorySelect = useCallback(async (category) => {
    console.log('[CategorySelect] clicked:', category, 'active:', activeCategory);
    if (activeCategory === category) {
      // Deselect if same category clicked
      setActiveCategory(null);
      setHighlightedObjectIds([]);
      setQueriedParcels([]);
      setIsDrawerOpen(false);
      setFilteredSummary(null);
      // Remove any filter entry for this category
      setAppliedFilters(prev => prev.filter(f => !f.startsWith(`Category filter: ${category}`)));
      return;
    }

    try {
      console.log('[CategorySelect] querying with', selectedObjectIds.length, 'IDs');
      const result = await queryCategory(category, selectedObjectIds);
      const objectIds = result.parcels.map(p => p.PARCEL_ID);
      console.log('[CategorySelect] got', objectIds.length, 'results, sample:', objectIds.slice(0, 3));
      
      setActiveCategory(category);
      setHighlightedObjectIds(objectIds);
      setQueriedParcels(result.parcels);
      setDrawerMode('query');
      setIsDrawerOpen(true);

      // --- Build filtered summary from the returned parcels ---
      const fParcels = result.parcels;
      let fArea = 0, fVacant = 0, fDeveloped = 0;
      const fBreakdown = {};
      const fBlocks = new Set();
      fParcels.forEach(p => {
        const area = Number(p.AREA_M2) || 0;
        fArea += area;
        const status = (p.PARCEL_STATUS_LABEL || '').toLowerCase();
        if (status.includes('vacant')) fVacant++;
        else if (status.includes('develop')) fDeveloped++;
        const cat = p.LANDUSE_CATEGORY || 'Unknown';
        if (!fBreakdown[cat]) fBreakdown[cat] = { count: 0, total_area_m2: 0, total_capacity_estimated: 0, total_shops_estimated: 0 };
        fBreakdown[cat].count++;
        fBreakdown[cat].total_area_m2 += area;
        fBreakdown[cat].total_capacity_estimated += Number(p.CAPACITY_ESTIMATED) || 0;
        fBreakdown[cat].total_shops_estimated += Number(p.SHOPS_ESTIMATED) || 0;
        if (p.BLOCK_ID) fBlocks.add(String(p.BLOCK_ID));
      });
      setFilteredSummary({
        total_parcels: fParcels.length,
        total_area_m2: Math.round(fArea * 100) / 100,
        vacant_count: fVacant,
        developed_count: fDeveloped,
        breakdown: fBreakdown,
        block_ids_covered: [...fBlocks],
      });

      // Record filter in session context (replace previous category filter if exists)
      setAppliedFilters(prev => {
        const without = prev.filter(f => !f.startsWith('Category filter:'));
        return [...without, `Category filter: ${category} (${fParcels.length} parcels)`];
      });
    } catch (e) {
      console.error('[CategorySelect] FAILED:', e);
    }
  }, [activeCategory, selectedObjectIds]);

  // Handle dropdown filter from QueryBar
  const handleDropdownFilter = useCallback((filteredParcels, filterDescription) => {
    if (!filteredParcels) {
      // Clear filter — reset highlights + filter state
      setHighlightedObjectIds([]);
      setQueriedParcels([]);
      setIsDrawerOpen(false);
      setFilteredSummary(null);
      setAppliedFilters(prev => prev.filter(f => !f.startsWith('Dropdown filter:')));
      return;
    }
    const objectIds = filteredParcels.map(p => p.PARCEL_ID);
    setHighlightedObjectIds(objectIds);
    setQueriedParcels(filteredParcels);
    setDrawerMode('query');
    setIsDrawerOpen(true);

    // Build filtered summary
    let fArea = 0, fVacant = 0, fDeveloped = 0;
    const fBreakdown = {};
    const fBlocks = new Set();
    filteredParcels.forEach(p => {
      const area = Number(p.AREA_M2) || 0;
      fArea += area;
      const status = (p.PARCEL_STATUS_LABEL || '').toLowerCase();
      if (status.includes('vacant')) fVacant++;
      else if (status.includes('develop')) fDeveloped++;
      const cat = p.LANDUSE_CATEGORY || 'Unknown';
      if (!fBreakdown[cat]) fBreakdown[cat] = { count: 0, total_area_m2: 0, total_capacity_estimated: 0, total_shops_estimated: 0 };
      fBreakdown[cat].count++;
      fBreakdown[cat].total_area_m2 += area;
      if (p.BLOCK_ID) fBlocks.add(String(p.BLOCK_ID));
    });
    setFilteredSummary({
      total_parcels: filteredParcels.length,
      total_area_m2: Math.round(fArea * 100) / 100,
      vacant_count: fVacant,
      developed_count: fDeveloped,
      breakdown: fBreakdown,
      block_ids_covered: [...fBlocks],
    });
    if (filterDescription) {
      setAppliedFilters(prev => {
        const without = prev.filter(f => !f.startsWith('Dropdown filter:'));
        return [...without, `Dropdown filter: ${filterDescription} (${filteredParcels.length} parcels)`];
      });
    }
  }, []);

  // Handle NL query result — highlight matching parcels on the map
  const handleNlQueryResult = useCallback((matchingParcelIds, question) => {
    setHighlightedObjectIds(matchingParcelIds);
    setActiveCategory(null);
    // Build queriedParcels from the matching IDs for the drawer
    const allParcels = selectionSummary?.parcels || [];
    const idSet = new Set(matchingParcelIds.map(String));
    const matched = allParcels.filter(p => idSet.has(String(p.PARCEL_ID)));
    if (matched.length > 0) {
      setQueriedParcels(matched);
      setDrawerMode('query');
      setIsDrawerOpen(true);

      // Build filtered summary for NL match
      let fArea = 0, fVacant = 0, fDeveloped = 0;
      const fBreakdown = {};
      const fBlocks = new Set();
      matched.forEach(p => {
        const area = Number(p.AREA_M2) || 0;
        fArea += area;
        const status = (p.PARCEL_STATUS_LABEL || '').toLowerCase();
        if (status.includes('vacant')) fVacant++;
        else if (status.includes('develop')) fDeveloped++;
        const cat = p.LANDUSE_CATEGORY || 'Unknown';
        if (!fBreakdown[cat]) fBreakdown[cat] = { count: 0, total_area_m2: 0, total_capacity_estimated: 0, total_shops_estimated: 0 };
        fBreakdown[cat].count++;
        fBreakdown[cat].total_area_m2 += area;
        if (p.BLOCK_ID) fBlocks.add(String(p.BLOCK_ID));
      });
      setFilteredSummary({
        total_parcels: matched.length,
        total_area_m2: Math.round(fArea * 100) / 100,
        vacant_count: fVacant,
        developed_count: fDeveloped,
        breakdown: fBreakdown,
        block_ids_covered: [...fBlocks],
      });
    }
    if (question) {
      setAppliedFilters(prev => {
        const without = prev.filter(f => !f.startsWith('Natural language query:'));
        return [...without, `Natural language query: "${question}" (${matchingParcelIds.length} matches)`];
      });
    }
  }, [selectionSummary]);

  // Handle parcel click from map
  const handleParcelClick = useCallback(async (objectId) => {
    try {
      const result = await getParcelDetail(objectId);
      setSelectedParcel(result.parcel);
      setDrawerMode('detail');
      setIsDrawerOpen(true);
    } catch (e) {
      console.error('Failed to get parcel detail:', e);
    }
  }, []);

  // Handle parcel selection from drawer list
  const handleParcelSelect = useCallback((parcel) => {
    setSelectedParcel(parcel);
    setDrawerMode('detail');
  }, []);

  // Handle highlight (hover/click) on parcel in drawer — zoom to it on map
  const handleHighlightParcel = useCallback((objectId) => {
    // Find parcel coordinates from queriedParcels or selectionSummary
    const allParcels = [
      ...(queriedParcels || []),
      ...(selectionSummary?.parcels || []),
    ];
    const parcel = allParcels.find(p => String(p.PARCEL_ID) === String(objectId));
    if (parcel?.REPR_LAT && parcel?.REPR_LON) {
      setZoomTarget([parcel.REPR_LAT, parcel.REPR_LON, Date.now()]);
    }
  }, [queriedParcels, selectionSummary]);

  // Handle back to query results from parcel detail
  const handleBackToQuery = useCallback(() => {
    setSelectedParcel(null);
    setDrawerMode('query');
  }, []);

  // Called by ParcelDetailDrawer when a capacity calculation completes
  const handleCapacityCalculated = useCallback((calcResult) => {
    setCapacityCalculations(prev => {
      // Replace if same parcel+type already exists
      const key = `${calcResult.type}_${calcResult.parcel_id}`;
      const without = prev.filter(c => `${c.type}_${c.parcel_id}` !== key);
      return [...without, calcResult];
    });
  }, []);

  // Build the complete report payload including all session context
  const buildReportPayload = useCallback((overrideSummary = null, overrideTitle = null, overrideType = 'selection') => {
    return {
      selection_summary: overrideSummary || selectionSummary,
      filtered_summary: filteredSummary || undefined,
      applied_filters: appliedFilters.length > 0 ? appliedFilters : undefined,
      capacity_calculations: capacityCalculations.length > 0 ? capacityCalculations : undefined,
      report_type: overrideType,
      report_title: overrideTitle || undefined,
    };
  }, [selectionSummary, filteredSummary, appliedFilters, capacityCalculations]);

  // Handle report generation
  const handleGenerateReport = useCallback(async () => {
    if (!selectionData?.parcels?.length) return;
    
    setIsReportOpen(true);
    setIsGeneratingReport(true);
    setReportData(null);
    setReportError(null);
    
    try {
      const payload = buildReportPayload(null, null, 'selection');
      const result = await generateTextReport(payload);
      setReportData(result);
    } catch (e) {
      console.error('Failed to generate report:', e);
      setReportError(e.message || 'Failed to generate report');
    } finally {
      setIsGeneratingReport(false);
    }
  }, [selectionSummary, selectionData, buildReportPayload]);

  // Handle draw mode change
  const handleDrawModeChange = useCallback((mode) => {
    setDrawMode(prev => prev === mode ? null : mode);
  }, []);

  // Handle zoom to block from AnalysisPanel
  const handleZoomToBlock = useCallback((block) => {
    if (block.centroid && block.centroid.length === 2) {
      setZoomTarget([...block.centroid, Date.now()]); // append timestamp to force re-trigger
    }
  }, []);

  // Handle block report generation from AnalysisPanel
  const handleBlockReport = useCallback(async (block) => {
    if (!selectionData?.parcels?.length) return;

    // Filter parcels to only this block
    const blockParcels = selectionData.parcels.filter(p =>
      (p.BLOCK_NO || p.BLOCK_ID || 'Unknown') === String(block.block_id)
    );
    if (!blockParcels.length) return;

    // Build a precise summary for the block
    let totalArea = 0, bVacant = 0, bDeveloped = 0;
    const categories = {};
    const bBlocks = new Set([String(block.block_id)]);
    blockParcels.forEach(p => {
      const area = Number(p.AREA_M2) || 0;
      totalArea += area;
      const status = (p.PARCEL_STATUS_LABEL || '').toLowerCase();
      if (status.includes('vacant')) bVacant++;
      else if (status.includes('develop')) bDeveloped++;
      const cat = p.LANDUSE_CATEGORY || 'Unknown';
      if (!categories[cat]) categories[cat] = { count: 0, total_area_m2: 0, total_capacity_estimated: 0, total_shops_estimated: 0 };
      categories[cat].count++;
      categories[cat].total_area_m2 += area;
      categories[cat].total_capacity_estimated += Number(p.CAPACITY_ESTIMATED) || 0;
      categories[cat].total_shops_estimated += Number(p.SHOPS_ESTIMATED) || 0;
    });
    const blockSummary = {
      total_parcels: blockParcels.length,
      total_area_m2: Math.round(totalArea * 100) / 100,
      vacant_count: bVacant,
      developed_count: bDeveloped,
      breakdown: categories,
      category_breakdown: Object.fromEntries(Object.entries(categories).map(([k, v]) => [k, v.count])),
      block_ids_covered: [...bBlocks],
      total_religious_capacity: categories?.Religious?.total_capacity_estimated || 0,
      total_shops_estimated: categories?.Commercial?.total_shops_estimated || 0,
    };

    setIsReportOpen(true);
    setIsGeneratingReport(true);
    setReportData(null);
    setReportError(null);

    try {
      const payload = {
        selection_summary: blockSummary,
        report_type: 'block',
        report_title: `Block ${block.block_id} — Land Analysis Report`,
        // Include any capacity calculations relevant to this block
        capacity_calculations: capacityCalculations.filter(c => {
          const p = selectionData.parcels.find(px => String(px.PARCEL_ID) === String(c.parcel_id));
          return p && (p.BLOCK_NO || p.BLOCK_ID) === String(block.block_id);
        }),
      };
      const result = await generateTextReport(payload);
      setReportData(result);
    } catch (e) {
      console.error('Failed to generate block report:', e);
      setReportError(e.message || 'Failed to generate report');
    } finally {
      setIsGeneratingReport(false);
    }
  }, [selectionData, capacityCalculations]);

  return (
    <div className="app-container" style={styles.container}>
      {/* Full-screen Map */}
      <MapView
        drawMode={drawMode}
        onDrawModeComplete={() => setDrawMode(null)}
        onSelectionComplete={handleSelectionComplete}
        onClearSelection={handleClearSelection}
        highlightedObjectIds={highlightedObjectIds}
        onParcelClick={handleParcelClick}
        selectedObjectIds={selectedObjectIds}
        zoomTarget={zoomTarget}
        clearTrigger={clearTrigger}
      />

      {/* Top Bar */}
      <TopBar
        selectionSummary={selectionSummary}
        onGenerateReport={handleGenerateReport}
        isGeneratingReport={isGeneratingReport}
        selectedObjectIds={selectedObjectIds}
        polygonCoordinates={polygonCoordinates}
        activeCategory={activeCategory}
        queriedParcels={queriedParcels}
        capacityCalculations={capacityCalculations}
      />

      {/* Left Toolbar */}
      <LeftToolbar
        drawMode={drawMode}
        onDrawModeChange={handleDrawModeChange}
        onClearSelection={handleClearSelection}
        hasSelection={selectedObjectIds.length > 0}
      />

      {/* Query Bar - only visible when selection exists */}
      {selectionSummary && (
        <QueryBar
          selectionSummary={selectionSummary}
          activeCategory={activeCategory}
          onCategorySelect={handleCategorySelect}
          selectedObjectIds={selectedObjectIds}
          queriedParcels={queriedParcels}
          onDropdownFilter={handleDropdownFilter}
          onNlQueryResult={handleNlQueryResult}
        />
      )}

      {/* Bottom Panel - selection statistics with tabs */}
      {selectionSummary && (
        <BottomPanel
          isExpanded={isBottomPanelExpanded}
          onToggle={() => setIsBottomPanelExpanded(prev => !prev)}
          selectionSummary={selectionSummary}
          selectionData={selectionData}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          activeCategory={activeCategory}
          onCategorySelect={handleCategorySelect}
          onGenerateReport={handleGenerateReport}
          isGeneratingReport={isGeneratingReport}
          onZoomToBlock={handleZoomToBlock}
          onBlockReport={handleBlockReport}
        />
      )}

      {/* Right Drawer - parcel detail, query results, calculators */}
      <ParcelDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        mode={drawerMode}
        queriedParcels={queriedParcels}
        activeCategory={activeCategory}
        selectedParcel={selectedParcel}
        onParcelSelect={handleParcelSelect}
        onHighlightParcel={handleHighlightParcel}
        onBackToQuery={handleBackToQuery}
        onCapacityCalculated={handleCapacityCalculated}
      />

      {/* Report Modal */}
      <ReportViewer
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        reportData={reportData}
        selectionData={selectionData}
        selectionSummary={selectionSummary}
        filteredSummary={filteredSummary}
        appliedFilters={appliedFilters}
        capacityCalculations={capacityCalculations}
        buildReportPayload={buildReportPayload}
        isLoading={isGeneratingReport}
        error={reportError}
      />
    </div>
  );
}

const styles = {
  container: {
    position: 'relative',
    width: '100vw',
    height: '100vh',
    overflow: 'hidden',
    background: 'var(--bg-deep-navy)',
  },
};
