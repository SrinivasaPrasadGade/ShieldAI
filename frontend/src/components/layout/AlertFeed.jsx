// frontend/src/components/layout/AlertFeed.jsx
import React, { useState } from 'react';
import { AlertCircle, ShieldAlert, Zap, Clock, ShieldCheck, MapPin, CheckCircle, Wifi, WifiOff } from 'lucide-react';
import { api } from '../../services/api';

export const AlertFeed = ({ alerts = [], onAlertClick = null, activeAlertId = null, isRealtimeConnected = false, markAsReadLocally = null }) => {
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');

  const getSeverityStyles = (severity, isRead) => {
    const opacity = isRead ? '0.5' : '1';
    switch (severity) {
      case 'CRITICAL':
        return { color: '#ef4444', glow: `rgba(239, 68, 68, 0.15)`, border: `rgba(239, 68, 68, 0.4)`, opacity };
      case 'HIGH':
        return { color: '#f97316', glow: `rgba(249, 115, 22, 0.15)`, border: `rgba(249, 115, 22, 0.4)`, opacity };
      case 'MEDIUM':
        return { color: '#eab308', glow: `rgba(234, 179, 8, 0.15)`, border: `rgba(234, 179, 8, 0.3)`, opacity };
      default:
        return { color: '#10b981', glow: `rgba(16, 185, 129, 0.15)`, border: `rgba(16, 185, 129, 0.3)`, opacity };
    }
  };

  const getAlertIcon = (alertType, severity) => {
    if (severity === 'CRITICAL') return <ShieldAlert size={16} color="#ef4444" />;
    if (alertType === 'ficn_detected') return <Zap size={16} color="#f97316" />;
    return <AlertCircle size={16} color="var(--accent-cyan)" />;
  };

  const handleMarkRead = async (e, alertId) => {
    e.stopPropagation();
    if (markAsReadLocally) {
      markAsReadLocally(alertId);
    }
    try {
      await api.markAlertRead(alertId);
    } catch (err) {
      console.error('Failed to mark alert as read', err);
    }
  };

  const filteredAlerts = alerts.filter(a => {
    if (severityFilter !== 'ALL' && a.severity !== severityFilter) return false;
    if (typeFilter !== 'ALL' && a.alert_type !== typeFilter) return false;
    return true;
  });

  return (
    <div className="glass-panel" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-glass)', background: 'rgba(255, 255, 255, 0.02)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={18} color="var(--accent-cyan)" />
            Live Intelligence Feed
          </h3>
          <span style={{ fontSize: '0.75rem', background: 'var(--accent-red-glow)', border: '1px solid var(--accent-red)', padding: '2px 8px', borderRadius: '10px', color: 'var(--accent-red)', fontWeight: 'bold' }}>
            {alerts.filter(a => !a.is_read).length} Unread
          </span>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '8px' }}>
          <select 
            value={severityFilter} 
            onChange={e => setSeverityFilter(e.target.value)}
            style={{ background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid var(--border-glass)', borderRadius: '6px', padding: '4px 8px', fontSize: '0.75rem', outline: 'none' }}
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
          </select>
          <select 
            value={typeFilter} 
            onChange={e => setTypeFilter(e.target.value)}
            style={{ background: 'rgba(0,0,0,0.3)', color: '#fff', border: '1px solid var(--border-glass)', borderRadius: '6px', padding: '4px 8px', fontSize: '0.75rem', outline: 'none' }}
          >
            <option value="ALL">All Types</option>
            <option value="scam_detected">Scam Detected</option>
            <option value="ficn_detected">Counterfeit Currency</option>
            <option value="fraud_ring_identified">Fraud Ring</option>
          </select>
        </div>

        {/* Connection Banner */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: isRealtimeConnected ? '#10b981' : '#f97316' }}>
          {isRealtimeConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
          {isRealtimeConnected ? 'Live Connection Active' : 'Reconnecting...'}
        </div>
      </div>

      {/* Feed List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {filteredAlerts.length === 0 ? (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)' }}>
            No alerts match criteria.
          </div>
        ) : (
          filteredAlerts.map((alert) => {
            const styles = getSeverityStyles(alert.severity, alert.is_read);
            const isActive = activeAlertId === alert.id;
            
            return (
              <div
                key={alert.id}
                onClick={() => onAlertClick && onAlertClick(alert)}
                style={{
                  padding: '12px 14px',
                  borderRadius: '10px',
                  background: isActive ? 'var(--bg-tertiary)' : 'rgba(255,255,255,0.01)',
                  border: `1px solid ${isActive ? 'var(--accent-cyan)' : styles.border}`,
                  boxShadow: isActive ? 'var(--shadow-glow)' : 'none',
                  cursor: 'pointer',
                  transition: 'var(--transition-smooth)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  opacity: styles.opacity
                }}
                onMouseOver={(e) => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseOut={(e) => { if (!isActive) e.currentTarget.style.background = 'rgba(255,255,255,0.01)'; }}
              >
                {/* Meta details */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ 
                    fontSize: '0.7rem', 
                    fontWeight: 'bold', 
                    color: styles.color,
                    background: styles.glow,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    border: `1px solid ${styles.color}22`
                  }}>
                    {alert.severity}
                  </span>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={10} />
                      {alert.created_at ? new Date(alert.created_at).toLocaleTimeString() : 'Just now'}
                    </span>
                    {!alert.is_read && (
                      <button 
                        onClick={(e) => handleMarkRead(e, alert.id)}
                        title="Mark as Read"
                        style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                      >
                        <CheckCircle size={14} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Title */}
                <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', color: 'var(--text-primary)', fontWeight: '500', fontSize: '0.85rem' }}>
                  {getAlertIcon(alert.alert_type, alert.severity)}
                  <span>{alert.title}</span>
                </div>

                {/* Description snippet */}
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', lineHeight: '1.4' }}>
                  {alert.description}
                </p>

                {/* Location pin */}
                {alert.location && (alert.location.city || alert.location.state) && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--accent-cyan)' }}>
                    <MapPin size={10} />
                    <span>{alert.location.city || alert.location.state}</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
export default AlertFeed;
