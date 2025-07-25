import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import TicketList from '../TicketList';
import { ticketService } from '../../services/ticketService';
import { TicketStatus, Priority } from '../../types';

// Mock the ticket service
vi.mock('../../services/ticketService');

// Mock react-router-dom
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockTickets = [
  {
    id: '1',
    discord_channel_id: 123456789,
    title: 'Test Ticket 1',
    description: 'This is a test ticket',
    status: TicketStatus.OPEN,
    priority: Priority.HIGH,
    creator_discord_id: 987654321,
    assigned_staff_id: 111222333,
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:30:00Z',
  },
  {
    id: '2',
    discord_channel_id: 123456790,
    title: 'Test Ticket 2',
    description: 'Another test ticket',
    status: TicketStatus.IN_PROGRESS,
    priority: Priority.MEDIUM,
    creator_discord_id: 987654322,
    created_at: '2024-01-02T09:00:00Z',
    updated_at: '2024-01-02T09:15:00Z',
  },
];

const mockPaginatedResponse = {
  data: mockTickets,
  total: 2,
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

describe('TicketList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ticketService.getTickets).mockResolvedValue(mockPaginatedResponse);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders the ticket list page title', async () => {
    renderTicketList();
    
    expect(screen.getByText('Tickets')).toBeInTheDocument();
  });

  it('displays loading state initially', () => {
    renderTicketList();
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('fetches and displays tickets', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
      expect(screen.getByText('Test Ticket 2')).toBeInTheDocument();
    });

    expect(ticketService.getTickets).toHaveBeenCalledWith({
      page: 1,
      per_page: 10,
      sort_by: 'created_at',
      sort_order: 'desc',
    });
  });

  it('displays ticket information correctly', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Check status chip
    expect(screen.getByText('OPEN')).toBeInTheDocument();
    
    // Check priority chip
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    
    // Check description truncation
    expect(screen.getByText('This is a test ticket')).toBeInTheDocument();
  });

  it('handles search functionality', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search by title or description...');
    fireEvent.change(searchInput, { target: { value: 'Test Ticket 1' } });

    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          search: 'Test Ticket 1',
          page: 1,
        })
      );
    });
  });

  it('handles status filter', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Get all comboboxes and select the first one (status filter)
    const comboboxes = screen.getAllByRole('combobox');
    const statusSelect = comboboxes[0]; // First combobox is status
    fireEvent.mouseDown(statusSelect);
    
    // Select OPEN status
    const openOption = screen.getByText('OPEN');
    fireEvent.click(openOption);

    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          status: [TicketStatus.OPEN],
          page: 1,
        })
      );
    });
  });

  it('handles priority filter', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Get all comboboxes and select the second one (priority filter)
    const comboboxes = screen.getAllByRole('combobox');
    const prioritySelect = comboboxes[1]; // Second combobox is priority
    fireEvent.mouseDown(prioritySelect);
    
    // Select HIGH priority
    const highOption = screen.getByText('HIGH');
    fireEvent.click(highOption);

    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          priority: [Priority.HIGH],
          page: 1,
        })
      );
    });
  });

  it('handles sorting', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Click on title column to sort
    const titleSortButton = screen.getByText('Title');
    fireEvent.click(titleSortButton);

    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          sort_by: 'title',
          sort_order: 'asc',
        })
      );
    });
  });

  it('handles pagination', async () => {
    const largeMockResponse = {
      ...mockPaginatedResponse,
      total: 25,
      total_pages: 3,
    };
    vi.mocked(ticketService.getTickets).mockResolvedValue(largeMockResponse);

    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Find and click next page button
    const nextPageButton = screen.getByLabelText('Go to next page');
    fireEvent.click(nextPageButton);

    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
        })
      );
    });
  });

  it('handles rows per page change', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Clear previous calls
    vi.clearAllMocks();

    // Change rows per page
    const rowsPerPageSelect = screen.getByDisplayValue('10');
    fireEvent.change(rowsPerPageSelect, { target: { value: '25' } });

    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          per_page: 25,
          page: 1, // Should reset to first page
        })
      );
    });
  });

  it('clears all filters', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    // Set some filters first
    const searchInput = screen.getByPlaceholderText('Search by title or description...');
    fireEvent.change(searchInput, { target: { value: 'test search' } });

    // Clear filters
    const clearButton = screen.getByLabelText('Clear all filters');
    fireEvent.click(clearButton);

    expect(searchInput).toHaveValue('');
    
    await waitFor(() => {
      expect(ticketService.getTickets).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          per_page: 10,
          sort_by: 'created_at',
          sort_order: 'desc',
        })
      );
    });
  });

  it('navigates to ticket detail when view button is clicked', async () => {
    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Test Ticket 1')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByLabelText('View ticket');
    fireEvent.click(viewButtons[0]);

    expect(mockNavigate).toHaveBeenCalledWith('/tickets/1');
  });

  it('displays error message when fetch fails', async () => {
    vi.mocked(ticketService.getTickets).mockRejectedValue(new Error('API Error'));

    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('Failed to fetch tickets. Please try again.')).toBeInTheDocument();
    });
  });

  it('displays no tickets message when list is empty', async () => {
    vi.mocked(ticketService.getTickets).mockResolvedValue({
      ...mockPaginatedResponse,
      data: [],
      total: 0,
    });

    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('No tickets found')).toBeInTheDocument();
    });
  });

  it('displays correct status colors', async () => {
    const ticketsWithDifferentStatuses = [
      { ...mockTickets[0], status: TicketStatus.OPEN },
      { ...mockTickets[1], status: TicketStatus.CLOSED, id: '3' },
    ];

    vi.mocked(ticketService.getTickets).mockResolvedValue({
      ...mockPaginatedResponse,
      data: ticketsWithDifferentStatuses,
    });

    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('OPEN')).toBeInTheDocument();
      expect(screen.getByText('CLOSED')).toBeInTheDocument();
    });
  });

  it('displays correct priority colors', async () => {
    const ticketsWithDifferentPriorities = [
      { ...mockTickets[0], priority: Priority.URGENT },
      { ...mockTickets[1], priority: Priority.LOW, id: '3' },
    ];

    vi.mocked(ticketService.getTickets).mockResolvedValue({
      ...mockPaginatedResponse,
      data: ticketsWithDifferentPriorities,
    });

    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText('URGENT')).toBeInTheDocument();
      expect(screen.getByText('LOW')).toBeInTheDocument();
    });
  });

  it('truncates long descriptions', async () => {
    const ticketWithLongDescription = {
      ...mockTickets[0],
      description: 'This is a very long description that should be truncated because it exceeds the maximum length allowed for display in the table',
    };

    vi.mocked(ticketService.getTickets).mockResolvedValue({
      ...mockPaginatedResponse,
      data: [ticketWithLongDescription],
    });

    renderTicketList();
    
    await waitFor(() => {
      expect(screen.getByText(/This is a very long description that should be.../)).toBeInTheDocument();
    });
  });
});