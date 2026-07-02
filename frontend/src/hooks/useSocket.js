// frontend/src/hooks/useSocket.js
import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = import.meta.env.VITE_REALTIME_URL || 'http://localhost:5001';
const REALTIME_TOKEN = import.meta.env.VITE_REALTIME_AUTH_TOKEN || '';

export const useSocket = (role = 'law_enforcement') => {
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [feed, setFeed] = useState([]);
  const [latestToast, setLatestToast] = useState(null);

  useEffect(() => {
    const socket = io(SOCKET_URL, {
      transports: ['websocket'],
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      query: { token: REALTIME_TOKEN },
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setConnected(true);
      socket.emit('join_dashboard', { role });
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    socket.on('historical_alerts', (data) => {
      setAlerts(data.alerts);
      setFeed(data.alerts);
    });

    socket.on('new_alert', (alert) => {
      setAlerts((prev) => {
        if (prev.some(a => a.id === alert.id)) return prev;
        return [alert, ...prev].slice(0, 500);
      });
      setLatestToast({ ...alert, _ts: Date.now() });
    });

    socket.on('alert_feed_update', (alert) => {
      setFeed((prev) => {
        if (prev.some(a => a.id === alert.id)) return prev;
        return [alert, ...prev].slice(0, 500);
      });
    });

    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, [role]);

  const markAsReadLocally = (alertId) => {
    setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a));
    setFeed(prev => prev.map(a => a.id === alertId ? { ...a, is_read: true } : a));
  };

  return {
    socket: socketRef.current,
    connected,
    alerts,
    feed,
    latestToast,
    setLatestToast,
    markAsReadLocally,
  };
};
export default useSocket;
