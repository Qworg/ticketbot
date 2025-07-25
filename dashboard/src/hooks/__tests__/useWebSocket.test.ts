import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useWebSocket } from '../useWebSocket';
import { websocketService } from '../../services/websocketService';

// Mock the websocketService
vi.mock('../../services/websocketService', () => ({
  websocketService: {
    connect: vi.fn(),
    disconnect: vi.fn(),
    subscribe: vi.fn(),
    subscribeToConnectionState: vi.fn(),
    getNotifications: vi.fn(),
    clearNotifications: vi.fn(),
    markNotificationAsRead: vi.fn(),
  },
}));

const mockWebSocketService = vi.mocked(websocketService);

describe('useWebSocket', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Setup default mock implementations
    mockWebSocketService.subscribe.mockReturnValue(() => {});
    mockWebSocketService.subscribeToConnectionState.mockReturnValue(() => {});
    mockWebSocketService.getNotifications.mockReturnValue([]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should connect to WebSocket on mount', () => {
    renderHook(() => useWebSocket());
    
    expect(mockWebSocketService.connect).toHaveBeenCalledTimes(1);
  });

  it('should disconnect from WebSocket on unmount', () => {
    const { unmount } = renderHook(() => useWebSocket());
    
    unmount();
    
    expect(mockWebSocketService.disconnect).toHaveBeenCalledTimes(1);
  });

  it('should subscribe to connection state changes', () => {
    renderHook(() => useWebSocket());
    
    expect(mockWebSocketService.subscribeToConnectionState).toHaveBeenCalledTimes(1);
    expect(mockWebSocketService.subscribeToConnectionState).toHaveBeenCalledWith(
      expect.any(Function)
    );
  });

  it('should subscribe to notification updates', () => {
    renderHook(() => useWebSocket());
    
    expect(mockWebSocketService.subscribe).toHaveBeenCalledWith(
      'notification_update',
      expect.any(Function)
    );
  });

  it('should load initial notifications', () => {
    const mockNotifications = [
      {
        id: '1',
        type: 'ticket_created' as const,
        title: 'New Ticket',
        message: 'A new ticket has been created',
        timestamp: new Date().toISOString(),
      },
    ];
    
    mockWebSocketService.getNotifications.mockReturnValue(mockNotifications);
    
    const { result } = renderHook(() => useWebSocket());
    
    expect(result.current.notifications).toEqual(mockNotifications);
  });

  it('should update connection state', () => {
    let connectionStateHandler: (connected: boolean) => void;
    
    mockWebSocketService.subscribeToConnectionState.mockImplementation((handler) => {
      connectionStateHandler = handler;
      return () => {};
    });
    
    const { result } = renderHook(() => useWebSocket());
    
    // Initially disconnected
    expect(result.current.isConnected).toBe(false);
    
    // Simulate connection
    act(() => {
      connectionStateHandler(true);
    });
    
    expect(result.current.isConnected).toBe(true);
    
    // Simulate disconnection
    act(() => {
      connectionStateHandler(false);
    });
    
    expect(result.current.isConnected).toBe(false);
  });

  it('should update notifications when notification_update event is received', () => {
    let notificationUpdateHandler: () => void;
    const initialNotifications = [
      {
        id: '1',
        type: 'ticket_created' as const,
        title: 'Initial Ticket',
        message: 'Initial notification',
        timestamp: new Date().toISOString(),
      },
    ];
    const updatedNotifications = [
      ...initialNotifications,
      {
        id: '2',
        type: 'ticket_updated' as const,
        title: 'Updated Ticket',
        message: 'Ticket has been updated',
        timestamp: new Date().toISOString(),
      },
    ];
    
    mockWebSocketService.getNotifications
      .mockReturnValueOnce(initialNotifications)
      .mockReturnValueOnce(updatedNotifications);
    
    mockWebSocketService.subscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'notification_update') {
        notificationUpdateHandler = handler;
      }
      return () => {};
    });
    
    const { result } = renderHook(() => useWebSocket());
    
    // Initial notifications
    expect(result.current.notifications).toEqual(initialNotifications);
    
    // Simulate notification update
    act(() => {
      notificationUpdateHandler();
    });
    
    expect(result.current.notifications).toEqual(updatedNotifications);
  });

  it('should provide subscribe function', () => {
    const { result } = renderHook(() => useWebSocket());
    
    expect(typeof result.current.subscribe).toBe('function');
    
    const mockHandler = vi.fn();
    result.current.subscribe('test_event', mockHandler);
    
    expect(mockWebSocketService.subscribe).toHaveBeenCalledWith('test_event', mockHandler);
  });

  it('should provide clearNotifications function', () => {
    const { result } = renderHook(() => useWebSocket());
    
    expect(typeof result.current.clearNotifications).toBe('function');
    
    act(() => {
      result.current.clearNotifications();
    });
    
    expect(mockWebSocketService.clearNotifications).toHaveBeenCalledTimes(1);
  });

  it('should provide markNotificationAsRead function', () => {
    const { result } = renderHook(() => useWebSocket());
    
    expect(typeof result.current.markNotificationAsRead).toBe('function');
    
    act(() => {
      result.current.markNotificationAsRead('notification-1');
    });
    
    expect(mockWebSocketService.markNotificationAsRead).toHaveBeenCalledWith('notification-1');
  });

  it('should update notifications after marking as read', () => {
    const initialNotifications = [
      {
        id: '1',
        type: 'ticket_created' as const,
        title: 'Test Ticket',
        message: 'Test notification',
        timestamp: new Date().toISOString(),
      },
    ];
    const updatedNotifications: any[] = [];
    
    mockWebSocketService.getNotifications
      .mockReturnValueOnce(initialNotifications)
      .mockReturnValueOnce(updatedNotifications);
    
    const { result } = renderHook(() => useWebSocket());
    
    expect(result.current.notifications).toEqual(initialNotifications);
    
    act(() => {
      result.current.markNotificationAsRead('1');
    });
    
    expect(result.current.notifications).toEqual(updatedNotifications);
  });

  it('should clean up subscriptions on unmount', () => {
    const unsubscribeConnectionState = vi.fn();
    const unsubscribeNotifications = vi.fn();
    
    mockWebSocketService.subscribeToConnectionState.mockReturnValue(unsubscribeConnectionState);
    mockWebSocketService.subscribe.mockReturnValue(unsubscribeNotifications);
    
    const { unmount } = renderHook(() => useWebSocket());
    
    unmount();
    
    expect(unsubscribeConnectionState).toHaveBeenCalledTimes(1);
    expect(unsubscribeNotifications).toHaveBeenCalledTimes(1);
    expect(mockWebSocketService.disconnect).toHaveBeenCalledTimes(1);
  });

  it('should handle multiple subscribe calls', () => {
    const { result } = renderHook(() => useWebSocket());
    
    const handler1 = vi.fn();
    const handler2 = vi.fn();
    
    result.current.subscribe('event1', handler1);
    result.current.subscribe('event2', handler2);
    
    expect(mockWebSocketService.subscribe).toHaveBeenCalledTimes(3); // 2 custom + 1 notification_update
    expect(mockWebSocketService.subscribe).toHaveBeenCalledWith('event1', handler1);
    expect(mockWebSocketService.subscribe).toHaveBeenCalledWith('event2', handler2);
  });

  it('should maintain stable function references', () => {
    const { result, rerender } = renderHook(() => useWebSocket());
    
    const initialSubscribe = result.current.subscribe;
    const initialClearNotifications = result.current.clearNotifications;
    const initialMarkNotificationAsRead = result.current.markNotificationAsRead;
    
    rerender();
    
    expect(result.current.subscribe).toBe(initialSubscribe);
    expect(result.current.clearNotifications).toBe(initialClearNotifications);
    expect(result.current.markNotificationAsRead).toBe(initialMarkNotificationAsRead);
  });
});