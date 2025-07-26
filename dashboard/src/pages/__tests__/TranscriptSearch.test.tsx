import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import TranscriptSearch from '../TranscriptSearch';
import { transcriptService } from '../../services/transcriptService';
import { TicketStatus } from '../../types';

// Mock the transcript service
vi.mock('../../services/transcriptService', () => ({
  transcriptService: {
    searchTranscripts: vi.fn(),
  },
}));

const mockSearchResponse = {
  data: [
    {
      id: '1',
      ticket_id: 'ticket-1',
      ticket_title: 'Login Issue',
      content: 'User having trouble logging in to the dashboard',
      created_at: '2024-01-15T10:00:00Z',
      updated_at: '2024-01-15T10:30:00Z',
      context_snippets: [
        'User having trouble <mark>logging</mark> in to the dashboard',
        'Please check your <mark>login</mark> credentials'
      ],
      relevance_score: 0.85
    },
    {
      id: '2',
      ticket_id: 'ticket-2',
      ticket_title: 'Password Reset',
      content: 'User needs password reset assistance',
      created_at: '2024-01-14T15:30:00Z',
      updated_at: '2024-01-14T16:00:00Z',
      context_snippets: [
        'User needs <mark>password</mark> reset assistance'
      ],
      relevance_score: 0.72,
      share_token: 'abc123'
    }
  ],
  total: 2,
  page: 1,
  size: 10,
  total_pages: 1,
  search_term: 'login',
  search_mode: 'basic'
};

