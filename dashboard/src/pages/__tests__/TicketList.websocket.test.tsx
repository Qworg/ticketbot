import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TicketList from '../TicketList';
import { ticketService } from '../../services/ticketService';
import { useWebSocket } from '../../hooks/useWebSocket';
import { TicketStatus, Priority } from '../../types';

// Mock services
vi.mock('../../services/ticketService');
vi.mock('../../hooks/useWebSocket');

const mockTicketService = vi.mocked(ticketService);
const mockUseWebSocket = vi.mocked(useWebSocket);

const mockTicket = {
  id: '1',
  discord_channel_id: 123456789,
  title: 'Test Ticket',
  description: 'Test description',
  status: TicketStatus.OPEN,
  priority: Priority.HIGH,
  creator_discord_id: 987654321,
  assigned_staff_id: 111222333,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T10:30:00Z',
};

const mockPaginatedResponse = {
  data: [mockTicket],
  total: 1,
  page: 1,
  per_page: 10,
  total_pages: 1,
};

const renderTicketList = () => {
  return render(
    <BrowserRouter>
      <TicketList />
    </BrowserRouter>
  );
};

describe('TicketList WebSocket Integration', () => {
  let mockSubscribe: ReturnType<typeof vi.fn>;
  let mockIsConnected: boolean;
  let mockNotifications: any[];
  let mockClearNotifications: ReturnType<typeof vi.fn>;
  let mockMarkNotificationAsRead: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    
    mockSubscribe = vi.fn().mockReturnValue(() => {});
    mockIsConnected = true;
    mockNotifications = [];
    mockClearNotifications = vi.fn();
    mockMarkNotificationAsRead = vi.fn();
    
    mockUseWebSocket.mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: mockIsConnected,
      notifications: mockNotifications,
      clearNotifications: mockClearNotifications,
      markNotificationAsRead: mockMarkNotificationAsRead,
    });
    
    mockTicketService.getTickets.mockResolvedValue(mockPaginatedResponse);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should display connection status indicator', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByTitle('Connected')).toBeInTheDocument();
    });
  });

  it('should display disconnected status when not connected', async () => {
    mockUseWebSocket.mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: false,
      notifications: mockNotifications,
      clearNotifications: mockClearNotifications,
      markNotificationAsRead: mockMarkNotificationAsRead,
    });
    
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByTitle('Disconnected')).toBeInTheDocument();
    });
  });

  it('should display notification count', async () => {
    const notifications = [
      {
        id: '1',
        type: 'ticket_created' as const,
        title: 'New Ticket',
        message: 'A new ticket has been created',
        timestamp: new Date().toISOString(),
      },
      {
        id: '2',
        type: 'ticket_updated' as const,
        title: 'Updated Ticket',
        message: 'A ticket has been updated',
        timestamp: new Date().toISOString(),
      },
    ];
    
    mockUseWebSocket.mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: mockIsConnected,
      notifications,
      clearNotifications: mockClearNotifications,
      markNotificationAsRead: mockMarkNotificationAsRead,
    });
    
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('2 notifications')).toBeInTheDocument();
    });
  });

  it('should subscribe to real-time events on mount', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith('ticket_created', expect.any(Function));
      expect(mockSubscribe).toHaveBeenCalledWith('ticket_updated', expect.any(Function));
      expect(mockSubscribe).toHaveBeenCalledWith('ticket_closed', expect.any(Function));
    });
  });

  it('should add new ticket when ticket_created event is received', async () => {
    let ticketCreatedHandler: (data: any) => void;
    
    mockSubscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'ticket_created') {
        ticketCreatedHandler = handler;
      }
      return () => {};
    });
    
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });
    
    const newTicket = {
      ...mockTicket,
      id: '2',
      title: 'New Real-time Ticket',
      created_at: new Date().toISOString(),
    };
    
    act(() => {
      ticketCreatedHandler(newTicket);
    });
    
    await waitFor(() => {
      expect(screen.getByText('New Real-time Ticket')).toBeInTheDocument();
    });
  });

  it('should update existing ticket when ticket_updated event is received', async () => {
    let ticketUpdatedHandler: (data: any) => void;
    
    mockSubscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'ticket_updated') {
        ticketUpdatedHandler = handler;
      }
      return () => {};
    });
    
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });
    
    const updatedTicket = {
      ...mockTicket,
      title: 'Updated Test Ticket',
      status: TicketStatus.IN_PROGRESS,
      updated_at: new Date().toISOString(),
    };
    
    act(() => {
      ticketUpdatedHandler(updatedTicket);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Updated Test Ticket')).toBeInTheDocument();
      expect(screen.getByText('IN PROGRESS')).toBeInTheDocument();
    });
  });

  it('should update ticket status when ticket_closed event is received', async () => {
    let ticketClosedHandler: (data: any) => void;
    
    mockSubscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'ticket_closed') {
        ticketClosedHandler = handler;
      }
      return () => {};
    });
    
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('OPEN')).toBeInTheDocument();
    });
    
    const closedTicket = {
      ...mockTicket,
      status: TicketStatus.CLOSED,
      closed_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    
    act(() => {
      ticketClosedHandler(closedTicket);
    });
    
    await waitFor(() => {
      expect(screen.getByText('CLOSED')).toBeInTheDocument();
    });
  });

  it('should show snackbar notification for real-time events', async () => {
    let ticketCreatedHandler: (data: any) => void;
    
    mockSubscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'ticket_created') {
        ticketCreatedHandler = handler;
      }
      return () => {};
    });
    
    renderTicketList();
    
    const newTicket = {
      ...mockTicket,
      id: '2',
      title: 'Notification Test Ticket',
    };
    
    act(() => {
      ticketCreatedHandler(newTicket);
    });
    
    await waitFor(() => {
      expect(screen.getByText('New ticket created: Notification Test Ticket')).toBeInTheDocument();
    });
  });

  it('should handle multiple real-time updates correctly', async () => {
    let ticketCreatedHandler: (data: any) => void;
    let ticketUpdatedHandler: (data: any) => void;
    
    mockSubscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'ticket_created') {
        ticketCreatedHandler = handler;
      } else if (eventType === 'ticket_updated') {
        ticketUpdatedHandler = handler;
      }
      return () => {};
    });
    
    renderTicketList();
    
    // Add new ticket
    const newTicket = {
      ...mockTicket,
      id: '2',
      title: 'Second Ticket',
    };
    
    act(() => {
      ticketCreatedHandler(newTicket);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Second Ticket')).toBeInTheDocument();
    });
    
    // Update existing ticket
    const updatedTicket = {
      ...mockTicket,
      title: 'Updated First Ticket',
      status: TicketStatus.CLOSED,
    };
    
    act(() => {
      ticketUpdatedHandler(updatedTicket);
    });
    
    await waitFor(() => {
      expect(screen.getByText('Updated First Ticket')).toBeInTheDocument();
      expect(screen.getByText('CLOSED')).toBeInTheDocument();
    });
  });

  it('should maintain ticket order when receiving real-time updates', async () => {
    let ticketCreatedHandler: (data: any) => void;
    
    mockSubscribe.mockImplementation((eventType, handler) => {
      if (eventType === 'ticket_created') {
        ticketCreatedHandler = handler;
      }
      return () => {};
    });
    
    renderTicketList();
    
    // Add new ticket (should appear at the top)
    const newTicket = {
      ...mockTicket,
      id: '2',
      title: 'Newer Ticket',
      created_at: new Date().toISOString(),
    };
    
    act(() => {
      ticketCreatedHandler(newTicket);
    });
    
    await waitFor(() => {
      const ticketRows = screen.getAllByRole('row');
      // Skip header row, check that newer ticket appears first
      expect(ticketRows[1]).toHaveTextContent('Newer Ticket');
      expect(ticketRows[2]).toHaveTextContent('Test Ticket');
    });
  });

  it('should handle WebSocket reconnection gracefully', async () => {
    // Start disconnected
    mockUseWebSocket.mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: false,
      notifications: mockNotifications,
      clearNotifications: mockClearNotifications,
      markNotificationAsRead: mockMarkNotificationAsRead,
    });
    
    const { rerender } = renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByTitle('Disconnected')).toBeInTheDocument();
    });
    
    // Simulate reconnection
    mockUseWebSocket.mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: true,
      notifications: mockNotifications,
      clearNotifications: mockClearNotifications,
      markNotificationAsRead: mockMarkNotificationAsRead,
    });
    
    rerender(
      <BrowserRouter>
        <TicketList />
      </BrowserRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByTitle('Connected')).toBeInTheDocument();
    });
  });

  it('should clean up subscriptions on unmount', () => {
    const unsubscribeFunctions = [vi.fn(), vi.fn(), vi.fn()];
    let callIndex = 0;
    
    mockSubscribe.mockImplementation(() => {
      return unsubscribeFunctions[callIndex++];
    });
    
    const { unmount } = renderTicketList();
    
    unmount();
    
    // All unsubscribe functions should have been called
    unsubscribeFunctions.forEach(unsubscribe => {
      expect(unsubscribe).toHaveBeenCalledTimes(1);
    });
  });
});