/**
 * Integration tests for dashboard components with API and WebSocket integration.
 * Tests complete user workflows and real-time synchronization.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { act } from 'react';

import App from '../../App';
import { TicketList } from '../../pages/TicketList';
import { TicketDetail } from '../../pages/TicketDetail';
import { TranscriptSearch } from '../../pages/TranscriptSearch';
import * as ticketService from '../../services/ticketService';
import * as websocketService from '../../services/websocketService';
import * as api from '../../services/api';

// Mock services
vi.mock('../../services/ticketService');
vi.mock('../../services/websocketService');
vi.mock('../../services/api');

const mockTicketService = vi.mocked(ticketService);
const mockWebSocketService = vi.mocked(websocketService);
const mockApi = vi.mocked(api);

// Test data
const mockTickets = [
  {
    id: 'ticket-1',
    title: 'Integration Test Ticket 1',
    description: 'Testing integration',
    status: 'open',
    priority: 'high',
    creator_discord_id: 111222333,
    assigned_staff_id: null,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z',
    messages: []
  },
  {
    id: 'ticket-2',
    title: 'Integration Test Ticket 2',
    description: 'Testing integration 2',
    status: 'in_progress',
    priority: 'medium',
    creator_discord_id: 111222334,
    assigned_staff_id: 444555666,
    created_at: '2024-01-01T11:00:00Z',
    updated_at: '2024-01-01T11:00:00Z',
    messages: []
  }
];

const mockMessages = [
  {
    id: 'msg-1',
    ticket_id: 'ticket-1',
    author_discord_id: 111222333,
    content: 'Hello, I need help',
    message_type: 'user_message',
    created_at: '2024-01-01T10:01:00Z'
  },
  {
    id: 'msg-2',
    ticket_id: 'ticket-1',
    author_discord_id: 444555666,
    content: 'Hi! How can I help you?',
    message_type: 'staff_message',
    created_at: '2024-01-01T10:02:00Z'
  }
];

describe('Dashboard Integration Tests', () => {
  let mockWebSocket: any;
  let user: ReturnType<typeof userEvent.setup>;

  beforeEach(() => {
    user = userEvent.setup();
    
    // Mock WebSocket
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      readyState: WebSocket.OPEN
    };

    // Setup service mocks
    mockTicketService.getTickets.mockResolvedValue({
      tickets: mockTickets,
      pagination: { page: 1, limit: 10, total: 2, pages: 1 }
    });

    mockTicketService.getTicket.mockImplementation((id) => 
      Promise.resolve(mockTickets.find(t => t.id === id))
    );

    mockWebSocketService.connect.mockReturnValue(mockWebSocket);
    mockWebSocketService.disconnect.mockImplementation(() => {});
    mockWebSocketService.subscribe.mockImplementation(() => () => {});

    mockApi.get.mockImplementation((url) => {
      if (url.includes('/tickets')) {
        return Promise.resolve({ data: { tickets: mockTickets, pagination: { page: 1, limit: 10, total: 2, pages: 1 } } });
      }
      return Promise.resolve({ data: {} });
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Ticket List Integration', () => {
    it('should load and display tickets from API', async () => {
      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      // Wait for tickets to load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
        expect(screen.getByText('Integration Test Ticket 2')).toBeInTheDocument();
      });

      // Verify API was called
      expect(mockTicketService.getTickets).toHaveBeenCalledWith({
        page: 1,
        limit: 10
      });
    });

    it('should filter tickets by status', async () => {
      mockTicketService.getTickets.mockResolvedValueOnce({
        tickets: [mockTickets[1]], // Only in_progress ticket
        pagination: { page: 1, limit: 10, total: 1, pages: 1 }
      });

      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      // Find and click status filter
      const statusFilter = screen.getByLabelText(/status/i);
      await user.selectOptions(statusFilter, 'in_progress');

      // Wait for filtered results
      await waitFor(() => {
        expect(mockTicketService.getTickets).toHaveBeenCalledWith({
          page: 1,
          limit: 10,
          status: 'in_progress'
        });
      });
    });

    it('should handle real-time ticket updates via WebSocket', async () => {
      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
      });

      // Simulate WebSocket message for new ticket
      const newTicket = {
        id: 'ticket-3',
        title: 'New Real-time Ticket',
        status: 'open',
        priority: 'low',
        created_at: '2024-01-01T12:00:00Z'
      };

      // Mock WebSocket subscription callback
      const subscribeCall = mockWebSocketService.subscribe.mock.calls.find(
        call => call[0] === 'ticket_created'
      );
      
      if (subscribeCall) {
        const callback = subscribeCall[1];
        act(() => {
          callback(newTicket);
        });

        await waitFor(() => {
          expect(screen.getByText('New Real-time Ticket')).toBeInTheDocument();
        });
      }
    });
  });

  describe('Ticket Detail Integration', () => {
    it('should load ticket details and messages', async () => {
      const ticketWithMessages = {
        ...mockTickets[0],
        messages: mockMessages
      };

      mockTicketService.getTicket.mockResolvedValue(ticketWithMessages);

      render(
        <BrowserRouter>
          <TicketDetail ticketId="ticket-1" />
        </BrowserRouter>
      );

      // Wait for ticket details to load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
        expect(screen.getByText('Hello, I need help')).toBeInTheDocument();
        expect(screen.getByText('Hi! How can I help you?')).toBeInTheDocument();
      });

      expect(mockTicketService.getTicket).toHaveBeenCalledWith('ticket-1');
    });

    it('should send new message and update UI', async () => {
      const ticketWithMessages = {
        ...mockTickets[0],
        messages: mockMessages
      };

      mockTicketService.getTicket.mockResolvedValue(ticketWithMessages);
      mockTicketService.addMessage.mockResolvedValue({
        id: 'msg-3',
        ticket_id: 'ticket-1',
        author_discord_id: 444555666,
        content: 'New message from staff',
        message_type: 'staff_message',
        created_at: '2024-01-01T10:03:00Z'
      });

      render(
        <BrowserRouter>
          <TicketDetail ticketId="ticket-1" />
        </BrowserRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
      });

      // Find message input and send button
      const messageInput = screen.getByPlaceholderText(/type your message/i);
      const sendButton = screen.getByRole('button', { name: /send/i });

      // Type and send message
      await user.type(messageInput, 'New message from staff');
      await user.click(sendButton);

      // Verify message was sent
      await waitFor(() => {
        expect(mockTicketService.addMessage).toHaveBeenCalledWith('ticket-1', {
          content: 'New message from staff',
          message_type: 'staff_message'
        });
      });
    });

    it('should update ticket status', async () => {
      mockTicketService.getTicket.mockResolvedValue(mockTickets[0]);
      mockTicketService.updateTicket.mockResolvedValue({
        ...mockTickets[0],
        status: 'in_progress'
      });

      render(
        <BrowserRouter>
          <TicketDetail ticketId="ticket-1" />
        </BrowserRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
      });

      // Find status dropdown
      const statusSelect = screen.getByLabelText(/status/i);
      await user.selectOptions(statusSelect, 'in_progress');

      // Verify status update was called
      await waitFor(() => {
        expect(mockTicketService.updateTicket).toHaveBeenCalledWith('ticket-1', {
          status: 'in_progress'
        });
      });
    });

    it('should handle real-time message updates', async () => {
      const ticketWithMessages = {
        ...mockTickets[0],
        messages: mockMessages
      };

      mockTicketService.getTicket.mockResolvedValue(ticketWithMessages);

      render(
        <BrowserRouter>
          <TicketDetail ticketId="ticket-1" />
        </BrowserRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Hello, I need help')).toBeInTheDocument();
      });

      // Simulate WebSocket message for new message
      const newMessage = {
        id: 'msg-3',
        ticket_id: 'ticket-1',
        author_discord_id: 111222333,
        content: 'Real-time message update',
        message_type: 'user_message',
        created_at: '2024-01-01T10:03:00Z'
      };

      // Mock WebSocket subscription callback
      const subscribeCall = mockWebSocketService.subscribe.mock.calls.find(
        call => call[0] === 'message_added'
      );
      
      if (subscribeCall) {
        const callback = subscribeCall[1];
        act(() => {
          callback(newMessage);
        });

        await waitFor(() => {
          expect(screen.getByText('Real-time message update')).toBeInTheDocument();
        });
      }
    });
  });

  describe('Transcript Search Integration', () => {
    const mockSearchResults = [
      {
        id: 'transcript-1',
        ticket_id: 'ticket-1',
        ticket_title: 'Integration Test Ticket 1',
        content: 'Hello, I need help with my account',
        created_at: '2024-01-01T10:00:00Z',
        highlight: 'Hello, I need <mark>help</mark> with my account'
      }
    ];

    it('should search transcripts and display results', async () => {
      mockTicketService.searchTranscripts.mockResolvedValue({
        results: mockSearchResults,
        pagination: { page: 1, limit: 10, total: 1, pages: 1 }
      });

      render(
        <BrowserRouter>
          <TranscriptSearch />
        </BrowserRouter>
      );

      // Find search input and button
      const searchInput = screen.getByPlaceholderText(/search transcripts/i);
      const searchButton = screen.getByRole('button', { name: /search/i });

      // Perform search
      await user.type(searchInput, 'help');
      await user.click(searchButton);

      // Wait for results
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
        expect(mockTicketService.searchTranscripts).toHaveBeenCalledWith({
          query: 'help',
          page: 1,
          limit: 10
        });
      });
    });

    it('should filter search results by date range', async () => {
      mockTicketService.searchTranscripts.mockResolvedValue({
        results: mockSearchResults,
        pagination: { page: 1, limit: 10, total: 1, pages: 1 }
      });

      render(
        <BrowserRouter>
          <TranscriptSearch />
        </BrowserRouter>
      );

      // Find date filters
      const startDateInput = screen.getByLabelText(/start date/i);
      const endDateInput = screen.getByLabelText(/end date/i);
      const searchButton = screen.getByRole('button', { name: /search/i });

      // Set date range
      await user.type(startDateInput, '2024-01-01');
      await user.type(endDateInput, '2024-01-02');
      await user.click(searchButton);

      // Verify search with date filters
      await waitFor(() => {
        expect(mockTicketService.searchTranscripts).toHaveBeenCalledWith({
          query: '',
          page: 1,
          limit: 10,
          start_date: '2024-01-01',
          end_date: '2024-01-02'
        });
      });
    });
  });

  describe('WebSocket Connection Management', () => {
    it('should handle WebSocket connection and reconnection', async () => {
      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      // Verify WebSocket connection was established
      expect(mockWebSocketService.connect).toHaveBeenCalled();

      // Simulate connection loss
      const connectionLostEvent = new Event('close');
      mockWebSocket.addEventListener.mock.calls.forEach(([event, callback]) => {
        if (event === 'close') {
          callback(connectionLostEvent);
        }
      });

      // Verify reconnection attempt
      await waitFor(() => {
        expect(mockWebSocketService.connect).toHaveBeenCalledTimes(2);
      });
    });

    it('should handle WebSocket errors gracefully', async () => {
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(
        <BrowserRouter>
          <App />
        </BrowserRouter>
      );

      // Simulate WebSocket error
      const errorEvent = new Event('error');
      mockWebSocket.addEventListener.mock.calls.forEach(([event, callback]) => {
        if (event === 'error') {
          callback(errorEvent);
        }
      });

      // Verify error was logged
      await waitFor(() => {
        expect(consoleSpy).toHaveBeenCalled();
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Error Handling Integration', () => {
    it('should handle API errors gracefully', async () => {
      mockTicketService.getTickets.mockRejectedValue(new Error('API Error'));

      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      // Wait for error handling
      await waitFor(() => {
        expect(screen.getByText(/error loading tickets/i)).toBeInTheDocument();
      });
    });

    it('should handle network connectivity issues', async () => {
      mockTicketService.getTickets.mockRejectedValue(new Error('Network Error'));

      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      // Wait for network error handling
      await waitFor(() => {
        expect(screen.getByText(/connection error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Performance Integration', () => {
    it('should handle large ticket lists efficiently', async () => {
      const largeTicketList = Array.from({ length: 100 }, (_, i) => ({
        ...mockTickets[0],
        id: `ticket-${i}`,
        title: `Ticket ${i}`
      }));

      mockTicketService.getTickets.mockResolvedValue({
        tickets: largeTicketList,
        pagination: { page: 1, limit: 100, total: 100, pages: 1 }
      });

      const startTime = performance.now();

      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText('Ticket 0')).toBeInTheDocument();
      });

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Ensure rendering completes within reasonable time (2 seconds)
      expect(renderTime).toBeLessThan(2000);
    });

    it('should handle rapid WebSocket updates efficiently', async () => {
      render(
        <BrowserRouter>
          <TicketList />
        </BrowserRouter>
      );

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Integration Test Ticket 1')).toBeInTheDocument();
      });

      // Simulate rapid WebSocket updates
      const subscribeCall = mockWebSocketService.subscribe.mock.calls.find(
        call => call[0] === 'ticket_updated'
      );

      if (subscribeCall) {
        const callback = subscribeCall[1];
        
        // Send 10 rapid updates
        for (let i = 0; i < 10; i++) {
          act(() => {
            callback({
              id: 'ticket-1',
              title: `Updated Ticket ${i}`,
              status: 'in_progress'
            });
          });
        }

        // Verify final state is correct
        await waitFor(() => {
          expect(screen.getByText('Updated Ticket 9')).toBeInTheDocument();
        });
      }
    });
  });
});