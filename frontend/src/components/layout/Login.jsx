// frontend/src/components/layout/Login.jsx
import React, { useState } from 'react';
import { Shield, Lock, Mail, Loader2 } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError('Invalid credentials. Please verify your clearance level.');
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100%',
      width: '100%',
      background: 'linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%)',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '420px',
        background: 'rgba(30, 41, 59, 0.7)',
        backdropFilter: 'blur(16px)',
        borderRadius: '24px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '40px 32px',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(79, 70, 229, 0.15)'
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '32px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)',
            padding: '16px',
            borderRadius: '50%',
            marginBottom: '20px',
            boxShadow: '0 0 30px rgba(79, 70, 229, 0.4)'
          }}>
            <Shield size={36} color="#ffffff" />
          </div>
          <h2 style={{ 
            color: '#f8fafc', 
            fontSize: '1.75rem', 
            fontWeight: '700',
            margin: '0 0 8px 0',
            textAlign: 'center'
          }}>
            Law Enforcement Portal
          </h2>
          <p style={{ color: '#94a3b8', margin: 0, textAlign: 'center', fontSize: '0.95rem' }}>
            Authorized personnel only. Please sign in to access the intelligence dashboard.
          </p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            borderLeft: '4px solid #ef4444',
            padding: '12px 16px',
            borderRadius: '0 8px 8px 0',
            marginBottom: '24px',
            color: '#fca5a5',
            fontSize: '0.9rem',
            fontWeight: '500'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ position: 'relative' }}>
            <Mail size={20} color="#64748b" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Official Email Address"
              required
              style={{
                width: '100%',
                padding: '14px 14px 14px 48px',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
                color: '#f8fafc',
                fontSize: '1rem',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'border-color 0.2s, box-shadow 0.2s'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#4f46e5';
                e.target.style.boxShadow = '0 0 0 2px rgba(79, 70, 229, 0.2)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          <div style={{ position: 'relative' }}>
            <Lock size={20} color="#64748b" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }} />
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              style={{
                width: '100%',
                padding: '14px 14px 14px 48px',
                background: 'rgba(15, 23, 42, 0.6)',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                borderRadius: '12px',
                color: '#f8fafc',
                fontSize: '1rem',
                outline: 'none',
                boxSizing: 'border-box',
                transition: 'border-color 0.2s, box-shadow 0.2s'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#4f46e5';
                e.target.style.boxShadow = '0 0 0 2px rgba(79, 70, 229, 0.2)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                e.target.style.boxShadow = 'none';
              }}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            style={{
              marginTop: '8px',
              padding: '16px',
              background: 'linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%)',
              color: '#ffffff',
              border: 'none',
              borderRadius: '12px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'transform 0.1s, box-shadow 0.2s',
              boxShadow: '0 10px 20px -5px rgba(79, 70, 229, 0.4)',
              opacity: isLoading ? 0.8 : 1
            }}
            onMouseOver={(e) => {
              if (!isLoading) {
                e.currentTarget.style.transform = 'translateY(-1px)';
                e.currentTarget.style.boxShadow = '0 12px 25px -5px rgba(79, 70, 229, 0.5)';
              }
            }}
            onMouseOut={(e) => {
              if (!isLoading) {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 10px 20px -5px rgba(79, 70, 229, 0.4)';
              }
            }}
          >
            {isLoading ? (
              <>
                <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
                Authenticating...
              </>
            ) : (
              'Access Dashboard'
            )}
          </button>
        </form>
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
