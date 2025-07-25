import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import TicketDetail from '../TicketDetail';
import { ticketService } from '../../services/ticketService';
import { messageService } from '../../services/messageService';
import { useWebSocket } from '../../hooks/useWebSocket';
import { Ticket, Message, TicketStatus, Priority, MessageType } from '../../types';

// Mock services
vi.mock('../../services/ticketService');
vi.mock('../../services/messageService');
vi.mock('../../hooks/useWebSocket');

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: () => ({ id: 'test-ticket-id' }),
    useNavigate: () => mockNavigate,
  };
});

const mockTicket: Ticket = {
  id: 'test-ticket-id',
  discord_channel_id: 123456789,
  title: 'Test Ticket',
  description: 'This is a test ticket',
  status: TicketStatus.OPEN,
  priority: Priority.MEDIUM,
  creator_discord_id: 987654321,
  assigned_staff_id: 111222333,
  created_at: '2024-01-01T10:00:00Z',
  updated_at: '2024-01-01T11:00:00Z',
};

const mockMessages: Message[] = [
  {
    id: 'msg-1',
    ticket_id: 'test-ticket-id',
    discord_message_id: 555666777,
    author_discord_id: 987654321,
    content: 'Hello, I need help with my account',
    message_type: MessageType.USER_MESSAGE,
    created_at: '2024-01-01T10:05:00Z',
  },
  {
    id: 'msg-2',
    ticket_id: 'test-ticket-id',
    discord_message_id: 555666778,
    author_discord_id: 111222333,
    content: 'Hi! I can help you with that. What seems to be the issue?',
    message_type: MessageType.STAFF_MESSAGE,
    created_at: '2024-01-01T10:10:00Z',
  },
];

const mockSubscribe = vi.fn(() => vi.fn());

