// frontend/src/pages/CommandDashboard.jsx
import React from 'react';
import AlertFeed from '../components/layout/AlertFeed';
import GeospatialMap from '../components/features/GeospatialMap';
import FraudNetworkGraph from '../components/features/FraudNetworkGraph';

export const CommandDashboard = ({ feed, activeAlert, onAlertClick }) => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', height: '100%', padding: '20px', gap: '20px', overflow: 'hidden' }}>
      <AlertFeed 
        alerts={feed} 
        onAlertClick={onAlertClick} 
        activeAlertId={activeAlert?.id} 
      />
      <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr', gap: '20px', height: '100%', overflow: 'hidden' }}>
        <GeospatialMap activeAlert={activeAlert} />
        <FraudNetworkGraph />
      </div>
    </div>
  );
};
export default CommandDashboard;
