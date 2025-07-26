import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import SharedTranscript from '../SharedTranscript';
import { transcriptService } from '../../services/transcriptService';

// Mock the transcript service
vi.mock('../../services/transcriptService', () => ({
  transcriptService: {
    getSharedTranscript: vi.fn(),
  },
}));

const mockTranscript = {
  id: 'transcript-1',
  ticket_id: 'ticket-1',
  content: 'This is a test transcript content',
  formatted_content: {
    messages: [
      {
        author: 'John Doe',
        type: 'user_message',
        content: 'Hello, I need help with my account',
        timestamp: '2024-01-15T10:00:00Z'
      },
      {
        author: 'Support Agent',
        type: 'staff_message',
        content: 'Hi John, I can help you with that. What seems to be the issue?',
        timestamp: '2024-01-15T10:01:00Z'
      }
    ]
  },
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:30:00Z'
};

const renderWithRouter = (shareToken: string) => {
  return render(
    <MemoryRouter initialEntries={[`/shared/${shareToken}`]}>
      <Routes>
        <Route path="/shared/:shareToken" element={<SharedTranscript />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('SharedTranscript', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.mocked(transcriptService.getSharedTranscript).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithRouter('valid-token');

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders transcript content when loaded successfully', async () => {
    vi.mocked(transcriptService.getSharedTranscript).mockResolvedValue({
      data: mockTranscript,
      success: true
    });

    renderWithRouter('valid-token');

    await waitFor(() => {
      expect(screen.getByText('Shared Transcript')).toBeInTheDocument();
      expect(screen.getByText('Conversation Transcript')).toBeInTheDocument();
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Support Agent')).toBeInTheDocument();
      expect(screen.getByText('Hello, I need help with my account')).toBeInTheDocument();
      expect(screen.getByText('Hi John, I can help you with that. What seems to be the issue?')).toBeInTheDocument();
    });

    expect(transcriptService.getSharedTranscript).toHaveBeenCalledWith('valid-token');
  });

  it('renders formatted messages with proper styling', async () => {
    vi.mocked(transcriptService.getSharedTranscript).mockResolvedValue({
      data: mockTranscript,
      success: true
    });

    renderWithRouter('valid-token');

    await waitFor(() => {
      // Check for user message chip
      const userChips = screen.getAllByText('user_message');
      expect(userChips.length).toBeGreaterThan(0);

      // Check for staff message chip
      const staffChips = screen.getAllByText('staff_message');
      expect(staffChips.length).toBeGreaterThan(0);

      // Check for timestamps
      expect(screen.getByText(/Jan 15, 2024 10:00/)).toBeInTheDocument();
      expect(screen.getByText(/Jan 15, 2024 10:01/)).toBeInTheDocument();
    });
  });

  it('falls back to plain text when formatted content is not available', async () => {
    const plainTranscript = {
      ...mockTranscript,
      formatted_content: null
    };

    vi.mocked(transcriptService.getSharedTranscript).mockResolvedValue({
      data: plainTranscript,
      success: true
    });

    renderWithRouter('valid-token');

    await waitFor(() => {
      expect(screen.getByText('This is a test transcript content')).toBeInTheDocument();
    });
  });

  it('shows error message for invalid token', async () => {
    vi.mocked(transcriptService.getSharedTranscript).mockRejectedValue({
      response: { status: 404 }
    });

    renderWithRouter('invalid-token');

    await waitFor(() => {
      expect(screen.getByText('This transcript link has expired or is invalid')).toBeInTheDocument();
    });
  });

  it('shows error message for permission denied', async () => {
    vi.mocked(transcriptService.getSharedTranscript).mockRejectedValue({
      response: { status: 403 }
    });

    renderWithRouter('restricted-token');

    await waitFor(() => {
      expect(screen.getByText('You do not have permission to view this transcript')).toBeInTheDocument();
    });
  });

  it('shows generic error message for other errors', async () => {
    vi.mocked(transcriptService.getSharedTranscript).mockRejectedValue({
      response: { status: 500 }
    });

    renderWithRouter('error-token');

    await waitFor(() => {
      expect(screen.getByText('Failed to load transcript')).toBeInTheDocument();
    });
  });

  it('shows error for missing share token', async () => {
    render(
      <MemoryRouter initialEntries={['/shared/']}>
        <Routes>
          <Route path="/shared/:shareToken?" element={<SharedTranscript />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Invalid share token')).toBeInTheDocument();
    });
  });

  it('displays creation and update timestamps', async () => {
    const transcriptWithDifferentTimes = {
      ...mockTranscript,
      created_at: '2024-01-15T10:00:00Z',
      updated_at: '2024-01-15T11:00:00Z'
    };

    vi.mocked(transcriptService.getSharedTranscript).mockResolvedValue({
      data: transcriptWithDifferentTimes,
      success: true
    });

    renderWithRouter('valid-token');

    await waitFor(() => {
      expect(screen.getByText(/Created: Jan 15, 2024 10:00/)).toBeInTheDocument();
      expect(screen.getByText(/Last updated: Jan 15, 2024 11:00/)).toBeInTheDocument();
    });
  });

  it('shows privacy notice', async () => {
    vi.mocked(transcriptService.getSharedTranscript).mockResolvedValue({
      data: mockTranscript,
      success: true
    });

    renderWithRouter('valid-token');

    await waitFor(() => {
      expect(screen.getByText('This is a shared transcript. Some information may be redacted for privacy.')).toBeInTheDocument();
    });
  });
});