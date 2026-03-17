import React, { useRef, useEffect, useMemo, useState, useCallback } from 'react';
import { MapContainer, TileLayer, FeatureGroup, Polygon, useMap } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import { getParcelsLightweight, selectPolygon, selectBBox } from '../api/client';

const RIYADH_CENTER = [24.7136, 46.6753];
const DEFAULT_ZOOM = 12;

// Google Maps tile layer
const GOOGLE_MAPS = 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}';

// Marker colors by category
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

// Fly-to handler reacts to zoomTarget changes
function FlyToHandler({ zoomTarget }) {
  const map = useMap();
  useEffect(() => {
    if (zoomTarget && zoomTarget.length >= 2) {
      map.flyTo([zoomTarget[0], zoomTarget[1]], 17, { duration: 1.2 });
    }
  }, [zoomTarget, map]);
  return null;
}

// DrawControl wrapper to handle mode changes
function DrawControlWrapper({ drawMode, onDrawComplete, clearTrigger }) {

  const map = useMap();
  const featureGroupRef = useRef();
  const drawControlRef = useRef();

  useEffect(() => {
    if (!featureGroupRef.current) return;

    // If drawMode changed, trigger the appropriate drawing tool
    if (drawMode === 'polygon') {
      const polygonDrawer = new L.Draw.Polygon(map, {
        shapeOptions: {
          color: '#3b82f6',
          fillColor: '#3b82f6',
          fillOpacity: 0.2,
          weight: 2,
        },
      });
      polygonDrawer.enable();
    } else if (drawMode === 'rectangle') {
      const rectangleDrawer = new L.Draw.Rectangle(map, {
        shapeOptions: {
          color: '#3b82f6',
          fillColor: '#3b82f6',
          fillOpacity: 0.2,
          weight: 2,
        },
      });
      rectangleDrawer.enable();
    }
  }, [drawMode, map]);

  const handleCreated = useCallback((e) => {
    const layer = e.layer;
    
    if (featureGroupRef.current) {
      featureGroupRef.current.clearLayers();
      // Don't keep the drawn layer — we render our own non-interactive
      // <Polygon> overlay instead, so marker clicks aren't blocked.
    }

    if (e.layerType === 'rectangle') {
      const bounds = layer.getBounds();
      onDrawComplete('bbox', {
        min_lat: bounds.getSouth(),
        max_lat: bounds.getNorth(),
        min_lon: bounds.getWest(),
        max_lon: bounds.getEast(),
      });
    } else if (e.layerType === 'polygon') {
      const latLngs = layer.getLatLngs()[0];
      const coordinates = latLngs.map((ll) => [ll.lat, ll.lng]);
      // Close the polygon
      coordinates.push(coordinates[0]);
      onDrawComplete('polygon', coordinates);
    }
  }, [onDrawComplete]);

  // Handle clear from parent
  useEffect(() => {
    if (clearTrigger && featureGroupRef.current) {
      featureGroupRef.current.clearLayers();
    }
  }, [clearTrigger]);

  return (
    <FeatureGroup ref={featureGroupRef}>
      <EditControl
        position="topright"
        onCreated={handleCreated}
        draw={{
          circle: false,
          circlemarker: false,
          marker: false,
          polyline: false,
          rectangle: false,
          polygon: false,
        }}
        edit={{
          edit: false,
          remove: false,
        }}
      />
    </FeatureGroup>
  );
}

