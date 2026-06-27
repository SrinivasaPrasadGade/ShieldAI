// frontend/src/pages/CitizenPortal.jsx
import React from 'react';
import CitizenChat from '../components/features/CitizenChat';
import CurrencyChecker from '../components/features/CurrencyChecker';

export const CitizenPortal = () => {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '20px', padding: '20px' }}>
      <CitizenChat />
      <CurrencyChecker />
    </div>
  );
};
export default CitizenPortal;