describe('TranscriptSearch', () => {
  const user = userEvent.setup();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders initial search interface', () => {
    render(<TranscriptSearch />);
    
    expect(screen.getByText('Search Transcripts')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter keywords to search in ticket conversations')).toBeInTheDocument();
    expect(screen.getByTestId('search-button')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /filters/i })).toBeInTheDocument();
    expect(screen.getByText('Search Ticket Transcripts')).toBeInTheDocument();
  });

  it('performs basic search when search button is clicked', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    const searchButton = screen.getByTestId('search-button');
    
    await user.type(searchInput, 'login');
    await user.click(searchButton);
    
    await waitFor(() => {
      expect(transcriptService.searchTranscripts).toHaveBeenCalledWith({
        search: 'login',
        search_mode: 'basic',
        highlight_results: true,
        page: 1,
        size: 10
      });
    });
  });

  it('performs search when Enter key is pressed', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(transcriptService.searchTranscripts).toHaveBeenCalled();
    });
  });

  it('displays search results correctly', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText('Search Results (2 found)')).toBeInTheDocument();
      expect(screen.getByText('Login Issue')).toBeInTheDocument();
      expect(screen.getByText('Password Reset')).toBeInTheDocument();
      expect(screen.getByText(/ticket-1/)).toBeInTheDocument();
      expect(screen.getByText('Relevance: 85%')).toBeInTheDocument();
    });
  });

  it('displays highlighted content snippets', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getAllByText('Matching Content:')[0]).toBeInTheDocument();
      // Check that highlighted content is rendered (contains HTML)
      const highlightedElements = screen.getAllByText(/logging|login/i);
      expect(highlightedElements.length).toBeGreaterThan(0);
    });
  });

  it('shows and hides advanced filters', async () => {
    render(<TranscriptSearch />);
    
    const filtersButton = screen.getByRole('button', { name: /filters/i });
    
    // Initially, advanced filters should not be visible
    expect(screen.queryByRole('combobox', { name: /search mode/i })).not.toBeInTheDocument();
    
    // Click to show filters
    await user.click(filtersButton);
    
    await waitFor(() => {
      expect(screen.getByRole('combobox', { name: /search mode/i })).toBeInTheDocument();
      expect(screen.getByLabelText('Created After')).toBeInTheDocument();
      expect(screen.getByLabelText('Created Before')).toBeInTheDocument();
      expect(screen.getByRole('combobox', { name: /ticket status/i })).toBeInTheDocument();
    });
  });

  it('applies advanced filters in search', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    const filtersButton = screen.getByRole('button', { name: /filters/i });
    
    await user.type(searchInput, 'login');
    await user.click(filtersButton);
    
    // Set search mode to fuzzy
    const searchModeSelect = screen.getByRole('combobox', { name: /search mode/i });
    await user.click(searchModeSelect);
    await user.click(screen.getByText('Fuzzy'));
    
    // Set date filter
    const createdAfterInput = screen.getByLabelText('Created After');
    await user.type(createdAfterInput, '2024-01-01');
    
    // Set status filter
    const statusSelect = screen.getByRole('combobox', { name: /ticket status/i });
    await user.click(statusSelect);
    await user.click(screen.getByText('Open'));
    
    const searchButton = screen.getByTestId('search-button');
    await user.click(searchButton);
    
    await waitFor(() => {
      expect(transcriptService.searchTranscripts).toHaveBeenCalledWith({
        search: 'login',
        search_mode: 'fuzzy',
        highlight_results: true,
        page: 1,
        size: 10,
        created_after: '2024-01-01',
        status: TicketStatus.OPEN
      });
    });
  });

  it('clears filters when clear button is clicked', async () => {
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    const filtersButton = screen.getByRole('button', { name: /filters/i });
    
    await user.type(searchInput, 'test search');
    await user.click(filtersButton);
    
    const clearButton = screen.getByRole('button', { name: /clear filters/i });
    await user.click(clearButton);
    
    expect(searchInput).toHaveValue('');
  });

  it('handles pagination correctly', async () => {
    const paginatedResponse = {
      ...mockSearchResponse,
      total: 25,
      total_pages: 3,
      page: 1
    };
    
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(paginatedResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument();
    });
    
    // Mock second page response
    const page2Response = { ...paginatedResponse, page: 2 };
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(page2Response);
    
    // Click page 2
    const page2Button = screen.getByRole('button', { name: 'Go to page 2' });
    await user.click(page2Button);
    
    await waitFor(() => {
      expect(transcriptService.searchTranscripts).toHaveBeenCalledWith(
        expect.objectContaining({ page: 2 })
      );
    });
  });

  it('displays error message when search fails', async () => {
    const errorMessage = 'Search service unavailable';
    vi.mocked(transcriptService.searchTranscripts).mockRejectedValue({
      response: { data: { detail: errorMessage } }
    });
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });

  it('shows error when searching with empty term', async () => {
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    
    // Type a space and then clear it to trigger the search with empty term
    await user.type(searchInput, ' ');
    await user.clear(searchInput);
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText('Please enter a search term')).toBeInTheDocument();
    });
  });

  it('displays no results message when search returns empty', async () => {
    const emptyResponse = {
      ...mockSearchResponse,
      data: [],
      total: 0
    };
    
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(emptyResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'nonexistent');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText('No transcripts found')).toBeInTheDocument();
      expect(screen.getByText('Try adjusting your search terms or filters')).toBeInTheDocument();
    });
  });

  it('disables search button when loading', async () => {
    // Mock a delayed response
    vi.mocked(transcriptService.searchTranscripts).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockSearchResponse), 100))
    );
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    const searchButton = screen.getByTestId('search-button');
    
    await user.type(searchInput, 'login');
    await user.click(searchButton);
    
    expect(screen.getByRole('button', { name: /searching/i })).toBeDisabled();
    
    await waitFor(() => {
      expect(screen.getByTestId('search-button')).not.toBeDisabled();
    });
  });

  it('renders share and view ticket buttons for results', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      const viewButtons = screen.getAllByLabelText('View Ticket');
      expect(viewButtons).toHaveLength(2);
      
      const shareButtons = screen.getAllByLabelText('Share Transcript');
      expect(shareButtons).toHaveLength(2); // All results should have share buttons
    });
  });

  it('opens share dialog when share button is clicked', async () => {
    vi.mocked(transcriptService.searchTranscripts).mockResolvedValue(mockSearchResponse);
    vi.mocked(transcriptService.shareTranscript).mockResolvedValue({
      data: { share_token: 'abc123', share_url: 'https://example.com/shared/abc123' },
      success: true
    });
    
    render(<TranscriptSearch />);
    
    const searchInput = screen.getByPlaceholderText('Enter keywords to search in ticket conversations');
    await user.type(searchInput, 'login');
    await user.keyboard('{Enter}');
    
    await waitFor(() => {
      expect(screen.getByText('Login Issue')).toBeInTheDocument();
    });

    const shareButtons = screen.getAllByLabelText('Share Transcript');
    await user.click(shareButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Share Transcript')).toBeInTheDocument();
      expect(screen.getByDisplayValue(/shared\/abc123/)).toBeInTheDocument();
    });

    expect(transcriptService.shareTranscript).toHaveBeenCalledWith('ticket-1');
  });
});