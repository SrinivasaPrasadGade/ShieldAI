// frontend/src/components/layout/TopBar.jsx
import React from 'react';
import { ShieldCheck, UserCheck, ShieldAlert, Cpu, Radio } from 'lucide-react';

export const TopBar = ({ activeView = 'dashboard', onViewChange = null, isRealtimeConnected = false }) => {
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '12px 30px',
      background: 'rgba(15, 23, 42, 0.8)',
      backdropFilter: 'blur(10px)',
      borderBottom: '1px solid var(--border-glass)',
      zIndex: 100,
      position: 'sticky',
      top: 0
    }}>
      {/* Title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          background: 'linear-gradient(135deg, var(--accent-cyan), var(--accent-purple))',
          padding: '8px',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <ShieldCheck size={20} color="#fff" />
        </div>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '6px' }}>
            ShieldAI
            <span style={{ fontSize: '0.65rem', background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: '4px', color: 'var(--text-secondary)' }}>
              v1.0.0
            </span>
          </h2>
        </div>
      </div>

      {/* Tab Switcher */}
      <div style={{ display: 'flex', background: 'rgba(0, 0, 0, 0.25)', border: '1px solid var(--border-glass)', padding: '4px', borderRadius: '10px', gap: '4px' }}>
        <button
          onClick={() => onViewChange && onViewChange('dashboard')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 16px',
            borderRadius: '8px',
            border: 'none',
            background: activeView === 'dashboard' ? 'var(--accent-cyan-glow)' : 'transparent',
            borderWidth: '1px',
            borderStyle: 'solid',
            borderColor: activeView === 'dashboard' ? 'rgba(6, 182, 212, 0.3)' : 'transparent',
            color: activeView === 'dashboard' ? 'var(--text-primary)' : 'var(--text-secondary)',
            fontWeight: '600',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'var(--transition-smooth)'
          }}
        >
          <Cpu size={14} />
          LE Command Centre
        </button>
        <button
          onClick={() => onViewChange && onViewChange('citizen')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 16px',
            borderRadius: '8px',
            border: 'none',
            background: activeView === 'citizen' ? 'var(--accent-purple-glow)' : 'transparent',
            borderWidth: '1px',
            borderStyle: 'solid',
            borderColor: activeView === 'citizen' ? 'rgba(139, 92, 246, 0.3)' : 'transparent',
            color: activeView === 'citizen' ? 'var(--text-primary)' : 'var(--text-secondary)',
            fontWeight: '600',
            fontSize: '0.85rem',
            cursor: 'pointer',
            transition: 'var(--transition-smooth)'
          }}
        >
          <UserCheck size={14} />
          Citizen Safety Shield
        </button>
      </div>

      {/* Network / Socket Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid var(--border-glass)',
          padding: '6px 12px',
          borderRadius: '8px',
          fontSize: '0.75rem'
        }}>
          <Radio size={12} color={isRealtimeConnected ? 'var(--accent-green)' : 'var(--accent-red)'} className={isRealtimeConnected ? 'animate-pulse' : ''} />
          <span style={{ color: 'var(--text-secondary)' }}>
            Socket Feed: <strong>{isRealtimeConnected ? 'Connected' : 'Offline'}</strong>
          </span>
        </div>
      </div>
    </div>
  );
};
export default TopBar;
