import React, { useRef, useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, FeatureGroup, CircleMarker, Polygon, Tooltip, useMap } from 'react-leaflet';
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

// DrawControl wrapper to handle mode changes
function DrawControlWrapper({ drawMode, onDrawComplete, onClearLayers }) {
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
      featureGroupRef.current.addLayer(layer);
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
    if (onClearLayers && featureGroupRef.current) {
      // This will be called when parent requests clear
    }
  }, [onClearLayers]);

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
          rectangle: {
            shapeOptions: {
              color: '#3b82f6',
              fillColor: '#3b82f6',
              fillOpacity: 0.2,
              weight: 2,
            },
          },
          polygon: {
            shapeOptions: {
              color: '#3b82f6',
              fillColor: '#3b82f6',
              fillOpacity: 0.2,
              weight: 2,
            },
          },
        }}
        edit={{
          edit: false,
          remove: true,
        }}
      />
    </FeatureGroup>
  );
}

// Markers layer component
function MarkersLayer({ parcels, highlightedObjectIds, selectedObjectIds, onParcelClick }) {
  const hasHighlight = highlightedObjectIds && highlightedObjectIds.length > 0;
  const highlightSet = new Set(highlightedObjectIds || []);
  const selectedSet = new Set(selectedObjectIds || []);

  return (
    <>
      {parcels.map((parcel) => {
        if (!parcel.REPR_LAT || !parcel.REPR_LON) return null;

        const objectId = parcel.OBJECTID;
        const category = parcel.LANDUSE_CATEGORY || 'Unknown';
        const color = CATEGORY_COLORS[category] || CATEGORY_COLORS.Unknown;
        const isReligious = category === 'Religious';
        const isHighlighted = highlightSet.has(objectId);
        const isSelected = selectedSet.has(objectId);

        // Determine radius and opacity based on state
        let radius = isReligious ? 8 : 5;
        let fillOpacity = 0.85;

        if (hasHighlight) {
          if (isHighlighted) {
            radius = 10;
            fillOpacity = 1;
          } else {
            fillOpacity = 0.15;
          }
        }

        return (
          <CircleMarker
            key={objectId}
            center={[parcel.REPR_LAT, parcel.REPR_LON]}
            radius={radius}
            pathOptions={{
              fillColor: color,
              fillOpacity,
              color: 'white',
              weight: 1,
              opacity: hasHighlight ? (isHighlighted ? 1 : 0.15) : 0.8,
            }}
            className={isHighlighted ? 'marker-pulse' : ''}
            eventHandlers={{
              click: () => onParcelClick(objectId),
            }}
          >
            <Tooltip
              direction="top"
              offset={[0, -10]}
              opacity={1}
            >
              <div style={{ minWidth: 120 }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>
                  {parcel.SUBTYPE_LABEL_EN || category}
                </div>
                <div style={{ fontSize: '0.85em', color: '#94a3b8' }}>
                  {Number(parcel.AREA_M2 || 0).toLocaleString()} m²
                </div>
              </div>
            </Tooltip>
          </CircleMarker>
        );
      })}
    </>
  );
}

export default function MapView({
  drawMode,
  onDrawModeComplete,
  onSelectionComplete,
  onClearSelection,
  highlightedObjectIds,
  onParcelClick,
  selectedObjectIds,
}) {
  const mapRef = useRef();
  const [parcels, setParcels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [drawnPolygon, setDrawnPolygon] = useState(null);

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
      if (type === 'bbox') {
        result = await selectBBox(data.min_lat, data.max_lat, data.min_lon, data.max_lon);
      } else if (type === 'polygon') {
        result = await selectPolygon(data);
        setDrawnPolygon(data);
      }

      if (result) {
        onSelectionComplete(result, result.selected_objectids || [], result.parcels || []);
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

        {/* Draw Controls */}
        <DrawControlWrapper
          drawMode={drawMode}
          onDrawComplete={handleDrawComplete}
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

        {/* Drawn Polygon Overlay */}
        {drawnPolygon && (
          <Polygon
            positions={drawnPolygon}
            pathOptions={{
              color: '#3b82f6',
              fillColor: '#3b82f6',
              fillOpacity: 0.15,
              weight: 2,
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
