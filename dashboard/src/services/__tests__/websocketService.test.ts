import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { websocketService } from '../websocketService';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(public url: string) {
    // Store reference for test access
    (global as any).mockWebSocketInstance = this;
  }

  send(data: string) {
    // Mock send implementation
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code: code || 1000, reason }));
    }
  }

  // Helper method to simulate connection opening
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  // Helper method to simulate receiving messages
  simulateMessage(data: any) {
    if (this.onmessage && this.readyState === MockWebSocket.OPEN) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  // Helper method to simulate connection close
  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason }));
    }
  }
}

// Mock global WebSocket
global.WebSocket = MockWebSocket as any;

describe('WebSocketService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useFakeTimers();
    
    // Disconnect any existing connection
    websocketService.disconnect();
    
    // Clear the mock instance reference
    (global as any).mockWebSocketInstance = null;
  });

  afterEach(() => {
    vi.useRealTimers();
    websocketService.disconnect();
  });

  describe('connect', () => {
    it('should establish WebSocket connection', () => {
      websocketService.connect();
      
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      expect(mockWs).toBeTruthy();
      
      // Simulate connection opening
      mockWs.simulateOpen();
      
      expect(websocketService.isConnected()).toBe(true);
    });

    it('should use correct WebSocket URL', () => {
      // Mock window.location
      Object.defineProperty(window, 'location', {
        value: { host: 'localhost:3000', protocol: 'http:' },
        writable: true,
      });

      websocketService.connect();
      
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      expect(mockWs.url).toBe('ws://localhost:3000/ws');
    });
  });

  describe('disconnect', () => {
    it('should close WebSocket connection', () => {
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      expect(websocketService.isConnected()).toBe(true);
      
      websocketService.disconnect();
      
      expect(websocketService.isConnected()).toBe(false);
    });
  });

  describe('subscribe', () => {
    it('should register event handler', () => {
      const handler = vi.fn();
      websocketService.subscribe('ticket_created', handler);
      
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      const testData = { id: '1', title: 'Test Ticket' };
      mockWs.simulateMessage({ 
        type: 'ticket_created', 
        data: testData, 
        timestamp: new Date().toISOString() 
      });
      
      expect(handler).toHaveBeenCalledWith(testData);
    });

    it('should return unsubscribe function', () => {
      const handler = vi.fn();
      const unsubscribe = websocketService.subscribe('ticket_created', handler);
      
      expect(typeof unsubscribe).toBe('function');
      
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      // Unsubscribe and verify handler is not called
      unsubscribe();
      
      mockWs.simulateMessage({ 
        type: 'ticket_created', 
        data: { id: '1' }, 
        timestamp: new Date().toISOString() 
      });
      
      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('subscribeToConnectionState', () => {
    it('should notify of connection state changes', () => {
      const handler = vi.fn();
      websocketService.subscribeToConnectionState(handler);
      
      // Should immediately notify of current state (disconnected)
      expect(handler).toHaveBeenCalledWith(false);
      
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      // Should notify when connected
      expect(handler).toHaveBeenCalledWith(true);
    });

    it('should return unsubscribe function', () => {
      const handler = vi.fn();
      const unsubscribe = websocketService.subscribeToConnectionState(handler);
      
      expect(typeof unsubscribe).toBe('function');
      
      handler.mockClear();
      unsubscribe();
      
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      // Handler should not be called after unsubscribe (except initial call)
      expect(handler).toHaveBeenCalledTimes(0);
    });
  });

  describe('notifications', () => {
    it('should create notifications for ticket events', () => {
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      mockWs.simulateMessage({
        type: 'ticket_created',
        data: { id: '1', title: 'New Ticket' },
        timestamp: new Date().toISOString()
      });
      
      const notifications = websocketService.getNotifications();
      expect(notifications).toHaveLength(1);
      expect(notifications[0].type).toBe('ticket_created');
      expect(notifications[0].title).toBe('New Ticket Created');
    });

    it('should clear all notifications', () => {
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      mockWs.simulateMessage({
        type: 'ticket_created',
        data: { id: '1', title: 'New Ticket' },
        timestamp: new Date().toISOString()
      });
      
      expect(websocketService.getNotifications()).toHaveLength(1);
      
      websocketService.clearNotifications();
      
      expect(websocketService.getNotifications()).toHaveLength(0);
    });
  });

  describe('error handling', () => {
    it('should handle JSON parse errors gracefully', () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      
      websocketService.connect();
      const mockWs = (global as any).mockWebSocketInstance as MockWebSocket;
      mockWs.simulateOpen();
      
      // Simulate invalid JSON message
      if (mockWs.onmessage) {
        mockWs.onmessage(new MessageEvent('message', { data: 'invalid json' }));
      }
      
      expect(consoleSpy).toHaveBeenCalledWith(
        'Failed to parse WebSocket message:',
        expect.any(Error)
      );
      
      consoleSpy.mockRestore();
    });
  });
});