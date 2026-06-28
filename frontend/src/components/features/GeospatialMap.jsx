import React, { useState, useEffect } from 'react';
import { Map as MapIcon, Compass } from 'lucide-react';
import { api } from '../../services/api';
import { MapContainer, TileLayer, CircleMarker, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

// Controller to handle flying to active alert coordinates
const MapController = ({ activeAlert }) => {
  const map = useMap();
  useEffect(() => {
    if (activeAlert?.location?.lat && activeAlert?.location?.lng) {
      map.flyTo([activeAlert.location.lat, activeAlert.location.lng], 6);
    }
  }, [activeAlert, map]);
  return null;
};

export const GeospatialMap = ({ activeAlert = null }) => {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mapMode, setMapMode] = useState('pins');

  useEffect(() => {
    const fetchIncidents = async () => {
      setLoading(true);
      try {
        await api.getNetwork(); 
        const mockIncidents = [
          { id: 1, type: 'digital_arrest', city: 'Hyderabad', lat: 17.3850, lng: 78.4867, severity: 'HIGH', title: 'CBI Video Call Scam' },
          { id: 2, type: 'digital_arrest', city: 'Mumbai', lat: 19.0760, lng: 72.8777, severity: 'HIGH', title: 'TRAI SIM Block Warning' },
          { id: 3, type: 'digital_arrest', city: 'Delhi', lat: 28.7041, lng: 77.1025, severity: 'CRITICAL', title: 'Operation Mamba Cyber Arrest' },
          { id: 4, type: 'digital_arrest', city: 'Bengaluru', lat: 12.9716, lng: 77.5946, severity: 'HIGH', title: 'HDFC Bank KYC Alert' },
          { id: 5, type: 'ficn', city: 'Malda', lat: 25.0108, lng: 88.1406, severity: 'HIGH', title: 'Counterfeit Seizure Rs 500' },
          { id: 6, type: 'ficn', city: 'Amritsar', lat: 31.6340, lng: 74.8723, severity: 'HIGH', title: 'Fake Currency seizure at border' },
          { id: 7, type: 'investment_fraud', city: 'Pune', lat: 18.5204, lng: 73.8567, severity: 'MEDIUM', title: 'BullTrade Telegram Scam' },
          { id: 8, type: 'investment_fraud', city: 'Chennai', lat: 13.0827, lng: 80.2707, severity: 'MEDIUM', title: 'Hotel Rating Scam' },
        ];
        setIncidents(mockIncidents);
      } catch (err) {
        console.error('Error fetching geo incidents:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchIncidents();
  }, [activeAlert]);

  return (
    <div className="glass-panel" style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: '400px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MapIcon size={18} color="var(--accent-cyan)" />
          India Cybercrime Geospatial Map
        </h3>
        
        <div style={{ display: 'flex', gap: '6px', background: 'var(--bg-secondary)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
          <button 
            onClick={() => setMapMode('pins')}
            style={{ padding: '4px 10px', borderRadius: '6px', border: 'none', background: mapMode === 'pins' ? 'var(--accent-cyan)' : 'transparent', color: '#fff', fontSize: '0.75rem', fontWeight: '500', cursor: 'pointer' }}
          >Pins</button>
          <button 
            onClick={() => setMapMode('heatmap')}
            style={{ padding: '4px 10px', borderRadius: '6px', border: 'none', background: mapMode === 'heatmap' ? 'var(--accent-cyan)' : 'transparent', color: '#fff', fontSize: '0.75rem', fontWeight: '500', cursor: 'pointer' }}
          >Heatmap</button>
        </div>
      </div>

      {/* Leaflet Map */}
      <div style={{ flex: 1, borderRadius: '12px', border: '1px solid var(--border-glass)', overflow: 'hidden', position: 'relative' }}>
        <MapContainer 
          center={[22.5937, 78.9629]} 
          zoom={4.5} 
          style={{ width: '100%', height: '100%', background: '#070a12', zIndex: 1 }}
          zoomControl={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; CARTO'
          />
          <MapController activeAlert={activeAlert} />

          {incidents.map((inc) => {
            const isCritical = inc.severity === 'CRITICAL';
            const color = mapMode === 'heatmap'
              ? (isCritical ? '#ef4444' : inc.severity === 'HIGH' ? '#f97316' : '#eab308')
              : (isCritical ? 'var(--accent-red)' : inc.severity === 'HIGH' ? 'var(--accent-orange)' : 'var(--accent-cyan)');

            return (
              <CircleMarker
                key={inc.id}
                center={[inc.lat, inc.lng]}
                radius={mapMode === 'heatmap' ? 24 : (isCritical ? 10 : 8)}
                pathOptions={{
                  fillColor: color,
                  fillOpacity: mapMode === 'heatmap' ? 0.3 : 0.8,
                  color: mapMode === 'heatmap' ? 'transparent' : color,
                  weight: 2,
                }}
              >
                <Tooltip direction="top" offset={[0, -10]} opacity={0.95}>
                  <div style={{ padding: '4px', fontSize: '0.8rem' }}>
                    <strong style={{ display: 'block', color: '#111' }}>{inc.city}</strong>
                    <span style={{ fontSize: '0.75rem', color: '#444' }}>{inc.title}</span><br/>
                    <span style={{ fontSize: '0.7rem', fontWeight: 'bold', color: isCritical ? '#d32f2f' : '#666' }}>
                      SEVERITY: {inc.severity}
                    </span>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>
        
        {/* Compass rose */}
        <div style={{ position: 'absolute', bottom: '16px', left: '16px', color: 'rgba(255,255,255,0.4)', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.7rem', pointerEvents: 'none', zIndex: 1000 }}>
          <Compass size={14} className="animate-spin" style={{ animationDuration: '20s' }} />
          <span>SHIELDAI NAV</span>
        </div>
      </div>

      {/* Footer Info */}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
        <span>Bounds: India Region</span>
        <span>Active Map Center: New Delhi (Cyber Command Cell)</span>
      </div>
    </div>
  );
};
export default GeospatialMap;
