import React, { useRef, useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polygon, FeatureGroup, GeoJSON } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';

const RIYADH_CENTER = [24.7136, 46.6753];
const DEFAULT_ZOOM = 12;

const MapView = ({ onAreaSelect, onPolygonSelect, setPolygons, selectedParcels }) => {
  const mapRef = useRef();
  const featureGroupRef = useRef();
  
  // Expose these as inputs to allow dynamic estimation changes
  const [shopSize, setShopSize] = useState(120);
  const [mosqueSpace, setMosqueSpace] = useState(8);

  // Fix Leaflet icon issue
  useEffect(() => {
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    });
  }, []);

  const handleCreated = (e) => {
    const layer = e.layer;
    if (e.layerType === 'rectangle') {
      const bounds = layer.getBounds();
      onAreaSelect({
        min_lon: bounds.getWest(),
        min_lat: bounds.getSouth(),
        max_lon: bounds.getEast(),
        max_lat: bounds.getNorth(),
        shop_size_m2: shopSize,
        mosque_space_m2: mosqueSpace
      });
    } else if (e.layerType === 'polygon') {
      // Leaflet polygon coordinates are {lat, lng} objects, map to [lng, lat] for geojson
      const geojson = layer.toGeoJSON();
      onPolygonSelect({
          geometry: geojson.geometry,
          shop_size_m2: shopSize,
          mosque_space_m2: mosqueSpace
      });
    }
    // Remove the drawn shape so we don't accumulate junk, 
    // the parent might render selected parcels instead
    if (featureGroupRef.current) {
        featureGroupRef.current.clearLayers();
    }
  };

  const getGeoJSONFeature = (parcel) => {
    // Basic conversion logic, assumed `WKT` string if there is one 
    // If your backend returns raw coords, parse them here.
    return null;
  };

  return (
    <div style={{ position: "relative", height: "100%", width: "100%", display: "flex", flexDirection: "column" }}>
        <div className="bg-white p-2 border-b flex gap-4 text-sm z-50 shadow-sm">
            <div className="flex items-center gap-2">
                <label className="font-semibold text-gray-700">Shop Size (m²):</label>
                <input 
                    type="number" 
                    value={shopSize} 
                    onChange={(e) => setShopSize(Number(e.target.value))}
                    className="border rounded px-2 py-1 w-20"
                />
            </div>
            <div className="flex items-center gap-2">
                <label className="font-semibold text-gray-700">Mosque Space per Person (m²):</label>
                <input 
                    type="number" 
                    value={mosqueSpace} 
                    onChange={(e) => setMosqueSpace(Number(e.target.value))}
                    className="border rounded px-2 py-1 w-20"
                />
            </div>
            <div className="ml-auto text-gray-500 italic flex items-center">
                Draw a new shape to apply updated criteria.
            </div>
        </div>

      <MapContainer 
        center={RIYADH_CENTER} 
        zoom={DEFAULT_ZOOM} 
        ref={mapRef}
        style={{ flex: 1, width: "100%", minHeight: "600px" }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
        />
        
        <FeatureGroup ref={featureGroupRef}>
          <EditControl
            position="topright"
            onCreated={handleCreated}
            draw={{
              circle: false,
              circlemarker: false,
              marker: false,
              polyline: false,
              rectangle: true,
              polygon: true
            }}
            edit={{
              edit: false,
              remove: false
            }}
          />
        </FeatureGroup>

        {/* Optional: Render selected parcels if they have geometry */}
        {selectedParcels && selectedParcels.map(parcel => {
            // Very simplified example if you had geometry fields
            return null;
        })}
      </MapContainer>
    </div>
  );
};

export default MapView;
