import { useEffect, useCallback, useState } from 'react';
import { websocketService, WebSocketNotification } from '../services/websocketService';

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [notifications, setNotifications] = useState<WebSocketNotification[]>([]);

  useEffect(() => {
    websocketService.connect();
    
    // Subscribe to connection state changes
    const unsubscribeConnectionState = websocketService.subscribeToConnectionState(setIsConnected);
    
    // Subscribe to notification updates
    const unsubscribeNotifications = websocketService.subscribe('notification_update', () => {
      setNotifications(websocketService.getNotifications());
    });
    
    // Initial notification load
    setNotifications(websocketService.getNotifications());
    
    return () => {
      unsubscribeConnectionState();
      unsubscribeNotifications();
      websocketService.disconnect();
    };
  }, []);

  const subscribe = useCallback((eventType: string, handler: (data: any) => void) => {
    return websocketService.subscribe(eventType, handler);
  }, []);

  const clearNotifications = useCallback(() => {
    websocketService.clearNotifications();
    setNotifications([]);
  }, []);

  const markNotificationAsRead = useCallback((id: string) => {
    websocketService.markNotificationAsRead(id);
    setNotifications(websocketService.getNotifications());
  }, []);

  return { 
    subscribe, 
    isConnected, 
    notifications, 
    clearNotifications, 
    markNotificationAsRead 
  };
};