// Markers layer — uses imperative Leaflet API for reliable style updates
function MarkersLayer({ parcels, highlightedObjectIds, selectedObjectIds, onParcelClick }) {
  const map = useMap();
  const layerGroupRef = useRef(null);
  const markerMapRef = useRef({}); // PARCEL_ID → L.circleMarker
  const categoryMapRef = useRef({}); // PARCEL_ID → category string
  const onParcelClickRef = useRef(onParcelClick);
  onParcelClickRef.current = onParcelClick;

  // Create markers once when parcels load
  useEffect(() => {
    if (!map || !parcels.length) return;

    // Clean up previous layer group
    if (layerGroupRef.current) {
      map.removeLayer(layerGroupRef.current);
      layerGroupRef.current = null;
    }

    const group = L.layerGroup();
    const markers = {};
    const categories = {};

    for (const parcel of parcels) {
      if (!parcel.REPR_LAT || !parcel.REPR_LON) continue;

      const id = parcel.PARCEL_ID;
      if (!id) continue; // skip null IDs

      const category = parcel.LANDUSE_CATEGORY || 'Unknown';
      const color = CATEGORY_COLORS[category] || CATEGORY_COLORS.Unknown;
      const isReligious = category === 'Religious';

      const marker = L.circleMarker([parcel.REPR_LAT, parcel.REPR_LON], {
        radius: isReligious ? 8 : 5,
        fillColor: color,
        fillOpacity: 0.85,
        color: 'white',
        weight: 1,
        opacity: 0.8,
      });

      marker.bindTooltip(
        `<div style="min-width:120px">
          <div style="font-weight:600;margin-bottom:4px">${parcel.SUBTYPE_LABEL_EN || category}</div>
          <div style="font-size:0.85em;color:#94a3b8">${Number(parcel.AREA_M2 || 0).toLocaleString()} m²</div>
        </div>`,
        { direction: 'top', offset: [0, -10], opacity: 1 }
      );

      // Use ref for callback so effect doesn't re-fire on callback changes
      marker.on('click', () => onParcelClickRef.current(id));
      group.addLayer(marker);
      markers[id] = marker;
      categories[id] = category;
    }

    group.addTo(map);
    layerGroupRef.current = group;
    markerMapRef.current = markers;
    categoryMapRef.current = categories;

    return () => {
      if (layerGroupRef.current) {
        map.removeLayer(layerGroupRef.current);
        layerGroupRef.current = null;
      }
    };
  }, [map, parcels]); // stable deps only — callback is via ref

  // Update styles when highlights change
  useEffect(() => {
    const markers = markerMapRef.current;
    const categories = categoryMapRef.current;
    const markerCount = Object.keys(markers).length;
    if (!markerCount) return;

    const hasHighlight = highlightedObjectIds && highlightedObjectIds.length > 0;
    const highlightSet = new Set((highlightedObjectIds || []).map(String));

    console.log('[Highlight] hasHighlight:', hasHighlight,
      'highlightedCount:', highlightSet.size,
      'totalMarkers:', markerCount);

    let matched = 0;
    for (const [id, marker] of Object.entries(markers)) {
      const cat = categories[id] || 'Unknown';
      const isReligious = cat === 'Religious';
      const isHighlighted = highlightSet.has(id);
      if (isHighlighted) matched++;

      let radius = isReligious ? 8 : 5;
      let fillOpacity = 0.85;
      let opacity = 0.8;

      if (hasHighlight) {
        if (isHighlighted) {
          radius = 12;
          fillOpacity = 1;
          opacity = 1;
        } else {
          fillOpacity = 0.25;
          opacity = 0.25;
        }
      }

      marker.setRadius(radius);
      marker.setStyle({ fillOpacity, opacity });
    }
    console.log('[Highlight] matched markers:', matched, '/', markerCount);
  }, [highlightedObjectIds]);

  return null; // rendering handled imperatively
}

