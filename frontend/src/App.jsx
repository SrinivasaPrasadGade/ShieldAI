// frontend/src/App.jsx
import React, { useState, useEffect } from 'react';
import { TopBar } from './components/layout/TopBar';
import { AlertFeed } from './components/layout/AlertFeed';
import { GeospatialMap } from './components/features/GeospatialMap';
import { FraudNetworkGraph } from './components/features/FraudNetworkGraph';
import { CitizenChat } from './components/features/CitizenChat';
import { CurrencyChecker } from './components/features/CurrencyChecker';
import { useSocket } from './hooks/useSocket';
import { useAuth } from './hooks/useAuth';
import { Login } from './components/layout/Login';
import { ShieldAlert, X } from 'lucide-react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    // Graceful error logging
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', textAlign: 'center', color: '#ef4444', background: '#0a0f1d', height: '100vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
          <h2 style={{ marginBottom: '10px' }}>Something went wrong</h2>
          <p style={{ color: '#94a3b8', marginBottom: '20px' }}>Please refresh the page or try again.</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{ padding: '8px 24px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: '600' }}
          >Try Again</button>
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const [activeView, setActiveView] = useState('citizen');
  const [activeAlert, setActiveAlert] = useState(null);
  const [showToast, setShowToast] = useState(false);
  const [toastData, setToastData] = useState(null);
  
  const { user, loading } = useAuth();
  const isAuthenticated = !!user;

  const { feed, connected, latestToast, markAsReadLocally } = useSocket('law_enforcement');

  // Trigger real-time toast notifications
  useEffect(() => {
    if (latestToast) {
      setToastData(latestToast);
      setShowToast(true);
      setActiveAlert(latestToast);
      
      // Auto-dismiss after 6s
      const timer = setTimeout(() => {
        setShowToast(false);
      }, 6000);

      return () => clearTimeout(timer);
    }
  }, [latestToast]);

  const handleAlertClick = (alert) => {
    setActiveAlert(alert);
  };

  const handleToastClick = () => {
    if (!isAuthenticated) return; // Prevent unauthorized access
    setActiveView('dashboard');
    if (toastData) {
      setActiveAlert(toastData);
    }
    setShowToast(false);
  };

  const handleViewChange = (view) => {
    setActiveView(view);
  };

  return (
    <ErrorBoundary>
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
        <TopBar 
          activeView={activeView} 
          onViewChange={handleViewChange} 
          isRealtimeConnected={connected} 
        />

        {/* Main Container */}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          
          {/* Realtime Toast Notification */}
          {showToast && toastData && (
            <div 
              onClick={handleToastClick}
              className="animate-pulse-glow"
              style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                width: '320px',
                background: 'rgba(239, 68, 68, 0.95)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '12px',
                padding: '16px',
                color: '#fff',
                zIndex: 1000,
                cursor: 'pointer',
                boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', fontSize: '0.85rem' }}>
                  <ShieldAlert size={16} />
                  HIGH RISK ALERT
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); setShowToast(false); }}
                  style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
                >
                  <X size={14} />
                </button>
              </div>
              <strong style={{ fontSize: '0.9rem', display: 'block' }}>{toastData.title}</strong>
              <div style={{ fontSize: '0.75rem', opacity: 0.9 }}>
                Location: {toastData.location?.city || 'Unknown'} | Risk Score: {toastData.severity}
              </div>
            </div>
          )}

          {/* View Switch */}
          {activeView === 'dashboard' ? (
            /* Law Enforcement View */
            !isAuthenticated ? (
              <div style={{ height: '100%', overflow: 'hidden' }}>
                <Login />
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', height: '100%', padding: '20px', gap: '20px', overflow: 'hidden' }}>
              {/* Left Feed */}
              <div style={{ height: '100%', overflow: 'hidden' }}>
                <AlertFeed 
                  alerts={feed} 
                  onAlertClick={handleAlertClick} 
                  activeAlertId={activeAlert?.id}
                  isRealtimeConnected={connected}
                  markAsReadLocally={markAsReadLocally}
                />
              </div>

              {/* Main grid panels */}
              <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr', gap: '20px', height: '100%', overflow: 'hidden' }}>
                {/* Geospatial Map */}
                <div style={{ overflow: 'hidden' }}>
                  <GeospatialMap activeAlert={activeAlert} />
                </div>
                {/* Graph Visualizer */}
                <div style={{ overflow: 'hidden' }}>
                  <FraudNetworkGraph selectedCluster={null} />
                </div>
                </div>
              </div>
            )
          ) : (
            /* Citizen View */
            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', height: '100%', padding: '20px', gap: '20px', overflow: 'auto' }}>
              {/* Chatbot Column */}
              <div style={{ minHeight: '500px' }}>
                <CitizenChat />
              </div>
              
              {/* Counterfeit Checker Column */}
              <div style={{ minHeight: '500px' }}>
                <CurrencyChecker />
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

export default App;
