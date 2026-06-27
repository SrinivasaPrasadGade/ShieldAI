// frontend/src/hooks/useSocket.js
import { useEffect, useRef, useState } from 'react';
import { io } from 'socket.io-client';

const SOCKET_URL = import.meta.env.VITE_REALTIME_URL || 'http://localhost:5001';

export const useSocket = (role = 'law_enforcement') => {
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [alerts, setAlerts] = useState([]);
  const [feed, setFeed] = useState([]);
  const [latestToast, setLatestToast] = useState(null);

  useEffect(() => {
    console.log(`Connecting to Socket.io server at: ${SOCKET_URL}`);
    const socket = io(SOCKET_URL, {
      transports: ['websocket'],
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('Socket.io connected successfully:', socket.id);
      setConnected(true);
      socket.emit('join_dashboard', { role });
    });

    socket.on('disconnect', () => {
      console.log('Socket.io disconnected');
      setConnected(false);
    });

    socket.on('joined', (data) => {
      console.log('Joined Socket room:', data);
    });

    socket.on('historical_alerts', (data) => {
      console.log('Received historical alerts:', data.alerts);
      setAlerts(data.alerts);
      setFeed(data.alerts);
    });

    socket.on('new_alert', (alert) => {
      console.log('🚨 NEW CRITICAL/HIGH ALERT RECEIVED:', alert);
      setAlerts((prev) => [alert, ...prev]);
      setLatestToast(alert);
    });

    socket.on('alert_feed_update', (alert) => {
      console.log('New alert feed update:', alert);
      setFeed((prev) => [alert, ...prev]);
    });

    return () => {
      if (socket) {
        socket.disconnect();
      }
    };
  }, [role]);

  return {
    socket: socketRef.current,
    connected,
    alerts,
    feed,
    latestToast,
    setLatestToast,
  };
};
export default useSocket;