describe('TicketDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    vi.mocked(useWebSocket).mockReturnValue({
      subscribe: mockSubscribe,
      isConnected: vi.fn(() => true),
    });

    vi.mocked(ticketService.getTicket).mockResolvedValue({
      data: mockTicket,
      success: true,
    });

    vi.mocked(messageService.getTicketMessages).mockResolvedValue({
      data: mockMessages,
      total: 2,
      page: 1,
      per_page: 100,
      total_pages: 1,
    });
  });

  const renderComponent = () => {
    return render(
      <BrowserRouter>
        <TicketDetail />
      </BrowserRouter>
    );
  };

  it('renders ticket details correctly', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    expect(screen.getByText('This is a test ticket')).toBeInTheDocument();
    expect(screen.getByText('User 987654321')).toBeInTheDocument();
    expect(screen.getByText('123456789')).toBeInTheDocument();
  });

  it('displays messages correctly', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Hello, I need help with my account')).toBeInTheDocument();
    });

    expect(screen.getByText('Hi! I can help you with that. What seems to be the issue?')).toBeInTheDocument();
    expect(screen.getAllByText(/User/)).toHaveLength(3); // 2 in messages + 1 in ticket info
  });

  it('shows loading state initially', () => {
    renderComponent();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('handles ticket loading error', async () => {
    vi.mocked(ticketService.getTicket).mockRejectedValue(new Error('API Error'));
    
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('allows sending new messages', async () => {
    const newMessage: Message = {
      id: 'msg-3',
      ticket_id: 'test-ticket-id',
      author_discord_id: 111222333,
      content: 'New test message',
      message_type: MessageType.STAFF_MESSAGE,
      created_at: '2024-01-01T10:15:00Z',
    };

    vi.mocked(messageService.addMessage).mockResolvedValue({
      data: newMessage,
      success: true,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    const messageInput = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(messageInput, { target: { value: 'New test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(messageService.addMessage).toHaveBeenCalledWith('test-ticket-id', 'New test message');
    });
  });

  it('allows updating ticket status', async () => {
    const updatedTicket = { ...mockTicket, status: TicketStatus.IN_PROGRESS };
    
    vi.mocked(ticketService.updateTicket).mockResolvedValue({
      data: updatedTicket,
      success: true,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    // Find and click the status select
    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);
    
    const inProgressOption = screen.getByText('IN_PROGRESS');
    fireEvent.click(inProgressOption);

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(ticketService.updateTicket).toHaveBeenCalledWith('test-ticket-id', {
        status: TicketStatus.IN_PROGRESS,
        priority: Priority.MEDIUM,
        assigned_staff_id: 111222333,
      });
    });
  });

  it('allows updating ticket priority', async () => {
    const updatedTicket = { ...mockTicket, priority: Priority.HIGH };
    
    vi.mocked(ticketService.updateTicket).mockResolvedValue({
      data: updatedTicket,
      success: true,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    // Find and click the priority select
    const prioritySelect = screen.getByLabelText('Priority');
    fireEvent.mouseDown(prioritySelect);
    
    const highOption = screen.getByText('HIGH');
    fireEvent.click(highOption);

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(ticketService.updateTicket).toHaveBeenCalledWith('test-ticket-id', {
        status: TicketStatus.OPEN,
        priority: Priority.HIGH,
        assigned_staff_id: 111222333,
      });
    });
  });

  it('allows updating assigned staff', async () => {
    const updatedTicket = { ...mockTicket, assigned_staff_id: 444555666 };
    
    vi.mocked(ticketService.updateTicket).mockResolvedValue({
      data: updatedTicket,
      success: true,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    // Find and update the staff ID field
    const staffInput = screen.getByLabelText('Assigned Staff ID');
    fireEvent.change(staffInput, { target: { value: '444555666' } });

    // Click save button
    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(ticketService.updateTicket).toHaveBeenCalledWith('test-ticket-id', {
        status: TicketStatus.OPEN,
        priority: Priority.MEDIUM,
        assigned_staff_id: 444555666,
      });
    });
  });

  it('disables message input for closed tickets', async () => {
    const closedTicket = { ...mockTicket, status: TicketStatus.CLOSED };
    
    vi.mocked(ticketService.getTicket).mockResolvedValue({
      data: closedTicket,
      success: true,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    const messageInput = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    expect(messageInput).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('disables ticket management for archived tickets', async () => {
    const archivedTicket = { ...mockTicket, status: TicketStatus.ARCHIVED };
    
    vi.mocked(ticketService.getTicket).mockResolvedValue({
      data: archivedTicket,
      success: true,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    const statusSelect = screen.getByLabelText('Status');
    const prioritySelect = screen.getByLabelText('Priority');
    const staffInput = screen.getByLabelText('Assigned Staff ID');
    const saveButton = screen.getByRole('button', { name: /save changes/i });

    expect(statusSelect).toBeDisabled();
    expect(prioritySelect).toBeDisabled();
    expect(staffInput).toBeDisabled();
    expect(saveButton).toBeDisabled();
  });

  it('sets up WebSocket subscriptions', async () => {
    renderComponent();

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith('ticket_updated', expect.any(Function));
      expect(mockSubscribe).toHaveBeenCalledWith('message_added', expect.any(Function));
    });
  });

  it('handles real-time ticket updates', async () => {
    const unsubscribe = vi.fn();
    mockSubscribe.mockReturnValue(unsubscribe);

    renderComponent();

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith('ticket_updated', expect.any(Function));
    });

    // Get the callback function passed to subscribe
    const ticketUpdateCallback = mockSubscribe.mock.calls.find(
      call => call[0] === 'ticket_updated'
    )?.[1];

    expect(ticketUpdateCallback).toBeDefined();

    // Simulate a ticket update
    const updatedTicket = { ...mockTicket, status: TicketStatus.IN_PROGRESS };
    ticketUpdateCallback(updatedTicket);

    await waitFor(() => {
      expect(screen.getByText('in_progress')).toBeInTheDocument();
    });
  });

  it('handles real-time message updates', async () => {
    const unsubscribe = vi.fn();
    mockSubscribe.mockReturnValue(unsubscribe);

    renderComponent();

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalledWith('message_added', expect.any(Function));
    });

    // Get the callback function passed to subscribe
    const messageAddedCallback = mockSubscribe.mock.calls.find(
      call => call[0] === 'message_added'
    )?.[1];

    expect(messageAddedCallback).toBeDefined();

    // Simulate a new message
    const newMessage: Message = {
      id: 'msg-3',
      ticket_id: 'test-ticket-id',
      author_discord_id: 111222333,
      content: 'Real-time message',
      message_type: MessageType.STAFF_MESSAGE,
      created_at: '2024-01-01T10:20:00Z',
    };

    messageAddedCallback(newMessage);

    await waitFor(() => {
      expect(screen.getByText('Real-time message')).toBeInTheDocument();
    });
  });

  it('navigates back to tickets list when breadcrumb is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    const backLink = screen.getByRole('button', { name: /tickets/i });
    fireEvent.click(backLink);

    expect(mockNavigate).toHaveBeenCalledWith('/tickets');
  });

  it('displays no messages message when there are no messages', async () => {
    vi.mocked(messageService.getTicketMessages).mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 100,
      total_pages: 1,
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('No messages yet. Start the conversation!')).toBeInTheDocument();
    });
  });

  it('handles message sending errors', async () => {
    vi.mocked(messageService.addMessage).mockRejectedValue(new Error('Send failed'));

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    const messageInput = screen.getByPlaceholderText('Type your message...');
    const sendButton = screen.getByRole('button', { name: /send/i });

    fireEvent.change(messageInput, { target: { value: 'Test message' } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText('Send failed')).toBeInTheDocument();
    });
  });

  it('handles ticket update errors', async () => {
    vi.mocked(ticketService.updateTicket).mockRejectedValue(new Error('Update failed'));

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Test Ticket')).toBeInTheDocument();
    });

    // Change status and try to save
    const statusSelect = screen.getByLabelText('Status');
    fireEvent.mouseDown(statusSelect);
    
    const inProgressOption = screen.getByText('IN_PROGRESS');
    fireEvent.click(inProgressOption);

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Update failed')).toBeInTheDocument();
    });
  });
});