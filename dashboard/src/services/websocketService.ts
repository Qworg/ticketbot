import { WebSocketMessage } from '../types';

type EventHandler = (data: any) => void;
type ConnectionStateHandler = (connected: boolean) => void;

export interface WebSocketNotification {
  id: string;
  type: 'ticket_created' | 'ticket_updated' | 'message_added' | 'ticket_closed';
  title: string;
  message: string;
  timestamp: string;
  data?: any;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private eventHandlers: Map<string, EventHandler[]> = new Map();
  private connectionStateHandlers: ConnectionStateHandler[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnecting = false;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private lastHeartbeat: number = 0;
  private notifications: WebSocketNotification[] = [];

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return;
    }

    this.isConnecting = true;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    try {
      this.ws = new WebSocket(wsUrl);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        this.notifyConnectionState(true);
        this.startHeartbeat();
        
        // Request state synchronization after reconnection
        if (this.reconnectAttempts > 0) {
          this.requestStateSync();
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
          this.lastHeartbeat = Date.now();
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason);
        this.isConnecting = false;
        this.notifyConnectionState(false);
        this.stopHeartbeat();
        
        // Only reconnect if it wasn't a clean close
        if (event.code !== 1000) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
        this.notifyConnectionState(false);
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    this.eventHandlers.clear();
    this.connectionStateHandlers.length = 0;
    this.notifications.length = 0;
  }

  subscribe(eventType: string, handler: EventHandler): () => void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, []);
    }
    this.eventHandlers.get(eventType)!.push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.eventHandlers.get(eventType);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  subscribeToConnectionState(handler: ConnectionStateHandler): () => void {
    this.connectionStateHandlers.push(handler);
    
    // Immediately notify of current state
    handler(this.isConnected());
    
    return () => {
      const index = this.connectionStateHandlers.indexOf(handler);
      if (index > -1) {
        this.connectionStateHandlers.splice(index, 1);
      }
    };
  }

  getNotifications(): WebSocketNotification[] {
    return [...this.notifications];
  }

  clearNotifications(): void {
    this.notifications.length = 0;
  }

  markNotificationAsRead(id: string): void {
    const index = this.notifications.findIndex(n => n.id === id);
    if (index > -1) {
      this.notifications.splice(index, 1);
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    // Handle heartbeat/pong messages
    if (message.type === 'pong') {
      return;
    }

    // Create notification for certain message types
    this.createNotification(message);

    // Dispatch to event handlers
    const handlers = this.eventHandlers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.data);
        } catch (error) {
          console.error('Error in WebSocket event handler:', error);
        }
      });
    }
  }

  private createNotification(message: WebSocketMessage): void {
    let notification: WebSocketNotification | null = null;

    switch (message.type) {
      case 'ticket_created':
        notification = {
          id: `${message.type}-${message.data.id}-${Date.now()}`,
          type: 'ticket_created',
          title: 'New Ticket Created',
          message: `Ticket "${message.data.title}" has been created`,
          timestamp: message.timestamp,
          data: message.data,
        };
        break;
      
      case 'ticket_updated':
        notification = {
          id: `${message.type}-${message.data.id}-${Date.now()}`,
          type: 'ticket_updated',
          title: 'Ticket Updated',
          message: `Ticket "${message.data.title}" has been updated`,
          timestamp: message.timestamp,
          data: message.data,
        };
        break;
      
      case 'message_added':
        notification = {
          id: `${message.type}-${message.data.id}-${Date.now()}`,
          type: 'message_added',
          title: 'New Message',
          message: `New message in ticket`,
          timestamp: message.timestamp,
          data: message.data,
        };
        break;
      
      case 'ticket_closed':
        notification = {
          id: `${message.type}-${message.data.id}-${Date.now()}`,
          type: 'ticket_closed',
          title: 'Ticket Closed',
          message: `Ticket "${message.data.title}" has been closed`,
          timestamp: message.timestamp,
          data: message.data,
        };
        break;
    }

    if (notification) {
      this.notifications.unshift(notification);
      
      // Keep only the last 50 notifications
      if (this.notifications.length > 50) {
        this.notifications = this.notifications.slice(0, 50);
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      this.connect();
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.lastHeartbeat = Date.now();
    
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        // Send ping
        this.ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));
        
        // Check if we've received a recent heartbeat
        const now = Date.now();
        if (now - this.lastHeartbeat > 30000) { // 30 seconds timeout
          console.warn('WebSocket heartbeat timeout, reconnecting...');
          this.ws.close();
        }
      }
    }, 15000); // Send ping every 15 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private notifyConnectionState(connected: boolean): void {
    this.connectionStateHandlers.forEach(handler => {
      try {
        handler(connected);
      } catch (error) {
        console.error('Error in connection state handler:', error);
      }
    });
  }

  private requestStateSync(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ 
        type: 'request_sync', 
        timestamp: new Date().toISOString() 
      }));
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketService();
export default websocketService;