export default function MapView({
  drawMode,
  onDrawModeComplete,
  onSelectionComplete,
  onClearSelection,
  highlightedObjectIds,
  onParcelClick,
  selectedObjectIds,
  zoomTarget,
  clearTrigger,
}) {
  const mapRef = useRef();
  const [parcels, setParcels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [drawnPolygon, setDrawnPolygon] = useState(null);

  // Clear drawn polygon when clearTrigger changes
  useEffect(() => {
    if (clearTrigger) {
      setDrawnPolygon(null);
    }
  }, [clearTrigger]);

  // Load parcels on mount
  useEffect(() => {
    const loadParcels = async () => {
      try {
        const result = await getParcelsLightweight();
        setParcels(result.parcels || []);
      } catch (e) {
        console.error('Failed to load parcels:', e);
      } finally {
        setIsLoading(false);
      }
    };
    loadParcels();
  }, []);

  // Handle draw complete
  const handleDrawComplete = useCallback(async (type, data) => {
    try {
      let result;
      let polygonCoords = null;
      if (type === 'bbox') {
        result = await selectBBox(data.min_lat, data.max_lat, data.min_lon, data.max_lon);
        // Store as polygon for boundary overlay
        polygonCoords = [
          [data.min_lat, data.min_lon],
          [data.min_lat, data.max_lon],
          [data.max_lat, data.max_lon],
          [data.max_lat, data.min_lon],
          [data.min_lat, data.min_lon],
        ];
        setDrawnPolygon(polygonCoords);
      } else if (type === 'polygon') {
        result = await selectPolygon(data);
        polygonCoords = data;
        setDrawnPolygon(data);
      }

      if (result) {
        // Pass polygon coordinates to onSelectionComplete for GDB export
        onSelectionComplete(result, result.selected_objectids || [], result.parcels || [], polygonCoords);
      }
    } catch (e) {
      console.error('Selection failed:', e);
    }

    onDrawModeComplete();
  }, [onSelectionComplete, onDrawModeComplete]);

  // Fix leaflet icon paths
  useEffect(() => {
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    });
  }, []);

  return (
    <div style={styles.container}>
      <MapContainer
        center={RIYADH_CENTER}
        zoom={DEFAULT_ZOOM}
        ref={mapRef}
        style={styles.map}
        zoomControl={true}
      >
        {/* Google Maps Basemap */}
        <TileLayer
          url={GOOGLE_MAPS}
          attribution='&copy; <a href="https://www.google.com/maps">Google Maps</a>'
          maxZoom={20}
        />

        {/* Fly-to on zoomTarget change */}
        <FlyToHandler zoomTarget={zoomTarget} />

        {/* Draw Controls */}
        <DrawControlWrapper
          drawMode={drawMode}
          onDrawComplete={handleDrawComplete}
          clearTrigger={clearTrigger}
        />

        {/* Parcel Markers */}
        {!isLoading && (
          <MarkersLayer
            parcels={parcels}
            highlightedObjectIds={highlightedObjectIds}
            selectedObjectIds={selectedObjectIds}
            onParcelClick={onParcelClick}
          />
        )}

        {/* Drawn Polygon Overlay — boundary only, non-interactive */}
        {drawnPolygon && (
          <Polygon
            positions={drawnPolygon}
            interactive={false}
            pathOptions={{
              color: '#3b82f6',
              fillColor: 'transparent',
              fillOpacity: 0,
              weight: 2.5,
              dashArray: '6, 4',
            }}
          />
        )}
      </MapContainer>

      {/* Loading Overlay */}
      {isLoading && (
        <div style={styles.loadingOverlay}>
          <div style={styles.loadingSpinner} />
          <span>Loading parcels...</span>
        </div>
      )}

      <style>{`
        .marker-pulse {
          animation: pulse-ring 1.5s ease-in-out infinite;
        }
        @keyframes pulse-ring {
          0% { transform: scale(1); }
          50% { transform: scale(1.2); }
          100% { transform: scale(1); }
        }
      `}</style>
    </div>
  );
}

const styles = {
  container: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 0,
  },
  map: {
    width: '100%',
    height: '100%',
  },
  loadingOverlay: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 12,
    padding: '24px 32px',
    background: 'var(--panel-surface)',
    borderRadius: 12,
    border: '1px solid var(--panel-border)',
    color: 'var(--text-secondary)',
    fontSize: '0.9rem',
    zIndex: 100,
  },
  loadingSpinner: {
    width: 32,
    height: 32,
    border: '3px solid var(--panel-border)',
    borderTopColor: 'var(--accent-blue)',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
  },
};
